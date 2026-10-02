from django.contrib import admin
from .models import Account, UsernameChange
from django.contrib.auth.admin import UserAdmin


class UsernameChangeInline(admin.TabularInline):
    """The names an account used before, e.g. to match a report that names a seller by an old name."""
    model = UsernameChange
    fields = readonly_fields = ('old_username', 'new_username', 'changed_at')
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# Register your models here.
@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'account_type', 'is_paid_account', 'email_verified', 'phone_number', 'personal_id', 'line_id', 'seller_rating', 'verified_seller')
    list_filter = UserAdmin.list_filter + ('account_type', 'is_paid_account', 'email_verified')
    fieldsets = UserAdmin.fieldsets + (
        # Until plans can be paid for online, staff grant Commercial (and Pro, with "paid account") to
        # sellers who ask by email. Nobody can change these on their own account.
        ('Plan', {'fields': ('account_type', 'is_paid_account')}),
        # Lets staff confirm an address by hand for someone who can't receive the link.
        ('Email', {'fields': ('email_verified', 'google_id')}),
    )
    readonly_fields = ('google_id',)
    inlines = [UsernameChangeInline]
    # Search finds accounts by a name they gave up, too.
    search_fields = UserAdmin.search_fields + ('username_changes__old_username',)
