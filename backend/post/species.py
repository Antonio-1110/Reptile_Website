"""
The species list and its review queue, in one place so the listing API and the admin behave the same.

Sellers may type a species that isn't in the list. The listing is saved but kept off the marketplace
(and out of search alerts and auctions) until staff review the name in the admin (Species requests):
- map it to an existing species: the name becomes an alias of that species, so the next seller who
  types it gets the species straight away;
- add it as a new species;
- or reject it: the seller is asked to choose a species from the list.
Either way the sellers waiting on it are emailed.
"""
import re

from django.conf import settings
from django.core.mail import mail_admins
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from common.notifications import send_notification

from .models import Species, SpeciesAlias, SpeciesRequest


def normalize(name):
    """Case, spacing and punctuation don't make a different species: "Ball-python" == "ball python"."""
    return re.sub(r'[\W_]+', '', name.casefold())


def find_species(name):
    """The species whose name or alias matches `name`, or None."""
    key = normalize(name)
    if not key:
        return None
    # The list is small (hundreds of rows), and the matching rules aren't expressible in SQL.
    for species in Species.objects.all():
        if normalize(species.name) == key:
            return species
    for alias in SpeciesAlias.objects.select_related('species'):
        if normalize(alias.name) == key:
            return alias.species
    return None


def find_open_request(name):
    """The pending or rejected request for `name`, if one exists (newest first)."""
    key = normalize(name)
    candidates = SpeciesRequest.objects.exclude(status=SpeciesRequest.Status.APPROVED)
    return next((request for request in candidates if normalize(request.name) == key), None)


def request_species(name):
    """The pending request listings asking for `name` wait on, created (and staff told) if needed."""
    existing = find_open_request(name)
    if existing and existing.status == SpeciesRequest.Status.PENDING:
        return existing
    species_request = SpeciesRequest.objects.create(name=name.strip())
    transaction.on_commit(lambda: mail_admins(
        f'New species to review: {species_request.name}',
        f'A seller listed an animal as "{species_request.name}", which isn\'t in the species list. '
        'The listing stays unpublished until the name is reviewed in the admin: Species requests.',
        fail_silently=True,
    ))
    return species_request


def release(species_request):
    """Drop a pending request no listing is waiting on any more, so the review queue stays accurate."""
    if (
        species_request
        and species_request.status == SpeciesRequest.Status.PENDING
        and not species_request.listings.exists()
    ):
        species_request.delete()


def _mark_reviewed(species_request, status, staff_user):
    species_request.status = status
    species_request.reviewed_by = staff_user
    species_request.reviewed_at = timezone.now()


@transaction.atomic
def approve(species_request, species, staff_user):
    """
    Accept the request as `species` (an existing one, or one just created for it) and publish the
    listings waiting on it. A name that differs from the species' own is kept as an alias.
    """
    if normalize(species_request.name) != normalize(species.name) and find_species(species_request.name) != species:
        SpeciesAlias.objects.update_or_create(name=species_request.name, defaults={'species': species})
    _mark_reviewed(species_request, SpeciesRequest.Status.APPROVED, staff_user)
    species_request.species = species
    species_request.save()
    listings = list(species_request.listings.select_related('account'))
    species_request.listings.update(species=species, species_request=None)
    transaction.on_commit(lambda: _email_approved(listings, species_request.name, species.name))
    return len(listings)


@transaction.atomic
def create_and_approve(species_request, staff_user, name=''):
    """Add the request as a new species (named `name`, or as requested) and approve it."""
    species = Species.objects.create(name=(name or species_request.name).strip())
    return approve(species_request, species, staff_user)


@transaction.atomic
def reject(species_request, staff_user, note=''):
    """Turn the name down; its listings stay unpublished until their sellers choose a listed species."""
    _mark_reviewed(species_request, SpeciesRequest.Status.REJECTED, staff_user)
    species_request.species = None
    species_request.staff_note = note
    species_request.save()
    listings = list(species_request.listings.select_related('account'))
    transaction.on_commit(lambda: _email_rejected(listings, species_request.name, note))
    return len(listings)


def _email_approved(listings, requested, species_name):
    for post in listings:
        values = {'title': post.title, 'requested': requested, 'species': species_name}
        send_notification([post.account.email], lambda values=values, post=post: (
            _('Your listing is live: %(title)s') % values,
            _('We reviewed the species you entered, "%(requested)s", and listed it as "%(species)s". Your listing "%(title)s" is now on the marketplace.') % values
            + f'\n\n{settings.FRONTEND_URL}/posts/{post.id}',
        ))


def _email_rejected(listings, requested, note):
    for post in listings:
        values = {'title': post.title, 'requested': requested, 'note': note}

        def build(values=values, post=post):
            body = _('We couldn\'t add "%(requested)s" to our species list, so your listing "%(title)s" isn\'t on the marketplace yet.') % values
            if note:
                body += '\n\n' + _('Reason: %(note)s') % values
            body += '\n\n' + _('Edit the listing and choose a species from the list to publish it: %(url)s') % {
                'url': f'{settings.FRONTEND_URL}/postinput?edit={post.id}&category=live_animal',
            }
            return _('Choose a different species for your listing: %(title)s') % values, body

        send_notification([post.account.email], build)
