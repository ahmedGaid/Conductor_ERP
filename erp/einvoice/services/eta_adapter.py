"""Stubbed ETA (Egyptian Tax Authority) e-invoicing adapter.

The real ETA API requires signed submissions + credentials + network access — out of scope for a
customer-hosted dev/offline build (no cloud-only deps). This adapter **simulates** the contract
deterministically: ``submit`` returns a stable UUID derived from the document hash (so a retry is
idempotent and tests are reproducible) and a "submitted" acknowledgement; ``query`` reports the
document as "valid". Swapping in a real HTTP client later only touches this file.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


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
    """Submit a document to ETA. Deterministic UUID = first 64 hex chars of its hash."""
    h = document_hash(document)
    return SubmitResult(uuid=h[:64], accepted=True)


def query(uuid: str) -> str:
    """Poll ETA for a submitted document's status. The stub validates everything it received."""
    return "valid" if uuid else "rejected"
