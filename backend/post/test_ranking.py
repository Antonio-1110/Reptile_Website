from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from account.models import Account
from .models import EquipmentPost, LiveAnimalPost, Species


def make_animal(account, species, title, days_old=0, **fields):
	fields = {'description': 'd', **fields}
	post = LiveAnimalPost.objects.create(account=account, species=species, title=title, contact_info='{}', **fields)
	LiveAnimalPost.objects.filter(pk=post.pk).update(created_at=timezone.now() - timedelta(days=days_old))
	return post


def titles(response):
	return [item['title'] for item in response.data['results']]


class RecommendedOrderingTests(APITestCase):
	def setUp(self):
		# Migration 0006 seeds sample listings; these tests order their own.
		LiveAnimalPost.objects.all().delete()
		EquipmentPost.objects.all().delete()
		self.seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass1234')
		self.species = Species.objects.create(name='Ball Pythons')

	def test_a_complete_listing_outranks_a_bare_one_posted_a_little_later(self):
		make_animal(self.seller, self.species, 'Bare', days_old=1)
		make_animal(
			self.seller, self.species, 'Complete', days_old=2,
			image='https://example.com/a.jpg', genetics='Pastel', description='x' * 100,
		)
		response = self.client.get(reverse('live-animal-list'), {'ordering': 'recommended'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(titles(response), ['Complete', 'Bare'])

	def test_age_still_wins_over_a_small_bonus(self):
		make_animal(self.seller, self.species, 'New and bare', days_old=0)
		make_animal(self.seller, self.species, 'Old with photo', days_old=30, image='https://example.com/a.jpg')
		response = self.client.get(reverse('live-animal-list'), {'ordering': 'recommended'})
		self.assertEqual(titles(response), ['New and bare', 'Old with photo'])

	def test_a_well_reviewed_seller_gets_a_boost(self):
		rated = Account.objects.create_user(username='rated', email='rated@example.com', password='pass1234')
		Account.objects.filter(pk=rated.pk).update(seller_rating=4.8, total_reviews=5)
		make_animal(self.seller, self.species, 'Unrated seller', days_old=1)
		make_animal(rated, self.species, 'Rated seller', days_old=2)
		response = self.client.get(reverse('live-animal-list'), {'ordering': 'recommended'})
		self.assertEqual(titles(response), ['Rated seller', 'Unrated seller'])

	def test_recommended_works_for_equipment(self):
		EquipmentPost.objects.create(account=self.seller, title='Tank', description='d', contact_info='{}')
		response = self.client.get(reverse('equipment-list'), {'ordering': 'recommended'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(titles(response), ['Tank'])

	def test_price_ordering_is_available(self):
		make_animal(self.seller, self.species, 'Dear', price=5000)
		make_animal(self.seller, self.species, 'Cheap', price=500)
		response = self.client.get(reverse('live-animal-list'), {'ordering': 'price,-id'})
		self.assertEqual(titles(response), ['Cheap', 'Dear'])

	def test_listings_without_a_price_come_last_either_way(self):
		make_animal(self.seller, self.species, 'No price')
		make_animal(self.seller, self.species, 'Priced', price=500)
		for ordering in ('price,-id', '-price,-id'):
			response = self.client.get(reverse('live-animal-list'), {'ordering': ordering})
			self.assertEqual(titles(response), ['Priced', 'No price'], ordering)


class SimilarListingsTests(APITestCase):
	def setUp(self):
		self.seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass1234')
		self.pythons = Species.objects.create(name='Ball Pythons')
		self.geckos = Species.objects.create(name='Leopard Geckos')
		self.post = make_animal(self.seller, self.pythons, 'Pastel Pied', genetics='Pastel/Pied', price=3000)

	def similar(self, post=None, name='live-animal-similar'):
		return self.client.get(reverse(name, args=[(post or self.post).pk]))

	def test_lists_the_same_species_with_shared_morphs_first(self):
		make_animal(self.seller, self.pythons, 'Plain python', days_old=0)
		make_animal(self.seller, self.pythons, 'Pied python', days_old=5, genetics='Pied')
		make_animal(self.seller, self.geckos, 'Gecko', genetics='Pastel/Pied')
		response = self.similar()
		self.assertEqual(response.status_code, 200)
		self.assertEqual([item['title'] for item in response.data], ['Pied python', 'Plain python'])

	def test_leaves_out_itself_sold_and_hidden_listings(self):
		make_animal(self.seller, self.pythons, 'Sold', status=LiveAnimalPost.Status.SOLD)
		make_animal(self.seller, self.pythons, 'Hidden', is_hidden=True)
		self.assertEqual(self.similar().data, [])

	def test_hidden_listings_stay_out_even_for_staff(self):
		make_animal(self.seller, self.pythons, 'Hidden', is_hidden=True)
		staff = Account.objects.create_user(username='staff', email='staff@example.com', password='pass1234', is_staff=True)
		self.client.force_authenticate(staff)
		self.assertEqual(self.similar().data, [])

	def test_is_capped(self):
		for index in range(10):
			make_animal(self.seller, self.pythons, f'Python {index}')
		self.assertEqual(len(self.similar().data), 6)

	def test_public_responses_hide_contact_details(self):
		make_animal(self.seller, self.pythons, 'Another')
		item = self.similar().data[0]
		self.assertNotIn('contact_info', item)
		self.assertNotIn('email', item['seller'])

	def test_hidden_listing_itself_is_not_found(self):
		hidden = make_animal(self.seller, self.pythons, 'Hidden', is_hidden=True)
		self.assertEqual(self.similar(hidden).status_code, 404)

	def test_equipment_matches_by_type(self):
		tank = EquipmentPost.objects.create(account=self.seller, title='Tank', description='d', contact_info='{}', category='enclosure')
		EquipmentPost.objects.create(account=self.seller, title='Other tank', description='d', contact_info='{}', category='enclosure')
		EquipmentPost.objects.create(account=self.seller, title='Lamp', description='d', contact_info='{}', category='lighting')
		response = self.similar(tank, 'equipment-similar')
		self.assertEqual([item['title'] for item in response.data], ['Other tank'])
