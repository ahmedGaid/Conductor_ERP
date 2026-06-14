# Accounting & Finance module

General Ledger core (Stage 5a). Customer priority #1.

## Layout (strict module boundary)
- `domain/` — `money.py` (integer-minor-unit `Money` value object), `accounts.py` (account types +
  normal-balance rule), `models.py` (ORM: Account, FiscalYear, Period, JournalEntry, JournalLine).
- `repositories/` — typed data-access boundary (no ORM in business logic).
- `services/` — `posting.py` (the double-entry invariant point), `reports.py` (trial balance, GL).
- `contracts/` — the ONLY surface other modules import: `post_journal`, `Money`, event names.
- `events.py` — `accounting.JournalPosted`, `accounting.PeriodClosed`.
- `api/` — DRF endpoints under `/api/accounting/`.

## Invariants (enforced in `services.posting.post_journal`, proven by `tests/`)
1. **Balanced** — total debits == total credits, and total > 0; else nothing is written.
2. **Valid lines** — ≥ 2 lines; each line has exactly one of debit/credit > 0; amounts ≥ 0.
3. **Postable accounts** — group/inactive accounts are rejected.
4. **Open period** — posting to a closed period (or no period) is rejected.
5. **Atomic** — entry + all lines commit together or not at all.
6. **Immutable** — a posted entry is never edited; undo is a `reverse_journal` mirror entry.
7. **Trial balance always balances** — total debits == total credits across posted lines.

## Money
Never a float. Amounts are integer **minor units** (e.g. `1050` == `10.50 EGP`). Default currency
EGP (2 minor digits). Cross-currency arithmetic raises.

## Next slices (Stage 5b+)
Cost centers, tax codes + ETA e-invoice records, bank accounts + reconciliation, budgets, fixed
assets + depreciation, and the full statement suite (IS, BS, Cash Flow, AR/AP aging, VAT).
