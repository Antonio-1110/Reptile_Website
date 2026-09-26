from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Q
from django.utils import timezone

from . import moderation
from . import species as species_catalog
from .models import Species, SpeciesAlias, SpeciesRequest, LiveAnimalPost, EquipmentPost, ContactRequest, Favorite, Report


class SpeciesAliasInline(admin.TabularInline):
    model = SpeciesAlias
    extra = 1


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'alias_names')
    search_fields = ('name', 'aliases__name')
    inlines = (SpeciesAliasInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('aliases')

    @admin.display(description='Aliases')
    def alias_names(self, species):
        return ', '.join(alias.name for alias in species.aliases.all())


class SpeciesRequestReviewForm(forms.ModelForm):
    """One decision per request; post/species.py carries it out and emails the waiting sellers."""
    MAP, CREATE, REJECT = 'map', 'create', 'reject'
    decision = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Decide later'),
            (MAP, 'Same as an existing species (choose it below; the name is kept as an alias)'),
            (CREATE, 'Add it as a new species'),
            (REJECT, 'Reject (the sellers choose a listed species instead)'),
        ],
    )
    new_species_name = forms.CharField(
        required=False, max_length=100,
        help_text='For "Add it as a new species": the name to list it under. Leave empty to use the requested name.',
    )

    class Meta:
        model = SpeciesRequest
        fields = ('decision', 'species', 'new_species_name', 'staff_note')
        help_texts = {
            'species': 'For "Same as an existing species".',
            'staff_note': 'For "Reject": the reason, emailed to the sellers and shown on their listing.',
        }

    def clean(self):
        cleaned = super().clean()
        decision = cleaned.get('decision')
        if decision == self.MAP and not cleaned.get('species'):
            self.add_error('species', 'Choose the species this name means.')
        if decision == self.CREATE:
            name = cleaned.get('new_species_name') or self.instance.name
            existing = species_catalog.find_species(name)
            if existing:
                self.add_error('new_species_name', f'"{existing}" already exists (or has this alias); choose it as an existing species instead.')
        return cleaned


@admin.register(SpeciesRequest)
class SpeciesRequestAdmin(admin.ModelAdmin):
    """
    The species review queue: filter by "Pending review", then map each name to an existing species,
    add it as a new one, or reject it. Its listings are published (or their sellers told) right away.
    """
    form = SpeciesRequestReviewForm
    list_display = ('name', 'status', 'waiting_listings', 'species', 'created_at', 'reviewed_by')
    list_filter = ('status',)
    search_fields = ('name',)
    list_select_related = ('species', 'reviewed_by')
    readonly_fields = ('name', 'status', 'waiting_listings', 'created_at', 'reviewed_by', 'reviewed_at')
    actions = ('add_as_new_species',)

    def has_add_permission(self, request):
        return False  # requests come from sellers' listings

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_waiting=Count('listings'))

    def get_fields(self, request, obj=None):
        fields = ('name', 'status', 'waiting_listings', 'created_at', 'reviewed_by', 'reviewed_at')
        if obj and obj.status == SpeciesRequest.Status.APPROVED:
            return fields + ('species',)
        return fields + ('decision', 'species', 'new_species_name', 'staff_note')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == SpeciesRequest.Status.APPROVED:
            return self.readonly_fields + ('species',)
        return self.readonly_fields

    @admin.display(description='Listings waiting', ordering='_waiting')
    def waiting_listings(self, species_request):
        return species_request._waiting

    def save_model(self, request, obj, form, change):
        decision = form.cleaned_data.get('decision')
        if decision == form.MAP:
            count = species_catalog.approve(obj, form.cleaned_data['species'], request.user)
        elif decision == form.CREATE:
            count = species_catalog.create_and_approve(obj, request.user, form.cleaned_data.get('new_species_name'))
        elif decision == form.REJECT:
            count = species_catalog.reject(obj, request.user, form.cleaned_data.get('staff_note', ''))
        else:
            super().save_model(request, obj, form, change)
            return
        self.message_user(request, f'"{obj.name}" {obj.get_status_display().lower()}; {count} listing(s) updated and their sellers emailed.')

    @admin.action(description='Add the requested names as new species')
    def add_as_new_species(self, request, queryset):
        for species_request in queryset.filter(status=SpeciesRequest.Status.PENDING):
            existing = species_catalog.find_species(species_request.name)
            if existing:
                self.message_user(request, f'"{species_request.name}" matches "{existing}"; open it to map it instead.', messages.WARNING)
                continue
            species_catalog.create_and_approve(species_request, request.user)


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


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'post', 'created_at')
