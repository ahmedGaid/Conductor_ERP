# SESSION 15 — Arabic-First User Guide (in-app)
# Files: apps/web/src/help/ (extend), i18n locales, ⌘K entry (one line), Docs (source of truth pointer)

Twenty reference: a real user-docs product (user guide + glossary, translated). Ours ships
IN-APP (customer-hosted, no CDN, works offline) — task-based, Arabic-first, reusing the
handover guide's content (`Docs/plan/delivery-readiness/FILE_02_HANDOVER_GUIDE.md`).

---

## Before You Start

1. Open `apps/web/src/help/` → what exists (structure, routing, current content). EXTEND it.
2. Read `FILE_02_HANDOVER_GUIDE.md` (AR+EN one-pager) → the seed content + tone.
3. Open Identity System §6 (Arabic lexicon) → the glossary section renders FROM these terms;
   never invent a second word.
4. Open the ⌘K module (FILE_08) → help entries surface there too.

"Do not write anything yet."

---

## Task A — Guide structure (task-based, not feature-based)

10–15 journeys, each one page, ar written FIRST then en to match: create your first invoice ·
receive goods · record a payment · month-start opening balances · run trial balance · e-invoice
submission (ETA) · add a user + role · take a backup (links RUNBOOK) · fix a rejected approval ·
ask the assistant safely. Each page: numbered steps, one screenshot-free diagram max (own
components, no images that rot), "what can go wrong" box with blame-free fixes.

## Task B — Glossary "المصطلحات"

Rendered from a single data file whose entries mirror Identity System §6 (term ar, term en, one
plain line each). A drift here is a bug: the acceptance file checks lexicon ↔ glossary match.

## Task C — Reachability (three roads — mechanic 6 spirit)

`?` from anywhere (when not in the cheatsheet context) or the help nav item opens the guide;
⌘K: "مساعدة / Help: <journey title>" entries deep-link to pages; every designed empty state
MAY link its relevant journey (wire the two most valuable now: first invoice, first import).

---

## Smoke Test

- [ ] Every journey page renders in ar (RTL) and en with identical structure
- [ ] Glossary terms match Identity System §6 one-to-one (spot check 10)
- [ ] ⌘K finds "فاتورة أولى" and lands on the right page
- [ ] Works with the network cable pulled (fully local assets)
- [ ] parity + tsc + gate03 green; brand-feel checklist (calm, quiet, no marketing voice)

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_16_UX_STATES_BATCH.md in a FRESH session.
```
