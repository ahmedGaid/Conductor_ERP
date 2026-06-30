# Conductor — Product Charter & Correctness Constitution

> **Rewrite of `Docs/Prompts2/*`.** The original set was a *greenfield build script* on a
> PostgreSQL/Oracle-stored-procedure + NestJS stack. Conductor is already a **shipped release
> candidate** on **Django modular-monolith + React/Vite, Arabic/RTL-first**, with all five modules,
> accounting, VAT, ETA e-invoicing, RBAC, an immutable audit spine, and a Linear-quality UX already
> merged. So this document keeps what the original got *right* — the precedence-ordered trust rules —
> discards what was wrong for us — the stack and the "build from zero" premise — and **adds the
> dimensions the original ignored entirely**: Arabic identity, brand craft, speed, resilience, and
> the keyboard-first calm that makes Linear/Notion/Telegram feel inevitable.
>
> This is a **constitution for a living product**, not a TODO. Every rule names *where it already
> lives in this codebase* and *the invariant that proves it still holds*. Use it to review changes,
> onboard a module, or settle "is this on-brand / is this safe."

---

## Part 0 — What we keep, what we drop

**Keep from Prompts2 (these were genuinely good):**
- Precedence-ordered rules — when two rules conflict, the lower number wins. Removes argument.
- Money is typed; tax/FX come from an engine and are frozen at posting — never literals, never recomputed.
- State before edit; posted financials change only via Amend/Reverse as **linked successors**.
- Mutability is **data, not `if/else`** — a declarative matrix, not scattered checks.
- Field security = **absent from the payload**, default-deny — never "hidden in the UI."
- AI **suggests**, human **commits**, the **timeline records** both — no silent financial action.
- Every correctness rule maps to a **runnable invariant** that fails the build, not a test you skip.

**Drop from Prompts2 (wrong for Conductor):**
- ❌ "There is no existing app — build greenfield." There is. It is finished and merged.
- ❌ Posting/tax/FX as DB stored procedures. Our source of truth is the **Django service layer**
  (`erp/<module>/services.py`) over DRF, with DB constraints/triggers as defense-in-depth — *not*
  business logic in PL/pgSQL. Two sources of truth is the bug, not the feature.
- ❌ Re-scaffolding `conductor/db/ api/ web/` + a `psql` Makefile. We have `erp/` (13 Django apps) +
  `apps/web`. Gates are `scripts/gates/_run.py` (00–13) + `check-i18n-parity.mjs` + `tsc -b`.
- ❌ Rebuilding the Sales Order from scratch. It exists, with a cash-sale fast-path and PDF invoice.
- ❌ Generic English JSX with physical CSS. We are RTL-default; LTR must read identically.

**The single biggest gap in the original:** it had *zero* mention of Arabic, RTL, i18n parity, the
brand system, or what makes software *feel* world-class. For an Egyptian-SME ERP, that is not polish
on top of the product — **it is the product.** It is Part II of this charter, and it outranks most of
the original's UI advice.

---

# PART I — THE CORRECTNESS CONSTITUTION (precedence-ordered)

When any two rules conflict, **the lower number wins.** Print them on the wall.

### Rule 0 — Correctness outranks delight.
Money, tax, inventory quantity, and audit are non-negotiable. A beautiful screen that can misstate a
balance is a defect, not a feature. No deadline buys an exception.
- **Lives in:** `erp/accounting`, `erp/sales`, `erp/purchasing`, `erp/inventory` service layers.
- **Invariant:** the full gate suite (`scripts/gates/_run.py all`, 00–13) is green before "done."

### Rule 1 — Money is typed; tax and FX are engine-derived and frozen.
No bare numeric money crosses a boundary. Every amount is `(integer minor units, currency)`; format
and parse **only at the edge** (`apps/web/src/lib/money.ts`). Tax is resolved by the pricing/tax
engine from data — never `amount * 0.14` anywhere. FX is captured **at posting** and never recomputed.
- **Lives in:** `erp/pricing` (tax-inclusive resolver, price lists, effective dates), money on the
  wire as minor units, `lib/money.ts` at the UI edge.
- **Invariant:** no inline tax-rate literal in any module; posted documents carry a frozen rate; the
  i18n/format layer is the *only* place money becomes a string.

### Rule 2 — Context respects permission (row **and** field).
A forbidden field is **absent from the serialized payload**, not nulled and not CSS-hidden. The list
of available actions is computed **server-side** from permission **AND** state — the client renders
that list; it can never invent `post` or `reverse`. An out-of-scope record returns **404, not 403**
(don't confirm existence).
- **Lives in:** `erp/identity` (RBAC), DRF serializers as the single *shape* layer, org-scoped
  querysets, per-org action gating (e.g. `cancel_order` org-gated via `OrgPreferences`).
- **Invariant:** a low-grant role's payload for a sensitive document contains **no** `margin` /
  `cost` key (assert on key absence, not value); cross-org id → 404; clerk without `doc.post` never
  receives `post` in `actions`.

### Rule 3 — State before edit; posted = immutable; change via linked successors.
States are explicit (Draft → Posted/Confirmed → Reversed/Cancelled/Amended). Posted financials are
immutable. The only ways their effect changes are **Amend** (reverse + new linked draft) and
**Reverse** (linked opposite-sign successor). Mutability is governed by a **declarative matrix**, not
ad-hoc checks — a field's editability in a state is *data* the service consults.
- **Lives in:** `erp/workflow` (lifecycle + WorkflowTracker stages), document `status` on each
  transaction model, org-gated Cancel window.
- **Invariant:** an `UPDATE` to a posted document's financial fields is rejected; a reversal exists
  as a row linked to its original with opposite sign; mutability decisions trace to the matrix, not a
  scattered `if`.

### Rule 4 — Total traceability. Nothing escapes the timeline.
Every business write produces an `AuditEntry` (immutable: append-only, `save`/`delete` raise). It
carries actor, module, action, entity, before/after, result, and `correlation_id`. AI-originated
changes carry their origin **and** the human approver. The timeline is a **product surface**, not a
debug log — users read it to answer "who, what, why" (see StageSnapshot / EntityLink click-through).
- **Lives in:** `erp/audit/models.py` (`AuditEntry`), surfaced as WorkflowTracker stage snapshots +
  clickable `EntityLink` history.
- **Invariant:** every posted/reversed document has a corresponding audit row; `AuditEntry` cannot be
  updated or deleted; reversal pairs render linked so "why" is answerable in the UI.

### Rule 5 — AI suggests, human commits, timeline records. No exceptions.
AI may **propose**. AI may never post, reverse, reprice, or move stock on its own. Every AI effect
flows: `suggestion → human accept → the same guarded write path → audit(source='ai', approver=human)`.
A suggestion to edit a posted field is rejected exactly like a human's — AI gets **no** privilege.
- **Lives in:** AI is *postponed by strategy* (`GROWTH_PLAN.md`, `DECISIONS.md` Phase 4) — the APIs
  are deliberately "assistant-ready" (17 modules / ~127 routes audited) so this rule is the contract
  the future assistant must honor, not retrofit.
- **Invariant:** no audit row with `source='ai'` exists without a matching accepted suggestion bearing
  a human approver; the accept path reuses the human write path (no AI shortcut).

---

# PART II — THE CRAFT CONSTITUTION (what the original missed)

These are why Conductor wins the niche. Linear's craft, Telegram's calm, Notion's clarity — applied
to an Arabic-first ERP. They are not decoration; for our user, they are differentiation. Several
**outrank** the original's generic UI advice.

### Rule 6 — Native Arabic, RTL-default. Parity is build-blocking.
RTL is the default; LTR must read **identically**, not as an afterthought. Every user-facing string is
a key in **both** `ar.json` and `en.json` — asymmetry fails the build. One **canonical** Arabic word
per concept (Visual Identity System §6; e.g. warehouse = **مخزن**, never two words for one idea).
Statuses are human; errors are **blame-free**.
- **Lives in:** `apps/web/src/i18n` (1266 keys, parity-gated), `LocaleMiddleware` so even DRF errors
  follow the UI language, `arabicSearch` orthography normalization.
- **Invariant:** `check-i18n-parity.mjs` clean; no hardcoded user-facing string; new Arabic terms are
  added to the Identity System lexicon *before* shipping.

### Rule 7 — Logical CSS only; tokens only; monochrome chrome.
Never physical `left/right` — `inline-start/end`, `block-*`, `text-align: start/end`. Raw hex lives
**only** in `tokens.css`; everywhere else `var(--color-*)`. Colour lives **inside** pages
(links/deltas/status) and always pairs with a word or icon — never in the app frame, never on the
logo. Near-black brand (near-white in dark). One type voice (IBM Plex Sans Arabic + Inter), one icon
hand (`src/app/icons.tsx`), no third font, no imported icon library, **no CDN** (customer-hosted).
- **Lives in:** `apps/web/src/styles/tokens.css`, `src/app/icons.tsx`, per-module accent system.
- **Invariant:** `gate03.py` (mechanical brand gate) green — then the human brand-feel checklist
  (`conductor-brand` skill), because a green gate only proves *not mechanically* off-brand.

### Rule 8 — Every state is designed. No bare "No data."
Empty, loading, error, partial, and offline states are each deliberately designed with a calm line of
copy and a next action. A blank box or a raw stack trace is a bug. Loading prefers optimistic/skeleton
over spinners; errors say what to do next, never blame the user.
- **Lives in:** shared `DocumentStatusNote`, designed empty/error states across the four transaction
  pages, optimistic-update + toast primitives (`erp-frontend` skill).
- **Invariant:** no screen can reach a bare empty/error string; reviewer checks every new view for its
  four designed states.

### Rule 9 — Speed is a feature with a budget. *(new — my addition)*
The original said "progressive loading"; that's not enough. Set numbers and defend them. **Open any
document workspace and within ~1s the screen answers: what's happening, what can I do next, why.**
Interactions feel instant: optimistic write + toast, hover-prefetch on links, server round-trips never
block the first paint. Settled motion from the token scale only — no bounce/spring; honour
`prefers-reduced-motion`. The "5-second test" from the original is good but too lax — make it the
**1-second test** for the answer, 5 seconds only for the deep drawer.
- **Lives in:** optimistic primitives, hover-prefetch, WorkflowTracker/MetricsBar from a single fetch.
- **Invariant:** first meaningful paint of a document does not wait on the timeline or drawer fetches;
  motion durations come from the token scale.

### Rule 10 — Keyboard-first, command-driven. *(new — my addition)*
The fastest ERP in the niche is reachable without the mouse. A command palette (Notion/Linear `⌘K`)
to jump to any document, customer, item, or action by name — Arabic or English, orthography-tolerant.
Every primary action has a shortcut; every workspace is navigable by keyboard; the palette is the
single entry point that makes a 20-module ERP feel like one calm surface.
- **Lives in:** ⌘K `CommandPalette` (`apps/web/src/app/CommandPalette.tsx`) backed by a universal
  search endpoint (`erp/core/search_api.py`, `GET /api/core/search`) that finds customers, suppliers,
  items, sales/purchase orders and journals by name or number — Arabic-folded server-side (a 1:1
  mirror of `arabicSearch.ts`) and gated by `access.accessible_modules` (R2). `arabicSearch` +
  `EntityLink`/`/api/core/resolve` remain the link substrate.
- **Invariant:** every primary action is keyboard-reachable; the palette resolves Arabic and English
  queries to the same entity (tests: `erp/core/tests/test_search.py`).

### Rule 11 — One workspace skeleton; one drawer; compare = split. *(kept + sharpened)*
All document modules share one skeleton (breadcrumb → header → smart summary → workflow → metrics →
lines → tabs → timeline) so learning one module teaches all. **One** dynamic drawer with a
breadcrumb push/pop — never stacked drawers. Side-by-side needs are a **split/compare** view, a
first-class feature, not a second drawer. Keep **lifecycle (WorkflowBar)** and **human approval
routing (ApprovalStrip)** visually distinct — they are different questions.
- **Lives in:** shared `DocumentHeader`/`DocumentMenu`/`DocumentStatusNote`, RouteBreadcrumb (shows
  doc number), per-module accent.
- **Invariant:** no two drawers render at once; the same skeleton drives every transaction page.

### Rule 12 — Resilience and trust for an SMB that self-hosts. *(new — my addition)*
Our user is a small Egyptian business on imperfect infrastructure, often their own machine. So:
**one-day, self-serve setup** (Setup Wizard + Docker backup/restore + CSV import + smart defaults —
already shipped, defend it), graceful behaviour on a flaky connection, a backup story the owner
actually trusts, and **printable/exportable proof** (zero-dependency PDF invoice, ETA e-invoice) for
every financial document because in Egypt the paper trail is the product. No feature ships that a
non-technical owner couldn't recover from a bad day with.
- **Lives in:** Setup Wizard, Docker backup/restore, generic CSV import, `InvoiceDocumentPage` PDF,
  `erp/einvoice` (ETA), org smart defaults.
- **Invariant:** a fresh install reaches first real invoice within the cold-start budget; every
  financial document has a print/export path; backup + restore is one documented command.

---

## Part III — How to use this charter

**Reviewing a change** — walk Rules 0→12 in order; the first one it violates is the verdict. A craft
rule (6–12) can fail a change that's technically correct; a correctness rule (0–5) can fail a change
that's beautiful. Lower number wins.

**Onboarding a new module** — it inherits Part I for free (typed money, RBAC shape layer, state
matrix, audit spine, AI contract) and must earn Part II (Arabic parity, tokens, designed states,
speed budget, the shared skeleton). Reuse primitives; add no new dependency without asking.

**Before "done" (frontend)** — from `apps/web`: `node scripts/check-i18n-parity.mjs` and `npx tsc -b`.
Mechanical brand gate: `python scripts/gates/gate03.py` (repo root). Full suite:
`.\.venv\Scripts\python.exe scripts\gates\_run.py all` (00–13). **Green gate = not mechanically
off-brand. Then run the `conductor-brand` brand-feel checklist** — the judgment a gate can't see.
Green gate **and** passed checklist = actually done.

**The one-line test for any decision:** *"Would Linear ship this — in Arabic, on a shopkeeper's
laptop, without ever misstating the books?"* If yes, it's Conductor.

---

## Appendix — Rule → where it lives → invariant (quick map)

| # | Rule | Lives in | Proven by |
|---|------|----------|-----------|
| 0 | Correctness > delight | all service layers | `gates _run.py all` green |
| 1 | Money typed; tax/FX frozen | `erp/pricing`, `lib/money.ts` | no inline rate; frozen FX on posted |
| 2 | Permission shapes context | `erp/identity`, DRF serializers | sensitive key absent; cross-org → 404 |
| 3 | State before edit | `erp/workflow`, doc `status` | posted edit rejected; reversal linked |
| 4 | Total traceability | `erp/audit` (`AuditEntry`) | audit row per post; rows immutable |
| 5 | AI suggests, human commits | APIs assistant-ready (`DECISIONS.md`) | no orphan `source='ai'` audit |
| 6 | Native Arabic, RTL, parity | `i18n`, `LocaleMiddleware` | parity gate clean |
| 7 | Logical CSS, tokens, monochrome | `tokens.css`, `icons.tsx` | `gate03.py` + brand checklist |
| 8 | Every state designed | shared status/empty components | no bare empty/error |
| 9 | Speed budget | optimistic + prefetch | first paint independent of drawers |
| 10 | Keyboard-first / palette | ⌘K `CommandPalette` + `core/search_api` | live records found by name/number, Arabic-folded |
| 11 | One skeleton, one drawer, split-compare | shared Document* components | never two drawers |
| 12 | Self-host resilience | Setup Wizard, backup, PDF, ETA | cold-start budget; one-command restore |
