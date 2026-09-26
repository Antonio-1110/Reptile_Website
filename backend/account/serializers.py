from rest_framework import serializers
from . import reviews
from .models import Account, Review

class AccountSerializer(serializers.ModelSerializer):
    """Seller profile serializer - used for display in listings"""
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    is_commercial = serializers.BooleanField(read_only=True)
    requires_rating = serializers.BooleanField(read_only=True)
    max_images_per_post = serializers.IntegerField(read_only=True)
    max_post_count = serializers.IntegerField(read_only=True)
    can_start_auction = serializers.BooleanField(read_only=True)

    class Meta:
        model = Account
        fields = [
            'id',
            'username',
            'display_name',
            'email',
            'account_type',
            'is_commercial',
            'requires_rating',
            'seller_rating',
            'total_reviews',
            'verified_seller',
            'is_paid_account',
            'max_images_per_post',
            'max_post_count',
            'can_start_auction',
            'bio',
        ]
        # account_type is read-only: commercial is a paid upgrade, so it can't be self-assigned here.
        read_only_fields = [
            'id',
            'display_name',
            'account_type',
            'is_commercial',
            'requires_rating',
            'seller_rating',
            'total_reviews',
            'verified_seller',
            'is_paid_account',
            'max_images_per_post',
            'max_post_count',
            'can_start_auction',
        ]


class PublicSellerSerializer(AccountSerializer):
    """Seller info embedded in public listings; omits email so contact goes through the /contact/ action."""

    class Meta(AccountSerializer.Meta):
        fields = [field for field in AccountSerializer.Meta.fields if field != 'email']


class SellerProfileSerializer(serializers.ModelSerializer):
    """A seller's public page (/api/sellers/<id>/): who they are and their track record, never contact details."""
    display_name = serializers.CharField(source='get_display_name', read_only=True)
    is_commercial = serializers.BooleanField(read_only=True)
    member_since = serializers.DateTimeField(source='date_joined', read_only=True)
    live_animal_count = serializers.IntegerField(read_only=True)
    equipment_count = serializers.IntegerField(read_only=True)
    # For the signed-in viewer: may they review this seller, and their review if they wrote one.
    can_review = serializers.SerializerMethodField()
    my_review = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            'id', 'username', 'display_name', 'account_type', 'is_commercial', 'verified_seller',
            'seller_rating', 'total_reviews', 'bio', 'member_since', 'live_animal_count', 'equipment_count',
            'can_review', 'my_review',
        ]
        read_only_fields = fields

    def _viewer(self):
        request = self.context.get('request')
        return request.user if request else None

    def get_can_review(self, seller):
        viewer = self._viewer()
        return bool(viewer) and reviews.can_review(viewer, seller)

    def get_my_review(self, seller):
        viewer = self._viewer()
        if not viewer or not viewer.is_authenticated:
            return None
        review = Review.objects.filter(seller=seller, reviewer=viewer).first()
        return ReviewSerializer(review, context=self.context).data if review else None


class ReviewSerializer(serializers.ModelSerializer):
    """A review as anyone sees it. Reviewers appear by username only: their real name stays private."""
    reviewer = serializers.CharField(source='reviewer.username', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'reviewer', 'rating', 'comment', 'created_at', 'updated_at', 'is_mine']
        read_only_fields = ['id', 'reviewer', 'created_at', 'updated_at', 'is_mine']
        extra_kwargs = {'rating': {'min_value': 1, 'max_value': 5}}

    def get_is_mine(self, review):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and review.reviewer_id == request.user.id)


class ProfileAccountSerializer(AccountSerializer):
    """The signed-in user's own profile (/api/v1/auth/profile/). Private contact fields live only here,
    never on AccountSerializer, because PublicSellerSerializer builds on that one."""
    post_count = serializers.SerializerMethodField()
    remaining_post_count = serializers.SerializerMethodField()

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + [
            'first_name', 'last_name', 'phone_number', 'line_id', 'contact_email', 'instagram', 'facebook',
            'post_count', 'remaining_post_count',
        ]
        read_only_fields = AccountSerializer.Meta.read_only_fields + ['post_count', 'remaining_post_count']

    def get_post_count(self, account):
        from post.models import EquipmentPost, LiveAnimalPost

        return LiveAnimalPost.objects.filter(account=account).count() + EquipmentPost.objects.filter(account=account).count()

    def get_remaining_post_count(self, account):
        return max(0, account.max_post_count - self.get_post_count(account))
