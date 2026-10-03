from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', '__str__', 'created_at', 'read_at', 'emailed_at')
    list_filter = ('read_at', 'emailed_at')
    search_fields = ('account__username', 'account__email')
    raw_id_fields = ('account',)
