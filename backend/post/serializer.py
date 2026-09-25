import json
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers
from .models import EquipmentPost, LiveAnimalPost, SavedSearch, Species
from account.serializers import PublicSellerSerializer


class PostLimitSerializerMixin:
    def validate(self, attrs):
        account = self.context['request'].user
        existing_post_count = LiveAnimalPost.objects.filter(account=account).count()
        existing_post_count += EquipmentPost.objects.filter(account=account).count()

        if self.instance is None and not account.can_create_post(existing_post_count):
            raise serializers.ValidationError({
                'detail': _('Post limit reached. This account allows %(count)s posts.') % {'count': account.max_post_count}
            })

        image = attrs.get('image', getattr(self.instance, 'image', ''))
        gallery = attrs.get('gallery', getattr(self.instance, 'gallery', [])) or []
        # The cover is normally also the first gallery entry, so count distinct photos.
        image_count = len(set(gallery) | ({image} if image else set()))
        if not account.can_upload_images(image_count):
            raise serializers.ValidationError({
                'gallery': _('Image limit exceeded. This account allows %(count)s images per post.') % {'count': account.max_images_per_post}
            })

        return attrs

class OwnerOnlyContactInfoMixin:
    """Only the listing's owner sees contact_info; everyone else gets it via the /contact/ action."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not request or instance.account_id != request.user.id:
            data.pop('contact_info', None)
        return data


MAX_PHOTO_SIZE_BYTES = 5 * 1024 * 1024


class ListingPhotoUploadSerializer(serializers.Serializer):
    """Validates a multipart photo upload that replaces a listing's photos."""
    photos = serializers.ListField(child=serializers.ImageField(), allow_empty=False)
    cover_index = serializers.IntegerField(min_value=0, default=0)

    def validate_photos(self, photos):
        account = self.context['request'].user
        if not account.can_upload_images(len(photos)):
            raise serializers.ValidationError(
                _('Image limit exceeded. This account allows %(count)s images per post.') % {'count': account.max_images_per_post}
            )
        for photo in photos:
            if photo.size > MAX_PHOTO_SIZE_BYTES:
                raise serializers.ValidationError(_('"%(name)s" is larger than 5 MB.') % {'name': photo.name})
        return photos

    def validate(self, attrs):
        if attrs['cover_index'] >= len(attrs['photos']):
            raise serializers.ValidationError({'cover_index': _('Cover index is out of range.')})
        return attrs


class SpeciesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Species
        fields = ['id', 'name']


class ContactInfoField(serializers.Field):
    def to_representation(self, value):
        if isinstance(value, dict):
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {'phone': value} if value else {}

    def to_internal_value(self, value):
        if isinstance(value, dict):
            return json.dumps(value)
        return str(value)

class EquipmentPostSerializer(OwnerOnlyContactInfoMixin, PostLimitSerializerMixin, serializers.ModelSerializer):
    # Nested seller info
    seller = PublicSellerSerializer(source='account', read_only=True)
    seller_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = EquipmentPost
        fields = [
            'id', 'title', 'description', 'price', 'location', 'contact_info',
            'condition', 'shipping_methods', 'image', 'gallery', 'created_at', 'updated_at',
            'seller', 'seller_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'seller', 'seller_id']
    
    def create(self, validated_data):
        # Set the account from the request user
        validated_data['account'] = self.context['request'].user
        return super().create(validated_data)


class LiveAnimalPostSerializer(OwnerOnlyContactInfoMixin, PostLimitSerializerMixin, serializers.ModelSerializer):
    contact_info = ContactInfoField()
    species_name = serializers.CharField(source='species.name', read_only=True)
    
    # Nested seller info
    seller = PublicSellerSerializer(source='account', read_only=True)
    seller_id = serializers.IntegerField(source='account.id', read_only=True)
    
    # For create/update, allow species ID
    species = serializers.PrimaryKeyRelatedField(
        queryset=Species.objects.all(),
        required=False
    )
    
    # Convert genetics string to list on serialization
    genes = serializers.SerializerMethodField()
    seller_name = serializers.CharField(source='account.get_display_name', read_only=True)
    seller_rating = serializers.FloatField(source='account.seller_rating', read_only=True)
    posted_days = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveAnimalPost
        fields = [
            'id', 'title', 'description', 'price', 'location', 'contact_info',
            'species', 'species_name', 'sex', 'genetics', 'genes', 'life_stage',
            'age_years', 'weight_grams', 'size_cm', 'diets', 'shipping_methods',
            'image', 'gallery', 'guide_notes', 'created_at', 'updated_at',
            'seller', 'seller_id', 'seller_name', 'seller_rating', 'posted_days'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'seller', 'seller_id', 'seller_name',
            'seller_rating', 'species_name', 'genes', 'posted_days'
        ]
    
    def get_genes(self, obj):
        """Convert genetics string to list"""
        if obj.genetics:
            return [gene.strip() for gene in obj.genetics.split('/') if gene.strip()]
        return []

    def get_posted_days(self, obj):
        return max(0, (timezone.now() - obj.created_at).days)
    
    def create(self, validated_data):
        # Set the account from the request user
        validated_data['account'] = self.context['request'].user
        return super().create(validated_data)


class SavedSearchSerializer(serializers.ModelSerializer):
    """A saved marketplace search. `query` is checked against the real listing filters and stored in a
    stable form; `name` defaults to the search text."""
    name = serializers.CharField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = SavedSearch
        fields = ['id', 'name', 'query', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_query(self, value):
        from .search_alerts import normalize_query
        try:
            return normalize_query(value)
        except ValueError as error:
            raise serializers.ValidationError(
                _('This search has filters that can\'t be saved: %(names)s.') % {'names': ', '.join(error.args[0])}
            )

    def validate(self, attrs):
        from django.conf import settings
        from django.http import QueryDict
        account = self.context['request'].user
        if self.instance is None and SavedSearch.objects.filter(account=account).count() >= settings.SAVED_SEARCH_LIMIT:
            raise serializers.ValidationError({
                'detail': _('You can keep up to %(count)s saved searches. Delete one to save another.') % {'count': settings.SAVED_SEARCH_LIMIT},
            })
        if not attrs.get('name'):
            attrs['name'] = QueryDict(attrs['query']).get('search') or _('Marketplace search')
        return attrs
