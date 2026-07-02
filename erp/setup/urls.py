"""First-run setup routes."""
from django.urls import path

from . import views

app_name = "setup"

urlpatterns = [
    path("status", views.SetupStatusView.as_view(), name="status"),
    path("chart-of-accounts", views.SetupChartOfAccountsView.as_view(), name="chart-of-accounts"),
    path("tax", views.SetupTaxView.as_view(), name="tax"),
    path("users", views.SetupInviteUserView.as_view(), name="users"),
    path("complete", views.SetupCompleteView.as_view(), name="complete"),
]
