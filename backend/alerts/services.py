from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Min, Q
from django.utils import timezone, translation
from django.utils.translation import gettext as _, ngettext

from account.models import Account
from common.notifications import send_notification

from .models import Alert


def listing_path(post):
    """The website path of a listing's page."""
    return f'/equipment/{post.pk}' if post._meta.model_name == 'equipmentpost' else f'/posts/{post.pk}'


def _texts(build):
    texts = {}
    for language_code, _name in settings.LANGUAGES:
        with translation.override(language_code):
            title, body = build()
            texts[language_code] = {'title': str(title), 'body': str(body)}
    return texts


def notify(accounts, build, *, link='', email=False):
    """
    Give each account an alert on the site. `build()` returns (title, body) in the active language,
    like common.notifications.send_notification, and is called once per language.

    email=True also emails it right away: for messages with a deadline or money at stake. Everything
    else waits on the site, and only reaches the inbox in a summary if it goes unread (see
    send_digests), which keeps email volume, and its cost, down.
    """
    accounts = [account for account in accounts if account is not None]
    if not accounts:
        return
    now = timezone.now()
    texts = _texts(build)
    Alert.objects.bulk_create([
        Alert(account=account, text=texts, link=link, emailed_at=now if email else None) for account in accounts
    ])
    if email:
        send_notification([account.email for account in accounts], build)


def text_for(alert, language_code=None):
    """The alert's (title, body) in the active language, falling back to English."""
    language_code = language_code or translation.get_language() or 'en'
    text = alert.text.get(language_code) or alert.text.get(language_code.split('-')[0]) or alert.text.get('en') or {}
    return text.get('title', ''), text.get('body', '')


def _waiting():
    return Q(alerts__read_at__isnull=True, alerts__emailed_at__isnull=True)


def send_digests(now=None):
    """
    Email a summary to each account whose unread (and not yet emailed) alerts number at least
    ALERT_DIGEST_MIN_UNREAD and have waited at least ALERT_DIGEST_MIN_DAYS, then drop alerts older
    than ALERT_RETENTION_DAYS. Returns how many summaries were sent.
    """
    now = now or timezone.now()
    oldest_allowed = now - timedelta(days=settings.ALERT_DIGEST_MIN_DAYS)
    due = (
        Account.objects.filter(is_active=True, email_verified=True)
        .annotate(waiting=Count('alerts', filter=_waiting()), oldest=Min('alerts__created_at', filter=_waiting()))
        .filter(waiting__gte=settings.ALERT_DIGEST_MIN_UNREAD, oldest__lte=oldest_allowed)
    )
    sent = 0
    for account in due:
        alerts = list(account.alerts.filter(read_at__isnull=True, emailed_at__isnull=True).order_by('created_at', 'id'))
        if not alerts:
            continue
        send_notification([account.email], lambda alerts=alerts: _digest(alerts))
        Alert.objects.filter(pk__in=[alert.pk for alert in alerts]).update(emailed_at=now)
        sent += 1
    Alert.objects.filter(created_at__lt=now - timedelta(days=settings.ALERT_RETENTION_DAYS)).delete()
    return sent


def _digest(alerts):
    count = len(alerts)
    lines = '\n'.join(f'- {text_for(alert)[0]}' for alert in alerts)
    subject = ngettext(
        'You have %(count)s unread alert on Reptilian', 'You have %(count)s unread alerts on Reptilian', count,
    ) % {'count': count}
    body = (
        _('These alerts are waiting for you on Reptilian:') + '\n\n' + lines + '\n\n'
        + _('Read them here: %(url)s') % {'url': f'{settings.FRONTEND_URL}/alerts'}
    )
    return subject, body
