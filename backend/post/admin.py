from django.contrib import admin
from .models import Species, LiveAnimalPost, EquipmentPost, ContactRequest, Favorite, Report

# Register your models here.
@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
@admin.register(LiveAnimalPost)
class LiveAnimalAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'account', 'created_at')

@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'post', 'created_at')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'post', 'created_at')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'post', 'created_at')
