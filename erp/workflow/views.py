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

from . import approvals, services, templates, triggers
from .engine import engine
from .models import ApprovalStatus, Workflow, WorkflowInstance
from .serializers import (
    DecisionSerializer,
    InstanceDetailSerializer,
    InstanceSerializer,
    StartInstanceSerializer,
    TemplateCreateSerializer,
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


class TemplateCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(templates.TEMPLATE_CATALOG)


class TemplateCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, template_id: str) -> Response:
        s = TemplateCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        graph = templates.expand(template_id, s.validated_data["params"])
        wf = services.save_graph(
            name=s.validated_data["name"], nodes=graph["nodes"], edges=graph["edges"],
        )
        if graph["trigger"]:
            triggers.create_trigger(
                workflow_id=wf.id,
                event_name=graph["trigger"]["event_name"],
                condition=graph["trigger"].get("condition"),
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
    """Approve/reject a waiting (approval) instance; re-enters the engine at that node.

    Routes through the RBAC-checked ``approvals.decide`` when the instance has a pending
    ``ApprovalRequest`` (true for every approval wait since FILE_09); falls back to a bare
    ``engine.resume`` only for the case of no request row at all (shouldn't happen going forward,
    kept so a pre-existing waiting instance from before this migration isn't stranded).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, instance_id) -> Response:
        get_object_or_404(WorkflowInstance, id=instance_id)
        s = DecisionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        pending = (
            WorkflowInstance.objects.get(id=instance_id)
            .approval_requests.filter(status=ApprovalStatus.PENDING)
            .order_by("-created_at")
            .first()
        )
        if pending is not None:
            approvals.decide(
                actor=request.user,
                request_id=pending.id,
                decision=s.validated_data["decision"],
                comment=s.validated_data.get("comment", ""),
            )
            instance = WorkflowInstance.objects.select_related("workflow", "current_node").get(
                id=instance_id
            )
        else:
            instance = engine.resume(instance_id, decision=s.validated_data["decision"])
        return _envelope(InstanceDetailSerializer(instance).data)


class AssistantActionCatalogView(APIView):
    """The actions an ``assistant_action`` node may be pointed at — for the canvas picker.

    Deliberately NOT filtered by the reader's own roles: the graph author picks what the step
    does, and the step runs later as whoever *triggers* the run, with that person's permissions
    checked at that moment (see the executor). Filtering here by the author's roles would hide
    steps a valid trigger could perform. The panel says which permission each step needs instead.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from erp.assistant.services.actions import ACTIONS

        return _envelope([
            {"name": a.name, "description": a.description, "kind": a.kind, "risk": a.risk,
             "args": list(a.args.keys())}
            for a in sorted(ACTIONS.values(), key=lambda a: a.name)
        ])


class DashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(services.dashboard_metrics())
