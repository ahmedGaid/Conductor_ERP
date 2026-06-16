"""Test helpers: GL accounts, an open period, an in-stock item, a warehouse, and a customer."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, FiscalYear, Period, TaxCode
from erp.inventory.contracts import receive
from erp.inventory.domain.models import Item, Warehouse
from erp.sales.domain.models import Customer

ACCOUNTS = [
    ("1000", "Cash", AccountType.ASSET),
    ("1100", "Accounts Receivable", AccountType.ASSET),
    ("1200", "Inventory", AccountType.ASSET),
    ("2100", "VAT Payable", AccountType.LIABILITY),
    ("2150", "GRNI", AccountType.LIABILITY),
    ("4000", "Sales Revenue", AccountType.INCOME),
    ("4090", "Sales Returns", AccountType.INCOME),
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


def make_customer(code: str = "CUST1", credit_limit_minor: int = 0) -> Customer:
    return Customer.objects.create(code=code, name="Acme Corp", credit_limit_minor=credit_limit_minor)


def make_vat(code: str = "VAT14", rate_bps: int = 1400) -> TaxCode:
    return TaxCode.objects.create(code=code, name=f"VAT {rate_bps / 100:.0f}%",
                                  rate_bps=rate_bps, output_account_code="2100")


def stocked(item: Item, warehouse: Warehouse, qty="20", unit_cost_minor=100_00) -> None:
    receive(item.sku, warehouse.code, Decimal(qty), unit_cost_minor, date=DATE)
