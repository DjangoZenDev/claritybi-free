"""FilterSets for ClarityBI reports API."""

import django_filters
from .models import Dashboard, Goal, Insight, KPI, SalesData


class SalesDataFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    revenue_min = django_filters.NumberFilter(field_name="revenue", lookup_expr="gte")
    revenue_max = django_filters.NumberFilter(field_name="revenue", lookup_expr="lte")
    region = django_filters.CharFilter(field_name="region", lookup_expr="iexact")
    category = django_filters.CharFilter(field_name="category", lookup_expr="iexact")

    class Meta:
        model = SalesData
        fields = ["date", "region", "category"]


class KPIFilter(django_filters.FilterSet):
    trend = django_filters.ChoiceFilter(choices=KPI.TREND_CHOICES)
    period = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = KPI
        fields = ["trend", "period"]


class DashboardFilter(django_filters.FilterSet):
    is_public = django_filters.BooleanFilter()
    name = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Dashboard
        fields = ["is_public", "name"]


class GoalFilter(django_filters.FilterSet):
    category = django_filters.ChoiceFilter(choices=Goal.CATEGORY_CHOICES)
    is_completed = django_filters.BooleanFilter()

    class Meta:
        model = Goal
        fields = ["category", "is_completed"]


class InsightFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(field_name="insight_type", choices=Insight.TYPE_CHOICES)
    severity = django_filters.ChoiceFilter(choices=Insight.SEVERITY_CHOICES)
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Insight
        fields = ["insight_type", "severity", "is_active"]
