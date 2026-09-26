from django.core.management import CommandError, call_command
from django.test.runner import DiscoverRunner


class CompilingTestRunner(DiscoverRunner):
    """Compiles the translation catalogs before the tests run. The compiled .mo files aren't committed
    (git can't merge binary files, so every branch that touched translations conflicted), and some tests
    check Chinese responses, so they need a catalog built from the current .po."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        try:
            call_command('compilemessages', verbosity=0, ignore_patterns=['.venv', '.e2e', 'media'])
        except CommandError as error:
            print(f'Warning: could not compile translations ({error}). Install GNU gettext; '
                  'tests of Chinese responses will fail.')
