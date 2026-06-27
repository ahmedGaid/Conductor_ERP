"""Price resolution — the precedence engine.

Given a customer, an item, a date and (optionally) a quantity, return the best applicable price:

  1. a customer-specific item price (negotiated)        — `CustomerItemPrice`
  2. the customer's assigned price list                 — `CustomerPriceList` -> `PriceListLine`
  3. the active default price list                      — `PriceList(is_default=True)`
  4. nothing (caller leaves the line blank)

Within a tier, candidates are filtered to the requested currency (price-list tiers only), effective on
the date, and reachable by the quantity break; the winner is the highest break, then the latest
``valid_from``, then the lowest price. Pure and deterministic — no I/O beyond the repositories, no
randomness — so it is safe to unit-test and to call from a request path. The resolver is **tax-agnostic**:
it returns the stored price plus a ``tax_inclusive`` flag; backing VAT out to a net line is the caller's
job (the pricing API does it with the order's tax code). See DECISIONS.md "Pricing engine — Oracle-EBS-core".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ..repositories import (
    customer_item_prices,
    customer_price_lists,
    price_list_lines,
    price_lists,
)


@dataclass(frozen=True)
class PriceResolution:
    unit_price_minor: int
    tax_inclusive: bool
    source: str  # "customer_item" | "customer_list" | "default_list"
    price_list_code: str | None


def _effective(row, on: date) -> bool:
    if row.valid_from and row.valid_from > on:
        return False
    if row.valid_to and row.valid_to < on:
        return False
    return True


def _best(rows: list, on: date, qty: Decimal):
    """Pick the best candidate: highest qty-break ≤ qty and effective on `on`, then latest start,
    then cheapest. Returns the winning row or None."""
    candidates = [r for r in rows if r.min_quantity <= qty and _effective(r, on)]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda r: (r.min_quantity, r.valid_from or date.min, -r.unit_price_minor),
    )


def resolve_unit_price(
    customer_code: str,
    item_sku: str,
    *,
    on: date | None = None,
    quantity: Decimal | None = None,
    currency: str = "EGP",
) -> PriceResolution | None:
    """Resolve the best unit price for (customer, item). Returns None when nothing applies."""
    on = on or date.today()
    qty = Decimal(quantity) if quantity is not None else Decimal(0)

    # Tier 1 — negotiated customer/item price (no currency dimension; treated as the order currency).
    override = _best(list(customer_item_prices.for_customer_item(customer_code, item_sku)), on, qty)
    if override is not None:
        return PriceResolution(override.unit_price_minor, override.tax_inclusive, "customer_item", None)

    # Tier 2 — the customer's assigned price list (currency must match).
    assignment = customer_price_lists.for_customer(customer_code)
    if assignment is not None and assignment.price_list.currency == currency and assignment.price_list.is_active:
        line = _best(list(price_list_lines.for_item(assignment.price_list, item_sku)), on, qty)
        if line is not None:
            return PriceResolution(
                line.unit_price_minor, assignment.price_list.tax_inclusive, "customer_list", assignment.price_list.code
            )

    # Tier 3 — the active default price list (currency must match).
    default = price_lists.default()
    if default is not None and default.currency == currency:
        line = _best(list(price_list_lines.for_item(default, item_sku)), on, qty)
        if line is not None:
            return PriceResolution(line.unit_price_minor, default.tax_inclusive, "default_list", default.code)

    return None
