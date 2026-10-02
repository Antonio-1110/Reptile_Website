"""Signing in with Google: the browser gets an ID token from Google Identity Services and sends it here.

Only the OAuth client ID is needed (no client secret): the token is a JWT that Google signs, so checking
its signature, audience, issuer and expiry proves Google issued it to this site for this person.
"""
import re

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from account.usernames import username_taken

GOOGLE_CERTS_URL = 'https://www.googleapis.com/oauth2/v3/certs'
GOOGLE_ISSUERS = ('accounts.google.com', 'https://accounts.google.com')

Account = get_user_model()
_jwks_client = None


class GoogleTokenError(Exception):
    pass


def _signing_key(token):
    global _jwks_client
    if _jwks_client is None:
        # Google rotates its keys every few days; the client caches them and refetches on an unknown key id.
        _jwks_client = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, timeout=10)
    return _jwks_client.get_signing_key_from_jwt(token).key


def verify_id_token(token):
    """The token's claims if Google issued it for this site's client ID to a confirmed address."""
    try:
        claims = jwt.decode(
            token, _signing_key(token), algorithms=['RS256'],
            audience=settings.GOOGLE_CLIENT_ID, issuer=GOOGLE_ISSUERS,
            options={'require': ['exp', 'iat', 'sub', 'aud', 'iss']},
        )
    except jwt.PyJWTError as error:
        raise GoogleTokenError(str(error)) from error
    # Only an address Google has confirmed may pick out an existing account here.
    if not claims.get('email') or claims.get('email_verified') is not True:
        raise GoogleTokenError('email not verified')
    return claims


def _new_username(email):
    base = re.sub(r'[^\w.+-]', '', email.split('@')[0])[:30] or 'keeper'
    username, n = base, 1
    while username_taken(username):
        n += 1
        username = f'{base}{n}'
    return username


@transaction.atomic
def account_for_google(claims):
    """The account the Google identity signs in to, linking or creating it. Returns (account, created)."""
    account = Account.objects.select_for_update().filter(google_id=claims['sub']).first()
    if account is not None:
        return account, False

    account = Account.objects.select_for_update().filter(email__iexact=claims['email']).first()
    if account is None:
        account = Account(username=_new_username(claims['email']), email=claims['email'], email_verified=True)
        account.set_unusable_password()
        account.google_id = claims['sub']
        account.save()
        return account, True

    if not account.is_active:
        return account, False  # refused by the view; a disabled account is left exactly as it is
    if not account.email_verified:
        # Nobody had proved they own this address, so the password may belong to someone who typed in
        # another person's email to take it over later. Google has proved ownership; that password and its
        # sessions go (the owner can set one with "Forgot password?").
        account.set_unusable_password()
        for token in OutstandingToken.objects.filter(user=account):
            BlacklistedToken.objects.get_or_create(token=token)
    account.google_id = claims['sub']
    account.email_verified = True
    account.save()
    return account, False
