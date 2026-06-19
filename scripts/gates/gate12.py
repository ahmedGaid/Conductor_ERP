"""Gate 12 — Phase 10 hardening (security + performance).

Asserts:
- the security/perf test suite passes — DRF rate limiting actually returns 429 past the limit, and
  the heaviest list endpoint (journals) serializes N rows in a bounded number of queries (no N+1);
- rate limiting is wired in base settings (anon + user throttles);
- production settings declare the OWASP hardening directives and require a real secret;
- Django's own deployment checklist (`manage.py check --deploy --fail-level WARNING`) passes under
  the production settings module — the authoritative proof that the prod posture is hardened.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SEC_TESTS = ["erp/monitoring/tests/test_security_perf.py"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite: throttle blocks past the limit; journals list query budget holds.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *SEC_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Phase 10 security/perf tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-800:]
        )

    # 2. Throttling wired in base settings.
    base = _read("config/settings/base.py")
    for sym in ("DEFAULT_THROTTLE_CLASSES", "AnonRateThrottle", "UserRateThrottle", "DEFAULT_THROTTLE_RATES"):
        _assert(sym in base, f"base settings missing throttle config: {sym}")

    # 3. Production settings declare the OWASP hardening directives + require a real secret.
    prod = _read("config/settings/prod.py")
    for sym in (
        "SECURE_SSL_REDIRECT",
        "SECURE_HSTS_SECONDS",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS",
        "SECURE_PROXY_SSL_HEADER",
        "CSRF_TRUSTED_ORIGINS",
        "SESSION_COOKIE_SECURE",
        "CSRF_COOKIE_SECURE",
    ):
        _assert(sym in prod, f"prod settings missing hardening directive: {sym}")
    _assert('SECRET_KEY = env("DJANGO_SECRET_KEY")' in prod, "prod must require DJANGO_SECRET_KEY with no default")

    # 4. Django's deployment checklist must pass under the prod settings module (the real proof).
    deploy_env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_SECRET_KEY": "aB3dE6fH9jK2mN5pQ8rS1tU4vW7xY0zCdEfGhIjKlMnOpQrStUvWxYz012345",
        "DJANGO_ALLOWED_HOSTS": "erp.example.com",
        "DJANGO_COOKIE_SECURE": "True",
        "DJANGO_SSL_REDIRECT": "True",
    }
    deploy = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env=deploy_env,
    )
    if deploy.returncode != 0:
        raise AssertionError(
            "manage.py check --deploy (prod) reported issues:\n" + deploy.stdout[-2500:] + "\n" + deploy.stderr[-800:]
        )
