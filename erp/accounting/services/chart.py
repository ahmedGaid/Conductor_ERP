"""Chart-of-accounts additions outside the baseline seed — one account created on demand."""
from __future__ import annotations

from django.db import transaction

from erp.audit import services as audit

from ..domain.accounts import AccountType
from ..domain.models import Account

_TYPE_PREFIX = {
    AccountType.ASSET: "1",
    AccountType.LIABILITY: "2",
    AccountType.EQUITY: "3",
    AccountType.INCOME: "4",
    AccountType.EXPENSE: "5",
}


def next_account_code(account_type: str) -> str:
    """Preview the code a new account of this type would receive if none is given."""
    prefix = _TYPE_PREFIX[account_type]
    candidates = [
        int(c) for c in Account.objects.filter(type=account_type, code__startswith=prefix)
        .values_list("code", flat=True) if c.isdigit()
    ]
    base = max(candidates, default=int(f"{prefix}000"))
    return str(base + 10)


@transaction.atomic
def create_account(*, name: str, type: str, code: str = "", parent_code: str = "",
                   actor=None) -> Account | None:
    """Create a chart-of-accounts leaf (code auto-assigned when omitted). Returns ``None`` if
    ``parent_code`` was given but no longer resolves — a stale reference, mirrors
    ``sales.place_order``."""
    parent = None
    if parent_code:
        parent = Account.objects.filter(code=parent_code).first()
        if parent is None:
            return None
    resolved_code = (code or "").strip() or next_account_code(type)
    account = Account.objects.create(
        code=resolved_code, name=name.strip(), type=type, parent=parent,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="accounting", action="create_account", entity_type="Account",
        entity_id=account.code, actor=actor,
        after={"code": account.code, "name": account.name, "type": account.type},
    )
    return account
