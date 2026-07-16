# Changelog

All notable changes to Conductor ERP are recorded here. Format: one `## vX.Y.Z — YYYY-MM-DD`
section per release, plain bullets. Internal doc (English only).

## v1.0.0 — 2026-07-16

- Core modules: Sales, Purchasing, Inventory, Accounting, CRM — with VAT, Egyptian e-invoicing
  (ETA), reporting, notifications, RBAC, and audit trail.
- Accounting depth: chart of accounts, journal entries, fiscal years/periods, trial balance.
- Workflow engine with webhooks; AI assistant (ask/chat) over scoped business data.
- Identity: JWT auth with HttpOnly refresh cookie, 2FA, per-role permissions, branches.
- Arabic/RTL-first UI with full ar/en parity; light/dark theming.
- Delivery-readiness hardening: partial payments, `provision_customer` go-live command, Playwright
  E2E coverage for Tier-1 write flows, smart-import fuzzy duplicate detection.
