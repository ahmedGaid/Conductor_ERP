"""Test helpers: the GL accounts inventory posts to, an open period, and an item + warehouses."""
from __future__ import annotations

import datetime as dt

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, FiscalYear, Period
from erp.inventory.domain.models import Item, Warehouse


def make_gl() -> None:
    Account.objects.create(code="1200", name="Inventory", type=AccountType.ASSET)
    Account.objects.create(code="5000", name="Cost of Goods Sold", type=AccountType.EXPENSE)
    Account.objects.create(code="2150", name="GRNI", type=AccountType.LIABILITY)
    fy, _ = FiscalYear.objects.get_or_create(
        code="2026",
        defaults={"start_date": dt.date(2026, 1, 1), "end_date": dt.date(2026, 12, 31)},
    )
    # A period spanning the whole year so any test date posts cleanly.
    Period.objects.create(
        fiscal_year=fy, code="2026", start_date=dt.date(2026, 1, 1),
        end_date=dt.date(2026, 12, 31), status="open",
    )


def make_item(sku: str = "WIDGET", **kw) -> Item:
    return Item.objects.create(sku=sku, name=kw.pop("name", "Widget"), type="stock", **kw)


def make_warehouse(code: str = "MAIN", name: str = "Main Warehouse") -> Warehouse:
    return Warehouse.objects.create(code=code, name=name)
