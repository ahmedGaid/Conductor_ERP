"""Assistant API — document extraction (part 1).

RBAC: extraction proposes a draft purchase document, so it requires the same role as creating
one (Branch Manager). When the assistant is disabled the endpoint 404s — indistinguishable from
absent, the same posture as out-of-scope records — and the UI hides all AI surfaces via /status.
"""
from __future__ import annotations

import dataclasses
import json
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.http import Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.audit import services as audit
from erp.core.errors import AppError, ValidationError
from erp.core.import_api import MAX_UPLOAD_BYTES
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER, SYSTEM_ADMIN

from .. import client, services
from ..errors import (
    ActionAlreadyHandledError,
    ActionFailedError,
    ActionForbiddenError,
    AssistantUnavailableError,
    VerifierFailed,
)
from ..gateway import status as gateway_status
from ..models import Attachment, Conversation, KnowledgeDocument, Message
from ..services import actions, files, imports, knowledge
from ..services.ask import MAX_QUESTION_CHARS
from ..services.extraction import ALLOWED_TYPES
from ..services.simulation import PlanStep, simulate
from ..verifier import run as verify_run

# Cross-card idempotency window (FILE_03 T3.1): a confirm that repeats another confirmed proposal's
# natural key within this window is deduplicated — nothing executes twice.
DEDUPE_WINDOW = timedelta(minutes=10)

logger = logging.getLogger(__name__)

_CanBuy = HasAnyRole.require(BRANCH_MANAGER)
# Managing the shared knowledge base is an admin task (the docs are company-wide, not per-user).
_CanManageKnowledge = HasAnyRole.require(SYSTEM_ADMIN)

# Text uploads the knowledge base accepts on top of the vision ALLOWED_TYPES (images + PDF).
KNOWLEDGE_TEXT_TYPES = {
    "text/plain", "text/markdown", "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _doc_row(d: KnowledgeDocument) -> dict:
    return {
        "id": d.id,
        "title": d.title,
        "filename": d.filename,
        "status": d.status,
        "error_text": d.error_text,
        "chunk_count": d.chunk_count,
        "size": d.size,
        "updated_at": d.updated_at.isoformat(),
    }


class AssistantStatusView(APIView):
    """Feature discovery for the web client: hide every AI surface when disabled."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        enabled = client.enabled()
        # Mode only means something once the feature is on — an unconfigured deployment
        # is neither degraded nor down, it's simply off (the panel never renders either way).
        mode = gateway_status.mode() if enabled else "full"
        return _envelope({"enabled": enabled, "mode": mode})


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


class KnowledgeView(APIView):
    """List (GET) and upload (POST) knowledge-base documents. Admin-only — the base is shared."""

    permission_classes = [IsAuthenticated, _CanManageKnowledge]

    def get(self, request: Request) -> Response:
        docs = KnowledgeDocument.objects.all()[:200]
        return _envelope([_doc_row(d) for d in docs])

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
        allowed = ALLOWED_TYPES | KNOWLEDGE_TEXT_TYPES
        if media_type not in allowed:
            raise ValidationError(
                "Unsupported file type.",
                data={"content_type": media_type, "allowed": sorted(allowed)},
            )
        doc = knowledge.ingest_document(
            data=upload.read(), media_type=media_type, filename=upload.name,
            title=(request.data.get("title") or upload.name)[:200], actor=request.user,
        )
        return _envelope(_doc_row(doc), status=201)


class KnowledgeDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanManageKnowledge]

    def delete(self, request: Request, pk: int) -> Response:
        knowledge.delete_document(pk, actor=request.user)
        return Response(status=204)


class AttachmentsView(APIView):
    """Upload a file to attach to a chat turn. Stored unclaimed; the next send claims it.

    Only ``IsAuthenticated`` — attachments are private to their uploader and are only ever read back
    into that user's own conversation. Same size/allowlist posture as document extraction.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError("No file was uploaded.")
        if upload.size and upload.size > MAX_UPLOAD_BYTES:
            raise ValidationError(
                "File is too large.",
                data={"max_bytes": MAX_UPLOAD_BYTES, "size": upload.size},
            )
        media_type = (upload.content_type or "").lower()
        if media_type not in files.ALLOWED_ATTACHMENT_TYPES:
            raise ValidationError(
                "Unsupported file type.",
                data={"content_type": media_type,
                      "allowed": sorted(files.ALLOWED_ATTACHMENT_TYPES)},
            )
        attachment = Attachment.objects.create(
            user=request.user, file=upload, name=(upload.name or "file")[:255],
            content_type=media_type, size=upload.size or 0,
        )
        return _envelope(
            {"id": attachment.id, "name": attachment.name,
             "content_type": attachment.content_type, "size": attachment.size},
            status=201,
        )


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

    Body: ``{"conversation_id": int, "message": str}``. Runs the agentic loop (``services.run_agent``)
    and emits ``step`` (per tool call) / ``token`` / ``citations`` / ``done`` events; on failure a
    single blame-free ``error`` event (never a stack trace). A client disconnect aborts quietly and
    keeps whatever prose was already produced.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        if not client.enabled():
            raise Http404
        regenerate = bool(request.data.get("regenerate"))
        message = (request.data.get("message") or "").strip()
        if not message and not regenerate:
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
        # Regenerate re-answers the existing last question — there must be one to re-answer.
        if regenerate and not conversation.messages.filter(role="user").exists():
            raise ValidationError("Nothing to regenerate yet.")
        page = request.data.get("context") or None
        # Validate any attachment references BEFORE the stream opens, so a bad id is a clean 404
        # (not a mid-stream error). The real claim — linking each to the new user message — happens
        # inside stream_answer once that message exists.
        attachment_ids = request.data.get("attachment_ids") or []
        if attachment_ids and not regenerate:
            files.fetch_unclaimed(attachment_ids, user=request.user)

        def _events():
            try:
                for event in services.run_agent(
                    question=message, actor=request.user, conversation=conversation,
                    page=page, regenerate=regenerate, attachment_ids=attachment_ids,
                ):
                    yield _sse(event)
            except (BrokenPipeError, ConnectionResetError, GeneratorExit):
                raise  # client cancelled — partial text already persisted; exit quietly
            except AppError as exc:
                yield _sse({"type": "error", "message": exc.message, "code": exc.code})
            except Exception:  # pragma: no cover - unexpected; never leak a trace to the client
                logger.exception("assistant chat stream failed")
                yield _sse({"type": "error", "message": AssistantUnavailableError.message})

        response = StreamingHttpResponse(_events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ActionExecuteView(APIView):
    """Confirm or dismiss a write proposal the agent prepared (plan session 10).

    Body: ``{"message_id": int, "decision": "confirm" | "dismiss"}``. The proposal lives in the
    assistant message's ``meta`` (own-checked via the conversation owner). Confirm runs the module
    contract **as the caller** and stamps the proposal consumed — single-use, so a second confirm
    409s. Nothing here bypasses module RBAC: a role that can't create the document is refused.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        decision = (request.data.get("decision") or "").strip()
        if decision not in ("confirm", "dismiss"):
            raise ValidationError("Choose confirm or dismiss.")
        # Own-check through the conversation: a foreign message is indistinguishable from absent.
        message = get_object_or_404(
            Message, pk=request.data.get("message_id"),
            conversation__user=request.user, role=Message.Role.ASSISTANT,
        )
        meta = message.meta or {}
        proposal = meta.get("proposal")
        if not proposal:
            raise Http404
        if proposal.get("status") != "pending":
            # Already confirmed/dismissed — single-use, never runs twice.
            raise ActionAlreadyHandledError

        name = proposal.get("action")
        if decision == "dismiss":
            proposal["status"] = "dismissed"
            message.save(update_fields=["meta"])
            audit.record(module="assistant", action="dismiss_action", entity_type="Action",
                         entity_id=name, actor=request.user)
            return _envelope({"status": "dismissed"})

        payload = proposal.get("payload") or {}
        key = actions.idempotency_key(name, payload)

        # Cross-card dedupe (FILE_03 T3.1): a same-key proposal this user confirmed recently — the
        # single-use guard above only stops replays of THIS card; this stops a second card (double
        # propose, agent retry) from re-executing the same write.
        cutoff = timezone.now() - DEDUPE_WINDOW
        prior = (
            Message.objects.filter(conversation__user=request.user, role=Message.Role.ASSISTANT,
                                    created_at__gte=cutoff)
            .exclude(pk=message.pk).order_by("-created_at")
        )
        for other in prior:
            other_proposal = (other.meta or {}).get("proposal")
            if (other_proposal and other_proposal.get("status") == "confirmed"
                    and other_proposal.get("idempotency_key") == key):
                result = other_proposal.get("result") or {}
                proposal["status"] = "confirmed"
                proposal["result"] = result
                proposal["idempotency_key"] = key
                message.save(update_fields=["meta"])
                audit.record(module="assistant", action="confirm_deduplicated", entity_type="Action",
                             entity_id=name, actor=request.user)
                return _envelope({"status": "confirmed", "followups": [], "deduplicated": True,
                                  **result})

        action = actions.ACTIONS.get(name)
        report = None
        try:
            with transaction.atomic():
                result = actions.execute(request.user, name, payload)
                if action is not None and action.invariants:
                    scope = {"links": result.get("links") or [], "payload": payload,
                             "actor": request.user}
                    report = verify_run(action.invariants, scope)
                    if not report.ok:
                        # Rollback-as-compensation (FILE_03): every current action is draft risk, so
                        # unwinding this atomic block fully undoes the write. `compensation` stays
                        # declared-but-unused until a post-risk action ships (Phase B).
                        raise VerifierFailed(
                            data={"findings": [dataclasses.asdict(f) for f in report.findings]})
        except PermissionError:
            # The role lost create rights since the card was shown — calm refusal, proposal untouched.
            raise ActionForbiddenError from None
        except VerifierFailed as exc:
            # The write was rolled back — this is our bug, not the user's. The proposal stays
            # pending and reusable; the audit trail records the failed verdicts.
            audit.record(module="assistant", action="verifier_failed", entity_type="Action",
                         entity_id=name, actor=request.user, result="failure",
                         after=exc.data)
            raise
        except AppError:
            raise  # module validation (unknown item, empty order…) — surface its blame-free message
        except Exception as exc:  # unexpected — never leak a trace; leave the proposal reusable
            raise ActionFailedError from exc

        if report is not None:
            result["verifier"] = {"ok": True, "packs": [f.pack for f in report.findings]}

        proposal["status"] = "confirmed"
        proposal["result"] = result
        proposal["idempotency_key"] = key
        if report is not None:
            proposal["verifier"] = result["verifier"]
        message.save(update_fields=["meta"])
        audit.record(module="assistant", action=name or "action", entity_type="Action",
                     entity_id=(result.get("links") or [{}])[0].get("value"), actor=request.user,
                     after={"summary": result.get("summary"), "verifier": result.get("verifier")})
        return _envelope({"status": "confirmed", "followups": [], **result})


# Simulation runs at most this many steps per call — a plan bigger than a screenful of changes
# should be split, and the cap keeps one request's rolled-back transaction bounded.
MAX_SIMULATION_STEPS = 10


class SimulateView(APIView):
    """Dry-run a plan of write-actions and return the FILE_04 diff — nothing is ever persisted
    (``simulation.simulate`` runs every step inside one transaction that always rolls back).

    Gated on ``IsAuthenticated`` ONLY — deliberately NOT on ``client.enabled()`` like the chat/ask
    views: simulation is pure DB dry-run, no model hop, so it works with the AI layer switched off.
    RBAC is not re-checked here either: ``actions.build``/``execute`` run as the caller, so the
    simulation refuses exactly what a real confirm would refuse (a step the actor can't run comes
    back ``ok: false`` with nothing written).

    Two input shapes:
    - ``{"steps": [{"action", "args"}, ...]}`` — a generic plan (Phase A/B's preview surface).
    - ``{"message_id": int}`` — preview one pending proposal the agent already prepared (T5.3): its
      stored, already-built payload is simulated directly as a one-step plan.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        message_id = request.data.get("message_id")
        if message_id is not None:
            steps = [self._step_from_proposal(request, message_id)]
        else:
            steps = self._steps_from_body(request.data.get("steps"))
        return _envelope(simulate(request.user, steps))

    def _step_from_proposal(self, request: Request, message_id) -> PlanStep:
        # Own-check through the conversation: a foreign message is indistinguishable from absent.
        message = get_object_or_404(
            Message, pk=message_id, conversation__user=request.user,
            role=Message.Role.ASSISTANT,
        )
        proposal = (message.meta or {}).get("proposal")
        if not proposal:
            raise Http404
        name = proposal.get("action")
        if name not in actions.ACTIONS:
            raise ValidationError(f"There is no action named '{name}'.")
        # The stored payload is post-build; hand it over as a prebuilt step so simulate() skips
        # build() and dry-runs the exact confirm this card would execute.
        return PlanStep(action=name, args={}, payload=proposal.get("payload") or {})

    def _steps_from_body(self, raw) -> list[PlanStep]:
        if not isinstance(raw, list) or not raw:
            raise ValidationError("Provide at least one step to simulate.")
        if len(raw) > MAX_SIMULATION_STEPS:
            raise ValidationError(
                f"A simulation runs at most {MAX_SIMULATION_STEPS} steps at once.")
        steps: list[PlanStep] = []
        for entry in raw:
            name = (entry or {}).get("action") if isinstance(entry, dict) else None
            if name not in actions.ACTIONS:
                raise ValidationError(f"There is no action named '{name}'.")
            steps.append(PlanStep(action=name, args=(entry.get("args") or {})))
        return steps


class DetourResumeView(APIView):
    """Resume paused work after a guided detour (plan session 13) — the return half of a session-12
    suggestion. Body: ``{"message_id": int, "resolved": {entity, id, label} | null}`` (the client also
    sends ``conversation_id`` for symmetry; the own-check goes through the message's conversation).

    The suggestion + its ``meta.pending`` live on the assistant message. Single-use, exactly like a
    proposal: once the card is resolved a second resume 409s. Streams the welcome-back over the same
    SSE contract as ``ChatView`` (reusing ``_sse``), so the client renders it like any reply.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        if not client.enabled():
            raise Http404
        # Own-check through the conversation: a foreign / unknown message is a plain 404.
        message = get_object_or_404(
            Message, pk=request.data.get("message_id"),
            conversation__user=request.user, role=Message.Role.ASSISTANT,
        )
        meta = message.meta or {}
        suggestion = meta.get("suggestion")
        if not suggestion or not meta.get("pending"):
            raise Http404  # nothing paused here to resume
        if suggestion.get("status") != "open":
            # Already resolved — single-use, never resumes twice.
            raise ActionAlreadyHandledError
        resolved = request.data.get("resolved") or None
        if resolved is not None and not isinstance(resolved, dict):
            raise ValidationError("resolved must be an object or null.")
        conversation = message.conversation

        def _events():
            try:
                for event in services.resume_detour(
                    actor=request.user, conversation=conversation,
                    source_message=message, resolved=resolved,
                ):
                    yield _sse(event)
            except (BrokenPipeError, ConnectionResetError, GeneratorExit):
                raise  # client cancelled — partial welcome-back already persisted; exit quietly
            except AppError as exc:
                yield _sse({"type": "error", "message": exc.message, "code": exc.code})
            except Exception:  # pragma: no cover - unexpected; never leak a trace to the client
                logger.exception("assistant detour resume failed")
                yield _sse({"type": "error", "message": AssistantUnavailableError.message})

        response = StreamingHttpResponse(_events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


def _import_card(request: Request):
    """Resolve (and own-check) the assistant message carrying an import card + its persisted task.

    Preview/execute are keyed by ``message_id`` (not a raw ``attachment_id``): the file and target
    ride in the card's ``meta.import``, so a client can never point the run at someone else's file or
    a different target — it only supplies the column mapping the user adjusted."""
    message = get_object_or_404(
        Message, pk=request.data.get("message_id"),
        conversation__user=request.user, role=Message.Role.ASSISTANT,
    )
    task = (message.meta or {}).get("import")
    if not task:
        raise Http404
    attachment = get_object_or_404(Attachment, pk=task.get("attachment_id"), user=request.user)
    mapping = request.data.get("mapping")
    if not isinstance(mapping, dict):
        raise ValidationError("A column mapping is required.")
    return message, task, attachment, mapping


class ImportInspectView(APIView):
    """Sniff an uploaded spreadsheet and propose a header→field mapping (plan session 14). Creating
    records is the same right as any create, so Branch Manager is required. Returns a mapping-stage
    card; the chat loop reaches the same ``imports.inspect`` directly when the user asks in chat."""

    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        attachment = get_object_or_404(Attachment, pk=request.data.get("attachment_id"),
                                       user=request.user)
        inspected = imports.inspect(request.user, attachment, request.data.get("target"))
        if "error" in inspected:
            return _envelope(inspected)
        return _envelope(imports.as_card(inspected, attachment.id))


class ImportPreviewView(APIView):
    """Dry-run every row of a mapped import — parse + duplicate check, nothing written."""

    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        _message, task, attachment, mapping = _import_card(request)
        return _envelope(imports.preview(request.user, attachment, mapping, task.get("target")))


class ImportExecuteView(APIView):
    """Create the valid, non-duplicate rows (single-use — a second run 409s). Persists the report
    into the card's ``meta.import`` so a reloaded thread shows the settled outcome, mirroring how a
    confirmed action proposal is stored."""

    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        message, task, attachment, mapping = _import_card(request)
        if task.get("stage") == "report":
            raise ActionAlreadyHandledError
        result = imports.execute(request.user, attachment, mapping, task.get("target"))
        meta = message.meta or {}
        meta["import"] = {**task, "mapping": mapping, "stage": "report", "report": result}
        message.meta = meta
        message.save(update_fields=["meta"])
        return _envelope(result)


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
