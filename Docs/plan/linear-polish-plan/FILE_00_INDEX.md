# Conductor — Linear-Level Polish — Master Index

## Project Goal

Close the gap between "good ERP" and Linear-level product feel, in four tiers:
**Feel** (undo-not-confirm, universal keyboard grammar, peek panels), **Surfaces** (saved
views, record timeline, notifications inbox), **Arabic craft** (number typography, PDF
polish), **ARP differentiators** (ambient digests, ⌘K↔AI bridge). Quality bar: Linear's
craft, Telegram's calm — every session ends with the `conductor-brand` feel checklist, not
just green gates.

## Relationship to other plans

Independent of `Docs/plan/ai-workspace-plan/` and `Docs/plan/rag-knowledge-plan/` except:
- FILE_11 (digests) needs the tool catalog (already shipped, session 08) — no blocker.
- FILE_12 (⌘K bridge) needs the assistant panel (shipped) — no blocker.
- Recommended order overall: ai-workspace FILE_10 → rag-knowledge plan → THIS plan → remaining
  ai-workspace 11–15. But tiers here are self-contained; this plan can interleave at any merge
  checkpoint if priorities shift.

## Session Map

| # | File | What gets built | Est. | Model |
|---|---|---|---|---|
| 01 | FILE_01_UNDO_PRIMITIVE.md | `useUndoableAction` + undo toast + template module | 30 min | Opus |
| 02 | FILE_02_UNDO_ROLLOUT.md | Apply undo pattern across remaining modules | 25 min | Sonnet |
| 03 | FILE_03_LIST_KEYBOARD_NAV.md | `useListNav` (j/k/enter/x/esc) + template module | 30 min | Opus |
| 04 | FILE_04_KEYBOARD_ROLLOUT.md | Apply list-nav across remaining modules | 25 min | Sonnet |
| 05 | FILE_05_PEEK_PANELS.md | Hover/space peek card off existing prefetch data | 30 min | Opus |
| 06 | FILE_06_SAVED_VIEWS.md | Named per-user filter sets on list pages (model + API + UI) | 30 min | Opus |
| 07 | FILE_07_RECORD_TIMELINE.md | Audit activity timeline on detail pages | 25 min | Sonnet |
| 08 | FILE_08_NOTIFICATIONS_INBOX.md | In-app triage inbox (unread → done) | 30 min | Opus |
| 09 | FILE_09_NUMBER_TYPOGRAPHY.md | Tabular figures, one digits policy, RTL money alignment + gate | 25 min | Opus |
| 10 | FILE_10_PDF_POLISH.md | Arabic invoice/document PDF craft pass | 30 min | Opus |
| 11 | FILE_11_AMBIENT_DIGESTS.md | Scheduled morning digest via existing tools + notifications | 30 min | Sonnet |
| 12 | FILE_12_CMDK_AI_BRIDGE.md | Palette no-match falls through to assistant | 20 min | Sonnet |
| 13 | FILE_13_ACCEPTANCE.md | Acceptance + regression + brand-feel sign-off | 30 min | Opus |

Natural checkpoints (`---`): after 02 (undo tier), after 04 (keyboard tier), after 08
(surfaces tier), after 10 (Arabic craft tier). Merge at each; fresh session per file.
"Model" column = suggest `/model` before the session (rollouts are mechanical).

## Affected files (exhaustive)

Frontend (`apps/web/src/`):
- `lib/useUndoableAction.ts` (new), `lib/useListNav.ts` (new), the toast primitive (extend)
- `components/PeekCard.tsx` (new) + `EntityLink` (extend)
- List + detail pages across sales/purchasing/inventory/crm/accounting (additive wiring)
- `app/CommandBar.tsx` (bridge), `app/ShortcutsDialog.tsx` (document new keys)
- `pages/**` saved-views UI, notifications inbox page/panel
- `styles/` — a `font-variant-numeric: tabular-nums` utility + money-cell class (tokens only)
- `i18n/locales/ar.json` + `en.json` (every new string, parity build-blocking)

Backend:
- `erp/<core-ish app per read>/` SavedView model + API (session 06 decides placement by
  reading how per-user prefs are stored today)
- Notifications: list/mark-read API additions if missing (additive)
- `erp/assistant/` digest service + schedule entry (session 11)
- PDF templates/generation path (session 10 — read first, location TBD)

## Never touch

- `erp/audit/models.py` — read-only source for the timeline; render, never write
- `tokens.css` — no raw hex; typography utilities use existing tokens
- Module `contracts.py` signatures
- Financial confirm flows — undo tier applies ONLY to reversible ops (archive/rename/assign/
  status flips that have a clean inverse); post/approve/delete/payment KEEP explicit confirm
- No new npm/pip dependencies

## Ground Rules (every session)

1. **Read before write** — every session opens the named files first; patterns get REUSED
   (toast, prefetch, shortcut registry), never duplicated.
2. **Undo = inverse call, not soft-delete.** The undo toast fires the existing inverse
   endpoint (unarchive, restore previous value). No new "trash" infrastructure.
3. **Template-then-rollout.** Tier sessions build the primitive + ONE module as the template;
   rollout sessions copy it mechanically. Never hand-vary the pattern per module.
4. **Frontend hard rules:** tokens only, logical CSS only, ar/en parity, monochrome chrome,
   designed states, settled motion, honour reduced-motion.
5. **Gates before "done":** `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc
   --noEmit`; root: `python scripts/gates/gate03.py`; backend sessions: `pytest erp/<app>`.
   Bundle gate must stay green (route-split anything heavy).
6. **Done means renamed** — `_done` suffix, never reopened; next session = lowest open file.
7. **Brand-feel checklist** (`conductor-brand`) runs on every UI session — a green gate is
   not "done".

## How to use this plan

1. New Claude Code session → paste `FILE_00_INDEX.md` + next `FILE_NN` → check the Model
   column, switch with `/model` if suggested.
2. Reads → tasks → smoke test → gates → commit → rename `_done` → `/compact` → fresh session.
3. One file = one session. Merge at tier checkpoints.

## After all sessions complete

- FILE_13 acceptance in both languages (ar RTL first), keyboard-only walkthrough included.
- Update `DECISIONS.md`: undo-not-confirm boundary (what stays confirm), digits policy chosen.
- Update the `erp-status` skill anchor.

*Generated by ag-plan skill. Do not edit this index manually.*
