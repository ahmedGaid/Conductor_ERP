"""Public contract for the pricing module.

Other modules (sales: order/quotation line prefill) resolve a price through this contract using
business keys only — customer ``code``, item ``sku`` — never pricing ORM instances. The resolver is
tax-agnostic; the caller backs VAT out of a tax-inclusive result.
"""
from __future__ import annotations

from .. import services  # noqa: F401  (ensures the services package imports cleanly)
from ..services.resolve import PriceResolution, resolve_unit_price

__all__ = ["PriceResolution", "resolve_unit_price"]
