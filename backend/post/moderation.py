"""
Moderation of reported listings, in one place so the report endpoint and the admin behave the same.
A hidden listing is visible only to its owner and staff; reports move from PENDING to RESOLVED
(action taken) or DISMISSED (nothing wrong).
"""
from django.conf import settings
from django.core.mail import mail_admins
from django.db import transaction
from django.utils import timezone

from .models import Report


def _post_field(post):
    return 'live_animal_post' if post._meta.model_name == 'liveanimalpost' else 'equipment_post'


def pending_reporter_count(post):
    return Report.objects.filter(status=Report.Status.PENDING, **{_post_field(post): post}).values('reporter').distinct().count()


def hide_if_reported_enough(post):
    """After a new report: hide the listing once enough different accounts have reported it."""
    threshold = settings.REPORT_AUTO_HIDE_THRESHOLD
    if threshold <= 0 or post.is_hidden or pending_reporter_count(post) < threshold:
        return False
    set_hidden(post, True)
    transaction.on_commit(lambda: mail_admins(
        f'Listing hidden after {threshold} reports: {post.title}',
        f'"{post.title}" (#{post.pk}, by {post.account}) was reported by {threshold} accounts and is now hidden. '
        'Review it in the admin: Reports, filtered by status "Pending review".',
        fail_silently=True,
    ))
    return True


def set_hidden(post, hidden):
    post.is_hidden = hidden
    post.save(update_fields=['is_hidden', 'updated_at'])


def review_reports(reports, status, staff_user, note=''):
    """Close pending reports as RESOLVED or DISMISSED, recording who reviewed them and when."""
    fields = {'status': status, 'reviewed_by': staff_user, 'reviewed_at': timezone.now()}
    if note:
        fields['staff_note'] = note
    return reports.filter(status=Report.Status.PENDING).update(**fields)
