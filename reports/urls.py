"""URL patterns for ClarityBI reports."""

from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.bi_dashboard, name="dashboard"),
    path("dashboards/", views.dashboard_list, name="dashboard_list"),
    path("dashboards/<slug:slug>/", views.dashboard_detail, name="dashboard_detail"),
    path("export/", views.export_report, name="export_report"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("print/", views.print_view, name="print_view"),
    path("htmx/kpi/", views.kpi_overview, name="kpi_overview"),
    path("htmx/revenue-chart/", views.revenue_chart, name="revenue_chart"),
    path("htmx/category-charts/", views.category_charts, name="category_charts"),
    path("htmx/sales-table/", views.sales_table, name="sales_table"),
    path("htmx/widget/<int:widget_id>/", views.widget_content, name="widget_content"),
    path("htmx/top-customers/", views.top_customers, name="top_customers"),
    path("htmx/recent-orders/", views.recent_orders, name="recent_orders"),
    path("htmx/insights/", views.insights_partial, name="insights_partial"),
    path("htmx/goals-widget/", views.goals_widget, name="goals_widget"),
    path("htmx/comparison-chart/", views.comparison_chart, name="comparison_chart"),
    path("htmx/bookmarks-dropdown/", views.bookmarks_dropdown, name="bookmarks_dropdown"),
    path("htmx/export-options/", views.export_options, name="export_options"),
    path("htmx/goal-form/", views.goal_form, name="goal_form"),
    path("htmx/report-preview/", views.report_preview, name="report_preview"),
    path("insights/generate/", views.generate_insights, name="generate_insights"),
    path("goals/", views.goals_page, name="goals_page"),
    path("goals/save/", views.goal_save, name="goal_save"),
    path("goals/<int:pk>/delete/", views.goal_delete, name="goal_delete"),
    path("time-comparison/", views.time_comparison, name="time_comparison"),
    path("report-builder/", views.report_builder, name="report_builder"),
    path("reports/save/", views.save_report, name="save_report"),
    path("reports/<int:pk>/", views.load_report, name="load_report"),
    path("reports/<int:pk>/delete/", views.delete_report, name="delete_report"),
    path("bookmarks/add/", views.bookmark_add, name="bookmark_add"),
    path("bookmarks/<int:pk>/delete/", views.bookmark_delete, name="bookmark_delete"),
]
