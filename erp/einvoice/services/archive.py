"""E-invoice long-term archiving (einvoice-eta-live FILE_05).

ETA requires an issued e-invoice and its supporting document to be retained for **five years**
(Egyptian Tax Procedures Law No. 206 of 2020, art. 37). The :class:`ETAInvoice` lifecycle row does
not itself hold the submitted document or the Tax-Authority response, so this module persists both
verbatim into :class:`ETAInvoiceArchive` at submission time and exposes a retrieval/export payload
for audit or tax review.

Claims discipline (§04j): an archive built on the simulated stub is flagged ``simulated=True`` and
the export payload says so — nothing here presents a simulated document as an ETA-accepted filing.
"""
from __future__ import annotations

import json

from django.utils import timezone

from ..domain.models import ETAInvoice, ETAInvoiceArchive


def _dumps(value) -> str:
    """Stable JSON for storage — ``ensure_ascii=False`` keeps Arabic readable in the archive."""
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def store(eta: ETAInvoice, *, document, raw_response, simulated: bool) -> ETAInvoiceArchive:
    """Persist (or refresh) the archive for a submitted e-invoice — the exact document + ETA response.

    Idempotent per invoice: re-submitting overwrites the one archive row rather than accumulating
    copies, so the archive always mirrors the last document actually sent. Never raises on a missing
    document — a transient submit that produced nothing simply archives what it had."""
    archive, _ = ETAInvoiceArchive.objects.update_or_create(
        eta_invoice=eta,
        defaults={
            "document_json": _dumps(document),
            "response_json": _dumps(raw_response),
            "document_hash": eta.document_hash,
            "simulated": simulated,
            "archived_at": timezone.now(),
        },
    )
    return archive


def for_invoice(eta: ETAInvoice) -> ETAInvoiceArchive | None:
    """The archive row for an invoice, or ``None`` if it has not been submitted/archived yet."""
    return ETAInvoiceArchive.objects.filter(eta_invoice=eta).first()


def export_payload(eta: ETAInvoice) -> dict | None:
    """The official-document export for an invoice: its submitted document, ETA identifiers, and
    status — the artefact a tax auditor asks for. ``None`` when nothing has been archived yet.

    ``simulated`` is surfaced so a consumer can never mistake a stub document for a filed one.
    """
    archive = for_invoice(eta)
    if archive is None:
        return None

    def _loads(raw: str):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):  # pragma: no cover — stored by _dumps, always valid
            return None

    return {
        "invoice_number": eta.invoice_number,
        "status": eta.status,
        "uuid": eta.uuid,
        "long_id": eta.long_id,
        "submission_uuid": eta.submission_uuid,
        "document_hash": archive.document_hash,
        "simulated": archive.simulated,
        "archived_at": archive.archived_at.isoformat() if archive.archived_at else None,
        "document": _loads(archive.document_json),
        "response": _loads(archive.response_json),
    }
