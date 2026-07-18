# FILE_01 — ETA credentials + sandbox env config

## Goal
Wire the ERP to talk to ETA's sandbox: credentials via env/secrets only, a settings block for ETA
endpoints/env, and operator visibility (name-only) that credentials are present. No real submission
yet — just authenticated reachability.

## Before you start (read)
- `erp/einvoice/services/eta_adapter.py` (the seam being replaced)
- `config/settings/base.py` + `prod.py` (env pattern via `env(...)`)
- `erp/monitoring/status_api.py` (`_backup_report` / env-name-only reporting pattern to mirror)
- Current official ETA integrator onboarding docs (look up — sandbox base URLs, auth flow)

## Tasks
- [ ] Add ETA settings: `ETA_ENV` (sandbox|production), `ETA_BASE_URL`, `ETA_CLIENT_ID`,
      `ETA_CLIENT_SECRET`, `ETA_RIN` — all from env, empty default, documented in `.env.example`.
- [ ] Implement ETA auth (token acquisition) in a new `eta_client.py` module; cache the token to
      its TTL. Do NOT log the secret or token.
- [ ] Extend the operator status panel to report ETA config presence by NAME only + last-auth-ok
      timestamp (never the secret).
- [ ] `.env.example` documents the five vars with placeholder values; real values never committed.

## Watch
- Secrets: env only, `.gitignore` covers `.env`, status panel shows names not values (existing
  discipline in `status_api.py`).
- Sandbox base URL / auth flow is volatile — verify against current ETA docs, cite in DECISIONS.

## Done when
`manage.py` shell (or a tiny mgmt command) authenticates to the ETA sandbox with env creds and gets
a token; operator panel shows ETA-config-present + last-auth-ok; no secret in repo, logs, or panel.

## How to test
- Set sandbox creds in `.env` → run the auth check → token acquired (200).
- Unset creds → check reports "not configured", no crash.
- `grep -ri` repo for the secret value → absent.
