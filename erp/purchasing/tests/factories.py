"""Test helpers: GL accounts, an open period, an item, a warehouse, and a supplier."""
from __future__ import annotations

import datetime as dt

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, FiscalYear, Period
from erp.inventory.domain.models import Item, Warehouse
from erp.purchasing.domain.models import Supplier

ACCOUNTS = [
    ("1000", "Cash", AccountType.ASSET),
    ("1200", "Inventory", AccountType.ASSET),
    ("2000", "Accounts Payable", AccountType.LIABILITY),
    ("2150", "GRNI", AccountType.LIABILITY),
    ("5000", "Cost of Goods Sold", AccountType.EXPENSE),
]

DATE = dt.date(2026, 6, 15)


def make_books() -> None:
    for code, name, type_ in ACCOUNTS:
        Account.objects.create(code=code, name=name, type=type_)
    fy, _ = FiscalYear.objects.get_or_create(
        code="2026",
        defaults={"start_date": dt.date(2026, 1, 1), "end_date": dt.date(2026, 12, 31)},
    )
    Period.objects.create(
        fiscal_year=fy, code="2026", start_date=dt.date(2026, 1, 1),
        end_date=dt.date(2026, 12, 31), status="open",
    )


def make_item(sku: str = "WIDGET") -> Item:
    return Item.objects.create(sku=sku, name="Widget", type="stock")


def make_warehouse(code: str = "MAIN") -> Warehouse:
    return Warehouse.objects.create(code=code, name="Main")


def make_supplier(code: str = "SUP1") -> Supplier:
    return Supplier.objects.create(code=code, name="Globex Supplies")
