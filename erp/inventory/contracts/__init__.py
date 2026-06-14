"""Public contract for the inventory module.

The surface other modules (Sales, Purchasing, ...) may use: move stock via these services and react
to the stock events on the bus. Never import inventory's ORM models from outside the module.
"""
from __future__ import annotations

from ..events import STOCK_ISSUED, STOCK_RECEIVED, STOCK_TRANSFERRED
from ..services.stock import issue_stock, receive_stock, transfer_stock

__all__ = [
    "issue_stock",
    "receive_stock",
    "transfer_stock",
    "STOCK_RECEIVED",
    "STOCK_ISSUED",
    "STOCK_TRANSFERRED",
]
