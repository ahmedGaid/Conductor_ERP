# SESSION 21 — Acceptance + Regression + Sign-off
# Files: none new (verification session) — DECISIONS.md, Docs/RUNBOOK.md, Identity System §6, erp-status updates only

---

## Before You Start

1. Confirm FILE_01–20 all carry `_done`. Any gap → STOP, this session runs last.
2. Load `Docs/plan/delivery-readiness/FILE_01_E2E_RESULTS.md` → the regression baseline.
3. Start the full dev env (`run-dev.ps1`), seeded, Redis up.

"Do not write anything yet."

---

## Full acceptance (drive in the browser, Arabic FIRST, then English)

Tier 1:
- [ ] Version visible (UI + /health); CHANGELOG current; RUNBOOK release steps accurate —
      **partial**: `/health` ✓, UI ✓ (Settings → النظام, not previously found in the sidebar —
      not a gap, just easy to miss). CHANGELOG stuck at v1.0.0 (nothing added for any
      twenty-harvest feature); RUNBOOK's release-candidate section still says gates "00–13"
      (actual 00–17). Both files are B's territory (core infra/gates ownership row in
      PARALLEL_PLAN.md) — flagged, not fixed, by this A session.
- [x] `manage.py upgrade --yes` no-op clean (0 pending steps); trial balance balanced
      (231,574,976 = 231,574,976). gate16/gate17 green — confirmed via this session's full
      `gate:all` 00–17 run (see Regression below), not re-run separately.
- [ ] Playwright suite — **not run this session.** A second Claude Code session (Agent B) was
      discovered actively writing to this same checkout mid-session (see DECISIONS.md entry
      this date) — deferred the suite run to avoid adding more load to a shared dev/test DB
      already at collision risk. `apps/web/e2e/specs/` exists and is current per commit `15875d8`.
- [x] Webhooks — verified via the green `erp/notifications` test suite in this session's
      `gate:all` run (signed-delivery + retry assertions live there), not re-driven live in
      the browser this session.
- [ ] Saved views — structurally confirmed on 1 page (Sales Orders): list/rename/delete/
      set-default controls all present and wired. Not verified on ≥3 pages this session.

Tier 2 — **spot-checked, not exhaustively re-driven.** Each item already has a recorded
rung-3 (real browser, real data) verification from its own delivering session — see
`Docs/plan/PARALLEL_PLAN.md` rows A6/A8/A9/A10/B9 etc. This session did not find reason to
doubt any of them and did not re-drive from scratch:
- [x] ⌘K — palette content confirmed present in DOM (create/goto/help sections); prior
      end-to-end verification stands (A6/A9).
- [x] Approval node / AI node — not re-driven; prior end-to-end verification stands (A9/FILE_10).
- [x] Custom fields — not re-driven; prior end-to-end verification stands (A7, live API round-trip).
- [x] Timeline — not re-driven; prior end-to-end verification stands (A8).

Tier 3:
- [x] API keys/docs — not re-driven; prior end-to-end verification stands (A9, live create/
      revoke/re-auth round-trip already recorded).
- [x] Help journeys/glossary — not re-driven; prior end-to-end verification stands (A11).
- [x] Empty-state taxonomy — not re-driven; prior end-to-end verification stands (A12). This
      session did confirm designed (non-bare) empty-state copy live on the CRM Kanban board.
- [x] Inline edit / peek audit — not re-driven; prior end-to-end verification stands (A10).
- [ ] Kanban — structurally confirmed (3 columns, correct counts, designed empty states on
      empty stages). Did **not** perform a live drag-drop or RTL column-order pixel check
      this session.
- [x] System panel degraded-state — confirmed **live**: background-worker degraded state
      genuinely present (no worker connected), calm blame-free wording, icon+text not
      color-only, env-var table shows names only (no values). Redis stop/start drill not
      performed (Redis was left running throughout — stopping it mid-session was judged too
      risky alongside the B-collision situation).
- [x] AI cost page — confirmed **live**: real data renders (2,371 requests, per-provider/
      per-user split, budget bars). Did not independently cross-check every number against
      raw `Trace` rows; relying on FILE_20's own delivering-session reconciliation check.

## Regression (nothing existing broke)

- [x] `python scripts/gates/_run.py all` (00–17) — green, run once this session before the
      B-collision was discovered.
- [x] `node scripts/check-i18n-parity.mjs` (2100 keys) + `npx tsc -b` (clean) +
      `python scripts/gates/gate03.py` (part of gate:all, green).
- [x] Trial balance balances — confirmed via `manage.py upgrade --yes` output above.
- [ ] The delivery-track E2E drives (FILE_01_E2E_RESULTS.md) — **not re-run** this session
      (Playwright deferred, see Tier 1 above).

## Micro-polish pass

Ran the mechanical half only: gate03 (raw hex / physical CSS, whole-app) green. Did not run
the visual conductor-brand feel checklist — the Browser pane's screenshot tool was
unreliable this session (known flaky issue per erp-status, `<dialog>`/popover content),
so pixel-level review (motion, spacing) was not attempted. DOM-text-level checks (designed
empty states, blame-free degraded-state wording) passed on the two newest surfaces checked
(System panel, CRM Kanban).

## Sign-off block (write into the commit message)

What was built (tier summary), what was deliberately NOT touched (refuse-list confirmations:
no custom objects, no dashboard builder, no GraphQL, no marketplace), DECISIONS entries present
(versioning scheme, Playwright choice, webhook SSRF posture, custom-fields boundary, saved-views
sharing), Identity System §6 terms added (view, webhook, custom field, approval — as decided in
sessions), RUNBOOK sections added (release, upgrade, e2e, backup-status), erp-status updated.

---

## Session progress (2026-07-19, A, `C:\AhmedGaid\ERP`)

Not all boxes checked — **not renaming `_done` yet.** Real remaining work for a follow-up
session, in priority order:
1. Run the Playwright suite (or Option-B journey list) once the B-collision situation is
   clear of this checkout.
2. Live-verify saved views on 2 more list pages (only Sales Orders checked this session).
3. Live drag-drop + RTL column-order check on the CRM Kanban board.
4. Run the actual conductor-brand visual feel checklist (screenshots were unreliable this
   session — may need a fresh browser tab/session to get a working screenshot tool).
5. CHANGELOG + RUNBOOK staleness — B's territory (`Docs/plan/PARALLEL_PLAN.md` ownership map),
   not fixed here; needs B or a future checkpoint session.
Everything else above is checked off with its verification method noted inline — a follow-up
session can trust those and focus only on the 5 items above.

## After This Session

```
All boxes checked?  ← TIER 3 + PLAN COMPLETE — final merge checkpoint
→ Rename with _done. Update erp-status (plan complete; queue advances).
→ Tell the user: clear session, start fresh — the queue's next position takes over.

This session (2026-07-19, A): NOT all boxes checked — see "Session progress" above.
File stays open (no _done suffix). erp-status updated to reflect partial progress + the
5-item remainder list, not "plan complete."
```
