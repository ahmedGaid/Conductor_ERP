# Session 07 — Subscription billing + self-serve signup

**Goal:** money in the door — subscription plans, metered AI usage, self-serve signup that provisions
a tenant. Depends on Session 06 (tenancy) and Session 02 (AI usage to meter). Branch `feat/billing`.

## Scope
- **Plans:** a small, legible ladder (e.g. Starter / Growth / Scale) — differentiate by users,
  branches, and AI credits, not by hiding core accounting behind paywalls (trust > nickel-and-diming).
- **Payments:** Egyptian/MENA reality — support **Paymob** (cards + wallets, dominant in Egypt) and
  optionally Fawry; keep the gateway behind an adapter interface so it's swappable and so
  customer-hosted installs can run with billing disabled. Ask the user before adding an SDK dep.
- **AI metering:** count assistant tokens per tenant (from Session 02's per-tenant cap) → usage-based
  add-on or included credits per plan.

## Tasks
1. `Subscription`, `Plan`, `Invoice` (billing, public schema, distinct from customer-facing ERP
   invoices), `UsageRecord` (AI + seats). Dunning states → drive Session 06 tenant suspend/resume.
2. **Signup flow:** public marketing page → sign up → pick plan → pay → `create_tenant` runs → land
   in a seeded, ready company. Target under 5 minutes end to end. Designed every step; Arabic-first.
   Instrument the funnel (signup → first invoice created) — this time-to-value number is the YC metric
   Session 08 reports.
3. **Billing portal:** in-app plan/seat/usage management for the tenant admin; upgrade/downgrade;
   receipts. Reuse the report/PDF engine for billing receipts.
4. **Adapter + offline:** payment gateway behind an interface (mirror the workflow adapter pattern);
   `BILLING_ENABLED` flag off for customer-hosted installs (they don't pay you per seat).
5. **Security:** webhook signatures verified (Paymob/Fawry callbacks); billing endpoints scope-safe;
   never trust client-sent plan/price — resolve server-side.

## Done bar
- Self-serve signup provisions a live tenant and records a subscription; a failed payment suspends,
  a successful one resumes (Session 06 lifecycle).
- Gateway webhook signature verified (test with a forged signature → rejected).
- `gate:all` GREEN; billing-disabled single-tenant mode unaffected.
