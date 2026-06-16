"""Tax-code computation + the VAT return report."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, FiscalYear, Period, TaxCode
from erp.accounting.services import (
    JournalInput,
    LineInput,
    compute_tax,
    find_tax_code,
    post_journal,
    vat_return,
)

pytestmark = pytest.mark.django_db


def _books():
    Account.objects.create(code="1100", name="AR", type=AccountType.ASSET)
    Account.objects.create(code="1190", name="VAT Input", type=AccountType.ASSET)
    Account.objects.create(code="2000", name="AP", type=AccountType.LIABILITY)
    Account.objects.create(code="2100", name="VAT Payable", type=AccountType.LIABILITY)
    Account.objects.create(code="4000", name="Revenue", type=AccountType.INCOME)
    fy, _ = FiscalYear.objects.get_or_create(
        code="2026", defaults={"start_date": dt.date(2026, 1, 1), "end_date": dt.date(2026, 12, 31)}
    )
    Period.objects.create(fiscal_year=fy, code="2026", start_date=dt.date(2026, 1, 1),
                          end_date=dt.date(2026, 12, 31), status="open")
    TaxCode.objects.create(code="VAT14", name="VAT 14%", rate_bps=1400,
                           output_account_code="2100", input_account_code="1190")


def test_compute_tax_rounds_half_up():
    _books()
    assert compute_tax(1000_00, "VAT14") == 140_00      # 14% of 1000.00
    assert compute_tax(100_03, "VAT14") == 14_00        # 14.0042 -> 14.00
    assert compute_tax(100_00, "UNKNOWN") == 0          # unknown code → 0
    assert find_tax_code("VAT14").rate_bps == 1400


def test_vat_return_nets_output_minus_reversals():
    _books()
    # An invoice: Cr VAT 140.00 (output).
    post_journal(JournalInput(
        date=dt.date(2026, 6, 1), source="sales", reference="INV1", memo="invoice",
        lines=[LineInput(account_code="1100", debit=1140_00),
               LineInput(account_code="4000", credit=1000_00),
               LineInput(account_code="2100", credit=140_00)],
    ))
    # A credit note: Dr VAT 40.00 (reversal).
    post_journal(JournalInput(
        date=dt.date(2026, 6, 10), source="sales", reference="CN1", memo="return",
        lines=[LineInput(account_code="2100", debit=40_00),
               LineInput(account_code="1100", credit=40_00)],
    ))

    vr = vat_return(dt.date(2026, 6, 1), dt.date(2026, 6, 30))
    assert vr.output_vat == 140_00
    assert vr.reversals == 40_00
    assert vr.input_vat == 0
    assert vr.net_payable == 100_00
    assert vr.is_payable


def test_vat_return_subtracts_recoverable_input_vat():
    _books()
    # Output VAT on a sale: Cr VAT Payable 140.00.
    post_journal(JournalInput(
        date=dt.date(2026, 6, 1), source="sales", reference="INV1", memo="invoice",
        lines=[LineInput(account_code="1100", debit=1140_00),
               LineInput(account_code="4000", credit=1000_00),
               LineInput(account_code="2100", credit=140_00)],
    ))
    # Input VAT on a purchase bill: Dr VAT Input 90.00 (recoverable).
    post_journal(JournalInput(
        date=dt.date(2026, 6, 5), source="purchasing", reference="BILL1", memo="bill",
        lines=[LineInput(account_code="1190", debit=90_00),
               LineInput(account_code="2000", credit=90_00)],
    ))

    vr = vat_return(dt.date(2026, 6, 1), dt.date(2026, 6, 30))
    assert vr.output_vat == 140_00
    assert vr.input_vat == 90_00
    assert vr.net_payable == 50_00      # 140 output − 90 input
    assert vr.is_payable
