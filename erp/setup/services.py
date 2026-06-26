"""First-run setup services.

Thin wrappers over identity's org-preferences service — the wizard reuses what already exists
(it never re-implements org defaults). For now the only state is the ``is_setup_complete`` flag;
the per-step provisioning endpoints (COA / tax / users) land in later wizard slices.
"""
from __future__ import annotations

from erp.accounting import contracts as accounting
from erp.identity import services as identity_services


def get_status() -> dict:
    """The wizard's view of what's done so far: the finish flag + per-step state."""
    org = identity_services.get_org_preferences()
    return {
        "is_setup_complete": org.is_setup_complete,
        "chart_of_accounts": accounting.baseline_summary(),
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
