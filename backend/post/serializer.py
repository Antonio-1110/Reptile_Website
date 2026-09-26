import json
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers
from .models import EquipmentPost, LiveAnimalPost, Species
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
    """
    Validates a multipart request that sets a listing's photos, in one of two forms:
    - `photos` + `cover_index`: the uploads replace every existing photo;
    - `order` (+ optional `photos`): the final photos, cover first. Each entry is either one of the
      listing's current photo URLs (kept as is) or "new:<n>", the n-th uploaded file. Existing photos
      left out are removed, so this also reorders and deletes without re-uploading.
    """
    NEW_PREFIX = 'new:'

    photos = serializers.ListField(child=serializers.ImageField(), required=False, default=list)
    cover_index = serializers.IntegerField(min_value=0, default=0)
    order = serializers.ListField(child=serializers.CharField(), required=False, allow_null=True, default=None)

    def validate_photos(self, photos):
        for photo in photos:
            if photo.size > MAX_PHOTO_SIZE_BYTES:
                raise serializers.ValidationError(_('"%(name)s" is larger than 5 MB.') % {'name': photo.name})
        return photos

    def validate(self, attrs):
        photos, order = attrs['photos'], attrs['order']
        if order is None:
            if not photos:
                raise serializers.ValidationError({'photos': _('Add at least one photo.')})
            if attrs['cover_index'] >= len(photos):
                raise serializers.ValidationError({'cover_index': _('Cover index is out of range.')})
            order = [f'{self.NEW_PREFIX}{attrs["cover_index"]}'] + [
                f'{self.NEW_PREFIX}{index}' for index in range(len(photos)) if index != attrs['cover_index']
            ]
        self._check_order(order, photos)
        account = self.context['request'].user
        if not account.can_upload_images(len(order)):
            raise serializers.ValidationError(
                {'photos': _('Image limit exceeded. This account allows %(count)s images per post.') % {'count': account.max_images_per_post}}
            )
        attrs['order'] = order
        return attrs

    def _check_order(self, order, photos):
        # Only the listing's own photos can be kept: anything else would let a seller point the listing
        # at arbitrary URLs.
        post = self.context['post']
        current = set(post.gallery or []) | ({post.image} if post.image else set())
        used_new = []
        for entry in order:
            if entry.startswith(self.NEW_PREFIX):
                index = entry[len(self.NEW_PREFIX):]
                if not index.isdigit() or int(index) >= len(photos):
                    raise serializers.ValidationError({'order': _('Photo order refers to a file that was not uploaded.')})
                used_new.append(int(index))
            elif entry not in current:
                raise serializers.ValidationError({'order': _('Photo order refers to a photo this listing does not have.')})
        if len(set(order)) != len(order) or sorted(used_new) != list(range(len(photos))):
            raise serializers.ValidationError({'order': _('Each photo must appear in the order exactly once.')})


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

class FavoriteFlagMixin(serializers.Serializer):
    # Whether the viewer saved the listing; the viewsets annotate it (FavoritesMixin), else False.
    is_favorite = serializers.SerializerMethodField()

    def get_is_favorite(self, obj):
        return bool(getattr(obj, 'is_favorite', False))


class PublicListingFieldsMixin(serializers.Serializer):
    """Read-only fields the listing detail page shows for both listing types."""
    seller_name = serializers.CharField(source='account.get_display_name', read_only=True)
    seller_rating = serializers.FloatField(source='account.seller_rating', read_only=True)
    posted_days = serializers.SerializerMethodField()

    def get_posted_days(self, obj):
        return max(0, (timezone.now() - obj.created_at).days)


class EquipmentPostSerializer(FavoriteFlagMixin, OwnerOnlyContactInfoMixin, PostLimitSerializerMixin, PublicListingFieldsMixin, serializers.ModelSerializer):
    # Same as live animals: the editor sends contact_info as an object.
    contact_info = ContactInfoField()
    # Nested seller info
    seller = PublicSellerSerializer(source='account', read_only=True)
    seller_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = EquipmentPost
        fields = [
            'id', 'title', 'description', 'price', 'location', 'contact_info',
            'category', 'condition', 'shipping_methods', 'image', 'gallery', 'created_at', 'updated_at',
            'seller', 'seller_id', 'seller_name', 'seller_rating', 'posted_days', 'is_favorite'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'seller', 'seller_id', 'seller_name', 'seller_rating', 'posted_days', 'is_favorite']
    
    def create(self, validated_data):
        # Set the account from the request user
        validated_data['account'] = self.context['request'].user
        return super().create(validated_data)


class LiveAnimalPostSerializer(FavoriteFlagMixin, OwnerOnlyContactInfoMixin, PostLimitSerializerMixin, PublicListingFieldsMixin, serializers.ModelSerializer):
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
    
    class Meta:
        model = LiveAnimalPost
        fields = [
            'id', 'title', 'description', 'price', 'location', 'contact_info',
            'species', 'species_name', 'sex', 'genetics', 'genes', 'life_stage',
            'age_years', 'weight_grams', 'size_cm', 'diets', 'shipping_methods',
            'image', 'gallery', 'guide_notes', 'created_at', 'updated_at',
            'seller', 'seller_id', 'seller_name', 'seller_rating', 'posted_days', 'is_favorite'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'seller', 'seller_id', 'seller_name',
            'seller_rating', 'species_name', 'genes', 'posted_days', 'is_favorite'
        ]
    
    def get_genes(self, obj):
        """Convert genetics string to list"""
        if obj.genetics:
            return [gene.strip() for gene in obj.genetics.split('/') if gene.strip()]
        return []
    
    def create(self, validated_data):
        # Set the account from the request user
        validated_data['account'] = self.context['request'].user
        return super().create(validated_data)
