"""E-invoice archiving + retrieval (einvoice-eta-live FILE_05).

Submitting an invoice retains the exact document + ETA response durably; a retrieval endpoint returns
that archive for audit/tax review; a simulated archive is honestly flagged (claims discipline §04j).
"""
from __future__ import annotations

import datetime as dt

import pytest

from erp.einvoice.domain.models import ETAInvoiceArchive
from erp.einvoice.services import EInvoiceInput, eta_adapter, record_invoice, submit_invoice
from erp.einvoice.services import archive
from erp.einvoice.services.eta_adapter import SubmitResult

pytestmark = pytest.mark.django_db


def _draft(number="INV-ARCH-1"):
    return record_invoice(EInvoiceInput(
        invoice_number=number, issue_date=dt.date(2026, 6, 1),
        customer_code="CUST1", customer_name="Acme",
        net_minor=100_00, tax_minor=14_00, total_minor=114_00))


def test_submit_archives_the_document_marked_simulated():
    eta = _draft()
    submit_invoice(eta)
    eta.refresh_from_db()

    arc = archive.for_invoice(eta)
    assert arc is not None
    assert arc.simulated is True            # stub — never a real filing
    assert arc.document_hash == eta.document_hash
    assert arc.archived_at is not None

    payload = archive.export_payload(eta)
    assert payload["simulated"] is True
    assert payload["status"] == "submitted"
    assert payload["invoice_number"] == "INV-ARCH-1"
    # The stub retains the local document so retrieval/export still returns something.
    assert payload["document"]["invoice"] == "INV-ARCH-1"


def test_archive_is_one_row_per_invoice_and_refreshes():
    eta = _draft("INV-ARCH-2")
    archive.store(eta, document={"v": 1}, raw_response=None, simulated=True)
    archive.store(eta, document={"v": 2}, raw_response={"ok": True}, simulated=False)

    assert ETAInvoiceArchive.objects.filter(eta_invoice=eta).count() == 1
    payload = archive.export_payload(eta)
    assert payload["document"] == {"v": 2}
    assert payload["response"] == {"ok": True}
    assert payload["simulated"] is False


def test_live_submission_archives_signed_document_not_simulated(monkeypatch):
    eta = _draft("INV-ARCH-3")
    eta_document = {"internalId": "INV-ARCH-3", "signatures": [{"signatureType": "I", "value": "x"}]}
    resp = {"submissionUUID": "SUB1", "acceptedDocuments": [{"uuid": "U1", "longId": "L1"}]}

    monkeypatch.setattr(eta_adapter, "is_live", lambda: True)
    monkeypatch.setattr(eta_adapter, "submit",
                        lambda doc: SubmitResult(uuid="U1", long_id="L1", submission_uuid="SUB1",
                                                 accepted=True, status="submitted",
                                                 document=eta_document, raw_response=resp))
    submit_invoice(eta)
    eta.refresh_from_db()

    payload = archive.export_payload(eta)
    assert payload["simulated"] is False
    assert payload["document"] == eta_document
    assert payload["response"] == resp
    assert payload["uuid"] == "U1"


def test_export_payload_none_before_submit():
    eta = _draft("INV-ARCH-4")
    assert archive.export_payload(eta) is None


def test_retrieval_api_404_before_submit_then_returns_document():
    from rest_framework.test import APIClient

    from erp.identity.models import User

    eta = _draft("INV-ARCH-5")
    user = User.objects.create_user(username="arch_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)

    assert client.get(f"/api/einvoice/invoices/{eta.id}/document").status_code == 404

    submit_invoice(eta)
    resp = client.get(f"/api/einvoice/invoices/{eta.id}/document")
    assert resp.status_code == 200
    data = resp.data["data"]
    assert data["invoice_number"] == "INV-ARCH-5"
    assert data["simulated"] is True
    assert data["document"]["invoice"] == "INV-ARCH-5"
