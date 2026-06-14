# Database

> Per-module data ownership and key tables. No module reads/writes another module's tables
> directly — access goes through that module's repositories/services.

| Table | Owner module | Notes |
|---|---|---|
| core_branch | core | Org/branch scoping primitive (uuid pk) |
| identity_user | identity | Custom user (AUTH_USER_MODEL) + branch FK + TOTP |
| audit_entry | audit | Immutable, append-only |

Roles are Django Groups (auth_group). Abstract bases `TimeStampedModel`/`AuditedModel` (in
`erp/core/models.py`) provide uuid pk + timestamps + actor stamps + branch + soft-delete to business
modules (no own table).

Conventions (business modules, from Stage 5): uuid pk, created_at/updated_at/created_by/updated_by,
branch_id scope, soft-delete (deleted_at). Money stored as integer minor units + currency.
