class AuctionError(Exception):
    """A rule was broken; the message is safe to show to the user. The API answers it with a 400
    `{"detail": message}` (common/exceptions.py), so views let it propagate."""
