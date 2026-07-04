# SESSION 1 — Undo Primitive + Template Module
# Files: apps/web/src/lib/useUndoableAction.ts (new), the toast primitive file, one sales list/detail page, ar.json, en.json

---

## Before You Start

1. Find the toast primitive: grep `toast` under `apps/web/src/lib` and `components` → read how
   toasts are created, their variants, and whether one already supports an action button.
2. Open the sales list page (orders or customers — whichever has archive/rename/assign-style
   ops) → read how mutations run today (optimistic update pattern, receipts engine
   `lib/feedback/sales.ts` fires on actions — note how, so undo coexists with receipts).
3. Open `apps/web/src/api/` for the module → list which operations have a clean inverse
   already exposed (archive/unarchive, status set, field set). Write the pairs down.
4. Recall: financial ops (post/approve/payment/delete) are OUT of scope — they keep confirm.

Do not write anything yet.

---

## Task A — `useUndoableAction` in `lib/useUndoableAction.ts`

One hook, reused everywhere:

```ts
interface UndoableOptions<T> {
  perform: () => Promise<T>;          // the real call (page already applied optimistic state)
  undo: (result: T) => Promise<void>; // the inverse call
  message: string;                    // toast copy, already translated
  undoLabel?: string;                 // defaults t("common.undo")
  windowMs?: number;                  // default 5000
  onUndone?: () => void;              // page reverts its optimistic state here
}
```

Behaviour: run `perform` immediately (action feels instant); show toast with an Undo button
for `windowMs`; Undo click → call `undo(result)`, then `onUndone`, then confirm-toast
`t("common.undone")`. Toast dismissal/timeout = action stands. A second undoable action while
one toast is open: previous toast collapses (its window simply ends — no queue). Failures of
`undo` use the existing blame-free error toast.

If the existing toast primitive lacks an action button: extend IT (variant with one button,
settled motion, auto-dismiss respecting reduced-motion) — do not build a second toast system.

## Task B — Template wiring (ONE module: sales)

Convert the inverse-pair operations you listed in step 3 on the sales pages from
confirm-dialog (or fire-and-forget) to undoable:

- archive/unarchive
- rename / field edit where a previous value exists
- assign/unassign, status flips with a clean inverse

Each conversion: optimistic apply → `useUndoableAction` → receipts keep firing as before.
Remove the confirm dialogs ONLY for these converted ops. Anything without a clean inverse
keeps its current behaviour untouched.

## Task C — i18n

`common.undo`, `common.undone`, plus per-op messages (e.g. `sales.archived` "Order archived")
in BOTH `ar.json` and `en.json`. Arabic copy: calm, past tense, no exclamation.

---

## Smoke Test

- [ ] Archive an order → instant, toast with Undo → click Undo → order back, state + server
      both reverted
- [ ] Let the toast expire → action stands, no drift after reload
- [ ] Two rapid undoable actions → no queue weirdness; latest toast wins
- [ ] Undo endpoint failure (kill dev server mid-undo) → blame-free error, UI consistent
      after reload
- [ ] Financial ops (post/approve/delete) unchanged — still confirm
- [ ] Receipts still fire on converted actions
- [ ] Gates green: parity, tsc, gate03. Brand-feel checklist on the toast.

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_01_UNDO_PRIMITIVE_done.md
→ /compact → FILE_02_UNDO_ROLLOUT.md (suggest /model sonnet — mechanical copy of the template)
```
