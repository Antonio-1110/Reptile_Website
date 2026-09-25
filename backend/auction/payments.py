"""
Payment gateways. All money goes through the platform first: bidders' deposits and buy-now purchases
are collected and held by us, then refunded or kept depending on how the sale goes.

The rest of the auction app only talks to the `PaymentGateway` interface below; the active gateway is
chosen by `settings.AUCTION_PAYMENT_GATEWAY`. To take real payments, subclass `PaymentGateway` for the
processor (e.g. ECPay, NewebPay, Stripe), point the setting at it, and add a webhook view that calls
`auction.services.confirm_deposit()` / `fail_deposit()` and `confirm_buy_now()` / `fail_buy_now()`
when the processor reports back.
"""
from dataclasses import dataclass, field

from django.conf import settings
from django.utils.module_loading import import_string


@dataclass
class PaymentResult:
    """What a gateway returns when asked to collect a payment."""
    paid: bool  # True if the money arrived on the spot; False if the payer still has to pay
    provider_reference: str = ''
    # Passed through to the frontend untouched, e.g. {'checkout_url': ...} or bank transfer details.
    client_data: dict = field(default_factory=dict)


class PaymentGateway:
    """
    `payment` is a Deposit or a BuyNowPurchase: both have `pk`, `amount`, `currency` and the paying
    account (`payer`).
    """
    name = None

    def collect(self, payment):
        """Start collecting `payment.amount` from the payer. Returns a PaymentResult."""
        raise NotImplementedError

    def refund(self, payment):
        """Give a collected payment back in full. Raise on failure; the caller then leaves it as is."""
        raise NotImplementedError

    def keep(self, payment):
        """Keep a collected payment (e.g. a deposit applied to the winner's purchase). Raise on failure."""
        raise NotImplementedError


class ManualPaymentGateway(PaymentGateway):
    """
    Payments are made outside the site (e.g. bank transfer) and confirmed by staff with the
    "Mark as paid" actions in the admin. Refunds are likewise done by hand.
    """
    name = 'manual'

    def collect(self, payment):
        return PaymentResult(paid=False, provider_reference=f'manual-{payment._meta.model_name}-{payment.pk}')

    def refund(self, payment):
        pass

    def keep(self, payment):
        pass


class InstantPaymentGateway(ManualPaymentGateway):
    """Development only: every payment counts as paid immediately, so the flows can be tried locally."""
    name = 'instant'

    def collect(self, payment):
        return PaymentResult(paid=True, provider_reference=f'instant-{payment._meta.model_name}-{payment.pk}')


def get_payment_gateway():
    return import_string(settings.AUCTION_PAYMENT_GATEWAY)()
