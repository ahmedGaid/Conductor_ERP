"""CRM API views — thin: validate, delegate to services, return {data}.

RBAC: CRM operations require a Branch Manager (System Admin / superuser bypass).
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from .. import services
from ..domain.models import Activity, Lead, Opportunity, Ticket
from .serializers import (
    ActivityCreateSerializer,
    ActivitySerializer,
    LeadConvertSerializer,
    LeadCreateSerializer,
    LeadSerializer,
    LeadStatusSerializer,
    OppCreateSerializer,
    OppLoseSerializer,
    OppStageSerializer,
    OppWinSerializer,
    OpportunitySerializer,
    TicketCreateSerializer,
    TicketResolveSerializer,
    TicketSerializer,
)

_CanCRM = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _opp_qs():
    return Opportunity.objects.select_related("lead").prefetch_related("lines")


# --- Leads -----------------------------------------------------------------

class LeadListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def get(self, request: Request) -> Response:
        qs = Lead.objects.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return _envelope(LeadSerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = LeadCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        lead = services.create_lead(actor=request.user, **s.validated_data)
        return _envelope(LeadSerializer(lead).data, status=201)


class LeadStatusView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, lead_id) -> Response:
        lead = get_object_or_404(Lead, id=lead_id)
        s = LeadStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.set_lead_status(lead, s.validated_data["status"], actor=request.user)
        return _envelope(LeadSerializer(Lead.objects.get(id=lead.id)).data)


class LeadConvertView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, lead_id) -> Response:
        lead = get_object_or_404(Lead, id=lead_id)
        s = LeadConvertSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        opp = services.convert_lead(lead, actor=request.user, **s.validated_data)
        return _envelope(OpportunitySerializer(_opp_qs().get(id=opp.id)).data, status=201)


# --- Opportunities ---------------------------------------------------------

class OppListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def get(self, request: Request) -> Response:
        qs = _opp_qs().order_by("-created_at")
        if request.query_params.get("stage"):
            qs = qs.filter(stage=request.query_params["stage"])
        return _envelope(OpportunitySerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = OppCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        opp = services.create_opportunity(
            name=v["name"], customer_code=v.get("customer_code", ""),
            warehouse_code=v.get("warehouse_code", ""), currency=v.get("currency", "EGP"),
            probability=v.get("probability", 10), expected_close=v.get("expected_close"),
            notes=v.get("notes", ""),
            lines=[
                services.OppLineInput(
                    item_sku=ln["item_sku"], quantity=ln["quantity"],
                    unit_price_minor=ln["unit_price"], description=ln.get("description", ""),
                )
                for ln in v.get("lines", [])
            ],
            actor=request.user,
        )
        return _envelope(OpportunitySerializer(_opp_qs().get(id=opp.id)).data, status=201)


class OppDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def get(self, request: Request, opp_id) -> Response:
        return _envelope(OpportunitySerializer(get_object_or_404(_opp_qs(), id=opp_id)).data)


class OppStageView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, opp_id) -> Response:
        opp = get_object_or_404(Opportunity, id=opp_id)
        s = OppStageSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.advance_stage(opp, s.validated_data["stage"], actor=request.user)
        return _envelope(OpportunitySerializer(_opp_qs().get(id=opp.id)).data)


class OppWinView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, opp_id) -> Response:
        opp = get_object_or_404(Opportunity, id=opp_id)
        s = OppWinSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.win_opportunity(
            opp, create_sales_order=s.validated_data["create_sales_order"], actor=request.user
        )
        return _envelope(OpportunitySerializer(_opp_qs().get(id=opp.id)).data)


class OppLoseView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, opp_id) -> Response:
        opp = get_object_or_404(Opportunity, id=opp_id)
        s = OppLoseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.lose_opportunity(opp, reason=s.validated_data["reason"], actor=request.user)
        return _envelope(OpportunitySerializer(_opp_qs().get(id=opp.id)).data)


# --- Activities ------------------------------------------------------------

class ActivityListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def get(self, request: Request) -> Response:
        qs = Activity.objects.all()
        if request.query_params.get("related_type"):
            qs = qs.filter(related_type=request.query_params["related_type"])
        if request.query_params.get("related_ref"):
            qs = qs.filter(related_ref=request.query_params["related_ref"])
        return _envelope(ActivitySerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = ActivityCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        activity = services.log_activity(actor=request.user, **s.validated_data)
        return _envelope(ActivitySerializer(activity).data, status=201)


class ActivityCompleteView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, activity_id) -> Response:
        activity = get_object_or_404(Activity, id=activity_id)
        services.complete_activity(activity, actor=request.user)
        return _envelope(ActivitySerializer(Activity.objects.get(id=activity.id)).data)


# --- Tickets ---------------------------------------------------------------

class TicketListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def get(self, request: Request) -> Response:
        qs = Ticket.objects.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        if request.query_params.get("priority"):
            qs = qs.filter(priority=request.query_params["priority"])
        return _envelope(TicketSerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = TicketCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ticket = services.create_ticket(actor=request.user, **s.validated_data)
        return _envelope(TicketSerializer(ticket).data, status=201)


class TicketDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def get(self, request: Request, ticket_id) -> Response:
        return _envelope(TicketSerializer(get_object_or_404(Ticket, id=ticket_id)).data)


class TicketStartView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, ticket_id) -> Response:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        services.start_ticket(ticket, actor=request.user)
        return _envelope(TicketSerializer(Ticket.objects.get(id=ticket.id)).data)


class TicketResolveView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, ticket_id) -> Response:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        s = TicketResolveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.resolve_ticket(ticket, resolution=s.validated_data["resolution"], actor=request.user)
        return _envelope(TicketSerializer(Ticket.objects.get(id=ticket.id)).data)


class TicketCloseView(APIView):
    permission_classes = [IsAuthenticated, _CanCRM]

    def post(self, request: Request, ticket_id) -> Response:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        services.close_ticket(ticket, actor=request.user)
        return _envelope(TicketSerializer(Ticket.objects.get(id=ticket.id)).data)
