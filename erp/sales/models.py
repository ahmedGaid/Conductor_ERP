"""Django discovers models here; definitions live in the domain layer (strict module layout)."""
from __future__ import annotations

from .domain.models import (  # noqa: F401
    Customer,
    OrderStatus,
    SalesOrder,
    SalesOrderLine,
)

__all__ = ["Customer", "OrderStatus", "SalesOrder", "SalesOrderLine"]
