"""Default RBAC roles.

Roles are Django Groups. This module is the single source of truth for the baseline role set so
seeding and tests agree. Module-specific operator roles (Sales Rep, Buyer, Warehouse Clerk, ...)
are added by their modules in Stage 5.
"""
from __future__ import annotations

SYSTEM_ADMIN = "System Admin"
BRANCH_MANAGER = "Branch Manager"
ACCOUNTANT = "Accountant"
AUDITOR = "Auditor"

DEFAULT_ROLES = [SYSTEM_ADMIN, BRANCH_MANAGER, ACCOUNTANT, AUDITOR]
