"""
Auction rules in one place, so the API, the admin, management commands and (later) payment webhooks
all behave the same way. Anything that moves money goes through the configured payment gateway, and
all money (deposits, buy-now payments) is collected and held by the platform.
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from common.money import format_money
from . import notifications, orders
from .errors import AuctionError
from .models import Auction, Bid, BuyNowPurchase, Deposit, Incident
from .payments import get_payment_gateway

logger = logging.getLogger(__name__)




def deposit_amount_for(starting_price):
    rate_amount = (Decimal(starting_price) * settings.AUCTION_DEPOSIT_RATE).quantize(Decimal('0.01'))
    return max(rate_amount, settings.AUCTION_MIN_DEPOSIT)


def request_deposit(auction, account):
    """
    Start (or restart, after a failed payment) the bidder's deposit for this auction.
    Returns (deposit, client_data); client_data tells the frontend how to pay, if payment is needed.
    """
    if auction.seller_id == account.id:
        raise AuctionError(_("You can't bid on your own auction."))
    if auction.status != Auction.Status.ACTIVE or timezone.now() >= auction.ends_at:
        raise AuctionError(_('This auction is no longer accepting bids.'))

    with transaction.atomic():
        deposit = Deposit.objects.select_for_update().filter(auction=auction, account=account).first()
        if deposit and deposit.status in (Deposit.Status.PENDING, Deposit.Status.HELD):
            return deposit, {}

        gateway = get_payment_gateway()
        if deposit is None:
            deposit = Deposit(auction=auction, account=account)
        deposit.amount = auction.deposit_amount
        deposit.currency = auction.currency
        deposit.provider = gateway.name
        deposit.status = Deposit.Status.PENDING
        deposit.save()

        payment = gateway.collect(deposit)
        deposit.status = Deposit.Status.HELD if payment.paid else Deposit.Status.PENDING
        deposit.provider_reference = payment.provider_reference
        deposit.save(update_fields=['status', 'provider_reference', 'updated_at'])
    return deposit, payment.client_data


def confirm_deposit(deposit, provider_reference=None):
    """The gateway (or staff) reports the deposit as paid."""
    with transaction.atomic():
        deposit = Deposit.objects.select_for_update().select_related('auction').get(pk=deposit.pk)
        if deposit.status != Deposit.Status.PENDING:
            return deposit
        deposit.status = Deposit.Status.HELD
        if provider_reference:
            deposit.provider_reference = provider_reference
        deposit.save(update_fields=['status', 'provider_reference', 'updated_at'])

        # Paid after the auction closed: nothing left to bid on, so hand the money straight back.
        if deposit.auction.status != Auction.Status.ACTIVE:
            _close_deposit(deposit, get_payment_gateway())
    return deposit


def fail_deposit(deposit):
    """The gateway reports the payment failed or was abandoned; the bidder may try again."""
    Deposit.objects.filter(pk=deposit.pk, status=Deposit.Status.PENDING).update(
        status=Deposit.Status.FAILED, updated_at=timezone.now(),
    )


def release_deposit(deposit):
    """Refund a held deposit (e.g. staff resolving a winner's deposit by hand)."""
    with transaction.atomic():
        deposit = Deposit.objects.select_for_update().get(pk=deposit.pk)
        if deposit.status == Deposit.Status.HELD:
            get_payment_gateway().refund(deposit)
            deposit.status = Deposit.Status.RELEASED
            deposit.save(update_fields=['status', 'updated_at'])
    return deposit


def capture_deposit(deposit):
    """Keep a held deposit (e.g. apply it to the winner's payment, or forfeit it if they back out)."""
    with transaction.atomic():
        deposit = Deposit.objects.select_for_update().get(pk=deposit.pk)
        if deposit.status == Deposit.Status.HELD:
            get_payment_gateway().keep(deposit)
            deposit.status = Deposit.Status.CAPTURED
            deposit.save(update_fields=['status', 'updated_at'])
    return deposit


def place_bid(auction, bidder, amount):
    amount = Decimal(amount)
    with transaction.atomic():
        # Lock the auction so two simultaneous bids can't both beat the same current price.
        auction = Auction.objects.select_for_update().get(pk=auction.pk)

        if auction.seller_id == bidder.id:
            raise AuctionError(_("You can't bid on your own auction."))
        if not auction.is_open:
            raise AuctionError(_('This auction is not accepting bids right now.'))

        deposit = Deposit.objects.filter(auction=auction, account=bidder, status=Deposit.Status.HELD).first()
        if deposit is None:
            raise AuctionError(_('Pay the deposit for this auction before bidding.'))

        minimum = auction.minimum_next_bid
        if amount < minimum:
            raise AuctionError(_('Your bid must be at least %(amount)s.') % {'amount': format_money(minimum, auction.currency)})

        return Bid.objects.create(auction=auction, bidder=bidder, amount=amount, deposit=deposit)


def cancel_auction(auction):
    with transaction.atomic():
        auction = Auction.objects.select_for_update().get(pk=auction.pk)
        if auction.status != Auction.Status.ACTIVE:
            raise AuctionError(_('This auction has already closed.'))
        if auction.bids.exists():
            raise AuctionError(_("An auction can't be cancelled once someone has bid."))
        auction.status = Auction.Status.CANCELLED
        auction.save(update_fields=['status', 'updated_at'])
        _close_deposits(auction, keep_account_id=None)
        _cancel_pending_purchases(auction)
    return auction


def settle_auction(auction):
    """
    Close an auction whose end time has passed: record the winning bid and refund every other
    bidder's deposit. The winner's deposit stays HELD until the sale is completed.
    """
    with transaction.atomic():
        auction = Auction.objects.select_for_update().get(pk=auction.pk)
        if auction.status != Auction.Status.ACTIVE or timezone.now() < auction.ends_at:
            return auction
        auction.winning_bid = auction.highest_bid
        auction.status = Auction.Status.ENDED
        auction.save(update_fields=['winning_bid', 'status', 'updated_at'])
        winner_id = auction.winning_bid.bidder_id if auction.winning_bid else None
        losing_deposits = list(
            auction.deposits.select_related('account').exclude(account_id=winner_id)
            .filter(status=Deposit.Status.HELD)
        )
        _close_deposits(auction, keep_account_id=winner_id)
        _cancel_pending_purchases(auction)
        if auction.winning_bid:
            order = orders.create_bid_order(auction, auction.winning_bid)
            transaction.on_commit(lambda: notifications.auction_won(order, losing_deposits))
    return auction


# --- Buy now --------------------------------------------------------------------------------------

def start_buy_now(auction, buyer):
    """
    Start paying the buy-now price in full. Nothing is reserved: several buyers may be paying at once,
    and the first payment to arrive wins (confirm_buy_now). Returns (purchase, client_data, competing),
    where competing is how many other buyers are paying right now.
    """
    with transaction.atomic():
        auction = Auction.objects.select_for_update().get(pk=auction.pk)
        if auction.seller_id == buyer.id:
            raise AuctionError(_("You can't buy your own animal."))
        if auction.buy_now_price is None:
            raise AuctionError(_("The seller hasn't offered a buy-now price for this auction."))
        if not auction.buy_now_open(auction.current_price):
            raise AuctionError(_('Buy now is no longer available for this auction.'))

        pending = auction.purchases.filter(status=BuyNowPurchase.Status.PENDING).select_related('buyer')
        existing = pending.filter(buyer=buyer).first()
        if existing:
            return existing, {}, pending.exclude(buyer=buyer).count()
        others = list(pending.exclude(buyer=buyer))

        gateway = get_payment_gateway()
        purchase = BuyNowPurchase.objects.create(
            auction=auction, buyer=buyer, amount=auction.buy_now_price, currency=auction.currency,
            provider=gateway.name,
        )
        payment = gateway.collect(purchase)
        purchase.provider_reference = payment.provider_reference
        purchase.save(update_fields=['provider_reference', 'updated_at'])
        if others:
            transaction.on_commit(lambda: notifications.buy_now_competition(auction, [purchase, *others]))

    if payment.paid:
        purchase = confirm_buy_now(purchase)
    return purchase, payment.client_data, len(others)


def confirm_buy_now(purchase, provider_reference=None):
    """
    The gateway (or staff) reports a buy-now payment as arrived. The first one wins: the auction
    closes, every deposit is refunded and other buyers' pending payments are cancelled. A payment that
    arrives after that is refunded in full.
    """
    with transaction.atomic():
        # Lock the auction first, so two payments arriving together are decided one at a time.
        auction = Auction.objects.select_for_update().select_related('seller').get(pk=purchase.auction_id)
        purchase = BuyNowPurchase.objects.select_for_update().select_related('buyer').get(pk=purchase.pk)
        if purchase.status not in (BuyNowPurchase.Status.PENDING, BuyNowPurchase.Status.CANCELLED):
            return purchase
        if provider_reference:
            purchase.provider_reference = provider_reference

        wins = auction.status == Auction.Status.ACTIVE and timezone.now() < auction.ends_at
        if not wins:
            get_payment_gateway().refund(purchase)
            purchase.status = BuyNowPurchase.Status.REFUNDED
            purchase.save(update_fields=['status', 'provider_reference', 'updated_at'])
            transaction.on_commit(lambda: notifications.paid_too_late(purchase))
            return purchase

        purchase.status = BuyNowPurchase.Status.PAID
        purchase.paid_at = timezone.now()
        purchase.save(update_fields=['status', 'paid_at', 'provider_reference', 'updated_at'])
        auction.status = Auction.Status.ENDED
        auction.winning_purchase = purchase
        auction.winning_bid = None
        auction.save(update_fields=['status', 'winning_purchase', 'winning_bid', 'updated_at'])

        bidder_deposits = [
            deposit for deposit in auction.deposits.select_related('account').exclude(account=purchase.buyer)
            if deposit.status in (Deposit.Status.HELD, Deposit.Status.PENDING)
        ]
        _close_deposits(auction, keep_account_id=None)  # the buyer's own deposit too, if they bid
        cancelled = _cancel_pending_purchases(auction)
        order = orders.create_buy_now_order(auction, purchase)
        transaction.on_commit(lambda: notifications.bought(order, bidder_deposits, cancelled))
    return purchase


def fail_buy_now(purchase):
    """The gateway reports the payment failed or was abandoned; the buyer may try again."""
    failed = BuyNowPurchase.objects.filter(pk=purchase.pk, status=BuyNowPurchase.Status.PENDING).update(
        status=BuyNowPurchase.Status.FAILED, updated_at=timezone.now(),
    )
    if failed:
        orders.record_incident(purchase.buyer, Incident.Kind.UNPAID_BUY_NOW, purchase.auction, 'Payment failed')


def _cancel_pending_purchases(auction):
    """The auction has closed: buy-now payments still in progress can no longer win."""
    pending = list(auction.purchases.select_for_update().select_related('buyer').filter(status=BuyNowPurchase.Status.PENDING))
    auction.purchases.filter(pk__in=[purchase.pk for purchase in pending]).update(
        status=BuyNowPurchase.Status.CANCELLED, updated_at=timezone.now(),
    )
    # Starting buy-now and never paying is worth tracking (it blocks nobody, but a pattern stands out).
    for purchase in pending:
        orders.record_incident(purchase.buyer, Incident.Kind.UNPAID_BUY_NOW, auction, 'Auction closed before payment arrived')
    return pending


def check_can_start_auction(account):
    """Paid commercial accounts only, and (when settings.SELLER_BOND_AMOUNT is set) with a bond held."""
    if not account.can_start_auction:
        raise AuctionError(_('Auctions are available to paid commercial accounts. Upgrade your account to start one.'))
    if orders.bond_required() and not orders.has_bond(account):
        raise AuctionError(_('Post the seller bond of %(amount)s before starting an auction.') % {
            'amount': format_money(settings.SELLER_BOND_AMOUNT),
        })


def settle_due_auctions():
    due = Auction.objects.filter(status=Auction.Status.ACTIVE, ends_at__lte=timezone.now())
    return [settle_auction(auction) for auction in due]


def _close_deposits(auction, keep_account_id):
    gateway = get_payment_gateway()
    for deposit in auction.deposits.select_for_update().exclude(account_id=keep_account_id):
        _close_deposit(deposit, gateway)


def _close_deposit(deposit, gateway):
    if deposit.status == Deposit.Status.PENDING:
        deposit.status = Deposit.Status.CANCELLED
    elif deposit.status == Deposit.Status.HELD:
        try:
            gateway.refund(deposit)
        except Exception:
            # Leave it HELD so it shows up for staff to refund, rather than failing the whole close.
            logger.exception('Could not release deposit %s', deposit.pk)
            return
        deposit.status = Deposit.Status.RELEASED
    else:
        return
    deposit.save(update_fields=['status', 'updated_at'])
