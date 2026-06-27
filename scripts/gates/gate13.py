"""Gate 13 — Phase 11 deployment packaging + runbook (the final phase).

Asserts the install is *shippable*: the one Django process serves the built React SPA, and the
operator has everything needed to install, run, back up, and recover it.

- the SPA test suite passes — the root view returns the built bundle (HashRouter, so only ``/`` is
  ever served) and degrades to a 503 build-hint (never a 500) when the bundle is absent;
- WhiteNoise is wired in **prod** settings (middleware + compressed-manifest static storage +
  serving the Vite build at the root), and the runtime deps (whitenoise, waitress) are declared;
- the SPA root view is mounted **last** in the URL conf so API/admin/health win;
- the Windows deployment kit is present and coherent: a prod env template, the waitress entrypoint,
  the NSSM service install/uninstall scripts (web + worker + beat), the nightly backup + tested
  restore + scheduled-task scripts, and the operator runbook.

This gate deliberately does NOT re-run ``manage.py check --deploy`` — gate12 already owns the
security-posture proof; gate13 owns packaging coherence.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SPA_TESTS = ["erp/monitoring/tests/test_spa.py"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite: the SPA shell is served at the root and degrades gracefully.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *SPA_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Phase 11 SPA-serving tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-800:]
        )

    # 2. WhiteNoise wired in prod settings (serve the bundle + compressed-manifest Django static).
    prod = _read("config/settings/prod.py")
    for sym in (
        "whitenoise.middleware.WhiteNoiseMiddleware",
        "CompressedManifestStaticFilesStorage",
        "WHITENOISE_ROOT",
        "apps",  # WHITENOISE_ROOT points at apps/web/dist
    ):
        _assert(sym in prod, f"prod settings missing WhiteNoise wiring: {sym}")

    # 3. Runtime serving deps declared.
    reqs = _read("requirements.txt")
    for dep in ("whitenoise", "waitress"):
        _assert(dep in reqs, f"requirements.txt missing prod-serving dependency: {dep}")

    # 4. SPA root view mounted last (after admin/api/health) so real routes win.
    urls = _read("config/urls.py")
    _assert("spa_index" in urls, "config/urls.py does not mount the SPA root view")
    spa_idx = urls.index('path("", spa_index')
    last_api_idx = urls.rfind('include("erp.notifications.api.urls")')
    _assert(spa_idx > last_api_idx, "SPA root view must be mounted AFTER the API routes")
    _assert(Path(REPO_ROOT / "config" / "spa.py").exists(), "config/spa.py (SPA view) missing")

    # 5. The Windows deployment + backup kit and the operator runbook are present.
    required = [
        "deploy/.env.prod.example",
        "deploy/serve_waitress.py",
        "deploy/windows/install-services.ps1",
        "deploy/windows/uninstall-services.ps1",
        "deploy/backup/backup.ps1",
        "deploy/backup/restore.ps1",
        "deploy/backup/register-backup-task.ps1",
        "Docs/RUNBOOK.md",
    ]
    for rel in required:
        _assert((REPO_ROOT / rel).exists(), f"deployment artifact missing: {rel}")

    # 6. The install script registers all three services (web + worker + beat) and the runbook
    #    documents backup/restore — cheap coherence checks against silent drift.
    install = _read("deploy/windows/install-services.ps1")
    for svc in ("Conductor-Web", "Conductor-Worker", "Conductor-Beat"):
        _assert(svc in install, f"install-services.ps1 does not register {svc}")
    _assert("--pool=solo" in install, "Celery worker on Windows must use --pool=solo")

    env_tmpl = _read("deploy/.env.prod.example")
    _assert("config.settings.prod" in env_tmpl, ".env.prod.example must select the prod settings")
    _assert("DJANGO_SECRET_KEY" in env_tmpl, ".env.prod.example must require a secret key")

    runbook = _read("Docs/RUNBOOK.md")
    for kw in ("collectstatic", "restore.ps1", "register-backup-task.ps1", "install-services.ps1"):
        _assert(kw in runbook, f"RUNBOOK.md does not document: {kw}")

    # 6b. The Docker Compose deployment kit is present and coherent: the image build, the stack
    #     definition, the container entrypoint, the env template, and a one-command backup/restore
    #     (the Docker parity of the Windows backup kit, for the self-hoster who runs `docker compose
    #     up`). RUNBOOK documents the Docker backup path too.
    docker_required = [
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        ".env.docker.example",
        "deploy/docker/entrypoint.sh",
        "deploy/docker/backup.sh",
        "deploy/docker/restore.sh",
    ]
    for rel in docker_required:
        _assert((REPO_ROOT / rel).exists(), f"Docker deployment artifact missing: {rel}")

    compose = _read("docker-compose.yml")
    for sym in ("postgres:16", "pg_data", "RUN_MIGRATIONS"):
        _assert(sym in compose, f"docker-compose.yml missing expected piece: {sym}")

    for kw in ("docker/backup.sh", "docker/restore.sh", "docker compose"):
        _assert(kw in runbook, f"RUNBOOK.md does not document the Docker backup path: {kw}")

    # 7. The .ps1 scripts must be pure ASCII. Windows PowerShell 5.1 reads a BOM-less file as ANSI,
    #    so a stray non-ASCII char (e.g. an em-dash) makes the whole script fail to PARSE on the
    #    target. Keep them ASCII-only so encoding can never break the operator's deploy.
    for rel in (
        "deploy/windows/install-services.ps1",
        "deploy/windows/uninstall-services.ps1",
        "deploy/backup/backup.ps1",
        "deploy/backup/restore.ps1",
        "deploy/backup/register-backup-task.ps1",
    ):
        raw = (REPO_ROOT / rel).read_bytes()
        bad = next((i for i, b in enumerate(raw) if b > 0x7F), -1)
        _assert(bad == -1, f"{rel} has a non-ASCII byte at offset {bad} — Windows PowerShell 5.1 will fail to parse it")

    # 8. The waitress entrypoint must put the repo root on sys.path — launched as
    #    `python deploy/serve_waitress.py` (directly or via NSSM) sys.path[0] is deploy/, not the
    #    repo root, so `import config` would otherwise fail at startup.
    serve = _read("deploy/serve_waitress.py")
    _assert("sys.path.insert" in serve, "serve_waitress.py must add the repo root to sys.path before importing config")
