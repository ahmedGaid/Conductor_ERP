"""Weighted-average costing — pure functions over (quantity, value) in minor units.

Value is carried as an integer minor-unit total alongside a Decimal quantity. The average unit cost
is always value / quantity; we never store a rounded average (that would drift). When stock is
issued, its cost is taken *proportionally* from the remaining value, so the running value stays exact.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def _round_minor(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def receipt_value(quantity: Decimal, unit_cost_minor: int) -> int:
    """Total minor-unit value added by receiving `quantity` at `unit_cost_minor` each."""
    return _round_minor(Decimal(quantity) * Decimal(unit_cost_minor))


def issue_value(on_hand_qty: Decimal, on_hand_value: int, issue_qty: Decimal) -> int:
    """Minor-unit cost of issuing `issue_qty`, taken proportionally from the current value.

    Issuing the entire on-hand quantity removes the entire value exactly (no residual).
    """
    if issue_qty >= on_hand_qty:
        return on_hand_value
    portion = Decimal(on_hand_value) * Decimal(issue_qty) / Decimal(on_hand_qty)
    return _round_minor(portion)


def average_cost_minor(quantity: Decimal, value_minor: int) -> int:
    """Weighted-average unit cost in minor units (for display); 0 when no stock."""
    if quantity == 0:
        return 0
    return _round_minor(Decimal(value_minor) / Decimal(quantity))
