from django.core.management import CommandError, call_command
from django.test import override_settings
from django.test.runner import DiscoverRunner


class CompilingTestRunner(DiscoverRunner):
    """Compiles the translation catalogs before the tests run. The compiled .mo files aren't committed
    (git can't merge binary files, so every branch that touched translations conflicted), and some tests
    check Chinese responses, so they need a catalog built from the current .po.

    It also hashes passwords with a fast hasher. The real one is slow on purpose, and the suite creates
    hundreds of accounts: it took the run from about 10 seconds to almost 5 minutes."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        # override_settings (not a plain assignment) so Django's cached hasher list is rebuilt.
        self._fast_hashers = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
        self._fast_hashers.enable()
        try:
            call_command('compilemessages', verbosity=0, ignore_patterns=['.venv', '.e2e', 'media'])
        except CommandError as error:
            print(f'Warning: could not compile translations ({error}). Install GNU gettext; '
                  'tests of Chinese responses will fail.')

    def teardown_test_environment(self, **kwargs):
        self._fast_hashers.disable()
        super().teardown_test_environment(**kwargs)
