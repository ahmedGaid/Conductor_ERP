"""FILE_02 — real ETA submission adapter: document mapping, submit/query dispatch, and the
issue-service wiring around a live result.

The live path is exercised with **mocked ETA responses** (the documented documentsubmissions /
document-details shapes). A real sandbox round-trip is STOP-gated on the company's ETA pre-production
credentials + tax profile — proven separately once those arrive; these tests pin the contract the
adapter must satisfy the moment it does.
"""
from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import pytest

from erp.einvoice.domain.models import ETAInvoice, ETAStatus
from erp.einvoice.services import eta_adapter, eta_client
from erp.einvoice.services import EInvoiceInput, record_invoice, submit_invoice
from erp.einvoice.services.eta_adapter import SubmitResult


def _cfg(**over):
    base = dict(
        rin="123456789", issuer_name="Acme LLC", activity_code="4610", branch_id="0",
        country="EG", governate="Cairo", region_city="Nasr City", street="1 Main St",
        building_number="10", api_base_url="https://api.preprod.invoicing.eta.gov.eg",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _inv(**over):
    base = dict(invoice="INV-1", customer="CUST1", customer_name="Beta Co",
                customer_tax_registration_number="987654321", customer_national_id="",
                date="2026-06-16", currency="EGP", tax_code="VAT14",
                net=1500_00, tax=210_00, total=1710_00)
    base.update(over)
    return base


# --- document mapping (pure) ---------------------------------------------------------------------

def test_build_document_shape_and_totals():
    doc = eta_adapter.build_document(_inv(), _cfg())

    assert doc["documentType"] == "I"
    assert doc["documentTypeVersion"] == "1.0"
    assert doc["dateTimeIssued"] == "2026-06-16T00:00:00Z"
    assert doc["internalId"] == "INV-1"
    assert doc["issuer"]["id"] == "123456789"
    assert doc["issuer"]["name"] == "Acme LLC"
    assert doc["issuer"]["address"]["country"] == "EG"
    assert doc["receiver"]["type"] == "B"
    assert doc["receiver"]["id"] == "987654321"
    assert doc["receiver"]["name"] == "Beta Co"
    assert doc["taxpayerActivityCode"] == "4610"
    assert doc["signatures"] == []  # unsigned — FILE_03 fills this

    # Amounts are decimal EGP, converted from integer minor units at this edge.
    assert doc["totalSalesAmount"] == 1500.0
    assert doc["netAmount"] == 1500.0
    assert doc["totalAmount"] == 1710.0
    assert doc["taxTotals"] == [{"taxType": "T1", "amount": 210.0}]

    # One consolidated line; its taxable item reconciles to the header.
    assert len(doc["invoiceLines"]) == 1
    line = doc["invoiceLines"][0]
    assert line["salesTotal"] == 1500.0
    assert line["netTotal"] == 1500.0
    assert line["total"] == 1710.0
    assert line["taxableItems"] == [{"taxType": "T1", "subType": "V009", "amount": 210.0, "rate": 14.0}]
    # ETA validation rule: taxable amount == rate% * netTotal.
    assert round(line["taxableItems"][0]["rate"] / 100 * line["netTotal"], 2) == line["taxableItems"][0]["amount"]


def test_build_document_receiver_falls_back_to_national_id():
    # No tax registration number, but a national ID -> type "P" individual receiver.
    doc = eta_adapter.build_document(_inv(customer_tax_registration_number="", customer_national_id="29001011234567"), _cfg())
    assert doc["receiver"]["type"] == "P"
    assert doc["receiver"]["id"] == "29001011234567"


def test_build_document_receiver_empty_under_eta_threshold():
    # Neither on file -> receiver id is empty; ETA allows this only under the reporting threshold
    # (EGP 50,000) — build_document does not enforce that cap, it is a submission-time concern.
    doc = eta_adapter.build_document(_inv(customer_tax_registration_number="", customer_national_id=""), _cfg())
    assert doc["receiver"]["type"] == "P"
    assert doc["receiver"]["id"] == ""


def test_build_document_untaxed_has_no_tax_blocks():
    doc = eta_adapter.build_document(_inv(tax=0, total=1500_00), _cfg())
    assert doc["taxTotals"] == []
    assert doc["invoiceLines"][0]["taxableItems"] == []
    assert doc["totalAmount"] == 1500.0


def test_minor_units_convert_to_decimal_egp():
    assert eta_adapter._egp(0) == 0.0
    assert eta_adapter._egp(100) == 1.0
    assert eta_adapter._egp(210_00) == 210.0
    assert eta_adapter._egp(199) == 1.99


def test_built_document_never_carries_a_secret():
    cfg = _cfg()
    cfg.client_secret = "TOP-SECRET-VALUE"  # would be a leak if the mapper ever read it
    blob = json.dumps(eta_adapter.build_document(_inv(), cfg))
    assert "TOP-SECRET-VALUE" not in blob


# --- submit dispatch ------------------------------------------------------------------------------

@pytest.mark.django_db
def test_submit_simulated_returns_local_reference():
    # Not configured → is_live() False → deterministic 64-char local hash, accepted.
    result = eta_adapter.submit(_inv())
    assert result.accepted
    assert len(result.uuid) == 64
    assert result.long_id == ""


def test_submit_live_accepted_parses_uuid_and_long_id(monkeypatch):
    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)
    monkeypatch.setattr("erp.einvoice.services.config.effective_config", lambda: _cfg())
    monkeypatch.setattr(eta_client, "submit_document", lambda doc: {
        "submissionUUID": "SUB26CHARBATCHID0000000000",
        "acceptedDocuments": [{"uuid": "DOC26CHARUUID00000000000000", "longId": "LONG42", "internalId": "INV-1"}],
        "rejectedDocuments": [],
    })
    result = eta_adapter.submit(_inv())
    assert result.accepted
    assert result.status == "submitted"
    assert result.uuid == "DOC26CHARUUID00000000000000"
    assert result.long_id == "LONG42"
    assert result.submission_uuid == "SUB26CHARBATCHID0000000000"


def test_submit_live_rejected_carries_reason(monkeypatch):
    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)
    monkeypatch.setattr("erp.einvoice.services.config.effective_config", lambda: _cfg())
    monkeypatch.setattr(eta_client, "submit_document", lambda doc: {
        "submissionUUID": "SUB",
        "acceptedDocuments": [],
        "rejectedDocuments": [{"internalId": "INV-1", "error": {"code": "0x100", "message": "Invalid tax code"}}],
    })
    result = eta_adapter.submit(_inv())
    assert not result.accepted
    assert result.status == "rejected"
    assert not result.retryable
    assert "Invalid tax code" in result.error
    assert "0x100" in result.error


def test_submit_live_transient_is_retryable(monkeypatch):
    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)
    monkeypatch.setattr("erp.einvoice.services.config.effective_config", lambda: _cfg())

    def _boom(doc):
        raise eta_client.ETASubmissionError("ETA document API unreachable: timed out", retryable=True)

    monkeypatch.setattr(eta_client, "submit_document", _boom)
    result = eta_adapter.submit(_inv())
    assert not result.accepted
    assert result.retryable
    assert result.status == ""


def test_submit_live_unexpected_shape_is_retryable(monkeypatch):
    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)
    monkeypatch.setattr("erp.einvoice.services.config.effective_config", lambda: _cfg())
    monkeypatch.setattr(eta_client, "submit_document",
                        lambda doc: {"submissionUUID": "S", "acceptedDocuments": [], "rejectedDocuments": []})
    result = eta_adapter.submit(_inv())
    assert not result.accepted
    assert result.retryable


# --- query dispatch -------------------------------------------------------------------------------

@pytest.mark.django_db
def test_query_simulated_stays_pending():
    assert eta_adapter.query("anything") == "pending"
    assert eta_adapter.query("") == "rejected"


@pytest.mark.parametrize("eta_status,expected", [
    ("Valid", "valid"),
    ("Submitted", "pending"),
    ("Invalid", "invalid"),
    ("Rejected", "rejected"),
])
def test_query_live_maps_eta_status(monkeypatch, eta_status, expected):
    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)
    monkeypatch.setattr(eta_client, "get_document", lambda uuid: {"status": eta_status})
    assert eta_adapter.query("DOCUUID") == expected


def test_query_live_transient_reads_pending(monkeypatch):
    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)

    def _boom(uuid):
        raise eta_client.ETASubmissionError("unreachable", retryable=True)

    monkeypatch.setattr(eta_client, "get_document", _boom)
    assert eta_adapter.query("DOCUUID") == "pending"


# --- issue-service wiring around a live result ---------------------------------------------------

pytestmark_db = pytest.mark.django_db


@pytest.mark.django_db
def test_submit_invoice_stores_live_identifiers(monkeypatch):
    eta = record_invoice(EInvoiceInput(invoice_number="INV-LIVE-1", issue_date=dt.date(2026, 6, 16),
                                       net_minor=1000_00, tax_minor=140_00, total_minor=1140_00))
    monkeypatch.setattr(eta_adapter, "submit", lambda doc: SubmitResult(
        uuid="ETAUUID26", accepted=True, long_id="LONG42", submission_uuid="SUB26", status="submitted"))
    submit_invoice(eta)
    eta.refresh_from_db()
    assert eta.status == ETAStatus.SUBMITTED
    assert eta.uuid == "ETAUUID26"
    assert eta.long_id == "LONG42"
    assert eta.submission_uuid == "SUB26"
    assert eta.submitted_at is not None


@pytest.mark.django_db
def test_submit_invoice_is_idempotent_no_second_eta_call(monkeypatch):
    eta = record_invoice(EInvoiceInput(invoice_number="INV-LIVE-2", issue_date=dt.date(2026, 6, 16),
                                       net_minor=100_00, tax_minor=0, total_minor=100_00))
    calls = {"n": 0}

    def _submit(doc):
        calls["n"] += 1
        return SubmitResult(uuid="ETAUUID26", accepted=True, status="submitted")

    monkeypatch.setattr(eta_adapter, "submit", _submit)
    submit_invoice(eta)
    submit_invoice(eta.__class__.objects.get(pk=eta.pk))  # re-fetch: already submitted with a uuid
    assert calls["n"] == 1  # ETA was hit exactly once


@pytest.mark.django_db
def test_submit_invoice_transient_keeps_it_submittable(monkeypatch):
    eta = record_invoice(EInvoiceInput(invoice_number="INV-LIVE-3", issue_date=dt.date(2026, 6, 16),
                                       net_minor=100_00, tax_minor=0, total_minor=100_00))
    monkeypatch.setattr(eta_adapter, "submit", lambda doc: SubmitResult(
        uuid="", accepted=False, error="unreachable", retryable=True))
    submit_invoice(eta)
    eta.refresh_from_db()
    assert eta.status == ETAStatus.DRAFT  # not rejected — a retry can still succeed
    assert eta.error_text == "unreachable"


@pytest.mark.django_db
def test_submit_invoice_rejection_is_terminal(monkeypatch):
    eta = record_invoice(EInvoiceInput(invoice_number="INV-LIVE-4", issue_date=dt.date(2026, 6, 16),
                                       net_minor=100_00, tax_minor=0, total_minor=100_00))
    monkeypatch.setattr(eta_adapter, "submit", lambda doc: SubmitResult(
        uuid="", accepted=False, error="[0x200] bad document", status="rejected", retryable=False))
    submit_invoice(eta)
    eta.refresh_from_db()
    assert eta.status == ETAStatus.REJECTED
    assert "bad document" in eta.error_text
