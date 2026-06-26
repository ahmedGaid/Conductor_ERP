"""First-run setup routes."""
from django.urls import path

from . import views

app_name = "setup"

urlpatterns = [
    path("status", views.SetupStatusView.as_view(), name="status"),
    path("complete", views.SetupCompleteView.as_view(), name="complete"),
]
