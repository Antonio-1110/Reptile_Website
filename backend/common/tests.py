from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.throttling import ScopedRateThrottle

from account.models import Account
from post.models import LiveAnimalPost, Species

LOW_RATES = {'auth': '2/minute', 'contact': '2/hour', 'report': '2/hour', 'payments': '2/hour'}


# The test settings use a cache that stores nothing (so limits never trip elsewhere in the suite);
# these tests need a real one. DRF copies the rates at import time, so they're patched directly.
@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
@mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', LOW_RATES)
class RateLimitTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')
        self.buyer = Account.objects.create_user(username='buyer', email='buyer@example.com', password='pass12345')
        species = Species.objects.create(name='Ball Pythons')
        self.post = LiveAnimalPost.objects.create(
            account=self.seller, species=species, title='Pied', description='Healthy', contact_info='{}',
        )

    def test_login_attempts_are_limited(self):
        url = reverse('jwt-login')
        codes = [self.client.post(url, {'username': 'buyer', 'password': 'wrong'}).status_code for _ in range(3)]
        self.assertEqual(codes, [401, 401, 429])

    def test_contact_requests_are_limited(self):
        self.client.force_authenticate(self.buyer)
        url = reverse('live-animal-contact', args=[self.post.id])
        codes = [self.client.get(url).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_limits_are_per_user(self):
        url = reverse('live-animal-report', args=[self.post.id])
        self.client.force_authenticate(self.buyer)
        for _ in range(2):
            self.client.post(url)
        self.assertEqual(self.client.post(url).status_code, 429)

        other = Account.objects.create_user(username='other', email='other@example.com', password='pass12345')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(url).status_code, 200)
