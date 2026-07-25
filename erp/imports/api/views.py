"""Smart Import Engine REST API (plan session 11) — thin endpoint shells over the already-built
services: readers/detect/mapping (sessions 2-3), normalize/validate (4/6), duplicates (7),
masters (8), engine (9), runner (10), autofix (this session's Task B).

Every endpoint is actor-scoped: ``IsAuthenticated`` + ``BRANCH_MANAGER``-or-admin at the class
level (the same role every import adapter's own ``write`` already requires), plus a per-batch
ownership check (``_get_owned_batch``) so one branch manager can't reach into another's
in-progress import — System Admin/superuser bypass, mirroring ``HasAnyRole``'s own admin bypass.
"""
from __future__ import annotations

import csv
import io

from django.conf import settings
from django.http import HttpResponse
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.assistant.models import Attachment
from erp.core.errors import ConflictError, NotFoundError, ValidationError
from erp.core.errors import PermissionError as ForbiddenError
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER, SYSTEM_ADMIN

from .. import analyze as analyze_svc
from .. import autofix, detect, duplicates, engine, masters, readers, runner
from .. import mapping as mapping_svc
from .. import validate as validate_svc
from ..models import ImportBatch, ImportProfile, ImportRow
from ..registry import entities as registry_entities
from ..registry import get as get_adapter

_CanImport = HasAnyRole.require(BRANCH_MANAGER)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _max_upload_bytes() -> int:
    return getattr(settings, "IMPORTS_MAX_FILE_MB", 50) * 1024 * 1024


def _is_elevated(actor) -> bool:
    if getattr(actor, "is_superuser", False):
        return True
    return SYSTEM_ADMIN in set(actor.roles)


def _get_owned_batch(actor, pk) -> ImportBatch:
    try:
        batch = ImportBatch.objects.get(pk=pk)
    except ImportBatch.DoesNotExist:
        raise NotFoundError("Import batch not found.")
    if not _is_elevated(actor) and batch.created_by_id != actor.id:
        raise ForbiddenError("You do not have access to this import batch.")
    return batch


def _require_status(batch: ImportBatch, *allowed: str) -> None:
    if batch.status not in allowed:
        raise ConflictError(
            f"Batch is '{batch.status}' — this action needs one of {list(allowed)}.",
            data={"status": batch.status, "allowed": list(allowed)},
        )


def _batch_row(batch: ImportBatch) -> dict:
    # `entity_fields` on the upload response only covers the moment of upload — a resumed batch
    # (page reload, or the review screen opened straight from `/imports/<id>`) has no other way to
    # learn its entity's field kinds (text/number/money/date/ref/enum), which the review grid needs
    # to render the right inline-edit input per column. Every batch has exactly one entity by the
    # time it's out of `mapping` status, so this is cheap and always in sync with the adapter.
    adapter = get_adapter(batch.entity) if batch.entity else None
    fields = [_field_row(f) for f in adapter.fields] if adapter else []
    return {
        "id": batch.pk,
        "entity": batch.entity,
        "status": batch.status,
        "strategy": batch.strategy,
        "mapping": batch.mapping,
        "fields": fields,
        # Grouped (document) entities only (FILE_15 CONFIRMED SCOPE) — null/empty for every
        # master adapter, so the review grid's existing flat rendering is unaffected.
        "group_by": adapter.group_by if adapter else None,
        "header_fields": list(getattr(adapter, "header_fields", [])) if adapter else [],
        "file_name": batch.source_file.name if batch.source_file_id else None,
        "row_count": batch.row_count,
        "processed_count": batch.processed_count,
        "error_count": batch.error_count,
        "stats": batch.stats,
        "profile_id": batch.profile_id,
        "created_by": batch.created_by_id,
        "created_by_name": (batch.created_by.get_full_name() or batch.created_by.username) if batch.created_by_id else None,
        "created_at": batch.created_at.isoformat(),
        "updated_at": batch.updated_at.isoformat(),
    }


def _row_row(row: ImportRow) -> dict:
    return {
        "row_number": row.row_number,
        "raw": row.raw,
        "normalized": row.normalized,
        "status": row.status,
        "issues": row.issues,
        "decision": row.decision,
        "result_ref": row.result_ref,
        "group_meta": row.group_meta or None,
    }


def _profile_row(p: ImportProfile) -> dict:
    return {"id": p.pk, "name": p.name, "entity": p.entity, "mapping": p.mapping, "options": p.options}


def _field_row(f) -> dict:
    return {
        "name": f.name, "required": f.required, "kind": f.kind,
        "ref": f.ref, "enum": f.enum,
    }


class _AlwaysAcceptContentNegotiation(BaseContentNegotiation):
    """DRF's default negotiation reserves the ``format`` query param for its OWN renderer
    selection and 404s when nothing registers that format — ``ReportView`` needs that exact
    param for something else (``?format=csv`` streams a CSV response it builds by hand), so it
    opts out of format-based negotiation entirely and always uses the first configured renderer.
    """

    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


# --- upload / mapping ---------------------------------------------------------------------------
class UploadView(APIView):
    """POST — sniff + read headers + detect the entity + create the batch (status ``mapping``)."""

    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError("No file was uploaded.")
        if upload.size and upload.size > _max_upload_bytes():
            raise ValidationError(
                "File is too large.",
                data={"max_bytes": _max_upload_bytes(), "size": upload.size},
            )

        attachment = Attachment.objects.create(
            user=request.user, file=upload, name=(upload.name or "file")[:255],
            content_type=upload.content_type or "", size=upload.size or 0,
        )
        # Read back from the saved attachment, never from `upload` itself — `upload`'s stream
        # would otherwise already be at EOF if anything upstream had read it.
        data = _read_attachment(attachment)
        try:
            file_info = readers.sniff(data)
            headers = readers.read_headers(data)
        except readers.UnsupportedFormat as exc:
            raise ValidationError("Unsupported file.", data={"message_key": exc.message_key}) from exc

        detected = detect.detect_entity(request.user, headers.headers, headers.samples)
        top_entity = detected.top.entity if detected.top else None

        mapping_suggestion = {}
        if top_entity:
            adapter = get_adapter(top_entity)
            result = mapping_svc.match_headers(headers.headers, adapter)
            mapping_suggestion = {
                h: {"field": m.field, "confidence": m.confidence, "method": m.method}
                for h, m in result.columns.items()
            }

        profile_hits = []
        if top_entity:
            profile_hits = [
                _profile_row(p) for p in ImportProfile.objects.filter(entity=top_entity).order_by("name")
            ]

        # Field specs for every candidate (not just the top pick) so the wizard can render the
        # mapping table immediately if the user picks a different candidate than the leader —
        # no extra round-trip needed.
        candidate_entities = {c.entity for c in detected.candidates}
        if top_entity:
            candidate_entities.add(top_entity)
        entity_fields = {e: [_field_row(f) for f in get_adapter(e).fields] for e in candidate_entities}
        entity_labels = {e: get_adapter(e).label_key for e in candidate_entities}

        batch = ImportBatch.objects.create(
            entity=top_entity or "", source_file=attachment,
            status=ImportBatch.Status.MAPPING, created_by=request.user,
        )

        return _envelope({
            "batch_id": batch.pk,
            "file_info": {
                "format": file_info.format,
                "sheets": [{"name": s.name, "row_count": s.row_count} for s in file_info.sheets],
                "encoding": file_info.encoding,
                "delimiter": file_info.delimiter,
            },
            "headers": headers.headers,
            "samples": headers.samples,
            "candidates": [
                {"entity": c.entity, "confidence": c.confidence, "label_key": entity_labels[c.entity]}
                for c in detected.candidates
            ],
            "mapping_suggestion": mapping_suggestion,
            "profile_hits": profile_hits,
            "entity_fields": entity_fields,
        }, status=201)


class MappingView(APIView):
    """POST ``{entity, mapping, profile_id?}`` — confirm the entity+mapping and run ``analyze``."""

    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        _require_status(batch, ImportBatch.Status.MAPPING)

        entity = request.data.get("entity") or batch.entity
        if entity not in registry_entities():
            raise ValidationError("Unknown entity.", data={"entity": entity, "known": registry_entities()})
        adapter = get_adapter(entity)

        row_mapping = request.data.get("mapping")
        profile_id = request.data.get("profile_id")
        profile = None
        if profile_id:
            try:
                profile = ImportProfile.objects.get(pk=profile_id, entity=entity)
            except ImportProfile.DoesNotExist:
                raise NotFoundError("Import profile not found.")
            if not row_mapping:
                headers = readers.read_headers(_read_attachment(batch.source_file))
                row_mapping = mapping_svc.apply_profile(profile, headers.headers).field_map()

        if not row_mapping:
            raise ValidationError("A header-to-field mapping is required.")
        unknown_fields = set(row_mapping) - {f.name for f in adapter.fields}
        if unknown_fields:
            raise ValidationError("Mapping names unknown fields.", data={"unknown": sorted(unknown_fields)})

        batch.entity = entity
        batch.mapping = row_mapping
        batch.profile = profile
        batch.save(update_fields=["entity", "mapping", "profile"])

        stats = analyze_svc.analyze(request.user, batch)
        validate_svc.validate_batch(request.user, batch)
        duplicates.find_candidates(request.user, adapter, batch)

        batch.refresh_from_db()
        return _envelope({"batch": _batch_row(batch), "stats": stats})


def _read_attachment(attachment) -> bytes:
    attachment.file.open("rb")
    try:
        return attachment.file.read()
    finally:
        attachment.file.close()


# --- batch status / rows -------------------------------------------------------------------------
class BatchDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def get(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        return _envelope(_batch_row(batch))


class BatchRowsView(APIView):
    """GET ``?status=&page=&page_size=`` — the preview-grid page."""

    permission_classes = [IsAuthenticated, _CanImport]

    def get(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        qs = batch.rows.all().order_by("row_number")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        page = max(int(request.query_params.get("page", 1) or 1), 1)
        page_size = min(max(int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)

        adapter = get_adapter(batch.entity) if batch.entity else None
        if adapter is not None and adapter.group_by and not status_filter:
            # Group-aware paging (FILE_15 CONFIRMED SCOPE): a page holds whole documents, never
            # splits one across the boundary — ``page`` counts DOCUMENTS here, not rows. Loads every
            # row of the batch once; document-adapter files are invoice-shaped (small relative to a
            # 100k-row master import), so this is a deliberate, bounded scope limit, not the general
            # case. Filtered tabs (error/valid/duplicate/skipped) keep plain row-based paging below.
            all_rows = list(qs)
            group_ids: list[str] = []
            seen: set[str] = set()
            for row in all_rows:
                gid = (row.group_meta or {}).get("group_id")
                if gid is not None and gid not in seen:
                    seen.add(gid)
                    group_ids.append(gid)
            total = len(group_ids)
            start = (page - 1) * page_size
            page_ids = set(group_ids[start : start + page_size])
            rows = [r for r in all_rows if (r.group_meta or {}).get("group_id") in page_ids]
        else:
            total = qs.count()
            start = (page - 1) * page_size
            rows = list(qs[start : start + page_size])

        return _envelope({
            "rows": [_row_row(r) for r in rows],
            "page": page, "page_size": page_size, "total": total,
        })


class RowDetailView(APIView):
    """PATCH — inline edit and/or duplicate decision on one row, then revalidate just that row."""

    permission_classes = [IsAuthenticated, _CanImport]

    def patch(self, request: Request, pk, row_number: int) -> Response:
        batch = _get_owned_batch(request.user, pk)
        _require_status(
            batch, ImportBatch.Status.PREVIEWING, ImportBatch.Status.READY, ImportBatch.Status.PAUSED,
        )
        try:
            row = batch.rows.get(row_number=row_number)
        except ImportRow.DoesNotExist:
            raise NotFoundError("Row not found.")

        decision = request.data.get("decision")
        if decision:
            row = validate_svc.apply_decision(request.user, batch, row.id, decision)
        edits = request.data.get("edits")
        if edits:
            row.decision = {**(row.decision or {}), "edits": {**(row.decision or {}).get("edits", {}), **edits}}
            row.save(update_fields=["decision"])
            validate_svc.revalidate_rows(request.user, batch, [row.id])
            row.refresh_from_db()

        return _envelope(_row_row(row))


# --- autofix ---------------------------------------------------------------------------------
class AutofixPreviewView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        return _envelope({"fixes": autofix.preview_fixes(batch)})


class AutofixApplyView(APIView):
    """POST ``{fixes: [...]}`` — apply exactly the caller-approved fixes (normally the exact dicts
    ``AutofixPreviewView`` returned). Nothing is applied without this call."""

    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        accepted = request.data.get("fixes")
        if not accepted:
            raise ValidationError("No fixes given to apply.")
        counts = autofix.apply_fixes(request.user, batch, accepted)
        return _envelope({"counts": counts})


# --- creation plan (masters) --------------------------------------------------------------------
class CreationPlanView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def get(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        return _envelope({"entries": (batch.stats or {}).get("creation_plan", [])})

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        approved = request.data.get("approved")
        if approved is None:
            result = masters.build_creation_plan(request.user, batch)
        else:
            result = masters.execute_creation_plan(request.user, batch, approved)
        return _envelope(result)


# --- execute / control / rollback -----------------------------------------------------------
class ExecuteView(APIView):
    """POST ``{strategy?, atomicity?, continue_after_errors?}`` — run inline (small batch) or
    queue for ``run_imports`` (spec: "extremely fast" for the common small file)."""

    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        _require_status(batch, ImportBatch.Status.READY, ImportBatch.Status.PREVIEWING)

        strategy = request.data.get("strategy")
        if strategy:
            if strategy not in ImportBatch.Strategy.values:
                raise ValidationError("Unknown strategy.", data={"strategy": strategy})
            batch.strategy = strategy
        stats = dict(batch.stats or {})
        if "atomicity" in request.data:
            stats["atomicity"] = request.data["atomicity"]
        if "continue_after_errors" in request.data:
            stats["continue_after_errors"] = bool(request.data["continue_after_errors"])
        batch.stats = stats

        # Check readiness against the in-memory (not-yet-saved) strategy/stats BEFORE writing
        # `ready` — a batch that fails this must never be left stuck in `ready` (the background
        # runner claims by status alone and has no way to notice it isn't actually ready).
        try:
            engine.check_readiness(batch)
        except engine.ReadinessError as exc:
            raise ConflictError("Batch is not ready to execute.", data={"reasons": exc.reasons})

        batch.status = ImportBatch.Status.READY
        batch.save(update_fields=["strategy", "stats", "status"])

        if runner.should_run_inline(batch):
            try:
                report = engine.execute_batch(request.user, batch)
            except engine.ReadinessError as exc:
                raise ConflictError("Batch is not ready to execute.", data={"reasons": exc.reasons})
            return _envelope({"queued": False, "report": report})

        return _envelope({"queued": True, "batch": _batch_row(batch)})


class PauseView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        runner.request_pause(request.user, batch)
        return _envelope({"queued": True})


class ResumeView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        runner.request_resume(request.user, batch)
        batch.refresh_from_db()
        return _envelope(_batch_row(batch))


class CancelView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        runner.request_cancel(request.user, batch)
        return _envelope({"queued": True})


class RollbackView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def post(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        _require_status(batch, ImportBatch.Status.DONE)
        result = engine.rollback_batch(request.user, batch)
        return _envelope(result)


# --- report / history --------------------------------------------------------------------------
class ReportView(APIView):
    """GET ``?format=csv`` streams per-row outcomes instead of the JSON report. DRF's own content
    negotiation reserves that same query param for renderer selection and 404s when no renderer
    registers ``csv`` — ``IgnoreClientContentNegotiation`` opts this view out so the view method
    decides the response format itself, exactly as Task A specifies."""

    permission_classes = [IsAuthenticated, _CanImport]
    content_negotiation_class = _AlwaysAcceptContentNegotiation

    def get(self, request: Request, pk) -> Response:
        batch = _get_owned_batch(request.user, pk)
        report = engine.build_report(batch)
        if request.query_params.get("format") == "csv":
            return _report_csv(batch, report)
        return _envelope(report)


def _report_csv(batch: ImportBatch, report: dict) -> HttpResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["row", "status", "model", "pk", "action"])
    for outcome in report["row_outcomes"]:
        ref = outcome.get("result_ref") or {}
        writer.writerow([outcome["row"], outcome["status"], ref.get("model", ""), ref.get("pk", ""), ref.get("action", "")])
    response = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="import-{batch.pk}-report.csv"'
    return response


class BatchListView(APIView):
    """GET — import history: who/when/file/rows/result, scoped to the actor unless elevated."""

    permission_classes = [IsAuthenticated, _CanImport]

    def get(self, request: Request) -> Response:
        qs = ImportBatch.objects.select_related("created_by", "source_file").order_by("-created_at")
        if not _is_elevated(request.user):
            qs = qs.filter(created_by=request.user)
        entity = request.query_params.get("entity")
        if entity:
            qs = qs.filter(entity=entity)
        page = max(int(request.query_params.get("page", 1) or 1), 1)
        page_size = min(max(int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE), 1), MAX_PAGE_SIZE)
        total = qs.count()
        start = (page - 1) * page_size
        batches = list(qs[start : start + page_size])
        return _envelope({"batches": [_batch_row(b) for b in batches], "page": page, "page_size": page_size, "total": total})


# --- profiles -----------------------------------------------------------------------------------
class ProfilesView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def get(self, request: Request) -> Response:
        qs = ImportProfile.objects.all().order_by("entity", "name")
        entity = request.query_params.get("entity")
        if entity:
            qs = qs.filter(entity=entity)
        return _envelope([_profile_row(p) for p in qs])

    def post(self, request: Request) -> Response:
        name = (request.data.get("name") or "").strip()
        entity = request.data.get("entity")
        row_mapping = request.data.get("mapping")
        if not name or not entity or not row_mapping:
            raise ValidationError("name, entity, and mapping are all required.")
        if entity not in registry_entities():
            raise ValidationError("Unknown entity.", data={"entity": entity})
        profile = ImportProfile.objects.create(
            name=name, entity=entity, mapping=row_mapping, options=request.data.get("options") or {},
            created_by=request.user,
        )
        return _envelope(_profile_row(profile), status=201)


class ProfileDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanImport]

    def delete(self, request: Request, pk) -> Response:
        try:
            profile = ImportProfile.objects.get(pk=pk)
        except ImportProfile.DoesNotExist:
            raise NotFoundError("Import profile not found.")
        profile.delete()
        return Response(status=204)
