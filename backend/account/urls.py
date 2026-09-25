from django.urls import path
from .views import UserRegister, UserLogin, UserLogout, UserProfile, AccountPlans

urlpatterns = [
    path('register/', UserRegister.as_view(), name='register'),
    path('login/', UserLogin.as_view(), name='login'),
    path('logout/', UserLogout.as_view(), name='logout'),
    path('profile/', UserProfile.as_view(), name='profile'),
    path('plans/', AccountPlans.as_view(), name='account-plans'),
]
