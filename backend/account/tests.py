import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
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
        response = self.client.post(reverse('jwt-register'), {
            'username': 'sneaky',
            'email': 'sneaky@example.com',
            'password': 'S3curePass!23',
            'account_type': 'commercial',
            'is_paid_account': True,
            'verified_seller': True,
            'seller_rating': 5.0,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        account = Account.objects.get(username='sneaky')
        self.assertFalse(account.is_commercial)
        self.assertFalse(account.is_paid_account)
        self.assertFalse(account.verified_seller)
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



class SellerProfileTests(APITestCase):
    def setUp(self):
        from post.models import EquipmentPost, LiveAnimalPost, Species

        self.seller = Account.objects.create_user(
            username='gecko_shop', email='shop@example.com', password='pass1234', first_name='Mei', last_name='Lin',
            phone_number='0911222333', line_id='shopline', bio='Crested geckos since 2015.', verified_seller=True,
        )
        self.buyer = Account.objects.create_user(username='just_buying', email='buyer@example.com', password='pass1234')
        species = Species.objects.create(name='Profile Geckos')
        LiveAnimalPost.objects.all().delete()  # ignore the sample listings from migration 0006
        self.gecko = LiveAnimalPost.objects.create(account=self.seller, species=species, title='Gecko', description='d', contact_info='{}')
        self.other = LiveAnimalPost.objects.create(account=self.buyer, species=species, title='Not theirs', description='d', contact_info='{}')
        LiveAnimalPost.objects.filter(pk=self.other.pk).delete()
        EquipmentPost.objects.create(account=self.seller, title='Tank', description='d', contact_info='')

    def test_seller_profile_is_public_and_has_no_contact_details(self):
        response = self.client.get(reverse('seller-profile', args=[self.seller.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['display_name'], 'Mei Lin')
        self.assertEqual(response.data['bio'], 'Crested geckos since 2015.')
        self.assertTrue(response.data['verified_seller'])
        self.assertEqual((response.data['live_animal_count'], response.data['equipment_count']), (1, 1))
        for private in ('email', 'phone_number', 'line_id', 'contact_email', 'personal_id', 'instagram', 'facebook'):
            self.assertNotIn(private, response.data)
        self.assertNotIn('0911222333', str(response.data))

    def test_accounts_without_listings_have_no_public_profile(self):
        self.assertEqual(self.client.get(reverse('seller-profile', args=[self.buyer.id])).status_code, 404)

    def test_deactivated_sellers_have_no_public_profile(self):
        Account.objects.filter(pk=self.seller.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse('seller-profile', args=[self.seller.id])).status_code, 404)

    def test_listings_can_be_filtered_to_one_seller(self):
        live = self.client.get(reverse('live-animal-list'), {'seller': self.seller.id}).data
        self.assertEqual([item['title'] for item in live['results']], ['Gecko'])
        equipment = self.client.get(reverse('equipment-list'), {'seller': self.seller.id}).data
        self.assertEqual([item['title'] for item in equipment['results']], ['Tank'])
        self.assertEqual(self.client.get(reverse('equipment-list'), {'seller': self.buyer.id}).data['count'], 0)


class SellerReviewTests(APITestCase):
    def setUp(self):
        from post.models import LiveAnimalPost, Species

        self.seller = Account.objects.create_user(username='gecko_shop', email='shop@example.com', password='pass1234')
        self.buyer = Account.objects.create_user(
            username='happy_buyer', email='buyer@example.com', password='pass1234', first_name='Private', last_name='Person',
        )
        self.other = Account.objects.create_user(username='second_buyer', email='other@example.com', password='pass1234')
        self.stranger = Account.objects.create_user(username='stranger', email='stranger@example.com', password='pass1234')
        LiveAnimalPost.objects.all().delete()  # ignore the sample listings from migration 0006
        self.listing = LiveAnimalPost.objects.create(
            account=self.seller, species=Species.objects.create(name='Review Geckos'), title='Gecko', description='d', contact_info='{}',
        )
        self.url = reverse('seller-reviews', args=[self.seller.id])

    def contacted(self, user):
        from post.models import ContactRequest
        ContactRequest.objects.create(requester=user, live_animal_post=self.listing)

    def review(self, user, rating, comment=''):
        self.client.force_authenticate(user)
        return self.client.post(self.url, {'rating': rating, 'comment': comment}, format='json')

    def rating(self):
        self.seller.refresh_from_db()
        return self.seller.seller_rating, self.seller.total_reviews

    def test_only_buyers_who_contacted_the_seller_can_review(self):
        response = self.review(self.stranger, 5)
        self.assertEqual(response.status_code, 403)
        self.assertIn('contacting', response.data['detail'])
        self.contacted(self.buyer)
        self.assertEqual(self.review(self.buyer, 5).status_code, 201)

    def test_sellers_cannot_review_themselves(self):
        self.assertEqual(self.review(self.seller, 5).status_code, 403)

    def test_rating_is_recomputed_on_every_change(self):
        self.contacted(self.buyer)
        self.contacted(self.other)
        self.review(self.buyer, 5, 'Healthy gecko, great packing.')
        self.assertEqual(self.rating(), (5.0, 1))
        self.review(self.other, 2)
        self.assertEqual(self.rating(), (3.5, 2))

        response = self.review(self.buyer, 4, 'Updated')  # a second POST edits the same review
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.rating(), (3.0, 2))

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(self.rating(), (4.0, 1))
        self.assertEqual(self.client.delete(self.url).status_code, 404)

    def test_rating_must_be_one_to_five(self):
        self.contacted(self.buyer)
        self.assertEqual(self.review(self.buyer, 0).status_code, 400)
        self.assertEqual(self.review(self.buyer, 6).status_code, 400)
        self.assertEqual(self.rating(), (0.0, 0))

    def test_reviews_are_public_and_show_only_the_reviewers_username(self):
        self.contacted(self.buyer)
        self.review(self.buyer, 5, 'Great')
        self.client.force_authenticate(None)
        results = self.client.get(self.url).data['results']
        self.assertEqual(results[0]['reviewer'], 'happy_buyer')
        self.assertNotIn('Private', str(results))
        self.assertFalse(results[0]['is_mine'])

    def test_profile_tells_the_viewer_whether_they_can_review(self):
        profile_url = reverse('seller-profile', args=[self.seller.id])
        self.assertFalse(self.client.get(profile_url).data['can_review'])  # anonymous
        self.contacted(self.buyer)
        self.client.force_authenticate(self.buyer)
        self.assertTrue(self.client.get(profile_url).data['can_review'])
        self.review(self.buyer, 4, 'Nice')
        self.assertEqual(self.client.get(profile_url).data['my_review']['rating'], 4)

    def test_auction_buyers_with_a_completed_order_can_review(self):
        from datetime import timedelta
        from decimal import Decimal
        from django.utils import timezone
        from auction.models import Auction, Order

        auction = Auction.objects.create(
            seller=self.seller, live_animal_post=self.listing, starting_price=Decimal('100'), min_increment=Decimal('10'),
            deposit_amount=Decimal('100'), currency='TWD', starts_at=timezone.now() - timedelta(days=2),
            ends_at=timezone.now() - timedelta(days=1), status=Auction.Status.ENDED,
        )
        order = Order.objects.create(
            auction=auction, buyer=self.other, source=Order.Source.BID, status=Order.Status.PAID,
            price=Decimal('100'), currency='TWD',
        )
        self.assertEqual(self.review(self.other, 5).status_code, 403)  # not completed yet
        Order.objects.filter(pk=order.pk).update(status=Order.Status.COMPLETED)
        self.assertEqual(self.review(self.other, 5).status_code, 201)


class PlanWorkflowTests(APITestCase):
    """
    Each plan end to end through the API, as a seller would hit it: how many listings, how many photos
    per listing, whether they may start auctions, and that nobody can switch plans themselves. The
    limits come from the Account model, so this checks every place that enforces them agrees.
    """
    PLANS = {
        # name: (account fields, max posts, max photos, may auction)
        'hobbyist': ({}, 5, 3, False),
        'commercial': ({'account_type': 'commercial'}, 20, 6, False),
        'commercial_paid': ({'account_type': 'commercial', 'is_paid_account': True}, 200, 12, True),
    }

    def setUp(self):
        from post.models import LiveAnimalPost, Species
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.species = Species.objects.create(name='Plan Pythons')
        LiveAnimalPost.objects.all().delete()  # ignore the sample listings from migration 0006

    def photo(self, name):
        buffer = io.BytesIO()
        Image.new('RGB', (4, 4)).save(buffer, format='PNG')
        return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')

    def create_listing(self):
        return self.client.post(reverse('live-animal-list'), {
            'title': 'Plan check', 'description': 'd', 'contact_info': {}, 'species': self.species.id,
        }, format='json')

    def test_each_plan_gets_exactly_its_limits(self):
        from post.models import LiveAnimalPost

        for name, (fields, max_posts, max_photos, may_auction) in self.PLANS.items():
            with self.subTest(plan=name):
                seller = Account.objects.create_user(username=f'{name}_seller', email=f'{name}@example.com', password='pass1234', **fields)
                self.client.force_authenticate(seller)

                profile = self.client.get(reverse('profile')).data
                self.assertEqual((profile['max_post_count'], profile['max_images_per_post']), (max_posts, max_photos))
                self.assertEqual(profile['can_start_auction'], may_auction)

                # Fill the plan up to one below its cap directly, then the last post over the API.
                LiveAnimalPost.objects.bulk_create([
                    LiveAnimalPost(account=seller, species=self.species, title=f'{index}', description='d', contact_info='{}')
                    for index in range(max_posts - 1)
                ])
                last = self.create_listing()
                self.assertEqual(last.status_code, 201, last.data)
                self.assertEqual(self.client.get(reverse('profile')).data['remaining_post_count'], 0)
                over = self.create_listing()
                self.assertEqual(over.status_code, 400)
                self.assertIn(str(max_posts), str(over.data))

                photos_url = reverse('live-animal-photos', args=[last.data['id']])
                too_many = [self.photo(f'{index}.png') for index in range(max_photos + 1)]
                self.assertEqual(self.client.post(photos_url, {'photos': too_many}, format='multipart').status_code, 400)
                just_right = [self.photo(f'{index}.png') for index in range(max_photos)]
                self.assertEqual(self.client.post(photos_url, {'photos': just_right}, format='multipart').status_code, 200)

                auction = self.client.post(reverse('auction-list'), {}, format='json')
                self.assertEqual(auction.status_code, 400 if may_auction else 403)  # 400: past the paywall, then validated

                self.client.patch(reverse('profile'), {'account_type': 'commercial', 'is_paid_account': True}, format='json')
                seller.refresh_from_db()
                self.assertEqual((seller.account_type, seller.is_paid_account), (fields.get('account_type', 'hobbyist'), fields.get('is_paid_account', False)))


class LegacyTokenAuthRetiredTests(APITestCase):
    def test_the_old_token_endpoints_are_gone(self):
        for path in ('/api/auth/register/', '/api/auth/login/', '/api/auth/logout/', '/api/auth/profile/'):
            self.assertEqual(self.client.post(path, {}).status_code, 404, path)

    def test_profile_and_plans_live_under_the_account_endpoints(self):
        self.assertEqual(reverse('profile'), '/api/v1/account/profile/')
        self.assertEqual(reverse('account-plans'), '/api/v1/account/plans/')

    def test_a_jwt_from_login_opens_the_profile(self):
        Account.objects.create_user(username='jwt_user', email='jwt@example.com', password='S3curePass!23')
        tokens = self.client.post(reverse('jwt-login'), {'username': 'jwt_user', 'password': 'S3curePass!23'}).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'jwt_user')
        self.assertIn('remaining_post_count', response.data)
