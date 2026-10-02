from django.contrib import admin

from .models import FeatureSwitch


@admin.register(FeatureSwitch)
class FeatureSwitchAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'enabled', 'updated_at')
    list_editable = ('enabled',)
    fields = ('name', 'description', 'enabled', 'updated_at')
    readonly_fields = ('name', 'description', 'updated_at')

    # Switches are declared in code (features/switches.py); the admin only turns them on and off.
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
