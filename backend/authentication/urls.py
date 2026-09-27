from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView, LogoutView, MeView, PasswordResetConfirmView, PasswordResetRequestView, RegisterView,
    ResendVerificationView, VerifyEmailView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='jwt-register'),
    path('login/', LoginView.as_view(), name='jwt-login'),
    path('refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('logout/', LogoutView.as_view(), name='jwt-logout'),
    path('me/', MeView.as_view(), name='jwt-me'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('verify-email/resend/', ResendVerificationView.as_view(), name='verify-email-resend'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
