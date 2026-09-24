"""Installing a key — the one write path, shared by the CLI command, ``provision_customer``,
and the API. Verifies first: an install can never leave the DB holding a key that fails
verification."""
from __future__ import annotations

from django.utils import timezone

from erp.audit import services as audit

from .core import LicenseInfo, LicenseKeyError
from .state import get_installed
from .verify import verify


def install_key(key_text: str, *, actor=None) -> LicenseInfo:
    """Verify ``key_text`` and store it as the installed license. Raises ``LicenseKeyError`` (never
    touching the DB) if the key doesn't verify."""
    key_text = key_text.strip()
    info = verify(key_text)  # raises LicenseKeyError subclasses — checked before any write

    installed = get_installed()
    installed.key_text = key_text
    installed.installed_at = timezone.now()
    installed.installed_by = actor if getattr(actor, "is_authenticated", False) else None
    installed.save(update_fields=["key_text", "installed_at", "installed_by"])

    audit.record(
        module="licensing",
        action="install_license",
        entity_type="InstalledLicense",
        entity_id=1,
        actor=actor,
        after={
            "license_id": info.license_id,
            "edition": info.edition,
            "tax_id": info.tax_id,
            "maintenance_until": str(info.maintenance_until),
        },
    )
    return info


__all__ = ["install_key", "LicenseKeyError"]
