# SESSION 1 — Release Versioning
# Files: VERSION (new), CHANGELOG.md (new), config/settings/base.py, erp/monitoring (health/system-check), apps/web settings/about surface, Docs/RUNBOOK.md, i18n locales

Twenty reference: versioned releases + a dedicated `upgrade` module keyed by version. This
session builds the version SOURCE; FILE_02/03 build the upgrade machinery on top of it.

---

## Before You Start

1. Open `erp/monitoring/` → find the `/health` and `/system-check` view fns and their response
   shapes.
2. Open `config/settings/base.py` → note how other constants are exposed.
3. Open `apps/web/src/` settings/preferences pages → find where an "about/version" line belongs
   (there may already be one — audit first).
4. Open `Docs/RUNBOOK.md` → find the deploy section (release steps append there).

"Do not write anything yet."

---

## Task A — `VERSION` file + settings

Repo root `VERSION` containing `1.0.0` (single line). In `config/settings/base.py`:

```python
CONDUCTOR_VERSION = (BASE_DIR / "VERSION").read_text().strip()  # single source of truth
```

## Task B — Expose it

- `/health` → add `"version": settings.CONDUCTOR_VERSION` to the JSON.
- `/system-check` → same.
- Frontend: fetch once (it's already calling health or config — reuse, don't add a request if
  avoidable) and show "الإصدار ١٫٠٫٠ / Version 1.0.0" in the settings/about surface. i18n keys
  in BOTH `ar.json` and `en.json`.

## Task C — `CHANGELOG.md` + tag discipline

- `CHANGELOG.md` at root, keep-a-changelog-lite: one `## vX.Y.Z — YYYY-MM-DD` section per
  release, plain bullets (EN internal doc). Seed it with `v1.0.0` summarizing the shipped core.
- RUNBOOK "Release" subsection: bump `VERSION` → update `CHANGELOG.md` → `git tag vX.Y.Z` →
  build → (from FILE_03 on) refresh the gate16 previous-release fixture dump.

---

## Smoke Test

- [ ] `curl /health` returns the version; `/system-check` too
- [ ] Version visible in the UI in ar AND en (RTL renders correctly)
- [ ] `node scripts/check-i18n-parity.mjs` + `npx tsc -b` green; `python scripts/gates/gate03.py` green
- [ ] RUNBOOK release steps read as copy-pasteable commands

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_02_UPGRADE_COMMAND.md in a FRESH session.
```
