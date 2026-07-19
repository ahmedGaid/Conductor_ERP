"""Gate 01 — core platform: auth/RBAC/2FA, audit, events, full system-check.

Asserts:
- the Stage 1 test suite (auth+RBAC+2FA, event isolation, audit immutability) passes;
- default RBAC roles seed correctly (idempotent);
- /system-check reports the worker/queue component and stays non-critical.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

STAGE1_TESTS = [
    "erp/core/tests",
    "erp/identity/tests",
    "erp/audit/tests",
]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check() -> None:
    # 1. Stage 1 test suite passes (run in a subprocess so pytest manages its own test DB).
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *STAGE1_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 1 tests failed:\n" + result.stdout[-2000:] + "\n" + result.stderr[-1000:]
        )

    # 2. Default roles seed idempotently, and the DEFAULT seed is customer-safe.
    from django.core.management import call_command

    call_command("seed_identity", verbosity=0)
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from erp.identity.roles import DEFAULT_ROLES

    for role in DEFAULT_ROLES:
        _assert(Group.objects.filter(name=role).exists(), f"missing seeded role: {role}")

    # The default seed always provisions the admin login. (The customer-safe invariant —
    # that the default path creates NO shared-password demo users — is pinned by
    # test_seed_default_is_admin_only, which runs on an isolated DB; asserting absence here
    # would be unreliable against the persistent dev DB seeded by earlier --demo-users runs.)
    User = get_user_model()
    _assert(User.objects.filter(username="admin", is_superuser=True).exists(), "admin user not seeded")

    # 3. system-check includes the worker/queue component and isn't critical.
    from django.test import Client

    body = Client().get("/system-check").json()
    _assert("workers" in body["components"], "system-check missing workers component")
    for name in ("database", "redis", "storage", "workers"):
        _assert(name in body["components"], f"system-check missing {name}")
    _assert(body["status"] != "critical", f"system-check critical: {body}")
