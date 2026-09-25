"""
Email users about new listings matching their saved searches:

    python manage.py send_search_alerts

Run it on a schedule (every few hours, e.g. from cron). Each run covers listings posted since the
previous alert for that search, so running it more or less often only changes how batched the emails are.
"""
from django.core.management.base import BaseCommand

from post.search_alerts import send_all_alerts


class Command(BaseCommand):
    help = 'Email users the new listings that match their saved searches.'

    def handle(self, *args, **options):
        checked, emailed = send_all_alerts()
        self.stdout.write(f'Checked {checked} saved search(es); sent {emailed} email(s).')
