# Conductor ERP — Master Daily E2E Test Prompt

> **How to use:** paste this whole file as the prompt for an autonomous AI coding agent
> (Claude Code with browser automation — Playwright MCP or the built-in browser/preview tools).
> It is designed to run **unattended, once per day**, as a full regression of the application.
>
> Automation options:
> - Claude Code scheduled routine: `/schedule` a daily cloud/local agent whose prompt is
>   `Read and execute Docs/testing/E2E_MASTER_PROMPT.md`.
> - Windows Task Scheduler: `claude -p "Read and execute Docs/testing/E2E_MASTER_PROMPT.md" --permission-mode acceptEdits`
>
> **This file is self-maintaining.** Phase 7 requires the executing agent to update it when new
> features ship. Never delete a journey; mark it `[RETIRED — reason]` instead.

---

## Mission

You are acting as a **real user** (an Egyptian SMB owner and their accountant) plus a **QA engineer**
with backend access. Verify Conductor ERP end to end: every major business workflow, through the real
browser UI, with every action verified against **four layers**:

1. **UI state** — the screen shows the result (row appears, status changes, toast confirms).
2. **API/network** — the request returned 2xx; no failed/4xx/5xx requests in the network log.
3. **Backend data** — the record actually exists/changed (verify via API `GET` or Django shell / SQL).
4. **Business rules** — totals add up, stock moved, GL entries balance, money is integer minor units.

A test only PASSES when all four layers agree. A green screen with a silently failed request is a FAIL.

**Fix loop:** when a test fails — investigate root cause in the code, fix it, run the project gates,
rerun the failed journey (and any journey touching the same module), and repeat until green. Only
skip a fix (mark `SKIPPED-NEEDS-HUMAN`) if it needs a product decision, a destructive migration, or
credentials you don't have.

---

## Environment facts (Appendix A — keep current)

| Fact | Value |
|---|---|
| Repo root | `c:\AhmedGaid\ERP` |
| Start dev | `.\run-dev.ps1` (migrates DB, starts both servers) — or start separately below |
| Backend | Django, `.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000` (modules in `erp/`, NOT `apps/`) |
| Frontend | Vite, `cd apps/web; npm run dev` → http://localhost:5173 |
| Database | Postgres `postgresql://erp:erp@localhost:5432/erp` |
| Redis | optional (background jobs only); app runs without it |
| Login | `admin` / `Dev12345!` (seed superuser) |
| Auth | `POST /api/identity/login`; token stored in localStorage `erp.token` |
| Language/theme | Switch language via ⌘K command palette (العربية/English). Persisted in localStorage `erp.lang` + `i18nextLng`, theme in `erp.theme`. App does NOT react to raw localStorage writes — use the in-app switch or reload. |
| Default direction | **Arabic / RTL is the default.** Test AR/RTL first, then EN/LTR. |
| Sample import files | `_smoke/customers.csv`, `_smoke/customers_ar.csv`, `_smoke/items.csv`, `_smoke/suppliers.csv` |
| Gates (must be green before "fixed") | `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit`; repo root: `python scripts/gates/gate03.py`; backend: `.venv\Scripts\python.exe -m pytest` |
| Deploy to dev env | `docker compose up -d --build` at repo root (see Phase 6) |
| Reports | `Docs/testing/e2e-reports/YYYY-MM-DD/` |

---

## Phase 0 — Boot & health

1. Check servers: `GET http://127.0.0.1:8000/api/identity/login` reachable (any HTTP response = up)
   and http://localhost:5173 serves the app. If not running, start them (see Appendix A). Wait for
   both before opening the browser.
2. Create today's report directory `Docs/testing/e2e-reports/YYYY-MM-DD/` with subfolder `screenshots/`.
3. Start browser session. **Attach listeners for the whole run:** console errors/warnings, page errors
   (uncaught JS exceptions), failed network requests (status ≥ 400 or aborted). Log every occurrence
   with the journey name; any console error or failed request during a journey fails that journey.
4. Baseline screenshot of the login page (light + note the theme).

## Phase 1 — Smoke: login, shell, chrome

- **S1 Login:** wrong password → designed, blame-free error (no raw stack, no bare "error"). Correct
  login → lands on Dashboard; `erp.token` set; no console errors.
- **S2 App shell:** sidebar renders all modules; command palette (⌘K) opens, searches, navigates;
  favorites stars work; theme toggle light↔dark (chrome stays monochrome in BOTH — no colored frame).
- **S3 i18n/RTL:** switch to Arabic via palette — layout mirrors (RTL), back-arrows point the correct
  way, no untranslated keys visible (raw `key.like.this` on screen = FAIL). Switch to English — reads
  identically. Screenshot both.
- **S4 Navigation sweep:** visit every top-level page from the sidebar once. Each must render a
  designed state (data, or a designed empty state — never a blank screen or "No data" bare text),
  with zero console errors and zero failed requests. Screenshot any page that looks broken.

## Phase 2 — Business workflows (the core)

For every journey: do it through the UI like a user, then verify all four layers. Use unique,
recognizable test data prefixed `E2E-YYYYMMDD-` so runs don't collide and cleanup is possible.
Amounts must exercise decimals (e.g. 1,234.56 EGP) to catch money-rounding bugs — verify the wire
value is integer minor units (piasters).

### J1 — Sales: quote → order → invoice (order-to-cash)
1. Create customer `E2E-YYYYMMDD Customer` (Arabic name too). Verify auto customer code assigned,
   unique, no collision (create a second customer immediately after — codes must differ).
2. Create quotation with ≥2 lines (one decimal quantity/price). Verify line totals + grand total math.
3. Convert/create sales order from it. Verify status transitions on both documents.
4. Invoice the order. Verify invoice totals match order; verify backend record via API GET.
5. Check inventory impact (if delivery/stock deduction applies): stock level of the item decreased
   by the sold quantity.
6. Check accounting impact: a balanced journal entry / AR posting exists for the invoice.

### J2 — Purchasing: request → PO → receipt (procure-to-pay)
1. Create supplier `E2E-YYYYMMDD Supplier` — verify auto supplier code, collision-free (same double-create check as J1).
2. Purchase request → purchase order (≥2 lines). Verify totals, status flow.
3. Receive goods. Verify stock level of the item **increased** by the received quantity.
4. Verify AP/accounting posting is balanced.

### J3 — Inventory
1. Create item `E2E-YYYYMMDD Item` with price. Appears in list; searchable.
2. Stock adjustment (+10 then −3). Stock ledger/movements show both entries; final quantity correct.
3. Verify item usable in a sales line (search from J1's form finds it).

### J4 — CRM
1. Create lead/contact `E2E-YYYYMMDD Lead`. Move it through pipeline stages (drag or action).
2. Verify stage persists after reload. Priority pill and status badges render correctly.
3. Convert lead → customer (if flow exists). Verify the customer record links back.

### J5 — Accounting
1. Create a manual journal entry: 2 lines, debits = credits. Unbalanced entry must be **rejected**
   with a clear error (business-rule check).
2. Verify entry appears in ledger/trial balance; trial balance stays balanced.
3. Open financial statements pages — figures render, no NaN, no raw negative-zero, money formatted
   at the edge (Arabic + English formats).
4. Bank reconciliation page opens with designed state.

### J6 — Pricing
1. Create a price list `E2E-YYYYMMDD PL` with a special price for J3's item.
2. Assign it to J1's customer. New quotation for that customer picks up the special price.

### J7 — E-invoice
1. Open the e-invoice module for J1's invoice. Verify submission flow reaches its expected dev-mode
   state (mock/sandbox); status is a human status, errors (if sandbox is down) are blame-free.

### J8 — Workflow/canvas
1. Open workflow list + canvas. Create/open a workflow; canvas renders; nodes draggable.
2. Execution viewer shows a designed state (or a real execution if one can be triggered).

### J9 — Assistant / AI (agentic features)
1. Open the assistant. Send a message **in Arabic** → reply must be in Arabic. Send one **in English**
   → reply in English (regression for the language-follow fix).
2. Ask a data question ("كم عميل لدينا؟" / how many customers) — answer must reflect real data
   (compare against the customers list count).
3. Exercise one write/agent action if available (e.g. draft creation) — verify it produces a **draft**
   requiring confirmation, never a silent commit.
4. Provider fail-over resilience: if the primary AI provider is down, the assistant must degrade
   gracefully (fallback provider or designed error) — never a spinner forever or a raw stack.
5. Log response times; > 30s for a simple question = performance finding.

### J10 — Smart import
1. Import `_smoke/customers.csv` and `_smoke/customers_ar.csv` through the import UI. Verify row
   counts match the files, Arabic names intact (no mojibake), duplicates handled per rules.
2. Import `_smoke/items.csv`, `_smoke/suppliers.csv` similarly.

### J11 — Identity, RBAC & admin
1. Create role `E2E-YYYYMMDD Role` with limited permissions + user `e2e-limited`.
2. Log in as that user (separate browser context): forbidden modules hidden or access-denied is a
   designed state; permitted ones work. **Direct-URL probe:** navigate straight to a forbidden page
   and hit a forbidden API — both must deny (403), not error.
3. Back as admin: audit/monitoring pages show today's activity.

### J12 — Notifications & settings
1. An action from J1–J11 that should notify, does (bell/panel updates).
2. Settings pages: dashboard settings reorder works and persists; navigation settings persist;
   density/contrast prefs apply.

## Phase 3 — Cross-cutting quality sweeps

- **C1 Console/network log review:** compile every console error/warning and failed request captured
  since Phase 0. Each unique one is a finding (dedupe by message).
- **C2 Visual/brand spot-check (AR/RTL + dark, the defaults):** chrome monochrome; color only inside
  content and always paired with a word/icon; one icon hand (no emoji/foreign glyphs as icons); no
  physical left/right layout bugs; screenshots of Dashboard, one list page, one detail page, one form —
  in AR/dark and EN/light (8 screenshots).
- **C3 Designed states:** force one error (kill backend briefly or block a request) → UI shows a
  designed, blame-free error, and recovers when the backend returns. Check one loading state (throttle)
  and one empty state (fresh filter with no results).
- **C4 Performance:** record navigation timing on Dashboard + the heaviest list page. First load
  < 5s dev-cold, subsequent navigations < 1.5s. Log regressions vs. the previous report if one exists
  (`Docs/testing/e2e-reports/<last-date>/report.md`).
- **C5 Data hygiene:** money values in API payloads are integers (minor units); dates render localized;
  no `undefined`/`null`/`NaN` visible anywhere.

## Phase 4 — New-feature discovery (keeps the suite current)

1. `git log --oneline --since=<date-of-last-report>` (fall back to 7 days). Also skim
   `Docs/plan/EXECUTION_ORDER.md` for freshly completed items.
2. For every user-facing feature shipped since the last run that has **no journey above**: test it now
   (same four-layer standard), and **add a numbered journey for it to Phase 2 of this file** in the
   same format. This step is mandatory — the suite must grow with the product.
3. Note the additions in the report under "Suite changes".

## Phase 5 — Fix loop (on any failure)

For each FAIL, in severity order (data corruption > broken workflow > console error > visual > perf):

1. **Reproduce** minimally. Capture screenshot + console + the failing request (payload/response).
2. **Root cause** in code — read the actual handler/component; don't patch symptoms.
3. **Fix** following project rules (CLAUDE.md: tokens only, logical CSS, i18n parity, no new deps).
4. **Gate:** run the gates from Appendix A relevant to what you touched (frontend → parity + tsc +
   gate03; backend → pytest).
5. **Rerun** the failed journey plus every journey in the same module. Repeat until green.
6. Record in the report: root cause, files changed, commit-ready diff summary. Commit the fix with a
   conventional message (`fix(module): ...`) — one commit per root cause. Do not push.

If a fix would be destructive or needs a product decision → mark `SKIPPED-NEEDS-HUMAN` with a clear
handoff note and continue.

## Phase 6 — Dev-environment deploy & re-verify

Only when **all local journeys pass** (no FAILs; SKIPPED-NEEDS-HUMAN allowed):

1. Deploy: `docker compose up -d --build` at repo root (the containerized dev environment). Wait for
   health (backend answers, frontend serves).
2. Rerun **Phase 1 fully** + an abridged Phase 2 (J1, J2, J9, J10 — the highest-value flows) against
   the deployed URL.
3. Environment-specific failures (works local, fails deployed) → fix loop again (usually env/config:
   `.env.docker.example` vs actual, static files, migrations), redeploy, re-verify.
4. Iterate until the deployed environment passes with **zero critical issues**. Then
   `docker compose down` unless told to keep it running.

## Phase 7 — Report & self-maintenance

Write `Docs/testing/e2e-reports/YYYY-MM-DD/report.md`:

```markdown
# E2E Report — YYYY-MM-DD
**Summary:** X passed · Y failed→fixed · Z skipped-needs-human · W new journeys added
**Verdict:** GREEN / GREEN-WITH-SKIPS / RED (why)

## Results by journey
| Journey | Result | Notes |
(one row per S/J/C item; link screenshots)

## Failures & fixes
(per failure: symptom → root cause → fix → files → gates rerun → rerun result)

## Skipped — needs human
(what, why, exact handoff)

## Suite changes
(journeys added/updated in the master prompt today)

## Performance
(timings vs previous run)

## Environment
(commit SHA tested, local + deployed results)
```

Then **maintain this master prompt**:
- Add the new journeys from Phase 4 (already done in place).
- Update Appendix A if any environment fact changed (ports, creds, commands, gates).
- Never delete a journey — mark `[RETIRED — reason, date]`.
- Keep test-data prefix convention and the four-layer standard intact.

Finally: clean up test data where a delete flow exists in the UI (use it — that's a test too);
otherwise leave `E2E-YYYYMMDD-` records (prefix makes them identifiable) and note them in the report.

---

## Hard rules for the executing agent

- **Never fake a pass.** No screenshot + four-layer verification = not a pass.
- **UI first.** Drive the browser like a human (click, type, keyboard). API calls are for
  *verification*, not as a substitute for the UI action.
- **Arabic first.** Run journeys in Arabic/RTL by default; S3 covers English parity.
- **Don't skip gates to save time** — a green gate is part of "fixed".
- **Don't reset or drop the database.** Additive test data only, prefixed `E2E-YYYYMMDD-`.
- **One commit per root cause; never push; never merge.**
- **Respect the brand bar** when fixing UI: would Linear ship this?
