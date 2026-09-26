from django.urls import path

from .views import AccountPlans, UserProfile

urlpatterns = [
    # The signed-in user's editable profile with post quota (the listing editor and settings use it),
    # and the public plan comparison.
    path('profile/', UserProfile.as_view(), name='profile'),
    path('plans/', AccountPlans.as_view(), name='account-plans'),
]
