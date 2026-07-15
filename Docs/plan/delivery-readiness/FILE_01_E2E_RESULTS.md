# FILE_01 — E2E Write-Flow Verification Results

Phase 1 of the delivery-readiness program (`FILE_00_ASSESSMENT.md`). Each session drives one module
cluster's **mutation** flows in the real browser as `admin`, verifies side effects, and logs
PASS/FAIL here. Any FAIL is root-caused + regression-tested against code (not this file).

Legend: **PASS** = drove in browser + side effects verified in DB. **FAIL** = broke; see the fix note.

---

## Phase 1a — Sales + Inventory (2026-07-15)

**Drive:** create sales order → confirm → deliver (stock issue) → invoice → collect payment, in the
browser at `http://localhost:5173` as `admin`, Arabic/RTL UI. Verified stock-on-hand and journal
postings via Django shell against a pre-drive baseline.

**Scenario:** order **SO-2026-000017** — customer **Acme Corp (ACME)**, warehouse **MAIN**,
1 line **WIDGET ×5 @ 100.00 EGP** (price auto-resolved from the **RETAIL** price list), tax **VAT14**.
Expected: net 500.00 · VAT 70.00 · gross 570.00 EGP (minor: 50000 / 7000 / 57000).

**Baseline (pre-drive):** WIDGET@MAIN qty 112, value 896000 minor (weighted-avg 8000/unit) ·
journal entries = 60 · last order SO-2026-000016.

| # | Step (UI action) | Result | Status after | Side effects verified |
|---|---|---|---|---|
| 1 | Create order (`طلب جديد` → `إنشاء الطلب`) | **PASS** | `مسودة` (draft) | Order SO-2026-000017 created; subtotal 50000, tax 7000, gross 57000; line WIDGET 5 @ 100 |
| 2 | Confirm (`تأكيد الطلب`) | **PASS** | `مؤكد` (confirmed) | Status → confirmed; no GL/stock movement (correct — confirm is a gate only) |
| 3 | Deliver (`تسليم`) | **PASS** | `تم التسليم` (delivered) | Stock issued: WIDGET@MAIN **112 → 107** (−5), value **896000 → 856000** (−40000). StockMovement `issue` qty 5 value 40000. Journal **JE-2026-000061**: Dr COGS(5000) 40000 / Cr Inventory(1200) 40000 |
| 4 | Invoice (`إصدار فاتورة`) | **PASS** | `تمت الفوترة` (invoiced) | invoiced_minor 57000, outstanding 57000, invoice_no JE-2026-000062. Journal **JE-2026-000062**: Dr AR(1100) 57000 / Cr Revenue(4000) 50000 / Cr VAT Payable(2100) 7000 |
| 5 | Collect (`تسجيل دفعة`) | **PASS** | `مدفوع` (paid) | paid_minor 57000, outstanding **0**. Journal **JE-2026-000063**: Dr Cash(1000) 57000 / Cr AR(1100) 57000 |

**Cross-checks (post-drive):**
- Journal entries **60 → 63** (+3, one per posting step). ✓
- Three order journals internally balanced: total Dr = Cr = 154000. ✓
- Accounts Receivable nets to zero across invoice + collect (57000 Dr − 57000 Cr). ✓
- Trial balance still balances after the drive: total Dr = Cr = 137,109,196. ✓
- **Bonus:** pricing resolve (RETAIL list → 100.00 EGP for WIDGET) worked in the order form. ✓

**FAILs / fixes:** none. The Sales→Inventory→Accounting integration (order lifecycle, weighted-average
COGS on issue, VAT-aware invoice posting, AR settlement on collect) is sound end-to-end.

**Note (not a bug):** the "collect" action posts the full outstanding immediately with no amount
dialog — full settlement in one click. Partial collection isn't exposed in this UI path (the service
layer supports partial payment); flag for Phase 4 handover docs if partial receipts are needed.

**Verdict: Phase 1a Sales+Inventory — PASS. Ready to proceed to Phase 1b (Purchasing+Accounting).**

---

## Phase 1b — Purchasing + Accounting (2026-07-16)

**Drive:** create purchase requisition → submit (auto-approve) → convert to PO → confirm → receive
goods (GRNI) → register supplier invoice (3-way match) → register payment, in the browser at
`http://localhost:5173` as `admin`, Arabic/RTL UI. Then posted one manual journal entry and
re-checked the trial balance. Verified stock, journal postings, and the trial balance via Django
shell against a pre-drive baseline.

**Scenario:** requisition → order **PO-2026-000012** — supplier **Globex Supplies (GLOBEX)**,
warehouse **MAIN**, 1 line **WIDGET ×20 @ 80.00 EGP** = 1,600.00 EGP (no VAT on this supplier's line).

**Baseline (pre-drive):** JE count 63 (last JE-2026-000063) · PR count 3 · PO count 11 ·
WIDGET@MAIN qty 107, value 856000 minor (weighted-avg 8000/unit, i.e. 80.00 EGP/unit).

| # | Step (UI action) | Result | Status after | Side effects verified |
|---|---|---|---|---|
| 1 | Create requisition (`طلب شراء جديد` → `إنشاء طلب`) | **PASS** | `مسودة` (draft) | PR-2026-000004 created; subtotal 1,600.00 EGP; line WIDGET 20 @ 80.00 |
| 2 | Submit for approval (`إرسال للموافقة`) | **PASS** | `مُوافَق عليه` (approved) | Auto-approved — under the amount threshold, no manual approval step needed |
| 3 | Convert to PO (`تحويل إلى أمر شراء`) | **PASS** | `مسودة` (draft) | PO-2026-000012 created from PR-2026-000004; same supplier/warehouse/line carried over |
| 4 | Confirm (`تأكيد الأمر`) | **PASS** | `مؤكد` (confirmed) | Status → confirmed; no GL/stock movement yet (correct — confirm is a gate only) |
| 5 | Receive goods (`استلام البضاعة`) | **PASS** | `تم الاستلام` (received) | Full receipt 20/20. Journal **JE-2026-000064** "GRN PO-2026-000012": Dr Inventory(1200) 1,600.00 / Cr GRNI(2150) 1,600.00. WIDGET@MAIN **107 → 127** (+20), value **856000 → 1016000** (+160000) |
| 6 | Register supplier invoice (`فاتورة المورد`) | **PASS** | `تمت الفوترة` (invoiced) | 3-way match: ordered 20 = received 20 = billed 20, all at 80.00 EGP/unit — no variance. billed_minor 160000, outstanding 160000. Journal **JE-2026-000065** "Bill PO-2026-000012": Dr GRNI(2150) 1,600.00 / Cr AP(2000) 1,600.00 — clears the GRNI suspense account exactly |
| 7 | Register payment (`تسجيل دفعة`) | **PASS** | `مدفوع` (paid) | paid_minor 160000, outstanding **0**. Journal **JE-2026-000066** "Payment PO-2026-000012": Dr AP(2000) 1,600.00 / Cr Cash(1000) 1,600.00 — clears AP exactly |
| 8 | Post manual journal (`قيد جديد` → `ترحيل القيد`) | **PASS** | posted | JE-2026-000067 "Manual test entry — bank charges": Dr Bank Charges(6100) 50.00 / Cr Cash(1000) 50.00. Form live-validated Dr=Cr=50.00 (`متوازن`) before submit accepted |

**Cross-checks (post-drive):**
- Journal entries **63 → 67** (+4, one per posting step + the manual entry). ✓
- Each PO journal internally balanced (GRN, Bill, Payment all Dr=Cr=1,600.00); manual JE Dr=Cr=50.00. ✓
- GRNI account line clears exactly: GRN posts Cr 1,600.00, Bill posts Dr 1,600.00 — net effect of this
  transaction on 2150 is zero. ✓
- AP account line clears exactly: Bill posts Cr 1,600.00, Payment posts Dr 1,600.00 — net zero. ✓
- Inventory value increase (+160000 minor) matches qty×cost exactly (20 × 8000 minor/unit). ✓
- Trial balance still balances after the drive: total Dr = Cr = **1,375,941.96 EGP**, status `متوازن`. ✓

**FAILs / fixes:** none. The Purchasing→Accounting integration (PR auto-approval below threshold,
PR→PO conversion, GRNI suspense posting on receipt, 3-way match on invoice with exact quantity/cost
match, AP settlement on payment) is sound end-to-end. Manual journal entry (unrelated to purchasing)
also posts correctly with live Dr/Cr balance validation in the UI.

**Note (not a bug):** like Sales' collect action, "register payment" posts the full outstanding
immediately with no amount dialog — full settlement in one click. Same flag as Phase 1a for
Phase 4 handover docs if partial supplier payments are needed.

**Verdict: Phase 1b Purchasing+Accounting — PASS. Ready to proceed to Phase 1c (CRM+Pricing+Workflows).**

---

## Phase 1c — CRM + Pricing + Workflows — _not started_
## Phase 1d — Identity + Setup — _not started_
