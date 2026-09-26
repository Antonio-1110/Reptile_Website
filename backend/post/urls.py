from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiveAnimalViewSet, EquipmentViewSet, SavedSearchViewSet, SpeciesViewSet

router = DefaultRouter()
router.register(r'live-animals', LiveAnimalViewSet, basename='live-animal')
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'species', SpeciesViewSet, basename='species')
router.register(r'saved-searches', SavedSearchViewSet, basename='saved-search')

urlpatterns = [
    path('', include(router.urls)),
]