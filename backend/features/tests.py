from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import FeatureSwitch
from .switches import is_enabled, set_enabled


class FeatureSwitchTests(APITestCase):
    def test_every_declared_switch_starts_at_its_default(self):
        self.assertFalse(FeatureSwitch.objects.get(name='auctions').enabled)
        self.assertFalse(is_enabled('auctions'))

    def test_anyone_can_read_which_features_are_on(self):
        response = self.client.get(reverse('features'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'auctions': False})
        set_enabled('auctions', True)
        self.assertEqual(self.client.get(reverse('features')).data, {'auctions': True})

    def test_a_missing_row_falls_back_to_the_default(self):
        FeatureSwitch.objects.all().delete()
        self.assertFalse(is_enabled('auctions'))
        self.assertEqual(self.client.get(reverse('features')).data, {'auctions': False})

    def test_staff_turn_switches_on_and_off_in_the_admin(self):
        admin = get_user_model().objects.create_superuser('boss', 'boss@example.com', 'pass1234')
        self.client.force_login(admin)
        switch = FeatureSwitch.objects.get(name='auctions')
        changelist = reverse('admin:features_featureswitch_changelist')
        page = self.client.get(changelist)
        self.assertContains(page, 'Auctions: starting auctions')
        response = self.client.post(changelist, {
            'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '1', 'form-0-id': str(switch.pk),
            'form-0-enabled': 'on', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(is_enabled('auctions'))
        # Switches come from code, so the admin can't add or delete them.
        self.assertEqual(self.client.get(reverse('admin:features_featureswitch_add')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:features_featureswitch_delete', args=[switch.pk])).status_code, 403)

    def test_command_lists_and_flips_switches(self):
        out = StringIO()
        call_command('feature', 'auctions', 'on', stdout=out)
        self.assertTrue(is_enabled('auctions'))
        self.assertIn('auctions: on', out.getvalue())
        call_command('feature', 'auctions', 'off', stdout=StringIO())
        self.assertFalse(is_enabled('auctions'))


class FeatureSwitchFlushTests(TransactionTestCase):
    """TransactionTestCase empties the database with `flush`, which sends post_migrate without `apps`."""

    def test_switches_come_back_after_a_flush(self):
        FeatureSwitch.objects.all().delete()
        call_command('flush', interactive=False, verbosity=0)
        self.assertFalse(FeatureSwitch.objects.get(name='auctions').enabled)
