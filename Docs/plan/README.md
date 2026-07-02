# Conductor ERP — Path to "Linear of ERP" + YC (session plan)

> Written 2026-07-02. Each file below is **one Claude Code session**, self-contained, ordered by
> dependency. Feed them one at a time. Every session ends with the same **done bar**:
> `.\.venv\Scripts\python.exe scripts\gates\_run.py all` GREEN, and (if UI touched) from `apps/web`:
> `node scripts/check-i18n-parity.mjs` + `npx tsc -b` + repo-root `python scripts/gates/gate03.py`.
> Recall skills BEFORE acting: `conductor-brand` (any UI/copy/identity), `erp-frontend` (apps/web),
> `erp-status`/`erp-resume` (state). Tokens only, logical CSS only, ar/en parity, monochrome chrome.

## The thesis (what "unbeatable" means here)
Not more features than SAP. **Fewer, faster, calmer, trustworthy** for Egyptian/MENA SMBs, with an
AI layer that turns a photo of a supplier invoice into a posted, ETA-compliant document in seconds.
Win on: **speed** (sub-second interactions), **one-day setup**, **native Arabic craft**, **AI that
does the boring data-entry**, and **trust** (correct money, correct tax, correct audit trail).

## Prerequisite
Merge **PR #28** (`feat/action-feedback-receipts`) first — Session 02's review UI builds on the
receipt engine, and every session branches from `main`.

## Order of execution
| # | Session file | Why this order |
|---|---|---|
| 00 | `00-security-hardening.md` | Fix data-scope leak + SSRF + auth before adding surface area or tenants. Blocks SaaS. |
| 01 | `01-perf-and-trust-bar.md` | Lock the speed/trust bar (p95 budgets, correctness invariants) so every later feature inherits it. |
| 02 | `02-ai-assistant-and-invoicing.md` | The headline differentiator. Depends on 00 (scoped data the AI reads) + PR #28 (receipt engine). |
| 03 | `03-core-costing.md` | Costing closes the accounting loop (COGS/landed cost). Feeds reports. |
| 04 | `04-core-hr-payroll.md` | HR/payroll — Egypt-specific (social insurance, tax brackets). Feeds GL + reports. |
| 05 | `05-reports-and-bi.md` | Reporting/BI layer over accounting+costing+HR. Depends on 03/04 data. |
| 06 | `06-saas-multitenancy.md` | Single-tenant → multi-tenant. Depends on 00 (scoping) being real. Biggest arch change. |
| 07 | `07-billing-and-provisioning.md` | Subscription billing + self-serve tenant provisioning. Depends on 06 (+ 02 for AI metering). |
| 08 | `08-yc-brand-gtm.md` | Positioning, pitch narrative, traction plan, demo script. Non-code; can run in parallel. |
| 09 | `09-eta-integration.md` | Real ETA API (the current submit/poll is a stub). Any time after 00; **before the 08 demo is recorded** — the wedge must be real. |

## Backlog (not scheduled — don't let sessions absorb these silently)
Bank reconciliation · fixed assets + depreciation · manufacturing/BOM · POS · ETA B2C receipts ·
SaaS observability (error tracking, uptime, per-tenant health) · mobile companion. Promote each to a
numbered session file when its turn comes.

## Non-negotiables carried into every session
- **Money:** integer minor units on the wire; format/parse only at the edge (`lib/money.ts`).
- **No new deps without asking.** Reuse existing primitives.
- **Every state designed** (empty/error/loading). **Blame-free Arabic errors.**
- **Deny-by-default RBAC**, now extended to **data scope** (see 00).
- **Offline-safe:** no CDN assets, customer-hostable even in SaaS mode (same code, tenancy is config).
