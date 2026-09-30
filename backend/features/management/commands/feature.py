from django.core.management.base import BaseCommand, CommandError

from features import switches


class Command(BaseCommand):
    help = 'List the feature switches, or turn one on or off: manage.py feature auctions on'

    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', choices=sorted(switches.SWITCHES))
        parser.add_argument('state', nargs='?', choices=['on', 'off'])

    def handle(self, *args, name=None, state=None, **options):
        if name and not state:
            raise CommandError('Say "on" or "off".')
        if name:
            switches.set_enabled(name, state == 'on')
        for switch, enabled in switches.all_switches().items():
            self.stdout.write(f'{switch}: {"on" if enabled else "off"}')
