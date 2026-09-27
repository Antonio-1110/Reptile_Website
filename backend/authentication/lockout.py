"""
Refuses password sign-in for a while after repeated failures, on the Django admin and the browsable
API's login page (the JWT login has its own rate limit). Bots try common passwords on /admin/ all day.

Failures are counted per username and per client address (the one Heroku's router saw, see
NUM_PROXIES), in the cache. Counting per username means someone who knows a staff username can keep
that account locked out; the admin's address being configurable (DJANGO_ADMIN_URL) makes that harder.
"""
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from rest_framework.throttling import BaseThrottle


def _keys(request, username):
    keys = [f'login-failures:user:{username.strip().lower()}'] if username else []
    if request is not None:
        keys.append(f'login-failures:ip:{BaseThrottle().get_ident(request)}')
    return keys


class LoginLockoutMixin:
    def clean(self):
        keys = _keys(self.request, self.cleaned_data.get('username'))
        if any(cache.get(key, 0) >= settings.LOGIN_LOCKOUT_FAILURES for key in keys):
            raise ValidationError(
                _('Too many failed sign-in attempts. Please wait %(minutes)s minutes and try again.')
                % {'minutes': settings.LOGIN_LOCKOUT_MINUTES},
                code='locked_out',
            )
        try:
            return super().clean()
        except ValidationError:
            # Each failure restarts the wait, so the lock lasts LOGIN_LOCKOUT_MINUTES after the last try.
            for key in keys:
                cache.set(key, cache.get(key, 0) + 1, timeout=settings.LOGIN_LOCKOUT_MINUTES * 60)
            raise


class LockoutAdminAuthenticationForm(LoginLockoutMixin, AdminAuthenticationForm):
    pass


class LockoutAuthenticationForm(LoginLockoutMixin, AuthenticationForm):
    pass
