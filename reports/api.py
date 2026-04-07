"""DRF ViewSets for ClarityBI reports API."""

from datetime import timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import DashboardFilter, GoalFilter, InsightFilter, KPIFilter, SalesDataFilter
from .models import Bookmark, Dashboard, Goal, Insight, KPI, SalesData, SavedReport
from .serializers import (
    BookmarkSerializer,
    DashboardListSerializer,
    DashboardSerializer,
    GoalSerializer,
    InsightSerializer,
    KPISerializer,
    SalesDataSerializer,
    SavedReportSerializer,
)


class DashboardViewSet(viewsets.ModelViewSet):
    """API endpoint for dashboards."""

    queryset = Dashboard.objects.filter(is_public=True)
    filterset_class = DashboardFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    lookup_field = "slug"

    def get_serializer_class(self):
        if self.action == "list":
            return DashboardListSerializer
        return DashboardSerializer


class KPIViewSet(viewsets.ModelViewSet):
    """API endpoint for KPIs."""

    queryset = KPI.objects.all()
    serializer_class = KPISerializer
    filterset_class = KPIFilter
    search_fields = ["name"]
    ordering_fields = ["name", "value", "updated_at"]


class SalesDataViewSet(viewsets.ModelViewSet):
    """API endpoint for sales data with filtering and aggregations."""

    queryset = SalesData.objects.all()
    serializer_class = SalesDataSerializer
    filterset_class = SalesDataFilter
    search_fields = ["region", "category"]
    ordering_fields = ["date", "revenue", "orders", "customers"]

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get aggregated summary for a date range."""
        days = int(request.query_params.get("days", 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        qs = self.get_queryset().filter(date__gte=start_date, date__lte=end_date)
        agg = qs.aggregate(
            total_revenue=Sum("revenue"),
            total_orders=Sum("orders"),
            total_customers=Sum("customers"),
            avg_order_value=Avg("avg_order_value"),
        )

        return Response({
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_revenue": float(agg["total_revenue"] or 0),
            "total_orders": agg["total_orders"] or 0,
            "total_customers": agg["total_customers"] or 0,
            "avg_order_value": float(agg["avg_order_value"] or 0),
        })

    @action(detail=False, methods=["get"])
    def by_region(self, request):
        """Get sales aggregated by region."""
        days = int(request.query_params.get("days", 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        qs = (
            self.get_queryset()
            .filter(date__gte=start_date, date__lte=end_date)
            .values("region")
            .annotate(total_revenue=Sum("revenue"), total_orders=Sum("orders"))
            .order_by("-total_revenue")
        )
        return Response(list(qs))

    @action(detail=False, methods=["get"])
    def by_category(self, request):
        """Get sales aggregated by category."""
        days = int(request.query_params.get("days", 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        qs = (
            self.get_queryset()
            .filter(date__gte=start_date, date__lte=end_date)
            .values("category")
            .annotate(total_revenue=Sum("revenue"), total_orders=Sum("orders"))
            .order_by("-total_revenue")
        )
        return Response(list(qs))

    @action(detail=False, methods=["get"])
    def trend(self, request):
        """Get daily revenue trend."""
        days = int(request.query_params.get("days", 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        qs = (
            self.get_queryset()
            .filter(date__gte=start_date, date__lte=end_date)
            .values("date")
            .annotate(total_revenue=Sum("revenue"), total_orders=Sum("orders"))
            .order_by("date")
        )
        data = [
            {
                "date": entry["date"].isoformat(),
                "revenue": float(entry["total_revenue"]),
                "orders": entry["total_orders"],
            }
            for entry in qs
        ]
        return Response(data)


class GoalViewSet(viewsets.ModelViewSet):
    """API endpoint for goals."""

    queryset = Goal.objects.all()
    serializer_class = GoalSerializer
    filterset_class = GoalFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "deadline", "created_at", "category"]


class InsightViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for insights (read-only)."""

    queryset = Insight.objects.filter(is_active=True)
    serializer_class = InsightSerializer
    filterset_class = InsightFilter
    search_fields = ["title", "description", "metric_name"]
    ordering_fields = ["created_at", "severity"]


class SavedReportViewSet(viewsets.ModelViewSet):
    """API endpoint for saved reports."""

    serializer_class = SavedReportSerializer
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "updated_at"]

    def get_queryset(self):
        return SavedReport.objects.filter(user=self.request.user)


class BookmarkViewSet(viewsets.ModelViewSet):
    """API endpoint for bookmarks."""

    serializer_class = BookmarkSerializer
    search_fields = ["name", "url"]
    ordering_fields = ["name", "created_at", "section_type"]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)
