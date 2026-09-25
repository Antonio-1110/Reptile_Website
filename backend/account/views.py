from django.shortcuts import render
from django.db.models import Count, Q
from rest_framework.generics import GenericAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
from django.utils.translation import gettext as _
from .serializers import UserRegisterSerializer, UserLoginSerializer, AccountSerializer, ProfileAccountSerializer, SellerProfileSerializer
from .models import Account

# Create your views here.

class UserRegister(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegisterSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate token for new user (optional, for token auth)
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': AccountSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)


class UserLogin(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate token (optional, for token auth)
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': AccountSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_200_OK)


class UserLogout(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        logout(request)
        return Response({
            'message': _('Logged out successfully')
        }, status=status.HTTP_200_OK)


class UserProfile(RetrieveUpdateAPIView):
    """Get or update current user profile"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileAccountSerializer
    
    def get_object(self):
        return self.request.user
    
    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class AccountPlans(APIView):
    """Public list of account plans and their limits, for the upgrade page. Limits are read from the
    Account model so this never drifts from what the API actually enforces."""
    permission_classes = [permissions.AllowAny]

    PLANS = [
        ('hobbyist', Account.AccountType.HOBBYIST, False),
        ('commercial', Account.AccountType.COMMERCIAL, False),
        ('commercial_paid', Account.AccountType.COMMERCIAL, True),
    ]

    def get(self, request):
        plans = []
        for plan_id, account_type, is_paid in self.PLANS:
            account = Account(account_type=account_type, is_paid_account=is_paid)
            plans.append({
                'id': plan_id,
                'account_type': account_type,
                'is_paid_account': is_paid,
                'max_post_count': account.max_post_count,
                'max_images_per_post': account.max_images_per_post,
                'can_start_auction': account.can_start_auction,
            })
        return Response(plans)



class SellerProfile(RetrieveAPIView):
    """
    A seller's public profile. Only accounts that have listed something have one: otherwise any
    account id would reveal a buyer's name.
    """
    serializer_class = SellerProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Account.objects.filter(is_active=True).annotate(
            live_animal_count=Count('liveanimalpost_posts', distinct=True),
            equipment_count=Count('equipmentpost_posts', distinct=True),
        ).filter(Q(live_animal_count__gt=0) | Q(equipment_count__gt=0))
