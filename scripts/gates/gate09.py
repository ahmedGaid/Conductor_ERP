"""Gate 09 — CRM (leads → pipeline → win, support tickets/SLA, cross-module to Sales).

Asserts:
- the CRM test suite passes — lead convert creates an opportunity (once only), winning an
  opportunity creates a **draft sales order via the sales public contract** whose subtotal matches
  the opportunity amount, unknown-customer / empty-opportunity wins are rejected, and ticket SLA
  breach is computed from priority;
- the CRM API is mounted;
- module boundary: CRM drives Sales ONLY through `erp.sales.contracts` — never its domain/models/
  services — and does not reach into accounting/inventory internals;
- money is integer minor units; transitions are atomic;
- the React CRM screens exist and are wired.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CRM = REPO_ROOT / "erp" / "crm"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

CRM_TESTS = ["erp/crm/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *CRM_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 5f CRM tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted.
    _assert("erp.crm.api.urls" in _read("config/urls.py"), "CRM API not mounted")

    # 3. Module boundary: CRM uses ONLY the public contract of sales.
    pipeline_src = _read("erp/crm/services/pipeline.py")
    _assert("from erp.sales import contracts" in pipeline_src or
            "from erp.sales.contracts import" in pipeline_src, "CRM must use sales.contracts")
    for forbidden in (
        "erp.sales.domain", "erp.sales.models", "erp.sales.services",
        "erp.accounting.domain", "erp.accounting.services",
        "erp.inventory.domain", "erp.inventory.services",
    ):
        # services may legitimately import nothing of these; scan every CRM service module.
        for path in (CRM / "services").rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            _assert(forbidden not in src, f"CRM reaches past a contract into {forbidden} ({path.name})")
    _assert("transaction.atomic" in pipeline_src, "CRM pipeline transitions are not atomic")
    _assert("UnknownCustomerError" in pipeline_src, "win must validate the sales customer via the contract")

    # 4. Money is integer minor units (no float columns).
    models_src = _read("erp/crm/domain/models.py")
    _assert("FloatField" not in models_src, "CRM must not use FloatField for money")
    _assert("BigIntegerField" in models_src, "money columns must be integer minor units")

    # 5. No raw SQL.
    for path in CRM.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 6. React CRM screens exist and are wired.
    for rel in (
        "api/crm.ts",
        "pages/crm/PipelinePage.tsx",
        "pages/crm/OpportunityDetailPage.tsx",
        "pages/crm/LeadsPage.tsx",
        "pages/crm/TicketsPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing CRM screen: src/{rel}")

    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    for route in ("/crm", "/crm/opportunities/:id", "/crm/leads", "/crm/tickets"):
        _assert(route in app, f"App.tsx missing CRM route: {route}")

    detail = (WEB_SRC / "pages" / "crm" / "OpportunityDetailPage.tsx").read_text(encoding="utf-8")
    for action in ("win", "lose", "Stage"):
        _assert(action in detail, f"opportunity detail missing {action} action")

    # CRM promoted to an active sidebar module (not in the "coming soon" list anymore).
    sidebar = (WEB_SRC / "app" / "Sidebar.tsx").read_text(encoding="utf-8")
    _assert('to: "/crm"' in sidebar, "CRM is not an active sidebar module")
