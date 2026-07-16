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
- [ ] Version visible (UI + /health); CHANGELOG current; RUNBOOK release steps accurate
- [ ] `manage.py upgrade --yes` no-op clean; gate16 drill green; gate17 snapshot green
- [ ] Playwright suite (or Option-B journey list) green on the seeded env
- [ ] Webhook subscription fires signed payload on sales-order confirm; retries + log correct
- [ ] Saved views: create/share/default/switch on ≥3 list pages

Tier 2:
- [ ] ⌘K: record actions run, assistant opens with context, permission-filtered
- [ ] Approval node halts/notifies/resumes; decision audited
- [ ] AI node drafts via catalog action as the actor; validator blocks approval-less writes
- [ ] Custom field full loop (define → form → value → column → saved view → export)
- [ ] Timeline tab on the four record types; AI/import entries link to source

Tier 3:
- [ ] API key curl round-trip + role limit; docs page matches gate17 inventory
- [ ] Help journeys open from `?`/⌘K; glossary == Identity System §6 (verify ALL entries)
- [ ] Empty-state taxonomy correct on every list page (spot 6 pages × 3 causes where possible)
- [ ] Inline edit + undo; posted docs refuse with reason; peek coverage table complete
- [ ] Kanban drag + menu fallback + RTL column order
- [ ] System panel degraded-state drill (stop/start Redis); no env values leak
- [ ] AI cost page numbers reconcile with traces

## Regression (nothing existing broke)

- [ ] The delivery-track E2E drives (FILE_01_E2E_RESULTS.md) re-pass: sales, purchasing,
      accounting, CRM/pricing, workflows
- [ ] `python scripts/gates/_run.py all` (now 00–17) green
- [ ] `node scripts/check-i18n-parity.mjs` + `npx tsc -b` + `python scripts/gates/gate03.py` green
- [ ] Trial balance balances after all acceptance activity

## Micro-polish pass

Sweep the new surfaces once against the conductor-brand checklist: any raw hex, physical CSS,
missing designed state, second Arabic word, un-settled motion → fix now, in this session.

## Sign-off block (write into the commit message)

What was built (tier summary), what was deliberately NOT touched (refuse-list confirmations:
no custom objects, no dashboard builder, no GraphQL, no marketplace), DECISIONS entries present
(versioning scheme, Playwright choice, webhook SSRF posture, custom-fields boundary, saved-views
sharing), Identity System §6 terms added (view, webhook, custom field, approval — as decided in
sessions), RUNBOOK sections added (release, upgrade, e2e, backup-status), erp-status updated.

---

## After This Session

```
All boxes checked?  ← TIER 3 + PLAN COMPLETE — final merge checkpoint
→ Rename with _done. Update erp-status (plan complete; queue advances).
→ Tell the user: clear session, start fresh — the queue's next position takes over.
```
