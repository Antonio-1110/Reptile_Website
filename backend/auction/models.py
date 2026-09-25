from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from account.models import Account
from post.models import EquipmentPost, LiveAnimalPost


class Auction(models.Model):
    """
    A timed auction on one of the seller's listings. Only paid commercial accounts may start one
    (`Account.can_start_auction`); anyone else may bid once they have a held `Deposit`.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        ENDED = 'ended', 'Ended'
        CANCELLED = 'cancelled', 'Cancelled'

    seller = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='auctions')
    live_animal_post = models.ForeignKey(LiveAnimalPost, on_delete=models.CASCADE, null=True, blank=True, related_name='auctions')
    equipment_post = models.ForeignKey(EquipmentPost, on_delete=models.CASCADE, null=True, blank=True, related_name='auctions')
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    min_increment = models.DecimalField(max_digits=10, decimal_places=2)
    # Optional: the seller agrees in advance to sell at this price. The first buyer to pay it in full
    # gets the animal and the auction closes (see services.start_buy_now).
    buy_now_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Fixed when the auction is created from the platform policy in settings, so changing the policy
    # later never changes what bidders on an existing auction owe.
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    winning_bid = models.OneToOneField('Bid', on_delete=models.SET_NULL, null=True, blank=True, related_name='won_auction')
    # Set instead of winning_bid when the auction closed because someone paid the buy-now price.
    winning_purchase = models.OneToOneField('BuyNowPurchase', on_delete=models.SET_NULL, null=True, blank=True, related_name='won_auction')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Auction'
        verbose_name_plural = 'Auctions'
        ordering = ['ends_at', 'id']
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(live_animal_post__isnull=False, equipment_post__isnull=True)
                    | Q(live_animal_post__isnull=True, equipment_post__isnull=False)
                ),
                name='auction_exactly_one_listing',
            ),
            models.UniqueConstraint(
                fields=['live_animal_post'], condition=Q(status='active'),
                name='one_active_auction_per_live_animal_post',
            ),
            models.UniqueConstraint(
                fields=['equipment_post'], condition=Q(status='active'),
                name='one_active_auction_per_equipment_post',
            ),
        ]

    def __str__(self):
        return f'Auction #{self.pk}: {self.post.title}'

    @property
    def post(self):
        return self.live_animal_post or self.equipment_post

    @property
    def is_open(self):
        now = timezone.now()
        return self.status == self.Status.ACTIVE and self.starts_at <= now < self.ends_at

    @property
    def highest_bid(self):
        # Every accepted bid beats the previous one, so the highest bid is also the latest.
        return self.bids.order_by('-amount', 'created_at').first()

    @property
    def current_price(self):
        highest = self.highest_bid
        return highest.amount if highest else None

    @property
    def minimum_next_bid(self):
        current = self.current_price
        return self.starting_price if current is None else current + self.min_increment

    def buy_now_open(self, current_price):
        """Whether buy-now is on offer, given the current top bid (passed in so lists can use an annotation)."""
        return (
            self.buy_now_price is not None
            and self.status == self.Status.ACTIVE
            and timezone.now() < self.ends_at
            # Once bidding reaches the seller's price, buying outright no longer makes sense.
            and (current_price is None or current_price < self.buy_now_price)
        )

    @property
    def sold_price(self):
        if self.winning_purchase_id:
            return self.winning_purchase.amount
        return self.winning_bid.amount if self.winning_bid_id else None


class Deposit(models.Model):
    """
    Money a bidder pays us before they may bid on an auction; one per bidder per auction.

    Lifecycle: PENDING (payment requested) -> HELD (paid, we hold it) -> RELEASED (refunded to a
    losing bidder, or everyone if the auction is cancelled) or CAPTURED (kept, e.g. applied to the
    winner's purchase). A payment that never completes ends up FAILED or CANCELLED.
    Status changes go through `auction.services`, which calls the configured payment gateway.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending payment'
        HELD = 'held', 'Held'
        RELEASED = 'released', 'Released'
        CAPTURED = 'captured', 'Captured'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='deposits')
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='auction_deposits')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Which gateway handled this deposit and its id for the payment there, so a webhook can find it.
    provider = models.CharField(max_length=50)
    provider_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Deposit'
        verbose_name_plural = 'Deposits'
        constraints = [
            models.UniqueConstraint(fields=['auction', 'account'], name='one_deposit_per_bidder_per_auction'),
        ]

    def __str__(self):
        return f'{self.account} · {self.amount} {self.currency} · {self.get_status_display()}'

    @property
    def payer(self):
        return self.account


class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='bids')
    bidder = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # The held deposit that allowed this bid. RESTRICT (not PROTECT) so a deposit can't be deleted on
    # its own while bids point at it, yet deleting the whole auction (or its listing) still cascades.
    deposit = models.ForeignKey(Deposit, on_delete=models.RESTRICT, related_name='bids')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bid'
        verbose_name_plural = 'Bids'
        ordering = ['-amount', 'created_at']

    def __str__(self):
        return f'{self.bidder} · {self.amount}'


class BuyNowPurchase(models.Model):
    """
    A buyer paying an auction's buy-now price in full, up front. Several buyers may be paying at once:
    the first payment to arrive wins and closes the auction; any later payment is refunded in full.

    Lifecycle: PENDING (payment requested) -> PAID (won; we hold the money until the handover) or
    REFUNDED (paid, but someone else paid first or the auction had closed). A payment that never
    arrives ends up FAILED, or CANCELLED once the auction closes without it.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending payment'
        PAID = 'paid', 'Paid (won)'
        REFUNDED = 'refunded', 'Refunded'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='purchases')
    buyer = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='buy_now_purchases')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50)
    provider_reference = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Buy-now purchase'
        verbose_name_plural = 'Buy-now purchases'
        constraints = [
            models.UniqueConstraint(
                fields=['auction'], condition=Q(status='paid'), name='one_paid_buy_now_per_auction',
            ),
            models.UniqueConstraint(
                fields=['auction', 'buyer'], condition=Q(status='pending'), name='one_pending_buy_now_per_buyer',
            ),
        ]

    def __str__(self):
        return f'{self.buyer} · {self.amount} {self.currency} · {self.get_status_display()}'

    @property
    def payer(self):
        return self.buyer


class Order(models.Model):
    """
    One sale coming out of an auction, from payment to handover. All money is held by us until the
    buyer has the animal. Created for the winning bid (the winner still owes the price minus their
    deposit), for a buy-now purchase (already paid in full), or for a runner-up offer (the seller
    offers the animal to the next-highest bidder after the winner failed to pay).

    Deadlines come from settings (ORDER_*), and `manage.py process_orders` enforces them.
    """
    class Source(models.TextChoices):
        BID = 'bid', 'Winning bid'
        BUY_NOW = 'buy_now', 'Buy now'
        RUNNER_UP = 'runner_up', 'Runner-up offer'

    class Status(models.TextChoices):
        OFFERED = 'offered', 'Offered to runner-up'            # waiting for them to accept by paying
        AWAITING_PAYMENT = 'awaiting_payment', 'Awaiting payment'  # the winner owes the balance
        PAID = 'paid', 'Paid (awaiting handover)'              # we hold the full price
        HANDED_OVER = 'handed_over', 'Handed over'             # waiting for the buyer to confirm
        COMPLETED = 'completed', 'Completed'                   # the seller is owed the payout
        DISPUTED = 'disputed', 'Problem reported'              # staff decide
        BUYER_DEFAULTED = 'buyer_defaulted', "Buyer didn't pay"  # deposit kept
        DECLINED = 'declined', 'Offer declined or expired'     # runner-up said no, or didn't answer
        SELLER_DEFAULTED = 'seller_defaulted', "Seller didn't hand over"  # buyer refunded in full
        REFUNDED = 'refunded', 'Refunded after review'

    class BalanceStatus(models.TextChoices):
        NONE = 'none', 'Nothing owed'
        PENDING = 'pending', 'Pending payment'
        PAID = 'paid', 'Paid'
        REFUNDED = 'refunded', 'Refunded'

    class RunnerUpDecision(models.TextChoices):
        OFFERED = 'offered', 'Offered'
        DECLINED = 'declined', 'Not offered'

    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='orders')
    buyer = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='orders')
    source = models.CharField(max_length=20, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    # Money already held that counts toward the price: the winner's deposit, or the buy-now payment.
    deposit = models.ForeignKey(Deposit, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    purchase = models.OneToOneField(BuyNowPurchase, on_delete=models.SET_NULL, null=True, blank=True, related_name='order')
    # What the buyer still has to pay us, and that payment's progress through the gateway.
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_status = models.CharField(max_length=20, choices=BalanceStatus.choices, default=BalanceStatus.NONE)
    provider = models.CharField(max_length=50, blank=True)
    provider_reference = models.CharField(max_length=255, blank=True)
    payment_due_at = models.DateTimeField(null=True, blank=True)
    handover_due_at = models.DateTimeField(null=True, blank=True)
    confirm_due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    paid_out_at = models.DateTimeField(null=True, blank=True, help_text='When staff paid the seller')
    handover_note = models.CharField(max_length=300, blank=True, help_text="Seller's note, e.g. courier and tracking number")
    problem_report = models.TextField(blank=True)
    # After the buyer defaults: whether the seller chose to offer the animal to the runner-up.
    runner_up_decision = models.CharField(max_length=20, choices=RunnerUpDecision.choices, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Order #{self.pk}: {self.auction.post.title} → {self.buyer} ({self.get_status_display()})'

    # The gateway collects `amount` from `payer` (see payments.PaymentGateway).
    @property
    def amount(self):
        return self.balance

    @property
    def payer(self):
        return self.buyer

    @property
    def seller(self):
        return self.auction.seller

    @property
    def payout(self):
        """What the seller receives: the price minus the marketplace fee (settings.ORDER_FEE_RATE)."""
        fee = (self.price * settings.ORDER_FEE_RATE).quantize(Decimal('0.01'))
        return self.price - fee


class SellerBond(models.Model):
    """
    Money a seller leaves with us while they sell through auctions, forfeited if they take a buyer's
    payment and never hand over the animal. Required only when settings.SELLER_BOND_AMOUNT is above 0.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending payment'
        HELD = 'held', 'Held'
        FORFEITED = 'forfeited', 'Forfeited'
        RELEASED = 'released', 'Released'
        FAILED = 'failed', 'Failed'

    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='seller_bond')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=50)
    provider_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Seller bond'
        verbose_name_plural = 'Seller bonds'

    def __str__(self):
        return f'{self.account} · {self.amount} {self.currency} · {self.get_status_display()}'

    @property
    def payer(self):
        return self.account


class Incident(models.Model):
    """
    Something an account did that staff may want to look at: starting buy-now payments and never
    paying, winning and not paying, taking payment and not handing over. Recorded automatically;
    nothing is blocked automatically. The "Accounts to review" admin page adds them up per account.
    """
    class Kind(models.TextChoices):
        UNPAID_BUY_NOW = 'unpaid_buy_now', 'Started buy-now, never paid'
        WINNER_DEFAULTED = 'winner_defaulted', "Won, didn't pay"
        SELLER_NO_SHOW = 'seller_no_show', "Seller didn't hand over"
        DISPUTE_LOST = 'dispute_lost', 'Seller lost a dispute'

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='incidents')
    kind = models.CharField(max_length=30, choices=Kind.choices)
    auction = models.ForeignKey(Auction, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Incident'
        verbose_name_plural = 'Incidents'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.account} · {self.get_kind_display()}'


class AccountToReview(Account):
    """Admin-only view of accounts with incidents (see AccountToReviewAdmin); no table of its own."""
    class Meta:
        proxy = True
        verbose_name = 'Account to review'
        verbose_name_plural = 'Accounts to review'
