"""Purchasing contract read helpers used by the assistant (agent-posting-plan FILE_03)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.identity.models import User
from erp.purchasing import contracts, services
from erp.purchasing.services import POLineInput

from .factories import make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _actor() -> User:
    u = User.objects.create_user(username="buyer", password="Dev12345!", email="buyer@example.test")
    u.is_superuser = True  # bypass scoping — these tests exercise the query, not the scope
    u.save(update_fields=["is_superuser"])
    return u


def _po(supplier, warehouse, qty="10", cost=100_00):
    return services.create_order(
        supplier=supplier, warehouse_code=warehouse.code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )


def test_find_orders_by_number():
    make_books()
    make_item()
    order = _po(make_supplier(), make_warehouse())
    actor = _actor()

    matches = contracts.find_orders(actor, query=order.number)
    assert [m["number"] for m in matches] == [order.number]


def test_find_orders_by_supplier():
    make_books()
    make_item()
    supplier = make_supplier()
    order = _po(supplier, make_warehouse())
    actor = _actor()

    matches = contracts.find_orders(actor, query=supplier.name)
    assert order.number in [m["number"] for m in matches]

    no_match = contracts.find_orders(actor, query="no such supplier at all")
    assert no_match == []


def test_find_orders_line_detail_shape():
    make_books()
    make_item()
    order = _po(make_supplier(), make_warehouse(), qty="10", cost=250_00)
    actor = _actor()
    line = order.lines.get()

    match = contracts.find_orders(actor, query=order.number)[0]
    assert match["status"] == order.status
    assert match["subtotal_minor"] == order.subtotal_minor
    assert match["lines"] == [
        {"line_no": line.line_no, "item_sku": line.item_sku, "quantity": str(line.quantity),
         "received_qty": str(line.received_qty), "unit_cost_minor": line.unit_cost_minor}
    ]
