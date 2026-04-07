"""Views for ClarityBI reports application."""

import csv
import io
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Bookmark,
    Dashboard,
    ExportLog,
    Goal,
    Insight,
    KPI,
    SalesData,
    SavedReport,
    Widget,
)


def _get_date_range(request):
    """Extract date range from request parameters."""
    days = int(request.GET.get("days", 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date, days


def _calc_change(current, previous):
    """Calculate percentage change between two values."""
    if not current or not previous or previous == 0:
        return 0, "flat"
    change = ((float(current) - float(previous)) / float(previous)) * 100
    trend = "up" if change > 0 else "down" if change < 0 else "flat"
    return round(change, 1), trend


@login_required
def bi_dashboard(request):
    """Main BI dashboard view with configurable widgets."""
    start_date, end_date, days = _get_date_range(request)
    kpis = KPI.objects.all()
    dashboards = Dashboard.objects.filter(is_public=True)

    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)
    summary = sales_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
    )

    insights = Insight.objects.filter(is_active=True)
    goals = Goal.objects.all()

    # Comparison data: current vs previous period
    prev_start = start_date - timedelta(days=days)
    prev_qs = SalesData.objects.filter(date__gte=prev_start, date__lt=start_date)
    prev_summary = prev_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
    )
    rev_change, rev_trend = _calc_change(summary["total_revenue"], prev_summary["total_revenue"])
    ord_change, ord_trend = _calc_change(summary["total_orders"], prev_summary["total_orders"])

    context = {
        "kpis": kpis,
        "dashboards": dashboards,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "insights": insights,
        "goals": goals,
        "rev_change": rev_change,
        "rev_trend": rev_trend,
        "ord_change": ord_change,
        "ord_trend": ord_trend,
        "page_title": "ClarityBI Dashboard",
    }
    return render(request, "reports/dashboard.html", context)


@login_required
def dashboard_detail(request, slug):
    """View a specific dashboard with its widgets."""
    dashboard = get_object_or_404(Dashboard, slug=slug)
    widgets = dashboard.widgets.all()
    start_date, end_date, days = _get_date_range(request)

    context = {
        "dashboard": dashboard,
        "widgets": widgets,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "page_title": dashboard.name,
    }
    return render(request, "reports/dashboard.html", context)


@login_required
def dashboard_list(request):
    """List all available dashboards."""
    dashboards = Dashboard.objects.filter(is_public=True)
    context = {
        "dashboards": dashboards,
        "page_title": "Dashboards",
    }
    return render(request, "reports/dashboard_list.html", context)


@login_required
def kpi_overview(request):
    """HTMX partial for KPI cards row with WoW and MoM deltas."""
    start_date, end_date, days = _get_date_range(request)
    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)

    summary = sales_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
    )

    prev_start = start_date - timedelta(days=days)
    prev_qs = SalesData.objects.filter(date__gte=prev_start, date__lt=start_date)
    prev_summary = prev_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
    )

    rev_change, rev_trend = _calc_change(summary["total_revenue"], prev_summary["total_revenue"])
    ord_change, ord_trend = _calc_change(summary["total_orders"], prev_summary["total_orders"])
    cust_change, cust_trend = _calc_change(summary["total_customers"], prev_summary["total_customers"])
    aov_change, aov_trend = _calc_change(summary["avg_order"], prev_summary["avg_order"])

    # WoW: current 7 days vs previous 7 days
    today = timezone.now().date()
    wow_current_start = today - timedelta(days=7)
    wow_prev_start = today - timedelta(days=14)
    wow_current = SalesData.objects.filter(date__gt=wow_current_start, date__lte=today).aggregate(
        rev=Sum("revenue"), orders=Sum("orders"),
    )
    wow_prev = SalesData.objects.filter(date__gt=wow_prev_start, date__lte=wow_current_start).aggregate(
        rev=Sum("revenue"), orders=Sum("orders"),
    )
    wow_rev_delta, _ = _calc_change(wow_current["rev"], wow_prev["rev"])
    wow_ord_delta, _ = _calc_change(wow_current["orders"], wow_prev["orders"])

    # MoM: current 30 days vs previous 30 days
    mom_current_start = today - timedelta(days=30)
    mom_prev_start = today - timedelta(days=60)
    mom_current = SalesData.objects.filter(date__gt=mom_current_start, date__lte=today).aggregate(
        rev=Sum("revenue"), orders=Sum("orders"),
    )
    mom_prev = SalesData.objects.filter(date__gt=mom_prev_start, date__lte=mom_current_start).aggregate(
        rev=Sum("revenue"), orders=Sum("orders"),
    )
    mom_rev_delta, _ = _calc_change(mom_current["rev"], mom_prev["rev"])
    mom_ord_delta, _ = _calc_change(mom_current["orders"], mom_prev["orders"])

    # Sparkline data -- daily revenue for the period
    daily = (
        sales_qs.values("date")
        .annotate(day_rev=Sum("revenue"), day_orders=Sum("orders"), day_cust=Sum("customers"))
        .order_by("date")
    )
    rev_spark = [float(d["day_rev"]) for d in daily]
    ord_spark = [int(d["day_orders"]) for d in daily]
    cust_spark = [int(d["day_cust"]) for d in daily]

    # Also pull sparkline_data from KPI model objects
    kpi_sparklines = {}
    for kpi in KPI.objects.all():
        if kpi.sparkline_data:
            kpi_sparklines[kpi.name] = json.dumps(kpi.sparkline_data)

    total_orders = summary["total_orders"] or 0
    total_customers = summary["total_customers"] or 0
    total_revenue = float(summary["total_revenue"] or 0)
    conv_rate = round((total_orders / total_customers * 100), 1) if total_customers else 0
    rev_per_cust = round(total_revenue / total_customers, 2) if total_customers else 0

    prev_orders = prev_summary["total_orders"] or 0
    prev_customers = prev_summary["total_customers"] or 0
    prev_conv = round((prev_orders / prev_customers * 100), 1) if prev_customers else 0
    prev_rpc = round(float(prev_summary["total_revenue"] or 0) / prev_customers, 2) if prev_customers else 0
    conv_change, conv_trend = _calc_change(conv_rate, prev_conv)
    rpc_change, rpc_trend = _calc_change(rev_per_cust, prev_rpc)

    # Fetch KPI model targets for progress bars
    kpi_targets = {}
    for kpi in KPI.objects.all():
        kpi_targets[kpi.name] = {
            "target": float(kpi.target) if kpi.target else None,
            "comparison_label": kpi.comparison_label,
            "progress_pct": kpi.progress_pct,
        }

    kpi_cards = [
        {
            "name": "Revenue",
            "value": summary["total_revenue"] or 0,
            "unit": "$",
            "change": rev_change,
            "trend": rev_trend,
            "format": "currency",
            "sparkline": kpi_sparklines.get("Revenue", json.dumps(rev_spark[-14:])),
            "color": "#3b82f6",
            "wow_delta": wow_rev_delta,
            "mom_delta": mom_rev_delta,
            "comparison_label": kpi_targets.get("Revenue", {}).get("comparison_label", ""),
            "target_pct": kpi_targets.get("Revenue", {}).get("progress_pct"),
        },
        {
            "name": "Orders",
            "value": total_orders,
            "unit": "",
            "change": ord_change,
            "trend": ord_trend,
            "format": "number",
            "sparkline": kpi_sparklines.get("Orders", json.dumps(ord_spark[-14:])),
            "color": "#8b5cf6",
            "wow_delta": wow_ord_delta,
            "mom_delta": mom_ord_delta,
            "comparison_label": kpi_targets.get("Orders", {}).get("comparison_label", ""),
            "target_pct": kpi_targets.get("Orders", {}).get("progress_pct"),
        },
        {
            "name": "Customers",
            "value": total_customers,
            "unit": "",
            "change": cust_change,
            "trend": cust_trend,
            "format": "number",
            "sparkline": kpi_sparklines.get("Customers", json.dumps(cust_spark[-14:])),
            "color": "#10b981",
            "wow_delta": None,
            "mom_delta": None,
            "comparison_label": kpi_targets.get("Customers", {}).get("comparison_label", ""),
            "target_pct": kpi_targets.get("Customers", {}).get("progress_pct"),
        },
        {
            "name": "Avg Order Value",
            "value": summary["avg_order"] or 0,
            "unit": "$",
            "change": aov_change,
            "trend": aov_trend,
            "format": "currency",
            "sparkline": kpi_sparklines.get("Avg Order Value", "[]"),
            "color": "#f59e0b",
            "wow_delta": None,
            "mom_delta": None,
            "comparison_label": kpi_targets.get("Avg Order Value", {}).get("comparison_label", ""),
            "target_pct": kpi_targets.get("Avg Order Value", {}).get("progress_pct"),
        },
        {
            "name": "Conversion Rate",
            "value": conv_rate,
            "unit": "%",
            "change": conv_change,
            "trend": conv_trend,
            "format": "percent",
            "sparkline": "[]",
            "color": "#ec4899",
            "wow_delta": None,
            "mom_delta": None,
            "comparison_label": "",
            "target_pct": None,
        },
        {
            "name": "Rev / Customer",
            "value": rev_per_cust,
            "unit": "$",
            "change": rpc_change,
            "trend": rpc_trend,
            "format": "currency",
            "sparkline": "[]",
            "color": "#6366f1",
            "wow_delta": None,
            "mom_delta": None,
            "comparison_label": "",
            "target_pct": None,
        },
    ]

    context = {
        "kpi_cards": kpi_cards,
        "days": days,
    }
    return render(request, "reports/partials/kpi_row.html", context)


@login_required
def revenue_chart(request):
    """HTMX partial for revenue chart data."""
    start_date, end_date, days = _get_date_range(request)
    sales_qs = (
        SalesData.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(total_revenue=Sum("revenue"), total_orders=Sum("orders"))
        .order_by("date")
    )

    labels = [entry["date"].strftime("%b %d") for entry in sales_qs]
    revenue_data = [float(entry["total_revenue"]) for entry in sales_qs]
    orders_data = [int(entry["total_orders"]) for entry in sales_qs]

    context = {
        "labels_json": json.dumps(labels),
        "revenue_json": json.dumps(revenue_data),
        "orders_json": json.dumps(orders_data),
        "days": days,
    }
    return render(request, "reports/partials/revenue_chart.html", context)


@login_required
def category_charts(request):
    """HTMX partial for category and region charts."""
    start_date, end_date, days = _get_date_range(request)
    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)

    by_region = (
        sales_qs.values("region")
        .annotate(total=Sum("revenue"))
        .order_by("-total")
    )
    region_labels = [r["region"] for r in by_region]
    region_data = [float(r["total"]) for r in by_region]

    by_category = (
        sales_qs.values("category")
        .annotate(total=Sum("revenue"))
        .order_by("-total")
    )
    category_labels = [c["category"] for c in by_category]
    category_data = [float(c["total"]) for c in by_category]

    context = {
        "region_labels_json": json.dumps(region_labels),
        "region_data_json": json.dumps(region_data),
        "category_labels_json": json.dumps(category_labels),
        "category_data_json": json.dumps(category_data),
        "days": days,
    }
    return render(request, "reports/partials/category_charts.html", context)


@login_required
def sales_table(request):
    """HTMX partial for sales data table with sorting/filtering."""
    start_date, end_date, days = _get_date_range(request)
    sort_by = request.GET.get("sort", "-date")
    region_filter = request.GET.get("region", "")
    category_filter = request.GET.get("category", "")
    page = int(request.GET.get("page", 1))
    per_page = 15

    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)

    if region_filter:
        sales_qs = sales_qs.filter(region=region_filter)
    if category_filter:
        sales_qs = sales_qs.filter(category=category_filter)

    allowed_sorts = ["date", "-date", "revenue", "-revenue", "orders", "-orders", "region", "-region", "category", "-category"]
    if sort_by in allowed_sorts:
        sales_qs = sales_qs.order_by(sort_by)

    total_count = sales_qs.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page
    sales = sales_qs[offset : offset + per_page]

    regions = SalesData.objects.values_list("region", flat=True).distinct().order_by("region")
    categories = SalesData.objects.values_list("category", flat=True).distinct().order_by("category")

    context = {
        "sales": sales,
        "sort_by": sort_by,
        "region_filter": region_filter,
        "category_filter": category_filter,
        "regions": regions,
        "categories": categories,
        "page": page,
        "total_pages": total_pages,
        "total_count": total_count,
        "days": days,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }
    return render(request, "reports/partials/sales_table.html", context)


@login_required
def widget_content(request, widget_id):
    """HTMX endpoint that renders widget content based on widget type."""
    widget = get_object_or_404(Widget, pk=widget_id)
    start_date, end_date, days = _get_date_range(request)

    if widget.widget_type == "kpi_card":
        return kpi_overview(request)
    elif widget.widget_type == "line_chart":
        return revenue_chart(request)
    elif widget.widget_type in ("bar_chart", "pie_chart"):
        return category_charts(request)
    elif widget.widget_type == "table":
        return sales_table(request)
    elif widget.widget_type == "metric":
        kpis = KPI.objects.all()
        return render(request, "reports/partials/kpi_row.html", {"kpi_cards": [], "kpis": kpis})
    elif widget.widget_type == "goal_ring":
        return goals_partial(request)
    elif widget.widget_type == "insight":
        return insights_partial(request)

    return HttpResponse("<p>Unknown widget type</p>")


@login_required
def export_report(request):
    """Export sales data as CSV or PDF."""
    export_format = request.GET.get("format", "csv")
    start_date, end_date, days = _get_date_range(request)

    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date).order_by("date")

    if export_format == "pdf":
        return _generate_pdf_report(request, sales_qs, start_date, end_date)

    if export_format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="claritybi_report_{start_date}_{end_date}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Date", "Region", "Category", "Revenue", "Orders", "Customers", "Avg Order Value"])
        for sale in sales_qs:
            writer.writerow([
                sale.date,
                sale.region,
                sale.category,
                sale.revenue,
                sale.orders,
                sale.customers,
                sale.avg_order_value,
            ])

        if request.user.is_authenticated:
            ExportLog.objects.create(
                user=request.user,
                export_format="csv",
                record_count=sales_qs.count(),
                file_size=len(response.content),
            )

        return response

    return HttpResponse("Unsupported format", status=400)


def _generate_pdf_report(request, sales_qs, start_date, end_date):
    """Generate a PDF report using reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph("ClarityBI Report", styles["Title"]))
    elements.append(Paragraph(f"Date Range: {start_date} to {end_date}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    # KPI Summary Table
    summary = sales_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
        total_profit=Sum("profit"),
        total_returns=Sum("returns"),
    )
    kpi_data = [
        ["Metric", "Value"],
        ["Total Revenue", f"${float(summary['total_revenue'] or 0):,.2f}"],
        ["Total Orders", f"{summary['total_orders'] or 0:,}"],
        ["Total Customers", f"{summary['total_customers'] or 0:,}"],
        ["Avg Order Value", f"${float(summary['avg_order'] or 0):,.2f}"],
        ["Total Profit", f"${float(summary['total_profit'] or 0):,.2f}"],
        ["Total Returns", f"{summary['total_returns'] or 0:,}"],
    ]
    elements.append(Paragraph("KPI Summary", styles["Heading2"]))
    kpi_table = Table(kpi_data, colWidths=[3 * inch, 3 * inch])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Revenue by Region
    by_region = (
        sales_qs.values("region")
        .annotate(total_rev=Sum("revenue"), total_ord=Sum("orders"))
        .order_by("-total_rev")
    )
    region_data = [["Region", "Revenue", "Orders"]]
    for r in by_region:
        region_data.append([
            r["region"] or "N/A",
            f"${float(r['total_rev']):,.2f}",
            f"{r['total_ord']:,}",
        ])

    if len(region_data) > 1:
        elements.append(Paragraph("Revenue by Region", styles["Heading2"]))
        region_table = Table(region_data, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        region_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(region_table)
        elements.append(Spacer(1, 0.3 * inch))

    # Revenue by Category
    by_category = (
        sales_qs.values("category")
        .annotate(total_rev=Sum("revenue"), total_ord=Sum("orders"))
        .order_by("-total_rev")
    )
    cat_data = [["Category", "Revenue", "Orders"]]
    for c in by_category:
        cat_data.append([
            c["category"] or "N/A",
            f"${float(c['total_rev']):,.2f}",
            f"{c['total_ord']:,}",
        ])

    if len(cat_data) > 1:
        elements.append(Paragraph("Revenue by Category", styles["Heading2"]))
        cat_table = Table(cat_data, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b5cf6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(cat_table)

    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="claritybi_report_{start_date}_{end_date}.pdf"'

    if request.user.is_authenticated:
        ExportLog.objects.create(
            user=request.user,
            export_format="pdf",
            record_count=sales_qs.count(),
            file_size=len(pdf_content),
        )

    return response


@login_required
def top_customers(request):
    """HTMX partial for top customers by revenue."""
    start_date, end_date, days = _get_date_range(request)
    top = (
        SalesData.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("region")
        .annotate(
            total_revenue=Sum("revenue"),
            total_orders=Sum("orders"),
            total_customers=Sum("customers"),
        )
        .order_by("-total_revenue")[:8]
    )
    context = {"top_customers": top, "days": days}
    return render(request, "reports/partials/top_customers.html", context)


@login_required
def recent_orders(request):
    """HTMX partial for recent orders feed."""
    recent = (
        SalesData.objects.all()
        .order_by("-date", "-revenue")[:15]
    )
    context = {"recent_orders": recent}
    return render(request, "reports/partials/recent_orders.html", context)


# ---------------------------------------------------------------------------
# New views
# ---------------------------------------------------------------------------


@login_required
def generate_insights(request):
    """Analyze SalesData and generate Insight objects."""
    today = timezone.now().date()

    # Delete old insights before regenerating
    Insight.objects.all().delete()

    # 1) Revenue trend: last 14 days vs previous 14 days
    current_start = today - timedelta(days=14)
    prev_start = today - timedelta(days=28)
    current_rev = SalesData.objects.filter(date__gt=current_start, date__lte=today).aggregate(r=Sum("revenue"))["r"] or Decimal("0")
    prev_rev = SalesData.objects.filter(date__gt=prev_start, date__lte=current_start).aggregate(r=Sum("revenue"))["r"] or Decimal("0")

    if prev_rev > 0:
        rev_pct = round(((float(current_rev) - float(prev_rev)) / float(prev_rev)) * 100, 1)
        if rev_pct > 10:
            Insight.objects.create(
                title="Revenue Trending Up",
                description=f"Revenue increased {rev_pct}% over the last 14 days compared to the prior 14-day period.",
                insight_type="trend",
                metric_name="Revenue",
                metric_value=current_rev,
                change_pct=Decimal(str(rev_pct)),
                severity="positive",
                icon="trending_up",
                valid_until=timezone.now() + timedelta(days=1),
            )
        elif rev_pct < -10:
            Insight.objects.create(
                title="Revenue Trending Down",
                description=f"Revenue decreased {abs(rev_pct)}% over the last 14 days compared to the prior 14-day period.",
                insight_type="trend",
                metric_name="Revenue",
                metric_value=current_rev,
                change_pct=Decimal(str(rev_pct)),
                severity="negative",
                icon="trending_down",
                valid_until=timezone.now() + timedelta(days=1),
            )

    # 2) Top performing region
    top_region = (
        SalesData.objects.filter(date__gt=current_start, date__lte=today)
        .values("region")
        .annotate(total=Sum("revenue"))
        .order_by("-total")
        .first()
    )
    if top_region and top_region["region"]:
        Insight.objects.create(
            title=f"Top Region: {top_region['region']}",
            description=f"{top_region['region']} leads with ${float(top_region['total']):,.2f} in revenue over the last 14 days.",
            insight_type="comparison",
            metric_name="Region Revenue",
            metric_value=top_region["total"],
            severity="positive",
            icon="star",
            valid_until=timezone.now() + timedelta(days=1),
        )

    # 3) KPI milestones
    for kpi in KPI.objects.all():
        if kpi.progress_pct >= 100:
            Insight.objects.create(
                title=f"Goal Reached: {kpi.name}",
                description=f"{kpi.name} has reached {kpi.progress_pct}% of its target.",
                insight_type="milestone",
                metric_name=kpi.name,
                metric_value=kpi.value,
                severity="positive",
                icon="check_circle",
                valid_until=timezone.now() + timedelta(days=7),
            )

    # 4) WoW comparison
    wow_current_start = today - timedelta(days=7)
    wow_prev_start = today - timedelta(days=14)
    wow_cur = SalesData.objects.filter(date__gt=wow_current_start, date__lte=today).aggregate(r=Sum("revenue"))["r"] or Decimal("0")
    wow_prev = SalesData.objects.filter(date__gt=wow_prev_start, date__lte=wow_current_start).aggregate(r=Sum("revenue"))["r"] or Decimal("0")
    if wow_prev > 0:
        wow_pct = round(((float(wow_cur) - float(wow_prev)) / float(wow_prev)) * 100, 1)
        sev = "positive" if wow_pct > 0 else "negative" if wow_pct < 0 else "neutral"
        Insight.objects.create(
            title="Week-over-Week Revenue",
            description=f"This week's revenue is {'up' if wow_pct >= 0 else 'down'} {abs(wow_pct)}% compared to last week.",
            insight_type="comparison",
            metric_name="WoW Revenue",
            metric_value=wow_cur,
            change_pct=Decimal(str(wow_pct)),
            severity=sev,
            icon="compare_arrows",
            valid_until=timezone.now() + timedelta(days=1),
        )

    referer = request.META.get("HTTP_REFERER", "/")
    return redirect(referer)


@login_required
def insights_partial(request):
    """HTMX partial returning active insights."""
    insights = Insight.objects.filter(is_active=True)
    return render(request, "reports/partials/insights.html", {"insights": insights})


@login_required
def goals_page(request):
    """Full page listing all goals with progress rings."""
    goals = Goal.objects.all()
    context = {
        "goals": goals,
        "page_title": "Goals",
        "categories": Goal.CATEGORY_CHOICES,
    }
    return render(request, "reports/goals.html", context)


@login_required
def goals_partial(request):
    """HTMX partial for dashboard goals widget (top 4 goals)."""
    goals = Goal.objects.filter(is_completed=False)[:4]
    return render(request, "reports/partials/goals.html", {"goals": goals})


@login_required
def create_goal(request):
    """POST: create Goal from form data. GET: return form partial."""
    if request.method == "POST":
        Goal.objects.create(
            name=request.POST.get("name", ""),
            description=request.POST.get("description", ""),
            target_value=Decimal(request.POST.get("target_value", "0")),
            current_value=Decimal(request.POST.get("current_value", "0")),
            unit=request.POST.get("unit", ""),
            category=request.POST.get("category", "revenue"),
            deadline=request.POST.get("deadline") or None,
        )
        return redirect("reports:goals_page")
    return render(request, "reports/partials/goal_form.html", {"categories": Goal.CATEGORY_CHOICES})


@login_required
def update_goal(request, pk):
    """POST: update goal fields, handle marking complete."""
    goal = get_object_or_404(Goal, pk=pk)
    if request.method == "POST":
        goal.name = request.POST.get("name", goal.name)
        goal.description = request.POST.get("description", goal.description)
        if request.POST.get("target_value"):
            goal.target_value = Decimal(request.POST["target_value"])
        if request.POST.get("current_value"):
            goal.current_value = Decimal(request.POST["current_value"])
        goal.unit = request.POST.get("unit", goal.unit)
        goal.category = request.POST.get("category", goal.category)
        if request.POST.get("deadline"):
            goal.deadline = request.POST["deadline"]
        if request.POST.get("mark_complete"):
            goal.is_completed = True
        goal.save()
    return redirect("reports:goals_page")


@login_required
def delete_goal(request, pk):
    """POST: delete goal."""
    if request.method == "POST":
        goal = get_object_or_404(Goal, pk=pk)
        goal.delete()
    return redirect("reports:goals_page")


@login_required
def time_comparison(request):
    """JSON: current period vs previous period daily revenue for comparison chart."""
    start_date, end_date, days = _get_date_range(request)
    prev_start = start_date - timedelta(days=days)

    current_data = (
        SalesData.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(revenue=Sum("revenue"))
        .order_by("date")
    )
    prev_data = (
        SalesData.objects.filter(date__gte=prev_start, date__lt=start_date)
        .values("date")
        .annotate(revenue=Sum("revenue"))
        .order_by("date")
    )

    return JsonResponse({
        "current": [
            {"date": d["date"].isoformat(), "revenue": float(d["revenue"])}
            for d in current_data
        ],
        "previous": [
            {"date": d["date"].isoformat(), "revenue": float(d["revenue"])}
            for d in prev_data
        ],
        "days": days,
    })


@login_required
def report_builder(request):
    """Full page with available metrics list and saved reports."""
    saved_reports = SavedReport.objects.filter(user=request.user)
    metrics = [
        {"key": "revenue", "label": "Revenue"},
        {"key": "orders", "label": "Orders"},
        {"key": "customers", "label": "Customers"},
        {"key": "avg_order_value", "label": "Avg Order Value"},
        {"key": "profit", "label": "Profit"},
        {"key": "returns", "label": "Returns"},
    ]
    regions = list(SalesData.objects.values_list("region", flat=True).distinct().order_by("region"))
    categories = list(SalesData.objects.values_list("category", flat=True).distinct().order_by("category"))

    context = {
        "saved_reports": saved_reports,
        "metrics": metrics,
        "regions": regions,
        "categories": categories,
        "page_title": "Report Builder",
    }
    return render(request, "reports/report_builder.html", context)


@login_required
def save_report(request):
    """POST: save SavedReport config from JSON body or form data."""
    if request.method == "POST":
        # Support both JSON body and form POST
        content_type = request.content_type or ""
        if "application/json" in content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)
            name = data.get("name", "Untitled Report")
            config = data.get("config", {})
            report_id = data.get("id")
        else:
            name = request.POST.get("name", "Untitled Report")
            sections_json = request.POST.get("sections", "{}")
            try:
                sections = json.loads(sections_json)
            except json.JSONDecodeError:
                sections = {}
            config = {"sections": sections}
            report_id = request.POST.get("id")

        if report_id:
            report = get_object_or_404(SavedReport, pk=report_id, user=request.user)
            report.name = name
            report.config = config
            report.save()
        else:
            report = SavedReport.objects.create(
                user=request.user,
                name=name,
                config=config,
            )

        # If HTMX request, return status message
        if request.headers.get("HX-Request"):
            return HttpResponse(
                '<p class="text-xs text-emerald-600 font-medium">Report saved successfully.</p>'
            )
        return JsonResponse({"id": report.id, "name": report.name})
    return JsonResponse({"error": "POST required"}, status=405)


@login_required
def load_report(request, pk):
    """Load a saved report and render it."""
    report = get_object_or_404(SavedReport, pk=pk, user=request.user)
    config = report.config or {}

    start_date, end_date, days = _get_date_range(request)
    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)

    selected_metrics = config.get("metrics", ["revenue", "orders"])
    region_filter = config.get("region", "")
    category_filter = config.get("category", "")

    if region_filter:
        sales_qs = sales_qs.filter(region=region_filter)
    if category_filter:
        sales_qs = sales_qs.filter(category=category_filter)

    agg_fields = {}
    for m in selected_metrics:
        if m in ("revenue", "profit"):
            agg_fields[f"total_{m}"] = Sum(m)
        elif m in ("orders", "customers", "returns"):
            agg_fields[f"total_{m}"] = Sum(m)
        elif m == "avg_order_value":
            agg_fields["avg_order_value"] = Avg("avg_order_value")

    summary = sales_qs.aggregate(**agg_fields) if agg_fields else {}

    daily = (
        sales_qs.values("date")
        .annotate(**agg_fields)
        .order_by("date")
    ) if agg_fields else []

    context = {
        "report": report,
        "summary": summary,
        "daily_data": list(daily),
        "selected_metrics": selected_metrics,
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "page_title": report.name,
    }
    return render(request, "reports/report_detail.html", context)


@login_required
def delete_report(request, pk):
    """POST: delete saved report."""
    if request.method == "POST":
        report = get_object_or_404(SavedReport, pk=pk, user=request.user)
        report.delete()
    return redirect("reports:report_builder")


@login_required
def report_preview(request):
    """HTMX partial: render report preview from config params."""
    start_date, end_date, days = _get_date_range(request)
    metrics = request.GET.getlist("metrics", ["revenue"])
    region = request.GET.get("region", "")
    category = request.GET.get("category", "")

    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)
    if region:
        sales_qs = sales_qs.filter(region=region)
    if category:
        sales_qs = sales_qs.filter(category=category)

    agg_fields = {}
    for m in metrics:
        if m in ("revenue", "profit"):
            agg_fields[f"total_{m}"] = Sum(m)
        elif m in ("orders", "customers", "returns"):
            agg_fields[f"total_{m}"] = Sum(m)
        elif m == "avg_order_value":
            agg_fields["avg_order_value"] = Avg("avg_order_value")

    summary = sales_qs.aggregate(**agg_fields) if agg_fields else {}

    context = {
        "summary": summary,
        "metrics": metrics,
        "days": days,
        "record_count": sales_qs.count(),
    }
    return render(request, "reports/partials/report_preview.html", context)


@login_required
def export_pdf(request):
    """PDF download using reportlab with KPI summary and breakdowns."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    start_date, end_date, days = _get_date_range(request)
    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date).order_by("date")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("ClarityBI Report", styles["Title"]))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    # KPI Summary
    summary = sales_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
        total_profit=Sum("profit"),
        total_returns=Sum("returns"),
    )
    kpi_data = [
        ["KPI", "Value"],
        ["Revenue", f"${float(summary['total_revenue'] or 0):,.2f}"],
        ["Orders", f"{summary['total_orders'] or 0:,}"],
        ["Customers", f"{summary['total_customers'] or 0:,}"],
        ["Avg Order Value", f"${float(summary['avg_order'] or 0):,.2f}"],
        ["Profit", f"${float(summary['total_profit'] or 0):,.2f}"],
        ["Returns", f"{summary['total_returns'] or 0:,}"],
    ]
    elements.append(Paragraph("KPI Summary", styles["Heading2"]))
    t = Table(kpi_data, colWidths=[3 * inch, 3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.3 * inch))

    # Revenue Trend (daily)
    daily = (
        sales_qs.values("date")
        .annotate(day_rev=Sum("revenue"), day_orders=Sum("orders"))
        .order_by("date")
    )
    if daily.exists():
        elements.append(Paragraph("Revenue Trend", styles["Heading2"]))
        trend_data = [["Date", "Revenue", "Orders"]]
        for d in daily:
            trend_data.append([
                d["date"].strftime("%Y-%m-%d"),
                f"${float(d['day_rev']):,.2f}",
                f"{d['day_orders']:,}",
            ])
        tt = Table(trend_data, colWidths=[2 * inch, 2.5 * inch, 1.5 * inch])
        tt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(tt)
        elements.append(Spacer(1, 0.3 * inch))

    # Region breakdown
    by_region = (
        sales_qs.values("region")
        .annotate(total_rev=Sum("revenue"), total_ord=Sum("orders"))
        .order_by("-total_rev")
    )
    if by_region.exists():
        elements.append(Paragraph("Revenue by Region", styles["Heading2"]))
        rd = [["Region", "Revenue", "Orders"]]
        for r in by_region:
            rd.append([r["region"] or "N/A", f"${float(r['total_rev']):,.2f}", f"{r['total_ord']:,}"])
        rt = Table(rd, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        rt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(rt)
        elements.append(Spacer(1, 0.3 * inch))

    # Category breakdown
    by_cat = (
        sales_qs.values("category")
        .annotate(total_rev=Sum("revenue"), total_ord=Sum("orders"))
        .order_by("-total_rev")
    )
    if by_cat.exists():
        elements.append(Paragraph("Revenue by Category", styles["Heading2"]))
        cd = [["Category", "Revenue", "Orders"]]
        for c in by_cat:
            cd.append([c["category"] or "N/A", f"${float(c['total_rev']):,.2f}", f"{c['total_ord']:,}"])
        ct = Table(cd, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        ct.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b5cf6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(ct)

    doc.build(elements)
    pdf_content = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf_content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="claritybi_full_report_{start_date}_{end_date}.pdf"'

    if request.user.is_authenticated:
        ExportLog.objects.create(
            user=request.user,
            export_format="pdf",
            record_count=sales_qs.count(),
            file_size=len(pdf_content),
        )

    return response


@login_required
def toggle_bookmark(request):
    """POST: add or remove a bookmark."""
    if request.method == "POST":
        url = request.POST.get("url", "")
        name = request.POST.get("name", "")
        section_type = request.POST.get("section_type", "dashboard")

        existing = Bookmark.objects.filter(user=request.user, url=url).first()
        if existing:
            existing.delete()
            return JsonResponse({"status": "removed"})
        else:
            bm = Bookmark.objects.create(
                user=request.user,
                url=url,
                name=name,
                section_type=section_type,
            )
            return JsonResponse({"status": "added", "id": bm.id})
    return JsonResponse({"error": "POST required"}, status=405)


@login_required
def bookmarks_list(request):
    """HTMX partial returning user's bookmarks."""
    bookmarks = Bookmark.objects.filter(user=request.user)
    return render(request, "reports/partials/bookmarks.html", {"bookmarks": bookmarks})


@login_required
def bookmarks_dropdown(request):
    """HTMX partial for the navbar bookmarks dropdown."""
    bookmarks = Bookmark.objects.filter(user=request.user)
    return render(request, "reports/partials/bookmarks_dropdown.html", {
        "bookmarks": bookmarks,
        "page_title": request.GET.get("page_title", "Dashboard"),
    })


@login_required
@require_POST
def bookmark_add(request):
    """POST: add a bookmark and return updated dropdown."""
    url = request.POST.get("url", "")
    name = request.POST.get("name", "")
    section_type = request.POST.get("section_type", "dashboard")
    if url and name:
        Bookmark.objects.get_or_create(
            user=request.user, url=url,
            defaults={"name": name, "section_type": section_type},
        )
    bookmarks = Bookmark.objects.filter(user=request.user)
    return render(request, "reports/partials/bookmarks_dropdown.html", {"bookmarks": bookmarks})


@login_required
def bookmark_delete(request, pk):
    """DELETE: remove a bookmark and return updated dropdown."""
    if request.method == "DELETE":
        Bookmark.objects.filter(pk=pk, user=request.user).delete()
    bookmarks = Bookmark.objects.filter(user=request.user)
    return render(request, "reports/partials/bookmarks_dropdown.html", {"bookmarks": bookmarks})


@login_required
def goals_widget(request):
    """HTMX partial for dashboard goals widget (top 4 goals)."""
    goals = Goal.objects.filter(is_completed=False)[:4]
    return render(request, "reports/partials/goals_widget.html", {"goals": goals})


@login_required
def comparison_chart(request):
    """HTMX partial for period comparison chart."""
    start_date, end_date, days = _get_date_range(request)
    prev_start = start_date - timedelta(days=days)

    current_qs = (
        SalesData.objects.filter(date__gte=start_date, date__lte=end_date)
        .values("date")
        .annotate(revenue=Sum("revenue"))
        .order_by("date")
    )
    prev_qs = (
        SalesData.objects.filter(date__gte=prev_start, date__lt=start_date)
        .values("date")
        .annotate(revenue=Sum("revenue"))
        .order_by("date")
    )

    current_labels = [d["date"].strftime("%b %d") for d in current_qs]
    current_data = [float(d["revenue"]) for d in current_qs]
    previous_data = [float(d["revenue"]) for d in prev_qs]

    context = {
        "current_labels_json": json.dumps(current_labels),
        "current_data_json": json.dumps(current_data),
        "previous_data_json": json.dumps(previous_data),
        "days": days,
    }
    return render(request, "reports/partials/comparison_chart.html", context)


@login_required
def export_options(request):
    """HTMX partial for export format selector."""
    return render(request, "reports/partials/export_options.html")


@login_required
def goal_form(request):
    """HTMX partial returning the goal create/edit form."""
    return render(request, "reports/partials/goal_form.html", {
        "categories": Goal.CATEGORY_CHOICES,
    })


@login_required
@require_POST
def goal_save(request):
    """POST: create or update a goal, return updated goals grid."""
    goal_id = request.POST.get("goal_id")
    if goal_id:
        goal = get_object_or_404(Goal, pk=goal_id)
    else:
        goal = Goal()

    goal.name = request.POST.get("name", "")
    goal.description = request.POST.get("description", "")
    goal.target_value = Decimal(request.POST.get("target_value", "0"))
    goal.current_value = Decimal(request.POST.get("current_value", "0"))
    goal.unit = request.POST.get("unit", "")
    goal.category = request.POST.get("category", "revenue")
    deadline = request.POST.get("deadline")
    goal.deadline = deadline if deadline else None
    goal.save()

    goals = Goal.objects.all()
    return render(request, "reports/goals.html", {
        "goals": goals,
        "page_title": "Goals",
        "categories": Goal.CATEGORY_CHOICES,
    })


@login_required
def goal_delete(request, pk):
    """DELETE: remove a goal, return updated goals grid."""
    Goal.objects.filter(pk=pk).delete()
    goals = Goal.objects.all()
    return render(request, "reports/goals.html", {
        "goals": goals,
        "page_title": "Goals",
        "categories": Goal.CATEGORY_CHOICES,
    })


@login_required
def print_view(request):
    """Render print-optimized page with minimal chrome."""
    start_date, end_date, days = _get_date_range(request)
    sales_qs = SalesData.objects.filter(date__gte=start_date, date__lte=end_date)

    summary = sales_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
        total_profit=Sum("profit"),
        total_returns=Sum("returns"),
    )

    # Build KPI cards for print template
    prev_start = start_date - timedelta(days=days)
    prev_qs = SalesData.objects.filter(date__gte=prev_start, date__lt=start_date)
    prev_summary = prev_qs.aggregate(
        total_revenue=Sum("revenue"),
        total_orders=Sum("orders"),
        total_customers=Sum("customers"),
        avg_order=Avg("avg_order_value"),
    )
    rev_change, rev_trend = _calc_change(summary["total_revenue"], prev_summary["total_revenue"])
    ord_change, ord_trend = _calc_change(summary["total_orders"], prev_summary["total_orders"])
    cust_change, cust_trend = _calc_change(summary["total_customers"], prev_summary["total_customers"])
    aov_change, aov_trend = _calc_change(summary["avg_order"], prev_summary["avg_order"])

    kpi_cards = [
        {"name": "Revenue", "value": summary["total_revenue"] or 0, "change": rev_change, "trend": rev_trend, "format": "currency"},
        {"name": "Orders", "value": summary["total_orders"] or 0, "change": ord_change, "trend": ord_trend, "format": "number"},
        {"name": "Customers", "value": summary["total_customers"] or 0, "change": cust_change, "trend": cust_trend, "format": "number"},
        {"name": "Avg Order Value", "value": summary["avg_order"] or 0, "change": aov_change, "trend": aov_trend, "format": "currency"},
        {"name": "Profit", "value": summary["total_profit"] or 0, "change": 0, "trend": "flat", "format": "currency"},
        {"name": "Returns", "value": summary["total_returns"] or 0, "change": 0, "trend": "flat", "format": "number"},
    ]

    region_summary = (
        sales_qs.values("region")
        .annotate(total_revenue=Sum("revenue"), total_orders=Sum("orders"), total_customers=Sum("customers"))
        .order_by("-total_revenue")
    )

    goals = Goal.objects.all()

    context = {
        "summary": summary,
        "kpi_cards": kpi_cards,
        "region_summary": region_summary,
        "goals": goals,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "today": timezone.now(),
        "page_title": "ClarityBI Report - Print",
    }
    return render(request, "reports/print.html", context)
