import json
import os
import uuid

from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.parsers import FormParser, MultiPartParser
from common.notifications import contact_lines, send_notification
from .serializer import (
    SavedSearchSerializer,
    LiveAnimalPostSerializer, EquipmentPostSerializer, SpeciesSerializer,
    ListingPhotoUploadSerializer,
)
from .filters import EquipmentPostFilter, LiveAnimalPostFilter
from django.db.models import Q
from . import moderation
from .models import LiveAnimalPost, EquipmentPost, Species, ContactRequest, Report, SavedSearch
from .search_alerts import SEARCH_FIELDS as LIVE_ANIMAL_SEARCH_FIELDS
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

# Create your views here.

class IsPostOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.account == request.user


def send_inquiry_to_seller(requester, post):
    """Email the seller the interested buyer's contact details, so the seller can reach out."""
    values = {'name': requester.get_display_name(), 'title': post.title}

    def build():
        subject = _('New inquiry about your listing: %(title)s') % values
        body = (
            _('%(name)s is interested in your listing "%(title)s" on the Reptile Marketplace and asked us to pass on their contact details:') % values
            + '\n\n' + contact_lines(requester.contact_details()) + '\n\n'
            + _('Please contact them directly. We never share your own contact details with buyers who ask.')
        )
        return subject, body

    send_notification([post.account.email], build)


class ContactSellerMixin:
    """
    Adds a `/contact/` action that passes the requester's contact details on to the seller, who then
    gets in touch. The seller's own details are never revealed here (that would let anyone with an
    account harvest them); they're only shared with a buyer who has paid (see auction.services).
    GET previews exactly what would be sent; POST sends it.
    """
    contact_request_field = None  # set by subclass to 'live_animal_post' or 'equipment_post'
    throttle_scope = None  # set per action (DRF only accepts action options that exist on the class)

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticated],
            throttle_classes=[ScopedRateThrottle], throttle_scope='contact')
    def contact(self, request, pk=None):
        post = self.get_object()
        requester = request.user

        if post.account_id == requester.id:
            return Response(
                {'detail': _("You can't contact yourself about your own listing.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requests = ContactRequest.objects.filter(requester=requester, **{self.contact_request_field: post})
        if request.method == 'GET':
            return Response({'contact': requester.contact_details(), 'already_sent': requests.exists()})

        # Only the first request per buyer/listing emails the seller, so repeat clicks can't spam them.
        if not requests.exists():
            ContactRequest.objects.create(requester=requester, **{self.contact_request_field: post})
            send_inquiry_to_seller(requester, post)

        return Response({
            'detail': _("We've sent your contact details to the seller. They'll get in touch with you."),
            'contact': requester.contact_details(),
        })


class ReportListingMixin:
    """Adds a `/report/` action that flags a listing for manual moderation review."""
    report_request_field = None  # set by subclass to 'live_animal_post' or 'equipment_post'
    throttle_scope = None  # set per action

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated],
            throttle_classes=[ScopedRateThrottle], throttle_scope='report')
    def report(self, request, pk=None):
        post = self.get_object()
        reporter = request.user

        if post.account_id == reporter.id:
            return Response(
                {'detail': _("You can't report your own listing.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_reported = Report.objects.filter(
            reporter=reporter, **{self.report_request_field: post}
        ).exists()

        if not already_reported:
            Report.objects.create(reporter=reporter, **{self.report_request_field: post})
            moderation.hide_if_reported_enough(post)

        return Response({
            'detail': _("Thanks — we've received your report and our team will review this listing."),
        })


class HiddenListingsMixin:
    """Listings hidden by moderation are invisible (404) to everyone but their owner and staff."""

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset
        visible = Q(is_hidden=False)
        if user.is_authenticated:
            visible |= Q(account=user)
        return queryset.filter(visible)


class ListingPhotosMixin:
    """
    Adds a `/photos/` action that sets a listing's photos: uploads new ones, and keeps, reorders or
    removes existing ones (see ListingPhotoUploadSerializer for the two request forms).
    """

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def photos(self, request, pk=None):
        post = self.get_object()  # IsPostOwnerOrReadOnly limits this to the listing's owner
        data = {'photos': request.FILES.getlist('photos'), 'cover_index': request.data.get('cover_index', 0)}
        if 'order' in request.data:
            # Multipart can't carry a list of strings cleanly, so `order` arrives as a JSON array.
            try:
                data['order'] = json.loads(request.data['order'])
            except (TypeError, ValueError):
                return Response({'order': [_('Send the photo order as a JSON list.')]}, status=status.HTTP_400_BAD_REQUEST)
        upload = ListingPhotoUploadSerializer(data=data, context={'request': request, 'post': post})
        upload.is_valid(raise_exception=True)
        photos = upload.validated_data['photos']

        folder = f'listings/{post._meta.model_name}/{post.pk}'
        new_urls = []
        for photo in photos:
            extension = os.path.splitext(photo.name)[1].lower() or '.jpg'
            name = default_storage.save(f'{folder}/{uuid.uuid4().hex}{extension}', photo)
            new_urls.append(request.build_absolute_uri(default_storage.url(name)))

        prefix = ListingPhotoUploadSerializer.NEW_PREFIX
        ordered = [
            new_urls[int(entry[len(prefix):])] if entry.startswith(prefix) else entry
            for entry in upload.validated_data['order']
        ]
        previous_urls = set(post.gallery or []) | ({post.image} if post.image else set())
        post.image = ordered[0] if ordered else ''
        post.gallery = ordered
        post.save(update_fields=['image', 'gallery', 'updated_at'])
        self._delete_uploaded_photos(request, previous_urls - set(ordered))

        return Response(self.get_serializer(post).data)

    @staticmethod
    def _delete_uploaded_photos(request, urls):
        # Only remove files this app stored; seeded or external URLs are left alone.
        media_prefix = request.build_absolute_uri(settings.MEDIA_URL)
        for url in urls:
            if url.startswith(media_prefix):
                default_storage.delete(url[len(media_prefix):])


class OwnListingsMixin:
    """Adds a `/mine/` action so sellers can list and manage their own listings."""

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(account=request.user))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """List all available species"""
    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    permission_classes = [permissions.AllowAny]


class LiveAnimalViewSet(HiddenListingsMixin, ContactSellerMixin, ReportListingMixin, OwnListingsMixin, ListingPhotosMixin, viewsets.ModelViewSet):
    queryset = LiveAnimalPost.objects.select_related('account', 'species').all()
    serializer_class = LiveAnimalPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsPostOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LiveAnimalPostFilter
    search_fields = LIVE_ANIMAL_SEARCH_FIELDS
    ordering_fields = ['price', 'created_at', 'age_years', 'weight_grams', 'size_cm']
    ordering = ['-created_at', '-id']
    contact_request_field = 'live_animal_post'
    report_request_field = 'live_animal_post'
    
    def perform_create(self, serializer):
        serializer.save(account=self.request.user)


class EquipmentViewSet(HiddenListingsMixin, ContactSellerMixin, ReportListingMixin, OwnListingsMixin, ListingPhotosMixin, viewsets.ModelViewSet):
    queryset = EquipmentPost.objects.select_related('account').all()
    serializer_class = EquipmentPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsPostOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EquipmentPostFilter
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at', '-id']
    contact_request_field = 'equipment_post'
    report_request_field = 'equipment_post'
    
    def perform_create(self, serializer):
        serializer.save(account=self.request.user)

class SavedSearchViewSet(viewsets.ModelViewSet):
    """
    The signed-in user's saved marketplace searches (list, save, rename, delete). Each is emailed about
    when new listings match it (manage.py send_search_alerts).
    """
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        return SavedSearch.objects.filter(account=self.request.user)

    def perform_create(self, serializer):
        # Alerts cover listings posted from now on, not everything that already matches.
        serializer.save(account=self.request.user, last_alerted_at=timezone.now())
