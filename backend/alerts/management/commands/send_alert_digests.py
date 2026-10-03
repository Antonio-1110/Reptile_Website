"""
Email a summary of unread alerts to accounts where they have piled up:

    python manage.py send_alert_digests

Run it on a schedule (e.g. hourly). How many unread alerts, and how old, trigger a summary is set by
ALERT_DIGEST_MIN_UNREAD and ALERT_DIGEST_MIN_DAYS; each alert is emailed at most once.
"""
from django.core.management.base import BaseCommand

from alerts.services import send_digests


class Command(BaseCommand):
    help = 'Email users a summary of their unread alerts once enough have waited long enough.'

    def handle(self, *args, **options):
        self.stdout.write(f'Sent {send_digests()} alert summary email(s).')
