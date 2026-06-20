"""Data-scope enforcement (Increment 5) — the single place that narrows a module's queryset to
the records a user is allowed to see, given their effective scope for that entity's *view*
permission.

This is the enforcement half of the RBAC scope model: Increment 2 modeled the scope ladder
(All > Company > Branch > Department > Team > Own) and resolved a user's effective scope; here we
finally apply it to real querysets. Every module list endpoint runs its base queryset through
``scope_queryset`` so scope is enforced consistently in one audited place rather than re-implemented
per module.

Enforceable dimensions today (records inherit ``erp.core.models.AuditedModel``):

- ``created_by`` — a real User FK, stamped by the services ⇒ the **Own** scope.
- ``branch`` — stamped on create from the actor's branch (Increment 5) ⇒ the **Branch** scope.

Semantics (confirmed with the client; see DECISIONS.md):

- **All / Company** — unrestricted (single-tenant: the company *is* everything).
- **Branch / Department / Team** — ``branch == user.branch OR branch IS NULL``. Records carry no
  department/team dimension yet, so those finer scopes resolve to branch-level filtering (a
  documented limitation; finer record tagging is a later increment). NULL-branch records (legacy /
  unstamped / org-wide) stay visible within any branch — safe for single-tenant and preserves
  data created before branch stamping.
- **Own** — ``created_by == user``.
- **Superuser / System Admin** — bypass entirely (matches every other RBAC check).
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from . import access
from .rbac import DataScope


def scope_queryset(
    user,
    qs: QuerySet,
    code: str,
    *,
    branch_field: str = "branch",
    owner_field: str = "created_by",
) -> QuerySet:
    """Filter ``qs`` to the records ``user`` may see for permission ``code`` at their scope.

    ``code`` is the entity's *view* permission (e.g. ``"sales.order.view"``). ``branch_field`` /
    ``owner_field`` let a caller point at differently-named columns, but every business record uses
    the ``AuditedModel`` defaults.
    """
    if access.is_superadmin(user):
        return qs

    scope = access.scope_for(user, code)

    if scope in (DataScope.ALL, DataScope.COMPANY):
        return qs
    if scope == DataScope.OWN:
        return qs.filter(**{owner_field: user})
    # BRANCH / DEPARTMENT / TEAM all resolve to branch-level filtering (records carry no finer
    # dimension yet). NULL-branch records remain visible org-wide.
    branch_id = getattr(user, "branch_id", None)
    return qs.filter(Q(**{f"{branch_field}_id": branch_id}) | Q(**{f"{branch_field}__isnull": True}))
