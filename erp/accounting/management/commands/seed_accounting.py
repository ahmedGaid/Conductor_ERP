"""Seed a baseline Chart of Accounts + the current fiscal year with 12 open monthly periods.

Idempotent: re-running updates nothing it already created. For dev/demo use.
    .\\.venv\\Scripts\\python.exe manage.py seed_accounting
"""
from __future__ import annotations

import calendar
import datetime as dt

from django.core.management.base import BaseCommand
from django.db import transaction

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, CostCenter, FiscalYear, Period, TaxCode

# (code, name, type, is_postable, parent_code)
COA = [
    ("1", "Assets", AccountType.ASSET, False, None),
    ("1000", "Cash", AccountType.ASSET, True, "1"),
    ("1010", "Bank", AccountType.ASSET, True, "1"),
    ("1100", "Accounts Receivable", AccountType.ASSET, True, "1"),
    ("1190", "VAT Input (Recoverable)", AccountType.ASSET, True, "1"),
    ("1200", "Inventory", AccountType.ASSET, True, "1"),
    ("1500", "Fixed Assets", AccountType.ASSET, True, "1"),
    ("1590", "Accumulated Depreciation", AccountType.ASSET, True, "1"),
    ("2", "Liabilities", AccountType.LIABILITY, False, None),
    ("2000", "Accounts Payable", AccountType.LIABILITY, True, "2"),
    ("2100", "VAT Payable", AccountType.LIABILITY, True, "2"),
    ("2150", "Goods Received Not Invoiced", AccountType.LIABILITY, True, "2"),
    ("3", "Equity", AccountType.EQUITY, False, None),
    ("3000", "Share Capital", AccountType.EQUITY, True, "3"),
    ("3100", "Retained Earnings", AccountType.EQUITY, True, "3"),
    ("4", "Income", AccountType.INCOME, False, None),
    ("4000", "Sales Revenue", AccountType.INCOME, True, "4"),
    ("4090", "Sales Returns", AccountType.INCOME, True, "4"),
    ("4200", "Gain on Asset Disposal", AccountType.INCOME, True, "4"),
    ("5", "Expenses", AccountType.EXPENSE, False, None),
    ("5000", "Cost of Goods Sold", AccountType.EXPENSE, True, "5"),
    ("5100", "Rent Expense", AccountType.EXPENSE, True, "5"),
    ("5200", "Salaries Expense", AccountType.EXPENSE, True, "5"),
    ("5300", "Depreciation Expense", AccountType.EXPENSE, True, "5"),
    ("5400", "Loss on Asset Disposal", AccountType.EXPENSE, True, "5"),
    ("5900", "Inventory Adjustment", AccountType.EXPENSE, True, "5"),
    ("6100", "Bank Charges", AccountType.EXPENSE, True, "5"),
]


class Command(BaseCommand):
    help = "Seed a baseline Chart of Accounts and the current fiscal year/periods."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        cash_codes = {"1000", "1010"}  # Cash, Bank
        for code, name, type_, postable, parent_code in COA:
            parent = Account.objects.filter(code=parent_code).first() if parent_code else None
            Account.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "type": type_,
                    "is_postable": postable,
                    "is_cash": code in cash_codes,
                    "parent": parent,
                },
            )

        # VAT tax codes (Egypt standard 14%, plus a 0% exempt code).
        # Output (sales) VAT → 2100 VAT Payable; input (purchase) VAT → 1190 VAT Recoverable.
        for code, name, rate_bps in [("VAT14", "VAT 14%", 1400), ("VAT0", "Exempt / 0%", 0)]:
            TaxCode.objects.update_or_create(
                code=code,
                defaults={"name": name, "rate_bps": rate_bps, "output_account_code": "2100",
                          "input_account_code": "1190", "is_active": True},
            )

        # Reporting dimensions (cost centers) — departments to tag journal lines with.
        for code, name in [("CC-SALES", "Sales Dept"), ("CC-OPS", "Operations"), ("CC-ADMIN", "Administration")]:
            CostCenter.objects.update_or_create(code=code, defaults={"name": name, "is_active": True})

        year = dt.date.today().year
        fy, _ = FiscalYear.objects.update_or_create(
            code=str(year),
            defaults={
                "start_date": dt.date(year, 1, 1),
                "end_date": dt.date(year, 12, 31),
            },
        )
        for month in range(1, 13):
            last_day = calendar.monthrange(year, month)[1]
            Period.objects.update_or_create(
                code=f"{year}-{month:02d}",
                defaults={
                    "fiscal_year": fy,
                    "start_date": dt.date(year, month, 1),
                    "end_date": dt.date(year, month, last_day),
                    "status": "open",
                },
            )

        self.stdout.write(self.style.SUCCESS(f"accounting seeded: {len(COA)} accounts, FY {year}, 12 periods"))
