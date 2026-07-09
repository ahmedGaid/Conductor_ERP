# SESSION 4 — Data Cleaning Normalizers
# Files: erp/imports/normalize.py (new), erp/imports/tests/test_normalize.py (new)

> Model note: Sonnet fits this session — it's a table of pure functions with exhaustive tests.

---

## Before You Start

1. Open `erp/imports/registry.py` → FieldSpec kinds (text/number/money/date/ref/enum) — one
   normalizer per kind, dispatched by spec.
2. Find how the codebase stores money (grep `minor` in `erp/core` / `erp/accounting`) — the
   money normalizer must emit integer minor units.
3. Find existing currency/unit/tax models (`erp/accounting`, `erp/inventory`, `erp/setup`) —
   normalizers RESOLVE into these records via adapter `lookup`, they never create.

"Do not write anything yet."

---

## Task A — Text pass (applies to every cell before typed parsing)

`clean_text(v)`: trim, collapse internal spaces, strip zero-width/control chars, normalize
punctuation variants, fix cp1256 mojibake remnants (reuse readers helper), normalize Arabic
letters for MATCHING ONLY (keep original for stored names — normalize a copy).

## Task B — Typed normalizers (spec steps 8, 10–13)

```python
def parse_date(v, dayfirst=True) -> date | Issue
    # 01/02/2026, 2026-02-01, 1 Feb 2026, 02.01.26, Excel serial numbers, ١/٢/٢٠٢٦
    # Arabic-Indic digits converted first; two-digit years pivot at 50; ambiguous → dayfirst
    # (Egypt convention) + flag issue code "date_ambiguous" so the preview can show it.

def parse_money(v, currency_minor_digits) -> int | Issue
    # "1,250.50", "1.250,50" (detect by last separator), "EGP 1250", "١٢٥٠٫٥٠" → minor units

def parse_number(v) -> Decimal | Issue

def normalize_currency(v) -> str | Issue     # EGP/L.E/LE/le/جنيه/ج.م → "EGP"; $/USD → "USD"; €/EUR → "EUR"
def normalize_unit(v) -> str                  # PCS/Piece/Pieces/Pc/Each/قطعة → canonical token
def normalize_tax(v) -> TaxToken             # VAT/VAT14/14%/ضريبة/Value Added Tax → {kind:"vat", rate:14?}
def normalize_phone(v, default_country="EG") -> str | Issue   # 010..., +2010..., spaces/dashes out
def normalize_email(v) -> str | Issue
def normalize_tax_id(v) -> str | Issue       # digits only, Egyptian tax-number length check (warn, not block)
def normalize_code(v) -> str                  # item/customer codes: upper, trim, unify dashes
```

Canonical tokens (currency/unit/tax) are resolved to actual DB records later by adapter
`lookup` — normalize.py stays DB-free and pure (fast tests, reusable in preview).

## Task C — Row pipeline

`normalize_row(adapter, mapping, raw) -> (normalized: dict, issues: list[Issue])` — dispatch
each mapped column through its FieldSpec kind; collect issues with `{field, code, message_key,
value}`; never raise. Unmapped columns dropped. Issue messages are i18n KEYS (frontend
translates) — blame-free wording per the Directive.

## Task D — Tests

Exhaustive tables per normalizer (every example format above, plus garbage input → Issue).
Round-trip: a messy fixture row → normalized dict matches expected exactly.

---

## Smoke Test

- [ ] Every date format in the spec parses; ١/٢/٢٠٢٦ → 2026-02-01
- [ ] "1.250,50" and "1,250.50" both → 125050 minor units
- [ ] جنيه → EGP; قطعة → canonical piece token; "14%" → vat 14
- [ ] Issues carry i18n keys, no hardcoded English sentences
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?  ← MERGE CHECKPOINT: parsing core done — gates green, merge branch to main.
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_05_MASTER_ADAPTERS.md in a FRESH session.
```
