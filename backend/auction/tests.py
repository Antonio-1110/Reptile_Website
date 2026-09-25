from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from account.models import Account
from post.models import EquipmentPost, LiveAnimalPost, Species
from . import services
from . import orders
from .models import Auction, BuyNowPurchase, Deposit, Incident, Order, SellerBond

INSTANT = 'auction.payments.InstantPaymentGateway'
MANUAL = 'auction.payments.ManualPaymentGateway'


def make_account(username, **fields):
    return Account.objects.create_user(username=username, email=f'{username}@example.com', password='pass1234', **fields)


class AuctionTestCase(APITestCase):
    def setUp(self):
        self.seller = make_account('seller', account_type='commercial', is_paid_account=True)
        self.buyer = make_account('buyer')
        self.other_buyer = make_account('other_buyer')
        self.species = Species.objects.create(name='Ball Pythons')
        self.listing = LiveAnimalPost.objects.create(
            account=self.seller, species=self.species, title='Pied Ball Python',
            description='Healthy animal', contact_info='{}',
        )

    def auction_payload(self, **overrides):
        payload = {
            'live_animal_post': self.listing.id,
            'starting_price': '5000.00',
            'min_increment': '100.00',
            'ends_at': (timezone.now() + timedelta(days=3)).isoformat(),
        }
        payload.update(overrides)
        return payload

    def create_auction(self, **overrides):
        fields = {
            'seller': self.seller, 'live_animal_post': self.listing,
            'starting_price': Decimal('5000.00'), 'min_increment': Decimal('100.00'),
            'deposit_amount': Decimal('500.00'), 'currency': 'TWD',
            'starts_at': timezone.now() - timedelta(minutes=1),
            'ends_at': timezone.now() + timedelta(days=3),
        }
        fields.update(overrides)
        return Auction.objects.create(**fields)

    def bid(self, auction, user, amount):
        self.client.force_authenticate(user)
        return self.client.post(reverse('auction-bids', args=[auction.id]), {'amount': amount}, format='json')

    def pay_deposit(self, auction, user):
        self.client.force_authenticate(user)
        return self.client.post(reverse('auction-deposit', args=[auction.id]))


class StartAuctionTests(AuctionTestCase):
    def test_hobbyist_cannot_start_auction(self):
        self.seller.account_type = 'hobbyist'
        self.seller.save()
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 403)

    def test_unpaid_commercial_account_cannot_start_auction(self):
        self.seller.is_paid_account = False
        self.seller.save()
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('paid commercial', str(response.data))

    def test_paid_commercial_account_can_start_auction(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['deposit_amount'], '500.00')
        self.assertEqual(response.data['currency'], 'TWD')
        self.assertEqual(response.data['minimum_next_bid'], '5000.00')
        self.assertTrue(response.data['is_open'])
        self.assertTrue(response.data['is_seller'])
        self.assertEqual(response.data['listing']['title'], 'Pied Ball Python')
        self.assertEqual(response.data['listing']['category'], 'live_animal')

    def test_deposit_never_falls_below_minimum(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(starting_price='300.00'), format='json')
        self.assertEqual(response.data['deposit_amount'], '100.00')

    def test_seller_cannot_auction_someone_elses_listing(self):
        other_seller = make_account('other_seller', account_type='commercial', is_paid_account=True)
        self.client.force_authenticate(other_seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 400)

    def test_listing_cannot_have_two_active_auctions(self):
        self.create_auction()
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 400)

    def test_must_choose_exactly_one_listing(self):
        equipment = EquipmentPost.objects.create(account=self.seller, title='Tank', description='40 gal', contact_info='{}')
        self.client.force_authenticate(self.seller)
        response = self.client.post(
            reverse('auction-list'), self.auction_payload(equipment_post=equipment.id), format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_auction_duration_is_limited(self):
        self.client.force_authenticate(self.seller)
        too_long = (timezone.now() + timedelta(days=31)).isoformat()
        response = self.client.post(reverse('auction-list'), self.auction_payload(ends_at=too_long), format='json')
        self.assertEqual(response.status_code, 400)

    def test_anyone_can_browse_auctions(self):
        self.create_auction()
        response = self.client.get(reverse('auction-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        result = response.data['results'][0]
        self.assertIsNone(result['my_deposit'])
        self.assertFalse(result['is_seller'])
        self.assertEqual(result['listing']['species_name'], 'Ball Pythons')
        self.assertNotIn('contact_info', result['listing'])
        self.assertIsNone(result['buy_now_price'])
        self.assertFalse(result['buy_now_available'])

    def test_auction_list_query_count_does_not_grow_with_auctions(self):
        self.create_auction()
        for index in range(3):
            listing = LiveAnimalPost.objects.create(
                account=self.seller, species=self.species, title=f'Extra {index}',
                description='Healthy animal', contact_info='{}',
            )
            self.create_auction(live_animal_post=listing)
        self.client.force_authenticate(self.buyer)
        with self.assertNumQueries(4):  # page count, auctions with their listings, the viewer's deposits and purchases
            self.client.get(reverse('auction-list'))


@override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
class BiddingTests(AuctionTestCase):
    def test_cannot_bid_without_deposit(self):
        auction = self.create_auction()
        response = self.bid(auction, self.buyer, '5000.00')
        self.assertEqual(response.status_code, 400)
        self.assertIn('deposit', response.data['detail'])

    def test_seller_cannot_pay_deposit_or_bid_on_own_auction(self):
        auction = self.create_auction()
        self.assertEqual(self.pay_deposit(auction, self.seller).status_code, 400)
        self.assertEqual(self.bid(auction, self.seller, '5000.00').status_code, 400)

    def test_anonymous_user_cannot_bid(self):
        auction = self.create_auction()
        response = self.client.post(reverse('auction-bids', args=[auction.id]), {'amount': '5000.00'}, format='json')
        self.assertIn(response.status_code, (401, 403))

    def test_deposit_then_bid(self):
        auction = self.create_auction()
        response = self.pay_deposit(auction, self.buyer)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'held')
        self.assertEqual(response.data['amount'], '500.00')

        response = self.bid(auction, self.buyer, '4999.00')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], 'Your bid must be at least TWD 5,000.')
        response = self.bid(auction, self.buyer, '5000.00')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_mine'])

        detail = self.client.get(reverse('auction-detail', args=[auction.id])).data
        self.assertEqual(detail['current_price'], '5000.00')
        self.assertEqual(detail['minimum_next_bid'], '5100.00')
        self.assertEqual(detail['bid_count'], 1)
        self.assertEqual(detail['my_deposit']['status'], 'held')

    def test_next_bid_must_beat_current_price_by_increment(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        self.pay_deposit(auction, self.other_buyer)
        self.bid(auction, self.buyer, '5000.00')
        self.assertEqual(self.bid(auction, self.other_buyer, '5050.00').status_code, 400)
        self.assertEqual(self.bid(auction, self.other_buyer, '5100.00').status_code, 201)

    def test_paying_deposit_twice_reuses_the_same_deposit(self):
        auction = self.create_auction()
        first = self.pay_deposit(auction, self.buyer).data
        second = self.pay_deposit(auction, self.buyer).data
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(Deposit.objects.count(), 1)

    def test_cannot_bid_after_auction_ends(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        Auction.objects.filter(pk=auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.bid(auction, self.buyer, '5000.00').status_code, 400)

    def test_cannot_bid_before_auction_starts(self):
        auction = self.create_auction(starts_at=timezone.now() + timedelta(hours=1))
        self.pay_deposit(auction, self.buyer)
        self.assertEqual(self.bid(auction, self.buyer, '5000.00').status_code, 400)

    def test_bid_history_hides_other_bidders(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        self.bid(auction, self.buyer, '5000.00')
        self.client.force_authenticate(self.other_buyer)
        response = self.client.get(reverse('auction-bids', args=[auction.id]))
        bid = response.data['results'][0]
        self.assertEqual(bid['amount'], '5000.00')
        self.assertFalse(bid['is_mine'])
        self.assertNotIn('bidder', bid)


@override_settings(AUCTION_PAYMENT_GATEWAY=MANUAL)
class ManualDepositTests(AuctionTestCase):
    def test_deposit_stays_pending_until_confirmed(self):
        auction = self.create_auction()
        response = self.pay_deposit(auction, self.buyer)
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(self.bid(auction, self.buyer, '5000.00').status_code, 400)

        services.confirm_deposit(Deposit.objects.get(pk=response.data['id']))
        self.assertEqual(self.bid(auction, self.buyer, '5000.00').status_code, 201)

    def test_failed_deposit_can_be_retried(self):
        auction = self.create_auction()
        deposit_id = self.pay_deposit(auction, self.buyer).data['id']
        services.fail_deposit(Deposit.objects.get(pk=deposit_id))
        response = self.pay_deposit(auction, self.buyer)
        self.assertEqual(response.data['id'], deposit_id)
        self.assertEqual(response.data['status'], 'pending')

    def test_deposit_paid_after_auction_closed_is_released(self):
        auction = self.create_auction()
        deposit = Deposit.objects.get(pk=self.pay_deposit(auction, self.buyer).data['id'])
        Auction.objects.filter(pk=auction.pk).update(status=Auction.Status.CANCELLED)
        self.assertEqual(services.confirm_deposit(deposit).status, Deposit.Status.RELEASED)


@override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
class CloseAuctionTests(AuctionTestCase):
    def test_settling_keeps_winner_deposit_and_releases_the_rest(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        self.pay_deposit(auction, self.other_buyer)
        self.bid(auction, self.buyer, '5000.00')
        self.bid(auction, self.other_buyer, '5100.00')
        Auction.objects.filter(pk=auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))

        call_command('close_auctions', stdout=open('/dev/null', 'w'))

        auction.refresh_from_db()
        self.assertEqual(auction.status, Auction.Status.ENDED)
        self.assertEqual(auction.winning_bid.bidder, self.other_buyer)
        self.assertEqual(auction.deposits.get(account=self.other_buyer).status, Deposit.Status.HELD)
        self.assertEqual(auction.deposits.get(account=self.buyer).status, Deposit.Status.RELEASED)

    def test_settling_does_not_touch_running_auctions(self):
        auction = self.create_auction()
        services.settle_due_auctions()
        auction.refresh_from_db()
        self.assertEqual(auction.status, Auction.Status.ACTIVE)

    def test_seller_can_cancel_auction_without_bids(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-cancel', args=[auction.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'cancelled')
        self.assertEqual(auction.deposits.get(account=self.buyer).status, Deposit.Status.RELEASED)

    def test_seller_cannot_cancel_auction_with_bids(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        self.bid(auction, self.buyer, '5000.00')
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-cancel', args=[auction.id]))
        self.assertEqual(response.status_code, 400)

    def test_only_seller_can_cancel(self):
        auction = self.create_auction()
        self.client.force_authenticate(self.buyer)
        response = self.client.post(reverse('auction-cancel', args=[auction.id]))
        self.assertEqual(response.status_code, 403)

    def test_new_auction_allowed_after_previous_one_is_cancelled(self):
        auction = self.create_auction()
        services.cancel_auction(auction)
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 201)

    def test_deleting_a_listing_removes_its_auction_bids_and_deposits(self):
        auction = self.create_auction()
        self.pay_deposit(auction, self.buyer)
        self.bid(auction, self.buyer, '5000.00')
        self.listing.delete()
        self.assertFalse(Auction.objects.exists())
        self.assertFalse(Deposit.objects.exists())


class BuyNowTests(AuctionTestCase):
    def setUp(self):
        super().setUp()
        self.seller.phone_number = '0911000111'
        self.seller.save()
        self.buyer.phone_number = '0922000222'
        self.buyer.save()

    def buy_now(self, auction, user):
        self.client.force_authenticate(user)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('auction-buy-now', args=[auction.id]))

    def test_seller_can_offer_a_buy_now_price_above_the_starting_price(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(buy_now_price='16000.00'), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['buy_now_price'], '16000.00')
        self.assertTrue(response.data['buy_now_available'])

        Auction.objects.all().delete()
        response = self.client.post(reverse('auction-list'), self.auction_payload(buy_now_price='5000.00'), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('buy_now_price', response.data)

    def test_buy_now_needs_a_buy_now_price(self):
        auction = self.create_auction()
        self.assertEqual(self.buy_now(auction, self.buyer).status_code, 400)

    def test_seller_cannot_buy_their_own_animal(self):
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        self.assertEqual(self.buy_now(auction, self.seller).status_code, 400)

    @override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
    def test_paying_the_buy_now_price_closes_the_auction_and_refunds_bidders(self):
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        self.pay_deposit(auction, self.other_buyer)
        self.bid(auction, self.other_buyer, '5000.00')
        mail.outbox.clear()

        response = self.buy_now(auction, self.buyer)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'paid')
        auction.refresh_from_db()
        self.assertEqual(auction.status, Auction.Status.ENDED)
        self.assertEqual(auction.winning_purchase.buyer, self.buyer)
        self.assertIsNone(auction.winning_bid)
        self.assertEqual(auction.deposits.get(account=self.other_buyer).status, Deposit.Status.RELEASED)
        self.assertEqual(self.bid(auction, self.other_buyer, '6000.00').status_code, 400)

        emails = {message.to[0]: message.body for message in mail.outbox}
        self.assertIn('0911000111', emails['buyer@example.com'])  # the buyer gets the seller's details
        self.assertIn('0922000222', emails['seller@example.com'])  # and the seller gets the buyer's
        self.assertIn('refunded in full', emails['other_buyer@example.com'])

        detail = self.client.get(reverse('auction-detail', args=[auction.id])).data
        self.assertEqual(detail['sold_via'], 'buy_now')
        self.assertEqual(detail['sold_price'], '16000.00')

    @override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
    def test_buy_now_goes_away_once_bidding_reaches_its_price(self):
        auction = self.create_auction(buy_now_price=Decimal('6000'))
        self.pay_deposit(auction, self.other_buyer)
        self.bid(auction, self.other_buyer, '6000.00')
        self.assertFalse(self.client.get(reverse('auction-detail', args=[auction.id])).data['buy_now_available'])
        self.assertEqual(self.buy_now(auction, self.buyer).status_code, 400)

    @override_settings(AUCTION_PAYMENT_GATEWAY=MANUAL)
    def test_first_payment_to_arrive_wins_and_later_ones_are_refunded(self):
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        first = self.buy_now(auction, self.buyer)
        mail.outbox.clear()
        second = self.buy_now(auction, self.other_buyer)

        self.assertEqual(first.data['status'], 'pending')
        self.assertEqual(second.data['competing_buyers'], 1)
        # Both buyers and the seller hear that it's a race.
        self.assertEqual(sorted(message.to[0] for message in mail.outbox),
                         ['buyer@example.com', 'other_buyer@example.com', 'seller@example.com'])

        # The second buyer's money arrives first.
        with self.captureOnCommitCallbacks(execute=True):
            services.confirm_buy_now(BuyNowPurchase.objects.get(pk=second.data['id']))
        auction.refresh_from_db()
        self.assertEqual(auction.winning_purchase.buyer, self.other_buyer)
        late = BuyNowPurchase.objects.get(pk=first.data['id'])
        self.assertEqual(late.status, BuyNowPurchase.Status.CANCELLED)

        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            services.confirm_buy_now(late)
        late.refresh_from_db()
        self.assertEqual(late.status, BuyNowPurchase.Status.REFUNDED)
        self.assertEqual(mail.outbox[0].to, ['buyer@example.com'])
        self.assertIn('refunded to you in full', mail.outbox[0].body)

    @override_settings(AUCTION_PAYMENT_GATEWAY=MANUAL)
    def test_repeat_buy_now_clicks_reuse_the_pending_payment(self):
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        first = self.buy_now(auction, self.buyer).data
        second = self.buy_now(auction, self.buyer).data
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(BuyNowPurchase.objects.count(), 1)


@override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
class OrderTests(AuctionTestCase):
    """The winner's journey after an auction ends: pay, hand over, confirm, and every way it falls through."""

    def setUp(self):
        super().setUp()
        self.seller.phone_number = '0911000111'
        self.seller.save()
        self.buyer.phone_number = '0922000222'
        self.buyer.save()
        self.auction = self.create_auction()
        self.pay_deposit(self.auction, self.other_buyer)
        self.bid(self.auction, self.other_buyer, '5000.00')
        self.pay_deposit(self.auction, self.buyer)
        self.bid(self.auction, self.buyer, '5100.00')
        Auction.objects.filter(pk=self.auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            services.settle_due_auctions()
        self.order = Order.objects.get(auction=self.auction)

    def order_url(self, name='detail', order=None):
        return reverse(f'order-{name}', args=[(order or self.order).id])

    def act(self, user, name, data=None, order=None):
        self.client.force_authenticate(user)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(self.order_url(name, order), data or {}, format='json')

    def pass_deadline(self, field, order=None):
        Order.objects.filter(pk=(order or self.order).pk).update(**{field: timezone.now() - timedelta(seconds=1)})
        with self.captureOnCommitCallbacks(execute=True):
            orders.process_due_orders()
        self.order.refresh_from_db()

    def test_winning_creates_an_order_for_the_rest_of_the_price(self):
        self.assertEqual(self.order.buyer, self.buyer)
        self.assertEqual(self.order.status, Order.Status.AWAITING_PAYMENT)
        self.assertEqual(self.order.price, Decimal('5100.00'))
        self.assertEqual(self.order.balance, Decimal('4600.00'))  # minus the NT$500 deposit
        hours = (self.order.payment_due_at - timezone.now()).total_seconds() / 3600
        self.assertAlmostEqual(hours, settings.ORDER_PAYMENT_HOURS, delta=0.1)
        emails = {message.to[0]: message.body for message in mail.outbox}
        self.assertIn('4,600', emails['buyer@example.com'])
        self.assertIn('0911000111', emails['buyer@example.com'])
        self.assertIn('0922000222', emails['seller@example.com'])
        self.assertIn('refunded in full', emails['other_buyer@example.com'])

    def test_asking_for_an_auctions_order_closes_it_if_its_time_is_up(self):
        auction = self.create_auction(live_animal_post=LiveAnimalPost.objects.create(
            account=self.seller, species=self.species, title='Second', description='-', contact_info='{}',
        ))
        self.pay_deposit(auction, self.buyer)
        self.bid(auction, self.buyer, '5000.00')
        Auction.objects.filter(pk=auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
        self.client.force_authenticate(self.buyer)
        results = self.client.get(reverse('order-list'), {'auction': auction.id}).data['results']
        self.assertEqual(results[0]['status'], 'awaiting_payment')

    def test_only_the_buyer_and_seller_can_see_the_order(self):
        self.client.force_authenticate(self.buyer)
        mine = self.client.get(reverse('order-list'), {'auction': self.auction.id}).data['results']
        self.assertEqual(mine[0]['role'], 'buyer')
        self.assertEqual(mine[0]['counterpart']['phone'], '0911000111')
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.get(self.order_url()).data['counterpart']['phone'], '0922000222')
        self.client.force_authenticate(self.other_buyer)
        self.assertEqual(self.client.get(reverse('order-list')).data['count'], 0)
        self.assertEqual(self.client.get(self.order_url()).status_code, 404)

    def test_happy_path_pay_hand_over_confirm(self):
        response = self.act(self.buyer, 'pay')
        self.assertEqual(response.data['status'], 'paid', response.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.deposit.status, Deposit.Status.CAPTURED)  # counts toward the price
        self.assertIsNotNone(self.order.handover_due_at)

        self.assertEqual(self.act(self.buyer, 'handed-over').status_code, 400)  # only the seller can
        response = self.act(self.seller, 'handed-over', {'note': 'Blackcat 1234'})
        self.assertEqual(response.data['status'], 'handed_over')
        self.assertIn('Blackcat 1234', mail.outbox[-1].body)

        self.assertEqual(self.act(self.seller, 'confirm').status_code, 400)  # only the buyer can
        response = self.act(self.buyer, 'confirm')
        self.assertEqual(response.data['status'], 'completed')

    @override_settings(ORDER_FEE_RATE=Decimal('0.05'))
    def test_seller_payout_is_the_price_minus_the_fee(self):
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.get(self.order_url()).data['payout'], '4845.00')
        self.client.force_authenticate(self.buyer)
        self.assertIsNone(self.client.get(self.order_url()).data['payout'])

    def test_winner_who_does_not_pay_loses_the_deposit_and_seller_may_offer_the_runner_up(self):
        self.pass_deadline('payment_due_at')
        self.assertEqual(self.order.status, Order.Status.BUYER_DEFAULTED)
        self.assertEqual(self.order.deposit.status, Deposit.Status.CAPTURED)
        self.assertTrue(Incident.objects.filter(account=self.buyer, kind=Incident.Kind.WINNER_DEFAULTED).exists())
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.get(self.order_url()).data['runner_up_amount'], '5000.00')

        response = self.act(self.seller, 'runner-up', {'offer': True})
        self.assertEqual(response.status_code, 200, response.data)
        offer = Order.objects.get(source=Order.Source.RUNNER_UP)
        self.assertEqual((offer.buyer, offer.status, offer.price), (self.other_buyer, Order.Status.OFFERED, Decimal('5000.00')))
        self.assertEqual(mail.outbox[-1].to, ['other_buyer@example.com'])

        # The runner-up sees no contact details until they pay; then it's a normal paid order.
        self.client.force_authenticate(self.other_buyer)
        self.assertIsNone(self.client.get(self.order_url(order=offer)).data['counterpart'])
        self.assertEqual(self.act(self.other_buyer, 'pay', order=offer).data['status'], 'paid')

    def test_runner_up_can_decline_without_penalty(self):
        self.pass_deadline('payment_due_at')
        self.act(self.seller, 'runner-up', {'offer': True})
        offer = Order.objects.get(source=Order.Source.RUNNER_UP)
        self.assertEqual(self.act(self.other_buyer, 'decline', order=offer).data['status'], 'declined')
        self.assertFalse(Incident.objects.filter(account=self.other_buyer).exists())

    def test_runner_up_offer_lapses(self):
        self.pass_deadline('payment_due_at')
        self.act(self.seller, 'runner-up', {'offer': True})
        offer = Order.objects.get(source=Order.Source.RUNNER_UP)
        self.pass_deadline('payment_due_at', order=offer)
        offer.refresh_from_db()
        self.assertEqual(offer.status, Order.Status.DECLINED)

    def test_seller_may_decline_to_offer_the_runner_up(self):
        self.pass_deadline('payment_due_at')
        response = self.act(self.seller, 'runner-up', {'offer': False})
        self.assertEqual(response.data['runner_up_decision'], 'declined')
        self.assertFalse(Order.objects.filter(source=Order.Source.RUNNER_UP).exists())

    def test_seller_who_never_hands_over_refunds_the_buyer_and_is_recorded(self):
        self.act(self.buyer, 'pay')
        self.pass_deadline('handover_due_at')
        self.assertEqual(self.order.status, Order.Status.SELLER_DEFAULTED)
        self.assertEqual(self.order.deposit.status, Deposit.Status.RELEASED)
        self.assertEqual(self.order.balance_status, Order.BalanceStatus.REFUNDED)
        self.assertTrue(Incident.objects.filter(account=self.seller, kind=Incident.Kind.SELLER_NO_SHOW).exists())

    def test_sale_completes_if_the_buyer_does_not_confirm_in_time(self):
        self.act(self.buyer, 'pay')
        self.act(self.seller, 'handed-over')
        self.pass_deadline('confirm_due_at')
        self.assertEqual(self.order.status, Order.Status.COMPLETED)

    def test_reported_problem_freezes_the_money_until_staff_decide(self):
        self.act(self.buyer, 'pay')
        self.act(self.seller, 'handed-over')
        self.assertEqual(self.act(self.buyer, 'report-problem', {'text': ''}).status_code, 400)
        response = self.act(self.buyer, 'report-problem', {'text': 'Arrived with a mouth infection'})
        self.assertEqual(response.data['status'], 'disputed')
        self.pass_deadline('confirm_due_at')  # deadlines don't apply while disputed
        self.assertEqual(self.order.status, Order.Status.DISPUTED)

        with self.captureOnCommitCallbacks(execute=True):
            orders.resolve_dispute(self.order, refund_buyer=True)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REFUNDED)
        self.assertEqual(self.order.balance_status, Order.BalanceStatus.REFUNDED)
        self.assertTrue(Incident.objects.filter(account=self.seller, kind=Incident.Kind.DISPUTE_LOST).exists())

    @override_settings(AUCTION_PAYMENT_GATEWAY=MANUAL)
    def test_payment_that_arrives_after_the_deadline_is_refunded(self):
        self.act(self.buyer, 'pay')  # manual gateway: stays pending
        self.pass_deadline('payment_due_at')
        with self.captureOnCommitCallbacks(execute=True):
            orders.confirm_order_payment(self.order)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.BUYER_DEFAULTED)
        self.assertEqual(self.order.balance_status, Order.BalanceStatus.REFUNDED)

    def test_process_orders_command(self):
        Order.objects.filter(pk=self.order.pk).update(payment_due_at=timezone.now() - timedelta(seconds=1))
        call_command('process_orders', stdout=open('/dev/null', 'w'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.BUYER_DEFAULTED)


@override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
class EquipmentSaleWordingTests(AuctionTestCase):
    """Equipment can be auctioned too; its emails and errors mustn't talk about an animal."""

    def setUp(self):
        super().setUp()
        self.gear = EquipmentPost.objects.create(account=self.seller, title='Heat Lamp', description='d', contact_info='{}')

    def buy_now(self, auction, user):
        self.client.force_authenticate(user)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse('auction-buy-now', args=[auction.id]))

    def test_equipment_sale_emails_do_not_mention_an_animal(self):
        auction = self.create_auction(live_animal_post=None, equipment_post=self.gear, buy_now_price=Decimal('9000.00'))
        mail.outbox.clear()
        self.assertEqual(self.buy_now(auction, self.buyer).status_code, 200)
        order = Order.objects.get(auction=auction)
        with self.captureOnCommitCallbacks(execute=True):
            orders.mark_handed_over(order, self.seller, note='')
        bodies = [message.body for message in mail.outbox]
        self.assertGreaterEqual(len(bodies), 3)
        for body in bodies:
            self.assertNotIn('animal', body)
            self.assertNotIn('個體', body)
        self.assertTrue(any('the item is yours' in body for body in bodies))

    def test_animal_sale_emails_keep_their_wording(self):
        auction = self.create_auction(buy_now_price=Decimal('9000.00'))
        mail.outbox.clear()
        self.buy_now(auction, self.buyer)
        self.assertTrue(any('the animal is yours' in message.body for message in mail.outbox))

    def test_seller_cannot_buy_own_equipment(self):
        auction = self.create_auction(live_animal_post=None, equipment_post=self.gear, buy_now_price=Decimal('9000.00'))
        response = self.buy_now(auction, self.seller)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['detail'], "You can't buy your own item.")


@override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT)
class BuyNowOrderTests(AuctionTestCase):
    def test_buy_now_creates_a_paid_order_waiting_for_the_handover(self):
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        self.client.force_authenticate(self.buyer)
        self.client.post(reverse('auction-buy-now', args=[auction.id]))
        order = Order.objects.get(auction=auction)
        self.assertEqual((order.source, order.status, order.price), (Order.Source.BUY_NOW, Order.Status.PAID, Decimal('16000')))
        self.assertIsNotNone(order.handover_due_at)

    @override_settings(AUCTION_PAYMENT_GATEWAY=MANUAL)
    def test_buy_now_payments_that_never_arrive_are_recorded(self):
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        self.client.force_authenticate(self.buyer)
        purchase_id = self.client.post(reverse('auction-buy-now', args=[auction.id])).data['id']
        services.fail_buy_now(BuyNowPurchase.objects.get(pk=purchase_id))
        self.client.force_authenticate(self.other_buyer)
        self.client.post(reverse('auction-buy-now', args=[auction.id]))
        services.cancel_auction(auction)
        kinds = list(Incident.objects.values_list('account__username', 'kind'))
        self.assertIn(('buyer', Incident.Kind.UNPAID_BUY_NOW), kinds)
        self.assertIn(('other_buyer', Incident.Kind.UNPAID_BUY_NOW), kinds)


@override_settings(AUCTION_PAYMENT_GATEWAY=INSTANT, SELLER_BOND_AMOUNT=Decimal('3000'))
class SellerBondTests(AuctionTestCase):
    def test_bond_is_required_before_starting_an_auction_when_configured(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('seller bond', response.data['detail'])

        bond = self.client.post(reverse('auction-seller-bond'))
        self.assertEqual(bond.data['status'], 'held')
        self.assertEqual(bond.data['amount'], '3000.00')
        response = self.client.post(reverse('auction-list'), self.auction_payload(), format='json')
        self.assertEqual(response.status_code, 201)

    def test_bond_is_forfeited_when_the_seller_never_hands_over(self):
        self.client.force_authenticate(self.seller)
        self.client.post(reverse('auction-seller-bond'))
        auction = self.create_auction(buy_now_price=Decimal('16000'))
        self.client.force_authenticate(self.buyer)
        self.client.post(reverse('auction-buy-now', args=[auction.id]))
        Order.objects.update(handover_due_at=timezone.now() - timedelta(seconds=1))
        orders.process_due_orders()
        self.assertEqual(SellerBond.objects.get(account=self.seller).status, SellerBond.Status.FORFEITED)

    @override_settings(SELLER_BOND_AMOUNT=Decimal('0'))
    def test_no_bond_needed_when_the_amount_is_zero(self):
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.post(reverse('auction-list'), self.auction_payload(), format='json').status_code, 201)
        self.assertFalse(self.client.get(reverse('auction-seller-bond')).data['required'])


class ReviewAdminTests(AuctionTestCase):
    def test_accounts_with_incidents_show_up_for_review(self):
        staff = Account.objects.create_superuser(username='staff', email='staff@example.com', password='pass12345')
        orders.record_incident(self.buyer, Incident.Kind.WINNER_DEFAULTED)
        orders.record_incident(self.buyer, Incident.Kind.UNPAID_BUY_NOW)
        orders.record_incident(self.other_buyer, Incident.Kind.UNPAID_BUY_NOW)
        self.client.force_login(staff)

        response = self.client.get(reverse('admin:auction_accounttoreview_changelist'), {'needs_review': 'yes'})
        self.assertContains(response, 'buyer@example.com')
        self.assertNotContains(response, 'other_buyer@example.com')  # one incident: below the threshold
        for name in ('auction_order_changelist', 'auction_incident_changelist', 'auction_sellerbond_changelist'):
            self.assertEqual(self.client.get(reverse(f'admin:{name}')).status_code, 200, name)
