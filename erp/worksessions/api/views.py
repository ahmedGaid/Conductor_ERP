"""WorkSession API — the signed-in user's private drafts. IsAuthenticated + owner-scoped."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import NotFoundError
from erp.core.errors import PermissionError as ForbiddenError

from .. import services
from ..models import WorkSession
from .serializers import serialize_session


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _get_owned_session(actor, pk) -> WorkSession:
    try:
        session = WorkSession.objects.get(pk=pk)
    except WorkSession.DoesNotExist:
        raise NotFoundError("Draft not found.")
    if session.owner_id != actor.id:
        raise ForbiddenError("You do not have access to this draft.")
    return session


class DraftListCreateView(APIView):
    """GET — the user's active drafts (the drafts surface). POST — upsert the current form's draft."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope([serialize_session(s) for s in services.list_active(request.user)])

    def post(self, request: Request) -> Response:
        d = request.data
        result = services.upsert_draft(
            request.user,
            workflow_key=d["workflow_key"],
            payload=d.get("payload", {}),
            entity_type=d.get("entity_type", ""),
            related_entity_id=d.get("related_entity_id", ""),
            schema_version=int(d.get("schema_version", 1)),
            client_version=int(d.get("client_version", 0)),
            expected_version=(int(d["expected_version"]) if d.get("expected_version") is not None else None),
        )
        return _envelope(
            {"session": serialize_session(result.session), "conflict": result.conflict},
            status=201,
        )


class ActiveDraftView(APIView):
    """GET the single active draft for one form (or null)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        workflow_key = request.query_params.get("workflow_key", "")
        related_entity_id = request.query_params.get("related_entity_id", "")
        session = services.get_active(request.user, workflow_key, related_entity_id)
        return _envelope(serialize_session(session) if session else None)


class DiscardDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk) -> Response:
        session = _get_owned_session(request.user, pk)
        services.discard(request.user, session.id)
        return _envelope(None, status=204)


class CompleteDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk) -> Response:
        session = _get_owned_session(request.user, pk)
        services.complete(
            request.user, session.id,
            related_entity_id=request.data.get("related_entity_id", ""),
        )
        session.refresh_from_db()
        return _envelope(serialize_session(session))
