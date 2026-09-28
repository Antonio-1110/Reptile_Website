from django.db.models import ProtectedError
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.views import exception_handler

from auction.errors import AuctionError


def api_exception_handler(exc, context):
    """
    DRF's handler, made to give every error one shape the frontend can rely on:
    - `{"detail": "message"}` for an error about the request as a whole, always a single string;
    - `{"field": ["message", …]}` for errors about particular fields (both may appear together).
    Serializer errors that aren't about one field land in `detail` (NON_FIELD_ERRORS_KEY), and a broken
    auction or order rule (AuctionError, whose message is written for users) is a 400 like any other.
    A delete blocked by a protected link (e.g. auction money still held, auction/models.py) is a 400 too.
    """
    if isinstance(exc, AuctionError):
        exc = exceptions.ValidationError({'detail': str(exc)})
    elif isinstance(exc, ProtectedError):
        exc = exceptions.ValidationError({'detail': _protected_message(exc)})
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and isinstance(response.data.get('detail'), list):
        response.data['detail'] = ' '.join(str(message) for message in response.data['detail'])
    return response


def _protected_message(exc):
    if any(hasattr(obj, 'holds_money') for obj in exc.protected_objects):
        return _(
            "This listing can't be deleted while its auction is running or someone's money for it is still "
            "held. Try again once the auction has ended and its sale is settled."
        )
    return _("This can't be deleted because other records still depend on it.")
