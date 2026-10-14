# Roadmap

Conductor ERP — customer-hosted, single-tenant, Arabic/RTL-first ERP for Egyptian SMBs
(internal category: ARP, Agentic Resource Planning). Django modular monolith + React/TS web.
Stage: beta / pre-launch. Queue authority: `Docs/plan/EXECUTION_ORDER.md`; lane board:
`Docs/plan/PARALLEL_PLAN.md`; scope and category: `Docs/ARP_STRATEGY.md`.

## Done

- **Platform** — correlation IDs, structured logging, error catalog, events, immutable audit trail,
  monitoring. JWT + HttpOnly refresh, 2FA, granular RBAC, data scope, approval limits, API keys (backend).
- **Core modules** — Accounting (GL, statements, VAT), Inventory (weighted average), Sales,
  Purchasing, CRM. Returns, partial flows, quotations and purchase requests included.
- **Egypt compliance** — ETA e-invoicing prepared and tracked in-app. Live filing stays simulated
  and the copy says so (claims discipline).
- **Workflow engine** — graph editor, approval nodes, outbound webhooks.
- **Frontend** — Arabic/RTL-first shell with tokens, logical CSS, ar/en parity, light/dark,
  saved views, ⌘K, Linear-grade polish, Playwright E2E, a11y check.
- **Smart Import** — parse, map, dedupe, auto-masters, adapters (sales, purchasing, journals,
  opening balances), DB-backed background runner. Accepted at 100k rows.
- **AI assistant** — chat, 23 actions (17 drafts + 6 guarded posting), multi-provider failover,
  attachments, governed memory, page-context distillation, "I don't know" discipline.
- **Release engineering** — `v1.0.0` (2026-07-16), `provision_customer`, `manage.py upgrade`,
  gates 00–17.

## Current

- **Customer handover readiness** — finish the pre-handover set. Remaining: delivery-readiness
  FILE_07 handover gate on a real customer box, and a customer-safe provisioning path (no shared
  demo-user password).
- **AI reliability, Phase 5 (orchestration)** — durable `AgentRun`/`AgentStep`, detached streaming,
  typed planner, structured clarify and mid-turn cost stop (T5.1–T5.10) have landed. Close out the
  rest of Phase 5.
- **Lane B backend queue** — twenty-harvest Tier 2, starting with FILE_19 (admin panel backend).
  Lane A (separate worktree) owns frontend and workflow.

## Next

- **Twenty-harvest FILE_20–21** — Tier 3 polish and acceptance.
- **Smart Import UI** — wizard, preview and report screens (lane A). Payments/receipts and
  inventory-opening adapters stay blocked on missing models.
- **API keys UI** and activity-timeline tab (lane A).
- **E-invoicing live** — real ETA submission once sandbox credentials arrive. Closes FILE_01 and
  unblocks FILE_02–05.
- **AI reliability, Phases 6–8** — guardrails and security, performance and cost, production hardening.
- **ARP phases A2, B, B2, C–F** — agent roster and daily brief, after queue positions 1–10 are done.
- **Open risks** — outstanding scope/SSRF security audit, GitHub Actions billing block
  (jobs die in ~2s account-wide), and founder call on the default `--color-text-subtle` contrast.
