"""
Concurrency tests: the same money-moving request arriving twice at once, from separate database
connections. They only mean something on PostgreSQL (production): SQLite serialises every write, so it
never exercises `select_for_update`, and these tests are skipped there. CI runs the suite on both.
"""
import threading
from collections import Counter
from datetime import timedelta
from decimal import Decimal

from django.db import connection, connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from account.models import Account
from post.models import LiveAnimalPost, Species
from . import orders, services
from .errors import AuctionError
from .models import Auction, Bid, BuyNowPurchase, Deposit, Order
from .payments import ManualPaymentGateway, PaymentResult

GATEWAY = 'auction.test_races.CountingGateway'


class CountingGateway(ManualPaymentGateway):
    """Payments stay pending until confirmed, and every refund/keep is counted, so a race that moves the
    same money twice shows up even when the database ends up looking right."""
    name = 'counting'
    calls = Counter()
    lock = threading.Lock()

    @classmethod
    def record(cls, action, payment):
        with cls.lock:
            cls.calls[(action, payment._meta.model_name, payment.pk)] += 1

    def collect(self, payment):
        return PaymentResult(paid=False, provider_reference=f'counting-{payment._meta.model_name}-{payment.pk}')

    def refund(self, payment):
        self.record('refund', payment)

    def keep(self, payment):
        self.record('keep', payment)


def run_together(*calls):
    """Run each call on its own thread (so its own database connection), released at the same moment.
    Returns what each call returned or raised, in order."""
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def run(index, call):
        try:
            barrier.wait()
            results[index] = call()
        except Exception as error:  # noqa: BLE001 - the test inspects what each side raised
            results[index] = error
        finally:
            connections.close_all()

    threads = [threading.Thread(target=run, args=(i, call)) for i, call in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


@override_settings(AUCTION_PAYMENT_GATEWAY=GATEWAY)
class RaceTestCase(TransactionTestCase):
    def setUp(self):
        if connection.vendor != 'postgresql':
            self.skipTest('Row locking is only exercised on PostgreSQL.')
        CountingGateway.calls.clear()
        self.seller = self.make_account('seller', account_type='commercial', is_paid_account=True)
        self.buyer = self.make_account('buyer')
        self.other_buyer = self.make_account('other_buyer')
        listing = LiveAnimalPost.objects.create(
            account=self.seller, species=Species.objects.create(name='Ball Pythons'), title='Pied Ball Python',
            description='Healthy animal', contact_info='{}',
        )
        self.auction = Auction.objects.create(
            seller=self.seller, live_animal_post=listing, starting_price=Decimal('5000.00'),
            min_increment=Decimal('100.00'), deposit_amount=Decimal('500.00'), buy_now_price=Decimal('9000.00'),
            currency='TWD', starts_at=timezone.now() - timedelta(minutes=1), ends_at=timezone.now() + timedelta(days=3),
        )

    @staticmethod
    def make_account(username, **fields):
        return Account.objects.create_user(username=username, email=f'{username}@example.com', password='pass1234', **fields)

    def held_deposit(self, account):
        deposit, _ = services.request_deposit(self.auction, account)
        return services.confirm_deposit(deposit)

    def assertNoUnexpectedErrors(self, results, allowed=(AuctionError,)):
        for result in results:
            if isinstance(result, Exception) and not isinstance(result, allowed):
                raise result

    def money_moves(self, action, payment):
        return CountingGateway.calls[(action, payment._meta.model_name, payment.pk)]


class ConcurrentBidTests(RaceTestCase):
    def test_two_bids_at_the_same_price_only_one_is_accepted(self):
        self.held_deposit(self.buyer)
        self.held_deposit(self.other_buyer)

        results = run_together(
            lambda: services.place_bid(self.auction, self.buyer, '5000.00'),
            lambda: services.place_bid(self.auction, self.other_buyer, '5000.00'),
        )

        self.assertNoUnexpectedErrors(results)
        self.assertEqual(sum(isinstance(result, Bid) for result in results), 1, results)
        self.assertEqual(Bid.objects.filter(auction=self.auction).count(), 1)

    def test_many_bidders_at_once_never_accept_a_bid_below_the_minimum(self):
        bidders = [self.buyer, self.other_buyer] + [self.make_account(f'bidder{i}') for i in range(4)]
        for bidder in bidders:
            self.held_deposit(bidder)

        run_together(*[
            (lambda bidder=bidder, amount=amount: services.place_bid(self.auction, bidder, amount))
            for bidder, amount in zip(bidders, ['5000', '5000', '5100', '5100', '5200', '5300'])
        ])

        # Replaying the accepted bids in order, each one must have beaten the one before by the increment.
        amounts = list(Bid.objects.filter(auction=self.auction).order_by('created_at', 'pk').values_list('amount', flat=True))
        self.assertTrue(amounts)
        for previous, current in zip(amounts, amounts[1:]):
            self.assertGreaterEqual(current, previous + self.auction.min_increment, amounts)


class ConcurrentDepositTests(RaceTestCase):
    def test_double_clicked_deposit_creates_one_deposit(self):
        results = run_together(
            lambda: services.request_deposit(self.auction, self.buyer),
            lambda: services.request_deposit(self.auction, self.buyer),
        )

        self.assertNoUnexpectedErrors(results)
        self.assertEqual(Deposit.objects.filter(auction=self.auction, account=self.buyer).count(), 1)

    def test_deposit_confirmed_twice_at_once_is_held_once(self):
        deposit, _ = services.request_deposit(self.auction, self.buyer)

        results = run_together(
            lambda: services.confirm_deposit(deposit, 'ref-1'),
            lambda: services.confirm_deposit(deposit, 'ref-2'),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        deposit.refresh_from_db()
        self.assertEqual(deposit.status, Deposit.Status.HELD)

    def test_deposit_paid_while_the_auction_closes_is_refunded_exactly_once(self):
        deposit, _ = services.request_deposit(self.auction, self.buyer)
        Auction.objects.filter(pk=self.auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))

        results = run_together(
            lambda: services.confirm_deposit(deposit),
            lambda: services.settle_auction(self.auction),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        deposit.refresh_from_db()
        self.assertIn(deposit.status, (Deposit.Status.RELEASED, Deposit.Status.CANCELLED))
        self.assertLessEqual(self.money_moves('refund', deposit), 1)
        self.assertEqual(self.money_moves('keep', deposit), 0)


class ConcurrentSettlementTests(RaceTestCase):
    def test_settling_twice_at_once_creates_one_order_and_refunds_losers_once(self):
        self.held_deposit(self.buyer)
        loser_deposit = self.held_deposit(self.other_buyer)
        services.place_bid(self.auction, self.other_buyer, '5000')
        services.place_bid(self.auction, self.buyer, '5100')
        Auction.objects.filter(pk=self.auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))

        results = run_together(
            lambda: services.settle_auction(self.auction),
            lambda: services.settle_auction(self.auction),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        self.assertEqual(Order.objects.filter(auction=self.auction).count(), 1)
        self.assertEqual(Order.objects.get(auction=self.auction).buyer, self.buyer)
        self.assertEqual(self.money_moves('refund', loser_deposit), 1)


class ConcurrentBuyNowTests(RaceTestCase):
    def test_two_buy_now_payments_arriving_together_sell_once_and_refund_the_other(self):
        first, _, _ = services.start_buy_now(self.auction, self.buyer)
        second, _, _ = services.start_buy_now(self.auction, self.other_buyer)

        results = run_together(
            lambda: services.confirm_buy_now(first),
            lambda: services.confirm_buy_now(second),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        statuses = sorted(BuyNowPurchase.objects.filter(auction=self.auction).values_list('status', flat=True))
        self.assertEqual(statuses, sorted([BuyNowPurchase.Status.PAID, BuyNowPurchase.Status.REFUNDED]))
        self.assertEqual(Order.objects.filter(auction=self.auction).count(), 1)
        loser = BuyNowPurchase.objects.get(auction=self.auction, status=BuyNowPurchase.Status.REFUNDED)
        self.assertEqual(self.money_moves('refund', loser), 1)

    def test_same_buy_now_payment_confirmed_twice_sells_once(self):
        purchase, _, _ = services.start_buy_now(self.auction, self.buyer)

        results = run_together(
            lambda: services.confirm_buy_now(purchase),
            lambda: services.confirm_buy_now(purchase),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, BuyNowPurchase.Status.PAID)
        self.assertEqual(Order.objects.filter(auction=self.auction).count(), 1)
        self.assertEqual(self.money_moves('refund', purchase), 0)

    def test_buy_now_payment_racing_a_winning_bid_close_sells_once(self):
        self.held_deposit(self.other_buyer)
        services.place_bid(self.auction, self.other_buyer, '5000')
        purchase, _, _ = services.start_buy_now(self.auction, self.buyer)
        Auction.objects.filter(pk=self.auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))

        results = run_together(
            lambda: services.confirm_buy_now(purchase),
            lambda: services.settle_auction(self.auction),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        self.assertEqual(Order.objects.filter(auction=self.auction).count(), 1)
        purchase.refresh_from_db()
        # The auction had already ended, so the bid wins and the buy-now money goes back.
        self.assertEqual(purchase.status, BuyNowPurchase.Status.REFUNDED)
        self.assertEqual(self.money_moves('refund', purchase), 1)


class ConcurrentOrderPaymentTests(RaceTestCase):
    def won_order(self):
        self.held_deposit(self.buyer)
        services.place_bid(self.auction, self.buyer, '5000')
        Auction.objects.filter(pk=self.auction.pk).update(ends_at=timezone.now() - timedelta(seconds=1))
        services.settle_auction(self.auction)
        order = Order.objects.get(auction=self.auction)
        order, _ = orders.pay_order(order, self.buyer)
        return order

    def test_balance_confirmed_twice_at_once_keeps_the_deposit_once(self):
        order = self.won_order()

        results = run_together(
            lambda: orders.confirm_order_payment(order, 'ref-1'),
            lambda: orders.confirm_order_payment(order, 'ref-2'),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(self.money_moves('keep', order.deposit), 1)

    def test_balance_arriving_as_the_deadline_passes_is_either_accepted_or_refunded(self):
        order = self.won_order()
        Order.objects.filter(pk=order.pk).update(payment_due_at=timezone.now() - timedelta(seconds=1))

        results = run_together(
            lambda: orders.confirm_order_payment(order),
            lambda: orders.process_due_orders(),
        )

        self.assertNoUnexpectedErrors(results, allowed=())
        order.refresh_from_db()
        paid = order.balance_status == Order.BalanceStatus.PAID
        refunded = order.balance_status == Order.BalanceStatus.REFUNDED
        self.assertTrue(paid or refunded, order.balance_status)
        # Paid means the sale went ahead; refunded means the buyer got every cent back, once.
        if paid:
            self.assertEqual(order.status, Order.Status.PAID)
        else:
            self.assertEqual(self.money_moves('refund', order), 1)
