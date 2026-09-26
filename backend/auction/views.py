from django.conf import settings
from django.db.models import Count, Max, Prefetch, Q
from django.utils.translation import gettext as _, gettext_lazy
from rest_framework import filters, mixins, permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
import django_filters
from django_filters.rest_framework import DjangoFilterBackend

from . import orders, services
from .models import Auction, BuyNowPurchase, Deposit, Order, SellerBond
from .serializers import (
    AuctionSerializer, BidSerializer, BuyNowPurchaseSerializer, DepositSerializer, OrderSerializer, SellerBondSerializer,
)


class CanStartAuction(permissions.BasePermission):
    """Starting an auction is behind the paywall: paid commercial accounts only."""
    message = gettext_lazy('Auctions are available to paid commercial accounts. Upgrade your account to start one.')

    def has_permission(self, request, view):
        if view.action != 'create':
            return True
        return request.user.is_authenticated and request.user.can_start_auction


class AuctionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = AuctionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanStartAuction]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'seller', 'live_animal_post', 'equipment_post']
    ordering_fields = ['ends_at', 'created_at', 'starting_price']
    ordering = ['ends_at', 'id']
    throttle_scope = None  # set per action (DRF only accepts action options that exist on the class)

    def get_queryset(self):
        queryset = Auction.objects.select_related(
            'seller', 'live_animal_post__species', 'equipment_post', 'winning_bid', 'winning_purchase',
        ).annotate(
            # distinct: the bids and purchases joins would otherwise multiply each other's counts.
            bid_count=Count('bids', distinct=True),
            top_bid=Max('bids__amount'),
            pending_buy_now=Count('purchases', filter=Q(purchases__status=BuyNowPurchase.Status.PENDING), distinct=True),
        )
        queryset = queryset.prefetch_related('orders')  # for sale_fell_through
        user = self.request.user
        # An unpublished listing (hidden by moderation, or its species under review) takes its auction
        # with it, so nobody can keep paying deposits or bidding on it; only the seller and staff still
        # see it. Every auction action looks the auction up through here.
        if not (user.is_authenticated and user.is_staff):
            hidden = (
                Q(live_animal_post__is_hidden=True) | Q(equipment_post__is_hidden=True)
                | Q(live_animal_post__isnull=False, live_animal_post__species__isnull=True)
            )
            queryset = queryset.exclude(hidden & ~Q(seller=user)) if user.is_authenticated else queryset.exclude(hidden)
        if user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch('deposits', queryset=Deposit.objects.filter(account=user), to_attr='my_deposits'),
                Prefetch(
                    'purchases', queryset=BuyNowPurchase.objects.filter(buyer=user).order_by('-created_at'),
                    to_attr='my_purchases',
                ),
            )
        return queryset

    def perform_create(self, serializer):
        try:
            services.check_can_start_auction(self.request.user)
        except services.AuctionError as error:
            raise PermissionDenied(str(error))
        serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def rules(self, request):
        """The auction settings the "start an auction" form explains and checks early (the API enforces them)."""
        return Response({
            'currency': settings.AUCTION_CURRENCY,
            'min_duration_hours': settings.AUCTION_MIN_DURATION_HOURS,
            'max_duration_days': settings.AUCTION_MAX_DURATION_DAYS,
            'deposit_rate': str(settings.AUCTION_DEPOSIT_RATE),
            'min_deposit': str(settings.AUCTION_MIN_DEPOSIT),
            'bond_required': orders.bond_required(),
            'bond_amount': str(settings.SELLER_BOND_AMOUNT),
        })

    @action(detail=False, methods=['get', 'post'], url_path='seller-bond', permission_classes=[permissions.IsAuthenticated],
            throttle_classes=[ScopedRateThrottle], throttle_scope='payments')
    def seller_bond(self, request):
        """GET: whether a bond is required and the seller's current one. POST: start paying it."""
        if request.method == 'GET':
            bond = SellerBond.objects.filter(account=request.user).first()
            return Response({
                'required': orders.bond_required(),
                'amount': str(settings.SELLER_BOND_AMOUNT),
                'currency': settings.AUCTION_CURRENCY,
                'bond': SellerBondSerializer(bond).data if bond else None,
            })
        bond, client_data = orders.request_bond(request.user)
        return Response({**SellerBondSerializer(bond).data, 'payment': client_data})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        """Auctions the current user is running as a seller."""
        queryset = self.filter_queryset(self.get_queryset().filter(seller=request.user))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel(self, request, pk=None):
        auction = self.get_object()
        if auction.seller_id != request.user.id:
            return Response(
                {'detail': _('Only the seller can cancel this auction.')},
                status=status.HTTP_403_FORBIDDEN,
            )
        services.cancel_auction(auction)
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated],
            throttle_classes=[ScopedRateThrottle], throttle_scope='payments')
    def deposit(self, request, pk=None):
        """Start paying the deposit that's required before bidding. Safe to call repeatedly."""
        auction = self.get_object()
        deposit, client_data = services.request_deposit(auction, request.user)
        return Response({**DepositSerializer(deposit).data, 'payment': client_data})

    @action(detail=True, methods=['get', 'post'])
    def bids(self, request, pk=None):
        auction = self.get_object()
        if request.method == 'GET':
            queryset = auction.bids.all()
            page = self.paginate_queryset(queryset)
            serializer = BidSerializer(page if page is not None else queryset, many=True, context=self.get_serializer_context())
            if page is not None:
                return self.get_paginated_response(serializer.data)
            return Response(serializer.data)

        serializer = BidSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        bid = services.place_bid(auction, request.user, serializer.validated_data['amount'])
        return Response(BidSerializer(bid, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='buy-now', permission_classes=[permissions.IsAuthenticated],
            throttle_classes=[ScopedRateThrottle], throttle_scope='payments')
    def buy_now(self, request, pk=None):
        """
        Pay the buy-now price in full. The auction closes when the payment arrives; if another buyer's
        payment arrives first, this one is refunded in full. Safe to call repeatedly.
        """
        auction = self.get_object()
        purchase, client_data, competing = services.start_buy_now(auction, request.user)
        return Response({
            **BuyNowPurchaseSerializer(purchase).data,
            'payment': client_data,
            'competing_buyers': competing,
        })


class OrderFilter(django_filters.FilterSet):
    # `role=buyer|seller`: which side of the sale the viewer is on (the "My orders" tabs).
    role = django_filters.ChoiceFilter(choices=[('buyer', 'buyer'), ('seller', 'seller')], method='filter_role')

    class Meta:
        model = Order
        fields = ['auction', 'status']

    def filter_role(self, queryset, name, value):
        user = self.request.user
        return queryset.filter(buyer=user) if value == 'buyer' else queryset.filter(auction__seller=user)


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Orders after a sale, visible only to their buyer and seller. `?auction=<id>` narrows the list to
    one auction (the listing page uses it); `?role=buyer|seller` to one side (the "My orders" page).
    Every action goes through auction.orders.
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter
    throttle_scope = None  # set per action

    def get_queryset(self):
        return orders.orders_for(self.request.user)

    def list(self, request, *args, **kwargs):
        # The listing page asks for an auction's order as soon as the countdown ends; close the auction
        # now rather than making the winner wait for the next close_auctions run.
        auction_id = request.query_params.get('auction')
        if auction_id and auction_id.isdigit():
            auction = Auction.objects.filter(pk=auction_id, status=Auction.Status.ACTIVE).first()
            if auction:
                services.settle_auction(auction)
        return super().list(request, *args, **kwargs)

    def _run(self, action, *args):
        order = action(self.get_object(), self.request.user, *args)
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=['post'], throttle_classes=[ScopedRateThrottle], throttle_scope='payments')
    def pay(self, request, pk=None):
        """The winner pays the rest of the price, or a runner-up accepts an offer by paying."""
        order, client_data = orders.pay_order(self.get_object(), request.user)
        return Response({**self.get_serializer(order).data, 'payment': client_data})

    @action(detail=True, methods=['post'], url_path='handed-over')
    def handed_over(self, request, pk=None):
        """Seller: the animal has been handed over or shipped (optional `note`, e.g. a tracking number)."""
        return self._run(orders.mark_handed_over, request.data.get('note', ''))

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Buyer: it arrived intact. Completes the sale."""
        return self._run(orders.confirm_received)

    @action(detail=True, methods=['post'], url_path='report-problem')
    def report_problem(self, request, pk=None):
        """Buyer: something is wrong (`text`). Freezes the money until staff decide."""
        return self._run(orders.report_problem, request.data.get('text', ''))

    @action(detail=True, methods=['post'], url_path='runner-up')
    def runner_up(self, request, pk=None):
        """Seller, after the winner defaulted: `{"offer": true}` offers the animal to the runner-up."""
        return self._run(orders.decide_runner_up, bool(request.data.get('offer')))

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        """Runner-up: turn the seller's offer down."""
        return self._run(orders.decline_offer)
