"""
Saved searches and their email alerts, in one place: what a saved query may contain, which new
listings match it, and sending the emails (run `manage.py send_search_alerts` every few hours).
"""
import operator
from functools import reduce

from django.conf import settings
from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone
from django.utils.translation import gettext as _, ngettext

from common.money import format_money
from common.notifications import send_notification

from .filters import LiveAnimalPostFilter
from .models import LiveAnimalPost, SavedSearch

# Same fields as the marketplace's ?search= (LiveAnimalViewSet.search_fields), so an alert matches
# exactly what the user would see.
SEARCH_FIELDS = ['title', 'description', 'genetics', 'species__name']
ALLOWED_KEYS = set(LiveAnimalPostFilter.base_filters) | {'search'}
# How many new listings one email lists (the rest are counted).
LISTINGS_PER_EMAIL = 10


def normalize_query(query):
    """Checks a listing-API query string and returns it in a stable form; raises ValueError if bad."""
    params = QueryDict(query.lstrip('?'), mutable=True)
    params.pop('page', None)
    unknown = sorted(set(params) - ALLOWED_KEYS)
    if unknown:
        raise ValueError(unknown)
    form = LiveAnimalPostFilter(data=params, queryset=LiveAnimalPost.objects.none()).form
    if not form.is_valid():
        raise ValueError(sorted(form.errors))
    return _stable_urlencode(params)


def _stable_urlencode(params):
    ordered = QueryDict(mutable=True)
    for key in sorted(params):
        ordered.setlist(key, params.getlist(key))
    return ordered.urlencode()


def matching_listings(saved_search, since):
    """Listings created after `since` that match the saved search, other than the user's own."""
    params = QueryDict(saved_search.query)
    # Hidden (moderated) and sold listings are left out, as they are from the marketplace itself.
    queryset = LiveAnimalPost.objects.filter(created_at__gt=since, is_hidden=False).exclude(
        status=LiveAnimalPost.Status.SOLD,
    ).exclude(account=saved_search.account)
    queryset = LiveAnimalPostFilter(data=params, queryset=queryset).qs
    for term in params.get('search', '').split():
        queryset = queryset.filter(reduce(operator.or_, (Q(**{f'{field}__icontains': term}) for field in SEARCH_FIELDS)))
    return queryset.select_related('species').order_by('-created_at', '-id')


def send_alert(saved_search, now=None):
    """Email the new matches since the last alert, if any. Returns how many listings matched."""
    now = now or timezone.now()
    listings = list(matching_listings(saved_search, saved_search.last_alerted_at).filter(created_at__lte=now))
    saved_search.last_alerted_at = now
    saved_search.save(update_fields=['last_alerted_at'])
    if not listings:
        return 0

    values = {'name': saved_search.name, 'count': len(listings)}

    def build():
        lines = [
            f'- {post.title}' + (f' ({format_money(post.price)})' if post.price is not None else '')
            + f'\n  {settings.FRONTEND_URL}/posts/{post.id}'
            for post in listings[:LISTINGS_PER_EMAIL]
        ]
        more = len(listings) - LISTINGS_PER_EMAIL
        body = (
            _('New listings match your saved search "%(name)s":') % values + '\n\n' + '\n'.join(lines)
            + ('\n' + _('…and %(more)s more.') % {'more': more} if more > 0 else '')
            + '\n\n' + _('Manage your saved searches: %(url)s') % {'url': f'{settings.FRONTEND_URL}/saved-searches'}
        )
        subject = ngettext('%(count)s new listing for "%(name)s"', '%(count)s new listings for "%(name)s"', len(listings)) % values
        return subject, body

    send_notification([saved_search.account.email], build)
    return len(listings)


def send_all_alerts():
    """Every saved search, once. Returns (searches checked, emails sent)."""
    now = timezone.now()
    emails = 0
    for saved_search in SavedSearch.objects.select_related('account').filter(account__is_active=True):
        if send_alert(saved_search, now):
            emails += 1
    return SavedSearch.objects.filter(account__is_active=True).count(), emails
