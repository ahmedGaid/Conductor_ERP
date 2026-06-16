"""Fixed assets — acquisition, straight-line depreciation, disposal gain/loss.

Every flow must keep the trial balance balanced and the asset sub-ledger in step with the GL.
"""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, AssetStatus, FixedAsset
from erp.accounting.errors import AssetStateError, InvalidAssetError
from erp.accounting.services import (
    AssetInput,
    acquire_asset,
    asset_register,
    dispose_asset,
    run_depreciation,
    trial_balance,
)

from .factories import make_period

pytestmark = pytest.mark.django_db

D = dt.date(2026, 6, 10)

# Accounts the fixed-asset flows touch.
_COA = [
    ("1000", "Cash", AccountType.ASSET),
    ("1500", "Fixed Assets", AccountType.ASSET),
    ("1590", "Accumulated Depreciation", AccountType.ASSET),
    ("4200", "Gain on Asset Disposal", AccountType.INCOME),
    ("5300", "Depreciation Expense", AccountType.EXPENSE),
    ("5400", "Loss on Asset Disposal", AccountType.EXPENSE),
]


def _seed_coa():
    for code, name, type_ in _COA:
        Account.objects.create(code=code, name=name, type=type_)
    make_period("2026-06")
    make_period("2026-07")


def _acquire(**kw):
    defaults = dict(
        code="FA-001", name="Delivery Van", acquisition_date=D,
        cost_minor=120_000_00, salvage_minor=0, useful_life_months=60,
    )
    defaults.update(kw)
    return acquire_asset(AssetInput(**defaults))


def _balanced() -> bool:
    return trial_balance().is_balanced


def test_acquire_posts_and_capitalises():
    _seed_coa()
    asset = _acquire()
    assert asset.acquire_journal_number
    assert asset.net_book_value_minor == 120_000_00
    tb = {r.account_code: r.balance for r in trial_balance().rows}
    assert tb["1500"] == 120_000_00       # asset debit balance
    assert tb["1000"] == -120_000_00      # cash credited
    assert _balanced()


def test_straight_line_monthly_charge():
    _seed_coa()
    _acquire(cost_minor=60_000_00, salvage_minor=0, useful_life_months=60)  # 1,000.00/mo
    result = run_depreciation("2026-06", dt.date(2026, 6, 30))
    assert len(result.entries) == 1
    assert result.total_minor == 1_000_00
    asset = FixedAsset.objects.get(code="FA-001")
    assert asset.accumulated_depreciation_minor == 1_000_00
    assert asset.months_depreciated == 1
    assert asset.net_book_value_minor == 59_000_00
    assert _balanced()


def test_depreciation_is_idempotent_per_period():
    _seed_coa()
    _acquire(cost_minor=60_000_00, useful_life_months=60)
    run_depreciation("2026-06", dt.date(2026, 6, 30))
    second = run_depreciation("2026-06", dt.date(2026, 6, 30))  # same period again
    assert second.total_minor == 0
    assert FixedAsset.objects.get(code="FA-001").accumulated_depreciation_minor == 1_000_00


def test_salvage_is_never_depreciated_below():
    from erp.accounting.domain.models import FiscalYear, Period
    _seed_coa()
    # cost 1,000.00, salvage 100.00, life 3 months → depreciable 900.00, 300.00/mo.
    _acquire(cost_minor=1_000_00, salvage_minor=100_00, useful_life_months=3)
    fy = FiscalYear.objects.get(code="2026")
    for month in range(6, 11):  # run five periods — more than the 3-month life
        code = f"2026-{month:02d}"
        Period.objects.get_or_create(
            code=code,
            defaults={"fiscal_year": fy, "start_date": dt.date(2026, month, 1),
                      "end_date": dt.date(2026, month, 28), "status": "open"},
        )
        run_depreciation(code, dt.date(2026, month, 28))
    asset = FixedAsset.objects.get(code="FA-001")
    assert asset.accumulated_depreciation_minor == 900_00  # exactly depreciable
    assert asset.net_book_value_minor == 100_00            # == salvage, never below
    assert _balanced()


def test_dispose_with_gain():
    _seed_coa()
    _acquire(cost_minor=60_000_00, useful_life_months=60)
    run_depreciation("2026-06", dt.date(2026, 6, 30))  # NBV now 59,000.00
    asset = FixedAsset.objects.get(code="FA-001")
    dispose_asset(asset, disposed_date=dt.date(2026, 6, 30), proceeds_minor=62_000_00)
    asset.refresh_from_db()
    assert asset.status == AssetStatus.DISPOSED
    assert asset.disposal_gain_loss_minor == 3_000_00  # 62,000 − 59,000 NBV
    tb = {r.account_code: r.balance for r in trial_balance().rows}
    assert tb.get("4200") == 3_000_00  # gain (income, credit-normal → positive signed)
    assert tb.get("1500") == 0         # asset cost fully derecognised (nets to zero)
    assert _balanced()


def test_dispose_with_loss():
    _seed_coa()
    _acquire(cost_minor=60_000_00, useful_life_months=60)
    run_depreciation("2026-06", dt.date(2026, 6, 30))  # NBV 59,000.00
    asset = FixedAsset.objects.get(code="FA-001")
    dispose_asset(asset, disposed_date=dt.date(2026, 6, 30), proceeds_minor=50_000_00)
    asset.refresh_from_db()
    assert asset.disposal_gain_loss_minor == -9_000_00
    tb = {r.account_code: r.balance for r in trial_balance().rows}
    assert tb.get("5400") == 9_000_00  # loss (expense, debit-normal)
    assert _balanced()


def test_dispose_twice_rejected():
    _seed_coa()
    _acquire()
    asset = FixedAsset.objects.get(code="FA-001")
    dispose_asset(asset, disposed_date=D, proceeds_minor=0)
    asset.refresh_from_db()
    with pytest.raises(AssetStateError):
        dispose_asset(asset, disposed_date=D, proceeds_minor=0)


def test_invalid_salvage_rejected():
    _seed_coa()
    with pytest.raises(InvalidAssetError):
        _acquire(cost_minor=1_000_00, salvage_minor=1_000_00)  # salvage == cost


def test_asset_register_totals():
    _seed_coa()
    _acquire(code="FA-001", cost_minor=60_000_00, useful_life_months=60)
    _acquire(code="FA-002", name="Laptop", cost_minor=30_000_00, useful_life_months=30)
    run_depreciation("2026-06", dt.date(2026, 6, 30))
    reg = asset_register()
    assert reg.total_cost == 90_000_00
    assert reg.total_accumulated == 2_000_00       # 1,000 + 1,000
    assert reg.total_nbv == 88_000_00
