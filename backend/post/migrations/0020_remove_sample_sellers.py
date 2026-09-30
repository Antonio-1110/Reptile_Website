"""
Removes the six sample sellers (and their listings) that migration 0006 added to every database,
including the live one, so the public site only shows real people. It matches each account on the
username and email 0006 gave it, and only while it still looks untouched: no password anyone could sign
in with, never signed in, not staff. Anything that doesn't match (or is already gone) is left alone.
"""
import logging

from django.db import migrations
from django.db.models import ProtectedError

logger = logging.getLogger(__name__)

# (username, email) exactly as 0006_liveanimalpost_gallery_... created them.
SAMPLE_SELLERS = [
    ('Apex Exotics', 'apex.exotics@example.com'),
    ('High Ridge Geckos', 'highridge.geckos@example.com'),
    ('Morph Kingdom', 'morphkingdom@example.com'),
    ('Desert Scales', 'desertscales@example.com'),
    ('Emerald Scale Co.', 'emeraldscale@example.com'),
    ('Moonlight Morphs', 'moonlightmorphs@example.com'),
]


def remove_sample_sellers(apps, schema_editor):
    Account = apps.get_model('account', 'Account')
    for username, email in SAMPLE_SELLERS:
        account = Account.objects.filter(
            username=username, email=email, last_login__isnull=True, is_staff=False, is_superuser=False,
        ).first()
        # 0006 never set a password, so the account can't be signed in to. One that has a real password
        # now belongs to someone; leave it.
        if account is None or (account.password and not account.password.startswith('!')):
            continue
        try:
            account.delete()  # takes the account's listings, favorites, inquiries and reviews with it
        except ProtectedError:
            logger.warning('Kept sample seller %s: money is still held for one of its auctions.', username)


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0009_account_google_id'),
        ('post', '0019_contact_request_replied_at'),
    ]

    operations = [
        migrations.RunPython(remove_sample_sellers, migrations.RunPython.noop),
    ]
