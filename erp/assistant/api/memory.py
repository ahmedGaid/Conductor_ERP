"""Memory API (ai-reliability T4.4): what the assistant remembers, and the controls to change it.

Every queryset here is actor-scoped inside ``services.memory`` — the view never filters by hand, so
there is one place where "whose memory is this" is decided (and one place the leakage suite has to
prove). Personal rows are own-only; organization rows need System Admin to change, though any
signed-in user may SEE them (they describe the workspace they work in, and hiding them would make
the assistant's behaviour unexplainable).
"""
from __future__ import annotations

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import Http404

from erp.core.errors import ValidationError

from ..services import memory as memory_service
from ..services import suggestions


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _scope(raw) -> str:
    scope = (raw or memory_service.SCOPE_USER).strip()
    if scope not in memory_service.SCOPES:
        raise ValidationError("Memory is either personal or organization-wide.")
    return scope


class MemoryView(APIView):
    """Everything this actor may see, plus today's pattern proposal (T4.3) if there is one."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        listing = memory_service.list_for_actor(request.user)
        proposal = suggestions.build_memory_proposal(request.user)
        return _envelope({
            **listing,
            "slots": memory_service.slots_for(request.user),
            "slot_keys": sorted(memory_service.SLOT_KEYS),
            "proposal": proposal,
        })

    def put(self, request: Request) -> Response:
        """Set one slot from the Memory page (``source="settings"``) — the third and last
        whitelisted write path."""
        scope = _scope(request.data.get("scope"))
        try:
            row = memory_service.remember(
                request.user, scope=scope, kind="slot",
                key=(request.data.get("key") or "").strip(),
                value=request.data.get("value") or "", source="settings",
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return _envelope({"id": row.id, "key": row.key, "value": row.value}, status=201)


class MemoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, pk: int) -> Response:
        scope = _scope(request.query_params.get("scope"))
        try:
            memory_service.forget(request.user, pk, scope=scope)
        except memory_service.MemoryNotFound as exc:
            raise Http404 from exc
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=204)


class MemoryProposalView(APIView):
    """Confirm or dismiss the pattern-derived proposal. Confirming writes with
    ``source="pattern"``; dismissing suppresses that slot for 90 days."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        decision = (request.data.get("decision") or "").strip()
        if decision not in ("confirm", "dismiss"):
            raise ValidationError("Choose confirm or dismiss.")
        slot = (request.data.get("slot") or "").strip()
        if decision == "dismiss":
            memory_service.suppress_proposal(request.user, slot)
            return _envelope({"status": "dismissed"})
        row = memory_service.remember(
            request.user, scope=memory_service.SCOPE_USER, kind="slot", key=slot,
            value=request.data.get("value") or "", source="pattern",
        )
        return _envelope({"status": "confirmed", "id": row.id, "key": row.key, "value": row.value})
