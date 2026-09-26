import json
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import serializers
from . import species as species_catalog
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
    # Other names that pick this species, so the editor can suggest it for them too.
    aliases = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Species
        fields = ['id', 'name', 'aliases']


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
    seller = PublicSellerSerializer(source='account', read_only=True)
    posted_days = serializers.SerializerMethodField()

    def get_posted_days(self, obj):
        return max(0, (timezone.now() - obj.created_at).days)


class EquipmentPostSerializer(FavoriteFlagMixin, OwnerOnlyContactInfoMixin, PostLimitSerializerMixin, PublicListingFieldsMixin, serializers.ModelSerializer):
    # Same as live animals: the editor sends contact_info as an object.
    contact_info = ContactInfoField()

    class Meta:
        model = EquipmentPost
        fields = [
            'id', 'status', 'title', 'description', 'price', 'location', 'contact_info', 'is_hidden',
            'category', 'condition', 'shipping_methods', 'image', 'gallery', 'created_at', 'updated_at',
            'seller', 'posted_days', 'is_favorite'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'seller', 'posted_days', 'is_hidden', 'is_favorite']
    
    def create(self, validated_data):
        # Set the account from the request user
        validated_data['account'] = self.context['request'].user
        return super().create(validated_data)


class LiveAnimalPostSerializer(FavoriteFlagMixin, OwnerOnlyContactInfoMixin, PostLimitSerializerMixin, PublicListingFieldsMixin, serializers.ModelSerializer):
    contact_info = ContactInfoField()
    # Null while the listing's species is under review (see species_review).
    species_name = serializers.CharField(source='species.name', read_only=True, allow_null=True)
    
    # Send `species` (an id from /posts/species/) or `requested_species` (a name as the seller typed
    # it). A name that matches a species or one of its aliases picks it; any other name is saved for
    # staff review and the listing stays unpublished until then (post/species.py).
    species = serializers.PrimaryKeyRelatedField(
        queryset=Species.objects.all(),
        required=False
    )
    requested_species = serializers.CharField(write_only=True, required=False, max_length=100)
    species_review = serializers.SerializerMethodField()
    
    # Convert genetics string to list on serialization
    genes = serializers.SerializerMethodField()
    
    class Meta:
        model = LiveAnimalPost
        fields = [
            'id', 'status', 'title', 'description', 'price', 'location', 'contact_info', 'is_hidden',
            'species', 'species_name', 'requested_species', 'species_review', 'sex', 'genetics', 'genes', 'life_stage',
            'age_years', 'weight_grams', 'size_cm', 'diets', 'shipping_methods',
            'image', 'gallery', 'guide_notes', 'created_at', 'updated_at',
            'seller', 'posted_days', 'is_favorite'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'seller', 'is_hidden', 'species_name', 'species_review', 'genes',
            'posted_days', 'is_favorite'
        ]
    
    def get_species_review(self, obj):
        """The typed species waiting on staff ("pending") or turned down ("rejected", with the reason)."""
        species_request = obj.species_request
        if species_request is None:
            return None
        return {'name': species_request.name, 'status': species_request.status, 'note': species_request.staff_note}

    def validate(self, attrs):
        attrs = super().validate(attrs)
        requested = attrs.pop('requested_species', '').strip()
        if requested and attrs.get('species'):
            raise serializers.ValidationError({'species': _('Choose a species from the list or type one, not both.')})
        if requested:
            attrs['species'] = species_catalog.find_species(requested)
            if attrs['species'] is None:
                attrs['species_request'] = self._species_request_for(requested)
        elif self.instance is None and not attrs.get('species'):
            raise serializers.ValidationError({'species': _('Choose a species.')})
        if attrs.get('species'):
            attrs['species_request'] = None

        # An unreviewed species unpublishes the listing, which would pull it out from under the bidders.
        if self.instance is not None and self.instance.species_id and attrs.get('species_request', None) is not None:
            from auction.models import Auction
            if self.instance.auctions.filter(status=Auction.Status.ACTIVE).exists():
                raise serializers.ValidationError({
                    'species': _("This listing has a running auction, so its species can't be changed to one that still needs review."),
                })
        return attrs

    def _species_request_for(self, name):
        """The request this listing should wait on for `name`; a new one is only created on save."""
        current = self.instance.species_request if self.instance is not None else None
        # Saving other changes to a listing that's already waiting (or was turned down) keeps its request.
        if current and species_catalog.normalize(current.name) == species_catalog.normalize(name):
            return current
        existing = species_catalog.find_open_request(name)
        if existing and existing.status == existing.Status.REJECTED:
            values = {'name': existing.name, 'note': existing.staff_note}
            message = (
                _('"%(name)s" isn\'t accepted as a species (%(note)s). Choose one from the list.') % values
                if existing.staff_note else
                _('"%(name)s" isn\'t accepted as a species. Choose one from the list.') % values
            )
            raise serializers.ValidationError({'species': message})
        return existing or name

    def _save_species_request(self, validated_data):
        # A name (rather than a request) means nobody has asked for this species yet.
        if isinstance(validated_data.get('species_request'), str):
            validated_data['species_request'] = species_catalog.request_species(validated_data['species_request'])

    @transaction.atomic
    def update(self, instance, validated_data):
        previous_request = instance.species_request
        self._save_species_request(validated_data)
        post = super().update(instance, validated_data)
        if previous_request and previous_request != post.species_request:
            species_catalog.release(previous_request)
        return post

    def get_genes(self, obj):
        """Convert genetics string to list"""
        if obj.genetics:
            return [gene.strip() for gene in obj.genetics.split('/') if gene.strip()]
        return []
    
    @transaction.atomic
    def create(self, validated_data):
        # Set the account from the request user
        validated_data['account'] = self.context['request'].user
        self._save_species_request(validated_data)
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
