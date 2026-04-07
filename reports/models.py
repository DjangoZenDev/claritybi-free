"""Models for the ClarityBI Pro reports application."""

from datetime import date as date_type

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class DataSource(models.Model):
    SOURCE_TYPE_CHOICES = [
        ("database", "Database"),
        ("csv", "CSV File"),
        ("api", "API Endpoint"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default="database")
    connection_string = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Dashboard(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="dashboards", null=True, blank=True,
    )
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Widget(models.Model):
    WIDGET_TYPE_CHOICES = [
        ("kpi_card", "KPI Card"),
        ("line_chart", "Line Chart"),
        ("bar_chart", "Bar Chart"),
        ("pie_chart", "Pie Chart"),
        ("table", "Data Table"),
        ("metric", "Metric Display"),
        ("goal_ring", "Goal Progress Ring"),
        ("insight", "Insight Card"),
    ]

    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="widgets")
    title = models.CharField(max_length=200)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPE_CHOICES)
    query_config = models.JSONField(default=dict, blank=True)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)
    height = models.IntegerField(default=4)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "position_y", "position_x"]

    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()})"


class KPI(models.Model):
    TREND_CHOICES = [
        ("up", "Trending Up"),
        ("down", "Trending Down"),
        ("flat", "Flat"),
    ]

    name = models.CharField(max_length=200)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    target = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True, default="")
    trend = models.CharField(max_length=10, choices=TREND_CHOICES, default="flat")
    period = models.CharField(max_length=50, blank=True, default="This Month")
    sparkline_data = models.JSONField(default=list, blank=True)
    comparison_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    comparison_label = models.CharField(max_length=50, blank=True, default="vs last period")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "KPI"
        verbose_name_plural = "KPIs"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}: {self.value} {self.unit}"

    @property
    def progress_pct(self):
        if self.target and self.target > 0:
            return round(float(self.value) / float(self.target) * 100, 1)
        return 0

    @property
    def comparison_delta(self):
        if self.comparison_value and self.comparison_value != 0:
            return round(((float(self.value) - float(self.comparison_value)) / float(self.comparison_value)) * 100, 1)
        return 0


class SalesData(models.Model):
    date = models.DateField()
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    orders = models.IntegerField(default=0)
    customers = models.IntegerField(default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    returns = models.IntegerField(default=0)
    region = models.CharField(max_length=100, blank=True, default="")
    category = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sales Data"
        verbose_name_plural = "Sales Data"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} - {self.region} - ${self.revenue}"


class Goal(models.Model):
    CATEGORY_CHOICES = [
        ("revenue", "Revenue"),
        ("growth", "Growth"),
        ("customers", "Customers"),
        ("efficiency", "Efficiency"),
        ("product", "Product"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    target_value = models.DecimalField(max_digits=15, decimal_places=2)
    current_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unit = models.CharField(max_length=20, blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="revenue")
    deadline = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.progress_pct}%)"

    @property
    def progress_pct(self):
        if self.target_value and self.target_value > 0:
            return min(round(float(self.current_value) / float(self.target_value) * 100, 1), 100)
        return 0

    @property
    def days_remaining(self):
        if self.deadline:
            delta = self.deadline - date_type.today()
            return max(0, delta.days)
        return None

    @property
    def is_overdue(self):
        if self.deadline:
            return date_type.today() > self.deadline and not self.is_completed
        return False


class Insight(models.Model):
    TYPE_CHOICES = [
        ("trend", "Trend"),
        ("anomaly", "Anomaly"),
        ("milestone", "Milestone"),
        ("recommendation", "Recommendation"),
        ("comparison", "Comparison"),
    ]

    SEVERITY_CHOICES = [
        ("positive", "Positive"),
        ("neutral", "Neutral"),
        ("negative", "Negative"),
        ("warning", "Warning"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    insight_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="trend")
    metric_name = models.CharField(max_length=100, blank=True, default="")
    metric_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    change_pct = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="neutral")
    icon = models.CharField(max_length=50, blank=True, default="lightbulb")
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.severity}] {self.title}"

    @property
    def severity_color(self):
        return {
            "positive": "emerald",
            "neutral": "blue",
            "negative": "red",
            "warning": "amber",
        }.get(self.severity, "gray")

    @property
    def is_valid(self):
        if self.valid_until:
            return timezone.now() < self.valid_until
        return True


class SavedReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_reports")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    config = models.JSONField(default=dict, blank=True)
    is_bookmarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Bookmark(models.Model):
    SECTION_TYPE_CHOICES = [
        ("dashboard", "Dashboard"),
        ("report", "Report"),
        ("kpi", "KPI"),
        ("chart", "Chart"),
        ("goal", "Goal"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    name = models.CharField(max_length=200)
    url = models.CharField(max_length=500)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPE_CHOICES, default="dashboard")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.section_type})"


class ExportLog(models.Model):
    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("pdf", "PDF"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="export_logs")
    export_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="csv")
    record_count = models.IntegerField(default=0)
    file_size = models.IntegerField(default=0, help_text="Size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} exported {self.export_format} ({self.record_count} records)"
