# FILE_02 — CI safety net  🟠 High

## The finding
Only two GitHub Actions workflows exist — `deploy-demo.yml` (SSH deploy) and
`nightly-demo-reset.yml` (cron DB reset). **Neither runs any test, gate, lint, or typecheck.** All
quality gating is a manual local step, so nothing stops a regression reaching `main`. "Gates green"
is currently a narrative claim (commit messages, `DECISIONS.md`) with no persisted proof of a run.

## Before you start (read)
- `.github/workflows/deploy-demo.yml`, `.github/workflows/nightly-demo-reset.yml` (existing shape)
- `scripts/gates/_run.py` (the harness CI will call)
- `pyproject.toml` `[tool.pytest.ini_options]`; `apps/web/package.json` scripts
- `Dockerfile` (services CI needs: Postgres 16, Redis)

## Tasks
- [ ] Add `.github/workflows/ci.yml`, triggered on `push` + `pull_request` to `main`.
- [ ] Job `backend`: Python 3.13, `pip install -r requirements.txt`, spin up Postgres 16 + Redis
      service containers, run `python scripts/gates/_run.py all` then `pytest` (settings
      `config.settings.dev`).
- [ ] Job `web`: Node 24, `npm ci` in `apps/web`, run `node scripts/check-i18n-parity.mjs` +
      `npx tsc -b` + `npm run build` (which fires the bundle-size + i18n prebuild guards).
- [ ] Fail the workflow on any non-zero exit. No `continue-on-error`.
- [ ] Add a green-CI status badge to `README.md`.
- [ ] Do NOT touch the deploy or nightly-reset workflows.

## Watch
- The gate harness expects DB + Redis reachable (`gate00`) — use service containers, health-check
  them before the gate step, matching `docker-compose.yml` service config.
- `gate15` (AI eval) is non-blocking by design — confirm it does not hard-fail CI without keys; if
  it needs a network/model it can't reach in CI, run gates `00–14,16,17` in CI and leave `15` local
  (note the exclusion in the workflow comment).
- No new *runtime* dependency is added; CI actions are infra, not app deps.

## Done when
A pull request against `main` shows the CI workflow running gates + pytest + web checks, and a
deliberately-broken commit makes CI red. README shows the badge.

## How to test
- Open a throwaway PR with a trivial change → CI runs and passes.
- Push a commit that breaks a test or a type → CI turns red on the matching job.
- `git log`/Actions tab shows the run as the persisted proof the audit said was missing.
