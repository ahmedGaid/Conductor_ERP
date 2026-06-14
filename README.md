# General ERP — Platform

Customer-hosted, single-tenant ERP built as a **Django modular monolith** (Python 3.13 + DRF),
with a React + TypeScript frontend. Arabic/RTL-first, bilingual. Built foundation-first: platform +
workflow/forms engine + UI shell, then ERP modules (Accounting → Inventory → Sales → Purchasing → CRM).

See [DECISIONS.md](DECISIONS.md) for why the stack and scope are what they are, and
[the build plan](../../Users/Rw/.claude/plans) for the full roadmap.

## Repository layout

```
config/        Django project (settings split, urls, wsgi/asgi, celery)
erp/           ERP modules (modular monolith)
  core/        cross-cutting: correlation IDs, logging, errors, events, repository base
  identity/    auth, users, RBAC, 2FA (Stage 1)
  audit/       immutable audit trail
  monitoring/  health + system-check
  ...          workflow, forms, accounting, inventory, sales, purchasing, crm (later stages)
apps/web/      React + TypeScript frontend (Stage 3+)
scripts/gates/ machine gates — each stage must pass its gate before the next
architecture/  auto/maintained docs (modules, events, database, api, error-catalog, ...)
```

## Prerequisites (Windows)

Installed via winget: Python 3.13, Node LTS, PostgreSQL 16, Memurai Developer (Redis-compatible).

## Quickstart (local dev)

```powershell
# 1. Create the database role + db (once)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -f scripts/sql/bootstrap_db.sql

# 2. Python env + deps
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt

# 3. Configure env
copy .env.example .env   # then edit DATABASE_URL / REDIS_URL if needed

# 4. Migrate + run
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py runserver

# 5. Gate (definition of done for the stage)
.\.venv\Scripts\python scripts/gates/_run.py 00
```

`GET http://localhost:8000/health` → `{ "ok": true }`.
`GET http://localhost:8000/system-check` → DB / Redis / storage status.

## Gates

Each phase ends with a machine gate that must exit 0 before advancing:

```powershell
python scripts/gates/_run.py 00     # scaffold + DB/Redis + /health
python scripts/gates/_run.py all    # every implemented gate, in order
```
