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

from erp.identity.services import get_org_preferences

from .core import LicenseKeyError
from .models import InstalledLicense
from .verify import verify

TRIAL_DAYS = 30

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


_NON_DIGITS_OR_LETTERS = re.compile(r"[\s\-]")


def _normalize_tax_id(value: str) -> str:
    """Spaces and dashes are cosmetic — ``123-456 789`` and ``123456789`` are the same ID."""
    return _NON_DIGITS_OR_LETTERS.sub("", value or "")


def get_installed() -> InstalledLicense:
    """The single installed-license row (pk=1), created on first access."""
    installed, _ = InstalledLicense.objects.get_or_create(pk=1)
    return installed


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

    if not installed.key_text:
        trial_start = timezone.localtime(installed.first_run_at).date()
        days_elapsed = (today - trial_start).days
        if days_elapsed < TRIAL_DAYS:
            return LicenseState(status="trial", trial_days_left=TRIAL_DAYS - days_elapsed)
        return LicenseState(status="trial_ended", trial_days_left=0)

    try:
        info = verify(installed.key_text)
    except LicenseKeyError as exc:
        return LicenseState(status="invalid", invalid_reason=exc.reason)

    org = get_org_preferences()
    if _normalize_tax_id(info.tax_id) != _normalize_tax_id(org.vat_number):
        return LicenseState(status="company_mismatch")

    return LicenseState(
        status="active",
        edition=info.edition,
        modules=info.modules,
        max_branches=info.max_branches,
        maintenance_active=info.maintenance_until >= today,
        maintenance_until=info.maintenance_until,
        ai_active=info.ai_until is not None and info.ai_until >= today,
        ai_until=info.ai_until,
    )
