# SESSION 2 — Streaming File Reader
# Files: erp/imports/readers.py (new), erp/imports/tests/test_readers.py (new)

> Model note: Sonnet fits this session.

---

## Before You Start

1. Open `erp/assistant/services/files.py` → how xlsx/csv are ALREADY read (library, encoding
   handling). Reuse the same library; do not add a new one.
2. Open `erp/imports/models.py` (session 1) → ImportBatch.source_file target model, where the
   bytes live (storage API).

"Do not write anything yet."

---

## Task A — `erp/imports/readers.py`

```python
def sniff(file) -> FileInfo:
    """format (xlsx/csv), sheets + row counts, encoding (csv: try utf-8-sig, utf-8, cp1256 —
    Arabic Windows Excel default), delimiter (csv.Sniffer with ; and \t fallback)."""

def read_headers(file, sheet=None) -> Headers:
    """Header row detection: first row with >60% non-empty text cells that is NOT numeric-only.
    Handles files where headers start at row 3 (title/logo rows above — common in real books).
    Returns headers + header_row_index + 10 sample rows below it."""

def iter_rows(file, sheet=None, start=0) -> Iterator[tuple[int, dict]]:
    """STREAMING row iterator (read_only mode for xlsx; csv line reader). Yields
    (row_number, {header: raw_value}). Never loads the whole sheet into memory —
    this is the 1M-row path (spec step 25). Skips fully-empty rows."""
```

`.xls` (legacy) → raise `UnsupportedFormat` with a message key (`imports.errors.xlsFormat` —
"save the file as .xlsx and upload again"). No new package (index decision 5).

## Task B — Encoding + mojibake repair

In `sniff`/cell reading: repair the classic cp1256-read-as-latin1 mojibake for Arabic text
(detect: high ratio of Ø/Ù chars → re-decode). Strip BOM, zero-width chars, control chars.

## Task C — Tests

Fixtures in `tests/fixtures/`: clean xlsx, csv utf-8, csv cp1256 Arabic, xlsx with 2 junk rows
above headers, csv with `;` delimiter, empty file. Test each path + streaming (iterate a
generated 10k-row csv without materializing a list).

---

## Smoke Test

- [ ] cp1256 Arabic csv → headers readable Arabic, no mojibake
- [ ] Headers found on row 3 when rows 1–2 are a title
- [ ] 10k-row file iterates lazily (assert generator, spot-check memory-free path)
- [ ] .xls upload → UnsupportedFormat with the i18n message key
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_03_DETECT_AND_MAP.md in a FRESH session.
```
