# Conductor ARP — Unified UI Plan (page header bar + tables + meta columns) — Master Index

## Project Goal

One consistent surface on every page, Linear-grade:

1. **Page header bar** — a sticky bar on every page: ‹ › history arrows, breadcrumb, the page's
   ONE primary action, and the ⋯ menu. Never scrolls away. Same position, same trigger, every page.
2. **Unified ⋯ actions** — print / export PDF / CSV / Excel / share / duplicate / doc-specific verbs
   all live in the ⋯ menu (or the one visible primary), permission-filtered, palette-registered.
   Ends the "buttons on some pages, dots on others" drift.
3. **Unified tables** — every list table gets the sales>orders treatment: checkbox multi-select
   (`x`, Shift-range, ⌘A, Esc), bulk action bar, keyboard nav, FilterBar, hover-prefetch.
4. **Meta columns** — Linear-style at-a-glance columns, mapped to REAL Conductor data:
   lifecycle status ring, owner initials chip, fulfilment % on orders, overdue markers on money
   docs, priority bars on urgency-worked queues (tickets, leads, purchase requests).

> **Staleness note (deliberate):** written 2026-07-05, ahead of its queue turn. Code will drift.
> Snippets are interface-level BY DESIGN; "Before You Start" reads are mandatory, intent wins
> over literal snippet, note drift in the commit.

## Decisions locked at planning (re-confirm only if code contradicts)

1. **Split pattern on reports.** Report pages (trial balance, ledger…) keep ONE visible export
   button (Print/PDF via the print stylesheet); CSV/Excel/share fold into ⋯. Everywhere else:
   one primary action + ⋯. `ExportButtons` is absorbed by the new pattern.
2. **Share = copy internal link.** Clipboard + success toast. Receiver must be a logged-in user
   with permission. NO public/tokenized links, NO server-side PDF mailing (future plans).
3. **‹ › are history arrows only** (`navigate(-1/+1)`), dimmed when history empty, auto-flip in
   RTL via logical CSS. Breadcrumb already covers "up to list" — no third button.
4. **Permission-gated menus.** No privilege → item absent (not greyed). Quiet, blame-free.
5. **Status ring = lifecycle stage.** Fills by stage (draft 20% → paid/closed 100%) and ALWAYS
   sits beside the status word — colour never alone (brand rule). Per-doc-type stage maps.
6. **Owner chip = monochrome initials circle.** Photo avatars need an upload backend → follow-up
   plan, NOT here.
7. **Priority where the work needs it.** Priority bars only on queues genuinely worked by urgency
   and where the field exists (CRM tickets/leads; purchase requests only if the field exists —
   verify at build). Money docs get an **overdue / due-soon marker** instead (real due-date data,
   the collections signal Egyptian SMBs act on). NEVER a decorative red box.
8. **Bulk verbs reuse existing endpoints only.** Where a bulk endpoint is missing, the verb runs
   the existing single-row endpoint across the selection in one optimistic pass (the OrdersPage
   `bulkAct` pattern). No new backend endpoints in this plan.
9. **No new dependencies.** Rings/chips/bars are hand-drawn SVG/CSS in the existing icon hand
   (single-stroke, `currentColor`). No chart/avatar libraries.
10. **Arabic lexicon first.** Any NEW user-facing term (e.g. نسخ الرابط) is added to Identity
    System §6 BEFORE its i18n keys ship. One Arabic word per concept.

## Out of scope (do not let sessions pull these in)

- **Attachments** (invoice photo, memo image on documents) — needs upload API + storage +
  gallery. Own follow-up plan, queued after this one.
- **Photo avatars** — same follow-up.
- **Excel/CSV import** — owned by `Docs/plan/smart-import-plan/` (queue pos 5). The ⋯ menu gets
  import items only WHEN that engine lands.
- **Public share links / send-PDF-outside** — future, needs security review.
- **Sparkline history graphs** (Linear's tiny charts) — no per-doc history series worth the
  pixels today; revisit after Reports/BI.

## Session Map

| # | File | What gets built | Model | Est. |
|---|---|---|---|---|
| 01 | FILE_01_PAGE_HEADER_BAR.md | Sticky PageHeaderBar primitive: ‹ › arrows + breadcrumb + action slots; wired in AppShell | Opus | 30 min |
| 02 | FILE_02_DOC_PAGES_ROLLOUT.md | Header bar + ⋯ menu on ALL document detail pages (extend the 4 DocumentHeader pages to every doc type) | Sonnet | 30 min |
| 03 | FILE_03_LISTS_REPORTS_ROLLOUT.md | Lists: New + ⋯ (print/export). Reports: split pattern, retire standalone ExportButtons row | Sonnet | 30 min |
| 04 | FILE_04_SHARE_PERMS_PALETTE.md | Share=copy-link item, permission filtering, register page actions in ⌘K palette | Sonnet | 25 min |
| 05 | FILE_05_TABLE_KIT.md | Selection checkbox column + bulk-bar as shared kit; sales>orders stays reference; fan to sales+purchasing | Opus | 30 min |
| 06 | FILE_06_TABLES_ROLLOUT.md | Fan table kit to remaining lists (inventory, accounting, CRM, admin/users) + per-module bulk verbs | Sonnet | 30 min |
| 07 | FILE_07_META_PRIMITIVES.md | StatusRing, OwnerChip, PriorityBar, DueMarker components + per-doc-type lifecycle maps | Opus | 30 min |
| 08 | FILE_08_META_ROLLOUT.md | Meta columns fanned to orders, invoices, POs, requests, tickets, leads… | Sonnet | 30 min |
| 09 | FILE_09_ACCEPTANCE.md | Both-language acceptance (ar RTL first), gates, brand-feel checklist, DECISIONS entries | Opus | 25 min |

Merge checkpoints (`---` boundaries): after **04** (header bar + actions complete app-wide),
after **06** (tables unified), after **09** (meta columns + acceptance).

## Affected files (exhaustive at planning time; verify at build time)

Frontend (`apps/web/src/`) — this plan is frontend-only:
- NEW: `components/PageHeaderBar.tsx` (+css), `components/SelectionColumn.tsx` (or kit docs),
  `components/StatusRing.tsx`, `components/OwnerChip.tsx`, `components/PriorityBar.tsx`,
  `components/DueMarker.tsx`, `lib/lifecycle.ts` (per-doc-type stage maps)
- CHANGED: `app/AppShell.tsx` + `AppShell.css` (bar mount, sticky), `app/RouteBreadcrumb.tsx`
  (moves into the bar), `app/CommandBar.tsx` (only if arrows land there instead — decide in 01),
  `components/DocumentMenu.tsx` / `DocumentHeader.tsx` (absorbed/extended),
  `components/ExportButtons.tsx` (retired into the pattern), every `pages/**` list + detail page,
  `app/PaletteActionsContext.tsx` consumers, `i18n/locales/ar.json` + `en.json`
- READ-ONLY use of: `hooks/useRowSelection.ts`, `hooks/useListKeyboardNav.ts`,
  `lib/optimistic.ts`, `lib/prefetch.ts`, existing `BulkActionBar`, `Popover`, `Tooltip`
- `Docs/Brand/Conductor_Visual_Identity_System.md` §6 — new Arabic terms

Backend: none (rule 8). If a session discovers a truly missing single-row endpoint, it lists it
in the commit + `erp-status` and skips the verb — never invents backend inline.

## Never touch

- `apps/web/src/styles/tokens.css` — no new raw hex without a token
- Physical CSS (`left/right`) — logical properties only; RTL is default
- The keyboard layer's contracts (`x`/⌘A/Esc semantics, `g` leader, typing/modal stand-down)
- Existing module service write-paths
- **No new npm dependencies.**

## Ground Rules (every session)

1. **Read before write** — the named reads, literally; code drift → intent wins, note it.
2. **Additive** — nothing existing breaks; pages not yet rolled out keep working untouched.
3. **Frontend hard rules** — tokens only, logical CSS, ar/en parity, designed states, monochrome
   chrome (the bar is CHROME → strictly monochrome; colour only via status words/rings inside
   the work), settled motion, human blame-free errors, Latin digits both locales.
4. **One visible primary per page.** If a session finds a page wanting two, the second goes in ⋯.
5. **Gates before "done"** — `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc -b`;
   repo root: `python scripts/gates/gate03.py`. UI sessions also run the `conductor-brand`
   brand-feel checklist (esp. "would Linear ship this?").
6. **Done means renamed** — green + committed → rename the file with `_done`.

## How to use this plan

1. New Claude Code session → load this index + the next `FILE_NN` (lowest without `_done`).
2. Model check (Model column) → suggest `/model` switch in one line if Sonnet fits.
3. Reads → tasks → smoke test → gates → commit → rename `_done` → update `erp-status` → tell the
   user to start a fresh session. One file = one session.

## After all sessions complete

- FILE_09 acceptance in both languages (ar RTL first) across sales, accounting, CRM.
- DECISIONS.md entries: split-pattern on reports, share=copy-link, lifecycle-ring semantics,
  priority-where-worked, bulk-via-existing-endpoints.
- Queue the follow-up plan: **attachments + photo avatars** (upload API, storage, gallery).
- Update the `erp-status` skill.
