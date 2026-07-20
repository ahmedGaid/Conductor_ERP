"""Stubbed ETA (Egyptian Tax Authority) e-invoicing adapter.

The real ETA API requires signed submissions + credentials + network access — out of scope for a
customer-hosted dev/offline build (no cloud-only deps). This adapter **simulates** the contract
deterministically: ``submit`` returns a stable local reference derived from the document hash (so a
retry is idempotent and tests are reproducible) and an acknowledgement that the document is
prepared. Swapping in a real HTTP client later only touches this file.

**Claims discipline (brand-philosophy-review §04j P1).** Nothing here reaches the Tax Authority, so
nothing here may report a Tax-Authority outcome. ``query`` returns ``"pending"`` — never ``"valid"``
— and ``SIMULATED`` tells callers (and the UI copy behind it) that the lifecycle is local only. A
real adapter sets ``SIMULATED = False`` and may then return ``"valid"``.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


# False only when this module actually talks to ETA. Read by ``issue.poll_invoice`` (which refuses
# to mark anything "valid" while it is True) and surfaced to the UI so the copy can stay honest.
SIMULATED = True


def document_hash(document: dict) -> str:
    """Stable sha256 over the canonical document — what ETA would sign/identify."""
    canonical = json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SubmitResult:
    uuid: str
    accepted: bool
    error: str = ""


def submit(document: dict) -> SubmitResult:
    """Prepare a document for ETA. The reference is LOCAL — the first 64 hex chars of the document
    hash — not a UUID assigned by the Tax Authority. Deterministic so retries are idempotent."""
    h = document_hash(document)
    return SubmitResult(uuid=h[:64], accepted=True)


def query(uuid: str) -> str:
    """Poll for a prepared document's outcome.

    The stub never saw ETA, so it cannot report an ETA verdict: a prepared document stays
    ``"pending"`` forever. Only a real adapter may return ``"valid"``.
    """
    return "pending" if uuid else "rejected"
