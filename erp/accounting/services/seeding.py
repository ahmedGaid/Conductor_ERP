"""Baseline accounting provisioning.

The chart of accounts, current fiscal year + 12 monthly periods, VAT tax codes and reporting cost
centers a brand-new company needs before it can post anything. This is the single source of truth:
the ``seed_accounting`` management command (dev/demo) and the first-run setup wizard both call
``seed_baseline_accounting`` — neither builds accounts by hand.

Idempotent: every row is ``update_or_create``, so re-running changes nothing it already created.
"""
from __future__ import annotations

import calendar
import datetime as dt
from decimal import Decimal

from django.db import transaction

from ..domain.accounts import AccountType
from ..domain.models import Account, CostCenter, FiscalYear, Period, TaxCode

# (code, name, name_ar, type, is_postable, parent_code)
# Arabic names are the canonical Egyptian accounting terms — one word per concept, matching the
# Identity System lexicon. Both languages ship seeded; nothing is left English-only on an Arabic screen.
COA = [
    ("1", "Assets", "الأصول", AccountType.ASSET, False, None),
    ("1000", "Cash", "النقدية", AccountType.ASSET, True, "1"),
    ("1010", "Bank", "البنك", AccountType.ASSET, True, "1"),
    ("1100", "Accounts Receivable", "الذمم المدينة", AccountType.ASSET, True, "1"),
    ("1190", "VAT Input (Recoverable)", "ضريبة القيمة المضافة — مدخلات", AccountType.ASSET, True, "1"),
    ("1200", "Inventory", "المخزون", AccountType.ASSET, True, "1"),
    ("1500", "Fixed Assets", "الأصول الثابتة", AccountType.ASSET, True, "1"),
    ("1590", "Accumulated Depreciation", "مجمع الإهلاك", AccountType.ASSET, True, "1"),
    ("2", "Liabilities", "الالتزامات", AccountType.LIABILITY, False, None),
    ("2000", "Accounts Payable", "الذمم الدائنة", AccountType.LIABILITY, True, "2"),
    ("2100", "VAT Payable", "ضريبة القيمة المضافة المستحقة", AccountType.LIABILITY, True, "2"),
    ("2150", "Goods Received Not Invoiced", "بضاعة واردة بدون فاتورة", AccountType.LIABILITY, True, "2"),
    ("3", "Equity", "حقوق الملكية", AccountType.EQUITY, False, None),
    ("3000", "Share Capital", "رأس المال", AccountType.EQUITY, True, "3"),
    ("3100", "Retained Earnings", "الأرباح المحتجزة", AccountType.EQUITY, True, "3"),
    ("3110", "Inventory Opening Balance", "رصيد المخزون الافتتاحي", AccountType.EQUITY, True, "3"),
    ("4", "Income", "الإيرادات", AccountType.INCOME, False, None),
    ("4000", "Sales Revenue", "إيرادات المبيعات", AccountType.INCOME, True, "4"),
    ("4090", "Sales Returns", "مردودات المبيعات", AccountType.INCOME, True, "4"),
    ("4200", "Gain on Asset Disposal", "أرباح بيع الأصول", AccountType.INCOME, True, "4"),
    ("5", "Expenses", "المصروفات", AccountType.EXPENSE, False, None),
    ("5000", "Cost of Goods Sold", "تكلفة البضاعة المباعة", AccountType.EXPENSE, True, "5"),
    ("5100", "Rent Expense", "مصروف الإيجار", AccountType.EXPENSE, True, "5"),
    ("5200", "Salaries Expense", "مصروف الرواتب", AccountType.EXPENSE, True, "5"),
    ("5300", "Depreciation Expense", "مصروف الإهلاك", AccountType.EXPENSE, True, "5"),
    ("5400", "Loss on Asset Disposal", "خسائر بيع الأصول", AccountType.EXPENSE, True, "5"),
    ("5900", "Inventory Adjustment", "تسوية المخزون", AccountType.EXPENSE, True, "5"),
    ("6100", "Bank Charges", "مصاريف بنكية", AccountType.EXPENSE, True, "5"),
]

CASH_CODES = {"1000", "1010"}  # Cash, Bank

# The standard sales-VAT code. Its rate is the company's headline VAT rate; the code id stays
# stable (sales/purchasing reference it as a string) even when the rate is adjusted in setup.
STANDARD_VAT_CODE = "VAT14"


@transaction.atomic
def seed_baseline_accounting() -> dict:
    """Provision the baseline COA + fiscal year/periods + VAT codes + cost centers (idempotent)."""
    for code, name, name_ar, type_, postable, parent_code in COA:
        parent = Account.objects.filter(code=parent_code).first() if parent_code else None
        Account.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "name_ar": name_ar,
                "type": type_,
                "is_postable": postable,
                "is_cash": code in CASH_CODES,
                "parent": parent,
            },
        )

    # VAT tax codes (Egypt standard 14%, plus a 0% exempt code).
    # Output (sales) VAT → 2100 VAT Payable; input (purchase) VAT → 1190 VAT Recoverable.
    # get_or_create (not update_or_create) so a rate the setup wizard already customised survives
    # a re-seed of the chart of accounts.
    for code, name, name_ar, rate_bps in [
        ("VAT14", "VAT 14%", "ضريبة القيمة المضافة 14%", 1400),
        ("VAT0", "Exempt / 0%", "معفاة / 0%", 0),
    ]:
        TaxCode.objects.get_or_create(
            code=code,
            defaults={"name": name, "name_ar": name_ar, "rate_bps": rate_bps,
                      "output_account_code": "2100",
                      "input_account_code": "1190", "is_active": True},
        )

    # Reporting dimensions (cost centers) — departments to tag journal lines with.
    for code, name, name_ar in [
        ("CC-SALES", "Sales Dept", "إدارة المبيعات"),
        ("CC-OPS", "Operations", "العمليات"),
        ("CC-ADMIN", "Administration", "الإدارة"),
    ]:
        CostCenter.objects.update_or_create(
            code=code, defaults={"name": name, "name_ar": name_ar, "is_active": True}
        )

    year = dt.date.today().year
    fy, _ = FiscalYear.objects.update_or_create(
        code=str(year),
        defaults={"start_date": dt.date(year, 1, 1), "end_date": dt.date(year, 12, 31)},
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
    return baseline_summary()


def baseline_summary() -> dict:
    """Current baseline state — what the setup wizard reads to know if the COA is in place."""
    count = Account.objects.count()
    return {"seeded": count > 0, "accounts": count}


def get_standard_vat_rate_bps() -> int:
    """The standard sales-VAT rate in basis points (1400 == 14%); the Egypt default if unset."""
    tc = TaxCode.objects.filter(code=STANDARD_VAT_CODE).first()
    return tc.rate_bps if tc else 1400


def set_standard_vat_rate(rate_bps: int) -> int:
    """Set the standard sales-VAT rate (basis points). Upserts the code so it works pre- or
    post-COA-seed; the code id stays stable while the display name tracks the rate."""
    rate_bps = max(0, int(rate_bps))
    pct = (Decimal(rate_bps) / 100).normalize()
    TaxCode.objects.update_or_create(
        code=STANDARD_VAT_CODE,
        defaults={"name": f"VAT {pct}%", "name_ar": f"ضريبة القيمة المضافة {pct}%",
                  "rate_bps": rate_bps, "output_account_code": "2100",
                  "input_account_code": "1190", "is_active": True},
    )
    return rate_bps
