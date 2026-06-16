"""Stock counts + adjustments — variances must post balanced GL and keep Inventory GL == stock value.

Also covers batch/lot traceability on receipts.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.domain.models import CountStatus, MovementType, StockBalance
from erp.inventory.errors import CountStateError, InvalidCountError
from erp.inventory.services import (
    adjust_stock,
    batches,
    create_count,
    post_count,
    receive_stock,
    set_counted,
)

from .factories import make_gl, make_item, make_warehouse

pytestmark = pytest.mark.django_db

D = dt.date(2026, 6, 15)


def _inventory_gl_balance() -> int:
    return general_ledger("1200").closing_balance


def _stock_value() -> int:
    return sum(b.value_minor for b in StockBalance.objects.all())


def test_shortage_posts_balanced_adjustment_and_keeps_invariant():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("100"), unit_cost_minor=10_00, date=D)
    assert _inventory_gl_balance() == _stock_value() == 100_000  # 100 × 10.00

    # Count finds only 95 on the shelf → shortage of 5 (cost 50.00).
    mv = adjust_stock(item=item, warehouse=wh, counted_quantity=Decimal("95"), date=D)
    assert mv.type == MovementType.ADJUSTMENT
    assert mv.value_minor == -5_000          # signed: shortage removes 50.00
    bal = StockBalance.objects.get(item=item, warehouse=wh)
    assert bal.quantity == Decimal("95")
    assert _inventory_gl_balance() == _stock_value() == 95_000
    assert trial_balance().is_balanced
    # The loss landed in Inventory Adjustment (expense, debit-normal).
    assert general_ledger("5900").closing_balance == 5_000


def test_overage_values_at_weighted_average():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=20_00, date=D)
    # Count finds 12 → overage of 2 at the 20.00 average = +40.00.
    mv = adjust_stock(item=item, warehouse=wh, counted_quantity=Decimal("12"), date=D)
    assert mv.value_minor == 4_000
    assert _inventory_gl_balance() == _stock_value() == 240_00
    assert trial_balance().is_balanced


def test_no_variance_posts_nothing():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=20_00, date=D)
    assert adjust_stock(item=item, warehouse=wh, counted_quantity=Decimal("10"), date=D) is None


def test_negative_count_rejected():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    with pytest.raises(InvalidCountError):
        adjust_stock(item=item, warehouse=wh, counted_quantity=Decimal("-1"), date=D)


def test_count_workflow_snapshots_and_posts():
    make_gl()
    item = make_item()
    other = make_item(sku="GADGET", name="Gadget")
    wh = make_warehouse()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("100"), unit_cost_minor=10_00, date=D)
    receive_stock(item=other, warehouse=wh, quantity=Decimal("50"), unit_cost_minor=4_00, date=D)

    count = create_count(warehouse=wh, count_date=D)
    assert count.lines.count() == 2  # snapshot of both balances
    widget_line = count.lines.get(item=item)
    assert widget_line.system_quantity == Decimal("100")

    set_counted(widget_line, Decimal("98"))      # 2 short
    set_counted(count.lines.get(item=other), Decimal("50"))  # spot on

    post_count(count)
    count.refresh_from_db()
    assert count.status == CountStatus.POSTED
    widget_line.refresh_from_db()
    assert widget_line.variance_quantity == Decimal("-2")
    assert widget_line.variance_value_minor == -2_000
    assert widget_line.movement is not None
    assert _inventory_gl_balance() == _stock_value()
    assert trial_balance().is_balanced


def test_cannot_set_or_post_twice():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("5"), unit_cost_minor=10_00, date=D)
    count = create_count(warehouse=wh, count_date=D)
    set_counted(count.lines.first(), Decimal("5"))
    post_count(count)
    with pytest.raises(CountStateError):
        post_count(count)
    with pytest.raises(CountStateError):
        set_counted(count.lines.first(), Decimal("4"))


def test_batch_traceability_report():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=10_00, date=D,
                  batch_no="LOT-A", expiry_date=dt.date(2027, 1, 31))
    receive_stock(item=item, warehouse=wh, quantity=Decimal("5"), unit_cost_minor=10_00, date=D,
                  batch_no="LOT-A", expiry_date=dt.date(2027, 1, 31))
    receive_stock(item=item, warehouse=wh, quantity=Decimal("8"), unit_cost_minor=10_00, date=D,
                  batch_no="LOT-B", expiry_date=dt.date(2026, 9, 30))

    rows = batches(warehouse_code="MAIN")
    by_batch = {r.batch_no: r for r in rows}
    assert Decimal(by_batch["LOT-A"].received_quantity) == Decimal("15")
    assert by_batch["LOT-B"].earliest_expiry == "2026-09-30"
    # Earliest expiry sorts first.
    assert rows[0].batch_no == "LOT-B"
