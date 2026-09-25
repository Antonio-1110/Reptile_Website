from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers

from post.models import EquipmentPost, LiveAnimalPost
from post.serializer import LiveAnimalPostSerializer
from . import orders
from .models import Auction, Bid, BuyNowPurchase, Deposit, Order, SellerBond
from .services import deposit_amount_for


def money(value):
    # Same "1234.50" format as the DecimalFields (SQLite returns aggregates like Max() unscaled).
    return str(Decimal(value).quantize(Decimal('0.01')))


class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = ['id', 'auction', 'amount', 'currency', 'status', 'created_at', 'updated_at']
        read_only_fields = fields


class BuyNowPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyNowPurchase
        fields = ['id', 'auction', 'amount', 'currency', 'status', 'paid_at', 'created_at']
        read_only_fields = fields


class BidSerializer(serializers.ModelSerializer):
    # Bidders are kept anonymous to each other; a bidder can still spot their own bids.
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = ['id', 'amount', 'created_at', 'is_mine']
        read_only_fields = ['id', 'created_at', 'is_mine']

    def get_is_mine(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.bidder_id == user.id


class AuctionSerializer(serializers.ModelSerializer):
    seller_id = serializers.IntegerField(source='seller.id', read_only=True)
    seller_name = serializers.CharField(source='seller.get_display_name', read_only=True)
    listing = serializers.SerializerMethodField()
    is_seller = serializers.SerializerMethodField()
    live_animal_post = serializers.PrimaryKeyRelatedField(queryset=LiveAnimalPost.objects.all(), required=False, allow_null=True)
    equipment_post = serializers.PrimaryKeyRelatedField(queryset=EquipmentPost.objects.all(), required=False, allow_null=True)
    starts_at = serializers.DateTimeField(required=False)
    is_open = serializers.BooleanField(read_only=True)
    bid_count = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    minimum_next_bid = serializers.SerializerMethodField()
    winning_bid_amount = serializers.DecimalField(source='winning_bid.amount', max_digits=10, decimal_places=2, read_only=True, default=None)
    buy_now_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=Decimal('1'))
    buy_now_available = serializers.SerializerMethodField()
    pending_buy_now_count = serializers.SerializerMethodField()
    sold_via = serializers.SerializerMethodField()
    sold_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    # The auction sold but the sale fell through (see orders.sale_fell_through): show it as unsold.
    sale_fell_through = serializers.SerializerMethodField()
    my_deposit = serializers.SerializerMethodField()
    my_purchase = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = [
            'id', 'seller_id', 'seller_name', 'is_seller', 'live_animal_post', 'equipment_post', 'listing',
            'starting_price', 'min_increment', 'deposit_amount', 'currency', 'starts_at', 'ends_at',
            'status', 'is_open', 'bid_count', 'current_price', 'minimum_next_bid', 'winning_bid_amount',
            'buy_now_price', 'buy_now_available', 'pending_buy_now_count', 'sold_via', 'sold_price', 'sale_fell_through',
            'my_deposit', 'my_purchase', 'created_at',
        ]
        read_only_fields = ['id', 'deposit_amount', 'currency', 'status', 'created_at']
        extra_kwargs = {
            'starting_price': {'min_value': Decimal('1')},
            'min_increment': {'min_value': Decimal('1')},
        }

    def get_listing(self, obj):
        # Enough of the listing to draw an auction card; the full listing (description, care notes,
        # gallery) comes from the listing endpoints. Contact details are never included.
        post = obj.post
        summary = {
            'id': post.id,
            'category': 'live_animal' if obj.live_animal_post_id else 'equipment',
            'title': post.title,
            'image': post.image,
            'location': post.location,
        }
        if obj.live_animal_post_id:
            summary.update({
                'species_name': post.species.name,
                'sex': post.sex,
                'life_stage': post.life_stage,
                'genes': LiveAnimalPostSerializer().get_genes(post),
            })
        return summary

    def get_is_seller(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.seller_id == user.id

    # bid_count / top_bid / my_deposits are annotated or prefetched by AuctionViewSet.get_queryset();
    # the fallbacks cover freshly created instances.
    def get_bid_count(self, obj):
        return obj.bid_count if hasattr(obj, 'bid_count') else obj.bids.count()

    def get_current_price(self, obj):
        top_bid = self._top_bid(obj)
        return None if top_bid is None else money(top_bid)

    def get_minimum_next_bid(self, obj):
        top_bid = self._top_bid(obj)
        return money(obj.starting_price if top_bid is None else top_bid + obj.min_increment)

    @staticmethod
    def _top_bid(obj):
        return obj.top_bid if hasattr(obj, 'top_bid') else obj.current_price

    def get_buy_now_available(self, obj):
        top_bid = self._top_bid(obj)
        return obj.buy_now_open(None if top_bid is None else Decimal(top_bid))

    def get_pending_buy_now_count(self, obj):
        # How many buyers are paying the buy-now price right now, so the page can warn that it's a race.
        if hasattr(obj, 'pending_buy_now'):
            return obj.pending_buy_now
        return obj.purchases.filter(status=BuyNowPurchase.Status.PENDING).count()

    def get_sale_fell_through(self, obj):
        if obj.status != Auction.Status.ENDED or not (obj.winning_bid_id or obj.winning_purchase_id):
            return False
        return orders.sale_fell_through(obj)

    def get_sold_via(self, obj):
        if obj.winning_purchase_id:
            return 'buy_now'
        return 'bid' if obj.winning_bid_id else None

    def get_my_purchase(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return None
        if hasattr(obj, 'my_purchases'):
            purchase = obj.my_purchases[0] if obj.my_purchases else None
        else:
            purchase = obj.purchases.filter(buyer=user).order_by('-created_at').first()
        return BuyNowPurchaseSerializer(purchase).data if purchase else None

    def get_my_deposit(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return None
        if hasattr(obj, 'my_deposits'):
            deposit = obj.my_deposits[0] if obj.my_deposits else None
        else:
            deposit = obj.deposits.filter(account=user).first()
        return DepositSerializer(deposit).data if deposit else None

    def validate(self, attrs):
        user = self.context['request'].user
        live_animal_post = attrs.get('live_animal_post')
        equipment_post = attrs.get('equipment_post')

        if bool(live_animal_post) == bool(equipment_post):
            raise serializers.ValidationError({
                'detail': _('Choose exactly one listing to auction.'),
            })
        post = live_animal_post or equipment_post
        if post.account_id != user.id:
            raise serializers.ValidationError({
                'detail': _('You can only auction your own listings.'),
            })
        listing_filter = {'live_animal_post': post} if live_animal_post else {'equipment_post': post}
        if Auction.objects.filter(status=Auction.Status.ACTIVE, **listing_filter).exists():
            raise serializers.ValidationError({
                'detail': _('This listing already has an active auction.'),
            })

        buy_now_price = attrs.get('buy_now_price')
        if buy_now_price is not None and buy_now_price <= attrs['starting_price']:
            raise serializers.ValidationError({
                'buy_now_price': _('The buy-now price must be higher than the starting price.'),
            })

        now = timezone.now()
        starts_at = attrs.setdefault('starts_at', now)
        ends_at = attrs['ends_at']
        if starts_at < now - timedelta(minutes=5):
            raise serializers.ValidationError({'starts_at': _("An auction can't start in the past.")})
        if ends_at - starts_at < timedelta(hours=settings.AUCTION_MIN_DURATION_HOURS):
            raise serializers.ValidationError({
                'ends_at': _('An auction must run for at least %(hours)s hours.') % {'hours': settings.AUCTION_MIN_DURATION_HOURS},
            })
        if ends_at - starts_at > timedelta(days=settings.AUCTION_MAX_DURATION_DAYS):
            raise serializers.ValidationError({
                'ends_at': _('An auction can run for at most %(days)s days.') % {'days': settings.AUCTION_MAX_DURATION_DAYS},
            })
        return attrs

    def create(self, validated_data):
        validated_data['seller'] = self.context['request'].user
        validated_data['deposit_amount'] = deposit_amount_for(validated_data['starting_price'])
        validated_data['currency'] = settings.AUCTION_CURRENCY
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    """An order as its buyer or seller sees it (nobody else can). `role` says which one is looking."""
    listing = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    deposit_amount = serializers.DecimalField(source='deposit.amount', max_digits=10, decimal_places=2, read_only=True, default=None)
    payout = serializers.SerializerMethodField()
    runner_up_amount = serializers.SerializerMethodField()
    counterpart = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'auction', 'listing', 'role', 'source', 'status', 'price', 'currency', 'deposit_amount',
            'balance', 'balance_status', 'payout', 'payment_due_at', 'handover_due_at', 'confirm_due_at',
            'paid_at', 'handed_over_at', 'completed_at', 'handover_note', 'problem_report',
            'runner_up_decision', 'runner_up_amount', 'counterpart', 'created_at',
        ]
        read_only_fields = fields

    def _viewer(self):
        return self.context['request'].user

    def get_listing(self, obj):
        post = obj.auction.post
        return {'id': post.id, 'title': post.title, 'category': 'live_animal' if obj.auction.live_animal_post_id else 'equipment'}

    def get_role(self, obj):
        return 'buyer' if obj.buyer_id == self._viewer().id else 'seller'

    def get_payout(self, obj):
        # The seller's figure only.
        return money(obj.payout) if obj.auction.seller_id == self._viewer().id else None

    def get_runner_up_amount(self, obj):
        # Shown to the seller while they decide whether to offer the animal to the runner-up.
        if obj.auction.seller_id != self._viewer().id or obj.status != Order.Status.BUYER_DEFAULTED or obj.runner_up_decision:
            return None
        bid = orders.runner_up_bid(obj)
        return money(bid.amount) if bid else None

    def get_counterpart(self, obj):
        return orders.counterpart_contact(obj, self._viewer())


class SellerBondSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerBond
        fields = ['id', 'amount', 'currency', 'status', 'created_at', 'updated_at']
        read_only_fields = fields
