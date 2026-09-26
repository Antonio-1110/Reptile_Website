from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from account.views import AccountPlans, UserProfile

from .views import LoginView, MeView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='jwt-register'),
    path('login/', LoginView.as_view(), name='jwt-login'),
    path('refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('me/', MeView.as_view(), name='jwt-me'),
    # The signed-in user's editable profile with post quota (the listing editor and settings use it),
    # and the public plan comparison.
    path('profile/', UserProfile.as_view(), name='profile'),
    path('plans/', AccountPlans.as_view(), name='account-plans'),
]
