from django.db import models

from . import switches


class FeatureSwitch(models.Model):
    """The stored state of a switch declared in features/switches.py."""
    name = models.CharField(max_length=50, unique=True)
    enabled = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def description(self):
        return switches.description(self.name)
