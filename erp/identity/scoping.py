"""Data-scope enforcement (Increment 5) — the single place that narrows a module's queryset to
the records a user is allowed to see, given their effective scope for that entity's *view*
permission.

This is the enforcement half of the RBAC scope model: Increment 2 modeled the scope ladder
(All > Company > Branch > Department > Team > Own) and resolved a user's effective scope; here we
finally apply it to real querysets. Every module list endpoint runs its base queryset through
``scope_queryset`` so scope is enforced consistently in one audited place rather than re-implemented
per module.

Enforceable dimensions (records inherit ``erp.core.models.AuditedModel``, all stamped from the
creating actor):

- ``created_by`` — a real User FK ⇒ the **Own** scope.
- ``branch`` — the actor's branch ⇒ the **Branch** scope.
- ``department`` / ``team`` — the actor's org placement ⇒ the **Department** / **Team** scopes
  (each belongs to one branch, so they narrow *within* a branch).

Semantics (confirmed with the client; see DECISIONS.md):

- **All / Company** — unrestricted (single-tenant: the company *is* everything).
- **Branch / Department / Team** — ``<dim> == user.<dim> OR <dim> IS NULL``. A NULL on the matched
  dimension means the record is legacy/unstamped/org-wide and stays visible (safe for single-tenant,
  and preserves data created before stamping). A user whose own dimension is unset sees only the
  NULL/unstamped records at that tier.
- **Own** — ``created_by == user``.
- **Superuser / System Admin** — bypass entirely (matches every other RBAC check).
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from . import access
from .rbac import DataScope

# Scope -> (record field, the matching attribute on the user). NULL on the record field always
# stays visible (legacy / unstamped / org-wide).
_DIMENSION = {
    DataScope.BRANCH: ("branch", "branch_id"),
    DataScope.DEPARTMENT: ("department", "department_id"),
    DataScope.TEAM: ("team", "team_id"),
}


def scope_queryset(
    user,
    qs: QuerySet,
    code: str,
    *,
    owner_field: str = "created_by",
) -> QuerySet:
    """Filter ``qs`` to the records ``user`` may see for permission ``code`` at their scope.

    ``code`` is the entity's *view* permission (e.g. ``"sales.order.view"``). Every business record
    uses the ``AuditedModel`` dimension columns (branch/department/team/created_by).
    """
    if access.is_superadmin(user):
        return qs

    scope = access.scope_for(user, code)

    if scope in (DataScope.ALL, DataScope.COMPANY):
        return qs
    if scope == DataScope.OWN:
        return qs.filter(**{owner_field: user})

    field, user_attr = _DIMENSION.get(scope, _DIMENSION[DataScope.BRANCH])
    value = getattr(user, user_attr, None)
    return qs.filter(Q(**{f"{field}_id": value}) | Q(**{f"{field}__isnull": True}))
