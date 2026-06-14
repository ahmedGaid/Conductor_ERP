"""Inventory error catalog (INV-NNN)."""
from __future__ import annotations

from erp.core.errors import AppError


class InsufficientStockError(AppError):
    code = "INV-001"
    status_code = 422
    message = "Insufficient stock on hand for this issue"


class InvalidQuantityError(AppError):
    code = "INV-002"
    status_code = 422
    message = "Quantity must be greater than zero"


class NonStockItemError(AppError):
    code = "INV-003"
    status_code = 422
    message = "Only stock items can have stock movements"


class SameWarehouseTransferError(AppError):
    code = "INV-004"
    status_code = 422
    message = "Transfer source and destination must differ"
