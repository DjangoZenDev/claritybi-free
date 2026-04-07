"""DRF serializers for ClarityBI reports."""

from rest_framework import serializers
from .models import (
    Bookmark,
    Dashboard,
    DataSource,
    ExportLog,
    Goal,
    Insight,
    KPI,
    SalesData,
    SavedReport,
    Widget,
)


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ["id", "name", "description", "source_type", "is_active", "created_at"]


class WidgetSerializer(serializers.ModelSerializer):
    widget_type_display = serializers.CharField(source="get_widget_type_display", read_only=True)

    class Meta:
        model = Widget
        fields = [
            "id", "dashboard", "title", "widget_type", "widget_type_display",
            "query_config", "position_x", "position_y", "width", "height", "order",
        ]


class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True, default="")

    class Meta:
        model = Dashboard
        fields = [
            "id", "name", "slug", "description", "owner", "owner_name",
            "is_public", "created_at", "updated_at", "widgets",
        ]


class DashboardListSerializer(serializers.ModelSerializer):
    widget_count = serializers.IntegerField(source="widgets.count", read_only=True)

    class Meta:
        model = Dashboard
        fields = ["id", "name", "slug", "description", "is_public", "created_at", "widget_count"]


class KPISerializer(serializers.ModelSerializer):
    progress_pct = serializers.ReadOnlyField()
    trend_display = serializers.CharField(source="get_trend_display", read_only=True)
    comparison_delta = serializers.ReadOnlyField()

    class Meta:
        model = KPI
        fields = [
            "id", "name", "value", "target", "unit", "trend",
            "trend_display", "period", "progress_pct", "sparkline_data",
            "comparison_value", "comparison_label", "comparison_delta",
            "updated_at",
        ]


class SalesDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesData
        fields = [
            "id", "date", "revenue", "orders", "customers",
            "avg_order_value", "profit", "returns", "region", "category",
            "created_at",
        ]


class SalesSummarySerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_customers = serializers.IntegerField()
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)


class GoalSerializer(serializers.ModelSerializer):
    progress_pct = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()

    class Meta:
        model = Goal
        fields = [
            "id", "name", "description", "target_value", "current_value",
            "unit", "category", "deadline", "is_completed", "progress_pct",
            "days_remaining", "is_overdue", "created_at", "updated_at",
        ]


class InsightSerializer(serializers.ModelSerializer):
    severity_color = serializers.ReadOnlyField()
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model = Insight
        fields = [
            "id", "title", "description", "insight_type", "metric_name",
            "metric_value", "change_pct", "severity", "severity_color",
            "icon", "is_active", "is_valid", "valid_until", "created_at",
        ]


class SavedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedReport
        fields = [
            "id", "user", "name", "description", "config",
            "is_bookmarked", "created_at", "updated_at",
        ]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = [
            "id", "user", "name", "url", "section_type", "created_at",
        ]
        read_only_fields = ["user"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ExportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportLog
        fields = [
            "id", "user", "export_format", "record_count",
            "file_size", "created_at",
        ]
        read_only_fields = ["user"]
