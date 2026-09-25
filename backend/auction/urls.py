from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuctionViewSet, OrderViewSet

router = DefaultRouter()
# Orders first: the auction routes would otherwise read "orders" as an auction id.
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'', AuctionViewSet, basename='auction')

urlpatterns = [
    path('', include(router.urls)),
]
