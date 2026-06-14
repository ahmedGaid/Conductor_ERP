# PROJECT STATUS — General ERP (Django)

> Living resume anchor. The `/erp-resume` skill reads this file. Keep it updated after every
> meaningful step. Last updated: **2026-06-14 (Stages 0, 1, 2 complete; starting Stage 3)**.

## CURRENT POSITION
**Stages 0, 1, 2 COMPLETE — `gate:all` (00, 01, 02) is GREEN.** No active blocker.
Next: **Stage 3 — Frontend foundation** (React + TS + Vite, i18next, Arabic/RTL default, design
tokens, app shell, i18n key-parity build gate). See plan + PHASE_06 design input.

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
- **Stage 3 — Frontend foundation (NEXT):** React + TS + Vite under `apps/web/`, i18next with
  Arabic/RTL default + live AR↔EN switch, design tokens (no hardcoded hex), logical CSS only, app
  shell (sidebar inline-start, command bar, language switcher), gate03 = i18n key-parity in both
  directions + boots `lang=ar dir=rtl`.
- Stage 4 — platform screens (dashboard, workflow list, React Flow canvas, node config, execution
  viewer) + workflow/instance DRF API. Stage 5 — ERP modules. Stage 6 — integrations/reporting.
  Stage 7 — hardening/deploy. (See plan.)

## How to resume
Read this file + the plan + `DECISIONS.md`, clear the active blocker, run `gate:00`, then continue
the roadmap. Update this file as steps complete.
