"""Gate 10 — E-Invoicing (ETA) compliance module.

Asserts:
- the e-invoicing test suite passes — invoicing a sales order records a draft ETA invoice **via the
  event bus** (decoupled), submit assigns a UUID, poll validates, record is idempotent, totals carry;
- the API is mounted;
- module boundary: e-invoicing is driven by the sales **event** (subscribes to the event NAME) and
  must NOT import sales' domain/models/services internals; the ETA call goes through the adapter;
- money is integer minor units; transitions are atomic;
- the React e-invoices screen exists and is wired.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EIN = REPO_ROOT / "erp" / "einvoice"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

EINVOICE_TESTS = ["erp/einvoice/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *EINVOICE_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 6 e-invoicing tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted + app registered.
    _assert("erp.einvoice.api.urls" in _read("config/urls.py"), "einvoice API not mounted")
    _assert("erp.einvoice" in _read("config/settings/base.py"), "einvoice app not installed")

    # 3. Decoupling: e-invoicing reacts to the sales event (by name) and never reaches into sales
    #    internals; the ETA call goes through the adapter, not inline.
    handlers_src = _read("erp/einvoice/handlers.py")
    _assert("ORDER_INVOICED" in handlers_src, "einvoice must subscribe to the sales OrderInvoiced event")
    for forbidden in ("erp.sales.domain", "erp.sales.models", "erp.sales.services"):
        for path in EIN.rglob("*.py"):
            if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
                continue
            _assert(forbidden not in path.read_text(encoding="utf-8"),
                    f"einvoice reaches past the event/contract into {forbidden}")
    issue_src = _read("erp/einvoice/services/issue.py")
    _assert("eta_adapter" in issue_src, "submission must go through the ETA adapter")
    _assert("transaction.atomic" in issue_src, "einvoice transitions are not atomic")

    # 4. Money is integer minor units (no float columns).
    models_src = _read("erp/einvoice/domain/models.py")
    _assert("FloatField" not in models_src, "einvoice must not use FloatField for money")
    _assert("BigIntegerField" in models_src, "money columns must be integer minor units")

    # 4b. Archiving + retrieval (FILE_05): the submitted document + ETA response are retained durably
    #     and there is a retrieval endpoint for audit/tax review.
    _assert("ETAInvoiceArchive" in models_src, "missing the ETAInvoiceArchive retention model")
    urls_src = _read("erp/einvoice/api/urls.py")
    _assert("/document" in urls_src, "missing the archived-document retrieval route")

    # 5. No raw SQL.
    for path in EIN.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 6. React screen exists and is wired as its OWN top-level section (not an accounting sub-tab).
    _assert((WEB_SRC / "api" / "einvoice.ts").is_file(), "missing src/api/einvoice.ts")
    _assert((WEB_SRC / "pages" / "einvoice" / "EInvoicesPage.tsx").is_file(),
            "missing pages/einvoice/EInvoicesPage.tsx")
    _assert((WEB_SRC / "pages" / "einvoice" / "EInvoiceNav.tsx").is_file(),
            "missing pages/einvoice/EInvoiceNav.tsx")
    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    _assert('path="/einvoice"' in app, "App.tsx missing the /einvoice route")
    sidebar = (WEB_SRC / "app" / "Sidebar.tsx").read_text(encoding="utf-8")
    _assert('to: "/einvoice"' in sidebar, "Sidebar missing the top-level e-invoicing section")
    page = (WEB_SRC / "pages" / "einvoice" / "EInvoicesPage.tsx").read_text(encoding="utf-8")
    for action in ("submitETAInvoice", "pollETAInvoice"):
        _assert(action in page, f"e-invoices screen missing {action} action")

    # 7. Real-sandbox smoke — OPT-IN, credential-gated (FILE_05). Off by default so CI (and every
    #    offline run) proves the simulated path above and stays green with no ETA credentials. Set
    #    GATE10_ETA_SANDBOX=1 on a box with real ETA pre-production credentials to also drive one live
    #    round-trip (submit → sign → poll). The command itself no-ops (exit 0) when ETA is not
    #    configured, so even with the flag set an unconfigured box cannot fail here.
    if os.environ.get("GATE10_ETA_SANDBOX"):
        smoke = subprocess.run(
            [sys.executable, "manage.py", "eta_sandbox_smoke", "--poll"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        if smoke.returncode != 0:
            raise AssertionError(
                "Real ETA sandbox smoke failed:\n" + smoke.stdout[-2000:] + "\n" + smoke.stderr[-800:]
            )
