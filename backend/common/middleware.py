"""Development-only convenience auth bypass. Never active when DEBUG=False."""
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import SessionAuthentication

DEV_USERNAME = 'dev-user'


def get_or_create_dev_user():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=DEV_USERNAME,
        defaults={'email': 'dev@reptile-marketplace.local', 'is_staff': True, 'is_superuser': True},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    return user


class DevAuthBypassMiddleware:
    """
    When DEBUG=True and a request has no authenticated user (no valid session/JWT/token),
    attaches a default dev user to request.user so the API/admin can be exercised locally
    without logging in every time. A no-op whenever DEBUG=False.

    DRF re-resolves request.user through its own authentication classes on every APIView
    request rather than trusting whatever this middleware set, so DevAuthBypassAuthentication
    (below) must also be listed in DEFAULT_AUTHENTICATION_CLASSES for this bypass to reach
    DRF endpoints too.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG and not request.user.is_authenticated:
            request.user = get_or_create_dev_user()
            request.dev_auth_bypass = True
        return self.get_response(request)


class DevAwareSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication that ignores a user attached by DevAuthBypassMiddleware. Without
    this, DRF treats the bypass user as a real session login and enforces CSRF, which rejects
    every anonymous POST (e.g. register/login) in development.
    """

    def authenticate(self, request):
        if getattr(request._request, 'dev_auth_bypass', False):
            return None
        return super().authenticate(request)


class DevAuthBypassAuthentication:
    """
    DRF authentication class mirroring DevAuthBypassMiddleware for API views. Only used as
    the last entry in DEFAULT_AUTHENTICATION_CLASSES, so real JWT/Session credentials
    always take priority; this only fires once every real authenticator has already failed.
    """

    def authenticate(self, request):
        if not settings.DEBUG:
            return None
        return (get_or_create_dev_user(), None)

    def authenticate_header(self, request):
        return 'Bearer'
