# PROJECT STATUS — General ERP (Django)

> Living resume anchor. The `/erp-resume` skill reads this file. Keep it updated after every
> meaningful step. Last updated: **2026-06-14 (Stages 0–3 complete; starting Stage 4)**.

## CURRENT POSITION
**Stages 0, 1, 2, 3 COMPLETE — `gate:all` (00, 01, 02, 03) is GREEN.** No active blocker.
Next: **Stage 4 — Platform screens** (dashboard with real metrics, workflow list, React Flow canvas
build/save round-trip, node config panel, execution viewer) **+ the workflow/instance DRF API** the
screens call (not yet built). See plan.

Stage 3 delivered (`apps/web/`, gate03): React 18 + TS + Vite frontend, **Arabic/RTL by default**
(`index.html` lang=ar dir=rtl; i18next fallback `ar`), live AR↔EN switch that re-applies
`<html dir/lang>` on `languageChanged`. Design tokens (`src/styles/tokens.css`) are the single
hex source; all other styles use `var(--token)` + **logical CSS only** (inline-start/end, no
physical left/right). App shell = sidebar (inline-start) + command bar + language switcher; `<bdi>`
wrapper for LTR tokens. Self-hosted fonts via `@fontsource` (IBM Plex Sans Arabic + Inter, no cloud
dep). i18n **key-parity** enforced both directions: `scripts/check-i18n-parity.mjs` runs as
`prebuild` (build fails on missing key) and gate03 also proves it catches drift via a fixture.
Run frontend: `cd apps/web; npm install; npm run dev` (Vite proxies `/api` → :8000).

Stage 1 delivered: custom `User` (branch FK + TOTP), RBAC via Django Groups + `HasAnyRole` DRF
permission, JWT login with 2FA challenge flow (`/api/identity/*`), audit service (immutable, blocks
update/delete, correlation-stamped) wired into login, event-bus isolation, `/system-check` with
db/redis/storage/workers, `seed_identity` (roles, HQ branch, demo users `admin/manager/accountant/
auditor`, password `Dev12345!`). Tests in `erp/*/tests`, run via `gate01`.

Stage 2 delivered (`erp/workflow` + `erp/forms`, gate02): graph workflow engine — deterministic
edge selection (guards vs else-fallback), crash-resumable state machine (one DB txn per transition,
`select_for_update` on the instance row), external-write idempotency (`sha256(instance|node|attempt)`
ledger + DB UNIQUE `ON CONFLICT DO NOTHING`), node executors (Start/Condition/Approval/Script/
ApiCall/End), self-built JSON-logic (no eval/exec), `{{ctx.path}}` template resolver, REST/SQL/
Webhook adapters behind one interface, simulated `erp_external.purchase_orders` target via RunSQL.
`erp/forms` dynamic Forms Builder (definitions + submissions) triggering workflows. 23 Stage-2 tests
(crash-resume, idempotency, determinism, approval, edges, adapters, forms). gate02 also statically
bans unsafe SQL building, eval/exec, and `random.*` in the engine.

Run gates: `cd C:\AhmedGaid\ERP; .\.venv\Scripts\python.exe scripts\gates\_run.py all`
Note: `erp` Postgres role granted CREATEDB (for pytest test DB).
Note: workflow/instance HTTP API (DRF endpoints) not yet built — add alongside Stage 3/4.

## What this project is
Customer-hosted, single-tenant **Django modular-monolith ERP** (Python 3.13 + DRF), React+TS
frontend, Arabic/RTL-first. Built **foundation-first**, then ERP modules (Accounting → Inventory →
Sales → Purchasing → CRM).

- Full roadmap/plan: `C:\Users\Rw\.claude\plans\cd-c-ahmedgaid-erp-files-read-thosse-bubbly-puddle.md`
- Decisions & rationale: `C:\AhmedGaid\ERP\DECISIONS.md`
- Source specs (input only): `C:\AhmedGaid\ERP\files\`
- Repo root: `C:\AhmedGaid\ERP` (git initialized, branch `main`, no commits yet)

## Environment facts (local dev)
- Python: `C:\Users\Rw\AppData\Local\Programs\Python\Python313\python.exe` (3.13.14)
- Virtualenv: `C:\AhmedGaid\ERP\.venv` — deps from `requirements.txt` INSTALLED ✅
- Run python as: `C:\AhmedGaid\ERP\.venv\Scripts\python.exe`
- PostgreSQL 16: service `postgresql-x64-16` RUNNING ✅. Superuser `postgres` / password `postgres`.
  psql at `C:\Program Files\PostgreSQL\16\bin\psql.exe`.
- App DB: database `erp`, role `erp` / password `erp`, owns `public` schema. Login verified ✅.
- Node 24 + npm 11 installed ✅ (for frontend, Stage 3+).
- Redis: `redis://localhost:6379/0` via winget `Redis.Redis` (MS port). Service `Redis` RUNNING
  (auto-start), `redis-cli ping` → PONG. `redis-cli` at `C:\Program Files\Redis\redis-cli.exe`.
  (Memurai failed — see DECISIONS.md.)
- `.env` exists at repo root (gitignored) with DATABASE_URL/REDIS_URL set.

## Toolchain install status
| Tool | Status |
|---|---|
| Python 3.13 | ✅ installed |
| Node LTS + npm | ✅ installed |
| PostgreSQL 16 | ✅ installed + DB/role created + migrated |
| Memurai (Redis) | ❌ BLOCKED — see below |

## ACTIVE BLOCKER → do this first on resume
Memurai (Redis) install via winget hung on a UAC elevation prompt; killing it left Windows Installer
in a stuck **error 1618 ("another installation in progress")** state. The fix chosen: **reboot the
machine** (clears 1618). After reboot:

1. Reinstall Memurai:
   ```
   winget install --id Memurai.MemuraiDeveloper -e --silent --accept-source-agreements --accept-package-agreements
   ```
   (If a UAC prompt appears, user approves it. If 1618 returns, the reboot didn't fully clear — retry once.)
2. Confirm the Memurai service is running and Redis answers:
   ```
   Get-Service *memurai*
   C:\Program Files\Memurai\memurai-cli.exe ping   # expect PONG
   ```
   (Memurai listens on 6379 by default, Redis-compatible.)
3. Run gate 00 (must print `GATE 00 PASSED`):
   ```
   cd C:\AhmedGaid\ERP
   .\.venv\Scripts\python.exe scripts\gates\_run.py 00
   ```

If Memurai still cannot install, fallback: install `Redis.Redis` via winget, OR (last resort) run
Celery eager + relax gate00's Redis check, recording it in DECISIONS.md.

## Stage 0 progress (scaffold & gate)
DONE:
- Repo + git init; `.gitignore`, `.env.example`, `.env`, `requirements.txt`, `pyproject.toml`, `README.md`.
- Django config package `config/` (settings base/dev/prod, `urls.py`, `wsgi/asgi`, `celery.py`).
- Modules: `erp/core` (correlation, structured JSON logging, errors+catalog, exceptions, event bus,
  repository base), `erp/identity` (custom `User` model), `erp/audit` (immutable `AuditEntry`),
  `erp/monitoring` (`/health` + `/system-check`).
- Gate harness `scripts/gates/_run.py` + `scripts/gates/gate00.py`.
- `DECISIONS.md`, `architecture/` skeleton (modules, dependencies, events, database, api, workflows,
  error-catalog), `scripts/sql/bootstrap_db.sql`.
- Migrations created AND applied to Postgres ✅ (identity.User, audit.AuditEntry, Django core).

REMAINING for Stage 0:
- Get Redis up (blocker above) and make `gate:00` pass green.
- Then: `git add -A && git commit` the Stage 0 baseline (only when user asks / after gate green).

## Next stages
- **Stage 4 — Platform screens (NEXT):** workflow/instance **DRF API** (CRUD workflows, start/list
  instances, approve/reject, node-level execution logs) + React screens: dashboard (real metrics),
  workflow list, **React Flow** canvas (build/save/round-trip), node config panel, execution viewer
  (node timeline, status pills, approve/reject). gate04 = canvas save→reload round-trips; viewer
  shows node-level logs; screens mirror in RTL.
- Stage 5 — ERP modules. Stage 6 — integrations/reporting. Stage 7 — hardening/deploy. (See plan.)

## How to resume
Read this file + the plan + `DECISIONS.md`, clear the active blocker, run `gate:00`, then continue
the roadmap. Update this file as steps complete.
