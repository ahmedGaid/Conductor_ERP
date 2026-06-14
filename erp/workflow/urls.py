"""Workflow API routes."""
from django.urls import path

from . import views

app_name = "workflow"

urlpatterns = [
    path("dashboard/metrics", views.DashboardMetricsView.as_view(), name="dashboard-metrics"),
    path("workflows", views.WorkflowListCreateView.as_view(), name="workflow-list"),
    path("workflows/<uuid:workflow_id>", views.WorkflowDetailView.as_view(), name="workflow-detail"),
    path("workflows/<uuid:workflow_id>/start", views.WorkflowStartView.as_view(), name="workflow-start"),
    path("instances", views.InstanceListView.as_view(), name="instance-list"),
    path("instances/<uuid:instance_id>", views.InstanceDetailView.as_view(), name="instance-detail"),
    path("instances/<uuid:instance_id>/decision", views.InstanceDecisionView.as_view(), name="instance-decision"),
]
