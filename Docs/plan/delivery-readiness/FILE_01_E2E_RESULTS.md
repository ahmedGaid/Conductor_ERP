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

## Phase 1c — CRM + Pricing + Workflows (2026-07-16)

**Drive:** create CRM opportunity + lead, edit a price list (add a tiered price line) + verify price
resolution, and create + **run** a workflow automation — in the browser at `http://localhost:5173`
as `admin`, Arabic/RTL UI. Verified side effects in Postgres via Django shell against a pre-drive
baseline.

**Baseline (pre-drive):** CRM Lead 2 · Opportunity 4 · Ticket 1 · Campaign 1 · Activity 0 ·
Pricing PriceList 3 / PriceListLine 7 · Workflow all tables 0.
(Note: CRM has **no separate Contact model** — leads/customers carry contact info; "contact" in the
plan maps to the Lead entity. Confirmed with the module owner's model set.)

| # | Step (UI action) | Result | Side effects verified |
|---|---|---|---|
| 1 | CRM → Pipeline → create opportunity (`Phase1c QA Opportunity`, ACME, WIDGET ×3 @ 100) | **PASS** | **OPP-2026-000005** created; amount 300.00 EGP, weighted 30.00 (10% Qualifying stage). Opportunity count 4→5 |
| 2 | CRM → Leads → add lead (`Phase1c QA Lead`, QA Test Co, Referral) | **PASS** | **LEAD-2026-000003** created, stage New. Lead count 2→3 (All 2→3, New 1→2) |
| 3 | Pricing → open STANDARD → add tiered price (GADGET, qty≥20 @ 250.00) | **PASS** | New PriceListLine added; STANDARD 5→6 lines. Row renders `GADGET / 20.0000 / 250.00 EGP / Always` |
| 4 | Price resolve (tiering, via pricing contract) | **PASS** *(after fix — see FAIL below)* | GADGET q25→250.00, q5→300.00; WIDGET q3→150.00 — all `default_list` STANDARD, deterministic |
| 5 | Workflows → create automation (start → script `2+3` → end) | **PASS** | Workflow **Phase1c QA Automation** v1 Active, 3 nodes; UI list + detail read back correctly |
| 6 | Workflows → **Run** the automation (UI Run button) | **PASS** | Instance `bdee4a59` ran to **completed**; script node output `{sum:5}`, end `{outcome:completed}`; execution-timeline viewer shows start→calc→done with advance logs |

### FAIL found + fixed — pricing had TWO default price lists (seed-integrity bug)

**Symptom:** GADGET (priced only on STANDARD) resolved to `None` for every unassigned customer,
while WIDGET resolved via a *different* list than expected.

**Root cause:** both RETAIL and STANDARD had `is_default=True`. The resolver's tier-3 default lookup
(`price_lists.default()` → `filter(is_default=True).first()`) then picks one arbitrarily (RETAIL),
so STANDARD-only items are unreachable. Origin = `scripts/seed_demo.py` `seed_pricing()`: it forced
STANDARD default with a raw `save()`, **not** the `set_single_default()` invariant, leaving RETAIL's
flag set. (The live API create/patch paths *do* call `set_single_default` — only the seed bypassed
it, same class as the Phase 0 "demo cash" seed artifact.)

**Fix:**
- `scripts/seed_demo.py` — `seed_pricing()` now calls `set_single_default(pl)` (demotes any other
  default) instead of a raw `save()`.
- Live DB cleaned: `set_single_default(STANDARD)` → single default = STANDARD.
- Regression test `erp/pricing/tests/test_resolve.py::test_set_single_default_demotes_other_defaults`
  — two-default scenario, asserts exactly one remains and a STANDARD-only item resolves
  deterministically. `pytest erp/pricing/tests/test_resolve.py` → **10 passed** (was 9).

**Post-fix resolve:** deterministic, single default STANDARD (see step 4).

**Environment caveat (NOT a product defect):** the workflow visual builder is a React Flow canvas.
In this headless browser, screenshots time out on the canvas, so coordinate clicks/drags (needed to
wire node→node edges) are unavailable, and palette node-add only registers after a "Fit View" pane
measure. Because of this the **create** graph was persisted via the `save_graph` service (the exact
contract the canvas POSTs), then the **run** was driven through the real authenticated UI Run button
(instance executed + timeline viewer confirmed). The workflow engine's create→start→run→decision
lifecycle is independently green: `pytest erp/workflow/tests/test_api.py` → **8 passed**. The
builder's server-side validation also works (it correctly rejected a 2-start-node graph with HTTP
400). **Recommend a 2-minute human smoke of the visual builder** (drag start→end, Save, Run) before
handover, since the canvas edge-drawing couldn't be exercised headlessly.

**Verdict: Phase 1c CRM+Pricing+Workflows — PASS** (one seed-integrity bug found + fixed +
regression-tested). Test artifacts left in demo DB: OPP-2026-000005, LEAD-2026-000003, STANDARD
GADGET@250 line, Phase1c QA Automation workflow + one completed instance — harmless demo data,
consistent with Phase 1a/1b artifacts. Ready to proceed to Phase 1d (Identity + Setup).

---

## Phase 1d — Identity + Setup (2026-07-16)

**Drive:** create a user + assign a role (Identity), and edit organization config (Setup) — in the
browser at `http://localhost:5173` as an admin (Ahmed Gaid, System Admin), Arabic/RTL UI. Verified
side effects in Postgres via Django shell against a pre-drive baseline. (Note: the in-app browser was
used this session — Claude-in-Chrome was disconnected; screenshots time out on this renderer, so the
UI was driven via authenticated in-page events + network capture, exactly what the real controls
POST/PATCH.)

**Baseline (pre-drive):** Users 7 · Groups/roles 4 (System Admin, Branch Manager, Accountant,
Auditor) · Branches 1 (Headquarters/HQ). OrgPreferences: company_name `Golden Eagle`, country
`Egypt`, vat_number `12121`, einvoice_enabled `True`, order_cancel_until `confirmed`, language `ar`.
(Note: **no Organization model** — the single tenant's editable config lives in `OrgPreferences`;
Branch is a `core` model with **no create/edit UI** — seed-only, 1 row. So Setup's editable
write-surface is the Organization settings page. Flagged, not a defect.)

| # | Step (UI action) | Result | Side effects verified |
|---|---|---|---|
| 1 | Admin → Users → Invite user (`phase1d_qa`, phase1d.qa@golden.example, Role=Accountant, Dept=Finance) | **PASS** | POST `/api/identity/users` → **201**. User created, group `Accountant`, department Finance (id 1), status `invited`. User count 7→8 |
| 2 | Users → select the new user → bulk **Activate** | **PASS** | POST `/api/identity/users/bulk` → **200**. Status `invited`→`active` |
| 3 | Users → select user → **Assign role** = Auditor → Apply | **PASS** | POST `/api/identity/users/bulk` → **200** `{affected:1}`. Group `Accountant`→`Auditor` (role reassigned) |
| 4 | Settings → Organization → E-invoicing toggle (on→off) | **PASS** | PATCH `/api/identity/org-preferences` → **200**. `einvoice_enabled` True→False |
| 5 | Organization → Company name → `Golden Eagle QA` (blur-save) | **PASS** | PATCH → **200**, body `{company_name:"Golden Eagle QA"}` |
| 6 | Organization → VAT number → `99887` (blur-save) | **PASS** | PATCH → **200**, `vat_number` 12121→99887 |
| 7 | Organization → Order-cancel window segmented → `Drafts only` | **PASS** | PATCH → **200**, `order_cancel_until` confirmed→draft |
| 8 | Restore org config to originals via UI (name, vat, order-cancel, einvoice) | **PASS** | 4× PATCH **200**; DB re-reads to baseline (`Golden Eagle` / `12121` / einvoice True / `confirmed`) |

**No product FAIL found.** Two hiccups were in the *test harness*, not the app: (a) dispatching a
non-bubbling `blur` event didn't reach React's delegated `focusout` listener — switching to a
`focusout` event fired the blur-save PATCHes correctly (the app saves-on-blur as designed); (b) one
mis-aimed click hit the bulk **Activate** button instead of **Assign role** — re-aimed at the button
after the role select and the assign went through. Both are artifacts of headless scripting, not
defects; every real control (invite, activate, assign-role, org-config save-on-change and
save-on-blur) worked and persisted on the first correct interaction.

**Verdict: Phase 1d Identity + Setup — PASS** (zero product bugs; no code changed → gates unchanged).
Test artifact left in demo DB: user `phase1d_qa` (active, Auditor) — harmless, consistent with the
Phase 1a–1c artifact policy; **suspend or delete before customer handover** if an extra admin-created
login is unwanted. Org config restored to baseline (no config drift left behind).

**Gap flagged for handover (not a Phase-1d defect):** there is **no UI to create or edit Branches**
(the `core.Branch` model is seed-only, 1 HQ row). If the customer needs multi-branch setup, that's a
missing setup surface — file under delivery backlog, not a write-flow FAIL.
