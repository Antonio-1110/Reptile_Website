from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, LogoutView, MeView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='jwt-register'),
    path('login/', LoginView.as_view(), name='jwt-login'),
    path('refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('logout/', LogoutView.as_view(), name='jwt-logout'),
    path('me/', MeView.as_view(), name='jwt-me'),
]
