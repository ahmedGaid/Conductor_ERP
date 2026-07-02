"""Data-scope enforcement — e-invoicing (the Session-00 reference implementation).

Proves the whole chain: invoicing an order stamps the ETA invoice with the order's branch (carried
on the event payload as a business key); scope_queryset narrows a BRANCH-scoped user to their own
branch (plus unstamped/NULL records); and the live /api/einvoice list + detail apply it, with an
out-of-scope detail returning 404.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.core.models import Branch
from erp.einvoice.domain.models import ETAInvoice
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
)
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

VIEW = "einvoice.invoice.view"


def _manager(username: str, branch: Branch | None, scope: str = "branch") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": scope})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def _catalog():
    make_books()
    make_vat()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh, qty="100")
    make_customer()


def _invoiced_order(actor):
    from erp.sales.domain.models import Customer

    customer = Customer.objects.get(code="CUST1")
    order = create_order(
        customer=customer, warehouse_code="MAIN", order_date=DATE, tax_code="VAT14",
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("1"), unit_price_minor=150_00)],
        actor=actor,
    )
    confirm_order(order, actor=actor)
    deliver_order(order, actor=actor)
    invoice_order(order, actor=actor)
    order.refresh_from_db()
    return order


def test_recording_stamps_the_source_orders_branch():
    _catalog()
    branch = Branch.objects.create(code="BR-A", name="Alpha")
    mgr = _manager("mgr_a", branch)
    order = _invoiced_order(mgr)
    eta = ETAInvoice.objects.get(invoice_number=order.invoice_number)
    assert eta.branch_id == branch.id


def test_branch_scope_isolates_other_branch_but_keeps_null():
    _catalog()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("mgr_a", a)
    mgr_b = _manager("mgr_b", b)
    order_a = _invoiced_order(mgr_a)
    order_b = _invoiced_order(mgr_b)
    eta_a = ETAInvoice.objects.get(invoice_number=order_a.invoice_number)
    eta_b = ETAInvoice.objects.get(invoice_number=order_b.invoice_number)
    # An unstamped (legacy / system) e-invoice stays visible to every branch.
    eta_null = ETAInvoice.objects.create(invoice_number="INV-NULL", issue_date=DATE)

    seen_by_a = set(scope_queryset(mgr_a, ETAInvoice.objects.all(), VIEW).values_list("id", flat=True))
    assert seen_by_a == {eta_a.id, eta_null.id}
    assert eta_b.id not in seen_by_a


def test_list_and_detail_endpoints_are_branch_scoped():
    _catalog()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("mgr_a", a)
    mgr_b = _manager("mgr_b", b)
    order_a = _invoiced_order(mgr_a)
    order_b = _invoiced_order(mgr_b)
    eta_a = ETAInvoice.objects.get(invoice_number=order_a.invoice_number)
    eta_b = ETAInvoice.objects.get(invoice_number=order_b.invoice_number)

    client = APIClient()
    client.force_authenticate(user=mgr_a)
    rows = client.get("/api/einvoice/invoices").data["data"]
    assert {r["invoice_number"] for r in rows} == {eta_a.invoice_number}

    assert client.get(f"/api/einvoice/invoices/{eta_a.id}").status_code == 200
    # Out of scope reads as absent — 404, never 403 (existence must not leak).
    assert client.get(f"/api/einvoice/invoices/{eta_b.id}").status_code == 404
    assert client.post(f"/api/einvoice/invoices/{eta_b.id}/submit").status_code == 404
