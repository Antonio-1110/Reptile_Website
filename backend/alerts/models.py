from django.db import models

from account.models import Account


class Alert(models.Model):
    """
    A notice for one account, shown on the site's Alerts page (price drops, saved-search matches,
    species reviews, auction and order steps). Accounts have no stored language, so the text is kept
    in every supported language and the API answers in the reader's (see alerts/services.py).
    Unread alerts that pile up are emailed as one summary (`manage.py send_alert_digests`).
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='alerts')
    text = models.JSONField(help_text='{language code: {"title": …, "body": …}}')
    link = models.CharField(max_length=300, blank=True, help_text='A path on the website, e.g. /posts/12')
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    # Set once the alert went out by email (right away or in a summary), so it's never emailed twice.
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['account', 'read_at'], name='alert_account_read_idx')]

    def __str__(self):
        return f'{self.account} — {self.text.get("en", {}).get("title", "")}'
