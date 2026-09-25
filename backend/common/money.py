from django.conf import settings


def format_money(amount, currency=None):
    # "TWD 10,500" (cents only when there are any), for messages and emails shown to users. Listings
    # store bare prices; the marketplace trades in AUCTION_CURRENCY.
    places = 0 if amount == amount.to_integral_value() else 2
    return f'{currency or settings.AUCTION_CURRENCY} {amount:,.{places}f}'
