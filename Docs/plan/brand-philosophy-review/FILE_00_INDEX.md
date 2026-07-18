# Brand Philosophy Review — Master Index

> **Review the ENTIRE app against the Product Philosophy front door**
> (`Docs/Brand/Conductor_Product_Philosophy.md`, created 2026-07-18) and the triad it points to.
> Not a redesign — a **judgment audit**: drive every screen, score it against the 8 Conductor
> Standard, file ranked findings. Fixing is a SEPARATE pass (findings → their own sessions).

## The rubric (score every screen against these)
The 8 Conductor Standard = the ship test. Re-asked as the 7 decision-questions per screen:
1. **Invisible complexity** — one obvious thing, one primary action?
2. **Instant performance** — feels instant, no spinner where cached data could paint?
3. **Calm by default** — monochrome chrome; colour only inside the work, paired with word/icon?
4. **Trust through transparency** — says what happens *before*, reassures *after*, reversible?
5. **Consistency** — same action behaves the same everywhere?
6. **Human AI** — AI bits notice/explain/protect, drafts-only + gated (N/A if none)?
7. **Craft** — type, spacing, motion, Arabic language, errors feel designed?
8. **Business confidence** — user leaves more informed and in control?
Plus the closer: **"Would Linear ship this?"** — an honest "no" = a finding.

## Output per screen (uniform, so it rolls up)
`screen · one-line verdict · which Standard(s) fail · severity (P1 break / P2 off-brand / P3 polish)
· the specific fix`. Findings roll into the scorecard artifact.

## Review sessions (drive the real UI, ar + en, light + dark)

| Session | Surface | Screens |
|---|---|---|
| **A** | **App frame + global states** (shell, sidebar, sticky header, ⌘K, notifications, login, empty/error/loading/no-permission taxonomy, error boundary) | cross-cutting |
| **B** | **Accounting** | 16 (dashboard, journals, TB, GL, IS, BS, cash-flow, VAT, assets, cost-centers, bank-rec, budgets, report-builder) |
| **C** | **Inventory** | 10 (items, warehouses, movements, stock-on-hand, counts, batches) |
| **D** | **Sales** | 9 (orders, order→invoice, quotations, customers) |
| **E** | **Purchasing** | 8 (orders, import, requests, suppliers) |
| **F** | **CRM** | 7 (pipeline/kanban, opportunities, leads, tickets, campaigns) |
| **G** | **Settings + Admin + Pricing** | 16 (profile, appearance, dashboard, nav, notifications, a11y, org, branches, webhooks, custom-fields, developers, users, roles, pricing) |
| **H** | **Assistant + Help + E-invoice + Workflows** | assistant/knowledge/ops, help center, /einvoice, workflows/instances |

~85 routes total. One session = one surface = one sitting. Ar+en, light+dark each.

## Method per session (deterministic)
1. Recall `conductor-brand` (rubric + Arabic lexicon) + `erp-frontend` (what's normal).
2. Run the app (`run-dev.ps1`, login `admin`/`Dev12345!`). Drive each screen in the surface.
3. For each: answer the 7 questions honestly; note every "no" as a finding with severity + fix.
4. Check the Arabic specifically against Identity §6 (one canonical word, human status, blame-free
   error) — this is where craft usually slips.
5. Append findings to the scorecard artifact (see below). Do NOT fix in this pass.

## The tonight deliverable
`brand-review-scorecard` artifact — the rubric + full inventory + systemic findings already known
from the QA audit, published so the founder can skim tonight. Per-screen scores fill in as sessions
A–H run. (Built 2026-07-18.)

## Systemic findings already known (seed the scorecard — from the QA audit)
- **No app-wide error boundary** → any render crash = white screen. Fails Standard 4 + 7 globally.
  (Fix owned by `pre-handover-hardening/FILE_03`.)
- **Most routes not code-split** (App.tsx eager-imports ~40 pages) → slower first paint. Tension
  with Standard 2 (instant). Candidate finding for Session A.
- E-invoice status copy must not *claim* live ETA submission (Standard 4 + Brief §12 claims
  discipline) — verify in Session H. (Decision owned by `pre-handover-hardening/FILE_01`.)

## Change log
- **2026-07-18 — Created.** Review program + tonight scorecard. Positioned in `EXECUTION_ORDER.md`
  as pos **BR** (founder-paced, off critical path; does not block handover — it feeds v1.1 polish).
