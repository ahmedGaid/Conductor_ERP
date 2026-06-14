# DECISIONS

Running log of choices made where specs were silent or in conflict, plus any deviation from a
stated requirement. Every entry is traceable so future maintainers (and Claude Code) understand
*why* the code looks the way it does.

## Reconciliation of conflicting specs (2026-06-14)

The `files/` folder contained three conflicting specs (full NestJS ERP, Django engineering
charter, Node/Express workflow-MVP). Confirmed direction with the client:

- **Scope:** phased, foundation-first — platform + workflow/forms engine + bilingual RTL UI first,
  then ERP modules in questionnaire priority order (Accounting → Inventory → Sales → Purchasing → CRM).
- **Backend stack:** Python 3.13 / Django + DRF (the "System Architecture & Engineering
  Requirements" doc wins). **NestJS and Node/Express are dropped.** The `PHASE_00–09` docs remain as
  *design input* (workflow-engine contract, RTL UI spec, Purchase-Request reference flow), re-expressed
  on Django.
- **Deployment:** customer-hosted, single-tenant, Windows Server, multi-machine capable, no cloud-only deps.
- **Engineering standards:** all adopted (correlation IDs + structured logging, immutable audit,
  fault isolation + domain events, privacy-safe diagnostics + monitoring).
- The MVP-only "forbidden list" (no real ERP modules; dev-user-only auth) is **superseded** — we build
  the real modules and real RBAC/2FA.

## Architecture choices

- **Django config package** is named `config/`; the **modules** live under `erp/` (e.g. `erp/core`,
  `erp/workflow`) to match the engineering charter's module tree without clashing with the project package.
- **`core` module uses a flat layout** (infrastructure), while business modules will follow the strict
  `module/{api,domain,services,repositories,contracts,events,tests,docs}/` sub-layout.
- **`identity` app label** is used instead of `auth` because `auth` clashes with `django.contrib.auth`'s
  app label.
- **Custom `User` model created in Stage 0** so `AUTH_USER_MODEL` is locked before the first migration
  (swapping it later requires a destructive reset). Stage 1 expands it (JWT, RBAC, TOTP 2FA, branch scoping).

## Toolchain (local dev provisioning, 2026-06-14)

- Machine had only git. Installed via winget: Python 3.13, Node LTS, PostgreSQL 16.
- **Redis:** Memurai Developer was the first choice but its MSI repeatedly failed — first a UAC/elevation
  hang that, when killed, left Windows Installer in a stuck 1618 state (required a reboot), then after
  reboot a `1603` failure (`SFXCA: Failed to create temp directory. Error code 5` in its .NET custom
  actions — an elevated-TEMP/ACL issue specific to that installer). Switched to **`Redis.Redis`** (the
  Microsoft Redis-on-Windows port, plain MSI, no managed custom actions) via winget — installed cleanly,
  runs as the auto-start `Redis` service on port 6379, `redis-cli ping` → PONG. Still a native winget
  install, no cloud dep. Note: this port is Redis 3.0.x (older) but sufficient as a Celery broker/result
  backend for dev; revisit for production if newer Redis features are needed.

## Workflow engine (Stage 2)

- **Condition edge semantics.** The PHASE specs both say "exactly one winner" *and* ship a `true`
  fallback edge — contradictory under a strict reading. Resolved deterministically: edges with an
  explicit JSON-logic condition are **guards**; a single null/`true` edge is the **else-fallback**.
  Exactly one guard must be truthy → it wins; ≥2 truthy guards → fail (ambiguous); 0 truthy guards →
  take the lone fallback, else fail. Deterministic and supports an else branch. See `engine/edges.py`.
- **JSON-logic is self-implemented** (`workflow/lib/jsonlogic.py`) — no external dependency, no
  eval/exec; auditable and deterministic. Covers var/compare/and/or/if/arithmetic/in.
- **External-write idempotency** uses both layers: a durable `IdempotencyRecord` ledger keyed by
  `sha256(instance|node|attempt)` (engine short-circuits a same-attempt re-run) **and** DB-level
  proof (UNIQUE `idempotency_key` + `ON CONFLICT DO NOTHING` in the target). Proven by tests.
- **`erp_external` schema** (the simulated external ERP target) lives in the same Postgres instance
  via a `RunSQL` migration — no second server, matching the PHASE intent.

## Open decisions (industry-standard default applied; confirm with client)

- **Inventory costing method** — questionnaire says "Not decided." Default **Weighted Average**,
  applied consistently to all valuations.
- **Backup policy** — left blank. Default: automated nightly backups with periodic tested restores.
- **Frontend serving** — React built separately; default to serving the static build behind Django for
  single-tenant simplicity.
