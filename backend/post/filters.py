from datetime import timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import LiveAnimalPost


class CommaListFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    """Accepts `?field=a,b,c` and matches any of the values."""


def json_list_has_any(field, values):
    # JSONField `contains` isn't supported on SQLite, so match the quoted value in the stored JSON text.
    query = Q()
    for value in values:
        query |= Q(**{f'{field}__icontains': f'"{value}"'})
    return query


class LiveAnimalPostFilter(django_filters.FilterSet):
    """
    Server-side filters backing the marketplace sidebar, so the client can page through results
    instead of downloading every listing. List params take comma-separated values; each
    `*_exclude` param inverts its counterpart.
    """

    status = CommaListFilter(field_name='status', lookup_expr='in')
    sex = CommaListFilter(field_name='sex', lookup_expr='in')
    life_stage = CommaListFilter(field_name='life_stage', lookup_expr='in')
    life_stage_exclude = CommaListFilter(field_name='life_stage', lookup_expr='in', exclude=True)
    location = CommaListFilter(field_name='location', lookup_expr='in')
    location_exclude = CommaListFilter(field_name='location', lookup_expr='in', exclude=True)
    species_name = django_filters.CharFilter(field_name='species__name', lookup_expr='iexact')
    genes = django_filters.CharFilter(method='filter_genes')

    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    size_min = django_filters.NumberFilter(field_name='size_cm', lookup_expr='gte')
    size_max = django_filters.NumberFilter(field_name='size_cm', lookup_expr='lte')
    weight_min = django_filters.NumberFilter(field_name='weight_grams', lookup_expr='gte')
    weight_max = django_filters.NumberFilter(field_name='weight_grams', lookup_expr='lte')
    age_min = django_filters.NumberFilter(field_name='age_years', lookup_expr='gte')
    age_max = django_filters.NumberFilter(field_name='age_years', lookup_expr='lte')
    posted_days_min = django_filters.NumberFilter(method='filter_posted_days_min')
    posted_days_max = django_filters.NumberFilter(method='filter_posted_days_max')

    diets = CommaListFilter(method='filter_json_any')
    diets_exclude = CommaListFilter(method='filter_json_none')
    shipping = CommaListFilter(method='filter_json_any')
    shipping_exclude = CommaListFilter(method='filter_json_none')

    class Meta:
        model = LiveAnimalPost
        fields = ['species']

    JSON_FIELDS = {
        'diets': 'diets', 'diets_exclude': 'diets',
        'shipping': 'shipping_methods', 'shipping_exclude': 'shipping_methods',
    }

    def filter_json_any(self, queryset, name, values):
        return queryset.filter(json_list_has_any(self.JSON_FIELDS[name], values))

    def filter_json_none(self, queryset, name, values):
        return queryset.exclude(json_list_has_any(self.JSON_FIELDS[name], values))

    def filter_genes(self, queryset, name, value):
        # `genes=Pastel,Pied` → the listing must carry every one of the traits.
        for gene in filter(None, (part.strip() for part in value.split(','))):
            queryset = queryset.filter(genetics__icontains=gene)
        return queryset

    # `posted_days` in the API is whole days since creation, so "at least N days" means created
    # N or more days ago, and "at most N days" means created less than N + 1 days ago.
    def filter_posted_days_min(self, queryset, name, value):
        return queryset.filter(created_at__lte=timezone.now() - timedelta(days=float(value)))

    def filter_posted_days_max(self, queryset, name, value):
        return queryset.filter(created_at__gt=timezone.now() - timedelta(days=float(value) + 1))
