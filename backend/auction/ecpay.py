"""
Card payments through ECPay (綠界) with its hosted checkout (AIO, 全方位金流).

The buyer's browser posts a signed form to ECPay's card page, pays there, and ECPay reports the result
twice: server to server (`notify`, ECPay's ReturnURL) and through the buyer's browser (`result`, the
OrderResultURL, which then sends them back to the site). Whichever arrives first confirms the payment;
the other finds it already done. Every attempt gets a new MerchantTradeNo, so a buyer who comes back
to an unfinished payment can start over; a stale attempt that is paid anyway is refunded.

References are stored as "<MerchantTradeNo>" while the buyer is paying and "<MerchantTradeNo>:<TradeNo>"
once ECPay has the money, since refunds and settlement need ECPay's own TradeNo.
"""
import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import parse_qsl, quote_plus, urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import orders, services
from .models import BuyNowPurchase, Deposit, Order, SellerBond
from .payments import PaymentGateway, PaymentResult

logger = logging.getLogger(__name__)

TEST_HOST = 'https://payment-stage.ecpay.com.tw'
LIVE_HOST = 'https://payment.ecpay.com.tw'


class ECPayError(Exception):
    pass


def check_mac_value(params, hash_key=None, hash_iv=None):
    """ECPay's CheckMacValue (SHA256): the sorted parameters between HashKey and HashIV, URL-encoded the
    way .NET does it, lower-cased and hashed."""
    hash_key = hash_key or settings.ECPAY_HASH_KEY
    hash_iv = hash_iv or settings.ECPAY_HASH_IV
    joined = '&'.join(f'{key}={params[key]}' for key in sorted(params, key=str.lower) if key != 'CheckMacValue')
    encoded = quote_plus(f'HashKey={hash_key}&{joined}&HashIV={hash_iv}', safe='').lower()
    # .NET's UrlEncode leaves these unescaped and escapes "~", which Python does the other way round.
    for escaped, char in (('%21', '!'), ('%2a', '*'), ('%28', '('), ('%29', ')')):
        encoded = encoded.replace(escaped, char)
    encoded = encoded.replace('~', '%7e')
    return hashlib.sha256(encoded.encode()).hexdigest().upper()


def is_configured():
    return bool(settings.ECPAY_MERCHANT_ID and settings.ECPAY_HASH_KEY and settings.ECPAY_HASH_IV)


def is_signed(params):
    expected = check_mac_value(params)
    return hmac.compare_digest(expected, params.get('CheckMacValue', '').upper())


# What each kind of payment is called on ECPay's page and in our references ("deposit:12"), and where the
# payer lands afterwards.
KINDS = {
    Deposit: 'deposit',
    BuyNowPurchase: 'purchase',
    Order: 'order',
    SellerBond: 'bond',
}
MODELS = {kind: model for model, kind in KINDS.items()}


def _item_name(payment):
    kind = KINDS[type(payment)]
    return {
        'deposit': _('Auction deposit'),
        'purchase': _('Buy-now payment'),
        'order': _('Auction payment'),
        'bond': _('Seller bond'),
    }[kind]


def return_path(payment):
    """Where on the website the payer goes once they've paid (or given up)."""
    if isinstance(payment, SellerBond):
        return '/my-listings'
    return f'/auctions/{payment.auction_id}'


def _new_trade_no(payment):
    # At most 20 letters and digits, unique across every attempt. ECPay's test merchant is shared by
    # everyone testing against it, hence the random tail.
    kind = KINDS[type(payment)][0].upper()
    stamp = format(int(time.time() * 1000), 'x')[-9:]
    return f'R{kind}{payment.pk}{stamp}{secrets.token_hex(2)}'[:20]


def split_reference(reference):
    merchant_trade_no, _sep, trade_no = (reference or '').partition(':')
    return merchant_trade_no, trade_no


class ECPayGateway(PaymentGateway):
    name = 'ecpay'

    def __init__(self):
        if not is_configured():
            raise ImproperlyConfigured('Set ECPAY_MERCHANT_ID, ECPAY_HASH_KEY and ECPAY_HASH_IV to use ECPay.')
        self.host = LIVE_HOST if settings.ECPAY_LIVE else TEST_HOST

    def collect(self, payment):
        trade_no = _new_trade_no(payment)
        fields = {
            'MerchantID': settings.ECPAY_MERCHANT_ID,
            'MerchantTradeNo': trade_no,
            'MerchantTradeDate': timezone.localtime(timezone.now(), timezone.get_fixed_timezone(8 * 60)).strftime('%Y/%m/%d %H:%M:%S'),
            'PaymentType': 'aio',
            'TotalAmount': str(int(payment.amount)),
            'TradeDesc': 'Reptilian',
            'ItemName': f'Reptilian {_item_name(payment)} #{payment.pk}',
            'ReturnURL': f'{settings.BACKEND_URL}/payments/ecpay/notify/',
            'OrderResultURL': f'{settings.BACKEND_URL}/payments/ecpay/result/',
            'ClientBackURL': settings.FRONTEND_URL + return_path(payment),
            # Card only: ATM and convenience-store payments can't be held, and their fees aren't refunded.
            'ChoosePayment': 'Credit',
            'EncryptType': '1',
            'CustomField1': f'{KINDS[type(payment)]}:{payment.pk}',
        }
        if not (translation.get_language() or '').startswith('zh'):
            fields['Language'] = 'ENG'
        fields['CheckMacValue'] = check_mac_value(fields)
        return PaymentResult(
            paid=False,
            provider_reference=trade_no,
            client_data={'redirect_form': {'action': f'{self.host}/Cashier/AioCheckOut/V5', 'fields': fields}},
        )

    def resume(self, payment):
        return self.collect(payment)

    def keep(self, payment):
        # Only held deposits wait unsettled; everything else was settled when it arrived.
        if settings.ECPAY_MANUAL_SETTLEMENT and isinstance(payment, Deposit):
            self._do_action(payment.provider_reference, payment.amount, 'C')

    def refund(self, payment):
        self.refund_reference(payment.provider_reference, payment.amount)

    def refund_reference(self, reference, amount):
        # "N" drops an authorization that hasn't been settled (no fee); "R" refunds a settled one.
        if not self._do_action(reference, amount, 'N', raise_on_error=False):
            self._do_action(reference, amount, 'R')

    def settle(self, payment):
        if settings.ECPAY_MANUAL_SETTLEMENT:
            self._do_action(payment.provider_reference, payment.amount, 'C')

    def _do_action(self, reference, amount, action, raise_on_error=True):
        merchant_trade_no, trade_no = split_reference(reference)
        if not trade_no:
            raise ECPayError(f'No ECPay TradeNo for {reference!r}; it was not paid through ECPay.')
        params = {
            'MerchantID': settings.ECPAY_MERCHANT_ID,
            'MerchantTradeNo': merchant_trade_no,
            'TradeNo': trade_no,
            'Action': action,
            'TotalAmount': str(int(amount)),
        }
        params['CheckMacValue'] = check_mac_value(params)
        request = Request(f'{self.host}/CreditDetail/DoAction', data=urlencode(params).encode(), method='POST')
        with urlopen(request, timeout=20) as response:
            reply = dict(parse_qsl(response.read().decode()))
        if reply.get('RtnCode') == '1':
            return True
        message = f'ECPay {action} failed for {reference}: {reply.get("RtnCode")} {reply.get("RtnMsg")}'
        if raise_on_error:
            raise ECPayError(message)
        logger.info(message)
        return False


# --- Results from ECPay ----------------------------------------------------------------------------

def _recorded(payment, reference):
    payment.refresh_from_db()
    return payment.provider_reference == reference


def _kept(payment):
    """After confirming: is the money staying with us (rather than refunded as too late)?"""
    if isinstance(payment, BuyNowPurchase):
        return payment.status == BuyNowPurchase.Status.PAID
    if isinstance(payment, Order):
        return payment.balance_status == Order.BalanceStatus.PAID
    if isinstance(payment, SellerBond):
        return payment.status == SellerBond.Status.HELD
    return False  # deposits stay held (unsettled) until the auction decides


def _confirm(payment, reference):
    if isinstance(payment, Deposit):
        services.confirm_deposit(payment, provider_reference=reference)
    elif isinstance(payment, BuyNowPurchase):
        services.confirm_buy_now(payment, provider_reference=reference)
    elif isinstance(payment, Order):
        orders.confirm_order_payment(payment, provider_reference=reference)
    else:
        orders.confirm_bond(payment, provider_reference=reference)


def _fail(payment):
    if isinstance(payment, Deposit):
        services.fail_deposit(payment)
    elif isinstance(payment, BuyNowPurchase):
        services.fail_buy_now(payment)
    elif isinstance(payment, Order):
        orders.fail_order_payment(payment)
    else:
        orders.fail_bond(payment)


def handle_result(params):
    """Apply a signed payment result from ECPay. Returns the payment it was about, or None."""
    kind, _sep, pk = params.get('CustomField1', '').partition(':')
    model = MODELS.get(kind)
    payment = model.objects.filter(pk=pk).first() if model and pk.isdigit() else None
    if payment is None or payment.provider != ECPayGateway.name:
        # Only payments started through ECPay can be settled by it, whichever gateway the site uses now.
        logger.error('ECPay result for an unknown payment: %s', params.get('MerchantTradeNo'))
        return None

    merchant_trade_no = params.get('MerchantTradeNo', '')
    paid = params.get('RtnCode') == '1'
    if paid and params.get('SimulatePaid') == '1' and settings.ECPAY_LIVE:
        logger.error('Ignored a simulated ECPay payment on the live site: %s', merchant_trade_no)
        return payment
    if not paid:
        # Only the attempt the payer is on can fail the payment; an older, abandoned one can't.
        if payment.provider_reference == merchant_trade_no:
            _fail(payment)
        return payment

    reference = f'{merchant_trade_no}:{params.get("TradeNo", "")}'
    if payment.provider_reference == reference:
        return payment  # ECPay reporting the same payment again
    gateway = ECPayGateway()
    if str(int(payment.amount)) != params.get('TradeAmt'):
        logger.error('ECPay amount mismatch on %s: %s', reference, params.get('TradeAmt'))
        gateway.refund_reference(reference, params.get('TradeAmt'))
        return payment

    _confirm(payment, reference)
    if not _recorded(payment, reference):
        # Paid after the payment was already settled another way (a second tab, an older attempt, or
        # after it was cancelled): nothing is waiting for this money, so give it back.
        logger.warning('Refunding an ECPay payment nothing was waiting for: %s', reference)
        gateway.refund_reference(reference, payment.amount)
    elif _kept(payment):
        gateway.settle(payment)
    return payment


def _signed_params(request):
    if not is_configured():
        # Without credentials the "signature" would use an empty key, which anyone can compute.
        raise Http404
    params = request.POST.dict()
    return params if params and is_signed(params) else None


@csrf_exempt
@require_POST
def notify(request):
    """ECPay's server-to-server ReturnURL. ECPay retries until it gets "1|OK"."""
    params = _signed_params(request)
    if params is None:
        return HttpResponseBadRequest('0|CheckMacValue Error')
    with transaction.atomic():
        handle_result(params)
    return HttpResponse('1|OK', content_type='text/plain')


@csrf_exempt
@require_POST
def result(request):
    """ECPay's OrderResultURL: the payer's browser, straight after paying. Sends them back to the site."""
    params = _signed_params(request)
    if params is None:
        return HttpResponseBadRequest('Invalid payment result.')
    payment = None
    try:
        with transaction.atomic():
            payment = handle_result(params)
    except Exception:
        # The payer still goes back to the site; ECPay's server-to-server call retries the update.
        logger.exception('Could not apply an ECPay result for %s', params.get('MerchantTradeNo'))
    path = return_path(payment) if payment else '/'
    return HttpResponseRedirect(settings.FRONTEND_URL + path, status=303)
