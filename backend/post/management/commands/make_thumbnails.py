"""
Make the card-sized copy of every listing's cover photo that doesn't have one yet:

    python manage.py make_thumbnails

New photos get theirs when they're uploaded; this is for listings from before thumbnails existed. It's
safe to run again: listings that already have one are skipped. Covers this app didn't store (the demo
data's hot-linked photos) are left alone, and their cards keep showing the cover itself.
"""
from urllib.parse import urljoin

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from post import photos as listing_photos
from post.models import EquipmentPost, LiveAnimalPost


class Command(BaseCommand):
    help = "Make card-sized copies of listing cover photos that don't have one yet."

    def handle(self, *args, **options):
        made = failed = 0
        for model in (LiveAnimalPost, EquipmentPost):
            for post in model.objects.exclude(image='').filter(thumbnail='').order_by('pk').iterator():
                if not listing_photos.stored_name(post.image):
                    continue
                try:
                    # Storage URLs are relative locally; the cover's own URL supplies the host.
                    listing_photos.refresh_thumbnail(post, lambda name: urljoin(post.image, default_storage.url(name)))
                except Exception as error:  # a missing or unreadable file shouldn't stop the others
                    failed += 1
                    self.stderr.write(f'{model.__name__} {post.pk}: {error}')
                    continue
                post.save(update_fields=['thumbnail'])
                made += 1
        self.stdout.write(f'Made {made} thumbnail(s); {failed} failed.')
