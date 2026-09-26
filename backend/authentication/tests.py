from django.contrib.auth import get_user_model
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

    def test_register_rejects_duplicate_username(self):
        Account.objects.create_user(username='taken', email='taken@example.com', password='pass12345')

        response = self.client.post(reverse('jwt-register'), {
            'username': 'taken',
            'email': 'other@example.com',
            'password': 'S3curePass!23',
        })

        self.assertEqual(response.status_code, 400)


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

    def test_refresh_returns_new_access_token(self):
        login_response = self.client.post(reverse('jwt-login'), {'username': 'seller', 'password': 'pass12345'})
        refresh_token = login_response.data['refresh']

        response = self.client.post(reverse('jwt-refresh'), {'refresh': refresh_token})

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)


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
        self.assertTrue(response.data['is_verified'])


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
        self.assertIn('This password is too common.', response.data['password'])

    def test_messages_follow_accept_language(self):
        response = self.register(HTTP_ACCEPT_LANGUAGE='zh-Hant')

        # Django's built-in model/password-validator messages come back translated.
        self.assertEqual(response.data['username'], ['一個相同名稱的使用者已經存在。'])
        self.assertIn('這個密碼太常見了。', response.data['password'])
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
