from decimal import Decimal
from unittest import mock
from urllib.parse import parse_qsl

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.urls import reverse

from . import ecpay, services
from .models import Auction, BuyNowPurchase, Deposit
from .tests import AuctionTestCase

# ECPay's public test merchant, the same for everyone testing against payment-stage.ecpay.com.tw.
TEST_MERCHANT = {
    'ECPAY_MERCHANT_ID': '3002607',
    'ECPAY_HASH_KEY': 'pwFHCqoQZGmho4w6',
    'ECPAY_HASH_IV': 'EkRm7iFT261dpevs',
}
ECPAY = override_settings(
    AUCTION_PAYMENT_GATEWAY='auction.ecpay.ECPayGateway', FRONTEND_URL='https://www.example.com',
    BACKEND_URL='https://api.example.com', ECPAY_LIVE=False, ECPAY_MANUAL_SETTLEMENT=False, **TEST_MERCHANT,
)


class FakeECPay:
    """Stands in for ECPay's DoAction API (refunds and settlement): records each call and answers with
    the queued RtnCodes, "1" (success) once they run out."""
    def __init__(self, *codes):
        self.codes = list(codes)
        self.calls = []

    def __call__(self, request, timeout):
        params = dict(parse_qsl(request.data.decode()))
        assert ecpay.is_signed(params), 'DoAction request is not signed'
        self.calls.append((params['Action'], params['MerchantTradeNo'], params['TradeNo'], params['TotalAmount']))
        code = self.codes.pop(0) if self.codes else '1'
        return mock.MagicMock(**{'__enter__.return_value.read.return_value': f'RtnCode={code}&RtnMsg=x'.encode()})

    @property
    def actions(self):
        return [call[0] for call in self.calls]


class CheckMacValueTests(AuctionTestCase):
    def test_matches_the_worked_example_in_ecpays_documentation(self):
        params = {
            'ChoosePayment': 'ALL', 'EncryptType': '1', 'ItemName': 'Apple iphone 15', 'MerchantID': '3002607',
            'MerchantTradeDate': '2023/03/12 15:30:23', 'MerchantTradeNo': 'ecpay20230312153023',
            'PaymentType': 'aio', 'ReturnURL': 'https://www.ecpay.com.tw/receive.php', 'TotalAmount': '30000',
            'TradeDesc': '促銷方案',
        }
        self.assertEqual(
            ecpay.check_mac_value(params, 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs'),
            '6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840',
        )

    @override_settings(AUCTION_PAYMENT_GATEWAY='auction.ecpay.ECPayGateway', ECPAY_MERCHANT_ID='')
    def test_refuses_to_run_without_credentials(self):
        with self.assertRaises(ImproperlyConfigured):
            ecpay.ECPayGateway()

    @override_settings(
        AUCTION_PAYMENT_GATEWAY='auction.payments.ManualPaymentGateway', ECPAY_MERCHANT_ID='', ECPAY_HASH_KEY='',
        ECPAY_HASH_IV='',
    )
    def test_results_are_refused_while_ecpay_is_switched_off(self):
        # With no keys, a forged result signed with empty ones must not touch a manual payment.
        auction = self.create_auction()
        services.request_deposit(auction, self.buyer)
        deposit = Deposit.objects.get(account=self.buyer)
        params = {
            'MerchantTradeNo': deposit.provider_reference, 'RtnCode': '0', 'CustomField1': f'deposit:{deposit.pk}',
        }
        params['CheckMacValue'] = ecpay.check_mac_value(params, '', '')
        for name in ('ecpay-notify', 'ecpay-result'):
            self.assertEqual(self.client.post(reverse(name), params).status_code, 404)
        self.assertEqual(Deposit.objects.get(pk=deposit.pk).status, Deposit.Status.PENDING)


@ECPAY
class ECPayCheckoutTests(AuctionTestCase):
    def setUp(self):
        super().setUp()
        self.auction = self.create_auction(buy_now_price=Decimal('9000.00'))
        self.fake = FakeECPay()
        patcher = mock.patch('auction.ecpay.urlopen', self.fake)
        patcher.start()
        self.addCleanup(patcher.stop)

    def start_deposit(self, user=None, language='en'):
        self.client.force_authenticate(user or self.buyer)
        response = self.client.post(reverse('auction-deposit', args=[self.auction.id]), HTTP_ACCEPT_LANGUAGE=language)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def ecpay_reply(self, form, rtn_code='1', trade_no='2409301234567890', amount=None, **extra):
        """What ECPay posts back for a checkout form: the fields it echoes, the outcome, signed."""
        fields = form['fields']
        params = {
            'MerchantID': fields['MerchantID'], 'MerchantTradeNo': fields['MerchantTradeNo'],
            'RtnCode': rtn_code, 'RtnMsg': 'Succeeded' if rtn_code == '1' else 'Failed', 'TradeNo': trade_no,
            'TradeAmt': amount or fields['TotalAmount'], 'PaymentDate': '2026/09/30 12:00:00',
            'PaymentType': 'Credit_CreditCard', 'PaymentTypeChargeFee': '14', 'TradeDate': fields['MerchantTradeDate'],
            'SimulatePaid': '0', 'CustomField1': fields['CustomField1'], 'CustomField2': '', 'CustomField3': '',
            'CustomField4': '', **extra,
        }
        params['CheckMacValue'] = ecpay.check_mac_value(params)
        return params

    def notify(self, params):
        return self.client.post(reverse('ecpay-notify'), params)

    def test_deposit_starts_a_signed_card_checkout_on_the_test_site(self):
        data = self.start_deposit()
        self.assertEqual(data['status'], 'pending')
        form = data['payment']['redirect_form']
        fields = form['fields']
        self.assertEqual(form['action'], 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5')
        self.assertEqual(fields['ChoosePayment'], 'Credit')
        self.assertEqual(fields['TotalAmount'], '500')
        self.assertEqual(fields['ReturnURL'], 'https://api.example.com/payments/ecpay/notify/')
        self.assertEqual(fields['OrderResultURL'], 'https://api.example.com/payments/ecpay/result/')
        self.assertEqual(fields['ClientBackURL'], f'https://www.example.com/auctions/{self.auction.id}')
        self.assertEqual(fields['Language'], 'ENG')
        self.assertLessEqual(len(fields['MerchantTradeNo']), 20)
        self.assertTrue(fields['MerchantTradeNo'].isalnum())
        self.assertTrue(ecpay.is_signed(fields))

    def test_chinese_speakers_get_ecpays_chinese_page(self):
        fields = self.start_deposit(language='zh-Hant')['payment']['redirect_form']['fields']
        self.assertNotIn('Language', fields)
        self.assertIn('保證金', fields['ItemName'])

    def test_paid_deposit_is_held_and_the_bidder_can_bid(self):
        form = self.start_deposit()['payment']['redirect_form']
        response = self.notify(self.ecpay_reply(form))
        self.assertEqual(response.content, b'1|OK')
        deposit = Deposit.objects.get(account=self.buyer)
        self.assertEqual(deposit.status, Deposit.Status.HELD)
        self.assertEqual(deposit.provider_reference, f'{form["fields"]["MerchantTradeNo"]}:2409301234567890')
        self.assertEqual(self.bid(self.auction, self.buyer, '5000.00').status_code, 201)

    def test_the_browser_return_confirms_the_payment_and_sends_the_payer_back(self):
        form = self.start_deposit()['payment']['redirect_form']
        response = self.client.post(reverse('ecpay-result'), self.ecpay_reply(form))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response['Location'], f'https://www.example.com/auctions/{self.auction.id}')
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.HELD)
        # ECPay's own server-to-server report then finds it done.
        self.assertEqual(self.notify(self.ecpay_reply(form)).content, b'1|OK')
        self.assertEqual(self.fake.calls, [])

    def test_unsigned_or_tampered_results_are_rejected(self):
        form = self.start_deposit()['payment']['redirect_form']
        params = self.ecpay_reply(form)
        params['TradeAmt'] = '1'
        self.assertEqual(self.notify(params).status_code, 400)
        self.assertEqual(self.client.post(reverse('ecpay-result'), params).status_code, 400)
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.PENDING)

    def test_results_for_payments_not_started_through_ecpay_are_ignored(self):
        with override_settings(AUCTION_PAYMENT_GATEWAY='auction.payments.ManualPaymentGateway'):
            services.request_deposit(self.auction, self.buyer)
        deposit = Deposit.objects.get(account=self.buyer)
        form = {'fields': {
            'MerchantID': '3002607', 'MerchantTradeNo': deposit.provider_reference, 'TotalAmount': '500',
            'MerchantTradeDate': '2026/09/30 12:00:00', 'CustomField1': f'deposit:{deposit.pk}',
        }}
        self.assertEqual(self.notify(self.ecpay_reply(form, rtn_code='10100058')).content, b'1|OK')
        self.assertEqual(Deposit.objects.get(pk=deposit.pk).status, Deposit.Status.PENDING)

    def test_a_failed_card_lets_the_bidder_try_again(self):
        form = self.start_deposit()['payment']['redirect_form']
        self.notify(self.ecpay_reply(form, rtn_code='10100058'))
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.FAILED)
        self.assertIn('redirect_form', self.start_deposit()['payment'])

    def test_coming_back_to_an_unfinished_payment_starts_a_fresh_checkout(self):
        first = self.start_deposit()['payment']['redirect_form']
        second = self.start_deposit()['payment']['redirect_form']
        self.assertNotEqual(first['fields']['MerchantTradeNo'], second['fields']['MerchantTradeNo'])
        # The abandoned attempt failing doesn't fail the one the bidder is on.
        self.notify(self.ecpay_reply(first, rtn_code='10100058'))
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.PENDING)
        self.notify(self.ecpay_reply(second))
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.HELD)

    def test_paying_twice_refunds_the_second_payment(self):
        first = self.start_deposit()['payment']['redirect_form']
        second = self.start_deposit()['payment']['redirect_form']
        self.notify(self.ecpay_reply(first, trade_no='1111'))
        self.notify(self.ecpay_reply(second, trade_no='2222'))
        deposit = Deposit.objects.get(account=self.buyer)
        self.assertEqual(deposit.provider_reference, f'{first["fields"]["MerchantTradeNo"]}:1111')
        self.assertEqual(self.fake.calls, [('N', second['fields']['MerchantTradeNo'], '2222', '500')])

    def test_a_payment_for_a_different_amount_is_refunded_not_accepted(self):
        form = self.start_deposit()['payment']['redirect_form']
        self.notify(self.ecpay_reply(form, amount='5'))
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.PENDING)
        self.assertEqual(self.fake.actions, ['N'])

    def test_losing_bidders_deposits_are_released_on_their_cards(self):
        form = self.start_deposit()['payment']['redirect_form']
        self.notify(self.ecpay_reply(form, trade_no='3333'))
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.post(reverse('auction-cancel', args=[self.auction.id])).status_code, 200)
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.RELEASED)
        self.assertEqual(self.fake.calls, [('N', form['fields']['MerchantTradeNo'], '3333', '500')])

    def test_a_settled_payment_is_refunded_when_it_cant_be_released(self):
        self.fake.codes = ['10200047']  # "N" refused: already settled, so "R" refunds it
        form = self.start_deposit()['payment']['redirect_form']
        self.notify(self.ecpay_reply(form, trade_no='4444'))
        services.release_deposit(Deposit.objects.get(account=self.buyer))
        self.assertEqual(self.fake.actions, ['N', 'R'])
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.RELEASED)

    def test_simulated_payments_are_ignored_on_the_live_site(self):
        form = self.start_deposit()['payment']['redirect_form']
        with override_settings(ECPAY_LIVE=True):
            self.notify(self.ecpay_reply(form, SimulatePaid='1'))
        self.assertEqual(Deposit.objects.get(account=self.buyer).status, Deposit.Status.PENDING)

    @override_settings(ECPAY_MANUAL_SETTLEMENT=True)
    def test_with_manual_settlement_buy_now_is_settled_and_deposits_wait(self):
        deposit_form = self.start_deposit(user=self.other_buyer)['payment']['redirect_form']
        self.notify(self.ecpay_reply(deposit_form, trade_no='5555'))
        self.assertEqual(self.fake.calls, [])  # the deposit stays an unsettled hold

        self.client.force_authenticate(self.buyer)
        with self.captureOnCommitCallbacks(execute=True):
            form = self.client.post(reverse('auction-buy-now', args=[self.auction.id])).data['payment']['redirect_form']
            self.notify(self.ecpay_reply(form, trade_no='6666'))
        self.assertEqual(BuyNowPurchase.objects.get(buyer=self.buyer).status, BuyNowPurchase.Status.PAID)
        self.assertEqual(Auction.objects.get(pk=self.auction.pk).status, Auction.Status.ENDED)
        self.assertEqual(sorted(self.fake.calls), [
            ('C', form['fields']['MerchantTradeNo'], '6666', '9000'),
            ('N', deposit_form['fields']['MerchantTradeNo'], '5555', '500'),
        ])
