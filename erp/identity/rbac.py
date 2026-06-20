"""RBAC vocabulary — the single source of truth for the granular permission model.

This module is **pure constants + helpers** (no Django model imports) so both ``models.py`` and the
``access.py`` service layer can depend on it without a cycle. It defines:

- the permission **registry**: which modules exist, what entities each contains, and the fixed set of
  actions (View/Create/Edit/Delete/Approve) — a permission *code* is ``"<module>.<entity>.<action>"``;
- **data scopes** (All > My Company > My Branch > My Department > My Team > My Records) and their
  breadth ordering (broadest wins when a user holds a permission via several roles);
- **approval document types** for amount-threshold limits;
- the **default permission sets** seeded onto the built-in roles.

Increment 2 *models and exposes* this; queryset **enforcement** of scope across modules is Increment 5.
"""
from __future__ import annotations

# --- Actions -----------------------------------------------------------------------------------
VIEW = "view"
CREATE = "create"
EDIT = "edit"
DELETE = "delete"
APPROVE = "approve"
ACTIONS = [VIEW, CREATE, EDIT, DELETE, APPROVE]
CRUD = [VIEW, CREATE, EDIT, DELETE]

# --- Registry: module -> entities ---------------------------------------------------------------
# Entities mirror the real ERP modules. Adding an entity here makes its 5 permission codes valid and
# pickable in the (later) role editor; it never changes behaviour on its own.
MODULES: dict[str, list[str]] = {
    "accounting": [
        "account", "journal", "fiscal_period", "tax_code", "fixed_asset",
        "cost_center", "bank_statement", "budget", "report",
    ],
    "inventory": ["item", "category", "warehouse", "stock_movement", "stock_count"],
    "sales": ["customer", "order", "quotation"],
    "purchasing": ["supplier", "order", "request"],
    "crm": ["lead", "opportunity", "ticket", "campaign", "activity"],
    "einvoice": ["invoice"],
    "notifications": ["notification"],
    "workflow": ["workflow", "instance", "form"],
    "administration": ["user", "role"],
}

MODULE_NAMES = list(MODULES.keys())


def code(module: str, entity: str, action: str) -> str:
    return f"{module}.{entity}.{action}"


def all_permission_codes() -> list[str]:
    """Every valid permission code from the registry."""
    return [
        code(module, entity, action)
        for module, entities in MODULES.items()
        for entity in entities
        for action in ACTIONS
    ]


def module_of(permission_code: str) -> str:
    """The module a permission code belongs to (its first dotted segment)."""
    return permission_code.split(".", 1)[0]


def is_valid_code(permission_code: str) -> bool:
    parts = permission_code.split(".")
    if len(parts) != 3:
        return False
    module, entity, action = parts
    return action in ACTIONS and entity in MODULES.get(module, [])


def module_codes(module: str, actions: list[str]) -> list[str]:
    """All codes for the given module across the given actions (a seeding convenience)."""
    return [code(module, entity, action) for entity in MODULES.get(module, []) for action in actions]


# --- Data scopes -------------------------------------------------------------------------------
# Listed broadest-first; the index is the breadth rank used to pick the winning scope when a user
# holds the same permission through multiple roles (a broader grant always wins).
class DataScope:
    ALL = "all"
    COMPANY = "company"
    BRANCH = "branch"
    DEPARTMENT = "department"
    TEAM = "team"
    OWN = "own"


SCOPE_ORDER = [
    DataScope.ALL, DataScope.COMPANY, DataScope.BRANCH,
    DataScope.DEPARTMENT, DataScope.TEAM, DataScope.OWN,
]
SCOPE_CHOICES = [
    (DataScope.ALL, "All records"),
    (DataScope.COMPANY, "My company"),
    (DataScope.BRANCH, "My branch"),
    (DataScope.DEPARTMENT, "My department"),
    (DataScope.TEAM, "My team"),
    (DataScope.OWN, "My records only"),
]


def broadest(scope_a: str, scope_b: str) -> str:
    """Return whichever scope is broader (lower rank = broader)."""
    rank = {s: i for i, s in enumerate(SCOPE_ORDER)}
    return scope_a if rank.get(scope_a, 99) <= rank.get(scope_b, 99) else scope_b


# --- Approval document types -------------------------------------------------------------------
DOCUMENT_TYPES = [
    "purchase_order", "sales_order", "quotation", "purchase_request",
    "invoice", "payment", "discount", "return", "journal",
]


# --- Default role permission sets (seeded; idempotent) -----------------------------------------
# Keys are the built-in role names (erp.identity.roles). Each value is a list of
# (permission_code, scope). System Admin bypasses checks in code, so it is not enumerated here.
def _full(module: str, scope: str) -> list[tuple[str, str]]:
    return [(c, scope) for c in module_codes(module, ACTIONS)]


def _view(module: str, scope: str) -> list[tuple[str, str]]:
    return [(c, scope) for c in module_codes(module, [VIEW])]


def default_role_permissions() -> dict[str, list[tuple[str, str]]]:
    from .roles import ACCOUNTANT, AUDITOR, BRANCH_MANAGER

    auditor = [(c, DataScope.ALL) for c in module_codes_all([VIEW])]

    accountant: list[tuple[str, str]] = []
    accountant += _full("accounting", DataScope.ALL)
    accountant += _view("inventory", DataScope.ALL)
    accountant += _view("sales", DataScope.ALL)
    accountant += _view("purchasing", DataScope.ALL)
    accountant += _view("einvoice", DataScope.ALL)
    accountant += [(code("einvoice", "invoice", APPROVE), DataScope.ALL)]

    manager: list[tuple[str, str]] = []
    for m in ("sales", "purchasing", "inventory", "crm"):
        manager += [(c, DataScope.BRANCH) for c in module_codes(m, ACTIONS)]
    manager += _view("accounting", DataScope.BRANCH)
    manager += _view("einvoice", DataScope.BRANCH)
    manager += _view("notifications", DataScope.BRANCH)

    return {AUDITOR: auditor, ACCOUNTANT: accountant, BRANCH_MANAGER: manager}


def module_codes_all(actions: list[str]) -> list[str]:
    """All codes across every module for the given actions."""
    return [c for m in MODULE_NAMES for c in module_codes(m, actions)]


# Approval limits seeded per role: {role: {document_type: limit_minor | None}} (None = unlimited).
def default_approval_limits() -> dict[str, dict[str, int | None]]:
    from .roles import ACCOUNTANT, BRANCH_MANAGER

    return {
        BRANCH_MANAGER: {
            "sales_order": 5_000_000,       # 50,000.00
            "purchase_order": 5_000_000,
            "quotation": 5_000_000,
            "purchase_request": 5_000_000,
            "discount": 500_000,            # 5,000.00
            "return": 2_000_000,            # 20,000.00
        },
        ACCOUNTANT: {
            "invoice": None,                # unlimited
            "payment": 10_000_000,          # 100,000.00
            "journal": None,
        },
    }
