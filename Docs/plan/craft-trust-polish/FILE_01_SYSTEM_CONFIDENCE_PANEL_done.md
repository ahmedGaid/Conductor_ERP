# FILE_01 — System Confidence panel (done 2026-07-19)

## Scope
The reassurance complement to the dashboard's "Needs attention today" panel — a calm, positive
health strip: Books balanced · VAT ready · Backups · Stock health · Assistant connected. Each
signal pairs its colour with a word (never colour alone) and deep-links to its proof.

## What shipped
- **Backend** — `erp/monitoring/confidence.py`, `GET /api/dashboard/confidence/`
  (`IsAuthenticated`, not admin-gated — unlike the sibling `SystemStatusView`). Five signals,
  each computed from real state, never fabricated:
  - `books` — `accounting.contracts.trial_balance_summary()["is_balanced"]`
  - `vat` — current fiscal period exists and is open (`current_fiscal_period()`)
  - `backups` — reuses `status_api._backup_report()`; ok if last snapshot ≤48h old
  - `stock` — `inventory.contracts.low_stock()` empty
  - `assistant` — `assistant.client.enabled()` AND a real provider API key is configured
    (`provider_chain()` alone doesn't prove this — it falls back to `["anthropic"]` even
    with no key set, per its own docstring)
  Each signal is computed defensively in a try/except loop — one failing check degrades to
  `warn`, never breaks the whole panel (same spirit as `DashboardPage`'s `AttentionPanel`).
  Mounted at `config/urls.py` under `api/dashboard/`.
- **Frontend** — `apps/web/src/api/confidence.ts` (client), `DashboardPage.tsx`
  (`ConfidencePanel` component + `loadDashboard` fetch, defensive `.catch(() => [])`),
  `DashboardPage.css` (`.dash__confidence-*`, reusing the `AttentionPanel` visual pattern —
  success/warning tokens, never colour alone), `dashboardWidgets.ts` (new `confidence` widget,
  hideable/reorderable from Settings → Dashboard like every other widget).
- **i18n** — `dashboard.confidence.*` (title + 5 signals × ok/warn phrasing) and
  `settings.dashboard.widgets.confidence`, ar + en.

## Verified
- `pytest erp/monitoring` — 30 passed (5 new tests: panel shape, a failing signal degrades to
  warn not 500, backups-unconfigured → warn, assistant-disabled → warn, non-admin/anonymous
  access rules).
- `node scripts/check-i18n-parity.mjs` — 2030 keys, ar/en parity green.
- `npx tsc -b` — clean.
- `python scripts/gates/gate03.py` — green.
- **Live (rung 3):** port 8000 was occupied by the separate `erp-demo` docker-compose stack
  (not this checkout — left untouched). Verified instead via a temporary local `manage.py
  runserver` on 8010 with the Vite proxy briefly repointed, then fully reverted (`git diff
  vite.config.ts` clean after). Logged in as `admin`, confirmed all 5 signals render with the
  real dev DB's actual state (Books balanced / VAT ready / **Backups not confirmed** — honestly
  reflects `BACKUP_DIR` unset in dev / Stock health good / Assistant connected), each linking to
  its real page (`/accounting/trial-balance`, `/accounting/vat-return`, `/settings`,
  `/inventory`, `/assistant`). Arabic strings verified via the automated parity gate only —
  in-browser language toggle didn't take effect (a user-preference setting unrelated to this
  change, not investigated further).

## Deviations
- "Backups" deep-links to `/settings` (no dedicated backups page exists yet — that's
  `twenty-harvest/FILE_19` Task B, System settings page, currently `todo` in B's Wave 4).
  Revisit the link once that page ships.
- "Assistant connected" means *configured + enabled*, not a live network ping — pinging a
  provider on every dashboard load would cost real API calls for a status dot; a config check is
  the calm, cheap, honest proxy the brand's "never fabricate" rule allows.
