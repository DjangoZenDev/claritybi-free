"""API URL configuration for ClarityBI reports."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import api

router = DefaultRouter()
router.register(r"dashboards", api.DashboardViewSet)
router.register(r"kpis", api.KPIViewSet)
router.register(r"sales", api.SalesDataViewSet)
router.register(r"goals", api.GoalViewSet)
router.register(r"insights", api.InsightViewSet)
router.register(r"saved-reports", api.SavedReportViewSet, basename="savedreport")
router.register(r"bookmarks", api.BookmarkViewSet, basename="bookmark")

urlpatterns = [
    path("", include(router.urls)),
]
