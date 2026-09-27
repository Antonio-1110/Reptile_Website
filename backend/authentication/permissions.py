from django.utils.translation import gettext_lazy
from rest_framework import permissions


class HasVerifiedEmail(permissions.BasePermission):
    """
    Signed-in users must have confirmed their email address before doing anything that reaches other
    people or money (posting, contacting a seller, reporting, bidding, paying). Otherwise throwaway
    accounts with someone else's address would be free. Reading is always allowed, and anonymous
    requests are left to the view's other permissions.
    """
    message = gettext_lazy(
        'Please confirm your email address first: open the link we emailed you. '
        'You can ask for a new link at the top of any page.'
    )

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return not user.is_authenticated or user.email_verified
