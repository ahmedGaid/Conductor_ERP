"""Public contract for the purchasing module — PO lifecycle services + event names."""
from __future__ import annotations

from dataclasses import dataclass

from ..events import PO_BILLED, PO_CONFIRMED, PO_PAID, PO_RECEIVED
from ..repositories import suppliers as _suppliers
from ..services.orders import (
    POLineInput,
    bill_order,
    confirm_order,
    create_order,
    pay_order,
    receive_order,
)


@dataclass(frozen=True)
class SupplierInfo:
    code: str
    name: str
    is_active: bool


def find_supplier(code: str) -> SupplierInfo | None:
    s = _suppliers.by_code(code)
    if s is None:
        return None
    return SupplierInfo(code=s.code, name=s.name, is_active=s.is_active)


def list_suppliers() -> list[SupplierInfo]:
    """Light snapshot of all active suppliers (for cross-module lookups/matching)."""
    return [
        SupplierInfo(code=s.code, name=s.name, is_active=s.is_active)
        for s in _suppliers.filter(is_active=True)
    ]


__all__ = [
    "SupplierInfo",
    "find_supplier",
    "list_suppliers",
    "POLineInput",
    "create_order",
    "confirm_order",
    "receive_order",
    "bill_order",
    "pay_order",
    "PO_CONFIRMED",
    "PO_RECEIVED",
    "PO_BILLED",
    "PO_PAID",
]
