"""First-run setup services.

Thin wrappers over identity's org-preferences service — the wizard reuses what already exists
(it never re-implements org defaults). For now the only state is the ``is_setup_complete`` flag;
the per-step provisioning endpoints (COA / tax / users) land in later wizard slices.
"""
from __future__ import annotations

from django.contrib.auth.models import Group

from erp.accounting import contracts as accounting
from erp.identity import services as identity_services
from erp.identity import users as identity_users


def get_status() -> dict:
    """The wizard's view of what's done so far: the finish flag + per-step state."""
    org = identity_services.get_org_preferences()
    return {
        "is_setup_complete": org.is_setup_complete,
        "chart_of_accounts": accounting.baseline_summary(),
        "tax": {
            "vat_rate_bps": accounting.get_standard_vat_rate_bps(),
            "einvoice_enabled": org.einvoice_enabled,
        },
        # The roles the invite-team step offers — mirrors the org-units role list (same source).
        "available_roles": list(Group.objects.order_by("name").values_list("name", flat=True)),
    }


def invite_user(actor, *, username, email, role=None) -> dict:
    """Create an invited team member (wizard step 4).

    Reuses identity's own ``create_user`` — the wizard never re-implements user provisioning. The
    one-time temporary password comes back with the row so the admin can hand it over.
    """
    user, temp_password = identity_users.create_user(
        username=username, email=email, role=role or None, actor=actor,
    )
    result = identity_users.serialize_list(user)
    result["temp_password"] = temp_password
    return result


def set_tax_settings(actor, *, vat_rate_bps=None, einvoice_enabled=None) -> dict:
    """Set the standard VAT rate (accounting) and/or the e-invoicing toggle (org preference)."""
    if vat_rate_bps is not None:
        accounting.set_standard_vat_rate(vat_rate_bps)
    if einvoice_enabled is not None:
        identity_services.update_org_preferences(actor, {"einvoice_enabled": bool(einvoice_enabled)})
    org = identity_services.get_org_preferences()
    return {
        "vat_rate_bps": accounting.get_standard_vat_rate_bps(),
        "einvoice_enabled": org.einvoice_enabled,
    }


def seed_chart_of_accounts() -> dict:
    """Provision the baseline chart of accounts (+ fiscal year, VAT codes, cost centers).

    Reuses accounting's own provisioning via its public contract — the wizard never builds
    accounts by hand. Idempotent.
    """
    return accounting.seed_baseline_accounting()


def mark_complete(actor) -> dict:
    """Flag setup as finished (writes an audit record via the identity service)."""
    identity_services.update_org_preferences(actor, {"is_setup_complete": True})
    return {"is_setup_complete": True}
