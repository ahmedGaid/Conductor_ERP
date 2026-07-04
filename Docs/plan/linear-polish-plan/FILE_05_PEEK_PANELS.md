# SESSION 5 — Peek Panels (hover cards off prefetch)
# Files: apps/web/src/components/PeekCard.tsx (new), the EntityLink component, its css, ar.json, en.json

---

## Before You Start

1. Open `EntityLink` (grep under `components`/`lib` — shipped with hover-prefetch in plan
   session 01) → read exactly what it prefetches, into which cache, on what hover delay.
2. Open the API detail payloads it prefetches (one per entity type: customer, supplier, item,
   order) → decide the 3–5 facts a peek shows per type. Money via `lib/money.ts` ONLY.
3. Check an existing popover/dropdown in the app (⌘K? filters?) → reuse its positioning +
   focus pattern; do not add a positioning library.
4. Recall `useListNav` (session 03): `space` on the active row should peek — check for key
   conflicts.

Do not write anything yet.

---

## Task A — `PeekCard.tsx`

One generic card: entity icon + title + type-specific fact rows + "open →" affordance.
Per type (start with customer, supplier, item):

- customer: balance owed, recent orders count, last activity
- supplier: balance owed to, open POs
- item: on-hand qty, reorder point state, price

Rendering rules: data from the SAME cache the prefetch fills (no second fetch when warm; if
cold, show the existing skeleton pattern, small). Monochrome; colour only where the app
already colours (deltas/status words). Settled motion from the token scale; honour
reduced-motion (no scale/fade beyond tokens). Logical positioning (inline-start/end aware) —
must sit correctly in RTL.

## Task B — Triggers

- `EntityLink` hover ≥ 400ms → peek (pointer only, not touch); leave → close after short
  grace. Keyboard: focus + `space` on a list's active row (via `useListNav`'s active index)
  peeks the row's primary entity; `esc` closes peek first, selection second.
- Dismiss on scroll/route change. Never traps focus.

## Task C — i18n

Fact labels per entity type ×2 locales (reuse existing term keys where they exist — check
before adding; one canonical Arabic word per concept).

---

## Smoke Test

- [ ] Hover a customer link → card with balance/orders, correct money format, no network call
      when prefetch already warmed it (check network tab)
- [ ] RTL: card position + text alignment correct
- [ ] Keyboard: j to a row, space → peek; esc closes; screen stays keyboard-navigable
- [ ] Touch device emulation → no peek (tap = navigate, unchanged)
- [ ] Reduced-motion → card appears without animation
- [ ] Gates green; brand-feel checklist on the card (quiet, dense, no noise)

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_05_PEEK_PANELS_done.md
→ /compact → FILE_06_SAVED_VIEWS.md
```
