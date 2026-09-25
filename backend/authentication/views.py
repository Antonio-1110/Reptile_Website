from rest_framework import generics, permissions
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import MeSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ — creates a new user, no token issued (log in separately)."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — SimpleJWT's token pair view, rate limited against password guessing."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ — returns the authenticated user's profile."""
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
