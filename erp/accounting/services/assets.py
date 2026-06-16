"""Fixed-asset sub-ledger: acquisition, straight-line depreciation, and disposal.

Every money movement posts through ``post_journal`` (the one double-entry invariant point), so the
asset register, the GL, and the trial balance can never diverge. Amounts are integer **minor units**.

GL mapping:
- **acquire**  → Dr Fixed Assets (1500) / Cr Cash|AP (the funding account)
- **depreciate** (monthly) → Dr Depreciation Expense (5300) / Cr Accumulated Depreciation (1590)
- **dispose**  → Cr Fixed Assets (cost), Dr Accumulated Depreciation (booked), Dr Cash (proceeds),
  with the balancing line a gain (Cr 4200) or loss (Dr 5400) versus net book value.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from ..domain.models import AssetStatus, DepreciationEntry, FixedAsset
from ..errors import AssetStateError, InvalidAssetError
from .posting import JournalInput, LineInput, post_journal

# Disposal gain/loss accounts (seeded in seed_accounting).
GAIN_ON_DISPOSAL_CODE = "4200"
LOSS_ON_DISPOSAL_CODE = "5400"


@dataclass
class AssetInput:
    code: str
    name: str
    acquisition_date: object       # datetime.date
    cost_minor: int
    useful_life_months: int
    in_service_date: object | None = None
    category: str = ""
    salvage_minor: int = 0
    funding_account_code: str = "1000"  # Cash by default; e.g. 2000 AP for a credit purchase
    asset_account_code: str = "1500"
    accumulated_account_code: str = "1590"
    expense_account_code: str = "5300"


def _monthly_charge(asset: FixedAsset) -> int:
    """Straight-line charge for one month, never taking accumulated past depreciable cost."""
    remaining = asset.depreciable_minor - asset.accumulated_depreciation_minor
    if remaining <= 0:
        return 0
    standard = round(asset.depreciable_minor / asset.useful_life_months)
    # The final period trues up so total depreciation == cost − salvage exactly.
    return min(standard, remaining)


@transaction.atomic
def acquire_asset(data: AssetInput, actor=None) -> FixedAsset:
    """Capitalise an asset and post Dr Fixed Assets / Cr funding account."""
    if data.cost_minor <= 0:
        raise InvalidAssetError("cost must be positive")
    if data.useful_life_months <= 0:
        raise InvalidAssetError("useful life (months) must be positive")
    if data.salvage_minor < 0 or data.salvage_minor >= data.cost_minor:
        raise InvalidAssetError("salvage must be between 0 and the cost")

    in_service = data.in_service_date or data.acquisition_date
    asset = FixedAsset.objects.create(
        code=data.code,
        name=data.name,
        category=data.category,
        acquisition_date=data.acquisition_date,
        in_service_date=in_service,
        cost_minor=data.cost_minor,
        salvage_minor=data.salvage_minor,
        useful_life_months=data.useful_life_months,
        asset_account_code=data.asset_account_code,
        accumulated_account_code=data.accumulated_account_code,
        expense_account_code=data.expense_account_code,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    entry = post_journal(
        JournalInput(
            date=data.acquisition_date,
            memo=f"Acquire fixed asset {asset.code} — {asset.name}",
            reference=asset.code,
            source="accounting.assets",
            lines=[
                LineInput(account_code=data.asset_account_code, debit=data.cost_minor),
                LineInput(account_code=data.funding_account_code, credit=data.cost_minor),
            ],
        ),
        actor=actor,
    )
    asset.acquire_journal_number = entry.number
    asset.save(update_fields=["acquire_journal_number"])
    return asset


@dataclass
class DepreciationRunResult:
    period_code: str
    entries: list[DepreciationEntry]
    total_minor: int


@transaction.atomic
def run_depreciation(period_code: str, date, actor=None) -> DepreciationRunResult:
    """Book one month of straight-line depreciation for every active asset.

    Idempotent per (asset, period): an asset already depreciated in this period is skipped, so a
    re-run posts nothing. Fully-depreciated and disposed assets are skipped.
    """
    already = set(
        DepreciationEntry.objects.filter(period_code=period_code).values_list("asset_id", flat=True)
    )
    entries: list[DepreciationEntry] = []
    total = 0
    assets = FixedAsset.objects.filter(status=AssetStatus.ACTIVE).order_by("code")
    for asset in assets:
        if asset.id in already:
            continue
        charge = _monthly_charge(asset)
        if charge <= 0:
            continue
        entry = post_journal(
            JournalInput(
                date=date,
                period_code=period_code,
                memo=f"Depreciation {period_code} — {asset.code}",
                reference=asset.code,
                source="accounting.assets",
                lines=[
                    LineInput(account_code=asset.expense_account_code, debit=charge),
                    LineInput(account_code=asset.accumulated_account_code, credit=charge),
                ],
            ),
            actor=actor,
        )
        asset.accumulated_depreciation_minor += charge
        asset.months_depreciated += 1
        asset.save(update_fields=["accumulated_depreciation_minor", "months_depreciated"])
        dep = DepreciationEntry.objects.create(
            asset=asset, period_code=period_code, amount_minor=charge, journal_number=entry.number
        )
        entries.append(dep)
        total += charge
    return DepreciationRunResult(period_code=period_code, entries=entries, total_minor=total)


@transaction.atomic
def dispose_asset(asset: FixedAsset, *, disposed_date, proceeds_minor: int,
                  proceeds_account_code: str = "1000", actor=None) -> FixedAsset:
    """Derecognise an asset: remove cost + accumulated depreciation, book proceeds and gain/loss."""
    if asset.status != AssetStatus.ACTIVE:
        raise AssetStateError(data={"asset": asset.code, "status": asset.status})
    if proceeds_minor < 0:
        raise InvalidAssetError("proceeds cannot be negative")

    cost = asset.cost_minor
    accumulated = asset.accumulated_depreciation_minor
    nbv = cost - accumulated
    gain_loss = proceeds_minor - nbv  # + gain / − loss

    lines = [
        LineInput(account_code=asset.asset_account_code, credit=cost,
                  memo=f"Derecognise {asset.code}"),
    ]
    if accumulated > 0:
        lines.append(LineInput(account_code=asset.accumulated_account_code, debit=accumulated))
    if proceeds_minor > 0:
        lines.append(LineInput(account_code=proceeds_account_code, debit=proceeds_minor))
    if gain_loss > 0:
        lines.append(LineInput(account_code=GAIN_ON_DISPOSAL_CODE, credit=gain_loss))
    elif gain_loss < 0:
        lines.append(LineInput(account_code=LOSS_ON_DISPOSAL_CODE, debit=-gain_loss))

    entry = post_journal(
        JournalInput(
            date=disposed_date,
            memo=f"Dispose fixed asset {asset.code} — {asset.name}",
            reference=asset.code,
            source="accounting.assets",
            lines=lines,
        ),
        actor=actor,
    )
    asset.status = AssetStatus.DISPOSED
    asset.disposed_date = disposed_date
    asset.disposal_proceeds_minor = proceeds_minor
    asset.disposal_gain_loss_minor = gain_loss
    asset.disposal_journal_number = entry.number
    asset.save(update_fields=[
        "status", "disposed_date", "disposal_proceeds_minor",
        "disposal_gain_loss_minor", "disposal_journal_number",
    ])
    return asset


@dataclass
class AssetRegisterRow:
    code: str
    name: str
    category: str
    acquisition_date: str
    cost_minor: int
    accumulated_depreciation_minor: int
    net_book_value_minor: int
    status: str


@dataclass
class AssetRegister:
    rows: list[AssetRegisterRow]
    total_cost: int
    total_accumulated: int
    total_nbv: int


def asset_register(*, include_disposed: bool = False) -> AssetRegister:
    """The fixed-asset register: cost, accumulated depreciation, and net book value per asset."""
    qs = FixedAsset.objects.all().order_by("code")
    if not include_disposed:
        qs = qs.filter(status=AssetStatus.ACTIVE)
    rows: list[AssetRegisterRow] = []
    total_cost = total_acc = total_nbv = 0
    for a in qs:
        rows.append(AssetRegisterRow(
            code=a.code, name=a.name, category=a.category,
            acquisition_date=str(a.acquisition_date),
            cost_minor=a.cost_minor,
            accumulated_depreciation_minor=a.accumulated_depreciation_minor,
            net_book_value_minor=a.net_book_value_minor,
            status=a.status,
        ))
        total_cost += a.cost_minor
        total_acc += a.accumulated_depreciation_minor
        total_nbv += a.net_book_value_minor
    return AssetRegister(rows=rows, total_cost=total_cost,
                         total_accumulated=total_acc, total_nbv=total_nbv)
