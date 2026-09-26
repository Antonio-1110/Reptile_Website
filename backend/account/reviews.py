"""
Seller reviews in one place: who may review whom, and keeping the seller's rating in step. A seller's
seller_rating and total_reviews are only ever computed from their reviews, never set directly.
"""
from django.db import transaction
from django.db.models import Avg, Count

from .models import Account, Review


def can_review(reviewer, seller):
    """Only someone who contacted the seller about a listing, or bought from them at auction."""
    from auction.models import Order
    from post.models import ContactRequest

    if not reviewer.is_authenticated or reviewer.pk == seller.pk:
        return False
    contacted = ContactRequest.objects.filter(requester=reviewer).filter(
        live_animal_post__account=seller,
    ).exists() or ContactRequest.objects.filter(requester=reviewer, equipment_post__account=seller).exists()
    return contacted or Order.objects.filter(
        buyer=reviewer, auction__seller=seller, status=Order.Status.COMPLETED,
    ).exists()


def refresh_rating(seller):
    stats = Review.objects.filter(seller=seller).aggregate(average=Avg('rating'), count=Count('id'))
    Account.objects.filter(pk=seller.pk).update(
        seller_rating=round(stats['average'] or 0.0, 2), total_reviews=stats['count'],
    )


def save_review(reviewer, seller, rating, comment=''):
    """Create or update the reviewer's review of the seller. Returns (review, created)."""
    with transaction.atomic():
        review, created = Review.objects.update_or_create(
            seller=seller, reviewer=reviewer, defaults={'rating': rating, 'comment': comment},
        )
        refresh_rating(seller)
    return review, created


def delete_review(reviewer, seller):
    with transaction.atomic():
        deleted, _ = Review.objects.filter(seller=seller, reviewer=reviewer).delete()
        refresh_rating(seller)
    return bool(deleted)
