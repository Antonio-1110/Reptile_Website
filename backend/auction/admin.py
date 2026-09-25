from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Q

from . import orders, services
from .models import AccountToReview, Auction, Bid, BuyNowPurchase, Deposit, Incident, Order, SellerBond


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ('bidder', 'amount', 'created_at')
    readonly_fields = fields
    can_delete = False


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'seller', 'status', 'starting_price', 'current_price', 'ends_at')
    list_filter = ('status',)
    readonly_fields = ('winning_bid', 'winning_purchase', 'deposit_amount', 'currency')
    inlines = [BidInline]


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ('id', 'auction', 'account', 'amount', 'currency', 'status', 'provider', 'provider_reference', 'updated_at')
    list_filter = ('status', 'provider')
    search_fields = ('account__username', 'provider_reference')
    # Status only changes through the actions below, so the gateway is always told.
    readonly_fields = ('auction', 'account', 'amount', 'currency', 'status', 'provider', 'provider_reference')
    actions = ['mark_paid', 'release', 'capture']

    @admin.action(description='Mark as paid (hold the deposit)')
    def mark_paid(self, request, queryset):
        for deposit in queryset.filter(status=Deposit.Status.PENDING):
            services.confirm_deposit(deposit)

    @admin.action(description='Release (refund) held deposits')
    def release(self, request, queryset):
        for deposit in queryset.filter(status=Deposit.Status.HELD):
            services.release_deposit(deposit)

    @admin.action(description='Capture (keep) held deposits')
    def capture(self, request, queryset):
        for deposit in queryset.filter(status=Deposit.Status.HELD):
            services.capture_deposit(deposit)


@admin.register(BuyNowPurchase)
class BuyNowPurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'auction', 'buyer', 'amount', 'currency', 'status', 'provider', 'provider_reference', 'paid_at')
    list_filter = ('status', 'provider')
    search_fields = ('buyer__username', 'provider_reference')
    # Status only changes through the actions below, so the auction closes and everyone is told.
    readonly_fields = ('auction', 'buyer', 'amount', 'currency', 'status', 'provider', 'provider_reference', 'paid_at')
    actions = ['mark_paid', 'mark_failed']

    @admin.action(description='Mark as paid (first paid wins; later payments are refunded)')
    def mark_paid(self, request, queryset):
        for purchase in queryset.filter(status__in=[BuyNowPurchase.Status.PENDING, BuyNowPurchase.Status.CANCELLED]).order_by('pk'):
            services.confirm_buy_now(purchase)

    @admin.action(description='Mark as failed (never paid)')
    def mark_failed(self, request, queryset):
        for purchase in queryset.filter(status=BuyNowPurchase.Status.PENDING):
            services.fail_buy_now(purchase)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'auction', 'buyer', 'source', 'status', 'price', 'balance', 'balance_status',
                    'payment_due_at', 'handover_due_at', 'confirm_due_at', 'paid_out_at')
    list_filter = ('status', 'source', 'balance_status')
    search_fields = ('buyer__username', 'auction__seller__username', 'provider_reference')
    # Everything changes through the actions below (auction/orders.py), so deadlines, refunds and
    # emails always happen together.
    readonly_fields = [field.name for field in Order._meta.fields]
    actions = ['mark_balance_paid', 'refund_buyer', 'complete_for_seller', 'mark_paid_out']

    @admin.action(description="Mark the buyer's payment as received")
    def mark_balance_paid(self, request, queryset):
        for order in queryset.filter(balance_status=Order.BalanceStatus.PENDING):
            orders.confirm_order_payment(order)

    @admin.action(description='Dispute: refund the buyer in full')
    def refund_buyer(self, request, queryset):
        for order in queryset.filter(status=Order.Status.DISPUTED):
            orders.resolve_dispute(order, refund_buyer=True)

    @admin.action(description='Dispute: complete the sale (seller gets paid)')
    def complete_for_seller(self, request, queryset):
        for order in queryset.filter(status=Order.Status.DISPUTED):
            orders.resolve_dispute(order, refund_buyer=False)

    @admin.action(description='Mark the seller as paid out')
    def mark_paid_out(self, request, queryset):
        for order in queryset.filter(status=Order.Status.COMPLETED, paid_out_at__isnull=True):
            orders.mark_paid_out(order)


@admin.register(SellerBond)
class SellerBondAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'amount', 'currency', 'status', 'provider', 'updated_at')
    list_filter = ('status',)
    search_fields = ('account__username', 'provider_reference')
    readonly_fields = ('account', 'amount', 'currency', 'status', 'provider', 'provider_reference')
    actions = ['mark_paid', 'release']

    @admin.action(description='Mark as paid (hold the bond)')
    def mark_paid(self, request, queryset):
        for bond in queryset.filter(status=SellerBond.Status.PENDING):
            orders.confirm_bond(bond)

    @admin.action(description='Release (refund) held bonds')
    def release(self, request, queryset):
        for bond in queryset.filter(status=SellerBond.Status.HELD):
            orders.release_bond(bond)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'account', 'kind', 'auction', 'note')
    list_filter = ('kind',)
    search_fields = ('account__username', 'note')
    readonly_fields = ('account', 'kind', 'auction', 'note', 'created_at')


class AboveThresholdFilter(admin.SimpleListFilter):
    title = 'needs review'
    parameter_name = 'needs_review'

    def lookups(self, request, model_admin):
        return [('yes', f'{settings.INCIDENT_REVIEW_THRESHOLD}+ incidents')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(incident_total__gte=settings.INCIDENT_REVIEW_THRESHOLD)
        return queryset


@admin.register(AccountToReview)
class AccountToReviewAdmin(admin.ModelAdmin):
    """
    Accounts that have done something worth a look, worst first. Read-only: to act, suspend the account
    (untick "active" on the Account) or warn them yourselves.
    """
    list_display = ('username', 'email', 'needs_review', 'incident_total', 'unpaid_buy_nows',
                    'winner_defaults', 'seller_no_shows', 'disputes_lost', 'listing_reports', 'is_active')
    list_filter = (AboveThresholdFilter, 'is_active')
    search_fields = ('username', 'email')

    def get_queryset(self, request):
        kind = Incident.Kind
        return super().get_queryset(request).annotate(
            incident_total=Count('incidents', distinct=True),
            unpaid_buy_nows=Count('incidents', filter=Q(incidents__kind=kind.UNPAID_BUY_NOW), distinct=True),
            winner_defaults=Count('incidents', filter=Q(incidents__kind=kind.WINNER_DEFAULTED), distinct=True),
            seller_no_shows=Count('incidents', filter=Q(incidents__kind=kind.SELLER_NO_SHOW), distinct=True),
            disputes_lost=Count('incidents', filter=Q(incidents__kind=kind.DISPUTE_LOST), distinct=True),
            listing_reports=Count('liveanimalpost_posts__reports', distinct=True),
        ).filter(Q(incident_total__gt=0) | Q(listing_reports__gt=0)).order_by('-incident_total', '-listing_reports')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description='Needs review')
    def needs_review(self, obj):
        return obj.incident_total >= settings.INCIDENT_REVIEW_THRESHOLD

    @admin.display(ordering='incident_total', description='Incidents')
    def incident_total(self, obj):
        return obj.incident_total

    @admin.display(ordering='unpaid_buy_nows', description='Unpaid buy-nows')
    def unpaid_buy_nows(self, obj):
        return obj.unpaid_buy_nows

    @admin.display(ordering='winner_defaults', description="Won, didn't pay")
    def winner_defaults(self, obj):
        return obj.winner_defaults

    @admin.display(ordering='seller_no_shows', description="Didn't hand over")
    def seller_no_shows(self, obj):
        return obj.seller_no_shows

    @admin.display(ordering='disputes_lost', description='Disputes lost')
    def disputes_lost(self, obj):
        return obj.disputes_lost

    @admin.display(ordering='listing_reports', description='Reports on listings')
    def listing_reports(self, obj):
        return obj.listing_reports
