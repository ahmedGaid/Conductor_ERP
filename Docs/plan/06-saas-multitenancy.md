# Session 06 — SaaS multi-tenancy (the big architectural change)

**Goal:** run one deployment serving many isolated companies, without losing the customer-hostable
single-tenant story (same codebase; tenancy is configuration). **Hard dependency on Session 00** —
data isolation must already be enforced, not advisory. This is 2+ sessions; split at `---`. Record
the model decision in DECISIONS.md **before** writing code.

## Decision to make first: isolation model
Recommended: **schema-per-tenant (PostgreSQL schemas)**. Strong isolation (each company its own
schema), single DB to operate, easy per-tenant backup/restore (you already have backup tooling),
and it maps cleanly to the existing single-tenant install (that install is just "one schema"). The
main alternative — a `tenant_id` column on every row (shared-schema) — is cheaper to build but one
missing filter leaks another company's data; given this is an **accounting** system, prefer the
harder-to-get-wrong isolation. Use `django-tenants` **only if** the user approves a new dependency
(see the no-new-deps rule); otherwise implement a thin schema-router.

---

## Part 1 — Tenant model + routing
1. `Tenant` registry (public schema): name, schema_name, plan, status, created_at.
2. **Resolution:** subdomain (`acme.conductor.app`) or a tenant header → set the active schema via a
   connection `search_path` per request (middleware, early in the stack, after correlation id).
3. **Migrations:** run per-schema; a management command migrates all tenant schemas. Public schema
   holds only the tenant registry + billing.
4. **Isolation test (non-negotiable):** a request for tenant A can **never** read tenant B's rows,
   proven by test across every module. This is the test the whole SaaS story rests on.

## Part 2 — Provisioning + lifecycle
1. `create_tenant(name, admin_email)` service: create schema, migrate it, seed identity + chart of
   accounts (reuse existing seeds + Setup Wizard), send the admin invite. Target: **one-click, under
   a minute** (matches the one-day-setup brand promise — now one-minute).
2. Tenant lifecycle: active / suspended (non-payment) / archived. Suspended → read-only or locked
   with a designed "subscription paused" state, not a crash.
3. Per-tenant backup/restore built on the existing Docker backup tooling (one schema = one dump).

## Part 3 — Background jobs + shared infrastructure are tenant-aware
1. **Celery:** every task that touches business data must set the tenant schema explicitly — pass
   `tenant_schema` in task kwargs and activate it at task start; never rely on ambient state. The
   hourly scheduled-reports beat (`accounting.run_scheduled_reports`) becomes a sweep **per tenant
   schema**.
2. **Cache/Redis:** prefix cache keys (throttles, token caches) with the tenant — otherwise one
   tenant's rate-limit or cached value bleeds into another's.
3. **Storage:** `STORAGE_ROOT`/`REPORTS_DIR` gain a per-tenant subdirectory; exports and backups
   never mix tenants in one folder.
4. **Test:** a beat sweep with two tenants writes each tenant's report into its own schema/folder
   and nothing into the other's.

## Part 4 — Keep single-tenant working
1. A single-tenant customer-hosted install = one tenant in one schema, tenancy middleware in a
   "single" mode. Same code path, config switch `TENANCY_MODE=single|multi`. Both must pass gates.
2. The AI layer (Session 02) already reads scope-filtered data as the actor — confirm it also
   respects the tenant schema boundary (it will, if it goes through services on the active
   connection).

## Done bar
- Cross-tenant isolation test suite GREEN across every module (list + detail + AI tools).
- `create_tenant` provisions a working, seeded company in < 60s.
- Single-tenant mode still passes `gate:all`.
- DECISIONS.md "SaaS 2026-07": isolation model + why schema-per-tenant, provisioning flow, single vs
  multi switch.
