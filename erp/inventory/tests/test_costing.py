"""Weighted-average costing math (pure, no DB)."""
from __future__ import annotations

from decimal import Decimal

from erp.inventory.domain import costing


def test_receipt_value_rounds_to_minor_units():
    assert costing.receipt_value(Decimal("3"), 100_00) == 300_00
    assert costing.receipt_value(Decimal("2.5"), 101) == 253  # 2.5 * 1.01 = 2.525 -> 253 minor


def test_issue_value_is_proportional():
    # 20 units worth 300.00; issue 5 -> a quarter of the value.
    assert costing.issue_value(Decimal("20"), 300_00, Decimal("5")) == 75_00


def test_issuing_all_removes_all_value():
    assert costing.issue_value(Decimal("7"), 123_45, Decimal("7")) == 123_45
    # even if asked for slightly more, the whole value leaves (guarded elsewhere)
    assert costing.issue_value(Decimal("7"), 123_45, Decimal("9")) == 123_45


def test_average_cost():
    assert costing.average_cost_minor(Decimal("20"), 300_00) == 15_00
    assert costing.average_cost_minor(Decimal("0"), 0) == 0
