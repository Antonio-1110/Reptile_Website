import io
from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from account.models import Account

from .models import Alert
from .services import notify, send_digests


def make_account(username, **fields):
    return Account.objects.create_user(username=username, email=f'{username}@example.com', password='pass12345', **fields)


class NotifyTests(APITestCase):
    def setUp(self):
        self.user = make_account('keeper')

    def test_stores_the_text_in_every_language_without_emailing(self):
        notify([self.user], lambda: ('Price drop', 'Now cheaper'), link='/posts/3')
        alert = Alert.objects.get()
        self.assertEqual(set(alert.text), {'en', 'zh-hant'})
        self.assertEqual((alert.link, alert.read_at, alert.emailed_at), ('/posts/3', None, None))
        self.assertEqual(mail.outbox, [])

    def test_urgent_alerts_are_also_emailed_right_away_and_never_again(self):
        notify([self.user], lambda: ('Payment due', 'Pay by Friday'), email=True)
        self.assertEqual(mail.outbox[0].to, ['keeper@example.com'])
        self.assertIsNotNone(Alert.objects.get().emailed_at)


class AlertApiTests(APITestCase):
    def setUp(self):
        self.user = make_account('keeper')
        self.other = make_account('other')
        notify([self.user], lambda: ('Price drop', 'Now cheaper'), link='/posts/3')
        notify([self.other], lambda: ('Not yours', 'Private'))
        self.client.force_authenticate(self.user)

    def test_lists_only_your_own_alerts(self):
        response = self.client.get(reverse('alert-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['title'] for item in response.data['results']], ['Price drop'])
        self.assertEqual(response.data['results'][0]['link'], '/posts/3')
        self.assertFalse(response.data['results'][0]['is_read'])

    def test_answers_in_the_readers_language(self):
        Alert.objects.filter(account=self.user).update(text={
            'en': {'title': 'Price drop', 'body': 'b'}, 'zh-hant': {'title': '降價', 'body': 'b'},
        })
        response = self.client.get(reverse('alert-list'), HTTP_ACCEPT_LANGUAGE='zh-TW')
        self.assertEqual(response.data['results'][0]['title'], '降價')

    def test_unread_count_and_marking_read(self):
        self.assertEqual(self.client.get(reverse('alert-unread-count')).data, {'count': 1})
        alert = Alert.objects.get(account=self.user)
        self.assertTrue(self.client.post(reverse('alert-read', args=[alert.pk])).data['is_read'])
        self.assertEqual(self.client.get(reverse('alert-unread-count')).data, {'count': 0})

        notify([self.user], lambda: ('Another', 'b'))
        self.assertEqual(self.client.post(reverse('alert-read-all')).data, {'marked_read': 1})
        self.assertFalse(Alert.objects.filter(account=self.user, read_at__isnull=True).exists())
        # Someone else's stay unread.
        self.assertTrue(Alert.objects.filter(account=self.other, read_at__isnull=True).exists())

    def test_cannot_mark_someone_elses_alert(self):
        theirs = Alert.objects.get(account=self.other)
        self.assertEqual(self.client.post(reverse('alert-read', args=[theirs.pk])).status_code, 404)


@override_settings(ALERT_DIGEST_MIN_UNREAD=3, ALERT_DIGEST_MIN_DAYS=2, ALERT_RETENTION_DAYS=90, FRONTEND_URL='https://reptiles.example')
class DigestTests(APITestCase):
    def setUp(self):
        self.user = make_account('keeper')

    def add_alerts(self, count, days_old, account=None):
        for index in range(count):
            notify([account or self.user], lambda index=index: (f'Alert {index}', 'b'))
        Alert.objects.filter(created_at__gte=timezone.now() - timedelta(minutes=1)).update(
            created_at=timezone.now() - timedelta(days=days_old),
        )

    def test_nothing_is_sent_until_enough_alerts_have_waited_long_enough(self):
        self.add_alerts(2, days_old=5)  # old enough, too few
        self.assertEqual(send_digests(), 0)
        self.add_alerts(1, days_old=1)  # enough now, but the oldest has waited long enough...
        self.assertEqual(send_digests(), 1)
        self.assertEqual(mail.outbox[0].to, ['keeper@example.com'])
        self.assertIn('Alert 0', mail.outbox[0].body)
        self.assertIn('https://reptiles.example/alerts', mail.outbox[0].body)

    def test_too_recent_alerts_wait(self):
        self.add_alerts(5, days_old=1)
        self.assertEqual(send_digests(), 0)
        self.assertEqual(mail.outbox, [])

    def test_each_alert_is_summarised_once(self):
        self.add_alerts(3, days_old=3)
        self.assertEqual(send_digests(), 1)
        self.assertEqual(send_digests(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(Alert.objects.filter(emailed_at__isnull=True).exists())

    def test_read_alerts_and_unconfirmed_addresses_are_left_out(self):
        self.add_alerts(3, days_old=3)
        Alert.objects.update(read_at=timezone.now())
        unconfirmed = make_account('unconfirmed', email_verified=False)
        self.add_alerts(3, days_old=3, account=unconfirmed)
        self.assertEqual(send_digests(), 0)

    def test_old_alerts_are_deleted(self):
        self.add_alerts(1, days_old=91)
        self.add_alerts(1, days_old=10)
        call_command('send_alert_digests', stdout=io.StringIO())
        self.assertEqual(Alert.objects.count(), 1)
