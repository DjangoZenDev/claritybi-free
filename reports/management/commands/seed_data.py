"""Management command to seed the database with sample data."""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from reports.models import (
    Bookmark, Dashboard, DataSource, ExportLog, Goal, Insight, KPI,
    SalesData, SavedReport, Widget,
)

User = get_user_model()

REGIONS = ["North America", "Europe", "Asia Pacific", "Latin America", "Middle East"]
CATEGORIES = ["Electronics", "Apparel", "Home & Garden", "Food & Beverage", "Health & Beauty"]

CHART_COLORS = {
    "blue": "#3b82f6",
    "indigo": "#6366f1",
    "violet": "#8b5cf6",
    "amber": "#f59e0b",
    "emerald": "#10b981",
}


class Command(BaseCommand):
    help = "Seed the database with sample dashboards, widgets, KPIs, and 90 days of sales data."

    def handle(self, *args, **options):
        self.stdout.write("Seeding ClarityBI database...")

        # Create admin user if not exists
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@claritybi.local",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin_user.set_password("admin")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("  Created admin user (admin/admin)"))

        # Create Data Sources
        DataSource.objects.all().delete()
        sources = [
            DataSource(name="Primary Database", description="Main PostgreSQL data warehouse", source_type="database", connection_string="postgresql://localhost/warehouse"),
            DataSource(name="Sales CSV Import", description="Monthly sales CSV uploads", source_type="csv", connection_string="/data/imports/"),
            DataSource(name="Analytics API", description="Google Analytics integration", source_type="api", connection_string="https://analytics.example.com/api/v2"),
        ]
        DataSource.objects.bulk_create(sources)
        self.stdout.write(self.style.SUCCESS("  Created 3 data sources"))

        # Create KPIs
        KPI.objects.all().delete()
        kpis = [
            KPI(name="Monthly Revenue", value=Decimal("284750.00"), target=Decimal("300000.00"), unit="$", trend="up", period="This Month"),
            KPI(name="Total Orders", value=Decimal("3842"), target=Decimal("4000"), unit="", trend="up", period="This Month"),
            KPI(name="Active Customers", value=Decimal("1256"), target=Decimal("1500"), unit="", trend="up", period="This Month"),
            KPI(name="Avg Order Value", value=Decimal("74.12"), target=Decimal("80.00"), unit="$", trend="down", period="This Month"),
            KPI(name="Conversion Rate", value=Decimal("3.24"), target=Decimal("4.00"), unit="%", trend="flat", period="This Month"),
            KPI(name="Customer Retention", value=Decimal("87.5"), target=Decimal("90.0"), unit="%", trend="up", period="This Quarter"),
        ]
        KPI.objects.bulk_create(kpis)
        self.stdout.write(self.style.SUCCESS("  Created 6 KPIs"))

        # Create Sales Data - 90 days across regions and categories
        SalesData.objects.all().delete()
        sales_records = []
        today = date.today()

        for day_offset in range(90):
            current_date = today - timedelta(days=day_offset)
            day_of_week = current_date.weekday()

            for region in REGIONS:
                for category in CATEGORIES:
                    # Base revenue varies by region and category
                    region_mult = {
                        "North America": 1.4,
                        "Europe": 1.2,
                        "Asia Pacific": 1.0,
                        "Latin America": 0.7,
                        "Middle East": 0.5,
                    }[region]

                    cat_mult = {
                        "Electronics": 1.5,
                        "Apparel": 1.1,
                        "Home & Garden": 0.9,
                        "Food & Beverage": 0.8,
                        "Health & Beauty": 1.0,
                    }[category]

                    # Weekend dip
                    weekend_mult = 0.7 if day_of_week >= 5 else 1.0

                    # Slight upward trend over time (more recent = higher)
                    trend_mult = 1.0 + (90 - day_offset) * 0.002

                    base_revenue = 500 * region_mult * cat_mult * weekend_mult * trend_mult
                    revenue = round(base_revenue * random.uniform(0.75, 1.35), 2)
                    orders = max(1, int(revenue / random.uniform(50, 120)))
                    customers = max(1, int(orders * random.uniform(0.6, 0.95)))
                    aov = round(revenue / orders, 2) if orders > 0 else 0

                    sales_records.append(
                        SalesData(
                            date=current_date,
                            revenue=Decimal(str(revenue)),
                            orders=orders,
                            customers=customers,
                            avg_order_value=Decimal(str(aov)),
                            region=region,
                            category=category,
                        )
                    )

        SalesData.objects.bulk_create(sales_records, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"  Created {len(sales_records)} sales data records (90 days x 5 regions x 5 categories)"))

        # Create Dashboards and Widgets
        Dashboard.objects.all().delete()

        # Main overview dashboard
        main_dash = Dashboard.objects.create(
            name="Business Overview",
            slug="business-overview",
            description="High-level business metrics and KPIs for executive review.",
            owner=admin_user,
            is_public=True,
        )
        Widget.objects.bulk_create([
            Widget(dashboard=main_dash, title="Key Performance Indicators", widget_type="kpi_card", order=1, position_x=0, position_y=0, width=12, height=2),
            Widget(dashboard=main_dash, title="Revenue Trend", widget_type="line_chart", order=2, position_x=0, position_y=2, width=12, height=4),
            Widget(dashboard=main_dash, title="Sales by Region", widget_type="bar_chart", order=3, position_x=0, position_y=6, width=6, height=4),
            Widget(dashboard=main_dash, title="Sales by Category", widget_type="pie_chart", order=4, position_x=6, position_y=6, width=6, height=4),
            Widget(dashboard=main_dash, title="Sales Detail", widget_type="table", order=5, position_x=0, position_y=10, width=12, height=6),
        ])

        # Sales dashboard
        sales_dash = Dashboard.objects.create(
            name="Sales Analytics",
            slug="sales-analytics",
            description="Detailed sales performance analysis by region and product category.",
            owner=admin_user,
            is_public=True,
        )
        Widget.objects.bulk_create([
            Widget(dashboard=sales_dash, title="Revenue KPIs", widget_type="kpi_card", order=1, position_x=0, position_y=0, width=12, height=2),
            Widget(dashboard=sales_dash, title="Daily Revenue", widget_type="line_chart", order=2, position_x=0, position_y=2, width=12, height=4),
            Widget(dashboard=sales_dash, title="Regional Breakdown", widget_type="bar_chart", order=3, position_x=0, position_y=6, width=12, height=4),
            Widget(dashboard=sales_dash, title="Transaction Log", widget_type="table", order=4, position_x=0, position_y=10, width=12, height=6),
        ])

        # Product dashboard
        product_dash = Dashboard.objects.create(
            name="Product Performance",
            slug="product-performance",
            description="Product category analysis and performance tracking.",
            owner=admin_user,
            is_public=True,
        )
        Widget.objects.bulk_create([
            Widget(dashboard=product_dash, title="Category Metrics", widget_type="kpi_card", order=1, position_x=0, position_y=0, width=12, height=2),
            Widget(dashboard=product_dash, title="Category Distribution", widget_type="pie_chart", order=2, position_x=0, position_y=2, width=6, height=4),
            Widget(dashboard=product_dash, title="Category Revenue Trend", widget_type="line_chart", order=3, position_x=6, position_y=2, width=6, height=4),
        ])

        self.stdout.write(self.style.SUCCESS("  Created 3 dashboards with widgets"))

        # Goals
        Goal.objects.all().delete()
        goals_data = [
            ("Q2 Revenue Target", "Reach $300K in quarterly revenue", Decimal("300000"), Decimal("284750"), "$", "revenue", date.today() + timedelta(days=45)),
            ("Customer Acquisition", "Acquire 1,500 active customers", Decimal("1500"), Decimal("1256"), "", "customers", date.today() + timedelta(days=30)),
            ("Reduce Returns Rate", "Keep returns below 2% of orders", Decimal("2"), Decimal("1.8"), "%", "efficiency", date.today() + timedelta(days=60)),
            ("Launch APAC Expansion", "Grow Asia Pacific revenue to $50K", Decimal("50000"), Decimal("32000"), "$", "growth", date.today() + timedelta(days=90)),
            ("Improve AOV", "Increase average order value to $80", Decimal("80"), Decimal("74.12"), "$", "product", date.today() + timedelta(days=20)),
        ]
        for name, desc, target, current, unit, category, deadline in goals_data:
            Goal.objects.create(name=name, description=desc, target_value=target, current_value=current, unit=unit, category=category, deadline=deadline)
        self.stdout.write(self.style.SUCCESS(f"  Created {len(goals_data)} goals"))

        # Insights
        Insight.objects.all().delete()
        from django.utils import timezone
        insights_data = [
            ("Revenue trending up", "Revenue has increased 12.5% compared to last period, driven by strong Electronics and Apparel sales.", "trend", "Revenue", Decimal("284750"), Decimal("12.5"), "positive", "trending-up"),
            ("North America leads", "North America accounts for 38% of total revenue, outperforming all other regions.", "comparison", "Region", None, None, "neutral", "globe"),
            ("Conversion rate stable", "Conversion rate has remained flat at 3.24%. Consider A/B testing checkout flow.", "recommendation", "Conversion", Decimal("3.24"), Decimal("0"), "warning", "lightbulb"),
            ("Customer milestone", "You've reached 1,256 active customers — 84% of your Q2 target!", "milestone", "Customers", Decimal("1256"), None, "positive", "trophy"),
            ("Returns anomaly", "Returns in Health & Beauty spiked 2.3x above average this week.", "anomaly", "Returns", None, Decimal("230"), "negative", "alert"),
        ]
        for title, desc, itype, metric, value, change, severity, icon in insights_data:
            Insight.objects.create(
                title=title, description=desc, insight_type=itype,
                metric_name=metric, metric_value=value, change_pct=change,
                severity=severity, icon=icon, is_active=True,
                valid_until=timezone.now() + timedelta(days=7),
            )
        self.stdout.write(self.style.SUCCESS(f"  Created {len(insights_data)} insights"))

        # Update KPIs with sparkline data and comparison values
        for kpi in KPI.objects.all():
            base = float(kpi.value)
            sparkline = [round(base * random.uniform(0.85, 1.15), 2) for _ in range(14)]
            kpi.sparkline_data = sparkline
            kpi.comparison_value = Decimal(str(round(base * random.uniform(0.8, 0.95), 2)))
            kpi.comparison_label = "vs last period"
            kpi.save()
        self.stdout.write(self.style.SUCCESS("  Updated KPIs with sparkline data"))

        # Bookmarks
        Bookmark.objects.filter(user=admin_user).delete()
        Bookmark.objects.create(user=admin_user, name="Business Overview", url="/", section_type="dashboard")
        Bookmark.objects.create(user=admin_user, name="Goals", url="/goals/", section_type="goal")
        self.stdout.write(self.style.SUCCESS("  Created sample bookmarks"))

        # Saved Report
        SavedReport.objects.filter(user=admin_user).delete()
        SavedReport.objects.create(
            user=admin_user, name="Monthly Executive Summary",
            config={"sections": {"kpis": True, "revenue_chart": True, "category_charts": True, "sales_table": False}},
        )
        self.stdout.write(self.style.SUCCESS("  Created sample saved report"))

        self.stdout.write(self.style.SUCCESS("\nClarityBI Pro seeding complete!"))
        self.stdout.write("Login: admin / admin")
