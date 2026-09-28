from django.contrib import admin
from .models import Account
from django.contrib.auth.admin import UserAdmin

# Register your models here.
@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'email_verified', 'phone_number', 'personal_id', 'line_id', 'seller_rating', 'verified_seller')
    list_filter = UserAdmin.list_filter + ('email_verified',)
    # Lets staff confirm an address by hand for someone who can't receive the link.
    fieldsets = UserAdmin.fieldsets + (('Email', {'fields': ('email_verified', 'google_id')}),)
    readonly_fields = ('google_id',)