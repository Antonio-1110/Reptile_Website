"""
One sweep over every API route, so a new endpoint can't quietly skip the permission and privacy rules
in .github/AGENTS.md §3. Each route's access rule is declared in ACCESS below, and a test fails when
the URLconf has a write (or private read) that isn't declared there: adding an endpoint means deciding
who may call it. The per-feature test classes still own the detailed behaviour.
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from account.models import Account
from auction import services
from auction.models import Auction, Order
from post.models import ContactRequest, EquipmentPost, LiveAnimalPost, SavedSearch, Species

# Who may call a route with a method:
#   public     anyone, signed in or not
#   signed_in  any signed-in account (the view may still refuse for business reasons)
#   owner      only the object's owner; anyone else is refused or can't see it
#   not_owner  any signed-in account except the owner (contacting, reporting, bidding on your own thing)
#   party      only the buyer or seller of an order or inquiry
ACCESS = {
    'profile': {'GET': 'signed_in', 'PUT': 'signed_in', 'PATCH': 'signed_in'},
    'account-plans': {'GET': 'public'},
    'seller-profile': {'GET': 'public'},
    'seller-reviews': {'GET': 'public', 'POST': 'not_owner', 'DELETE': 'signed_in'},

    'live-animal-list': {'GET': 'public', 'POST': 'signed_in'},
    'live-animal-detail': {'GET': 'public', 'PUT': 'owner', 'PATCH': 'owner', 'DELETE': 'owner'},
    'live-animal-mine': {'GET': 'signed_in'},
    'live-animal-favorites': {'GET': 'signed_in'},
    'live-animal-favorite': {'POST': 'signed_in', 'DELETE': 'signed_in'},
    'live-animal-contact': {'GET': 'not_owner', 'POST': 'not_owner'},
    'live-animal-report': {'POST': 'not_owner'},
    'live-animal-photos': {'POST': 'owner'},
    'equipment-list': {'GET': 'public', 'POST': 'signed_in'},
    'equipment-detail': {'GET': 'public', 'PUT': 'owner', 'PATCH': 'owner', 'DELETE': 'owner'},
    'equipment-mine': {'GET': 'signed_in'},
    'equipment-favorites': {'GET': 'signed_in'},
    'equipment-favorite': {'POST': 'signed_in', 'DELETE': 'signed_in'},
    'equipment-contact': {'GET': 'not_owner', 'POST': 'not_owner'},
    'equipment-report': {'POST': 'not_owner'},
    'equipment-photos': {'POST': 'owner'},
    'species-list': {'GET': 'public'},
    'species-detail': {'GET': 'public'},
    'saved-search-list': {'GET': 'signed_in', 'POST': 'signed_in'},
    'saved-search-detail': {'GET': 'owner', 'PATCH': 'owner', 'DELETE': 'owner'},
    'inquiry-list': {'GET': 'signed_in'},
    'inquiry-detail': {'GET': 'party'},
    'inquiry-replied': {'POST': 'owner'},  # the listing's seller
    'inquiry-waiting': {'GET': 'signed_in'},

    'auction-list': {'GET': 'public', 'POST': 'signed_in'},
    'auction-detail': {'GET': 'public'},
    'auction-mine': {'GET': 'signed_in'},
    'auction-rules': {'GET': 'public'},
    'auction-seller-bond': {'GET': 'signed_in', 'POST': 'signed_in'},
    'auction-bids': {'GET': 'public', 'POST': 'not_owner'},
    'auction-deposit': {'POST': 'not_owner'},
    'auction-buy-now': {'POST': 'not_owner'},
    'auction-cancel': {'POST': 'owner'},
    'order-list': {'GET': 'signed_in'},
    'order-detail': {'GET': 'party'},
    'order-pay': {'POST': 'party'},
    'order-handed-over': {'POST': 'party'},
    'order-confirm': {'POST': 'party'},
    'order-report-problem': {'POST': 'party'},
    'order-runner-up': {'POST': 'party'},
    'order-decline': {'POST': 'party'},
}

# Sign-in, registration and token endpoints are public by design; authentication/tests.py covers them.
EXEMPT_PREFIXES = ('/api/v1/auth/',)
EXEMPT_NAMES = {'api-root'}

# Never in a public response (AGENTS.md §3, Privacy).
PRIVATE_KEYS = {
    'contact_info', 'email', 'phone_number', 'personal_id', 'line_id', 'contact_email', 'instagram', 'facebook',
}

REFUSED = (401, 403, 404)
WRITE_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')


def api_routes():
    """(name, path pattern, methods) for every route under /api/v1/, read from the URLconf."""
    routes = {}

    def walk(patterns, prefix):
        for entry in patterns:
            if isinstance(entry, URLResolver):
                walk(entry.url_patterns, prefix + str(entry.pattern))
                continue
            path = '/' + (prefix + str(entry.pattern)).replace('^', '').replace('$', '')
            if not path.startswith('/api/v1/') or '<format>' in path or entry.name is None:
                continue
            callback = entry.callback
            view = getattr(callback, 'cls', None) or callback.view_class
            if getattr(callback, 'actions', None):
                methods = {method.upper() for method in callback.actions if method in view.http_method_names}
            else:
                methods = {method.upper() for method in view.http_method_names if hasattr(view, method)}
            routes.setdefault(entry.name, (path, set()))[1].update(methods - {'OPTIONS', 'HEAD'})

    walk(get_resolver().url_patterns, '')
    return {name: (path, methods) for name, (path, methods) in routes.items()}


def private_keys_in(data, path='$'):
    """Every PRIVATE_KEYS key anywhere in a JSON document, with where it was found."""
    found = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in PRIVATE_KEYS:
                found.append(f'{path}.{key}')
            found += private_keys_in(value, f'{path}.{key}')
    elif isinstance(data, list):
        for index, item in enumerate(data):
            found += private_keys_in(item, f'{path}[{index}]')
    return found


class AccessFixtures(APITestCase):
    def setUp(self):
        self.owner = self.make_account(
            'owner', account_type='commercial', is_paid_account=True, phone_number='0912345678',
            personal_id='A123456789', line_id='owner-line', contact_email='owner-contact@example.com',
            instagram='@owner_ig', facebook='owner.fb',
        )
        self.buyer = self.make_account('buyer')
        self.stranger = self.make_account('stranger')
        self.species = species = Species.objects.create(name='Ball Pythons')
        self.live_post = LiveAnimalPost.objects.create(
            account=self.owner, species=species, title='Pied Ball Python', description='Healthy animal',
            contact_info='{"line": "owner-line"}',
        )
        self.equipment_post = EquipmentPost.objects.create(
            account=self.owner, title='Glass tank', description='40 gallons', contact_info='{"line": "owner-line"}',
        )
        self.saved_search = SavedSearch.objects.create(
            account=self.owner, name='Pythons', query='category=live_animal', last_alerted_at=timezone.now(),
        )
        self.auction = self.make_auction(live_animal_post=self.live_post, buy_now_price=Decimal('9000.00'))
        self.inquiry = ContactRequest.objects.create(requester=self.buyer, live_animal_post=self.live_post)

        # A second auction, won by the buyer, for the order routes.
        sold_listing = LiveAnimalPost.objects.create(
            account=self.owner, species=species, title='Albino Ball Python', description='Healthy animal', contact_info='{}',
        )
        sold = self.make_auction(live_animal_post=sold_listing)
        deposit, _ = services.request_deposit(sold, self.buyer)
        services.confirm_deposit(deposit)
        services.place_bid(sold, self.buyer, '5000')
        Auction.objects.filter(pk=sold.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
        services.settle_auction(sold)
        self.order = Order.objects.get(auction=sold)

    @staticmethod
    def make_account(username, **fields):
        return Account.objects.create_user(
            username=username, email=f'{username}@example.com', password='pass12345', **fields,
        )

    def make_auction(self, **fields):
        return Auction.objects.create(
            seller=self.owner, starting_price=Decimal('5000.00'), min_increment=Decimal('100.00'),
            deposit_amount=Decimal('500.00'), currency='TWD', starts_at=timezone.now() - timedelta(minutes=1),
            ends_at=timezone.now() + timedelta(days=3), **fields,
        )

    def object_for(self, name):
        """The owner's object that a detail route is about."""
        if name.startswith('live-animal-'):
            return self.live_post
        if name.startswith('equipment-'):
            return self.equipment_post
        if name.startswith('species-'):
            return self.species
        if name.startswith('saved-search-'):
            return self.saved_search
        if name.startswith('order-'):
            return self.order
        if name.startswith('inquiry-'):
            return self.inquiry
        if name.startswith('seller-'):
            return self.owner
        return self.auction

    def url_for(self, name, path):
        return reverse(name, kwargs={'pk': self.object_for(name).pk}) if 'pk>' in path else reverse(name)

    def call(self, user, method, url):
        self.client.force_authenticate(user)
        return getattr(self.client, method.lower())(url, {}, format='json')


class RouteDeclarationTests(AccessFixtures):
    def test_every_api_route_declares_who_may_call_it(self):
        undeclared = []
        for name, (path, methods) in api_routes().items():
            if name in EXEMPT_NAMES or path.startswith(EXEMPT_PREFIXES):
                continue
            missing = methods - set(ACCESS.get(name, {}))
            if missing:
                undeclared.append(f'{name} {sorted(missing)} ({path})')
        self.assertEqual(undeclared, [], 'Add these routes to ACCESS in common/test_access.py.')

    def test_access_table_has_no_stale_routes(self):
        routes = api_routes()
        stale = [
            f'{name} {method}' for name, rules in ACCESS.items() for method in rules
            if name not in routes or method not in routes[name][1]
        ]
        self.assertEqual(stale, [])


class PermissionSweepTests(AccessFixtures):
    def routes_with(self, *rules):
        for name, (path, methods) in api_routes().items():
            for method in sorted(methods):
                if ACCESS.get(name, {}).get(method) in rules:
                    yield name, method, self.url_for(name, path)

    def test_anonymous_visitors_cannot_write_or_read_private_data(self):
        for name, method, url in self.routes_with('signed_in', 'owner', 'not_owner', 'party'):
            with self.subTest(route=name, method=method):
                self.assertIn(self.call(None, method, url).status_code, (401, 403))

    def test_anonymous_visitors_can_read_public_routes(self):
        for name, method, url in self.routes_with('public'):
            if method != 'GET':
                continue
            with self.subTest(route=name):
                self.assertEqual(self.call(None, method, url).status_code, 200)

    def test_other_accounts_cannot_touch_the_owners_things(self):
        for name, method, url in self.routes_with('owner', 'party'):
            with self.subTest(route=name, method=method):
                self.assertIn(self.call(self.stranger, method, url).status_code, REFUSED)
        self.live_post.refresh_from_db()
        self.assertEqual(self.live_post.title, 'Pied Ball Python')
        self.assertTrue(SavedSearch.objects.filter(pk=self.saved_search.pk).exists())
        self.assertEqual(Auction.objects.get(pk=self.auction.pk).status, Auction.Status.ACTIVE)

    def test_owners_cannot_contact_report_or_bid_on_their_own_things(self):
        for name, method, url in self.routes_with('not_owner'):
            with self.subTest(route=name, method=method):
                self.assertGreaterEqual(self.call(self.owner, method, url).status_code, 400)

    def test_owners_and_parties_get_past_the_permission_checks(self):
        # Parties first: deleting the owner's listing below also deletes its inquiry.
        for user in (self.owner, self.buyer):
            response = self.call(user, 'GET', reverse('order-detail', kwargs={'pk': self.order.pk}))
            self.assertEqual(response.status_code, 200)
            response = self.call(user, 'GET', reverse('inquiry-detail', kwargs={'pk': self.inquiry.pk}))
            self.assertEqual(response.status_code, 200)
        # Deletes go last so the objects are still there for everything else.
        checks = sorted(self.routes_with('owner'), key=lambda check: check[1] == 'DELETE')
        for name, method, url in checks:
            with self.subTest(route=name, method=method):
                self.assertNotIn(self.call(self.owner, method, url).status_code, REFUSED)


class PublicPrivacySweepTests(AccessFixtures):
    def test_public_responses_never_contain_contact_details(self):
        secrets = ['owner@example.com', '0912345678', 'A123456789', 'owner-line', 'owner-contact@example.com',
                   '@owner_ig', 'owner.fb']
        for viewer in (None, self.stranger):
            for name, (path, methods) in api_routes().items():
                if 'GET' not in methods or ACCESS.get(name, {}).get('GET') != 'public':
                    continue
                url = self.url_for(name, path)
                with self.subTest(route=name, viewer=getattr(viewer, 'username', 'anonymous')):
                    response = self.call(viewer, 'GET', url)
                    self.assertEqual(response.status_code, 200)
                    body = response.content.decode()
                    self.assertEqual(private_keys_in(json.loads(body)), [])
                    for secret in secrets:
                        self.assertNotIn(secret, body)
