# SESSION 3 — Dataset Detection + Header Mapping
# Files: erp/imports/detect.py (new), erp/imports/mapping.py (new), erp/imports/tests/test_detect.py, erp/imports/tests/test_mapping.py

---

## Before You Start

1. Open `erp/imports/registry.py` → FieldSpec (synonyms live THERE, per adapter — this session
   consumes them, it does not hardcode entity vocabularies).
2. Open `erp/assistant/services/llm.py` → `complete_json` signature, error/retry behavior.
3. Open `erp/imports/readers.py` → Headers shape.

"Do not write anything yet."

---

## Task A — `mapping.py`: deterministic header matcher (runs FIRST, no AI)

```python
def normalize_header(h: str) -> str:
    """lower, trim, collapse spaces, strip punctuation (#, ., :), strip diacritics,
    normalize Arabic letters (أإآ→ا, ة→ه, ى→ي), unify Arabic-Indic digits."""

def levenshtein(a, b) -> int      # small pure-Python, early-exit at max distance 3

def match_headers(headers, adapter) -> MappingResult:
    """Per header, in order: exact synonym hit (en+ar lists) → prefix/contains hit →
    levenshtein ≤ 2 against synonyms → unmapped. Score each match 0–100.
    Returns {header: {field, confidence, method}}; unmapped headers → 'ignore'."""
```

Synonym examples to seed in session-5 adapters (documented here so the vocab is consistent):
invoice no/invoice #/doc number/رقم الفاتورة → invoice_number; customer/client/buyer/العميل →
customer; qty/quantity/الكمية → quantity; price/unit price/rate/السعر → unit_price;
item/product/sku/material/الصنف → item.

## Task B — `detect.py`: what IS this file?

```python
def detect_entity(actor, headers, sample_rows) -> DetectResult:
    """1) Deterministic: run match_headers against EVERY registered adapter; score =
       weighted coverage of required fields. Clear winner (top ≥70, gap ≥20) → high confidence.
    2) Ambiguous → ONE complete_json call: headers + 5 sample rows + candidate entity list
       → {entity, confidence, reason}. Model output must name a REGISTERED entity or is discarded.
    Returns ranked candidates [{entity, confidence}] — UI shows top-1 if high, choices if low."""
```

## Task C — AI-assisted mapping fallback

`mapping.suggest_with_model(actor, headers, sample_rows, adapter)`: for headers the
deterministic pass left unmapped, ONE `complete_json` call proposing field assignments;
validate every proposal against `adapter.fields` (unknown field → drop). Merge as
`method="model"`, confidence capped at 80 — model suggestions always show as overridable.

## Task D — Profile application

`mapping.apply_profile(profile, headers) -> MappingResult`: exact header set → apply directly
(confidence 100, method="profile"); extra/missing headers → apply intersection, flag the rest.

## Task E — Tests

Deterministic table: each synonym example above maps right, in both languages, mixed-language
file too. Levenshtein catches `Invoce No`. Detection picks customers-file vs invoices-file
fixtures deterministically (no model call — mock and assert NOT called on clear cases; called
once on the ambiguous fixture). Model proposing an unknown field → dropped.

---

## Smoke Test

- [ ] Arabic-headed customer file → detected `customers`, all headers mapped, zero model calls
- [ ] Misspelled English headers → fuzzy-mapped with visible lower confidence
- [ ] Ambiguous 3-column file → ranked candidates, model consulted once
- [ ] Profile with matching headers → instant full mapping
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_04_NORMALIZERS.md in a FRESH session.
```
