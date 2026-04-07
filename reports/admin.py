"""Admin configuration for ClarityBI reports."""

from django.contrib import admin
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


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "source_type", "is_active", "created_at"]
    list_filter = ["source_type", "is_active"]
    search_fields = ["name", "description"]


class WidgetInline(admin.TabularInline):
    model = Widget
    extra = 0
    fields = ["title", "widget_type", "order", "width", "height"]


@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "owner", "is_public", "created_at"]
    list_filter = ["is_public"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WidgetInline]


@admin.register(Widget)
class WidgetAdmin(admin.ModelAdmin):
    list_display = ["title", "dashboard", "widget_type", "order"]
    list_filter = ["widget_type", "dashboard"]
    search_fields = ["title"]


@admin.register(KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ["name", "value", "target", "unit", "trend", "period", "updated_at"]
    list_filter = ["trend", "period"]
    search_fields = ["name"]


@admin.register(SalesData)
class SalesDataAdmin(admin.ModelAdmin):
    list_display = ["date", "revenue", "orders", "customers", "avg_order_value", "profit", "returns", "region", "category"]
    list_filter = ["region", "category", "date"]
    search_fields = ["region", "category"]
    date_hierarchy = "date"


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "current_value", "target_value", "deadline", "is_completed", "updated_at"]
    list_filter = ["category", "is_completed"]
    search_fields = ["name", "description"]
    date_hierarchy = "created_at"


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ["title", "insight_type", "severity", "metric_name", "is_active", "created_at"]
    list_filter = ["insight_type", "severity", "is_active"]
    search_fields = ["title", "description", "metric_name"]


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_bookmarked", "created_at", "updated_at"]
    list_filter = ["is_bookmarked"]
    search_fields = ["name", "description"]


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "url", "section_type", "created_at"]
    list_filter = ["section_type"]
    search_fields = ["name", "url"]


@admin.register(ExportLog)
class ExportLogAdmin(admin.ModelAdmin):
    list_display = ["user", "export_format", "record_count", "file_size", "created_at"]
    list_filter = ["export_format"]
    date_hierarchy = "created_at"
