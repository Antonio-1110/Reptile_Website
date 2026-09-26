from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone

from . import moderation
from .models import Species, LiveAnimalPost, EquipmentPost, ContactRequest, Report


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


class ListingAdmin(admin.ModelAdmin):
    """Shared by both listing types: hidden listings and their open reports, with hide/unhide actions."""
    list_display = ('id', 'title', 'account', 'is_hidden', 'pending_reports', 'created_at')
    list_filter = ('is_hidden',)
    search_fields = ('title', 'account__username')
    actions = ('hide_listings', 'unhide_listings')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _pending_reports=Count('reports', filter=Q(reports__status=Report.Status.PENDING)),
        )

    @admin.display(description='Pending reports', ordering='_pending_reports')
    def pending_reports(self, listing):
        return listing._pending_reports

    @admin.action(description='Hide the selected listings')
    def hide_listings(self, request, queryset):
        for listing in queryset:
            moderation.set_hidden(listing, True)

    @admin.action(description='Show the selected listings again')
    def unhide_listings(self, request, queryset):
        for listing in queryset:
            moderation.set_hidden(listing, False)


admin.site.register(LiveAnimalPost, ListingAdmin)
admin.site.register(EquipmentPost, ListingAdmin)


@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'post', 'created_at')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """
    The moderation queue: filter by "Pending review", look at the listing, then hide it and resolve
    the reports, or dismiss them. Listings can also hide themselves after enough reports
    (REPORT_AUTO_HIDE_THRESHOLD).
    """
    list_display = ('id', 'post', 'listing_hidden', 'reporter', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('live_animal_post__title', 'equipment_post__title', 'reporter__username')
    readonly_fields = ('reporter', 'live_animal_post', 'equipment_post', 'created_at', 'reviewed_by', 'reviewed_at')
    list_select_related = ('reporter', 'live_animal_post', 'equipment_post', 'reviewed_by')
    actions = ('hide_and_resolve', 'resolve', 'dismiss', 'unhide_listing')

    @admin.display(boolean=True, description='Listing hidden')
    def listing_hidden(self, report):
        return report.post.is_hidden

    @admin.action(description='Hide the reported listings and resolve their reports')
    def hide_and_resolve(self, request, queryset):
        for report in queryset:
            moderation.set_hidden(report.post, True)
        moderation.review_reports(queryset, Report.Status.RESOLVED, request.user)

    @admin.action(description='Resolve (action taken elsewhere)')
    def resolve(self, request, queryset):
        moderation.review_reports(queryset, Report.Status.RESOLVED, request.user)

    @admin.action(description='Dismiss (nothing wrong) and show the listings again')
    def dismiss(self, request, queryset):
        for report in queryset:
            moderation.set_hidden(report.post, False)
        moderation.review_reports(queryset, Report.Status.DISMISSED, request.user)

    @admin.action(description='Show the reported listings again')
    def unhide_listing(self, request, queryset):
        for report in queryset:
            moderation.set_hidden(report.post, False)

    def save_model(self, request, obj, form, change):
        # Changing a report's status by hand records the reviewer too.
        if change and 'status' in form.changed_data and obj.status != Report.Status.PENDING:
            obj.reviewed_by, obj.reviewed_at = request.user, timezone.now()
        super().save_model(request, obj, form, change)
