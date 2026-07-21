"""ETA (Egyptian Tax Authority) e-invoicing adapter — the seam between the ERP lifecycle and ETA.

Two modes behind one interface (``document_hash`` / ``submit`` / ``query``):

* **Simulated** (default, when ETA is not configured or not enabled): ``submit`` returns a stable
  local reference derived from the document hash so retries are idempotent and tests are
  reproducible; ``query`` stays ``"pending"`` forever. Nothing reaches the Tax Authority, so
  nothing may claim a Tax-Authority verdict (brand-philosophy-review §04j claims discipline).
* **Live** (FILE_02, when ``is_live()``): ``submit`` builds the ETA Invoice v1.0 document from the
  invoice, POSTs it via :mod:`eta_client`, and maps the real response (submission UUID, long ID,
  accepted/rejected) to a :class:`SubmitResult`; ``query`` reads the document's ETA status.

**Contract source.** ETA Invoice v1.0 document schema + the documentsubmissions response shape were
verified 2026-07-21 against the official SDK (https://sdk.invoicing.eta.gov.eg/documents/invoice-v1-0/
and .../einvoicingapi/01-submit-documents/). Amounts on the wire are **decimal EGP**; internally
money is integer minor units (piasters), converted at this edge only.

**Data the aggregate record cannot supply.** ``ETAInvoice`` deliberately holds no line items and no
cross-module FK (gate10 event-decoupling), so a live document carries a **single consolidated
invoice line** built from the aggregate net/tax/total. The issuer tax profile (name, activity code,
address) arrives via config/env — the STOP-gated input; the document shape is complete and correct,
but a *validating* submission needs the real company profile. The receiver's tax registration number
/ national ID now arrives via the ``sales.OrderInvoiced`` event payload (``Customer.tax_registration_
number`` / ``.national_id``, migration 0011 on sales + 0005 here) — see the receiver block below.

**Signing (FILE_03).** The final document carries a detached CAdES-BES signature over its canonical
serialization (:mod:`signing`). ``build_document`` fills ``signatures`` when a signing certificate is
configured; with none configured it stays ``[]`` (the simulated/unconfigured path), so the pure
mapping stays testable without key material.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def is_live() -> bool:
    """True when the app should actually talk to ETA: credentials present *and* an API base URL.

    Auth-only config (FILE_01) is not enough — a document call also needs ``api_base_url``. When
    this is False every path stays on the simulated stub, exactly as an unconfigured install."""
    from . import config, eta_client

    cfg = config.effective_config()
    return eta_client.is_configured() and bool(str(cfg.api_base_url or "").strip())


def document_hash(document: dict) -> str:
    """Stable sha256 over the canonical document — what ETA would sign/identify."""
    canonical = json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SubmitResult:
    uuid: str
    accepted: bool
    error: str = ""
    long_id: str = ""
    submission_uuid: str = ""
    status: str = ""            # "submitted" | "rejected" | "" (transient)
    retryable: bool = False     # a transient failure — keep the invoice submittable, do not reject
    # FILE_05 archiving — the exact document that was submitted and the raw ETA response, threaded up
    # so the lifecycle layer can persist them for retention. Live: the signed ETA Invoice v1.0 doc +
    # the documentsubmissions response. Stub: the local document + a simulated marker (never a filing).
    document: dict | None = None
    raw_response: dict | None = None


def _egp(minor: int) -> float:
    """Integer minor units (piasters) → decimal EGP for the wire. Exact for 2-decimal amounts."""
    return float(Decimal(int(minor or 0)) / Decimal(100))


def _rate_percent(net_minor: int, tax_minor: int) -> float:
    """Effective VAT rate as a percentage, to 2 dp. Zero when there is no net to tax."""
    if not net_minor:
        return 0.0
    rate = (Decimal(int(tax_minor)) / Decimal(int(net_minor)) * Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(rate)


def build_document(inv: dict, cfg) -> dict:
    """Map an invoice's business data (+ the issuer config) to an ETA Invoice v1.0 document.

    ``inv`` is the flat dict :func:`erp.einvoice.services.issue._document` produces (business keys
    and integer-minor amounts). DB-free; deterministic given ``inv``/``cfg`` and the (external)
    signing certificate — with no certificate configured it is a pure mapping (``signatures == []``).
    """
    from . import signing
    net_minor = int(inv.get("net") or 0)
    tax_minor = int(inv.get("tax") or 0)
    total_minor = int(inv.get("total") or 0)
    currency = str(inv.get("currency") or "EGP")
    net_egp = _egp(net_minor)
    tax_egp = _egp(tax_minor)
    total_egp = _egp(total_minor)

    taxable_items = []
    tax_totals = []
    if tax_minor:
        # ETA taxType "T1" = value added tax; subType "V009" = the standard VAT rate. The exact
        # subType belongs to the customer's tax setup — "V009" is the common default; a richer
        # tax_code → subType map is a follow-up once ETA sub-types are configured per install.
        rate = _rate_percent(net_minor, tax_minor)
        taxable_items = [{"taxType": "T1", "subType": "V009", "amount": tax_egp, "rate": rate}]
        tax_totals = [{"taxType": "T1", "amount": tax_egp}]

    line = {
        # One consolidated line — the aggregate record stores no per-line detail (see module docs).
        "description": f"Invoice {inv.get('invoice', '')}",
        "itemType": "EGS",          # Egyptian GS/GPC code system; itemCode is the real classification
        "itemCode": "",             # unknown at the aggregate level — a validating submission needs it
        "unitType": "EA",           # each
        "quantity": 1,
        "internalCode": str(inv.get("invoice") or ""),
        "unitValue": {"currencySold": currency, "amountEGP": net_egp},
        "salesTotal": net_egp,
        "discount": {"rate": 0, "amount": 0},
        "netTotal": net_egp,
        "taxableItems": taxable_items,
        "total": total_egp,
    }

    issuer = {
        "type": "B",
        "id": str(getattr(cfg, "rin", "") or ""),
        "name": str(getattr(cfg, "issuer_name", "") or ""),
        "address": {
            "branchId": str(getattr(cfg, "branch_id", "") or ""),
            "country": str(getattr(cfg, "country", "EG") or "EG"),
            "governate": str(getattr(cfg, "governate", "") or ""),
            "regionCity": str(getattr(cfg, "region_city", "") or ""),
            "street": str(getattr(cfg, "street", "") or ""),
            "buildingNumber": str(getattr(cfg, "building_number", "") or ""),
        },
    }
    # Receiver identity: a business customer is type "B" with their tax registration number; an
    # individual is type "P" with their national ID. Neither is required under the ETA reporting
    # threshold (EGP 50,000) — a walk-in/cash sale below it may post with no receiver id (SDD).
    tax_reg = str(inv.get("customer_tax_registration_number") or "").strip()
    national_id = str(inv.get("customer_national_id") or "").strip()
    if tax_reg:
        receiver_type, receiver_id = "B", tax_reg
    elif national_id:
        receiver_type, receiver_id = "P", national_id
    else:
        receiver_type, receiver_id = "P", ""
    receiver = {
        "type": receiver_type,
        "id": receiver_id,
        "name": str(inv.get("customer_name") or ""),
        "address": {"country": "EG"},
    }

    document = {
        "issuer": issuer,
        "receiver": receiver,
        "documentType": "I",
        "documentTypeVersion": "1.0",
        "dateTimeIssued": f"{inv.get('date', '')}T00:00:00Z",
        "taxpayerActivityCode": str(getattr(cfg, "activity_code", "") or ""),
        "internalId": str(inv.get("invoice") or ""),
        "invoiceLines": [line],
        "totalDiscountAmount": 0,
        "totalSalesAmount": net_egp,
        "netAmount": net_egp,
        "taxTotals": tax_totals,
        "totalItemsDiscountAmount": 0,
        "extraDiscountAmount": 0,
        "totalAmount": total_egp,
        "signatures": [],
    }
    # Sign the canonical serialization (which excludes ``signatures``) → fill the array. Stays ``[]``
    # when no certificate is configured — the simulated/unconfigured path.
    document["signatures"] = signing.build_signatures(document)
    return document


def _parse_submission(internal_id: str, resp: dict, *, document=None, raw_response=None) -> SubmitResult:
    """Map an ETA documentsubmissions response to a :class:`SubmitResult`.

    Response shape (verified against the SDK): ``{submissionUUID, acceptedDocuments:[{uuid, longId,
    internalId}], rejectedDocuments:[{internalId, error:{code, message, ...}}]}``. ``document`` /
    ``raw_response`` are carried through onto the result for FILE_05 archiving (accepted path only —
    a rejected/transient submission has no filed document to retain).
    """
    accepted = resp.get("acceptedDocuments") or []
    rejected = resp.get("rejectedDocuments") or []
    submission_uuid = str(resp.get("submissionUUID") or resp.get("submissionId") or "")

    for doc in accepted:
        if not isinstance(doc, dict):
            continue
        if len(accepted) == 1 or str(doc.get("internalId") or "") == internal_id:
            return SubmitResult(
                uuid=str(doc.get("uuid") or ""),
                long_id=str(doc.get("longId") or ""),
                submission_uuid=submission_uuid,
                accepted=True,
                status="submitted",
                document=document,
                raw_response=raw_response,
            )

    for doc in rejected:
        if not isinstance(doc, dict):
            continue
        if len(rejected) == 1 or str(doc.get("internalId") or "") == internal_id:
            err = doc.get("error") if isinstance(doc.get("error"), dict) else {}
            code = str(err.get("code") or "").strip()
            message = str(err.get("message") or "").strip() or "The Tax Authority rejected the document."
            return SubmitResult(
                uuid="", submission_uuid=submission_uuid, accepted=False, status="rejected",
                error=(f"[{code}] {message}" if code else message),
            )

    # Neither list carried our document — an unexpected shape; treat as transient so it is retried
    # rather than burning the invoice on a response we could not read.
    return SubmitResult(
        uuid="", submission_uuid=submission_uuid, accepted=False,
        error="The Tax Authority returned no result for this document.", retryable=True,
    )


def submit(document: dict) -> SubmitResult:
    """Submit a prepared invoice to ETA (live) or produce a deterministic local reference (stub).

    Live: builds the ETA document, POSTs it, and returns the parsed submission outcome. A transient
    failure comes back ``accepted=False, retryable=True`` (the caller leaves the invoice submittable
    rather than marking it rejected). Stub: the reference is the first 64 hex chars of the document
    hash — deterministic, so a retry is idempotent."""
    if not is_live():
        # Stub: archive the local document (marked simulated by the caller) so retrieval works and a
        # demo/test has something to export — never a real ETA filing.
        return SubmitResult(uuid=document_hash(document)[:64], accepted=True, document=dict(document))

    from . import config, eta_client

    cfg = config.effective_config()
    eta_document = build_document(document, cfg)
    internal_id = str(document.get("invoice") or "")
    try:
        resp = eta_client.submit_document(eta_document)
    except eta_client.ETAConfigError as exc:
        # Configuration vanished between the is_live() check and here — stay unsubmitted, not rejected.
        return SubmitResult(uuid="", accepted=False, error=str(exc), retryable=True)
    except eta_client.ETASubmissionError as exc:
        return SubmitResult(uuid="", accepted=False, error=str(exc), retryable=exc.retryable)
    return _parse_submission(internal_id, resp, document=eta_document, raw_response=resp)


def query(uuid: str) -> str:
    """Poll a prepared document's outcome.

    Live: read the document's ETA status → ``"valid"`` / ``"pending"`` (still submitted or in
    progress) / the terminal status string (``invalid`` / ``rejected`` / ``cancelled``). A transient
    read failure returns ``"pending"`` — never invent a verdict. Stub: a prepared document rests at
    ``"pending"`` forever (only a real adapter may return ``"valid"``)."""
    if not is_live():
        return "pending" if uuid else "rejected"
    if not uuid:
        return "rejected"

    from . import eta_client

    try:
        resp = eta_client.get_document(uuid)
    except (eta_client.ETASubmissionError, eta_client.ETAConfigError):
        # No verdict to report yet — leave the record where it is; FILE_04 owns retry/reconciliation.
        return "pending"
    status = str(resp.get("status") or "").strip().lower()
    if status == "valid":
        return "valid"
    if status in ("", "submitted", "inprogress", "in progress"):
        return "pending"
    return status  # invalid | rejected | cancelled → the caller marks the invoice rejected
