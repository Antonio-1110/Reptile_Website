from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Account


class AccountTypeBehaviorTests(TestCase):
    def test_hobbyist_has_no_rating_requirements(self):
        account = Account.objects.create_user(
            username='hobbyist',
            email='hobbyist@example.com',
            password='pass1234',
            account_type=Account.AccountType.HOBBYIST,
        )

        self.assertFalse(account.is_commercial)
        self.assertFalse(account.requires_rating)
        self.assertTrue(account.can_upload_images(3))
        self.assertTrue(account.can_create_post())

    def test_commercial_accounts_require_rating_and_more_limits(self):
        account = Account.objects.create_user(
            username='dealer',
            email='dealer@example.com',
            password='pass1234',
            account_type=Account.AccountType.COMMERCIAL,
            seller_rating=4.8,
            total_reviews=20,
            is_paid_account=True,
        )

        self.assertTrue(account.is_commercial)
        self.assertTrue(account.requires_rating)
        self.assertTrue(account.can_upload_images(10))
        self.assertTrue(account.can_create_post())


class ProfileQuotaTests(APITestCase):
    def test_profile_includes_post_usage_and_remaining_quota(self):
        account = Account.objects.create_user(
            username='profile-seller',
            email='profile@example.com',
            password='pass1234',
        )
        self.client.force_authenticate(account)

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['post_count'], 0)
        self.assertEqual(response.data['remaining_post_count'], 5)


class ProfileUpdateTests(APITestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            username='settings-user',
            email='settings@example.com',
            password='pass1234',
        )
        self.client.force_authenticate(self.account)

    def test_user_can_update_editable_profile_fields(self):
        response = self.client.patch(reverse('profile'), {
            'first_name': 'Gecko Garden',
            'last_name': '',
            'phone_number': '0912-345-678',
            'line_id': 'geckogarden',
            'contact_email': 'hello@geckogarden.tw',
            'instagram': '@geckogarden',
            'facebook': 'https://facebook.com/geckogarden',
            'bio': 'Leopard gecko breeder in Tainan.',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['display_name'], 'Gecko Garden')
        self.assertEqual(response.data['phone_number'], '0912-345-678')
        self.assertEqual(response.data['line_id'], 'geckogarden')
        self.assertEqual(response.data['contact_email'], 'hello@geckogarden.tw')
        self.assertEqual(response.data['instagram'], '@geckogarden')
        self.assertEqual(response.data['facebook'], 'https://facebook.com/geckogarden')
        self.account.refresh_from_db()
        self.assertEqual(self.account.bio, 'Leopard gecko breeder in Tainan.')

    def test_account_type_paid_status_verification_and_rating_are_read_only(self):
        self.client.patch(reverse('profile'), {
            'account_type': 'commercial',
            'is_paid_account': True,
            'verified_seller': True,
            'seller_rating': 5.0,
        }, format='json')

        self.account.refresh_from_db()
        self.assertFalse(self.account.is_commercial)
        self.assertFalse(self.account.is_paid_account)
        self.assertFalse(self.account.verified_seller)
        self.assertEqual(self.account.seller_rating, 0.0)

    def test_username_must_stay_unique(self):
        Account.objects.create_user(username='taken', email='taken@example.com', password='pass1234')

        response = self.client.patch(reverse('profile'), {'username': 'taken'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_contact_email_must_be_valid(self):
        response = self.client.patch(reverse('profile'), {'contact_email': 'not-an-email'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('contact_email', response.data)

    def test_bio_length_is_limited(self):
        response = self.client.patch(reverse('profile'), {'bio': 'x' * 501}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_profile_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse('profile')).status_code, 401)

    def test_private_contact_fields_stay_out_of_public_listings(self):
        from post.models import LiveAnimalPost, Species

        self.account.phone_number = '0912-345-678'
        self.account.line_id = 'geckogarden'
        self.account.contact_email = 'hello@geckogarden.tw'
        self.account.instagram = '@geckogarden'
        self.account.facebook = 'geckogarden'
        self.account.save()
        LiveAnimalPost.objects.create(
            account=self.account, species=Species.objects.create(name='Leopard Geckos'),
            title='Gecko', description='d', contact_info='{}',
        )
        self.client.force_authenticate(None)

        seller = self.client.get(reverse('live-animal-list')).data['results'][0]['seller']

        for field in ('phone_number', 'line_id', 'email', 'contact_email', 'instagram', 'facebook', 'first_name', 'last_name'):
            self.assertNotIn(field, seller)


class RegistrationTests(APITestCase):
    def test_registration_cannot_self_assign_commercial_type_or_rating(self):
        response = self.client.post(reverse('register'), {
            'username': 'sneaky',
            'email': 'sneaky@example.com',
            'password': 'pass12345',
            'password2': 'pass12345',
            'account_type': 'commercial',
            'seller_rating': 5.0,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        account = Account.objects.get(username='sneaky')
        self.assertFalse(account.is_commercial)
        self.assertEqual(account.seller_rating, 0.0)


class AccountPlansTests(APITestCase):
    def test_plans_are_public_and_match_account_limits(self):
        response = self.client.get(reverse('account-plans'))

        self.assertEqual(response.status_code, 200)
        plans = {plan['id']: plan for plan in response.data}
        self.assertEqual(plans['hobbyist']['max_post_count'], Account(account_type='hobbyist').max_post_count)
        self.assertEqual(
            plans['commercial_paid']['max_images_per_post'],
            Account(account_type='commercial', is_paid_account=True).max_images_per_post,
        )
        self.assertFalse(plans['commercial']['can_start_auction'])
        self.assertTrue(plans['commercial_paid']['can_start_auction'])

