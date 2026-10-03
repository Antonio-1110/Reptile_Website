"""
Clean-up after a listing is deleted, however that happens: by its seller through the API, by staff in
the admin, or along with its account. Doing it here rather than in the viewsets means the admin's
delete can't skip it.
"""
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from . import photos as listing_photos
from . import species as species_catalog
from .models import EquipmentPost, LiveAnimalPost


@receiver(post_delete, sender=LiveAnimalPost)
@receiver(post_delete, sender=EquipmentPost)
def remove_listing_leftovers(sender, instance, **kwargs):
    # Uploaded photos are public files; left behind they would stay reachable (and billed) forever.
    # Removed only once the delete is committed, so a delete that rolls back keeps its photos.
    folder = listing_photos.photo_folder(instance)
    transaction.on_commit(lambda: listing_photos.delete_photo_folder(folder))
    if sender is LiveAnimalPost:
        species_catalog.release(instance.species_request)
