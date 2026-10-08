from django.urls import path
from rest_framework.routers import DefaultRouter

from .category_views import CategoryViewSet
from .dashboard_views import DashboardSummaryView
from .views import TicketViewSet

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard_summary"),
    *router.urls,
]
