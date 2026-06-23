# Conductor ERP — working agreement

General ERP for Egyptian SMBs. Django modular-monolith (`apps/`) + React 18/TS/Vite web
(`apps/web`), **Arabic/RTL-first**, customer-hosted single-tenant. Quality bar: **Linear's craft,
Telegram's calm.** Brand personality: **quiet, precise, trustworthy.**

This file is deliberately short. The real rules live in **skills** — recall them; don't reinvent.

## Recall the right skill BEFORE you act (not after)
- **Any UI / design / styling / copy / identity / invoice / email / Arabic term / "is this on-brand"**
  → invoke the **`conductor-brand`** skill first. It owns the brand triad + Arabic lexicon + the
  brand-feel checklist.
- **Building/editing the React frontend** (`apps/web`) → invoke **`erp-frontend`** (tokens, logical-CSS,
  i18n, optimistic/toast/prefetch primitives, gates).
- **Resuming / status / "where are we"** → invoke **`erp-resume`**. For how a module was first built →
  **`erp-history`**.

If a task touches both UI behaviour and brand, recall **both** `conductor-brand` and `erp-frontend`.

## Source-of-truth map (open the file — don't answer from memory)
- Live status / next steps → `PROJECT_STATUS.md`
- Decisions & rejected paths → `DECISIONS.md`
- Build spec & phases → `files/ERP_BuildSpec.md`, `files/PHASE_*.md`
- Brand (3 pillars) → `Docs/Brand/` — Brief (*words*) · Directive (*in-app behaviour*) ·
  Visual Identity System (*assets + off-app surfaces + Arabic lexicon*)
- Design tokens (the only place raw hex is allowed) → `apps/web/src/styles/tokens.css`

## Hard rules — the safety net (the skills carry the full version)
- **Tokens only.** Raw hex lives ONLY in `tokens.css`; everywhere else `var(--color-*)`.
- **Logical CSS only.** `inline-start/end`, `block-*`, `text-align: start/end` — never physical
  `left/right`. RTL is the default; LTR must read identically.
- **i18n ar/en parity is build-blocking.** Every user-facing string is a key in BOTH `ar.json` and
  `en.json`. No hardcoded strings.
- **Monochrome chrome.** Colour lives *inside* pages (links/deltas/status), never in the app frame
  or on the logo. Near-black brand (near-white in dark). Colour always pairs with a word/icon.
- **One type voice** (IBM Plex Sans Arabic + Inter) and **one icon hand** (own single-stroke set in
  `src/app/icons.tsx`). No third font, no imported icon library, no CDN assets (customer-hosted).
- **Native Arabic.** One canonical word per concept (Identity System §6) — add it there before
  shipping. Human statuses, blame-free errors. Never two Arabic words for one concept.
- **Designed states.** Every empty/error/loading state is designed; never bare "No data"/blank.
- **Settled motion** from the token scale only; no bounce/spring; honour reduced-motion.
- **No new dependencies** without asking. Reuse existing primitives/components.
- **Money:** integer minor units on the wire; format/parse only at the edge (`lib/money.ts`).

## Before you say "done" (frontend work)
Run from `apps/web`: `node scripts/check-i18n-parity.mjs` and `npx tsc --noEmit`. Full mechanical
brand gate: `python scripts/gates/gate03.py` (repo root). **There is no JS unit-test runner.**
A green gate means *not mechanically off-brand* — still run the `conductor-brand` brand-feel checklist
(the judgment rules a gate can't see). Green gate **and** passed checklist = actually done.

## Style
Match surrounding code — comment density, naming, idioms. Don't add a brand; enforce the one that
exists, consistently, on every screen. When unsure if something is on-brand: open the doc, run the
checklist, ask "would Linear ship this?"
