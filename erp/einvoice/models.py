"""Django discovers models here; definitions live in the domain layer (strict module layout)."""
from __future__ import annotations

from .domain.models import ETAInvoice, ETAStatus  # noqa: F401

__all__ = ["ETAInvoice", "ETAStatus"]
