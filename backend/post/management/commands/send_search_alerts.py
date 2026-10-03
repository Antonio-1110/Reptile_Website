"""
Alert users on the site to new listings matching their saved searches:

    python manage.py send_search_alerts

Run it on a schedule (every few hours, e.g. from cron). Each run covers listings posted since the
previous alert for that search, so running it more or less often only changes how batched the alerts are.
"""
from django.core.management.base import BaseCommand

from post.search_alerts import send_all_alerts


class Command(BaseCommand):
    help = 'Alert users to the new listings that match their saved searches.'

    def handle(self, *args, **options):
        checked, alerted = send_all_alerts()
        self.stdout.write(f'Checked {checked} saved search(es); made {alerted} alert(s).')
