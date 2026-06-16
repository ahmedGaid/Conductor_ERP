"""E-invoicing — recording from the sales invoice event + the ETA submit/poll lifecycle."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from erp.einvoice.domain.models import ETAInvoice, ETAStatus
from erp.einvoice.errors import InvalidEInvoiceTransitionError
from erp.einvoice.services import (
    EInvoiceInput,
    poll_invoice,
    record_invoice,
    submit_invoice,
)
from erp.sales.services import confirm_order, create_order, deliver_order, invoice_order
from erp.sales.services import OrderLineInput
from erp.sales.tests.factories import (
    DATE,
    make_books,
    make_customer,
    make_item,
    make_vat,
    make_warehouse,
    stocked,
)

pytestmark = pytest.mark.django_db


def _invoiced_order(tax_code="VAT14"):
    make_books()
    make_vat()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE, tax_code=tax_code,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    order.refresh_from_db()
    return order


def test_invoicing_records_eta_invoice_via_the_event_bus():
    order = _invoiced_order()
    eta = ETAInvoice.objects.get(invoice_number=order.invoice_number)
    assert eta.status == ETAStatus.DRAFT
    assert eta.order_number == order.number
    assert eta.customer_code == "CUST1"
    assert eta.net_minor == 1500_00
    assert eta.tax_minor == 210_00
    assert eta.total_minor == 1710_00
    assert eta.document_hash  # computed at record time


def test_submit_then_poll_validates():
    order = _invoiced_order()
    eta = ETAInvoice.objects.get(invoice_number=order.invoice_number)

    submit_invoice(eta)
    eta.refresh_from_db()
    assert eta.status == ETAStatus.SUBMITTED
    assert len(eta.uuid) == 64
    assert eta.submitted_at is not None
    first_uuid = eta.uuid

    # Submit is idempotent on the UUID.
    submit_invoice(eta)
    eta.refresh_from_db()
    assert eta.uuid == first_uuid

    poll_invoice(eta)
    eta.refresh_from_db()
    assert eta.status == ETAStatus.VALID
    assert eta.validated_at is not None


def test_poll_before_submit_rejected():
    order = _invoiced_order(tax_code="")
    eta = ETAInvoice.objects.get(invoice_number=order.invoice_number)
    with pytest.raises(InvalidEInvoiceTransitionError):
        poll_invoice(eta)


def test_record_invoice_is_idempotent():
    data = EInvoiceInput(invoice_number="JV-2026-000099", issue_date=dt.date(2026, 6, 16),
                         net_minor=100_00, tax_minor=14_00, total_minor=114_00)
    a = record_invoice(data)
    b = record_invoice(data)
    assert a.id == b.id
    assert ETAInvoice.objects.filter(invoice_number="JV-2026-000099").count() == 1


def test_untaxed_invoice_still_recorded():
    order = _invoiced_order(tax_code="")
    eta = ETAInvoice.objects.get(invoice_number=order.invoice_number)
    assert eta.tax_minor == 0
    assert eta.total_minor == 1500_00


def test_eta_lifecycle_via_api():
    from rest_framework.test import APIClient

    from erp.identity.models import User

    order = _invoiced_order()
    eta = ETAInvoice.objects.get(invoice_number=order.invoice_number)

    user = User.objects.create_user(username="ein_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)

    listed = client.get("/api/einvoice/invoices").data["data"]
    assert any(r["invoice_number"] == order.invoice_number for r in listed)

    submitted = client.post(f"/api/einvoice/invoices/{eta.id}/submit").data["data"]
    assert submitted["status"] == "submitted"
    assert submitted["uuid"]

    validated = client.post(f"/api/einvoice/invoices/{eta.id}/poll").data["data"]
    assert validated["status"] == "valid"


def test_eta_requires_authentication():
    from rest_framework.test import APIClient

    assert APIClient().get("/api/einvoice/invoices").status_code == 401
