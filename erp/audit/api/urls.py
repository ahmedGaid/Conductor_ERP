"""Audit API routes."""
from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    path("timeline/", views.RecordTimelineView.as_view(), name="record-timeline"),
]
