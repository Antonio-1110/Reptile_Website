"""
Emails about auction sales: buy-now races, auction results and every step of an order.
services.py and orders.py send these once the database change has committed.
"""
from django.core.mail import mail_admins
from django.utils import timezone
from django.utils.translation import gettext as _

from common.money import format_money
from common.notifications import contact_lines, send_notification


# Added to every email that tells a buyer about money, because "pay me directly instead" is the
# classic scam on marketplaces like this one.
def _pay_through_us_warning():
    return _('Only ever pay through Reptilian. Never send money directly to a seller: we can only protect payments made through us.')


def _when(moment):
    """A deadline as shown in emails, in the site's time zone."""
    return timezone.localtime(moment).strftime('%Y-%m-%d %H:%M')


def _for_listing(auction, animal, equipment):
    """The wording for what's being sold: most emails say "the animal", which is wrong for equipment."""
    return equipment if auction.equipment_post_id else animal


def _handover_instructions(auction, values):
    return _for_listing(
        auction,
        _('Hand the animal over (or ship it) by %(handover_due)s, then mark it as handed over on the listing page. If it isn\'t handed over by then, the buyer is refunded in full and it counts against your account.'),
        _('Hand the item over (or ship it) by %(handover_due)s, then mark it as handed over on the listing page. If it isn\'t handed over by then, the buyer is refunded in full and it counts against your account.'),
    ) % values


def _values(auction, purchase=None):
    values = {'title': auction.post.title, 'price': format_money(auction.buy_now_price, auction.currency)}
    if purchase is not None:
        values['paid'] = format_money(purchase.amount, purchase.currency)
    return values


def buy_now_competition(auction, purchases):
    """Several buyers are paying the buy-now price at once: tell each of them and the seller."""
    values = _values(auction)
    for purchase in purchases:
        send_notification([purchase.buyer.email], lambda: (
            _('Another buyer is also buying "%(title)s"') % values,
            _('Another buyer has also started buying "%(title)s" at the buy-now price of %(price)s. Whoever completes payment first gets it. If someone else pays before you, any payment you make is refunded in full.') % values
            + '\n\n' + _pay_through_us_warning(),
        ))
    send_notification([auction.seller.email], lambda: (
        _('Several buyers are buying "%(title)s" at your buy-now price') % values,
        _for_listing(
            auction,
            _('%(count)s buyers are paying your buy-now price of %(price)s for "%(title)s" right now. The first payment to arrive wins and closes the auction; anyone who pays after is refunded in full. You don\'t need to do anything. If you have more than one of these animals, you can reach the other buyers after the sale.'),
            _('%(count)s buyers are paying your buy-now price of %(price)s for "%(title)s" right now. The first payment to arrive wins and closes the auction; anyone who pays after is refunded in full. You don\'t need to do anything. If you have more than one of these items, you can reach the other buyers after the sale.'),
        ) % {**values, 'count': len(purchases)},
    ))


def bought(order, bidder_deposits, cancelled_purchases):
    """A buy-now payment arrived first: tell the buyer, the seller, the bidders and anyone else paying."""
    auction, purchase = order.auction, order.purchase
    values = {**_values(auction, purchase), 'handover_due': _when(order.handover_due_at)}
    buyer, seller = order.buyer, auction.seller

    send_notification([buyer.email], lambda: (
        _('You bought "%(title)s"') % values,
        _for_listing(
            auction,
            _('Your payment of %(paid)s for "%(title)s" has arrived, so the animal is yours and the auction has closed. We hold your payment until you have received the animal, and only then pay the seller.'),
            _('Your payment of %(paid)s for "%(title)s" has arrived, so the item is yours and the auction has closed. We hold your payment until you have received the item, and only then pay the seller.'),
        ) % values
        + '\n\n' + _('The seller has until %(handover_due)s to hand it over or ship it. If they don\'t, you get a full refund.') % values
        + '\n\n' + _("The seller's contact details, to arrange the handover:") + '\n' + contact_lines(seller.contact_details())
        + '\n\n' + _pay_through_us_warning(),
    ))
    send_notification([seller.email], lambda: (
        _('"%(title)s" was bought at your buy-now price') % values,
        _for_listing(
            auction,
            _('A buyer paid your buy-now price of %(paid)s for "%(title)s", so the auction has closed and every bidder\'s deposit is being refunded. We hold the payment and pay you once the animal has been handed over.'),
            _('A buyer paid your buy-now price of %(paid)s for "%(title)s", so the auction has closed and every bidder\'s deposit is being refunded. We hold the payment and pay you once the item has been handed over.'),
        ) % values
        + '\n\n' + _handover_instructions(auction, values)
        + '\n\n' + _("The buyer's contact details, to arrange the handover:") + '\n' + contact_lines(buyer.contact_details()),
    ))
    for deposit in bidder_deposits:
        deposit_values = {**values, 'deposit': format_money(deposit.amount, deposit.currency)}
        send_notification([deposit.account.email], lambda: (
            _('The auction for "%(title)s" has closed early') % deposit_values,
            _('Another buyer paid the seller\'s buy-now price for "%(title)s", so the auction closed early and no bids can win it. Your deposit of %(deposit)s is being refunded in full.') % deposit_values,
        ))
    for other in cancelled_purchases:
        send_notification([other.buyer.email], lambda: (
            _('"%(title)s" has been bought by someone else') % values,
            _('Another buyer completed payment for "%(title)s" first, so it is no longer available. If you still complete a payment, it will be refunded to you in full.') % values,
        ))


def paid_too_late(purchase):
    """A buy-now payment arrived after the listing was already sold (or the auction had closed)."""
    values = _values(purchase.auction, purchase)
    send_notification([purchase.buyer.email], lambda: (
        _('Your payment for "%(title)s" is being refunded') % values,
        _('Your payment of %(paid)s for "%(title)s" arrived after the auction had closed (another buyer paid first, or it ended). It is being refunded to you in full.') % values,
    ))


# --- Orders ---------------------------------------------------------------------------------------

def _order_values(order):
    values = {
        'title': order.auction.post.title,
        'price': format_money(order.price, order.currency),
        'balance': format_money(order.balance, order.currency),
        'payout': format_money(order.payout, order.currency),
    }
    for field in ('payment_due_at', 'handover_due_at', 'confirm_due_at'):
        moment = getattr(order, field)
        if moment:
            values[field.replace('_at', '')] = _when(moment)
    if order.deposit_id:
        values['deposit'] = format_money(order.deposit.amount, order.deposit.currency)
    return values


def auction_won(order, losing_deposits):
    """An auction ended with a winner: the winner pays the rest, the seller waits, the others get refunds."""
    values = _order_values(order)
    seller, buyer = order.auction.seller, order.buyer
    send_notification([buyer.email], lambda: (
        _('You won "%(title)s"') % values,
        _('You won "%(title)s" with a bid of %(price)s. Please pay the remaining %(balance)s through Reptilian by %(payment_due)s (your deposit counts toward the price). If you don\'t pay in time, your deposit is kept and the sale is cancelled.') % values
        + '\n\n' + _("The seller's contact details, to arrange the handover:") + '\n' + contact_lines(seller.contact_details())
        + '\n\n' + _pay_through_us_warning(),
    ))
    send_notification([seller.email], lambda: (
        _('"%(title)s" sold for %(price)s') % values,
        _for_listing(
            order.auction,
            _('Your auction for "%(title)s" ended with a winning bid of %(price)s. The winner has until %(payment_due)s to pay us the rest; we\'ll email you as soon as they do, and only then should you hand the animal over.'),
            _('Your auction for "%(title)s" ended with a winning bid of %(price)s. The winner has until %(payment_due)s to pay us the rest; we\'ll email you as soon as they do, and only then should you hand the item over.'),
        ) % values
        + '\n\n' + _("The buyer's contact details, to arrange the handover:") + '\n' + contact_lines(buyer.contact_details()),
    ))
    for deposit in losing_deposits:
        deposit_values = {**values, 'deposit': format_money(deposit.amount, deposit.currency)}
        send_notification([deposit.account.email], lambda: (
            _('The auction for "%(title)s" has ended') % deposit_values,
            _('The auction for "%(title)s" has ended and another bidder won. Your deposit of %(deposit)s is being refunded in full.') % deposit_values,
        ))


def order_paid(order):
    values = _order_values(order)
    send_notification([order.auction.seller.email], lambda: (
        _('Payment received for "%(title)s": please hand it over') % values,
        _('The buyer has paid the full price of %(price)s for "%(title)s", and we are holding it.') % values
        + '\n\n' + _handover_instructions(order.auction, values),
    ))
    send_notification([order.buyer.email], lambda: (
        _('Payment received for "%(title)s"') % values,
        _for_listing(
            order.auction,
            _('We have received your payment for "%(title)s" and are holding it until you have the animal. The seller has until %(handover_due)s to hand it over or ship it; if they don\'t, you get a full refund.'),
            _('We have received your payment for "%(title)s" and are holding it until you have the item. The seller has until %(handover_due)s to hand it over or ship it; if they don\'t, you get a full refund.'),
        ) % values,
    ))


def order_paid_too_late(order):
    values = _order_values(order)
    send_notification([order.buyer.email], lambda: (
        _('Your payment for "%(title)s" is being refunded') % values,
        _('Your payment for "%(title)s" arrived after the deadline, when the sale had already been cancelled. It is being refunded to you in full.') % values,
    ))


def order_handed_over(order):
    values = {**_order_values(order), 'note': order.handover_note or '-'}
    send_notification([order.buyer.email], lambda: (
        _('"%(title)s" has been handed over: please confirm') % values,
        _('The seller says "%(title)s" has been handed over or shipped. Their note: %(note)s') % values
        + '\n\n' + _for_listing(
            order.auction,
            _('Once you have the animal and it is healthy, confirm on the listing page by %(confirm_due)s. If something is wrong, report a problem there instead and we will hold the payment while we look into it. If we hear nothing by then, the sale completes and the seller is paid.'),
            _('Once you have the item and it is as described, confirm on the listing page by %(confirm_due)s. If something is wrong, report a problem there instead and we will hold the payment while we look into it. If we hear nothing by then, the sale completes and the seller is paid.'),
        ) % values,
    ))


def order_completed(order):
    values = _order_values(order)
    send_notification([order.auction.seller.email], lambda: (
        _('Sale completed: "%(title)s"') % values,
        _('The sale of "%(title)s" is complete. We will pay you %(payout)s.') % values,
    ))
    send_notification([order.buyer.email], lambda: (
        _('Sale completed: "%(title)s"') % values,
        _for_listing(
            order.auction,
            _('The sale of "%(title)s" is complete. Enjoy your new animal!'),
            _('The sale of "%(title)s" is complete. Enjoy!'),
        ) % values,
    ))


def order_disputed(order):
    values = {**_order_values(order), 'problem': order.problem_report}
    send_notification([order.auction.seller.email], lambda: (
        _('The buyer reported a problem with "%(title)s"') % values,
        _('The buyer reported a problem with "%(title)s": %(problem)s') % values
        + '\n\n' + _('We are holding the payment while our team looks into it, and may contact you.'),
    ))
    mail_admins(f'Order #{order.pk} disputed: {order.auction.post.title}', f'{order.problem_report}\n\nReview it in the admin: Orders → #{order.pk}.', fail_silently=True)


def order_refunded(order):
    values = _order_values(order)
    send_notification([order.buyer.email, order.auction.seller.email], lambda: (
        _('Order for "%(title)s" refunded') % values,
        _('After reviewing the problem reported with "%(title)s", we have refunded the buyer in full.') % values,
    ))


def buyer_defaulted(order, runner_up):
    values = _order_values(order)
    send_notification([order.buyer.email], lambda: (
        _('Your purchase of "%(title)s" was cancelled') % values,
        _('We did not receive the rest of the payment for "%(title)s" by %(payment_due)s, so the sale is cancelled and your deposit of %(deposit)s is kept.') % values,
    ))
    if runner_up is not None:
        offer_values = {**values, 'runner_up': format_money(runner_up.amount, order.currency)}
    else:
        offer_values = values
    auction = order.auction

    # Built per language inside send_notification, so the choice of message is made there too.
    def build():
        if runner_up is not None:
            message = _for_listing(
                auction,
                _('You can offer "%(title)s" to the next-highest bidder at their bid of %(runner_up)s: open the listing page to decide. If you don\'t want to, you keep the animal.'),
                _('You can offer "%(title)s" to the next-highest bidder at their bid of %(runner_up)s: open the listing page to decide. If you don\'t want to, you keep the item.'),
            ) % offer_values
        else:
            message = _for_listing(
                auction,
                _('Nobody else bid on it, so you simply keep the animal.'),
                _('Nobody else bid on it, so you simply keep the item.'),
            )
        return (
            _('The winner of "%(title)s" did not pay') % offer_values,
            _for_listing(
                auction,
                _('The winner of "%(title)s" did not pay by the deadline, so the sale is cancelled. Do not hand the animal over.'),
                _('The winner of "%(title)s" did not pay by the deadline, so the sale is cancelled. Do not hand the item over.'),
            ) % offer_values
            + '\n\n' + message,
        )
    send_notification([auction.seller.email], build)


def runner_up_offered(order):
    values = _order_values(order)
    send_notification([order.buyer.email], lambda: (
        _('"%(title)s" is offered to you') % values,
        _('The winner of "%(title)s" did not pay, and the seller is offering it to you at your bid of %(price)s. To buy it, pay on the listing page by %(payment_due)s. You are not obliged to: you can decline or simply let the offer lapse.') % values
        + '\n\n' + _pay_through_us_warning(),
    ))


def runner_up_declined(order):
    values = _order_values(order)
    send_notification([order.auction.seller.email], lambda: (
        _('Offer for "%(title)s" not taken up') % values,
        _for_listing(
            order.auction,
            _('The next-highest bidder did not take up your offer for "%(title)s", so you keep the animal.'),
            _('The next-highest bidder did not take up your offer for "%(title)s", so you keep the item.'),
        ) % values,
    ))


def seller_defaulted(order, bond):
    values = _order_values(order)
    send_notification([order.buyer.email], lambda: (
        _('Refund for "%(title)s"') % values,
        _('The seller did not hand over "%(title)s" by %(handover_due)s, so we are refunding everything you paid, in full.') % values,
    ))
    penalty = ''
    if bond is not None:
        bond_values = {'bond': format_money(bond.amount, bond.currency)}
        penalty = '\n\n' + _('Your seller bond of %(bond)s has been forfeited; post a new one to keep selling at auction.') % bond_values
    send_notification([order.auction.seller.email], lambda: (
        _('Sale of "%(title)s" cancelled: not handed over') % values,
        _('You did not mark "%(title)s" as handed over by %(handover_due)s, so the buyer has been refunded in full and this has been recorded on your account.') % values
        + penalty,
    ))
