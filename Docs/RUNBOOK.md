# Conductor ERP — Operator Runbook (Phase 11)

> The single document an operator needs to **install, run, upgrade, back up, and recover** a
> customer-hosted Conductor ERP install on Windows Server. Customer-hosted, single-tenant: the
> customer owns every secret and every byte of data. No cloud dependency.

## 0. Architecture in one paragraph
One Django process (served by **waitress**) answers the API **and** serves the built React SPA +
Django/DRF static via **WhiteNoise** — there is no separate web server for static files. Two Celery
processes run alongside it: a **worker** (background jobs — reports, notifications, workflow steps)
and **beat** (the periodic scheduler, e.g. the hourly scheduled-report sweep). State lives in
**PostgreSQL 16** (all business data) and **Redis** (Celery broker/results + cache/throttle). The
frontend is a **HashRouter** SPA, so the server only ever serves `/` — no URL-rewrite rules needed.
Put **IIS/Nginx in front only for TLS** and a public hostname; it reverse-proxies to waitress on
`127.0.0.1:8000`.

```
            HTTPS                         127.0.0.1:8000
  Browser ───────► IIS/Nginx (TLS) ───────────────────► waitress ─► Django (API + WhiteNoise static/SPA)
                                                                      │
                                                  PostgreSQL ◄────────┼────────► Redis
                                                                      │
                                              Celery worker + beat ───┘  (own services, share the venv + .env)
```

Services (registered via NSSM): **Conductor-Web**, **Conductor-Worker**, **Conductor-Beat**.

## 1. Prerequisites (install once)
| Component | Notes |
|---|---|
| Python 3.13 | per-machine install; used to create the venv |
| PostgreSQL 16 | service `postgresql-x64-16`; create DB `erp` + role `erp` (see §3) |
| Redis | a Windows Redis service named `Redis` (winget `Redis.Redis`), auto-start |
| Node 20+ / npm | only to **build** the frontend bundle (not needed at runtime) |
| NSSM | https://nssm.cc — wraps the three processes as Windows services |

## 1a. Quick local run (one file)
Once the venv + `.env` exist and PostgreSQL/Redis are up, **double-click `run.cmd`** at the repo
root (or run it from a terminal). It builds the frontend on first run, migrates, seeds the baseline
users + chart of accounts (idempotent), and starts the **whole app in one foreground process**
(waitress + WhiteNoise serving API + static + the React UI) at <http://127.0.0.1:8000> — no Vite
dev server, no background windows. Sign in `admin` / `Dev12345!`; Ctrl+C to stop. Celery
worker/beat are NOT started by `run.cmd` (background jobs are optional — see §2 for services).

## 2. First install
```powershell
# From the repo root (e.g. C:\AhmedGaid\ERP)
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Configure the environment
copy deploy\.env.prod.example .env
notepad .env          # set DJANGO_SECRET_KEY, DATABASE_URL, DJANGO_ALLOWED_HOSTS, CSRF/SSL, SMTP...

# Build the frontend bundle (produces apps/web/dist, which Django then serves)
cd apps\web; npm ci; npm run build; cd ..\..

# Database + Django static
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput   # gathers admin/DRF static for WhiteNoise

# Seed the baseline (identity roles/users + chart of accounts + fiscal periods)
.\.venv\Scripts\python.exe manage.py seed_identity
.\.venv\Scripts\python.exe manage.py seed_accounting
# (seed_demo.py is DEV demo data only — do NOT run it on a real customer install)

# Register + start the three services (run from an elevated PowerShell)
.\deploy\windows\install-services.ps1            # -Nssm <path> -BindHost 127.0.0.1 -Port 8000
Get-Service Conductor-*
```
Then point IIS/Nginx (TLS) at `http://127.0.0.1:8000` and browse to `https://<your-host>/`.
Sign in with the admin account created by `seed_identity` (change its password immediately).

### Smoke test
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health           # service liveness
Invoke-RestMethod http://127.0.0.1:8000/system-check     # db/redis/storage/workers
# GET / should return the SPA shell (index.html); /api/... requires a JWT.
```

## 3. PostgreSQL / Redis prod notes
- **Create DB + role** (as superuser `postgres`):
  ```sql
  CREATE ROLE erp LOGIN PASSWORD '<strong>';
  CREATE DATABASE erp OWNER erp;
  ```
  `scripts/sql/bootstrap_db.sql` has the canonical bootstrap. The `erp` role needs `CREATEDB` only
  for running the test/gate suite (it builds a throwaway test DB) — a pure prod role does not.
- **Redis** must be running before the worker/beat start; the services declare a dependency on the
  `Redis` service. Verify: `& 'C:\Program Files\Redis\redis-cli.exe' ping` → `PONG`.
- Keep Postgres and Redis on the same host for a single-tenant install; both are in the backup story
  only for Postgres (Redis holds transient broker/cache state and is safe to lose).

## 4. Day-2 operations
```powershell
# Status / restart
Get-Service Conductor-*
Restart-Service Conductor-Web
# Logs (rotating, ~10 MB): deploy\logs\Conductor-*.out.log / .err.log
```

### Upgrading to a new release
```powershell
.\deploy\windows\uninstall-services.ps1        # or: Stop-Service Conductor-*  (stop writes first)
git pull                                        # or deploy the new code drop
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd apps\web; npm ci; npm run build; cd ..\..
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\deploy\windows\install-services.ps1          # re-register (idempotent) and start
```
Always take a backup (§5) **before** `migrate` on an upgrade.

## 5. Backup & restore (the DECISIONS policy: nightly backups + periodic tested restores)
**Nightly automated backup** — register once, runs at 02:00:
```powershell
.\deploy\backup\register-backup-task.ps1 -At 02:00 -OutDir C:\ConductorBackups -RetainDays 14
Start-ScheduledTask -TaskName ConductorNightlyBackup    # verify it runs now
```
Each run writes `C:\ConductorBackups\<timestamp>\` with `db.dump` (pg_dump custom format),
`storage.zip` (documents/reports, if any), and `MANIFEST.txt` (sizes + the exact restore command).
Runs older than the retention window are pruned automatically.

**Tested restore (do this periodically — an untested backup is not a backup):**
```powershell
# Restore the latest dump into a SCRATCH database and verify, WITHOUT touching production:
.\deploy\backup\restore.ps1 -DumpPath C:\ConductorBackups\<timestamp>\db.dump `
    -DbName erp_restore_test -CreateDb
# The script prints row counts for core tables. For a full drill, point a throwaway .env's
# DATABASE_URL at erp_restore_test and run the gate suite against it.
```

**Real recovery (destructive — restores the LIVE database):**
```powershell
Stop-Service Conductor-*                                 # stop all writes first
.\deploy\backup\restore.ps1 -DumpPath C:\ConductorBackups\<timestamp>\db.dump -DbName erp -Force
# restore storage.zip back into STORAGE_ROOT if documents were affected
Start-Service Conductor-*
```

### Docker deployments (`docker compose`)
A stack started with `docker compose up` has the **same backup story in one command** — the
PostgreSQL data lives in the `pg_data` volume inside the `db` container, so dump/restore go through
that container (no local `pg_dump` needed on the host). Both scripts are POSIX shell; run them from
any host with a shell (Linux VPS, or Git Bash / WSL on Windows).

**Take a backup** (writes a timestamped folder on the host, *outside* the Docker volume so it can be
copied offsite — `db.dump` custom format + best-effort `storage.tar.gz` + `MANIFEST.txt`):
```bash
deploy/docker/backup.sh                       # -> <repo>/backups/<timestamp>/
deploy/docker/backup.sh /mnt/offsite 30       # custom out-dir + keep 30 days
```
Schedule it with cron for nightly backups, e.g. `0 2 * * * /opt/conductor/deploy/docker/backup.sh`.

**Tested restore (safe — into a scratch db, never touches production):**
```bash
deploy/docker/restore.sh backups/<timestamp>/db.dump      # -> erp_restore_test, prints row counts
```

**Real recovery (destructive — restores the LIVE database; requires `--force`):**
```bash
docker compose stop web worker beat                       # stop writes first
deploy/docker/restore.sh backups/<timestamp>/db.dump --force
# if documents were affected: tar -xzf backups/<timestamp>/storage.tar.gz into the storage volume
docker compose start web worker beat
```

## 6. Health, security & troubleshooting
- **Endpoints:** `/health` (liveness), `/system-check` (db/redis/storage/workers), `/admin` (Django).
- **Security posture** is enforced by prod settings + verified by `gate12`
  (`manage.py check --deploy`): HSTS, SSL redirect, secure cookies, CSRF-trusted-origins, DRF rate
  limiting (anon/user). HTTPS is terminated at IIS/Nginx; waitress trusts `X-Forwarded-Proto`.
- **SPA shows a "not built yet" page:** `apps/web/dist` is missing — run `npm ci && npm run build`.
- **403/CSRF on POST:** add the public origin to `DJANGO_CSRF_TRUSTED_ORIGINS` in `.env`.
- **Worker/beat won't start:** confirm `Redis` service is running (`redis-cli ping` → `PONG`).
- **400 Bad Request on every page:** the host isn't in `DJANGO_ALLOWED_HOSTS`.

## 7. Release-candidate definition
A build is a release candidate when **`gate:all` is green** end to end:
```powershell
.\.venv\Scripts\python.exe scripts\gates\_run.py all     # gates 00–13
```
Gate 13 specifically proves the deployment packaging is coherent: WhiteNoise is wired, the SPA is
served at the root, and the deploy/backup kit + this runbook are present.
