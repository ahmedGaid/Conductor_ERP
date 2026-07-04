# SESSION 13 — Acceptance + Regression + Brand-Feel Sign-off
# Files: none new — verification, polish, DECISIONS.md

---

## Before You Start

1. Re-read `FILE_00_INDEX.md` — the four tiers are the contract.
2. Seeded demo data; test in Arabic RTL FIRST, then English.
3. This acceptance includes a full **keyboard-only walkthrough** and a **feel pass** — budget
   real time for both.

---

## Full acceptance checklist

**Undo tier**
- [ ] Every converted op across all modules: instant apply → undo round-trip → state correct
- [ ] Toast expiry = action stands (reload check)
- [ ] Financial ops still confirm — post/approve/delete/payment spot-checked per module
- [ ] Documented skip lists match reality

**Keyboard tier**
- [ ] Keyboard-only session: navigate to a module list, j/k/enter into a record, back, x-select
      3 rows, bulk action, esc — per module, no mouse
- [ ] Nav inert in inputs/overlays everywhere; ⌘K and ⌘J never fight the list
- [ ] ShortcutsDialog complete, both languages

**Peek + views + timeline + inbox**
- [ ] Peek: warm-cache hover shows instantly (no request), RTL correct, space/esc keyboard flow
- [ ] Saved views: save/switch/rename/delete/default; user isolation probed; URL-driven
- [ ] Timeline on 5+ detail types, human wording, access-denied probe on foreign module
- [ ] Inbox: event → dot → row → navigate+read → all-read → designed empty state

**Arabic craft**
- [ ] Tabular digits on every dense screen; policy line in Docs/Brand; RTL negatives correct
- [ ] PDF before/after pair stored; Arabic invoice zoom-400% type check; ETA fields unchanged

**ARP differentiators**
- [ ] Digest: per-user module scoping, language pref, all-quiet silence, inbox delivery
- [ ] ⌘K bridge: question → panel running; disabled-assistant hides the row

## Regression checklist

- [ ] Receipts still fire on all converted actions
- [ ] Bulk-select unchanged where not driven by x
- [ ] Hover-prefetch still warms detail navigation (peek didn't break it)
- [ ] Assistant panel, threads, attachments, actions — untouched flows still work
- [ ] `pytest` per touched backend app green; parity + tsc + gate03 + bundle gate green
- [ ] p95 + query-budget tests still green (`test_security_perf.py`)

## The feel pass (judgment, not gates)

Run the `conductor-brand` brand-feel checklist end-to-end on: undo toast, focus ring, peek
card, views dropdown, timeline, inbox, digest copy, palette AI row. For each ask: **would
Linear ship this?** Anything that feels loud, springy, delayed, or translationese gets fixed
NOW, in this session.

## Sign-off block

- **Built:** undo-not-confirm across modules, universal list keyboard grammar, peek panels,
  saved views, record timelines, notifications inbox, number typography + digits policy,
  Arabic PDF pass, ambient digests, ⌘K↔AI bridge.
- **Not touched:** financial confirm flows, audit write path, tokens.css, money formatting
  logic, ETA compliance fields, contracts signatures. Zero new dependencies.
- **DECISIONS.md:** record — undo/confirm boundary (the kinds that stay confirm), the digits
  policy, digest schedule + silence rule.
- Update the `erp-status` skill anchor.

```
All green + feel pass done?
→ Commit, rename FILE_13_ACCEPTANCE_done.md
→ Merge to main. Fresh session for the next task.
```
