# GROWTH PLAN — "Start your company in one day"

> Strategy decision (2026-06-26): **postpone AI.** Win instead on **speed, clean feel, and
> one-day setup.** The product (Accounting, Inventory, Sales, Purchasing, CRM, VAT, e-invoice,
> RBAC) is already built and the UX is already Linear-quality. The one big thing MISSING is that
> a brand-new company cannot set ITSELF up — today only the dev seed scripts can.
> This plan fills that gap. Build top to bottom. Each task is small and shippable.

---

## The one sentence
**"Sign up in the morning, send your first real invoice before lunch."**
No consultants. No 6-month setup. That is the whole pitch while AI is postponed.

---

## PHASE 1 — Self-serve Setup Wizard (THE HEADLINE) 🎯

Goal: a new company goes from empty database to "ready to work" in under 30 minutes,
with no developer and no seed script.

A first-run wizard that appears when an organization has no data yet. Steps:

1. **Company profile** — name, logo, country, base currency, language (ar/en), VAT number.
2. **Chart of accounts** — pick a ready template (reuse what `seed_accounting` already builds)
   instead of building accounts by hand. One click = done.
3. **Tax setup** — set the VAT rate(s) (Egypt 14% default), enable/disable e-invoice.
4. **Invite team** — add a few users + pick their role (RBAC already exists, just expose it here).
5. **Finish** — land on the Dashboard with a short "what to do next" checklist.

Tasks for Claude Code:
- [ ] Backend: an `is_setup_complete` flag on the organization + a `POST /setup/*` endpoint group
      that wraps the existing seed/COA/tax/user services (do NOT rewrite them — call them).
- [ ] Frontend: `SetupWizardPage.tsx` (multi-step, keyboard-first, matches current design tokens).
- [ ] Route guard: if setup is not complete, redirect to the wizard after login.
- [ ] i18n: ar/en keys for every wizard string (keep parity — run the parity gate).
- [ ] Gate: `gate:all` stays GREEN; `tsc -b` from apps/web clean.

**Why first:** this is the actual differentiator now that AI is postponed. Nothing else matters
if a customer can't start on their own.

---

## PHASE 2 — CSV Import (makes setup real)

A new company already has customers, suppliers, and products in Excel. Let them bring it in.

- [ ] Generic CSV importer: upload → map columns → preview → confirm, with row-level error report.
- [ ] Wire it to the 3 highest-value lists first: **Customers, Suppliers, Items.**
- [ ] Download-a-template button for each (so the columns are obvious).
- [ ] Reuse existing create services for validation (one source of truth).

**Why:** without import, "one-day setup" is a lie for anyone who isn't brand-new.

---

## PHASE 3 — Perfect the daily money loop

Pick ONE everyday flow and make it flawless, because this is what they touch every day:
**Quotation → Sales Order → Invoice → (e-invoice) → mark paid.**

- [ ] Walk the whole loop as a real user and list every friction point (extra clicks, confusing
      labels, missing defaults). Fix them.
- [ ] Smart defaults everywhere (today's date, default warehouse, default tax, last-used customer).
- [ ] One clear primary action per screen (the "one obvious action" principle is already started).
- [ ] A printable / PDF invoice that looks on-brand (this is what the customer's customer sees).

**Why:** speed and feel are now the product. The daily loop is where that is won or lost.

---

## PHASE 4 — Leave the AI door open (cheap, do later)

Don't build AI. Just don't block it.

- [ ] Make sure every action also has a clean API endpoint (so an assistant can call it later).
- [ ] Keep data well-structured and labeled (already the case — just keep it that way).
- [ ] Note in DECISIONS.md: "AI postponed; APIs kept assistant-ready."

---

## How to work this plan
- Do phases in order. Inside a phase, ship one checkbox at a time as its own small PR.
- After each PR: run `gate:all` (00–13) GREEN + `tsc -b` from `apps/web` + i18n parity.
- Update `PROJECT_STATUS.md` "Active work" as phases complete; move history to the `erp-history` skill.
- Keep the design on-brand — recall the `conductor-brand` and `erp-frontend` skills before UI work.

## Definition of done for the whole plan
A stranger can sign up, set up their company, import their data, and send a real invoice —
**in one day, with no help from you.**

---

## Appendix — PR-by-PR checklist

Each row is one small, shippable PR. Ship in order. Per-PR ritual: `gate:all` (00–13) GREEN,
`tsc -b` from `apps/web`, i18n parity.

### Phase 1 — Setup Wizard (split by step)
- [ ] **1.0** Backend: `is_setup_complete` flag on org + empty `POST /setup/*` group + route guard
      (redirect to wizard if incomplete). *Done:* fresh org redirects to `/setup`.
- [ ] **1.1** Wizard shell: `SetupWizardPage.tsx`, multi-step frame, keyboard-first, ar/en keys.
      *Done:* empty steps navigable, parity gate green.
- [ ] **1.2** Step 2 **first** — Chart of accounts template (most magic per line; reuses
      `seed_accounting`). *Done:* one click seeds COA, visible in accounts list.
- [ ] **1.3** Step 1 — Company profile (name, logo, country, currency, language, VAT no.).
      *Done:* writes to the **same** settings surface a user edits later.
- [ ] **1.4** Step 3 — Tax setup (VAT 14% default, e-invoice toggle). *Done:* rate persists, editable later.
- [ ] **1.5** Step 4 — Invite team + role (reuses RBAC). *Done:* invited user lands with correct role.
- [ ] **1.6** Step 5 — Finish → Dashboard + "what to do next" checklist; flips `is_setup_complete`.

### Phase 1.5 — Backup / restore (new — don't skip)
- [x] **1.5.0** One-command DB dump + restore, documented for the self-hoster.
      *Done:* a stranger can take and restore a backup with no help. Bare-metal Windows kit shipped in
      Phase 11 (`deploy/backup/*.ps1`); Docker parity added (`deploy/docker/backup.sh` + `restore.sh`,
      RUNBOOK §5, gate13 coherence check) in `3044b02`.

### Phase 2 — CSV import (treated as real, not one PR)
- [x] **2.0** Import friction list: encoding (Win-1256/BOM/Arabic-from-Excel), duplicates,
      partial success, re-upload idempotency. *Done:* decisions written before code —
      `DECISIONS.md` "Phase 2.0 — CSV import friction decisions (2026-06-27)".
- [x] **2.1** Generic importer engine: upload → map → preview → confirm + row-level errors.
      *Done:* works on one list end-to-end — `erp/core/imports.py` engine + `ImportDialog` wired to
      Customers (`856fcea`); 10 tests; gate:all green. (Live browser click-through still pending.)
- [x] **2.2** Customers + template download (reuse create service for validation).
      *Done:* delivered within 2.1 (Customers was the proving list) — endpoint, template download
      button, and `CustomerSerializer` reuse all in `856fcea`.
- [x] **2.3** Suppliers + template. *Done:* reused the engine; `SUPPLIER_IMPORT` + endpoints +
      `ImportDialog` on the Suppliers list; shared DRF glue in `erp/core/import_api.py` (`905640e`).
- [x] **2.4** Items + template. *Done:* `ITEM_IMPORT` with a `to_kwargs` hook resolving
      `category_code` → Category (missing = row error, not silent null); type-choice + decimal
      validation; `ImportDialog` on the Items list (`6fb8504`). **Phase 2 import lists complete.**

### Phase 3 — Daily money loop
- [x] **3.0** Walk Quote→SO→Invoice→e-invoice→paid; write the friction list. *Done (2026-06-27):*
      friction list in `DECISIONS.md` "Phase 3.0 — Daily money loop friction list" (A smart-defaults,
      B step-count, C thin payment, D e-invoice context switch, E no PDF invoice, F label/i18n snags).
- [x] **3.1** Smart defaults (date, warehouse, tax, last-used customer). *Done (2026-06-27):*
      `lib/lastUsed.ts` + `hooks/useSmartDefault.ts` seed customer/warehouse/tax on new order+quotation
      from last-used (or the only option); qty defaults to 1; date is server-defaulted. **Unit-price
      prefill split out** — `Item` has no price field, needs a schema decision first (see DECISIONS.md
      finding A).
- [ ] **3.2** One primary action per screen.
- [ ] **3.3** On-brand printable/PDF invoice (conductor-brand checklist passes).
- [ ] **3.4** Time a cold stranger: signup → first invoice. **Record the number.**

### Phase 4 — Leave the AI door open
- [ ] **4.0** Audit every action has a clean API endpoint; list gaps.
- [ ] **4.1** Note in `DECISIONS.md`: "AI postponed; APIs kept assistant-ready."
