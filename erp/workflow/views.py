"""Workflow API views — thin: validate, delegate to services/engine, return an envelope.

Responses use the same ``{"data": ...}`` envelope as the identity API. Errors flow through the
core DRF exception handler (``{"error": {...}}``).
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .engine import engine
from .models import Workflow, WorkflowInstance
from .serializers import (
    DecisionSerializer,
    InstanceDetailSerializer,
    InstanceSerializer,
    StartInstanceSerializer,
    WorkflowGraphSerializer,
    WorkflowListItemSerializer,
)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class WorkflowListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        rows = services.list_workflows()
        return _envelope(WorkflowListItemSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        s = WorkflowGraphSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        wf = services.save_graph(
            name=s.validated_data["name"],
            status=s.validated_data.get("status", "active"),
            nodes=s.validated_data["nodes"],
            edges=s.validated_data["edges"],
        )
        return _envelope(WorkflowGraphSerializer(wf).data, status=201)


class WorkflowDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, workflow_id) -> Response:
        wf = get_object_or_404(Workflow, id=workflow_id)
        return _envelope(WorkflowGraphSerializer(wf).data)

    def put(self, request: Request, workflow_id) -> Response:
        get_object_or_404(Workflow, id=workflow_id)
        s = WorkflowGraphSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        wf = services.save_graph(
            workflow_id=workflow_id,
            name=s.validated_data["name"],
            status=s.validated_data.get("status", "active"),
            nodes=s.validated_data["nodes"],
            edges=s.validated_data["edges"],
        )
        return _envelope(WorkflowGraphSerializer(wf).data)


class WorkflowStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, workflow_id) -> Response:
        wf = get_object_or_404(Workflow, id=workflow_id)
        s = StartInstanceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        instance = engine.start_instance(wf, s.validated_data.get("payload", {}), user=request.user)
        return _envelope(InstanceDetailSerializer(instance).data, status=201)


class InstanceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = WorkflowInstance.objects.select_related("workflow", "current_node").order_by(
            "-created_at"
        )
        workflow_id = request.query_params.get("workflow")
        if workflow_id:
            qs = qs.filter(workflow_id=workflow_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return _envelope(InstanceSerializer(qs[:200], many=True).data)


class InstanceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, instance_id) -> Response:
        instance = get_object_or_404(
            WorkflowInstance.objects.select_related("workflow", "current_node"), id=instance_id
        )
        return _envelope(InstanceDetailSerializer(instance).data)


class InstanceDecisionView(APIView):
    """Approve/reject a waiting (approval) instance; re-enters the engine at that node."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, instance_id) -> Response:
        get_object_or_404(WorkflowInstance, id=instance_id)
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        instance = engine.resume(instance_id, decision=s.validated_data["decision"])
        return _envelope(InstanceDetailSerializer(instance).data)


class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(services.dashboard_metrics())
