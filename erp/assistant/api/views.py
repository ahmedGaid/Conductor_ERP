"""Assistant API — document extraction (part 1).

RBAC: extraction proposes a draft purchase document, so it requires the same role as creating
one (Branch Manager). When the assistant is disabled the endpoint 404s — indistinguishable from
absent, the same posture as out-of-scope records — and the UI hides all AI surfaces via /status.
"""
from __future__ import annotations

from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import ValidationError
from erp.core.import_api import MAX_UPLOAD_BYTES
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from .. import client, services
from ..services.extraction import ALLOWED_TYPES

_CanBuy = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class AssistantStatusView(APIView):
    """Feature discovery for the web client: hide every AI surface when disabled."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope({"enabled": client.enabled()})


class ExtractDocumentView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError("No file was uploaded.")
        # Hard ceiling checked BEFORE reading the file into memory (Session-00 posture).
        if upload.size and upload.size > MAX_UPLOAD_BYTES:
            raise ValidationError(
                "File is too large.",
                data={"max_bytes": MAX_UPLOAD_BYTES, "size": upload.size},
            )
        media_type = (upload.content_type or "").lower()
        if media_type not in ALLOWED_TYPES:
            raise ValidationError(
                "Unsupported file type.",
                data={"content_type": media_type, "allowed": sorted(ALLOWED_TYPES)},
            )
        proposal = services.extract_document(
            data=upload.read(), media_type=media_type, filename=upload.name,
            actor=request.user,
        )
        return _envelope(proposal)
