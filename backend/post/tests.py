import json
import io
import shutil
import tempfile
from pathlib import Path

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APITestCase

from account.models import Account
from .models import ContactRequest, EquipmentPost, LiveAnimalPost, Report, SavedSearch, Species


class PostLimitTests(APITestCase):
	def setUp(self):
		self.account = Account.objects.create_user(
			username='seller',
			email='seller@example.com',
			password='pass1234',
		)
		self.species = Species.objects.create(name='Ball Pythons')
		self.client.force_authenticate(self.account)

	def post_payload(self, **overrides):
		payload = {
			'title': 'Ball Python',
			'description': 'Healthy animal',
			'price': '450.00',
			'location': 'TPE',
			'contact_info': {},
			'species': self.species.id,
			'sex': 'unsexed',
			'life_stage': 'adult',
			'shipping_methods': ['localPickup'],
			'gallery': [],
		}
		payload.update(overrides)
		return payload

	def test_hobbyist_cannot_create_a_sixth_post(self):
		for index in range(self.account.max_post_count):
			LiveAnimalPost.objects.create(
				account=self.account,
				species=self.species,
				title=f'Existing {index}',
				description='Existing animal',
				contact_info='{}',
			)

		response = self.client.post(
			reverse('live-animal-list'),
			self.post_payload(),
			format='json',
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn('Post limit reached', str(response.data))

	def test_hobbyist_cannot_create_a_post_with_four_images(self):
		response = self.client.post(
			reverse('live-animal-list'),
			self.post_payload(
				image='https://example.com/cover.jpg',
				gallery=[
					'https://example.com/one.jpg',
					'https://example.com/two.jpg',
					'https://example.com/three.jpg',
				],
			),
			format='json',
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn('Image limit exceeded', str(response.data))

	def test_hobbyist_can_create_post_at_image_limit(self):
		response = self.client.post(
			reverse('live-animal-list'),
			self.post_payload(
				image='https://example.com/cover.jpg',
				gallery=[
					'https://example.com/one.jpg',
					'https://example.com/two.jpg',
				],
			),
			format='json',
		)

		self.assertEqual(response.status_code, 201)

	def test_hobbyist_cannot_update_post_over_image_limit(self):
		post = LiveAnimalPost.objects.create(
			account=self.account,
			species=self.species,
			title='Existing animal',
			description='Existing animal',
			contact_info='{}',
			image='https://example.com/cover.jpg',
			gallery=['https://example.com/one.jpg', 'https://example.com/two.jpg'],
		)

		response = self.client.patch(
			reverse('live-animal-detail', args=[post.id]),
			{'gallery': [
				'https://example.com/one.jpg',
				'https://example.com/two.jpg',
				'https://example.com/three.jpg',
			]},
			format='json',
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn('Image limit exceeded', str(response.data))

	def test_seller_cannot_update_another_sellers_post(self):
		post = LiveAnimalPost.objects.create(
			account=self.account,
			species=self.species,
			title='Existing animal',
			description='Existing animal',
			contact_info='{}',
		)
		other_account = Account.objects.create_user(
			username='other-seller',
			email='other@example.com',
			password='pass1234',
		)
		self.client.force_authenticate(other_account)

		response = self.client.patch(
			reverse('live-animal-detail', args=[post.id]),
			{'title': 'Unauthorized update'},
			format='json',
		)

		self.assertEqual(response.status_code, 403)
		post.refresh_from_db()
		self.assertEqual(post.title, 'Existing animal')

	def test_owner_can_update_own_post(self):
		post = LiveAnimalPost.objects.create(
			account=self.account,
			species=self.species,
			title='Existing animal',
			description='Existing animal',
			contact_info='{}',
		)

		response = self.client.patch(
			reverse('live-animal-detail', args=[post.id]),
			{'title': 'Updated title'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		post.refresh_from_db()
		self.assertEqual(post.title, 'Updated title')

	def test_owner_can_delete_own_post(self):
		post = LiveAnimalPost.objects.create(
			account=self.account,
			species=self.species,
			title='Existing animal',
			description='Existing animal',
			contact_info='{}',
		)

		response = self.client.delete(reverse('live-animal-detail', args=[post.id]))

		self.assertEqual(response.status_code, 204)
		self.assertFalse(LiveAnimalPost.objects.filter(id=post.id).exists())

	def test_non_owner_cannot_delete_post(self):
		post = LiveAnimalPost.objects.create(
			account=self.account,
			species=self.species,
			title='Existing animal',
			description='Existing animal',
			contact_info='{}',
		)
		other_account = Account.objects.create_user(
			username='other-seller-2',
			email='other2@example.com',
			password='pass1234',
		)
		self.client.force_authenticate(other_account)

		response = self.client.delete(reverse('live-animal-detail', args=[post.id]))

		self.assertEqual(response.status_code, 403)
		self.assertTrue(LiveAnimalPost.objects.filter(id=post.id).exists())


class MyListingsTests(APITestCase):
	def setUp(self):
		self.account = Account.objects.create_user(
			username='seller',
			email='seller@example.com',
			password='pass1234',
		)
		self.other_account = Account.objects.create_user(
			username='other-seller',
			email='other@example.com',
			password='pass1234',
		)
		self.species = Species.objects.create(name='Ball Pythons')
		LiveAnimalPost.objects.create(
			account=self.account, species=self.species, title='Mine', description='d', contact_info='{}',
		)
		LiveAnimalPost.objects.create(
			account=self.other_account, species=self.species, title='Not mine', description='d', contact_info='{}',
		)
		EquipmentPost.objects.create(
			account=self.account, title='My tank', description='d', contact_info='{}',
		)

	def test_anonymous_user_cannot_list_own_listings(self):
		response = self.client.get(reverse('live-animal-mine'))
		self.assertEqual(response.status_code, 401)

	def test_mine_returns_only_own_live_animal_listings(self):
		self.client.force_authenticate(self.account)
		response = self.client.get(reverse('live-animal-mine'))

		self.assertEqual(response.status_code, 200)
		results = response.data.get('results', response.data)
		self.assertEqual([item['title'] for item in results], ['Mine'])

	def test_mine_returns_only_own_equipment_listings(self):
		self.client.force_authenticate(self.account)
		response = self.client.get(reverse('equipment-mine'))

		self.assertEqual(response.status_code, 200)
		results = response.data.get('results', response.data)
		self.assertEqual([item['title'] for item in results], ['My tank'])


class ContactAndReportTests(APITestCase):
	def setUp(self):
		self.seller = Account.objects.create_user(
			username='seller',
			email='seller@example.com',
			password='pass1234',
		)
		self.buyer = Account.objects.create_user(
			username='buyer',
			email='buyer@example.com',
			password='pass1234',
		)
		self.species = Species.objects.create(name='Ball Pythons')
		self.post = LiveAnimalPost.objects.create(
			account=self.seller,
			species=self.species,
			title='Friendly Ball Python',
			description='Healthy animal',
			contact_info='{"phone": "0912345678", "email": "seller@example.com"}',
		)

	def test_equipment_contact_and_report_work_like_live_animals(self):
		gear = EquipmentPost.objects.create(account=self.seller, title='Heat Mat', description='d', contact_info='{}')
		self.client.force_authenticate(self.buyer)
		self.assertEqual(self.client.get(reverse('equipment-contact', args=[gear.id])).status_code, 200)
		self.assertIn(self.client.post(reverse('equipment-contact', args=[gear.id])).status_code, (200, 201))
		self.assertTrue(ContactRequest.objects.filter(requester=self.buyer, equipment_post=gear).exists())
		self.assertIn(self.client.post(reverse('equipment-report', args=[gear.id])).status_code, (200, 201))
		self.assertTrue(Report.objects.filter(reporter=self.buyer, equipment_post=gear).exists())

	def test_anonymous_user_cannot_request_contact(self):
		response = self.client.post(reverse('live-animal-contact', args=[self.post.id]))
		self.assertEqual(response.status_code, 401)

	def test_seller_cannot_request_contact_for_own_listing(self):
		self.client.force_authenticate(self.seller)
		response = self.client.post(reverse('live-animal-contact', args=[self.post.id]))
		self.assertEqual(response.status_code, 400)
		self.assertEqual(self.client.get(reverse('live-animal-contact', args=[self.post.id])).status_code, 400)

	def test_contact_preview_shows_the_buyers_own_details(self):
		self.buyer.phone_number = '0987654321'
		self.buyer.line_id = 'buyerline'
		self.buyer.save()
		self.client.force_authenticate(self.buyer)
		response = self.client.get(reverse('live-animal-contact', args=[self.post.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['contact']['phone'], '0987654321')
		self.assertEqual(response.data['contact']['line'], 'buyerline')
		self.assertFalse(response.data['already_sent'])
		self.assertEqual(len(mail.outbox), 0)

	def test_contact_sends_the_buyers_details_and_never_reveals_the_sellers(self):
		self.buyer.phone_number = '0987654321'
		self.buyer.save()
		self.client.force_authenticate(self.buyer)
		response = self.client.post(reverse('live-animal-contact', args=[self.post.id]))

		self.assertEqual(response.status_code, 200)
		self.assertNotIn('0912345678', str(response.data))
		self.assertNotIn('contact_info', response.data)
		self.assertEqual(response.data['contact']['phone'], '0987654321')
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].to, ['seller@example.com'])
		self.assertIn('0987654321', mail.outbox[0].body)
		self.assertIn('buyer@example.com', mail.outbox[0].body)
		self.assertEqual(ContactRequest.objects.filter(requester=self.buyer, live_animal_post=self.post).count(), 1)

	def test_repeated_contact_request_does_not_resend_email(self):
		self.client.force_authenticate(self.buyer)
		self.client.post(reverse('live-animal-contact', args=[self.post.id]))
		response = self.client.post(reverse('live-animal-contact', args=[self.post.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(ContactRequest.objects.filter(requester=self.buyer, live_animal_post=self.post).count(), 1)
		self.assertTrue(self.client.get(reverse('live-animal-contact', args=[self.post.id])).data['already_sent'])

	def test_anonymous_user_cannot_report_listing(self):
		response = self.client.post(reverse('live-animal-report', args=[self.post.id]))
		self.assertEqual(response.status_code, 401)

	def test_seller_cannot_report_own_listing(self):
		self.client.force_authenticate(self.seller)
		response = self.client.post(reverse('live-animal-report', args=[self.post.id]))
		self.assertEqual(response.status_code, 400)

	def test_buyer_can_report_listing(self):
		self.client.force_authenticate(self.buyer)
		response = self.client.post(reverse('live-animal-report', args=[self.post.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Report.objects.filter(reporter=self.buyer, live_animal_post=self.post).count(), 1)

	def test_repeated_report_does_not_create_duplicate(self):
		self.client.force_authenticate(self.buyer)
		self.client.post(reverse('live-animal-report', args=[self.post.id]))
		response = self.client.post(reverse('live-animal-report', args=[self.post.id]))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(Report.objects.filter(reporter=self.buyer, live_animal_post=self.post).count(), 1)


class SeedDemoCommandTests(APITestCase):
	def run_seed(self, *args):
		from io import StringIO
		from django.core.management import call_command
		call_command('seed_demo', *args, stdout=StringIO())

	def demo_accounts(self):
		from post.management.commands.seed_demo import DEMO_EMAIL_DOMAIN
		return Account.objects.filter(email__endswith=f'@{DEMO_EMAIL_DOMAIN}')

	def test_seeded_sellers_respect_post_and_image_limits(self):
		self.run_seed()

		self.assertEqual(self.demo_accounts().count(), 13)
		self.assertGreaterEqual(LiveAnimalPost.objects.count(), 50)
		for account in self.demo_accounts():
			posts = account.liveanimalpost_posts.count() + account.equipmentpost_posts.count()
			self.assertLessEqual(posts, account.max_post_count, account.username)
			for post in account.liveanimalpost_posts.all():
				self.assertTrue(account.can_upload_images(len(post.gallery) + bool(post.image)), post.title)
				self.assertIn(post.location, dict(LiveAnimalPost.Locations.choices))

	def test_seeded_auctions_follow_auction_rules(self):
		from auction.models import Auction, Deposit
		self.run_seed()

		auctions = Auction.objects.all()
		self.assertTrue(auctions.filter(status=Auction.Status.ACTIVE, bids__isnull=False).exists())
		self.assertTrue(auctions.filter(status=Auction.Status.ENDED, winning_bid__isnull=False).exists())
		for auction in auctions:
			self.assertTrue(auction.seller.can_start_auction, auction)
			amounts = [bid.amount for bid in auction.bids.order_by('created_at')]
			self.assertEqual(amounts, sorted(amounts), auction)
			if amounts:
				self.assertGreaterEqual(amounts[0], auction.starting_price)
			for bid in auction.bids.all():
				self.assertNotEqual(bid.bidder_id, auction.seller_id)
				if auction.status == Auction.Status.ACTIVE:
					self.assertEqual(bid.deposit.status, Deposit.Status.HELD, auction)
				elif bid.bidder_id == auction.winning_bid.bidder_id:
					# Held while the winner still owes the rest; applied to the price once they've paid.
					self.assertIn(bid.deposit.status, (Deposit.Status.HELD, Deposit.Status.CAPTURED), auction)
				else:
					self.assertEqual(bid.deposit.status, Deposit.Status.RELEASED, auction)
			if auction.status == Auction.Status.ENDED and auction.winning_bid:
				self.assertEqual(auction.orders.get().buyer, auction.winning_bid.bidder)

	def test_seeded_users_can_log_in_with_demo_password(self):
		from post.management.commands.seed_demo import DEMO_PASSWORD
		self.run_seed()

		response = self.client.post(reverse('jwt-login'), {'username': 'buyer_amy', 'password': DEMO_PASSWORD})

		self.assertEqual(response.status_code, 200)

	def test_reset_recreates_demo_data_without_touching_real_accounts(self):
		real = Account.objects.create_user(username='real-user', email='real@example.com', password='pass12345')
		self.run_seed()
		first_count = LiveAnimalPost.objects.count()

		self.run_seed('--reset')

		self.assertEqual(LiveAnimalPost.objects.count(), first_count)
		self.assertTrue(Account.objects.filter(pk=real.pk).exists())

	def test_delete_removes_only_demo_data(self):
		real = Account.objects.create_user(username='real-user', email='real@example.com', password='pass12345')
		posts_before = LiveAnimalPost.objects.count()  # migration 0006 ships a few sample listings
		self.run_seed()

		self.run_seed('--delete')

		self.assertFalse(self.demo_accounts().exists())
		self.assertEqual(LiveAnimalPost.objects.count(), posts_before)
		self.assertTrue(Account.objects.filter(pk=real.pk).exists())


class LiveAnimalFilterTests(APITestCase):
	def setUp(self):
		from datetime import timedelta
		from django.utils import timezone
		seller = Account.objects.create_user(
			username='filter-seller', email='filter@example.com', password='pass12345',
			account_type=Account.AccountType.COMMERCIAL, is_paid_account=True,
		)
		python = Species.objects.create(name='Filter Pythons')
		gecko = Species.objects.create(name='Filter Geckos')
		LiveAnimalPost.objects.all().delete()  # ignore the sample listings from migration 0006

		def make(title, species, **fields):
			days_old = fields.pop('days_old', 0)
			post = LiveAnimalPost.objects.create(
				account=seller, species=species, title=title, description='d', contact_info='{}', **fields,
			)
			LiveAnimalPost.objects.filter(pk=post.pk).update(created_at=timezone.now() - timedelta(days=days_old, hours=1))
			return post

		self.pied = make('Pied Python', python, sex='1.0', life_stage='adult', location='TPE', price=9000,
			size_cm=120, weight_grams=1500, age_years=4, genetics='Pastel/Pied', diets=['frozenThawed'],
			shipping_methods=['shipping'], days_old=40)
		self.hatchling = make('Normal Python', python, sex='unsexed', life_stage='hatchling', location='KHH', price=1500,
			size_cm=40, weight_grams=90, age_years=0.2, diets=['live'], shipping_methods=['localPickup'], days_old=2)
		self.gecko = make('Lilly White Gecko', gecko, sex='0.1', life_stage='juvenile', location='TPE', price=6000,
			size_cm=12, weight_grams=10, age_years=0.5, genetics='Lilly White', diets=['pellets', 'live'],
			shipping_methods=['localPickup', 'shipping'], days_old=10)

	def titles(self, **params):
		response = self.client.get(reverse('live-animal-list'), params)
		self.assertEqual(response.status_code, 200)
		return sorted(item['title'] for item in response.data['results'])

	def test_multi_value_and_exclude_filters(self):
		self.assertEqual(self.titles(sex='1.0,unsexed'), ['Normal Python', 'Pied Python'])
		self.assertEqual(self.titles(life_stage='juvenile,hatchling'), ['Lilly White Gecko', 'Normal Python'])
		self.assertEqual(self.titles(life_stage_exclude='adult'), ['Lilly White Gecko', 'Normal Python'])
		self.assertEqual(self.titles(location='TPE'), ['Lilly White Gecko', 'Pied Python'])
		self.assertEqual(self.titles(location_exclude='TPE'), ['Normal Python'])

	def test_range_filters(self):
		self.assertEqual(self.titles(price_min=2000, price_max=8000), ['Lilly White Gecko'])
		self.assertEqual(self.titles(size_min=100), ['Pied Python'])
		self.assertEqual(self.titles(weight_max=100), ['Lilly White Gecko', 'Normal Python'])
		self.assertEqual(self.titles(age_min=0.3, age_max=1), ['Lilly White Gecko'])

	def test_posted_days_matches_posted_days_field(self):
		self.assertEqual(self.titles(posted_days_max=2), ['Normal Python'])
		self.assertEqual(self.titles(posted_days_min=10), ['Lilly White Gecko', 'Pied Python'])
		self.assertEqual(self.titles(posted_days_min=3, posted_days_max=39), ['Lilly White Gecko'])

	def test_json_list_filters(self):
		self.assertEqual(self.titles(diets='live'), ['Lilly White Gecko', 'Normal Python'])
		self.assertEqual(self.titles(diets='pellets,frozenThawed'), ['Lilly White Gecko', 'Pied Python'])
		self.assertEqual(self.titles(diets_exclude='live'), ['Pied Python'])
		self.assertEqual(self.titles(shipping='shipping'), ['Lilly White Gecko', 'Pied Python'])
		self.assertEqual(self.titles(shipping_exclude='shipping'), ['Normal Python'])

	def test_search_species_and_genes(self):
		self.assertEqual(self.titles(search='geckos'), ['Lilly White Gecko'])
		self.assertEqual(self.titles(search='pied'), ['Pied Python'])
		self.assertEqual(self.titles(species_name='filter pythons'), ['Normal Python', 'Pied Python'])
		self.assertEqual(self.titles(genes='Pastel,Pied'), ['Pied Python'])
		self.assertEqual(self.titles(genes='Pastel,Lilly White'), [])

	def test_results_are_paginated_with_total_count(self):
		response = self.client.get(reverse('live-animal-list'), {'location': 'TPE'})
		self.assertEqual(response.data['count'], 2)
		self.assertIsNone(response.data['next'])


class EquipmentFilterTests(APITestCase):
	def setUp(self):
		from datetime import timedelta
		from django.utils import timezone
		seller = Account.objects.create_user(
			username='gear-seller', email='gear@example.com', password='pass12345',
			account_type=Account.AccountType.COMMERCIAL, is_paid_account=True,
		)

		def make(title, **fields):
			days_old = fields.pop('days_old', 0)
			post = EquipmentPost.objects.create(account=seller, title=title, description='d', contact_info='{}', **fields)
			EquipmentPost.objects.filter(pk=post.pk).update(created_at=timezone.now() - timedelta(days=days_old, hours=1))
			return post

		make('Glass Terrarium', category='enclosure', condition=2, location='TPE', price=4000,
			shipping_methods=['localPickup'], days_old=20)
		make('UVB Kit', category='lighting', condition=1, location='KHH', price=2500,
			shipping_methods=['localPickup', 'shipping'], days_old=1)
		make('Broken Heat Mat', category='heating', condition=0, location='TPE', price=100,
			shipping_methods=['shipping'], days_old=5)

	def titles(self, **params):
		response = self.client.get(reverse('equipment-list'), params)
		self.assertEqual(response.status_code, 200)
		return sorted(item['title'] for item in response.data['results'])

	def test_category_and_condition_filters(self):
		self.assertEqual(self.titles(category='enclosure,lighting'), ['Glass Terrarium', 'UVB Kit'])
		self.assertEqual(self.titles(category_exclude='enclosure'), ['Broken Heat Mat', 'UVB Kit'])
		self.assertEqual(self.titles(condition='1,2'), ['Glass Terrarium', 'UVB Kit'])

	def test_shared_listing_filters(self):
		self.assertEqual(self.titles(price_min=1000, price_max=3000), ['UVB Kit'])
		self.assertEqual(self.titles(location_exclude='TPE'), ['UVB Kit'])
		self.assertEqual(self.titles(shipping='shipping'), ['Broken Heat Mat', 'UVB Kit'])
		self.assertEqual(self.titles(posted_days_min=3), ['Broken Heat Mat', 'Glass Terrarium'])
		self.assertEqual(self.titles(search='terrarium'), ['Glass Terrarium'])

	def test_unknown_category_is_rejected_on_create(self):
		seller = Account.objects.get(username='gear-seller')
		self.client.force_authenticate(seller)
		response = self.client.post(reverse('equipment-list'), {
			'title': 'Mystery', 'description': 'd', 'contact_info': '{}', 'category': 'spaceship',
		}, format='json')
		self.assertEqual(response.status_code, 400)
		self.assertIn('category', response.data)

	def test_equipment_accepts_contact_info_object_like_the_editor_sends(self):
		seller = Account.objects.get(username='gear-seller')
		self.client.force_authenticate(seller)
		response = self.client.post(reverse('equipment-list'), {
			'title': 'Heat Lamp', 'description': 'd', 'contact_info': {}, 'category': 'heating',
		}, format='json')
		self.assertEqual(response.status_code, 201, response.data)

	def test_detail_has_public_seller_fields_but_no_contact_details(self):
		post = EquipmentPost.objects.get(title='UVB Kit')
		data = self.client.get(reverse('equipment-detail', args=[post.id])).data
		self.assertEqual(data['seller_name'], post.account.get_display_name())
		self.assertEqual(data['posted_days'], 1)
		self.assertIn('seller_rating', data)
		self.assertNotIn('contact_info', data)
		self.assertNotIn('email', data['seller'])

	def test_category_is_saved_and_returned(self):
		seller = Account.objects.get(username='gear-seller')
		self.client.force_authenticate(seller)
		response = self.client.post(reverse('equipment-list'), {
			'title': 'Carrier', 'description': 'd', 'contact_info': '{}', 'category': 'transport', 'condition': 2,
		}, format='json')
		self.assertEqual(response.status_code, 201, response.data)
		self.assertEqual(response.data['category'], 'transport')
		self.assertEqual(EquipmentPost.objects.get(pk=response.data['id']).category, 'transport')


class SellerInquiryEmailTests(APITestCase):
	def test_inquiry_email_is_sent_in_every_supported_language(self):
		seller = Account.objects.create_user(username='email-seller', email='seller@example.com', password='pass12345')
		buyer = Account.objects.create_user(username='email-buyer', email='buyer@example.com', password='pass12345')
		species = Species.objects.create(name='Email Species')
		post = LiveAnimalPost.objects.create(account=seller, species=species, title='Pied', description='d', contact_info='{}')
		self.client.force_authenticate(buyer)

		# The buyer's UI language must not decide the seller's email language.
		self.client.post(reverse('live-animal-contact', args=[post.id]), HTTP_ACCEPT_LANGUAGE='zh-Hant')

		self.assertEqual(len(mail.outbox), 1)
		email = mail.outbox[0]
		self.assertIn('New inquiry about your listing: Pied', email.subject)
		self.assertIn('你的刊登有新的詢問：Pied', email.subject)
		self.assertIn('is interested in your listing "Pied"', email.body)
		self.assertIn('對你在爬蟲市集上的刊登「Pied」有興趣', email.body)


class ContactPrivacyTests(APITestCase):
	def setUp(self):
		self.seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass1234')
		self.buyer = Account.objects.create_user(username='buyer', email='buyer@example.com', password='pass1234')
		species = Species.objects.create(name='Ball Pythons')
		self.post = LiveAnimalPost.objects.create(
			account=self.seller, species=species, title='Python', description='d',
			contact_info='{"phone": "0912345678"}',
		)
		EquipmentPost.objects.create(account=self.seller, title='Tank', description='d', contact_info='0912345678')

	def assert_no_contact_details(self, listing):
		self.assertNotIn('contact_info', listing)
		self.assertNotIn('email', listing['seller'])

	def test_anonymous_listing_responses_hide_contact_details(self):
		self.assert_no_contact_details(self.client.get(reverse('live-animal-list')).data['results'][0])
		self.assert_no_contact_details(self.client.get(reverse('live-animal-detail', args=[self.post.id])).data)
		self.assert_no_contact_details(self.client.get(reverse('equipment-list')).data['results'][0])

	def test_other_users_do_not_see_contact_details(self):
		self.client.force_authenticate(self.buyer)
		self.assert_no_contact_details(self.client.get(reverse('live-animal-detail', args=[self.post.id])).data)

	def test_owner_sees_own_contact_details(self):
		self.client.force_authenticate(self.seller)
		response = self.client.get(reverse('live-animal-detail', args=[self.post.id]))
		self.assertEqual(response.data['contact_info'], {'phone': '0912345678'})


def make_image(name='photo.png', size=(10, 10)):
	buffer = io.BytesIO()
	Image.new('RGB', size, 'green').save(buffer, format='PNG')
	return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


class ListingPhotoUploadTests(APITestCase):
	def setUp(self):
		self.media_root = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
		override = override_settings(MEDIA_ROOT=self.media_root)
		override.enable()
		self.addCleanup(override.disable)

		self.seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass1234')
		self.other = Account.objects.create_user(username='other', email='other@example.com', password='pass1234')
		self.post = LiveAnimalPost.objects.create(
			account=self.seller, species=Species.objects.create(name='Ball Pythons'),
			title='Python', description='d', contact_info='{}',
			image='https://example.com/seeded.jpg', gallery=['https://example.com/seeded.jpg'],
		)
		self.url = reverse('live-animal-photos', args=[self.post.id])

	def upload(self, photos, cover_index=0):
		return self.client.post(self.url, {'photos': photos, 'cover_index': cover_index}, format='multipart')

	def stored_files(self):
		return [path for path in Path(self.media_root).rglob('*') if path.is_file()]

	def test_owner_uploads_photos_and_chosen_cover_comes_first(self):
		self.client.force_authenticate(self.seller)
		response = self.upload([make_image('a.png'), make_image('b.png')], cover_index=1)

		self.assertEqual(response.status_code, 200)
		self.post.refresh_from_db()
		self.assertEqual(len(self.post.gallery), 2)
		self.assertEqual(self.post.image, self.post.gallery[0])
		self.assertTrue(self.post.image.startswith('http://testserver/media/listings/liveanimalpost/'))
		self.assertEqual(len(self.stored_files()), 2)

	def test_reupload_replaces_and_deletes_previous_uploads(self):
		self.client.force_authenticate(self.seller)
		self.upload([make_image('a.png'), make_image('b.png')])
		self.upload([make_image('c.png')])

		self.post.refresh_from_db()
		self.assertEqual(len(self.post.gallery), 1)
		self.assertEqual(len(self.stored_files()), 1)

	def test_equipment_listing_accepts_photos(self):
		tank = EquipmentPost.objects.create(account=self.seller, title='Tank', description='d', contact_info='')
		self.client.force_authenticate(self.seller)
		response = self.client.post(
			reverse('equipment-photos', args=[tank.id]), {'photos': [make_image()]}, format='multipart',
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(response.data['gallery']), 1)

	def test_non_owner_cannot_upload(self):
		self.client.force_authenticate(self.other)
		self.assertEqual(self.upload([make_image()]).status_code, 403)
		self.assertEqual(self.stored_files(), [])

	def test_anonymous_cannot_upload(self):
		self.assertEqual(self.upload([make_image()]).status_code, 401)

	def test_hobbyist_photo_limit_is_enforced(self):
		self.client.force_authenticate(self.seller)
		response = self.upload([make_image(f'{index}.png') for index in range(4)])

		self.assertEqual(response.status_code, 400)
		self.assertIn('Image limit exceeded', str(response.data))
		self.assertEqual(self.stored_files(), [])

	def test_non_image_file_is_rejected(self):
		self.client.force_authenticate(self.seller)
		response = self.upload([SimpleUploadedFile('notes.png', b'not an image', content_type='image/png')])
		self.assertEqual(response.status_code, 400)

	def test_out_of_range_cover_index_is_rejected(self):
		self.client.force_authenticate(self.seller)
		self.assertEqual(self.upload([make_image()], cover_index=3).status_code, 400)

	def test_three_photos_with_cover_in_gallery_fit_hobbyist_limit(self):
		self.client.force_authenticate(self.seller)
		self.assertEqual(self.upload([make_image(f'{index}.png') for index in range(3)]).status_code, 200)

	# --- `order`: keep, reorder and remove existing photos without re-uploading them -------------

	def set_order(self, order, photos=(), listing_url=None):
		return self.client.post(listing_url or self.url, {'photos': list(photos), 'order': json.dumps(order)}, format='multipart')

	def upload_three(self):
		self.client.force_authenticate(self.seller)
		self.upload([make_image(f'{name}.png') for name in 'abc'])
		self.post.refresh_from_db()
		return list(self.post.gallery)

	def test_order_reorders_and_removes_existing_photos(self):
		first, second, third = self.upload_three()
		response = self.set_order([third, first])

		self.assertEqual(response.status_code, 200, response.data)
		self.post.refresh_from_db()
		self.assertEqual(self.post.gallery, [third, first])
		self.assertEqual(self.post.image, third)
		self.assertEqual(len(self.stored_files()), 2)  # the removed upload is deleted from storage

	def test_order_mixes_kept_and_new_photos(self):
		first, _, _ = self.upload_three()
		response = self.set_order(['new:0', first], photos=[make_image('d.png')])

		self.assertEqual(response.status_code, 200, response.data)
		self.post.refresh_from_db()
		self.assertEqual(len(self.post.gallery), 2)
		self.assertEqual(self.post.gallery[1], first)
		self.assertNotIn(self.post.gallery[0], [first])
		self.assertEqual(len(self.stored_files()), 2)

	def test_order_keeps_seeded_external_photos(self):
		self.client.force_authenticate(self.seller)
		response = self.set_order(['new:0', 'https://example.com/seeded.jpg'], photos=[make_image()])

		self.assertEqual(response.status_code, 200, response.data)
		self.post.refresh_from_db()
		self.assertEqual(self.post.gallery[1], 'https://example.com/seeded.jpg')

	def test_order_cannot_point_the_listing_at_someone_elses_url(self):
		before = self.upload_three()
		response = self.set_order(['https://evil.example.com/x.jpg'])

		self.assertEqual(response.status_code, 400)
		self.assertIn('order', response.data)
		self.post.refresh_from_db()
		self.assertEqual(self.post.gallery, before)

	def test_order_must_use_each_upload_and_photo_exactly_once(self):
		first, _, _ = self.upload_three()
		self.assertEqual(self.set_order(['new:0'], photos=[make_image('d.png'), make_image('e.png')]).status_code, 400)
		self.assertEqual(self.set_order(['new:1'], photos=[make_image('d.png')]).status_code, 400)
		self.assertEqual(self.set_order([first, first]).status_code, 400)
		self.assertEqual(self.set_order(['new:x'], photos=[make_image('d.png')]).status_code, 400)
		self.assertEqual(len(self.stored_files()), 3)  # nothing new was stored

	def test_order_total_counts_toward_the_photo_limit(self):
		kept = self.upload_three()
		response = self.set_order([*kept, 'new:0'], photos=[make_image('d.png')])

		self.assertEqual(response.status_code, 400)
		self.assertIn('Image limit exceeded', str(response.data))

	def test_empty_order_removes_every_photo(self):
		self.upload_three()
		response = self.set_order([])

		self.assertEqual(response.status_code, 200, response.data)
		self.post.refresh_from_db()
		self.assertEqual((self.post.image, self.post.gallery), ('', []))
		self.assertEqual(self.stored_files(), [])

	def test_order_must_be_a_json_list(self):
		self.client.force_authenticate(self.seller)
		response = self.client.post(self.url, {'order': 'not json'}, format='multipart')
		self.assertEqual(response.status_code, 400)

	def test_non_owner_cannot_reorder(self):
		kept = self.upload_three()
		self.client.force_authenticate(self.other)
		self.assertEqual(self.set_order(list(reversed(kept))).status_code, 403)

class ReportModerationTests(APITestCase):
	def setUp(self):
		self.seller = Account.objects.create_user(username='mod-seller', email='seller@example.com', password='pass1234')
		self.reporters = [
			Account.objects.create_user(username=f'reporter{index}', email=f'r{index}@example.com', password='pass1234')
			for index in range(3)
		]
		self.staff = Account.objects.create_superuser(username='staff', email='staff@example.com', password='pass1234')
		LiveAnimalPost.objects.all().delete()  # ignore the sample listings from migration 0006
		self.post = LiveAnimalPost.objects.create(
			account=self.seller, species=Species.objects.create(name='Mod Pythons'),
			title='Suspicious Python', description='d', contact_info='{}',
		)
		self.detail_url = reverse('live-animal-detail', args=[self.post.id])

	def report(self, user):
		self.client.force_authenticate(user)
		return self.client.post(reverse('live-animal-report', args=[self.post.id]))

	def listed_titles(self):
		return [item['title'] for item in self.client.get(reverse('live-animal-list')).data['results']]

	def test_hidden_listing_is_only_visible_to_its_owner_and_staff(self):
		LiveAnimalPost.objects.filter(pk=self.post.pk).update(is_hidden=True)
		self.assertEqual(self.listed_titles(), [])  # anonymous
		self.assertEqual(self.client.get(self.detail_url).status_code, 404)
		self.client.force_authenticate(self.reporters[0])
		self.assertEqual(self.client.get(self.detail_url).status_code, 404)
		self.client.force_authenticate(self.seller)
		self.assertTrue(self.client.get(self.detail_url).data['is_hidden'])
		self.assertEqual(self.client.get(reverse('live-animal-mine')).data['count'], 1)
		self.client.force_authenticate(self.staff)
		self.assertEqual(self.client.get(self.detail_url).status_code, 200)

	def test_reports_only_queue_for_review_by_default(self):
		for reporter in self.reporters:
			self.report(reporter)
		self.post.refresh_from_db()
		self.assertFalse(self.post.is_hidden)
		self.assertEqual(Report.objects.filter(status=Report.Status.PENDING).count(), 3)

	@override_settings(REPORT_AUTO_HIDE_THRESHOLD=2, ADMINS=[('Staff', 'staff@example.com')])
	def test_listing_hides_itself_after_enough_different_reporters(self):
		with self.captureOnCommitCallbacks(execute=True):
			self.report(self.reporters[0])
			self.report(self.reporters[0])  # the same account twice still counts once
		self.post.refresh_from_db()
		self.assertFalse(self.post.is_hidden)

		with self.captureOnCommitCallbacks(execute=True):
			self.report(self.reporters[1])
		self.post.refresh_from_db()
		self.assertTrue(self.post.is_hidden)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('Suspicious Python', mail.outbox[0].subject)

	def admin_action(self, action, reports):
		self.client.force_login(self.staff)
		return self.client.post(reverse('admin:post_report_changelist'), {
			'action': action, '_selected_action': [report.pk for report in reports],
		})

	def test_staff_can_hide_and_resolve_or_dismiss_from_the_admin(self):
		self.report(self.reporters[0])
		self.report(self.reporters[1])
		reports = list(Report.objects.all())

		self.assertEqual(self.admin_action('hide_and_resolve', reports[:1]).status_code, 302)
		self.post.refresh_from_db()
		self.assertTrue(self.post.is_hidden)
		resolved = Report.objects.get(pk=reports[0].pk)
		self.assertEqual((resolved.status, resolved.reviewed_by), (Report.Status.RESOLVED, self.staff))
		self.assertIsNotNone(resolved.reviewed_at)

		self.admin_action('dismiss', reports[1:])
		self.post.refresh_from_db()
		self.assertFalse(self.post.is_hidden)
		self.assertEqual(Report.objects.get(pk=reports[1].pk).status, Report.Status.DISMISSED)
		self.assertEqual(Report.objects.get(pk=reports[0].pk).status, Report.Status.RESOLVED)  # closed reports stay closed

	def test_admin_lists_listings_with_their_pending_reports(self):
		self.report(self.reporters[0])
		self.client.force_login(self.staff)
		response = self.client.get(reverse('admin:post_liveanimalpost_changelist'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Suspicious Python')


class SavedSearchTests(APITestCase):
	def setUp(self):
		from datetime import timedelta
		from django.utils import timezone
		self.timedelta, self.timezone = timedelta, timezone
		self.user = Account.objects.create_user(username='searcher', email='searcher@example.com', password='pass1234')
		self.seller = Account.objects.create_user(username='breeder', email='breeder@example.com', password='pass1234')
		self.pythons = Species.objects.create(name='Search Pythons')
		self.geckos = Species.objects.create(name='Search Geckos')
		LiveAnimalPost.objects.all().delete()  # ignore the sample listings from migration 0006
		self.url = reverse('saved-search-list')

	def save(self, query, **fields):
		self.client.force_authenticate(self.user)
		return self.client.post(self.url, {'query': query, **fields}, format='json')

	def listing(self, title, species, account=None, **fields):
		return LiveAnimalPost.objects.create(
			account=account or self.seller, species=species, title=title, description='d', contact_info='{}', **fields,
		)

	def test_saving_needs_an_account(self):
		self.assertEqual(self.client.post(self.url, {'query': 'search=pied'}, format='json').status_code, 401)

	def test_query_is_checked_and_stored_in_a_stable_form(self):
		response = self.save('sex=1.0&search=pied&page=3&price_max=9000')
		self.assertEqual(response.status_code, 201, response.data)
		self.assertEqual(response.data['query'], 'price_max=9000&search=pied&sex=1.0')  # sorted, page dropped
		self.assertEqual(response.data['name'], 'pied')  # defaults to the search text

	def test_unknown_or_invalid_filters_are_rejected(self):
		self.assertEqual(self.save('colour=red').status_code, 400)
		self.assertEqual(self.save('price_min=cheap').status_code, 400)

	@override_settings(SAVED_SEARCH_LIMIT=2)
	def test_saved_searches_are_capped_per_account(self):
		self.save('search=a')
		self.save('search=b')
		response = self.save('search=c')
		self.assertEqual(response.status_code, 400)
		self.assertIn('2', str(response.data))

	def test_users_only_see_and_delete_their_own(self):
		saved = self.save('search=pied', name='Pied males').data
		self.client.force_authenticate(self.seller)
		self.assertEqual(self.client.get(self.url).data['count'], 0)
		self.assertEqual(self.client.delete(reverse('saved-search-detail', args=[saved['id']])).status_code, 404)
		self.client.force_authenticate(self.user)
		self.assertEqual(self.client.delete(reverse('saved-search-detail', args=[saved['id']])).status_code, 204)

	@override_settings(FRONTEND_URL='https://reptiles.example')
	def test_alerts_email_only_new_matches_once(self):
		self.listing('Old Pied Python', self.pythons)  # posted before the search was saved
		saved = SavedSearch.objects.get(pk=self.save('search=pied&species_name=search pythons').data['id'])
		SavedSearch.objects.filter(pk=saved.pk).update(last_alerted_at=self.timezone.now() - self.timedelta(seconds=1))
		LiveAnimalPost.objects.filter(title='Old Pied Python').update(created_at=self.timezone.now() - self.timedelta(days=1))

		match = self.listing('New Pied Python', self.pythons, price=8000)
		self.listing('New Pied Gecko', self.geckos)  # wrong species
		self.listing('New Normal Python', self.pythons)  # no "pied"
		self.listing('My Own Pied Python', self.pythons, account=self.user)  # the user's own

		from django.core.management import call_command
		call_command('send_search_alerts', stdout=io.StringIO())
		self.assertEqual(len(mail.outbox), 1)
		body = mail.outbox[0].body
		self.assertEqual(mail.outbox[0].to, ['searcher@example.com'])
		self.assertIn('New Pied Python', body)
		self.assertIn(f'https://reptiles.example/posts/{match.id}', body)
		for other in ('Old Pied Python', 'New Pied Gecko', 'New Normal Python', 'My Own Pied Python'):
			self.assertNotIn(other, body)

		call_command('send_search_alerts', stdout=io.StringIO())
		self.assertEqual(len(mail.outbox), 1)  # nothing new since the last alert

	def test_alerts_leave_out_hidden_listings(self):
		saved = SavedSearch.objects.get(pk=self.save('search=pied').data['id'])
		SavedSearch.objects.filter(pk=saved.pk).update(last_alerted_at=self.timezone.now() - self.timedelta(seconds=1))
		self.listing('Hidden Pied Python', self.pythons, is_hidden=True)

		from django.core.management import call_command
		call_command('send_search_alerts', stdout=io.StringIO())
		self.assertEqual(mail.outbox, [])
