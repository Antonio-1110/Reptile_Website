"""
Marketplace ordering beyond "newest first" (issue #60).

"Recommended" sorts by the posting time moved forward by a few bonus days for signs of a good
listing: a photo, a real description, filled-in genetics, a verified or well-reviewed seller. A strong
listing therefore sits above weaker ones posted a few days after it, but still sinks as it ages, so
new listings keep getting seen. It's a plain SQL expression, so it pages like any other ordering.

"Similar listings" picks other listings of the same species (animals) or type (equipment), preferring
shared morphs, the same area and a comparable price.
"""
from django.db.models import Case, DateTimeField, F, Func, IntegerField, Q, Value, When
from django.db.models.functions import Length

# Bonus days per signal. Kept small: a week at most, so a listing's age still decides most of the order.
PHOTO_BONUS = 2
DESCRIPTION_BONUS = 1
DESCRIPTION_MIN_LENGTH = 80
GENETICS_BONUS = 1
VERIFIED_SELLER_BONUS = 1
RATED_SELLER_BONUS = 2
RATED_SELLER_MIN_RATING = 4.5
RATED_SELLER_MIN_REVIEWS = 3

SIMILAR_COUNT = 6
# Only the newest matches are scored; enough to find good neighbours without loading a whole species.
SIMILAR_CANDIDATES = 60


class AddDays(Func):
    """`datetime + <integer expression> days`, written per database (SQLite has no interval type)."""
    output_field = DateTimeField()
    arity = 2

    def _compile(self, compiler):
        date_sql, date_params = compiler.compile(self.source_expressions[0])
        days_sql, days_params = compiler.compile(self.source_expressions[1])
        return date_sql, days_sql, [*date_params, *days_params]

    def as_sql(self, compiler, connection, **extra_context):
        date_sql, days_sql, params = self._compile(compiler)
        return f'({date_sql} + make_interval(days => ({days_sql})::integer))', params

    def as_sqlite(self, compiler, connection, **extra_context):
        date_sql, days_sql, params = self._compile(compiler)
        return f"datetime({date_sql}, ({days_sql}) || ' days')", params


def _bonus(condition, days):
    return Case(When(condition, then=Value(days)), default=Value(0), output_field=IntegerField())


def bonus_days(model):
    parts = [
        _bonus(~Q(image=''), PHOTO_BONUS),
        _bonus(Q(description_length__gte=DESCRIPTION_MIN_LENGTH), DESCRIPTION_BONUS),
        _bonus(Q(account__verified_seller=True), VERIFIED_SELLER_BONUS),
        _bonus(
            Q(account__seller_rating__gte=RATED_SELLER_MIN_RATING, account__total_reviews__gte=RATED_SELLER_MIN_REVIEWS),
            RATED_SELLER_BONUS,
        ),
    ]
    if any(field.name == 'genetics' for field in model._meta.get_fields()):
        parts.append(_bonus(~Q(genetics=''), GENETICS_BONUS))
    total = parts[0]
    for part in parts[1:]:
        total = total + part
    return total


def recommended(queryset):
    queryset = queryset.annotate(description_length=Length('description'))
    return queryset.annotate(
        ranked_at=AddDays(F('created_at'), bonus_days(queryset.model)),
    ).order_by('-ranked_at', '-id')


def _genes(post):
    return {gene.strip().lower() for gene in (getattr(post, 'genetics', '') or '').split('/') if gene.strip()}


def _similarity(post, other):
    score = 3 * len(_genes(post) & _genes(other))
    if other.location == post.location:
        score += 1
    if post.price and other.price and post.price / 2 <= other.price <= post.price * 2:
        score += 1
    return score


def similar_listings(post, queryset):
    """
    Up to SIMILAR_COUNT listings like `post` from `queryset` (already limited to what the public may
    see). An animal without a confirmed species has nothing to compare with, so it gets none.
    """
    if hasattr(post, 'species_id'):
        if post.species_id is None:
            return []
        queryset = queryset.filter(species_id=post.species_id)
    else:
        queryset = queryset.filter(category=post.category)
    candidates = list(
        queryset.exclude(pk=post.pk).exclude(status=post.Status.SOLD).order_by('-created_at', '-id')[:SIMILAR_CANDIDATES]
    )
    # Python's sort is stable, so equally similar listings keep the newest-first order.
    candidates.sort(key=lambda other: _similarity(post, other), reverse=True)
    return candidates[:SIMILAR_COUNT]
