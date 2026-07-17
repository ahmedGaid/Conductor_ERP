"""Audit API routes."""
from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    path("history", views.RecordHistoryView.as_view(), name="record-history"),
    path("timeline/", views.RecordTimelineView.as_view(), name="record-timeline"),
]
