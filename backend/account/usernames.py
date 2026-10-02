"""
Choosing and changing usernames. Seller pages and links use the account id, so a new username breaks no
links; these rules are about people recognising each other:
- names that differ only in case are the same name, so "Apex_Exotics" can't pass for "apex_exotics";
- an account can change its username once every USERNAME_CHANGE_DAYS days, so a seller can't keep
  shedding a name buyers have learned to avoid;
- a name given up stays reserved that long, so nobody can take a name buyers know straight after its
  owner leaves it.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import Account, UsernameChange

# Changes this soon after joining don't count and aren't recorded: fixing a typo, or the choose-username
# step after Google sign-in, whose first name was made from the email address and shouldn't be kept.
NEW_ACCOUNT_GRACE = timedelta(days=1)


def _window():
    return timedelta(days=settings.USERNAME_CHANGE_DAYS)


def username_taken(name, account=None):
    """Whether an account other than `account` uses `name` or gave it up recently."""
    others = Account.objects.exclude(pk=account.pk) if account else Account.objects.all()
    if others.filter(username__iexact=name).exists():
        return True
    if not settings.USERNAME_CHANGE_DAYS:
        return False
    held = UsernameChange.objects.filter(old_username__iexact=name, changed_at__gte=timezone.now() - _window())
    if account:
        held = held.exclude(account=account)
    return held.exists()


def next_change_at(account):
    """When the account may change its username again, or None if it may now."""
    if not settings.USERNAME_CHANGE_DAYS:
        return None
    last = account.username_changes.order_by('-changed_at').first()
    available = last.changed_at + _window() if last else None
    return available if available and available > timezone.now() else None


def record_change(account, old_username):
    if timezone.now() - account.date_joined < NEW_ACCOUNT_GRACE:
        return
    UsernameChange.objects.create(account=account, old_username=old_username, new_username=account.username)
