# SESSION 18 — CRM Pipeline Kanban
# Files: apps/web/src (crm board page/view), erp/crm (stage-change service verify only), i18n locales

Twenty reference: any object renders as a kanban; for pipeline work the board IS the native
shape. Ours is ONE board (CRM leads by stage) — not a generic board engine (scope brake).

---

## Before You Start

1. Open `erp/crm/` models + services → the lead stage field, its allowed transitions, and the
   EXISTING stage-change service fn (drag calls it; if none exists, STOP → module owner adds it
   first — same STOP-rule as smart-import's missing service paths).
2. Check DnD reality: NO new dependencies. Grep apps/web for existing drag primitives
   (workflow canvas is @xyflow — canvas-only, likely NOT reusable for list DnD; unified-ui may
   have column-drag). If nothing reusable → implement minimal pointer-events DnD in the kit
   (grab, ghost, drop target highlight) — bounded to this board.
3. Open FILE_07's view tabs — the board is a VIEW of the leads page (table ⇄ board switch on
   the same page_key), not a second page.

"Do not write anything yet."

---

## Task A — Board rendering

Columns = stages in pipeline order; **RTL: column order flows start→end** (first stage at the
inline-start). Cards: lead name, company, owner chip, value (formatted minor units), days-in-
stage — reuse meta-chip kit. Column header: stage word + count + sum. Monochrome; stage
distinction by position + label, never color alone. Designed empty column state (one quiet
line).

## Task B — Drag = service call

Drop on another column → optimistic move + toast undo → stage-change service fn (RBAC, audit,
events all inherited). Illegal transition (service rejects) → card returns with the human
reason. **Keyboard/accessible fallback:** card ⋯ menu (and ⌘K on the record) offers "نقل إلى
المرحلة… / Move to stage…" — drag is an enhancement, never the only road.

## Task C — View switch

Table ⇄ board toggle on the leads page persists in prefs (and coexists with saved views:
board honours the active view's filters).

---

## Smoke Test

- [ ] Drag a lead two stages forward → persists (reload proves it); undo returns it
- [ ] Illegal transition bounces with human ar/en message; audit shows the legal move
- [ ] RTL board: stage 1 at inline-start in Arabic, mirrored correctly in English
- [ ] Move-via-menu works keyboard-only
- [ ] Board respects the active saved view's filters
- [ ] parity + tsc + gate03 green; brand-feel checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_19_ADMIN_PANEL.md in a FRESH session.
```
