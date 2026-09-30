"""
Payment gateways. All money goes through the platform first: bidders' deposits and buy-now purchases
are collected and held by us, then refunded or kept depending on how the sale goes.

The rest of the auction app only talks to the `PaymentGateway` interface below; the active gateway is
chosen by `settings.AUCTION_PAYMENT_GATEWAY`. `auction/ecpay.py` takes card payments through ECPay; its
callback views confirm or fail payments with `auction.services` / `auction.orders` when ECPay reports back.
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
    `payment` is a Deposit, BuyNowPurchase, Order (its balance) or SellerBond: each has `pk`, `amount`
    and `currency`.
    """
    name = None

    def collect(self, payment):
        """Start collecting `payment.amount` from the payer. Returns a PaymentResult."""
        raise NotImplementedError

    def resume(self, payment):
        """The payer came back to a payment they started and didn't finish. Returns a PaymentResult
        whose client_data lets them carry on, if the gateway can offer that."""
        return PaymentResult(paid=False, provider_reference=payment.provider_reference)

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


def resume_payment(payment):
    """A fresh way to pay for a payment that's still pending; returns the client_data for it. The caller
    holds the payment's row lock."""
    gateway = get_payment_gateway()
    result = gateway.resume(payment)
    if (payment.provider, payment.provider_reference) != (gateway.name, result.provider_reference):
        payment.provider = gateway.name
        payment.provider_reference = result.provider_reference
        payment.save(update_fields=['provider', 'provider_reference', 'updated_at'])
    return result.client_data
