# SESSION 9 — Sales
# Files: apps/mobile/lib/presentation/pages/sales/**, sales domain/data layers (new)

**Objective:** the first full business module on mobile, and the template for how CREATE works on
a phone: customers and invoices — list, detail, and a full invoice-creation flow that goes
through the exact same API/contracts as web. When this session lands, a salesperson can issue a
real invoice from the field.

---

## Before You Start

1. Open web sales pages (list, invoice detail, invoice create) + `apps/web/src/api/sales.ts` →
   endpoints, payload shapes, status vocabulary, line-item rules.
2. Open `erp/sales/contracts/__init__.py` (read-only) → understand what the server validates —
   mobile duplicates NONE of it; it only shapes the payload and renders field errors.
3. Open the patterns from session 08 (`ListScreenPattern`, `RecordScreenPattern`, `FilterSheet`).
4. Check how web handles e-invoice (ETA) status display on invoices → mirror the chip.
5. Recall `flutter-lessons` issues 5 (optimistic list updates), 6 (local submit bool), 8 (money).

"Do not write anything yet."

---

## Task A — Customers

1. Customers list: ListScreenPattern — server search, balance column (money variant), filter by
   status/salesperson if web has them.
2. Customer RecordScreen: contact block (phone → tap-to-call, tap-to-WhatsApp via OS intents.
   Flutter has no built-in intent launcher — `url_launcher` is the standard package but is NOT on
   the approved list: add it via a one-line DECISIONS entry at execution time, per ground rule 6),
   balance + aging summary, recent invoices list (deep links), attachments section stub
   (session 13 fills).
3. Customer create/edit: a `FormScreenPattern` worth building properly NOW (it serves every
   module): sectioned fields from the design system, keyboard-aware scrolling
   (`Scrollable.ensureVisible` on focus), dirty-state guard ("تجاهل التغييرات؟" AppDialog),
   server field-errors mapped inline under fields (`ApiFailure.fields` → i18n). Submit →
   optimistic toast + navigate to record.

## Task B — Invoices

1. Invoice list: status FilterSheet (same statuses/colours/words as web), date-range chip
   (PeriodPicker), amount shown with money formatter, unpaid emphasis exactly as web does it.
2. Invoice RecordScreen: header status + ETA chip, customer link, line-items table (mobile
   rendering: stacked line cards on phone, table on tablet — same data order as web), totals
   block (subtotal/VAT/total — tabular), payments section, activity/audit trail section if web
   shows one. Actions per status (send, record payment, void…) — mirror web's action set; each
   action = same endpoint web calls; destructive ones get AppDialog + haptic; every mutation
   invalidates the relevant cache keys and updates the loaded list in place.
3. PDF: "عرض الفاتورة" → server-rendered invoice PDF (same endpoint as web) → viewer + share.

## Task C — Invoice create (the flagship mobile form)

1. Entry: header + action bar button (no floating brand-breaking blob unless web's pattern says
   otherwise), also from customer record ("فاتورة جديدة").
2. Flow (single screen, sections, not a wizard — Linear-calm): customer picker (search AppSheet,
   recent-first), line items: item picker (search AppSheet + barcode button stub wired in session
   11), qty/price editors with numeric keypads, per-line VAT as web dictates (server is truth —
   totals ALWAYS from a server `preview`/draft call if web uses one; if web computes client-side,
   still call the server before final submit and reconcile — no drift allowed. READ what web
   does; match it).
3. Draft safety: form state persists locally (drift `drafts` table keyed by form+user) on every
   change — process death, interruption, or navigation never loses a half-built invoice.
   Reopening the create screen offers the draft ("استكمال مسودة؟"). This local draft mechanism
   becomes shared FormScreenPattern behaviour.
4. Submit offline → queue via… NOT YET. Until session 16, submitting while offline shows a
   designed "الاتصال مطلوب لإصدار الفاتورة" state and the draft is safe. (Write queue lands in
   16; do not half-build it here.)

---

## Smoke Test

- [ ] Side-by-side with web: same customer list order, same invoice statuses/words, same totals
      for the same invoice (piaster-exact — money port + server truth)
- [ ] Create a real invoice on device (ar): pick customer, 3 lines, VAT correct, submit → appears
      on WEB instantly with identical numbers; audit trail shows the same user
- [ ] Server-side validation error (e.g. blocked customer) → inline blame-free field error
- [ ] Kill app mid-create → reopen → draft offer restores every field
- [ ] Invoice PDF renders + shares; tap-to-call works from customer record
- [ ] RTL + LTR passes on all five screens; designed states visible for empty search / error /
      loading; tablet two-pane list→detail works
- [ ] analyze + test + parity green; PARITY.md sales rows flipped

## Risks

- Totals drift between client preview and server → the "server is truth" rule in Task C.2 is
  absolute; reconcile-or-block, never ship a mismatch.
- Item picker performance on large catalogs → server search + builder lists; no client-side full
  catalog loads.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_10_PURCHASING_AND_APPROVALS.md
```
