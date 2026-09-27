"""
Emails to users. Accounts have no stored language preference, so every email carries each supported
language (English first) in one message.
"""
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import translation
from django.utils.translation import gettext_lazy

# Labels for Account.contact_details() keys.
CONTACT_LABELS = {
    'username': gettext_lazy('Username'),
    'name': gettext_lazy('Display name'),
    'email': gettext_lazy('Email'),
    'phone': gettext_lazy('Phone'),
    'line': 'LINE',
    'instagram': 'Instagram',
    'facebook': 'Facebook',
}


def contact_lines(details):
    """Account.contact_details() as "Label: value" lines, in the active language."""
    return '\n'.join(f'{CONTACT_LABELS[key]}: {value}' for key, value in details.items())


def send_notification(recipients, build, reply_to=None):
    """
    Send one email to `recipients`. `build()` returns (subject, body) in the active language; it's
    called once per language in settings.LANGUAGES and the results are joined. `reply_to` is an
    address the recipient's "Reply" should go to instead of our no-reply sender.
    """
    recipients = [address for address in recipients if address]
    if not recipients:
        return
    subjects, bodies = [], []
    for language_code, _name in settings.LANGUAGES:
        with translation.override(language_code):
            subject, body = build()
            subjects.append(str(subject))
            bodies.append(body)
    EmailMessage(
        subject=' / '.join(dict.fromkeys(subjects)),
        body='\n\n————————\n\n'.join(bodies),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
        reply_to=[reply_to] if reply_to else None,
    ).send(fail_silently=True)
