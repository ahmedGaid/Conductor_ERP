# Demo Deploy — free public sales-demo, auto-updated from `main`

**Goal:** one free, public URL showing Conductor ERP with demo data, for sales calls — not
production/unattended. Auto-refreshes whenever `main` gets a push.

**Not in scope:** multi-tenant SaaS, HA, backups, security hardening beyond defaults — disposable,
supervised sales demo, reset nightly. Shared doc: either lane (A or B) may execute — see Ownership
note below.

## STATUS (2026-07-17): host pivoted VM → Render → PC — card friction every step
Oracle Free VM signup rejected the card (Oracle's fraud/verification is known to falsely-decline,
especially non-US cards). Render was the next pick, but it also requires a card on file (confirmed
by the user's own signup attempt — as of 2026 essentially every always-on cloud free tier
(Oracle/Google Cloud/AWS/Azure/Fly.io/Koyeb/Render) gates behind a card, industry-wide anti-abuse
move). Genuinely card-free multi-service alternatives (PythonAnywhere, Appliku+Hetzner) all have
real dealbreakers (PythonAnywhere: SQLite-only + no background workers/scheduled tasks on new free
accounts since Jan 2026; Appliku is a deploy tool, not a host — still needs a real card-bearing
server underneath).

**Chosen path is now: the user's own PC** (see "PC path" below) — zero card, zero cost, and a
strictly BETTER fit than Render for this app: runs the existing `docker-compose.yml` unmodified
(real Postgres + real Celery worker/beat, no SQLite-compatibility risk, no
`CELERY_TASK_ALWAYS_EAGER` compromise needed), fronted by a free Cloudflare Tunnel (outbound-only,
no router ports opened). Matches the actual use case restated by the user: a supervised sales-call
demo, not an unattended 24/7 public product — the PC only needs to be on/connected when a prospect
might click the link.

The Render and VM/docker-compose sections below are kept for reference (Render section = what to
do if a workaround card becomes available and a "real" host is preferred later; VM section =
shelved). Files for each path, so it's clear what's active:
- **PC path (ACTIVE):** `deploy/demo-redeploy.ps1`, `deploy/demo-watch-and-deploy.ps1`,
  `deploy/demo-nightly-reset.ps1`, `deploy/register-demo-tasks.ps1`.
- **Render path (fallback, needs a card):** `.github/workflows/nightly-demo-reset.yml`.
- **VM path (shelved):** `.github/workflows/deploy-demo.yml`, `deploy/demo-redeploy.sh`,
  `deploy/demo-nightly-reset.sh`, `deploy/.env.demo.example`.

## PC path (ACTIVE)
1. Install Docker Desktop (free, no card) if not already present; set it to start at login.
2. Install `cloudflared` (`winget install --id Cloudflare.cloudflared.cloudflared`). Two options:
   - **Quick tunnel** (zero signup): `cloudflared tunnel --url http://localhost:8000` → gives an
     instant `https://<random>.trycloudflare.com` URL. Simplest, but the hostname changes if the
     tunnel process restarts — fine if you keep one `cloudflared` process running continuously and
     just resend the link if the PC ever reboots.
   - **Named tunnel** (stable hostname, needs a free Cloudflare account + a domain on its free DNS):
     `cloudflared tunnel login` → `cloudflared tunnel create demo` → route it to a hostname like
     `demo.yourdomain.com` → `cloudflared tunnel run demo`. No card either way — Cloudflare's free
     plan only needs an email.
3. `cd` to the repo, copy `deploy/.env.demo.example` → `.env`, fill in secrets. Set
   `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` to whichever hostname step 2 gave you.
4. `docker compose up -d` — real full stack, nothing trimmed.
5. Seed once: `docker compose exec web python manage.py seed_identity`, `...seed_accounting`,
   `docker compose exec web python scripts/seed_demo.py` (or just run
   `deploy/demo-nightly-reset.ps1` once — it does teardown+seed together).
6. Auto-redeploy on push to `main`: a home PC has no inbound path for GitHub to reach (that's the
   point of the tunnel being outbound-only), so it's inverted — `deploy/demo-watch-and-deploy.ps1`
   polls `origin/main` on a schedule and redeploys when it moved, instead of GitHub pushing to us.
7. Elevated PowerShell, once: `deploy\register-demo-tasks.ps1` — registers two Scheduled Tasks
   (watch-and-redeploy every 5 min, nightly reset at 03:00), running as the current user (S4U logon,
   no stored password) since `docker compose` needs the logged-in user's Docker Desktop session —
   a SYSTEM-context task (like the existing backup task) can't reach it.
8. Keep the PC on + network connected whenever a prospect might click the link (e.g. during a
   scheduled call). Not for an unsupervised "click anytime" public link — that's an accepted
   trade-off for zero cost/card.

## Render path (ACTIVE)
1. render.com → sign up via GitHub → connect `ahmedGaid/Conductor_ERP`.
2. New → PostgreSQL → Free instance, pick a region (e.g. Frankfurt) → wait for provisioning →
   copy both the **Internal Database URL** (for the web service) and **External Database URL**
   (for seeding from a laptop + the nightly-reset workflow).
3. New → Web Service → same repo → Environment: **Docker** (uses the repo's root `Dockerfile`
   as-is, default CMD `python deploy/serve_waitress.py` already serves API+SPA same-origin) →
   Instance Type: **Free** → same region as the Postgres instance.
4. Env vars on the web service:
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`
   - `DJANGO_SECRET_KEY=` (generate a 50+ char random value)
   - `DJANGO_DEBUG=false`
   - `DJANGO_ALLOWED_HOSTS=<yourapp>.onrender.com`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://<yourapp>.onrender.com`
   - `DATABASE_URL=` (the Internal Database URL from step 2)
   - `CELERY_TASK_ALWAYS_EAGER=true` (no worker/beat container on Render free tier — tasks run
     inline instead; `erp/monitoring` admin status page will show `redis`/`workers` as red, that's
     expected and admin-only, not customer-visible)
   - `RUN_MIGRATIONS=true` (single instance, entrypoint.sh gates migrate/collectstatic on this)
   - `PORT=8000` — **verify at deploy time**: Render's Docker runtime may default to port 10000;
     `serve_waitress.py` listens on `CONDUCTOR_PORT` (default 8000, matches the Dockerfile's
     `EXPOSE 8000`) — if Render's logs show a port-binding mismatch, this env var is the fix.
5. Deploy. Known limitation, accepted for a demo: Render free web service disk is **ephemeral** —
   any file a prospect uploads live vanishes on the next redeploy/restart (fine, it's a demo).
   Also no Celery beat means the hourly/daily scheduled jobs (`CELERY_BEAT_SCHEDULE` in
   `config/settings/base.py` — scheduled reports, AI digests, webhook retry sweep) never fire;
   accepted gap, not needed for a sales walkthrough.
6. Seed once: point a **local** shell at Render's Postgres (simpler than relying on Render's Shell
   tab) —
   ```
   set DATABASE_URL=<External Database URL from step 2>
   set DJANGO_SETTINGS_MODULE=config.settings.prod
   .venv\Scripts\python.exe manage.py migrate
   .venv\Scripts\python.exe manage.py seed_identity
   .venv\Scripts\python.exe manage.py seed_accounting
   .venv\Scripts\python.exe scripts\seed_demo.py
   ```
7. Auto-deploy on push to `main`: **native to Render, nothing to configure** — connect the repo
   (step 1) and it redeploys on every push to the branch you pick in the service settings.
8. Nightly reset: Render has no free cron job, so `.github/workflows/nightly-demo-reset.yml`
   (already added) uses GitHub Actions' free scheduler instead — wipes + reseeds via the External
   Database URL. Needs one repo secret: `RENDER_DEMO_DATABASE_URL` (the External Database URL).

---

## VM path (SHELVED fallback — kept for reference, not the active plan)
Reuses the existing single-tenant Docker stack (`Dockerfile` + `docker-compose.yml` + `deploy/`)
— no CORS split (SPA + API already same-origin via Waitress+Whitenoise — see `docker-compose.yml`
comments).

## Architecture
```
GitHub (push to main)
      │  GitHub Actions (deploy-demo.yml, SSH)
      ▼
Free VM (Oracle A1.Flex; fallback: E2.1.Micro / Fly.io / Render free tier)
      │  docker compose up -d   (existing docker-compose.yml, UNMODIFIED)
      ├── web    — Django + built React SPA, same origin, Waitress :8000
      ├── worker — Celery
      ├── beat   — Celery beat
      ├── db     — Postgres 16
      └── redis  — Celery broker
      │
Cloudflare Tunnel (free) → public HTTPS URL, no open firewall ports, no purchased domain needed
```

## Why this shape
- Existing image already serves SPA+API same origin → `DJANGO_CORS_ALLOWED_ORIGINS` stays empty,
  no CORS work needed (`deploy/.env.prod.example` line 24 confirms "not needed by default").
- `deploy/docker/entrypoint.sh` already runs migrate + collectstatic on `web` boot
  (`RUN_MIGRATIONS=true`) — nothing new to write there.
- Cloudflare Tunnel replaces Nginx+ports+origin-cert steps — no OCI security-list/ufw dance,
  works even if the free VM lands with no public IP.

## New files (infra-only — touches nothing under `erp/**` or `apps/web/**`)
1. `.github/workflows/deploy-demo.yml` — on push to `main`: SSH to VM, run
   `deploy/demo-redeploy.sh`. GitHub repo secrets needed: `DEMO_SSH_HOST`, `DEMO_SSH_USER`,
   `DEMO_SSH_KEY` (dedicated deploy key; restrict via `command=` in the VM's `authorized_keys`
   if practical).
2. `deploy/demo-redeploy.sh` — `git pull --ff-only && docker compose build && docker compose up -d`.
3. `deploy/demo-nightly-reset.sh` + a VM crontab entry — `docker compose down -v && docker compose
   up -d`, then re-run seeds (`migrate`, `seed_identity`, `seed_accounting`,
   `scripts/seed_demo.py`) inside the `web` container. Demo looks fresh every morning, survives a
   prospect (or you, live) making a mess the day before.
4. `deploy/.env.demo.example` — copy of `deploy/.env.prod.example` with `DJANGO_ALLOWED_HOSTS` /
   `DJANGO_CSRF_TRUSTED_ORIGINS` set to the Cloudflare Tunnel hostname, `DJANGO_DEBUG=false`,
   demo-labelled `DEFAULT_FROM_EMAIL`.

## One-time manual steps (user — needs account access, not agent-executable)
1. Create Oracle Cloud Free VM (A1.Flex shape; "out of host capacity" → retry across
   availability domains, or fall back to E2.1.Micro / Fly.io / Render free tier).
2. Install Docker + `cloudflared` on the VM; `cloudflared tunnel create demo` → point at
   `localhost:8000`; note the hostname it gives you.
3. Clone repo to VM, copy `deploy/.env.demo.example` → `.env`, fill in secrets.
4. Add the 3 GitHub secrets (`DEMO_SSH_HOST/USER/KEY`) in repo Settings → Secrets → Actions.
5. First boot: `docker compose up -d`, then seed once (migrate + seed_identity + seed_accounting +
   `scripts/seed_demo.py`) inside the `web` container.
6. Add nightly reset to VM crontab: e.g. `0 3 * * * /path/to/deploy/demo-nightly-reset.sh`.

## Ownership / lane note
Infra-only — doesn't touch `erp/**` (A/B feature territory) or `apps/web/**` (A territory). Either
agent lane may execute the "New files" section without conflict; whichever lane is free next picks
it up, note the task in `PARALLEL_PLAN.md` if run mid-wave. Manual steps (VM/DNS/GitHub secrets)
are the user's — they need account credentials neither agent has.

## Acceptance
- Push to `main` → within ~1–2 min, public demo URL reflects it, no manual redeploy step.
- Fresh visit every morning shows clean seeded demo data regardless of the day before.
- Zero recurring cost at every layer (VM, tunnel, DNS, CI minutes).
