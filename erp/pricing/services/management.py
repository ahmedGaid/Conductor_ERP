"""Price-list management helpers — invariants that the API and seeds both rely on."""
from __future__ import annotations

from erp.core.repository import atomic

from ..domain.models import PriceList


def set_single_default(price_list: PriceList) -> None:
    """Make ``price_list`` the one default, clearing the flag on every other list (atomic)."""
    with atomic():
        PriceList.objects.exclude(pk=price_list.pk).filter(is_default=True).update(is_default=False)
        if not price_list.is_default:
            price_list.is_default = True
            price_list.save(update_fields=["is_default"])


def ensure_default_price_list(code: str = "STD", name: str = "Standard prices") -> PriceList:
    """Return the active default list, creating an empty one if the org has none yet (idempotent)."""
    existing = PriceList.objects.filter(is_default=True, is_active=True).first()
    if existing is not None:
        return existing
    by_code = PriceList.objects.filter(code=code).first()
    if by_code is not None:
        set_single_default(by_code)
        return by_code
    price_list = PriceList.objects.create(code=code, name=name, is_default=True)
    return price_list
