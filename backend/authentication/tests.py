import re
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

Account = get_user_model()


class RegisterTests(APITestCase):
    def test_register_creates_user_with_hashed_password(self):
        response = self.client.post(reverse('jwt-register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'S3curePass!23',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['username'], 'newuser')
        self.assertNotIn('password', response.data)

        user = Account.objects.get(username='newuser')
        self.assertNotEqual(user.password, 'S3curePass!23')
        self.assertTrue(user.check_password('S3curePass!23'))

    def test_register_enforces_the_password_rules_the_form_lists(self):
        # The sign-up form lists these rules (Frontend/src/constants/passwordRules.js): 8+ characters,
        # with both English letters and numbers.
        for password in ['abc1234', '8675309123', 'onlyletters', '!!!!!!!!']:
            with self.subTest(password=password):
                response = self.client.post(reverse('jwt-register'), {
                    'username': 'newuser99', 'email': 'someone@example.com', 'password': password,
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn('password', response.data)
        self.assertFalse(Account.objects.filter(username='newuser99').exists())

    def test_register_accepts_any_password_with_8_characters_letters_and_numbers(self):
        # No similarity or common-password checks any more (the owner's call).
        for number, password in enumerate(['abcd1234', 'newuser99', 'password1']):
            with self.subTest(password=password):
                response = self.client.post(reverse('jwt-register'), {
                    'username': f'newuser9{number}', 'email': f'user{number}@example.com', 'password': password,
                })
                self.assertEqual(response.status_code, 201, response.data)

    def test_register_rejects_duplicate_username(self):
        Account.objects.create_user(username='taken', email='taken@example.com', password='pass12345')

        response = self.client.post(reverse('jwt-register'), {
            'username': 'taken',
            'email': 'other@example.com',
            'password': 'S3curePass!23',
        })

        self.assertEqual(response.status_code, 400)


    def test_register_rejects_an_email_already_used_in_another_case(self):
        Account.objects.create_user(username='first', email='shared@example.com', password='pass12345')

        response = self.client.post(reverse('jwt-register'), {
            'username': 'second',
            'email': 'Shared@Example.com',
            'password': 'S3curePass!23',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)


class LoginAndTokenTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(reverse('jwt-login'), {'username': 'seller', 'password': 'pass12345'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(reverse('jwt-login'), {'username': 'seller', 'password': 'wrong-password'})
        self.assertEqual(response.status_code, 401)

    def test_login_accepts_the_email_address_in_any_case(self):
        response = self.client.post(reverse('jwt-login'), {'username': 'Seller@Example.com', 'password': 'pass12345'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)

    def test_login_by_email_still_needs_the_right_password(self):
        response = self.client.post(reverse('jwt-login'), {'username': 'seller@example.com', 'password': 'wrong-password'})
        self.assertEqual(response.status_code, 401)

    def test_a_username_that_looks_like_an_email_signs_in_as_itself(self):
        Account.objects.create_user(username='seller@example.com', email='odd@example.com', password='other12345')

        response = self.client.post(reverse('jwt-login'), {'username': 'seller@example.com', 'password': 'other12345'})

        self.assertEqual(response.status_code, 200)

    def test_refresh_returns_new_access_token(self):
        login_response = self.client.post(reverse('jwt-login'), {'username': 'seller', 'password': 'pass12345'})
        refresh_token = login_response.data['refresh']

        response = self.client.post(reverse('jwt-refresh'), {'refresh': refresh_token})

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)


class LogoutAndRotationTests(APITestCase):
    def setUp(self):
        Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')
        self.tokens = self.client.post(reverse('jwt-login'), {'username': 'seller', 'password': 'pass12345'}).data

    def test_logout_retires_the_refresh_token(self):
        response = self.client.post(reverse('jwt-logout'), {'refresh': self.tokens['refresh']})
        self.assertEqual(response.status_code, 200)

        response = self.client.post(reverse('jwt-refresh'), {'refresh': self.tokens['refresh']})
        self.assertEqual(response.status_code, 401)

    def test_logout_rejects_an_invalid_token(self):
        response = self.client.post(reverse('jwt-logout'), {'refresh': 'not-a-token'})
        self.assertEqual(response.status_code, 401)

    def test_refresh_hands_out_a_new_refresh_token_and_retires_the_old_one(self):
        response = self.client.post(reverse('jwt-refresh'), {'refresh': self.tokens['refresh']})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['refresh'], self.tokens['refresh'])

        reused = self.client.post(reverse('jwt-refresh'), {'refresh': self.tokens['refresh']})
        self.assertEqual(reused.status_code, 401)

        rotated = self.client.post(reverse('jwt-refresh'), {'refresh': response.data['refresh']})
        self.assertEqual(rotated.status_code, 200)


class MeEndpointTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            username='seller', email='seller@example.com', password='pass12345', verified_seller=True,
        )

    def test_me_requires_authentication(self):
        # DEBUG is forced to False by Django's test runner, so the dev bypass never applies here.
        response = self.client.get(reverse('jwt-me'))
        self.assertIn(response.status_code, (401, 403))

    def test_me_returns_profile_with_valid_access_token(self):
        login_response = self.client.post(reverse('jwt-login'), {'username': 'seller', 'password': 'pass12345'})
        access_token = login_response.data['access']

        response = self.client.get(reverse('jwt-me'), HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'seller')
        self.assertEqual(response.data['email'], 'seller@example.com')
        self.assertTrue(response.data['verified_seller'])


class DevAuthBypassTests(APITestCase):
    def test_anonymous_request_is_blocked_when_debug_is_false(self):
        response = self.client.get(reverse('jwt-me'))
        self.assertIn(response.status_code, (401, 403))

    @override_settings(DEBUG=True)
    def test_anonymous_request_is_authenticated_as_dev_user_when_debug_is_true(self):
        from common.middleware import DEV_USERNAME

        response = self.client.get(reverse('jwt-me'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], DEV_USERNAME)
        self.assertTrue(Account.objects.filter(username=DEV_USERNAME).exists())

    @override_settings(DEBUG=True)
    def test_anonymous_post_is_not_rejected_by_csrf_when_debug_is_true(self):
        # The bypass user must not be mistaken for a session login, which would enforce CSRF.
        self.client = self.client_class(enforce_csrf_checks=True)

        response = self.client.post(reverse('jwt-register'), {
            'username': 'debuguser',
            'email': 'debuguser@example.com',
            'password': 'S3curePass!23',
        })

        self.assertEqual(response.status_code, 201)

    @override_settings(DEBUG=True)
    def test_valid_jwt_takes_priority_over_dev_bypass(self):
        Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')
        access_token = self.client.post(
            reverse('jwt-login'), {'username': 'seller', 'password': 'pass12345'},
        ).data['access']

        response = self.client.get(reverse('jwt-me'), HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.assertEqual(response.data['username'], 'seller')


class ApiLanguageTests(APITestCase):
    def register(self, **headers):
        Account.objects.create_user(username='taken', email='taken@example.com', password='pass12345')
        return self.client.post(reverse('jwt-register'), {
            'username': 'taken', 'email': 'new@example.com', 'password': '123',
        }, **headers)

    def test_messages_default_to_english(self):
        response = self.register()

        self.assertEqual(response.data['username'], ['A user with that username already exists.'])
        self.assertIn('Your password must contain both English letters and numbers.', response.data['password'])

    def test_messages_follow_accept_language(self):
        response = self.register(HTTP_ACCEPT_LANGUAGE='zh-Hant')

        # Django's built-in model messages and our password rule come back translated.
        self.assertEqual(response.data['username'], ['一個相同名稱的使用者已經存在。'])
        self.assertIn('密碼必須同時包含英文字母和數字。', response.data['password'])
        self.assertEqual(response['Content-Language'], 'zh-hant')

    def test_our_own_messages_are_translated(self):
        from post.models import LiveAnimalPost, Species
        seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')
        post = LiveAnimalPost.objects.create(
            account=seller, species=Species.objects.create(name='S'), title='T', description='d', contact_info='{}',
        )
        self.client.force_authenticate(seller)

        english = self.client.post(reverse('live-animal-report', args=[post.id]))
        chinese = self.client.post(reverse('live-animal-report', args=[post.id]), HTTP_ACCEPT_LANGUAGE='zh-Hant')

        self.assertEqual(english.data['detail'], "You can't report your own listing.")
        self.assertEqual(chinese.data['detail'], '你不能檢舉自己的刊登。')


def link_params(message):
    """The uid and token from the link in an emailed message."""
    query = parse_qs(urlparse(re.search(r'https?://\S+', message.body).group()).query)
    return {'uid': query['uid'][0], 'token': query['token'][0]}


class EmailVerificationTests(APITestCase):
    def register(self):
        return self.client.post(reverse('jwt-register'), {
            'username': 'newuser', 'email': 'newuser@example.com', 'password': 'S3curePass!23',
        })

    def test_registering_emails_a_confirmation_link_and_starts_unverified(self):
        self.assertEqual(self.register().status_code, 201)

        user = Account.objects.get(username='newuser')
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['newuser@example.com'])
        self.assertIn('/verify-email?uid=', mail.outbox[0].body)

    def test_opening_the_link_confirms_the_address(self):
        self.register()

        response = self.client.post(reverse('verify-email'), link_params(mail.outbox[0]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Account.objects.get(username='newuser').email_verified)

    def test_opening_the_link_again_still_reports_success(self):
        self.register()
        params = link_params(mail.outbox[0])
        self.client.post(reverse('verify-email'), params)

        response = self.client.post(reverse('verify-email'), params)

        self.assertEqual(response.status_code, 200)

    def test_a_wrong_token_is_rejected(self):
        self.register()
        params = {**link_params(mail.outbox[0]), 'token': 'abc-123'}

        response = self.client.post(reverse('verify-email'), params)

        self.assertEqual(response.status_code, 400)
        self.assertIn('invalid or has expired', response.data['detail'])
        self.assertFalse(Account.objects.get(username='newuser').email_verified)

    def test_a_link_for_an_old_address_stops_working_when_the_address_changes(self):
        self.register()
        params = link_params(mail.outbox[0])
        Account.objects.filter(username='newuser').update(email='changed@example.com')

        self.assertEqual(self.client.post(reverse('verify-email'), params).status_code, 400)

    def test_signed_in_user_can_ask_for_a_new_link(self):
        self.register()
        user = Account.objects.get(username='newuser')
        self.client.force_authenticate(user)

        response = self.client.post(reverse('verify-email-resend'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_no_new_link_is_sent_once_confirmed(self):
        user = Account.objects.create_user(username='done', email='done@example.com', password='pass12345')
        self.client.force_authenticate(user)

        response = self.client.post(reverse('verify-email-resend'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_me_reports_whether_the_address_is_confirmed(self):
        user = Account.objects.create_user(
            username='fresh', email='fresh@example.com', password='pass12345', email_verified=False,
        )
        self.client.force_authenticate(user)

        self.assertFalse(self.client.get(reverse('jwt-me')).data['email_verified'])

    def test_changing_the_email_on_the_profile_needs_a_new_confirmation(self):
        user = Account.objects.create_user(username='mover', email='old@example.com', password='pass12345')
        self.client.force_authenticate(user)

        response = self.client.patch(reverse('profile'), {'email': 'new@example.com'}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['email_verified'])
        self.assertEqual(mail.outbox[0].to, ['new@example.com'])

    def test_saving_the_profile_with_the_same_email_keeps_it_confirmed(self):
        user = Account.objects.create_user(username='stayer', email='same@example.com', password='pass12345')
        self.client.force_authenticate(user)

        response = self.client.patch(reverse('profile'), {'email': 'same@example.com', 'bio': 'Hi'}, format='json')

        self.assertTrue(response.data['email_verified'])
        self.assertEqual(mail.outbox, [])


    def test_the_profile_cannot_take_an_email_another_account_uses(self):
        Account.objects.create_user(username='owner', email='mine@example.com', password='pass12345')
        user = Account.objects.create_user(username='copycat', email='copy@example.com', password='pass12345')
        self.client.force_authenticate(user)

        response = self.client.patch(reverse('profile'), {'email': 'MINE@example.com'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_the_database_refuses_two_accounts_with_one_email(self):
        from django.db import IntegrityError, transaction

        Account.objects.create_user(username='one', email='dup@example.com', password='pass12345')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Account.objects.create_user(username='two', email='DUP@example.com', password='pass12345')
        # Accounts without an address don't clash.
        Account.objects.create_user(username='blank1', email='', password='pass12345')
        Account.objects.create_user(username='blank2', email='', password='pass12345')


class UnverifiedAccountLimitTests(APITestCase):
    def setUp(self):
        from post.models import LiveAnimalPost, Species

        seller = Account.objects.create_user(username='seller', email='seller@example.com', password='pass12345')
        self.post = LiveAnimalPost.objects.create(
            account=seller, species=Species.objects.create(name='Geckos'), title='Leo', description='d', contact_info='{}',
        )
        self.user = Account.objects.create_user(
            username='fresh', email='fresh@example.com', password='pass12345', email_verified=False,
        )
        self.client.force_authenticate(self.user)

    def test_unverified_account_can_browse(self):
        self.assertEqual(self.client.get(reverse('live-animal-list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('live-animal-detail', args=[self.post.id])).status_code, 200)

    def test_unverified_account_cannot_post_a_listing(self):
        response = self.client.post(reverse('live-animal-list'), {'title': 'X'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertIn('confirm your email address', response.data['detail'])

    def test_unverified_account_cannot_contact_a_seller(self):
        response = self.client.post(reverse('live-animal-contact', args=[self.post.id]))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(mail.outbox, [])

    def test_unverified_account_cannot_report_a_listing(self):
        self.assertEqual(self.client.post(reverse('live-animal-report', args=[self.post.id])).status_code, 403)

    def test_unverified_account_cannot_bid(self):
        response = self.client.post(reverse('auction-bids', args=[1]), {'amount': '100'})
        self.assertEqual(response.status_code, 403)

    def test_confirming_the_address_lifts_the_limits(self):
        Account.objects.filter(pk=self.user.pk).update(email_verified=True)
        self.user.refresh_from_db()
        self.client.force_authenticate(self.user)

        self.assertEqual(self.client.post(reverse('live-animal-contact', args=[self.post.id])).status_code, 200)


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = Account.objects.create_user(username='forgetful', email='forgetful@example.com', password='OldPass!234')

    def request_reset(self, email='forgetful@example.com'):
        return self.client.post(reverse('password-reset'), {'email': email})

    def test_requesting_a_reset_emails_a_link(self):
        response = self.request_reset('Forgetful@Example.com')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox[0].to, ['forgetful@example.com'])
        self.assertIn('/reset-password?uid=', mail.outbox[0].body)
        self.assertIn('forgetful', mail.outbox[0].body)

    def test_unknown_address_gets_the_same_answer_and_no_email(self):
        known = self.request_reset()
        unknown = self.request_reset('nobody@example.com')

        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(unknown.data, known.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_the_link_sets_a_new_password(self):
        self.request_reset()

        response = self.client.post(reverse('password-reset-confirm'), {
            **link_params(mail.outbox[0]), 'password': 'BrandNew!567',
        })

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew!567'))

    def test_the_link_works_only_once(self):
        self.request_reset()
        params = link_params(mail.outbox[0])
        self.client.post(reverse('password-reset-confirm'), {**params, 'password': 'BrandNew!567'})

        response = self.client.post(reverse('password-reset-confirm'), {**params, 'password': 'Another!890'})

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew!567'))

    def test_weak_passwords_are_rejected(self):
        self.request_reset()

        response = self.client.post(reverse('password-reset-confirm'), {**link_params(mail.outbox[0]), 'password': '123'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)

    def test_resetting_signs_out_everywhere_and_confirms_the_email(self):
        Account.objects.filter(pk=self.user.pk).update(email_verified=False)
        refresh = self.client.post(reverse('jwt-login'), {'username': 'forgetful', 'password': 'OldPass!234'}).data['refresh']
        self.request_reset()

        self.client.post(reverse('password-reset-confirm'), {**link_params(mail.outbox[0]), 'password': 'BrandNew!567'})

        self.assertEqual(self.client.post(reverse('jwt-refresh'), {'refresh': refresh}).status_code, 401)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    LOGIN_LOCKOUT_FAILURES=3, LOGIN_LOCKOUT_MINUTES=15,
)
class AdminLoginLockoutTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        Account.objects.create_superuser(username='boss', email='boss@example.com', password='Right!Pass123')
        self.url = reverse('admin:login')

    def sign_in(self, password, username='boss', address='203.0.113.7'):
        return self.client.post(
            self.url, {'username': username, 'password': password, 'next': reverse('admin:index')},
            HTTP_X_FORWARDED_FOR=address,
        )

    def test_the_right_password_signs_in(self):
        self.assertEqual(self.sign_in('Right!Pass123').status_code, 302)

    def test_repeated_wrong_passwords_lock_the_account_even_for_the_right_one(self):
        for _ in range(3):
            self.assertEqual(self.sign_in('wrong').status_code, 200)

        response = self.sign_in('Right!Pass123', address='198.51.100.9')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Too many failed sign-in attempts')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_one_address_guessing_many_usernames_is_locked_out(self):
        for name in ('a', 'b', 'c'):
            self.sign_in('wrong', username=name)

        self.assertContains(self.sign_in('Right!Pass123'), 'Too many failed sign-in attempts')
        self.assertEqual(self.sign_in('Right!Pass123', address='198.51.100.9').status_code, 302)

    def test_the_lock_wears_off(self):
        from django.core.cache import cache

        for _ in range(3):
            self.sign_in('wrong')
        cache.clear()  # what the timeout does after LOGIN_LOCKOUT_MINUTES

        self.assertEqual(self.sign_in('Right!Pass123').status_code, 302)

    def test_the_browsable_api_login_is_locked_the_same_way(self):
        for _ in range(3):
            self.client.post('/api-auth/login/', {'username': 'boss', 'password': 'wrong'})

        response = self.client.post('/api-auth/login/', {'username': 'boss', 'password': 'Right!Pass123'})

        self.assertContains(response, 'Too many failed sign-in attempts')


class AdminAddressTests(APITestCase):
    def tearDown(self):
        self.reload_urls()

    def reload_urls(self):
        import importlib

        from django.urls import clear_url_caches

        import backend.urls

        clear_url_caches()
        importlib.reload(backend.urls)

    def test_admin_is_at_admin_by_default(self):
        self.assertEqual(reverse('admin:index'), '/admin/')

    def test_admin_address_comes_from_the_setting(self):
        with override_settings(ADMIN_URL='staff-x7k2/'):
            self.reload_urls()
            self.assertEqual(reverse('admin:index'), '/staff-x7k2/')
            self.assertEqual(self.client.get('/admin/').status_code, 404)


GOOGLE_CLIENT_ID = 'test-client.apps.googleusercontent.com'


@override_settings(GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID)
class GoogleSignInTests(APITestCase):
    """Tokens are signed with a key made here, standing in for Google's published keys."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from cryptography.hazmat.primitives.asymmetric import rsa

        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        from unittest import mock

        patcher = mock.patch('authentication.google._signing_key', return_value=self.private_key.public_key())
        patcher.start()
        self.addCleanup(patcher.stop)

    def google_token(self, **claims):
        import time

        import jwt

        now = int(time.time())
        payload = {
            'iss': 'https://accounts.google.com', 'aud': GOOGLE_CLIENT_ID, 'sub': '1234567890',
            'email': 'keeper@gmail.com', 'email_verified': True, 'iat': now, 'exp': now + 600,
        }
        payload.update(claims)
        return jwt.encode(payload, self.private_key, algorithm='RS256')

    def sign_in(self, **claims):
        return self.client.post(reverse('google-sign-in'), {'credential': self.google_token(**claims)})

    def test_a_new_google_user_gets_a_confirmed_account_without_a_password(self):
        response = self.sign_in()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['created'])
        account = Account.objects.get(email='keeper@gmail.com')
        self.assertEqual(account.username, 'keeper')
        self.assertTrue(account.email_verified)
        self.assertFalse(account.has_usable_password())
        self.assertEqual(account.google_id, '1234567890')
        me = self.client.get(reverse('jwt-me'), HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(me.data['username'], 'keeper')

    def test_signing_in_again_uses_the_same_account(self):
        self.sign_in()
        response = self.sign_in(email='renamed@gmail.com')

        self.assertFalse(response.data['created'])
        self.assertEqual(Account.objects.filter(google_id='1234567890').count(), 1)
        self.assertFalse(Account.objects.filter(email='renamed@gmail.com').exists())

    def test_a_taken_username_gets_a_number(self):
        Account.objects.create_user(username='keeper', email='other@example.com', password='pass12345')

        self.sign_in()

        self.assertEqual(Account.objects.get(email='keeper@gmail.com').username, 'keeper2')

    def test_an_existing_account_with_the_address_is_signed_in_and_keeps_its_password(self):
        account = Account.objects.create_user(username='olduser', email='Keeper@Gmail.com', password='pass12345')

        response = self.sign_in()

        self.assertFalse(response.data['created'])
        account.refresh_from_db()
        self.assertEqual(account.google_id, '1234567890')
        self.assertTrue(account.check_password('pass12345'))

    def test_an_unconfirmed_account_with_the_address_loses_its_password_and_sessions(self):
        # Someone may have signed up with the owner's address first, to get into the account later.
        account = Account.objects.create_user(
            username='squatter', email='keeper@gmail.com', password='pass12345', email_verified=False,
        )
        refresh = self.client.post(reverse('jwt-login'), {'username': 'squatter', 'password': 'pass12345'}).data['refresh']

        response = self.sign_in()

        self.assertEqual(response.status_code, 200)
        account.refresh_from_db()
        self.assertTrue(account.email_verified)
        self.assertFalse(account.has_usable_password())
        self.assertEqual(self.client.post(reverse('jwt-refresh'), {'refresh': refresh}).status_code, 401)

    def test_a_token_for_another_site_is_refused(self):
        response = self.sign_in(aud='someone-else.apps.googleusercontent.com')

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Account.objects.filter(email='keeper@gmail.com').exists())

    def test_an_expired_token_is_refused(self):
        response = self.sign_in(iat=1000, exp=2000)
        self.assertEqual(response.status_code, 401)

    def test_a_token_not_issued_by_google_is_refused(self):
        response = self.sign_in(iss='https://evil.example.com')
        self.assertEqual(response.status_code, 401)

    def test_an_unconfirmed_google_address_is_refused(self):
        Account.objects.create_user(username='olduser', email='keeper@gmail.com', password='pass12345')

        response = self.sign_in(email_verified=False)

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(Account.objects.get(username='olduser').google_id)

    def test_a_forged_signature_is_refused(self):
        token = self.google_token()
        header, payload, _signature = token.split('.')
        response = self.client.post(reverse('google-sign-in'), {'credential': f'{header}.{payload}.AAAA'})
        self.assertEqual(response.status_code, 401)

    def test_a_disabled_account_cannot_sign_in(self):
        Account.objects.create_user(username='banned', email='keeper@gmail.com', password='pass12345', is_active=False)

        response = self.sign_in()

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('access', response.data)
        self.assertIsNone(Account.objects.get(username='banned').google_id)

    @override_settings(GOOGLE_CLIENT_ID='')
    def test_it_is_off_until_a_client_id_is_set(self):
        response = self.sign_in()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Signing in with Google is not available.')

    def test_a_google_only_account_can_set_a_password_by_reset_link(self):
        self.sign_in()

        self.client.post(reverse('password-reset'), {'email': 'keeper@gmail.com'})

        self.assertEqual(len(mail.outbox), 1)
