from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class Account(AbstractUser):
    class AccountType(models.TextChoices):
        HOBBYIST = 'hobbyist', 'Hobbyist'
        COMMERCIAL = 'commercial', 'Commercial'

    # Note: username, email, password inherited from AbstractUser
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.HOBBYIST,
    )
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    personal_id = models.CharField(max_length=12, blank=True, null=True)
    line_id = models.CharField(max_length=40, blank=True, null=True)
    # Contact details buyers may use; separate from the login `email`, which stays private.
    contact_email = models.EmailField(blank=True)
    instagram = models.CharField(max_length=60, blank=True, help_text="Instagram handle, e.g. @geckogarden")
    facebook = models.CharField(max_length=200, blank=True, help_text="Facebook page name or URL")

    # Seller profile
    seller_rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        help_text="Average seller rating (0-5)",
        blank=True,
        null=True,
    )
    total_reviews = models.IntegerField(default=0)
    bio = models.TextField(blank=True, null=True, max_length=500)
    verified_seller = models.BooleanField(default=False)
    is_paid_account = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'

    def __str__(self):
        return self.username

    @property
    def is_commercial(self):
        return self.account_type == self.AccountType.COMMERCIAL

    @property
    def requires_rating(self):
        return self.is_commercial

    @property
    def max_post_count(self):
        if self.is_commercial and self.is_paid_account:
            return 200
        if self.is_commercial:
            return 20
        return 5

    @property
    def max_images_per_post(self):
        if self.is_commercial and self.is_paid_account:
            return 12
        if self.is_commercial:
            return 6
        return 3

    @property
    def can_start_auction(self):
        # Starting an auction is a paid feature; anyone may bid (after paying a deposit).
        return self.is_commercial and self.is_paid_account

    def can_create_post(self, current_post_count=0):
        return current_post_count < self.max_post_count

    def can_upload_images(self, image_count):
        return image_count <= self.max_images_per_post

    def get_display_name(self):
        """Return seller display name (first name + last name, or username)"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.username
    def contact_details(self):
        """
        The ways to reach this person, as shared with the other side of a deal (a seller receiving a
        buyer's inquiry, or the two sides of a paid sale). Never exposed publicly. Empty fields are left out.
        """
        details = {
            'name': self.get_display_name(),
            'email': self.contact_email or self.email,
            'phone': self.phone_number,
            'line': self.line_id,
            'instagram': self.instagram,
            'facebook': self.facebook,
        }
        return {key: value for key, value in details.items() if value}


class Review(models.Model):
    """
    A buyer's rating of a seller. One per buyer and seller (the buyer can edit it). Only someone who
    contacted the seller about a listing, or bought from them at auction, may leave one; the seller's
    seller_rating and total_reviews are recomputed from these (see account/reviews.py).
    """
    seller = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='reviews_received')
    reviewer = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='reviews_written')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['seller', 'reviewer'], name='one_review_per_buyer_per_seller'),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='review_rating_1_to_5'),
            models.CheckConstraint(condition=~models.Q(seller=models.F('reviewer')), name='no_reviewing_yourself'),
        ]

    def __str__(self):
        return f'{self.reviewer} → {self.seller}: {self.rating}★'
