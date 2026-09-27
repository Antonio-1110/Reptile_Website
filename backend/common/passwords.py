import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class LettersAndNumbersValidator:
    """
    A password needs at least one English letter and one digit. With MinimumLengthValidator this is
    the whole policy the sign-up and reset forms list (Frontend/src/constants/passwordRules.js).
    """

    def validate(self, password, user=None):
        if not (re.search(r'[A-Za-z]', password) and re.search(r'\d', password)):
            raise ValidationError(
                _('Your password must contain both English letters and numbers.'),
                code='password_needs_letters_and_numbers',
            )

    def get_help_text(self):
        return _('Your password must contain both English letters and numbers.')
