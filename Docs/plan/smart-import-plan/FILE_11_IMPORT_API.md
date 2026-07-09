# SESSION 11 — Import REST API
# Files: erp/imports/api/views.py, erp/imports/api/urls.py (new), root api urls include, erp/imports/tests/test_api.py (new)

> Model note: Sonnet fits this session — endpoint shells over already-built services.

---

## Before You Start

1. Open `erp/assistant/api/views.py` + `api/urls.py` → auth/permission decorator pattern,
   upload handling, error-response shape. Mirror EXACTLY.
2. Open every service this wraps: readers, detect, mapping, analyze, validate, duplicates,
   masters, engine, runner (sessions 2–10).

"Do not write anything yet."

---

## Task A — Endpoints (all actor-scoped, server-side validation — spec step 26)

```
POST /api/imports/upload            file → attachment + sniff + read_headers + detect_entity
                                    → creates ImportBatch(status=mapping)
                                    → {batch_id, file_info, candidates, mapping_suggestion, profile_hits}
POST /api/imports/{id}/mapping      {entity, mapping, profile_id?} → analyze() (async if huge)
                                    → stats (spec step 6 numbers)
GET  /api/imports/{id}              batch + stats + progress (poll target; match how the app
                                    does live updates today — check before inventing SSE)
GET  /api/imports/{id}/rows?status=&page=   preview grid page (raw+normalized+issues+decision)
PATCH /api/imports/{id}/rows/{row}  inline edit / duplicate decision → revalidate_rows → row back
POST /api/imports/{id}/autofix      auto-fix pass (Task B) → preview of proposed fixes
POST /api/imports/{id}/autofix/apply  {accepted_row_ids or all}
GET/POST /api/imports/{id}/creation-plan    masters plan / approve subset
POST /api/imports/{id}/execute      {strategy, atomicity, continue_after_errors}
                                    → inline result or queued
POST /api/imports/{id}/pause|resume|cancel|rollback
GET  /api/imports/{id}/report       report dict; ?format=csv streams per-row outcomes
GET  /api/imports/                  history list (spec step 23): who/when/file/rows/result
GET/POST/DELETE /api/imports/profiles       saved mappings CRUD
```

## Task B — Auto Fix service (spec step 16 — small, lives in `validate.py` or new `autofix.py`)

Deterministic only, each fix previewable `{row, field, from, to, code}`:
re-run normalizers with lenient flags (date dayfirst flip where unambiguous after all),
apply adapter defaults for missing optional fields, map near-miss enum/unit/currency/tax
tokens (levenshtein ≤1 to a known token), trim/space fixes. NO model call in v1 — record
"AI-assisted autofix deferred" in DECISIONS at acceptance.

## Task C — Permissions + limits

Upload size limit setting (`IMPORTS_MAX_FILE_MB`, default 50). Every endpoint: batch owner or
elevated import role (find the RBAC pattern — `erp/identity`). Rollback: owner + the module
permissions for what gets reverted (engine already checks per record; endpoint checks batch
access). History list scoped to what the actor may see.

## Task D — Tests

Endpoint-per-endpoint: happy path + unauthenticated 401 + unpermitted 403 + wrong-state 409
(execute while mapping, edit while running). Full lifecycle test: upload→mapping→analyze→
patch row→creation-plan approve→execute→report, asserting DB effects at each step.

---

## Smoke Test

- [ ] Full lifecycle via curl/httpie on a 100-row customers csv — every response shape matches Task A
- [ ] Row PATCH revalidates just that row; wrong-state transitions → 409
- [ ] Autofix preview → apply → issues drop; nothing applied without the apply call
- [ ] Profile save on one batch → next upload of same headers auto-applies it
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_12_WIZARD_UPLOAD_MAP_UI.md in a FRESH session.
```
