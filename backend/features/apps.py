from django.apps import AppConfig
from django.db.models.signals import post_migrate


class FeaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'features'

    def ready(self):
        from .switches import create_missing_switches
        # Every declared switch gets a row (at its default) so staff can find and flip it in the admin.
        post_migrate.connect(create_missing_switches, sender=self)
