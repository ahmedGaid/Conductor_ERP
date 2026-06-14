"""Domain events published by the inventory module (consumed via the core event bus)."""
from __future__ import annotations

STOCK_RECEIVED = "inventory.StockReceived"
STOCK_ISSUED = "inventory.StockIssued"
STOCK_TRANSFERRED = "inventory.StockTransferred"
