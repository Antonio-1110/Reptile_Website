"""
One-time links sent by email: confirming an address after sign-up, and resetting a forgotten password.
Links point at the frontend (FRONTEND_URL), which posts the uid and token back to the API.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator, default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _

from common.notifications import send_notification


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = 'authentication.emails.EmailVerificationTokenGenerator'

    def _make_hash_value(self, user, timestamp):
        # Changes once the address is verified or replaced, so a link works once and only for the
        # address it was sent to. Expires after PASSWORD_RESET_TIMEOUT, like reset links.
        return f'{user.pk}{user.email}{user.email_verified}{timestamp}'


email_verification_token = EmailVerificationTokenGenerator()
# Django's reset tokens hash the password and last login, so a link stops working once it's been used.
password_reset_token = default_token_generator


def encode_uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def user_from_uid(uid):
    try:
        pk = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError):
        return None
    return get_user_model().objects.filter(pk=pk, is_active=True).first() if pk.isdigit() else None


def send_verification_email(user):
    url = f'{settings.FRONTEND_URL}/verify-email?uid={encode_uid(user)}&token={email_verification_token.make_token(user)}'
    send_notification([user.email], lambda: (
        _('Confirm your email address'),
        _('Hi %(username)s, please confirm this is your email address by opening this link:') % {'username': user.username}
        + f'\n\n{url}\n\n'
        + _("Until then you can browse, but you can't post listings, contact sellers or bid. "
            "If you didn't create this account, you can ignore this email."),
    ))


def send_password_reset_email(user):
    url = f'{settings.FRONTEND_URL}/reset-password?uid={encode_uid(user)}&token={password_reset_token.make_token(user)}'
    send_notification([user.email], lambda: (
        _('Reset your password'),
        _('Someone asked to reset the password for the account %(username)s. To choose a new password, open this link:')
        % {'username': user.username}
        + f'\n\n{url}\n\n'
        + _("If it wasn't you, ignore this email: your password stays the same."),
    ))


def send_password_changed_email(user):
    # So the owner hears about it if someone who got into their account changed the password.
    url = f'{settings.FRONTEND_URL}/forgot-password'
    send_notification([user.email], lambda: (
        _('Your password was changed'),
        _('The password for the account %(username)s was just changed, and it was signed out on every other device.')
        % {'username': user.username}
        + '\n\n'
        + _("If it wasn't you, choose a new password now with this link, then check your account settings:")
        + f'\n\n{url}',
    ))
