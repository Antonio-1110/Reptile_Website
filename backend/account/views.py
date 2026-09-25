from django.shortcuts import render
from django.db.models import Count, Q
from rest_framework.generics import GenericAPIView, RetrieveAPIView, RetrieveUpdateAPIView, get_object_or_404
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
from django.utils.translation import gettext as _
from . import reviews
from .serializers import UserRegisterSerializer, UserLoginSerializer, AccountSerializer, ProfileAccountSerializer, ReviewSerializer, SellerProfileSerializer
from .models import Account, Review

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



def public_sellers():
    """Accounts with a public profile: active, and they've listed something (see SellerProfile)."""
    return Account.objects.filter(is_active=True).annotate(
        live_animal_count=Count('liveanimalpost_posts', distinct=True),
        equipment_count=Count('equipmentpost_posts', distinct=True),
    ).filter(Q(live_animal_count__gt=0) | Q(equipment_count__gt=0))


class SellerProfile(RetrieveAPIView):
    """
    A seller's public profile. Only accounts that have listed something have one: otherwise any
    account id would reveal a buyer's name.
    """
    serializer_class = SellerProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return public_sellers()


class SellerReviews(GenericAPIView):
    """
    GET: a seller's reviews, newest first (public). POST: write or update your review
    ({rating: 1-5, comment}); only if you contacted the seller about a listing or bought from them at
    auction. DELETE: remove your review. The seller's rating is recomputed each time.
    """
    serializer_class = ReviewSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'report'  # same abuse profile as reports: a few per hour is plenty

    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == 'GET' else [permissions.IsAuthenticated()]

    def get_throttles(self):
        return [] if self.request.method == 'GET' else super().get_throttles()

    def seller(self):
        return get_object_or_404(public_sellers(), pk=self.kwargs['pk'])

    def get(self, request, pk):
        queryset = Review.objects.filter(seller=self.seller()).select_related('reviewer')
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def post(self, request, pk):
        seller = self.seller()
        if not reviews.can_review(request.user, seller):
            return Response(
                {'detail': _('You can review a seller after contacting them about a listing or buying from them.')},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review, created = reviews.save_review(
            request.user, seller, serializer.validated_data['rating'], serializer.validated_data.get('comment', ''),
        )
        return Response(self.get_serializer(review).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, pk):
        if not reviews.delete_review(request.user, self.seller()):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
