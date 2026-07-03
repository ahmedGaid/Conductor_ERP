"""Assistant API — document extraction (part 1).

RBAC: extraction proposes a draft purchase document, so it requires the same role as creating
one (Branch Manager). When the assistant is disabled the endpoint 404s — indistinguishable from
absent, the same posture as out-of-scope records — and the UI hides all AI surfaces via /status.
"""
from __future__ import annotations

import json
import logging

from django.db.models import Q
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import AppError, ValidationError
from erp.core.import_api import MAX_UPLOAD_BYTES
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from .. import client, services
from ..errors import AssistantUnavailableError
from ..models import Conversation
from ..services.ask import MAX_QUESTION_CHARS
from ..services.extraction import ALLOWED_TYPES

logger = logging.getLogger(__name__)

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


class AskView(APIView):
    """Natural-language questions over the caller's scoped data.

    Only ``IsAuthenticated`` — the answer is built from tools that filter to the user's own scope,
    so a Salesperson gets their branch's numbers and nothing more (no extra role needed to *ask*).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        question = (request.data.get("question") or "").strip()
        if not question:
            raise ValidationError("Ask a question first.")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValidationError(
                "That question is too long.",
                data={"max_chars": MAX_QUESTION_CHARS, "length": len(question)},
            )
        conversation = None
        conversation_id = request.data.get("conversation_id")
        if conversation_id is not None:
            # Owned by the caller, else indistinguishable from absent (404, not 403).
            conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
        page = request.data.get("context") or None
        return _envelope(services.answer_question(
            question=question, actor=request.user, conversation=conversation, page=page,
        ))


def _sse(event: dict) -> str:
    """One SSE frame: a single ``data:`` line carrying the event as JSON, blank-line terminated."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class ChatView(APIView):
    """Streaming chat over the caller's scoped data (SSE). Same auth posture as ``AskView`` — the
    answer is built from scope-filtered tools, so no extra role is needed to ask.

    Body: ``{"conversation_id": int, "message": str}``. Emits ``token`` / ``citations`` / ``done``
    events; on failure a single blame-free ``error`` event (never a stack trace). A client
    disconnect aborts quietly and keeps whatever prose was already produced (see ``stream_answer``).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        if not client.enabled():
            raise Http404
        message = (request.data.get("message") or "").strip()
        if not message:
            raise ValidationError("Ask a question first.")
        if len(message) > MAX_QUESTION_CHARS:
            raise ValidationError(
                "That question is too long.",
                data={"max_chars": MAX_QUESTION_CHARS, "length": len(message)},
            )
        # Resolve (and own-check) the conversation BEFORE streaming, so a bad id is a plain 404 with
        # no half-open stream. ``conversation_id`` absent ⇒ pk=None ⇒ 404, same as an unknown id.
        conversation = get_object_or_404(
            Conversation, pk=request.data.get("conversation_id"), user=request.user,
        )
        page = request.data.get("context") or None

        def _events():
            try:
                for event in services.stream_answer(
                    question=message, actor=request.user, conversation=conversation, page=page,
                ):
                    yield _sse(event)
            except (BrokenPipeError, ConnectionResetError, GeneratorExit):
                raise  # client cancelled — partial text already persisted; exit quietly
            except AppError as exc:
                yield _sse({"type": "error", "message": exc.message})
            except Exception:  # pragma: no cover - unexpected; never leak a trace to the client
                logger.exception("assistant chat stream failed")
                yield _sse({"type": "error", "message": AssistantUnavailableError.message})

        response = StreamingHttpResponse(_events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


def _first_line(conversation: Conversation) -> str:
    first = conversation.messages.first()
    return (first.content.splitlines()[0][:100] if first and first.content else "")


def _summary(conversation: Conversation) -> dict:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "pinned": conversation.pinned,
        "archived": conversation.archived,
        "updated_at": conversation.updated_at.isoformat(),
        "preview": _first_line(conversation),
    }


def _detail(conversation: Conversation) -> dict:
    return {
        **_summary(conversation),
        "created_at": conversation.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "meta": m.meta,
                "created_at": m.created_at.isoformat(),
            }
            for m in conversation.messages.all()
        ],
    }


class ConversationsView(APIView):
    """List / create the caller's own conversations. Private per owner."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Conversation.objects.filter(user=request.user)
        if request.query_params.get("archived") == "1":
            qs = qs.filter(archived=True)
        else:
            qs = qs.filter(archived=False)
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(messages__content__icontains=q)
            ).distinct()
        return _envelope([_summary(c) for c in qs])

    def post(self, request: Request) -> Response:
        conversation = Conversation.objects.create(
            user=request.user, title=(request.data.get("title") or "").strip()[:200],
        )
        return _envelope(_detail(conversation), status=201)


class ConversationDetailView(APIView):
    """Read / patch (title, pinned, archived) / delete one owned conversation."""

    permission_classes = [IsAuthenticated]

    def _get(self, request: Request, pk: int) -> Conversation:
        return get_object_or_404(Conversation, pk=pk, user=request.user)

    def get(self, request: Request, pk: int) -> Response:
        return _envelope(_detail(self._get(request, pk)))

    def patch(self, request: Request, pk: int) -> Response:
        conversation = self._get(request, pk)
        fields: list[str] = []
        if "title" in request.data:
            conversation.title = (request.data.get("title") or "").strip()[:200]
            fields.append("title")
        for flag in ("pinned", "archived"):
            if flag in request.data:
                setattr(conversation, flag, bool(request.data.get(flag)))
                fields.append(flag)
        if fields:
            conversation.save(update_fields=[*fields, "updated_at"])
        return _envelope(_detail(conversation))

    def delete(self, request: Request, pk: int) -> Response:
        self._get(request, pk).delete()
        return Response(status=204)
