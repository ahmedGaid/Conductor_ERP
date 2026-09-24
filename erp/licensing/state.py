"""``current_state()`` — the one question every other file in this plan asks: what can this
install do right now? Reads the DB + the configured public keys + the clock; never raises for a
bad or missing key — a bad state is a value (``LicenseState``), not an exception.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from erp.audit import services as audit
from erp.identity.services import get_org_preferences

from .core import LicenseKeyError
from .models import InstalledLicense
from .verify import verify

TRIAL_DAYS = 30
# A server's clock can drift by minutes, not days — more than this is a real rollback, not jitter.
CLOCK_ROLLBACK_GRACE_DAYS = 2

Status = str  # one of: unmanaged | trial | trial_ended | active | invalid | company_mismatch


@dataclass(frozen=True)
class LicenseState:
    status: Status
    edition: str | None = None
    modules: tuple[str, ...] = ()
    max_branches: int | None = None
    maintenance_active: bool = False
    maintenance_until: _dt.date | None = None
    ai_active: bool = False
    ai_until: _dt.date | None = None
    trial_days_left: int | None = None
    invalid_reason: str | None = None
    # The company name/tax ID the KEY says — not whatever OrgPreferences currently claims. Printed
    # documents use this (FILE_03 decision 4: company binding) so a copied install can't relabel
    # itself. None when no key has ever verified (trial / trial_ended / invalid).
    licensed_company_name: str | None = None
    licensed_tax_id: str | None = None
    clock_rollback: bool = False


_NON_DIGITS_OR_LETTERS = re.compile(r"[\s\-]")


def _normalize_tax_id(value: str) -> str:
    """Spaces and dashes are cosmetic — ``123-456 789`` and ``123456789`` are the same ID."""
    return _NON_DIGITS_OR_LETTERS.sub("", value or "")


def get_installed() -> InstalledLicense:
    """The single installed-license row (pk=1), created on first access."""
    installed, _ = InstalledLicense.objects.get_or_create(pk=1)
    return installed


def _check_clock_rollback(installed: InstalledLicense, today: _dt.date) -> bool:
    """True if the clock looks like it moved backward by more than a drift-sized amount.

    Never mutates ``last_seen_date`` backward — it only ever ratchets forward on a normal
    (non-rollback) call, so once the clock catches back up to the real date the flag clears
    itself without any special-case reset logic. The audit row is written once, on the
    False->True transition (``clock_rollback_flagged``), not on every request the rollback
    stays in effect — this runs on every ``/api/*`` call, so re-auditing each time would flood
    the trail for as long as the clock stayed behind."""
    rolled_back = (
        installed.last_seen_date is not None
        and (installed.last_seen_date - today).days > CLOCK_ROLLBACK_GRACE_DAYS
    )
    if rolled_back:
        if not installed.clock_rollback_flagged:
            audit.record(
                module="licensing", action="clock_rollback_detected", entity_type="InstalledLicense",
                entity_id=1,
                after={"last_seen_date": str(installed.last_seen_date), "observed_today": str(today)},
            )
            installed.clock_rollback_flagged = True
            installed.save(update_fields=["clock_rollback_flagged"])
        return True
    if installed.clock_rollback_flagged:
        installed.clock_rollback_flagged = False
        installed.save(update_fields=["clock_rollback_flagged"])
    if installed.last_seen_date is None or today > installed.last_seen_date:
        installed.last_seen_date = today
        installed.save(update_fields=["last_seen_date"])
    return False


def current_state(*, today: _dt.date | None = None) -> LicenseState:
    """The install's current license state. Cheap (one query when a key is installed, one
    get-or-create otherwise) — call it fresh each time rather than caching across requests."""
    if settings.LICENSE_MODE == "off":
        return LicenseState(status="unmanaged")

    today = today or timezone.localdate()
    installed = get_installed()

    if not installed.first_run_at:
        installed.first_run_at = timezone.now()
        installed.save(update_fields=["first_run_at"])

    clock_rollback = _check_clock_rollback(installed, today)

    if not installed.key_text:
        trial_start = timezone.localtime(installed.first_run_at).date()
        days_elapsed = (today - trial_start).days
        if days_elapsed < TRIAL_DAYS:
            return LicenseState(
                status="trial", trial_days_left=TRIAL_DAYS - days_elapsed, clock_rollback=clock_rollback,
            )
        return LicenseState(status="trial_ended", trial_days_left=0, clock_rollback=clock_rollback)

    try:
        info = verify(installed.key_text)
    except LicenseKeyError as exc:
        return LicenseState(status="invalid", invalid_reason=exc.reason, clock_rollback=clock_rollback)

    org = get_org_preferences()
    if _normalize_tax_id(info.tax_id) != _normalize_tax_id(org.vat_number):
        return LicenseState(
            status="company_mismatch", clock_rollback=clock_rollback,
            licensed_company_name=info.company_name, licensed_tax_id=info.tax_id,
        )

    return LicenseState(
        status="active",
        edition=info.edition,
        modules=info.modules,
        max_branches=info.max_branches,
        maintenance_active=info.maintenance_until >= today,
        maintenance_until=info.maintenance_until,
        ai_active=info.ai_until is not None and info.ai_until >= today,
        ai_until=info.ai_until,
        clock_rollback=clock_rollback,
        licensed_company_name=info.company_name,
        licensed_tax_id=info.tax_id,
    )
