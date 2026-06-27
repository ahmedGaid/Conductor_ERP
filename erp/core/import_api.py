"""DRF glue for CSV imports — shared by every importable list's API view.

Keeps the multipart parsing (file + mapping + mode + commit) and the template response in one place
so each module's import view is two thin methods over its :class:`ImportSpec`.
"""
from __future__ import annotations

import json

from django.http import HttpResponse

from .errors import ValidationError
from .imports import ImportError_, ImportSpec, import_from_upload, result_payload, template_csv


def run_import_request(spec: ImportSpec, request) -> dict:
    """Parse a multipart import request, run preview/commit, and return the JSON payload.

    Multipart fields: ``file`` (CSV), optional ``mapping`` (JSON {field: source_header}),
    ``mode`` (create | upsert), ``commit`` (bool). Whole-file problems raise a 400 ValidationError.
    """
    upload = request.FILES.get("file")
    if upload is None:
        raise ValidationError("No file was uploaded.")

    mapping = None
    raw_mapping = request.data.get("mapping")
    if raw_mapping:
        try:
            mapping = json.loads(raw_mapping) if isinstance(raw_mapping, str) else dict(raw_mapping)
        except (ValueError, TypeError) as exc:
            raise ValidationError("The column mapping is not valid JSON.") from exc

    mode = request.data.get("mode") or "create"
    if mode not in ("create", "upsert"):
        mode = "create"
    commit = str(request.data.get("commit", "")).strip().lower() in ("1", "true", "yes")

    try:
        result = import_from_upload(
            spec, upload.read(), mapping, mode=mode, commit=commit, user=request.user,
        )
    except ImportError_ as exc:
        raise ValidationError(str(exc)) from exc
    return result_payload(result)


def template_response(spec: ImportSpec, filename: str) -> HttpResponse:
    """A CSV download (canonical headers + one example row) so the columns are obvious."""
    response = HttpResponse(template_csv(spec), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
