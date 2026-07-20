# Changelog

All notable changes to Conductor ERP are recorded here. Format: one `## vX.Y.Z — YYYY-MM-DD`
section per release, plain bullets. Internal doc (English only).

## v1.1.0 — 2026-07-20

- twenty-harvest feature set: saved views (list-page filter/sort presets), Kanban drag-and-drop
  stage changes (CRM pipeline), API keys + docs page, help journeys/glossary, custom fields,
  timeline/activity feed, inline edit + peek audit, empty-state taxonomy, system panel
  (degraded-state banners), AI cost/usage page, approval + AI workflow nodes, webhooks
  (signed delivery + retry), ⌘K command palette.
- Playwright E2E suite (`apps/web/e2e/`) covering Tier-1 write flows; gates extended 00–13 → 00–17
  (API schema snapshot, plus others from this cycle).

## v1.0.0 — 2026-07-16

- Core modules: Sales, Purchasing, Inventory, Accounting, CRM — with VAT, Egyptian e-invoicing
  (ETA), reporting, notifications, RBAC, and audit trail.
- Accounting depth: chart of accounts, journal entries, fiscal years/periods, trial balance.
- Workflow engine with webhooks; AI assistant (ask/chat) over scoped business data.
- Identity: JWT auth with HttpOnly refresh cookie, 2FA, per-role permissions, branches.
- Arabic/RTL-first UI with full ar/en parity; light/dark theming.
- Delivery-readiness hardening: partial payments, `provision_customer` go-live command, Playwright
  E2E coverage for Tier-1 write flows, smart-import fuzzy duplicate detection.
