# SESSION 12 — Accounting Views
# Files: apps/mobile/lib/presentation/pages/more/accounting/**, accounting + CRM domain/data
#        layers (new), settings screens (new, small)

**Objective:** the accountant's read surface — chart of accounts, ledger drill-down, trial
balance, VAT position, bank reconciliation status — as fast, honest, RTL-perfect tables. Plus
this session sweeps the remaining "read-mostly" web areas into More (CRM lists, e-invoice status,
settings/admin reads) so the parity ledger has no orphan rows before Phase 3. Journal ENTRY
creation stays desktop-shaped work — mobile shows everything, and creates only what web's flows
make sensible on a phone (deferred rows documented, not hidden).

---

## Before You Start

1. Open web accounting pages (accounts tree, ledger, trial balance, VAT, bank recon) + API
   module → endpoints, drill-down paths, period semantics.
2. Open web CRM + e-invoice (ETA) + settings pages → list what exists TODAY; PARITY.md is built
   from this read, not from this plan.
3. Session 08's `ReportTable` + `PeriodPicker` — the workhorses here.

"Do not write anything yet."

---

## Task A — Accounting

1. Chart of accounts: tree as an indented ListScreen (expand/collapse, balances per account,
   money variant). Tap → account ledger.
2. Account ledger: ReportTable — date, doc link, description, debit, credit, running balance;
   PeriodPicker; every doc reference deep-links to its record (invoice/PO/payment screens from
   earlier sessions — the graph connects HERE and suddenly the app feels whole).
3. Trial balance: ReportTable + period; totals pinned; must balance to the piaster with web for
   the same period (smoke test).
4. VAT position: mirror web's VAT return/draft view (read-only; filing stays where web puts it).
5. Bank reconciliation: status list per account (last reconciled, unmatched count); unmatched
   lines list read-only. (Phase D of the roadmap — recon by photo — will land HERE later; leave
   an architecture note, not code.)

## Task B — CRM + remaining reads (`pages/more/`)

1. CRM: leads/contacts ListScreen + RecordScreen + create/edit FormScreen (CRM on the move is a
   real use case — calls/WhatsApp intents from records, same as customers).
2. E-invoice: submission status list, per-invoice ETA detail (chips already on invoice records
   from session 09 — this is the module-level view).
3. Settings (More → settings): profile, language override (ar/en — flips app direction live),
   appearance (auto/light/dark), biometric toggle, devices (session 07), about/version.
   Admin-only reads web exposes (user list, roles view) render read-only where RBAC allows —
   the SAME permission checks flow from the server; mobile never decides permissions.

## Task C — Parity sweep

Walk `PARITY.md` row by row against the live web nav. Every row must now be: done, scheduled
(sessions 13–16 cover attachments/AI/notifications/offline), or **deferred with a written
reason** (e.g. "journal-entry composer — desktop-shaped; revisit on demand"). Zero blank rows.

---

## Smoke Test

- [ ] Trial balance for last closed month: mobile total === web total, piaster-exact, ar + en
- [ ] Ledger drill-down: dashboard → account → ledger row → source invoice → its customer — five
      deep-link hops, no dead ends
- [ ] RTL ledger table: columns ordered correctly, debits/credits not mirrored into wrong columns
      (classic RTL-table bug — verify against web's RTL rendering)
- [ ] Language switch in settings flips direction live without restart — Flutter rebuilds
      `Directionality` from the new locale immediately; verify no half-flipped screen survives
      (any stragglers = a physical-direction bug to fix, `flutter-lessons` issue 10)
- [ ] Restricted user sees exactly what web shows them — nothing more (spot-check 2 screens)
- [ ] PARITY.md: zero blank rows
- [ ] analyze + test + parity script green

## Risks

- RTL numeric tables are subtle (digit shaping, column order, alignment) → budget the session's
  care here; compare against web's rendering, which already solved it.
- Stray physical-direction widgets only surface on live flip → the flip smoke item catches them;
  fix the widget, never special-case the flip.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_13_ATTACHMENTS_AND_CAMERA.md
```
