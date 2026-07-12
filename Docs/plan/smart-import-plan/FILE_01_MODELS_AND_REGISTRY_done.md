# SESSION 1 — Imports App: Models + Adapter Registry
# Files: erp/imports/* (new app), config/settings/base.py, erp/imports/tests/test_registry.py

---

## Before You Start

1. Open an existing small app for structure reference (`erp/pricing/` or `erp/setup/`) — apps.py,
   models.py, migrations layout, how it's registered in `config/settings/base.py`.
2. Open `erp/assistant/models.py` → how attachments/files are stored (the upload FK target).
3. Open `erp/audit/services.py` → `record(...)` signature.
4. Open one module write-path (`erp/sales/services/orders.py`) → note the create-function shape
   (actor-first? kwargs? returns record?) — the adapter protocol must match this reality.

"Do not write anything yet."

---

## Task A — App skeleton

Create `erp/imports/` Django app (`ImportsConfig`, name `erp.imports`). Add to INSTALLED_APPS.

## Task B — Models (`erp/imports/models.py` + migration 0001)

```python
class ImportProfile(models.Model):        # saved mapping (spec step 5)
    company/owner scoping as the codebase does it, name, entity, mapping = JSONField(),
    options = JSONField(default=dict), created_by, timestamps

class ImportBatch(models.Model):
    entity, source_file (FK to the existing attachment/file model), profile (FK, null=True),
    status = choices: analyzing/mapping/previewing/ready/running/paused/done/failed/rolled_back,
    strategy = choices: create_only/update_only/upsert/skip_existing (spec step 19),
    mapping = JSONField(), stats = JSONField(default=dict),   # counts, timings, stage
    row_count, processed_count, error_count, created_by, timestamps

class ImportRow(models.Model):            # one per source row; the working table
    batch FK, row_number, raw = JSONField(), normalized = JSONField(default=dict),
    status = choices: pending/valid/error/duplicate/skipped/imported/reverted,
    issues = JSONField(default=list),     # [{field, code, message}]
    decision = JSONField(default=dict),   # user choices: merge target, edited values, skip
    result_ref = JSONField(default=dict)  # {model, pk} of the written record (rollback anchor)
    index batch+status, unique batch+row_number
```

## Task C — Adapter protocol + registry (`erp/imports/registry.py`)

```python
@dataclass
class FieldSpec:
    name: str; required: bool; kind: str        # text/number/money/date/ref/enum
    ref: str | None = None                      # registry entity for lookups (e.g. "customers")
    synonyms_en: list[str] = ...; synonyms_ar: list[str] = ...
    default: Any = None

class ImportAdapter(Protocol):
    entity: str; label_key: str                 # i18n key, not a hardcoded label
    fields: list[FieldSpec]
    natural_key: list[str]                      # duplicate/existing matching
    group_by: str | None                        # None for masters; header column for documents
    def lookup(self, actor, field, value) -> Any | None       # resolve refs against DB
    def validate(self, actor, row: dict) -> list[Issue]       # beyond field-spec checks
    def write(self, actor, row: dict) -> object               # calls module service write-path
    def exists(self, actor, row: dict) -> object | None       # natural-key fetch

REGISTER: dict[str, ImportAdapter] = {}
def register(adapter): ...
def get(entity): ...
```

Core rule stated in the module docstring: **the engine never imports module models directly;
only adapters do.** Add one throwaway `_ExampleAdapter` in tests only.

## Task D — Tests

`tests/test_registry.py`: register/get roundtrip; FieldSpec defaults; ImportBatch status
transitions helper (if you add one); migration applies clean.

---

## Smoke Test

- [ ] `python manage.py migrate` clean; `python manage.py makemigrations --check` clean after
- [ ] `pytest erp/imports` green
- [ ] Registry register/get works; duplicate entity registration raises
- [ ] No module app imports inside `erp/imports/` core files (grep `from erp.sales` etc. → only in `adapters/`)

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done. A _done file is finished forever — never reopen it.
→ Update erp-status. Type /compact.
→ Open FILE_02_FILE_READER.md in a FRESH session.
```
