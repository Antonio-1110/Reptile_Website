"""
Close every auction whose end time has passed: record the winner and refund the other bidders'
deposits. Run it on a schedule (e.g. every minute from cron):

    python manage.py close_auctions
"""
from django.core.management.base import BaseCommand

from auction.services import settle_due_auctions


class Command(BaseCommand):
    help = 'Settle auctions whose end time has passed.'

    def handle(self, *args, **options):
        settled = settle_due_auctions()
        self.stdout.write(f'Settled {len(settled)} auction(s).')
