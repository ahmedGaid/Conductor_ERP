# General ERP — Platform

Customer-hosted, single-tenant ERP built as a **Django modular monolith** (Python 3.13 + DRF),
with a React + TypeScript frontend. Arabic/RTL-first, bilingual. Built foundation-first: platform +
workflow/forms engine + UI shell, then ERP modules (Accounting → Inventory → Sales → Purchasing → CRM).

See [DECISIONS.md](DECISIONS.md) for why the stack and scope are what they are, and
[the build plan](../../Users/Rw/.claude/plans) for the full roadmap.

## Design & brand — read before touching any UI or copy

Start at the **[Product Philosophy front door](Docs/Brand/Conductor_Product_Philosophy.md)** — one
screen covering the mission, the 8-point **Conductor Standard** (the ship test), and where every
rule lives. It points into the brand triad, the sources of truth:

- **[Brand & Marketing Brief](Docs/Brand/Conductor_Brand_Marketing_Brief.md)** — *what we say* (copy, naming, positioning).
- **[Product Design & Engineering Directive](Docs/Brand/Conductor_ERP_Product_Design_Engineering_Directive.md)** — *how it looks & behaves* (wins on any pixel).
- **[Visual Identity System](Docs/Brand/Conductor_Visual_Identity_System.md)** — assets, off-app surfaces, the Arabic lexicon.

Every user-facing PR runs the **Conductor Quality Review**
([.github/pull_request_template.md](.github/pull_request_template.md)) — the same 8-point ship test
as a checklist.

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
