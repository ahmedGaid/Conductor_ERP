# SESSION 3 — Upgrade Drill + API Snapshot Gates
# Files: scripts/gates/gate16.py (new), scripts/gates/gate17.py (new), scripts/gates/_run.py, scripts/gates/snapshots/ (new), Docs/RUNBOOK.md

Twenty reference: `ci-cross-version-upgrade.yaml` (upgrades are TESTED, not hoped) and
`ci-breaking-changes.yaml` (API surface diffed on every change). We encode both as gates.

---

## Before You Start

1. Open `scripts/gates/_run.py` + one recent gate (e.g. gate15) → match the gate contract
   (exit 0 = pass, printed summary).
2. Open `Docs/RUNBOOK.md` backup section → reuse the exact pg_dump/pg_restore invocations.
3. Open the DRF url/router registrations (root `api/urls.py` + one module's `api/urls.py`) →
   understand what gate17 can inventory without new dependencies.

"Do not write anything yet."

---

## Task A — gate16: cross-version upgrade drill

- Fixture: `scripts/gates/fixtures/prev_release.dump` — a pg_dump of a SEEDED database at the
  previous release. FIRST run: create it from the current release (drill = self-upgrade) and
  document in RUNBOOK that every release refreshes this dump (FILE_01 release steps).
- Gate: restore dump into a scratch database (`erp_upgrade_drill`) → run `manage.py upgrade
  --yes` against it → assert system-check OK + trial balance balanced + a spot row-count table
  (customers/items/invoices > 0). Drop scratch DB. Any step fails → exit 1 with the failing
  stage named.
- Skippable with a clear message when PostgreSQL tools are absent (CI/dev-box mismatch), but
  NEVER silently.

## Task B — gate17: API schema snapshot (additive-only)

- Build a deterministic inventory: for every registered DRF route → method(s), path, serializer
  class → field names/types/required. Serialize to
  `scripts/gates/snapshots/api_schema.json` (sorted, stable).
- Gate: regenerate and diff against the committed snapshot. **Removed route/field or changed
  type/required → exit 1** (breaking). Added routes/fields → pass + note. Intentional break →
  regenerate snapshot in the same commit (the diff in review IS the approval).

## Task C — Wire both into `_run.py` (gate:all now 00–17)

---

## Smoke Test

- [ ] `python scripts/gates/gate16.py` green on the dev box (drill DB created + dropped)
- [ ] `python scripts/gates/gate17.py` green on clean tree
- [ ] Locally rename one serializer field → gate17 exits 1 naming it → revert
- [ ] `python scripts/gates/_run.py all` green end-to-end

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_04_E2E_PLAYWRIGHT.md in a FRESH session.
```
