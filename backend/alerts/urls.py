from rest_framework.routers import SimpleRouter

from .views import AlertViewSet

router = SimpleRouter()
router.register('', AlertViewSet, basename='alert')

urlpatterns = router.urls
