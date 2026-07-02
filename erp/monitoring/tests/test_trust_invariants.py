"""Session 01 trust bar — the "it can never be wrong" invariants SMBs pay for.

Property-style (seeded random over real service flows; no test-only shortcuts):
- every posted journal balances: debits == credits, always;
- every invoice satisfies net + tax == total;
- on-hand stock never goes negative, whatever the movement sequence;
- a replayed request produces exactly one side-effect (state machine or Idempotency-Key);
- every state-changing action writes an AuditEntry with actor + correlation id.
"""
from __future__ import annotations

import random
from decimal import Decimal

import pytest
from django.db.models import Sum
from rest_framework.test import APIClient

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, JournalEntry, JournalLine
from erp.accounting.errors import UnbalancedEntryError
from erp.accounting.services import JournalInput, LineInput, post_journal
from erp.audit.models import AuditEntry
from erp.core.correlation import correlation_scope
from erp.identity.models import User
from erp.inventory.domain.models import StockBalance, StockMovement
from erp.inventory.errors import InsufficientStockError
from erp.inventory.services import adjust_stock, issue_stock, receive_stock, transfer_stock
from erp.sales.domain.models import OrderStatus
from erp.sales.services import OrderLineInput, complete_sale, create_order, receive_payment
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


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="trust_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _random_orders(rng: random.Random, customer, warehouse, n: int) -> list:
    """Drive n random orders through the real order-to-cash flow (some taxed, some discounted)."""
    orders = []
    for _ in range(n):
        qty = Decimal(rng.randint(1, 20))
        price = rng.randint(1_00, 400_00)  # keeps every order below the approval threshold
        gross = int(qty) * price
        discount = rng.choice([0, rng.randint(0, gross // 4)])
        order = create_order(
            customer=customer, warehouse_code=warehouse.code, order_date=DATE,
            tax_code="VAT14" if rng.random() < 0.5 else "",
            lines=[OrderLineInput(item_sku="WIDGET", quantity=qty, unit_price_minor=price,
                                  discount_minor=discount)],
        )
        complete_sale(order)
        if rng.random() < 0.5:
            receive_payment(order, order.outstanding_minor)
        orders.append(order)
    return orders


def test_every_posted_journal_balances():
    """debits == credits on EVERY posted journal — checked in the DB, not the service's own math."""
    make_books()
    make_vat()
    item, wh = make_item(), make_warehouse()
    stocked(item, wh, qty="500", unit_cost_minor=100_00)
    customer = make_customer()
    rng = random.Random(20260701)
    _random_orders(rng, customer, wh, 8)
    for i in range(5):  # plus random balanced manual journals
        amount = rng.randint(1, 10_000_00)
        post_journal(JournalInput(date=DATE, memo=f"manual {i}", lines=[
            LineInput(account_code="1000", debit=amount),
            LineInput(account_code="4000", credit=amount),
        ]))
    per_entry = JournalLine.objects.values("entry_id").annotate(d=Sum("debit"), c=Sum("credit"))
    assert len(per_entry) >= 13  # stocking receipt + order flows + manual journals all posted
    for row in per_entry:
        assert row["d"] == row["c"], row


def test_unbalanced_journal_is_rejected_and_writes_nothing():
    make_books()
    before = JournalEntry.objects.count()
    with pytest.raises(UnbalancedEntryError):
        post_journal(JournalInput(date=DATE, memo="bad", lines=[
            LineInput(account_code="1000", debit=100),
            LineInput(account_code="4000", credit=99),
        ]))
    assert JournalEntry.objects.count() == before


def test_every_invoice_satisfies_net_plus_tax_equals_total():
    make_books()
    make_vat()
    item, wh = make_item(), make_warehouse()
    stocked(item, wh, qty="500", unit_cost_minor=100_00)
    customer = make_customer()
    orders = _random_orders(random.Random(20260702), customer, wh, 10)
    for order in orders:
        order.refresh_from_db()
        assert order.invoice_number
        assert order.subtotal_minor + order.tax_minor == order.invoiced_minor, order.number
        assert order.paid_minor <= order.invoiced_minor


def test_on_hand_never_negative_after_any_movement_sequence():
    make_books()
    # adjust_stock posts count variances to Inventory Adjustment, which the sales factories don't seed.
    Account.objects.create(code="5900", name="Inventory Adjustment", type=AccountType.EXPENSE)
    item = make_item()
    warehouses = [make_warehouse("WH1"), make_warehouse("WH2")]
    rng = random.Random(20260703)
    refused = 0
    for _ in range(60):
        wh = rng.choice(warehouses)
        qty = Decimal(rng.randint(1, 30))
        try:
            action = rng.choice(["receive", "issue", "issue", "transfer", "adjust"])
            if action == "receive":
                receive_stock(item=item, warehouse=wh, quantity=qty,
                              unit_cost_minor=rng.randint(1_00, 50_00), date=DATE)
            elif action == "issue":
                issue_stock(item=item, warehouse=wh, quantity=qty, date=DATE)
            elif action == "transfer":
                source, dest = rng.sample(warehouses, 2)
                transfer_stock(item=item, source=source, destination=dest, quantity=qty, date=DATE)
            else:
                adjust_stock(item=item, warehouse=wh, counted_quantity=Decimal(rng.randint(0, 40)),
                             date=DATE, unit_cost_minor=10_00)
        except InsufficientStockError:
            refused += 1  # the guard refusing an over-issue IS the invariant holding
        for balance in StockBalance.objects.all():
            assert Decimal(balance.quantity) >= 0, balance.quantity
    assert StockMovement.objects.exists()
    assert refused > 0  # the sequence genuinely attempted over-issues


def test_replayed_receive_request_has_exactly_one_side_effect():
    """Same Idempotency-Key → one movement, one balance bump; the replay gets the same movement."""
    make_books()
    make_item()
    make_warehouse()
    client = _admin_client()
    payload = {"item_sku": "WIDGET", "warehouse_code": "MAIN", "quantity": "5", "unit_cost": 10_00}

    first = client.post("/api/inventory/movements/receive", payload, format="json",
                        HTTP_IDEMPOTENCY_KEY="RCV-REPLAY-1")
    replay = client.post("/api/inventory/movements/receive", payload, format="json",
                         HTTP_IDEMPOTENCY_KEY="RCV-REPLAY-1")
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.data["data"]["id"] == first.data["data"]["id"]
    assert StockMovement.objects.count() == 1
    balance = StockBalance.objects.get()
    assert Decimal(balance.quantity) == Decimal("5")

    # A different key is a genuinely new request, not a replay.
    fresh = client.post("/api/inventory/movements/receive", payload, format="json",
                        HTTP_IDEMPOTENCY_KEY="RCV-REPLAY-2")
    assert fresh.status_code == 201
    assert StockMovement.objects.count() == 2


def test_replayed_complete_sale_has_exactly_one_side_effect():
    """The order state machine rejects the replay: one invoice, one AR posting, amounts unchanged."""
    make_books()
    item, wh = make_item(), make_warehouse()
    stocked(item, wh)
    customer = make_customer()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("2"), unit_price_minor=100_00)],
    )
    client = _admin_client()

    first = client.post(f"/api/sales/orders/{order.id}/complete", {}, format="json")
    assert first.status_code == 200
    order.refresh_from_db()
    invoiced = order.invoiced_minor

    # complete_sale only drives remaining steps, so a replay on an INVOICED order is a designed
    # no-op: it succeeds without repeating any side-effect (double-click safe).
    replay = client.post(f"/api/sales/orders/{order.id}/complete", {}, format="json")
    assert replay.status_code == 200
    order.refresh_from_db()
    assert order.status == OrderStatus.INVOICED
    assert order.invoiced_minor == invoiced
    assert JournalEntry.objects.filter(source="sales", reference=order.number).count() == 1


def test_state_changing_actions_audit_actor_and_correlation():
    """Spot-check three modules: inventory, sales, accounting all audit actor + correlation id."""
    make_books()
    item, wh = make_item(), make_warehouse()
    customer = make_customer()
    user = User.objects.create_user(username="trust_actor", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])

    with correlation_scope("CID-TRUST"):
        receive_stock(item=item, warehouse=wh, quantity=Decimal("10"),
                      unit_cost_minor=100_00, date=DATE, actor=user)
        order = create_order(
            customer=customer, warehouse_code=wh.code, order_date=DATE,
            lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("1"), unit_price_minor=100_00)],
            actor=user,
        )
        complete_sale(order, actor=user)

    entries = AuditEntry.objects.filter(correlation_id="CID-TRUST")
    seen = {(e.module, e.action) for e in entries}
    for expected in [("inventory", "receive_stock"), ("sales", "invoice_order"),
                     ("accounting", "post_journal")]:
        assert expected in seen, seen
    # Bus subscribers (e-invoicing, notifications) act as the system, not the user — for those the
    # shared correlation id (asserted by the filter above) is the trace back to the user's action.
    SYSTEM_MODULES = {"einvoice", "notifications"}
    offenders = [(e.module, e.action) for e in entries
                 if e.module not in SYSTEM_MODULES and e.actor_id != user.id]
    assert not offenders, f"user-invoked action audited without the acting user: {offenders}"
    assert any(e.module in SYSTEM_MODULES for e in entries), \
        "event-driven follow-ups must share the originating correlation id"
