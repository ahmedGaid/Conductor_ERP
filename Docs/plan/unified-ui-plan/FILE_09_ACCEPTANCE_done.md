# FILE_09 — Acceptance, DECISIONS, docs, close-out

**Model:** Opus · **Est:** 25 min · **FINAL MERGE CHECKPOINT**

## Goal

Prove the whole program in both languages, write the durable records, queue the follow-ups.

## Before You Start

- FILE_00 index; all `_done` files' commit notes (drift log)
- `DECISIONS.md` format; `Docs/Brand/Conductor_Visual_Identity_System.md` §6

## Tasks

1. **Full walkthrough, AR first then EN** (run-dev, both themes):
   - Any page → bar sticks, ‹ › mirror browser history, breadcrumb correct, RTL arrows right
   - Invoice detail → primary + ⋯ (print, PDF, share-copy-link, doc verbs); restricted role
     sees fewer items, no gaps/greys
   - Report → PDF visible, CSV/Excel in ⋯, export matches filters + language
   - Any list → x/Shift/⌘A/Esc, bulk verb optimistic round-trip, تصدير المحدد CSV opens in
     Excel with correct Arabic
   - Orders/invoices/tickets → rings+words, chips, due markers, priority bars — colour never
     alone, digits Latin
   - ⌘K on any page lists that page's actions and runs them
   - Print one document + one list + one report — clean paper output
2. **DECISIONS.md entries:** split-pattern on reports; share = copy-internal-link (public links
   deferred); lifecycle-ring semantics (cancelled = hollow); priority-where-worked + overdue
   markers; bulk via existing endpoints only; no-checkbox-without-verb.
3. **Lexicon audit:** every term this program shipped exists in Identity System §6, one word
   per concept, used identically in menu/toast/palette.
4. **Queue follow-up plan stubs** (one paragraph each in `Docs/plan/arp-roadmap.md` or the
   queue doc): (a) attachments — invoice photo/memo upload + gallery + storage decision;
   (b) photo avatars; (c) smart-import ⋯ entry points (when Phase A engine lands).
5. Update the `erp-status` skill: program done, commits, what's queued.

## Gates (all, final)

- `apps/web`: `node scripts/check-i18n-parity.mjs`, `npm run build` (full: tsc -b + vite)
- Repo root: `python scripts/gates/gate03.py` (+ gate14 if separate)
- conductor-brand full brand-feel checklist — question 10 honestly: would Linear ship this?

Commit → rename `_done` → merge → update `erp-status` → END of plan.
