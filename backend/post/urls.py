from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiveAnimalViewSet, EquipmentViewSet, SpeciesViewSet

router = DefaultRouter()
router.register(r'live-animals', LiveAnimalViewSet, basename='live-animal')
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'species', SpeciesViewSet, basename='species')

urlpatterns = [
    path('', include(router.urls)),
]