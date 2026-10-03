from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext as _
from rest_framework import generics, permissions
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView

from .emails import send_password_changed_email, send_password_reset_email, send_verification_email, user_from_uid
from .google import GoogleTokenError, account_for_google, verify_id_token
from .serializers import (
    GoogleSignInSerializer, LoginSerializer, MeSerializer, PasswordChangeSerializer, PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer, RegisterSerializer, VerifyEmailSerializer,
)

Account = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — creates a new user, no token issued (log in separately).

    The account starts unverified and gets an email with a link to confirm the address.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def perform_create(self, serializer):
        send_verification_email(serializer.save())


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — `username` (or the account's email) and `password` for a token pair.

    Rate limited against password guessing.
    """
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class GoogleSignInView(APIView):
    """POST /api/v1/auth/google/ — `credential` from Google's sign-in button; answers like login/.

    Signs in to the account already linked to that Google account, else the one using its (confirmed)
    email address, else creates a new account with a username made from the address and no password.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def get_authenticate_header(self, request):
        # A refused sign-in is a 401, like a wrong password on login/ (DRF sends 403 without this).
        return 'Bearer realm="api"'

    def post(self, request):
        if not settings.GOOGLE_CLIENT_ID:
            raise ValidationError({'detail': _('Signing in with Google is not available.')})
        serializer = GoogleSignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            claims = verify_id_token(serializer.validated_data['credential'])
        except GoogleTokenError:
            raise AuthenticationFailed(_("Google couldn't confirm who you are. Please try again."))
        account, created = account_for_google(claims)
        if not account.is_active:
            raise AuthenticationFailed(_('This account has been disabled.'))
        refresh = RefreshToken.for_user(account)
        update_last_login(None, account)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'created': created})


class LogoutView(TokenBlacklistView):
    """POST /api/v1/auth/logout/ — retires the given refresh token so it can't be used again.

    The refresh token itself is the proof, so this works even after the access token has expired.
    """


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ — returns the authenticated user's profile."""
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class VerifyEmailView(APIView):
    """POST /api/v1/auth/verify-email/ — `uid` and `token` from the emailed link confirm the address.

    No sign-in needed: the link may be opened on another device.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            # A used link no longer checks out (the token covers the verified flag), but opening it
            # twice, e.g. from two email apps, shouldn't look like an error.
            uid = request.data.get('uid') if hasattr(request.data, 'get') else None
            user = user_from_uid(str(uid)) if uid else None
            if user is not None and user.email_verified:
                return Response({'detail': _('Your email address is confirmed.')})
            serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        return Response({'detail': _('Your email address is confirmed.')})


class ResendVerificationView(APIView):
    """POST /api/v1/auth/verify-email/resend/ — emails the signed-in user a new confirmation link."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'email'

    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({'detail': _('Your email address is already confirmed.')})
        send_verification_email(user)
        return Response({'detail': _("We've sent a new link to %(email)s.") % {'email': user.email}})


class PasswordResetRequestView(APIView):
    """POST /api/v1/auth/password-reset/ — `email`; emails a reset link to the accounts using it.

    Answers the same whether or not an account exists, so it can't be used to find out who has one.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'email'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Accounts made with Google sign-in have no password yet; this is how their owners set one.
        for account in Account.objects.filter(email__iexact=serializer.validated_data['email'], is_active=True):
            send_password_reset_email(account)
        return Response({'detail': _(
            "If an account uses that email address, we've sent it a link to choose a new password."
        )})


class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password-reset/confirm/ — `uid`, `token` and the new `password`.

    Also signs the account out everywhere (retires its refresh tokens), and confirms the email address,
    since opening the link proves the owner can read it.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['password'])
        user.email_verified = True
        user.save(update_fields=['password', 'email_verified'])
        sign_out_everywhere(user)
        return Response({'detail': _('Your password has been changed. You can sign in with it now.')})


class PasswordChangeView(APIView):
    """POST /api/v1/auth/password-change/ — the signed-in user's `current_password` and new `password`.

    Signs the account out on every other device and answers with a fresh token pair for this one, like
    login/. Accounts without a password (made with Google sign-in) set one with password-reset/ instead.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        sign_out_everywhere(user)
        send_password_changed_email(user)
        refresh = RefreshToken.for_user(user)
        return Response({
            'detail': _('Your password has been changed. Other devices have been signed out.'),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


def sign_out_everywhere(user):
    """Retires every refresh token the account holds. Access tokens already handed out still work
    until they expire (SIMPLE_JWT ACCESS_TOKEN_LIFETIME), as they aren't checked against the blacklist."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
