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


class ApiConventionTests(APITestCase):
    """The conventions every endpoint follows (see common/exceptions.py and the root urls.py)."""

    def setUp(self):
        self.seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')
        species = Species.objects.create(name='Ball Pythons')
        self.post = LiveAnimalPost.objects.create(
            account=self.seller, species=species, title='Pied', description='Healthy', contact_info='{}',
        )

    def test_every_endpoint_is_under_api_v1(self):
        for name, args in [
            ('jwt-login', []), ('profile', []), ('account-plans', []), ('live-animal-list', []),
            ('equipment-list', []), ('species-list', []), ('saved-search-list', []), ('auction-list', []),
            ('order-list', []), ('seller-profile', [self.seller.id]), ('seller-reviews', [self.seller.id]),
        ]:
            self.assertTrue(reverse(name, args=args).startswith('/api/v1/'), name)
        self.assertEqual(self.client.get('/api/posts/live-animals/').status_code, 404)

    def test_field_errors_are_lists_keyed_by_field(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('live-animal-list'), {'description': 'd', 'species': self.post.species_id}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIsInstance(response.data['title'], list)

    @override_settings(SAVED_SEARCH_LIMIT=0)
    def test_errors_about_the_whole_request_are_a_single_detail_string(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('saved-search-list'), {'query': 'search=pied'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'You can keep up to 0 saved searches. Delete one to save another.')

    def test_the_seller_object_is_public_information_only(self):
        data = self.client.get(reverse('live-animal-detail', args=[self.post.id])).data
        self.assertEqual(set(data['seller']), {
            'id', 'username', 'display_name', 'is_commercial', 'verified_seller', 'seller_rating', 'total_reviews',
        })
        self.assertFalse({'seller_id', 'seller_name', 'seller_rating'} & set(data))
