# SESSION 11 — Inventory & Barcode
# Files: apps/mobile/app/(tabs)/more/inventory/**, apps/mobile/src/api/endpoints/inventory.ts (new),
#        apps/mobile/src/scan/** (new)

**Objective:** inventory on the phone — items, stock levels per warehouse, movements — plus the
capability that makes mobile BETTER than desktop here: the camera as a barcode/QR scanner, wired
into item search, invoice/PO line entry (sessions 09–10 stubs), and receiving counts. A
storekeeper walks the aisle scanning; the ERP follows.

---

## Before You Start

1. Open web inventory pages + API module → item fields, stock/warehouse endpoints, movement
   history shape, whether items carry a barcode field (READ the item model via
   `erp/inventory` API serializers — if no barcode field exists, adding one is a BACKEND
   decision: additive nullable field + admin/web edit surface; do it properly or defer with a
   PARITY.md note; never a mobile-only hack).
2. Read `expo-camera` current docs — barcode scanning API (`CameraView` barcode settings),
   permission flow, torch control.
3. Sessions 09/10 barcode stubs — the integration points you'll now fill.

"Do not write anything yet."

---

## Task A — Inventory module

1. Items ListScreen: server search, category/warehouse FilterSheet, stock-level column with
   low-stock emphasis EXACTLY as web renders it (word + colour pairing).
2. Item RecordScreen: details, per-warehouse stock table, recent movements (paginated), price
   info per pricing rules web shows, attachments stub, barcode display (renders the item's own
   barcode/QR via `react-native-svg` — no new dep — so a phone can BE the label in a pinch).
3. Item create/edit: FormScreen; barcode field fillable by scanning (Task B).
4. Stock movements list + movement detail (read views; adjustments/transfers only if web has
   them — mirror exactly what exists, PARITY.md rows for anything deferred).

## Task B — Scanner (`src/scan/`)

1. `ScanSheet`: full-screen camera modal — permission ask with a designed pre-prompt (explain
   WHY before the OS dialog; decline → designed fallback state with settings link), viewfinder
   with a calm reticle (no laser-red gimmicks; monochrome, token-timed pulse honouring reduced
   motion), torch toggle, haptic + brief highlight on successful decode. Debounce duplicate
   reads (same code within 2 s = one event).
2. Formats: EAN-13/8, Code128, QR (+ whatever the market needs — configurable constant).
3. API: `scanOne(): Promise<string>` (resolve on first decode) and `scanMany(onCode)` (continuous
   mode for receiving/counting: stays open, beep-haptic per code, running count chip).
4. Wire-ups:
   - Items list header: scan icon → `scanOne` → lookup by barcode (server endpoint — add the
     `?barcode=` filter param backend-side if missing; additive, tested) → item record or "غير
     موجود" designed state offering item-create with barcode prefilled.
   - Invoice/PO line pickers (09/10 stubs): scan → item added as a line, qty 1, cursor on qty.
   - Receiving (session 10): `scanMany` mode — each scan increments the matching line's received
     count; unknown codes collect into a visible "غير معروف" list, never silently dropped.
5. Global: search screen (cmd-K analogue) gets the scan icon too — scanning is a first-class
   way to navigate the ERP.

---

## Smoke Test

- [ ] Real device, real printed barcodes (print 3 EAN-13 samples): scan from items list → correct
      item record in under a second; unknown code → designed not-found + create-with-prefill
- [ ] Invoice create: scan 3 items → 3 lines, correct items, totals right
- [ ] Receiving continuous mode: scan the same code 5× → received count 5; unknown code appears
      in the unknown list
- [ ] Permission declined → designed fallback, app fully usable without camera
- [ ] Low light: torch toggle works; scanning still succeeds
- [ ] Stock levels match web for the same warehouse; movements paginate
- [ ] RTL pass; reduced-motion reticle static; tsc + parity green; PARITY.md inventory rows flipped

## Risks

- Item model lacking a barcode field → the Before-You-Start decision path (proper additive
  backend change or explicit deferral) — no shortcuts.
- Cheap-device camera performance → test scanning on a low-end Android; if decode is slow,
  restrict active formats to the configured set only.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_12_ACCOUNTING_VIEWS.md
```
