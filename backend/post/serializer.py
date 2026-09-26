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

        # Bidders are paying deposits on a running auction, so the listing can't be marked reserved or
        # sold under them; the auction decides who gets it.
        new_status = attrs.get('status')
        if self.instance is not None and new_status and new_status != self.instance.Status.AVAILABLE:
            from auction.models import Auction
            if self.instance.auctions.filter(status=Auction.Status.ACTIVE).exists():
                raise serializers.ValidationError({
                    'status': _("This listing has a running auction. It can't be marked reserved or sold until the auction ends.")
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
    # Same as live animals: the editor sends contact_info as an object.
    contact_info = ContactInfoField()
    # Nested seller info
    seller = PublicSellerSerializer(source='account', read_only=True)
    seller_id = serializers.IntegerField(source='account.id', read_only=True)
    
    class Meta:
        model = EquipmentPost
        fields = [
            'id', 'status', 'title', 'description', 'price', 'location', 'contact_info',
            'category', 'condition', 'shipping_methods', 'image', 'gallery', 'created_at', 'updated_at',
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
            'id', 'status', 'title', 'description', 'price', 'location', 'contact_info',
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
