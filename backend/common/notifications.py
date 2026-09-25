"""
Emails to users. Accounts have no stored language preference, so every email carries each supported
language (English first) in one message.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import gettext_lazy

# Labels for Account.contact_details() keys.
CONTACT_LABELS = {
    'name': gettext_lazy('Name'),
    'email': gettext_lazy('Email'),
    'phone': gettext_lazy('Phone'),
    'line': 'LINE',
    'instagram': 'Instagram',
    'facebook': 'Facebook',
}


def contact_lines(details):
    """Account.contact_details() as "Label: value" lines, in the active language."""
    return '\n'.join(f'{CONTACT_LABELS[key]}: {value}' for key, value in details.items())


def send_notification(recipients, build):
    """
    Send one email to `recipients`. `build()` returns (subject, body) in the active language; it's
    called once per language in settings.LANGUAGES and the results are joined.
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
    send_mail(
        subject=' / '.join(dict.fromkeys(subjects)),
        message='\n\n————————\n\n'.join(bodies),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )
