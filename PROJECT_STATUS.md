# PROJECT STATUS — General ERP (Django)

> Living resume anchor. The `/erp-resume` skill reads this file. Keep it updated after every
> meaningful step. Last updated: **2026-06-14 (Stage 0 complete; starting Stage 1)**.

## CURRENT POSITION
**Stage 0 + Stage 1 COMPLETE — `gate:all` (00, 01) is GREEN.** No active blocker.
Next: **Stage 2 — Workflow engine + Forms builder** (deterministic, crash-resumable, idempotent
engine + REST/SQL/Webhook adapters; tests-first per the engine contract in `architecture/workflows.md`).

Stage 1 delivered: custom `User` (branch FK + TOTP), RBAC via Django Groups + `HasAnyRole` DRF
permission, JWT login with 2FA challenge flow (`/api/identity/*`), audit service (immutable, blocks
update/delete, correlation-stamped) wired into login, event-bus isolation, `/system-check` with
db/redis/storage/workers, `seed_identity` (roles, HQ branch, demo users `admin/manager/accountant/
auditor`, password `Dev12345!`). Tests in `erp/*/tests`, run via `gate01`.

Run gates: `cd C:\AhmedGaid\ERP; .\.venv\Scripts\python.exe scripts\gates\_run.py all`
Note: `erp` Postgres role granted CREATEDB (for pytest test DB).

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

## Next stages (do NOT start until gate:00 is green)
- **Stage 1 — Core platform:** flesh out auth (JWT, RBAC, TOTP 2FA, branch scoping in `identity`),
  wire audit writes + correlation into services, event-bus isolation test, `/system-check` full,
  gate01.
- Stage 2 — Workflow engine + Forms. Stage 3 — Frontend foundation (i18n/RTL). Stage 4 — screens.
  Stage 5 — ERP modules. Stage 6 — integrations/reporting. Stage 7 — hardening/deploy. (See plan.)

## How to resume
Read this file + the plan + `DECISIONS.md`, clear the active blocker, run `gate:00`, then continue
the roadmap. Update this file as steps complete.
