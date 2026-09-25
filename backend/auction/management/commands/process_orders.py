"""
Apply order deadlines that have passed (auction/orders.py): winners who didn't pay, runner-up offers
that lapsed, sellers who didn't hand over, and confirmation windows that closed. Run it on a schedule
next to close_auctions, e.g. every 5 minutes from cron:

    python manage.py close_auctions && python manage.py process_orders
"""
from django.core.management.base import BaseCommand

from auction.orders import process_due_orders


class Command(BaseCommand):
    help = 'Apply order deadlines that have passed.'

    def handle(self, *args, **options):
        changed = process_due_orders()
        self.stdout.write(f'Updated {changed} order(s).')
