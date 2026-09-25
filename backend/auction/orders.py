"""
What happens after an auction sells, in one place: payment of the balance, handover, confirmation,
and every way a sale can fall through. All money stays with us until the buyer has the animal.

    winning bid ─► AWAITING_PAYMENT ──paid──► PAID ──seller hands over──► HANDED_OVER ──buyer confirms──► COMPLETED
    buy now ──────────────────────────────────┘ │                              │  (or the confirm window passes)
    runner-up offer ─► OFFERED ──paid──────────┘ │                              └─ problem reported ─► DISPUTED
         │                                       └─ handover deadline missed ─► SELLER_DEFAULTED (buyer refunded)
         └─ declined / lapsed ─► DECLINED
    AWAITING_PAYMENT ── payment deadline missed ─► BUYER_DEFAULTED (deposit kept; seller may offer the runner-up)

Deadlines are settings (ORDER_*); `manage.py process_orders` enforces them.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from . import notifications
from .errors import AuctionError
from .models import BuyNowPurchase, Deposit, Incident, Order, SellerBond
from .payments import get_payment_gateway

# Once an order reaches these, buyer and seller see each other's contact details to arrange the
# handover. (A winner who still owes the balance has paid a deposit, so they count.)
CONTACT_STATUSES = {
    Order.Status.AWAITING_PAYMENT, Order.Status.PAID, Order.Status.HANDED_OVER,
    Order.Status.COMPLETED, Order.Status.DISPUTED,
}


def record_incident(account, kind, auction=None, note=''):
    Incident.objects.create(account=account, kind=kind, auction=auction, note=note[:300])


# --- Creating orders (called by services when an auction sells) -----------------------------------

def create_bid_order(auction, bid):
    """The auction ended with a winner: they owe the price minus the deposit they already paid."""
    deposit = auction.deposits.filter(account=bid.bidder, status=Deposit.Status.HELD).first()
    held = deposit.amount if deposit else 0
    return Order.objects.create(
        auction=auction, buyer=bid.bidder, source=Order.Source.BID, status=Order.Status.AWAITING_PAYMENT,
        price=bid.amount, currency=auction.currency, deposit=deposit, balance=max(bid.amount - held, 0),
        payment_due_at=timezone.now() + timedelta(hours=settings.ORDER_PAYMENT_HOURS),
    )


def create_buy_now_order(auction, purchase):
    """A buy-now payment won: the full price is already with us, so the handover clock starts."""
    now = timezone.now()
    return Order.objects.create(
        auction=auction, buyer=purchase.buyer, source=Order.Source.BUY_NOW, status=Order.Status.PAID,
        price=purchase.amount, currency=purchase.currency, purchase=purchase, paid_at=now,
        handover_due_at=now + timedelta(days=settings.ORDER_HANDOVER_DAYS),
    )


# --- Paying ---------------------------------------------------------------------------------------

def pay_order(order, account):
    """
    The buyer pays what they owe: the winner's balance, or a runner-up accepting an offer.
    Returns (order, client_data); client_data tells the frontend how to pay, if payment is needed.
    """
    with transaction.atomic():
        order = _lock(order)
        if order.buyer_id != account.id:
            raise AuctionError(_('Only the buyer can pay for this order.'))
        if order.status not in (Order.Status.AWAITING_PAYMENT, Order.Status.OFFERED):
            raise AuctionError(_('This order is not waiting for payment.'))
        if order.balance_status == Order.BalanceStatus.PENDING:
            return order, {}
        gateway = get_payment_gateway()
        payment = gateway.collect(order)
        order.provider = gateway.name
        order.provider_reference = payment.provider_reference
        order.balance_status = Order.BalanceStatus.PENDING
        order.save(update_fields=['provider', 'provider_reference', 'balance_status', 'updated_at'])
    if payment.paid:
        order = confirm_order_payment(order)
    return order, payment.client_data


def confirm_order_payment(order, provider_reference=None):
    """The gateway (or staff) reports the buyer's payment as arrived."""
    with transaction.atomic():
        order = _lock(order)
        if order.balance_status != Order.BalanceStatus.PENDING:
            return order
        if provider_reference:
            order.provider_reference = provider_reference
        if order.status not in (Order.Status.AWAITING_PAYMENT, Order.Status.OFFERED):
            # Too late: the deadline passed (or the offer lapsed) before the money arrived.
            get_payment_gateway().refund(order)
            order.balance_status = Order.BalanceStatus.REFUNDED
            order.save(update_fields=['balance_status', 'provider_reference', 'updated_at'])
            transaction.on_commit(lambda: notifications.order_paid_too_late(order))
            return order

        if order.deposit and order.deposit.status == Deposit.Status.HELD:
            get_payment_gateway().keep(order.deposit)  # the deposit counts toward the price
            order.deposit.status = Deposit.Status.CAPTURED
            order.deposit.save(update_fields=['status', 'updated_at'])
        now = timezone.now()
        order.balance_status = Order.BalanceStatus.PAID
        order.status = Order.Status.PAID
        order.paid_at = now
        order.handover_due_at = now + timedelta(days=settings.ORDER_HANDOVER_DAYS)
        order.save()
        transaction.on_commit(lambda: notifications.order_paid(order))
    return order


def fail_order_payment(order):
    """The gateway reports the payment failed or was abandoned; the buyer may try again before the deadline."""
    Order.objects.filter(pk=order.pk, balance_status=Order.BalanceStatus.PENDING).update(
        balance_status=Order.BalanceStatus.NONE, updated_at=timezone.now(),
    )


# --- Handover -------------------------------------------------------------------------------------

def mark_handed_over(order, account, note=''):
    """The seller has handed the animal over or shipped it; the buyer's confirmation window starts."""
    with transaction.atomic():
        order = _lock(order)
        if order.auction.seller_id != account.id:
            raise AuctionError(_('Only the seller can mark this order as handed over.'))
        if order.status != Order.Status.PAID:
            raise AuctionError(_('This order is not waiting for the handover.'))
        now = timezone.now()
        order.status = Order.Status.HANDED_OVER
        order.handed_over_at = now
        order.confirm_due_at = now + timedelta(days=settings.ORDER_CONFIRM_DAYS)
        order.handover_note = note.strip()[:300]
        order.save()
        transaction.on_commit(lambda: notifications.order_handed_over(order))
    return order


def confirm_received(order, account):
    """The buyer confirms the animal arrived intact: the sale is complete and the seller can be paid."""
    with transaction.atomic():
        order = _lock(order)
        if order.buyer_id != account.id:
            raise AuctionError(_('Only the buyer can confirm this order.'))
        if order.status != Order.Status.HANDED_OVER:
            raise AuctionError(_('This order is not waiting for your confirmation.'))
        _complete(order)
    return order


def report_problem(order, account, text):
    """The buyer reports a problem instead of confirming; the money stays frozen until staff decide."""
    text = (text or '').strip()
    if not text:
        raise AuctionError(_('Please describe the problem.'))
    with transaction.atomic():
        order = _lock(order)
        if order.buyer_id != account.id:
            raise AuctionError(_('Only the buyer can report a problem with this order.'))
        if order.status not in (Order.Status.PAID, Order.Status.HANDED_OVER):
            raise AuctionError(_('A problem can only be reported before the sale is complete.'))
        order.status = Order.Status.DISPUTED
        order.problem_report = text[:2000]
        order.save(update_fields=['status', 'problem_report', 'updated_at'])
        transaction.on_commit(lambda: notifications.order_disputed(order))
    return order


def resolve_dispute(order, refund_buyer):
    """Staff decision on a reported problem: refund the buyer in full, or complete the sale."""
    with transaction.atomic():
        order = _lock(order)
        if order.status != Order.Status.DISPUTED:
            return order
        if refund_buyer:
            _refund_buyer(order)
            order.status = Order.Status.REFUNDED
            order.save(update_fields=['status', 'updated_at'])
            record_incident(order.auction.seller, Incident.Kind.DISPUTE_LOST, order.auction, order.problem_report)
            transaction.on_commit(lambda: notifications.order_refunded(order))
        else:
            _complete(order)
    return order


def mark_paid_out(order):
    """Staff have paid the seller for a completed order."""
    Order.objects.filter(pk=order.pk, status=Order.Status.COMPLETED, paid_out_at__isnull=True).update(
        paid_out_at=timezone.now(), updated_at=timezone.now(),
    )


# --- When the winner doesn't pay: the runner-up -----------------------------------------------------

def runner_up_bid(order):
    """The best bid from someone other than the defaulted winner (and the seller), or None."""
    return (
        order.auction.bids.exclude(bidder_id__in=[order.buyer_id, order.auction.seller_id])
        .select_related('bidder').order_by('-amount', 'created_at').first()
    )


def decide_runner_up(order, account, offer):
    """
    After the winner defaulted, the seller decides whether to offer the animal to the runner-up at
    their own bid. We never hold the animal, so saying no simply ends the sale.
    """
    with transaction.atomic():
        order = _lock(order)
        if order.auction.seller_id != account.id:
            raise AuctionError(_('Only the seller can decide this.'))
        if order.status != Order.Status.BUYER_DEFAULTED or order.runner_up_decision:
            raise AuctionError(_('There is no runner-up decision to make for this order.'))
        bid = runner_up_bid(order) if offer else None
        if offer and bid is None:
            raise AuctionError(_('Nobody else bid on this auction.'))
        order.runner_up_decision = Order.RunnerUpDecision.OFFERED if offer else Order.RunnerUpDecision.DECLINED
        order.save(update_fields=['runner_up_decision', 'updated_at'])
        if not offer:
            return order
        offer_order = Order.objects.create(
            auction=order.auction, buyer=bid.bidder, source=Order.Source.RUNNER_UP, status=Order.Status.OFFERED,
            price=bid.amount, currency=order.currency, balance=bid.amount,
            payment_due_at=timezone.now() + timedelta(hours=settings.ORDER_RUNNER_UP_OFFER_HOURS),
        )
        transaction.on_commit(lambda: notifications.runner_up_offered(offer_order))
    return offer_order


def decline_offer(order, account):
    """The runner-up turns the offer down. No penalty: they were never obliged to buy."""
    with transaction.atomic():
        order = _lock(order)
        if order.buyer_id != account.id or order.status != Order.Status.OFFERED:
            raise AuctionError(_('There is no offer to decline.'))
        order.status = Order.Status.DECLINED
        order.save(update_fields=['status', 'updated_at'])
        transaction.on_commit(lambda: notifications.runner_up_declined(order))
    return order


# --- Deadlines (manage.py process_orders) -----------------------------------------------------------

def process_due_orders():
    """Apply every deadline that has passed. Returns how many orders changed."""
    now = timezone.now()
    handlers = [
        (Order.Status.AWAITING_PAYMENT, 'payment_due_at', _buyer_defaulted),
        (Order.Status.OFFERED, 'payment_due_at', _offer_lapsed),
        (Order.Status.PAID, 'handover_due_at', _seller_defaulted),
        (Order.Status.HANDED_OVER, 'confirm_due_at', _confirm_window_passed),
    ]
    changed = 0
    for status, due_field, handler in handlers:
        for order in Order.objects.filter(status=status, **{f'{due_field}__lte': now}):
            with transaction.atomic():
                order = _lock(order)
                if order.status == status and getattr(order, due_field) <= now:
                    handler(order)
                    changed += 1
    return changed


def _buyer_defaulted(order):
    """The winner didn't pay in time: their deposit is kept and the seller may offer the runner-up."""
    if order.deposit and order.deposit.status == Deposit.Status.HELD:
        get_payment_gateway().keep(order.deposit)
        order.deposit.status = Deposit.Status.CAPTURED
        order.deposit.save(update_fields=['status', 'updated_at'])
    order.status = Order.Status.BUYER_DEFAULTED
    order.save(update_fields=['status', 'updated_at'])
    record_incident(order.buyer, Incident.Kind.WINNER_DEFAULTED, order.auction)
    runner_up = runner_up_bid(order)
    transaction.on_commit(lambda: notifications.buyer_defaulted(order, runner_up))


def _offer_lapsed(order):
    order.status = Order.Status.DECLINED
    order.save(update_fields=['status', 'updated_at'])
    transaction.on_commit(lambda: notifications.runner_up_declined(order))


def _seller_defaulted(order):
    """The seller took no action by the handover deadline: the buyer gets everything back."""
    _refund_buyer(order)
    order.status = Order.Status.SELLER_DEFAULTED
    order.save(update_fields=['status', 'updated_at'])
    seller = order.auction.seller
    record_incident(seller, Incident.Kind.SELLER_NO_SHOW, order.auction)
    bond = SellerBond.objects.select_for_update().filter(account=seller, status=SellerBond.Status.HELD).first()
    if bond:
        get_payment_gateway().keep(bond)
        bond.status = SellerBond.Status.FORFEITED
        bond.save(update_fields=['status', 'updated_at'])
    transaction.on_commit(lambda: notifications.seller_defaulted(order, bond))


def _confirm_window_passed(order):
    """The buyer neither confirmed nor reported a problem in time: the sale completes."""
    _complete(order)


# --- Helpers --------------------------------------------------------------------------------------

def _lock(order):
    return Order.objects.select_for_update().select_related(
        'auction__seller', 'buyer', 'deposit', 'purchase',
    ).get(pk=order.pk)


def _complete(order):
    order.status = Order.Status.COMPLETED
    order.completed_at = timezone.now()
    order.save(update_fields=['status', 'completed_at', 'updated_at'])
    # The buyer has it: the listing is sold (it stays visible, but out of the marketplace list).
    post = order.auction.post
    post.status = post.Status.SOLD
    post.save(update_fields=['status', 'updated_at'])
    transaction.on_commit(lambda: notifications.order_completed(order))


def _refund_buyer(order):
    """Give the buyer back everything they paid us for this order."""
    gateway = get_payment_gateway()
    if order.deposit and order.deposit.status in (Deposit.Status.HELD, Deposit.Status.CAPTURED):
        gateway.refund(order.deposit)
        order.deposit.status = Deposit.Status.RELEASED
        order.deposit.save(update_fields=['status', 'updated_at'])
    if order.balance_status == Order.BalanceStatus.PAID:
        gateway.refund(order)
        order.balance_status = Order.BalanceStatus.REFUNDED
        order.save(update_fields=['balance_status', 'updated_at'])
    if order.purchase and order.purchase.status == BuyNowPurchase.Status.PAID:
        gateway.refund(order.purchase)
        order.purchase.status = BuyNowPurchase.Status.REFUNDED
        order.purchase.save(update_fields=['status', 'updated_at'])


# --- Reading --------------------------------------------------------------------------------------

def orders_for(account):
    """Orders the account is part of, as buyer or as seller."""
    return Order.objects.filter(Q(buyer=account) | Q(auction__seller=account)).select_related(
        'auction__seller', 'auction__live_animal_post', 'auction__equipment_post', 'buyer',
    )


def counterpart_contact(order, account):
    """The other side's contact details, once the order has got far enough; otherwise None."""
    if order.status not in CONTACT_STATUSES:
        return None
    if account.id == order.buyer_id:
        return order.auction.seller.contact_details()
    if account.id == order.auction.seller_id:
        return order.buyer.contact_details()
    return None


# --- Seller bond ----------------------------------------------------------------------------------

def bond_required():
    return settings.SELLER_BOND_AMOUNT > 0


def has_bond(account):
    return SellerBond.objects.filter(account=account, status=SellerBond.Status.HELD).exists()


def request_bond(account):
    """Start (or restart) paying the seller bond. Returns (bond, client_data)."""
    if not bond_required():
        raise AuctionError(_('A seller bond is not required right now.'))
    if not account.can_start_auction:
        raise AuctionError(_('Auctions are available to paid commercial accounts. Upgrade your account to start one.'))
    with transaction.atomic():
        bond = SellerBond.objects.select_for_update().filter(account=account).first()
        if bond and bond.status in (SellerBond.Status.PENDING, SellerBond.Status.HELD):
            return bond, {}
        gateway = get_payment_gateway()
        bond = bond or SellerBond(account=account)
        bond.amount = settings.SELLER_BOND_AMOUNT
        bond.currency = settings.AUCTION_CURRENCY
        bond.provider = gateway.name
        bond.status = SellerBond.Status.PENDING
        bond.save()
        payment = gateway.collect(bond)
        bond.provider_reference = payment.provider_reference
        bond.status = SellerBond.Status.HELD if payment.paid else SellerBond.Status.PENDING
        bond.save(update_fields=['provider_reference', 'status', 'updated_at'])
    return bond, payment.client_data


def confirm_bond(bond):
    SellerBond.objects.filter(pk=bond.pk, status=SellerBond.Status.PENDING).update(
        status=SellerBond.Status.HELD, updated_at=timezone.now(),
    )


def release_bond(bond):
    """Give a held bond back (e.g. the seller stops selling)."""
    with transaction.atomic():
        bond = SellerBond.objects.select_for_update().get(pk=bond.pk)
        if bond.status == SellerBond.Status.HELD:
            get_payment_gateway().refund(bond)
            bond.status = SellerBond.Status.RELEASED
            bond.save(update_fields=['status', 'updated_at'])
    return bond
