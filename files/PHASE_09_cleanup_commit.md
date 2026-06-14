# Phase 09 — Cleanup, Full Verify, Commit & Push

## Goal
Final sweep: remove implementation noise, prove the whole build with one command, then commit and push.

## Files to touch
- whole repo (cleanup pass)
- `README.md` — quickstart (`db:up`, migrate, seed, `dev:api`, `dev:web`, `gate:all`)
- `DECISIONS.md` — finalize the deviation/forbidden-temptation log
- `scripts/gates/gate09.ts`

## Compact
- Remove debug `console.log` added during implementation (keep the structured logger).
- Remove every `TODO`/`FIXME` not tracked in `DECISIONS.md`.
- `npm run lint -- --fix` in both workspaces; ensure no unused imports; `npm run typecheck` clean.
- Confirm nothing on the forbidden list was built (no accounting/inventory logic, no ERP core modules as business
  logic, no AI/LLM code, no BPMN engine, no queues/multi-node infra, no auth beyond the dev user). gate09 greps for
  red-flag imports/usages and fails if found.

## Final verify (definition of done)
```bash
npm run gate:all
```
Must exit `0`. This transitively runs gates 00–08 (schema, engine determinism/crash-resume/idempotency, adapters,
API, i18n/RTL build gate, screens, and the full e2e), i.e. every success-criteria box.

## Git
```bash
git add -A
git commit -m "feat: graph-based ERP workflow orchestration layer MVP (engine, adapters, bilingual RTL UI, PR-approval reference flow)"
git push        # if no git remote is configured: skip and record 'no remote' in DECISIONS.md
```

## Verification (gate:09)
- [ ] `npm run lint` and `npm run typecheck` exit 0 in both workspaces.
- [ ] No forbidden-list code present (grep gate passes).
- [ ] `README.md` documents the full quickstart and the `gate:all` definition of done.
- [ ] `npm run gate:all` exits 0.
- [ ] A commit exists on the current branch with the message above (and a push, unless no remote — noted in DECISIONS.md).

## Done signal
`npm run gate:all` is green, the tree is clean, and the work is committed (and pushed if a remote exists).
The MVP is complete.
