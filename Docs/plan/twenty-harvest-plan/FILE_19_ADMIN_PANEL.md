# SESSION 19 — Admin / System Panel (read-only)
# Files: erp/monitoring/api (extend), apps/web settings→system page (new), i18n locales

Twenty reference: the admin panel + config variables + health surfaces — the self-hoster's IT
person self-serves instead of calling support. Ours is READ-ONLY by design (changing config
stays in `.env` + restart — no config-mutation surface, less to break, less to secure).

---

## Before You Start

1. Open `erp/monitoring/` health + system-check services → what's already collected
   (DB/Redis/storage). The page is a VIEW over these + small additions, not a new subsystem.
2. Open `config/settings/` env handling + `.env.example` → the NAMES catalog (values NEVER
   leave the server).
3. Open Celery wiring (`config/celery.py`) → cheapest queue-depth/last-heartbeat probe.
4. Open `Docs/RUNBOOK.md` backup section → what "last backup" info can be shown honestly
   (file mtime of the documented dump location, if configured — else "not configured" state).

"Do not write anything yet."

---

## Task A — Backend: one endpoint

`/api/system/status/` (admin role only): version (FILE_01), DB ok + latency, Redis ok, Celery
worker seen recently + queue depth, storage free space, env-var NAMES each marked set/unset
(values never serialized — enforce in code + test), last-backup info or "not configured",
uptime. No secrets, no write operations.

## Task B — Settings → "النظام / System"

Status rows with word+glyph state (تعمل / لا تستجيب — never color alone), version line, env
table (name, set/unset chip), backup line linking the RUNBOOK help journey (FILE_15), a calm
degraded banner reusing the information-banner pattern when something is down, and "what to do"
one-liners per failure (actionable blockers — mechanic 5). Auto-refresh at a settled interval;
manual refresh action.

## Task C — Tests

Admin-only (403 otherwise); env VALUES absent from response body under all cases (assert
aggressively); degraded Redis renders degraded state (mock).

---

## Smoke Test

- [ ] Admin sees all-green panel on the dev box; non-admin gets 403 + no nav entry
- [ ] Stop Redis → panel shows the degraded row + actionable line; start → recovers
- [ ] Response JSON contains env NAMES only (grep the payload for a known secret value → absent)
- [ ] `pytest erp/monitoring` green; parity + tsc + gate03 green; brand checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_20_AI_COST_PAGE.md in a FRESH session.
```
