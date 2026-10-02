"""
Parts of the site staff can turn off and on from the admin (Feature switches), without a redeploy.

Each switch is declared here with the state it starts in. The backend enforces a switch (auction rules
check `is_enabled('auctions')`); the frontend reads them all from /api/v1/features/ only to hide what
is switched off.
"""
from django.apps import apps as global_apps
from django.utils.translation import gettext_lazy as _

SWITCHES = {
    # Off until the site can take payments: starting auctions, deposits, bids, buy-now and seller bonds.
    'auctions': (False, _('Auctions: starting auctions, deposits, bids, buy now and the seller bond.')),
}


def default(name):
    return SWITCHES[name][0]


def description(name):
    return SWITCHES[name][1] if name in SWITCHES else ''


def is_enabled(name):
    from .models import FeatureSwitch
    enabled = FeatureSwitch.objects.filter(name=name).values_list('enabled', flat=True).first()
    return default(name) if enabled is None else enabled


def all_switches():
    from .models import FeatureSwitch
    stored = dict(FeatureSwitch.objects.values_list('name', 'enabled'))
    return {name: stored.get(name, default(name)) for name in SWITCHES}


def set_enabled(name, enabled):
    from .models import FeatureSwitch
    if name not in SWITCHES:
        raise KeyError(name)
    FeatureSwitch.objects.update_or_create(name=name, defaults={'enabled': enabled})


def create_missing_switches(apps=global_apps, using='default', **kwargs):
    """After `migrate` (and `flush`, which passes no `apps`): a row for every declared switch, at its
    default, so staff can find it in the admin."""
    try:
        FeatureSwitch = apps.get_model('features', 'FeatureSwitch')
    except LookupError:
        return  # migrating only other apps, before the features table exists
    for name in SWITCHES:
        FeatureSwitch.objects.using(using).get_or_create(name=name, defaults={'enabled': default(name)})
