"""Gate 08 — Purchasing & Suppliers (procure-to-pay, cross-module).

Asserts:
- the purchasing test suite passes — full draft→paid flow leaves the trial balance balanced and
  **GRNI back at zero**, receipt keeps Inventory GL == stock value, the **3-way match** blocks
  billing on a partial receipt, and over-payment is rejected;
- the purchasing API is mounted;
- module boundary: purchasing uses ONLY the accounting + inventory public contracts;
- money is integer minor units; transitions are atomic; the 3-way match is enforced;
- the React purchasing screens exist and are wired.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUR = REPO_ROOT / "erp" / "purchasing"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

PURCHASING_TESTS = ["erp/purchasing/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *PURCHASING_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 5e purchasing tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted.
    _assert("erp.purchasing.api.urls" in _read("config/urls.py"), "purchasing API not mounted")

    # 3. Module boundary: purchasing uses ONLY the public contracts of accounting + inventory.
    orders_src = _read("erp/purchasing/services/orders.py")
    _assert("from erp.accounting.contracts import" in orders_src, "purchasing must use accounting.contracts")
    _assert("from erp.inventory import contracts" in orders_src or
            "from erp.inventory.contracts import" in orders_src, "purchasing must use inventory.contracts")
    for forbidden in (
        "erp.accounting.domain", "erp.accounting.models", "erp.accounting.services",
        "erp.inventory.domain", "erp.inventory.models", "erp.inventory.services",
    ):
        _assert(forbidden not in orders_src, f"purchasing reaches past a contract into {forbidden}")
    _assert("transaction.atomic" in orders_src, "purchasing transitions are not atomic")
    _assert("ThreeWayMatchError" in orders_src, "3-way match is not enforced")

    # 4. Money is integer minor units (no float columns).
    models_src = _read("erp/purchasing/domain/models.py")
    _assert("FloatField" not in models_src, "purchasing must not use FloatField for money")
    _assert("BigIntegerField" in models_src, "money columns must be integer minor units")

    # 5. No raw SQL.
    for path in PUR.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 6. React purchasing screens exist and are wired.
    for rel in (
        "api/purchasing.ts",
        "pages/purchasing/SuppliersPage.tsx",
        "pages/purchasing/PurchaseOrdersPage.tsx",
        "pages/purchasing/PurchaseOrderDetailPage.tsx",
        "pages/purchasing/NewPurchaseOrderPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing purchasing screen: src/{rel}")

    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    for route in ("/purchasing", "/purchasing/orders/new", "/purchasing/orders/:id"):
        _assert(route in app, f"App.tsx missing purchasing route: {route}")

    detail = (WEB_SRC / "pages" / "purchasing" / "PurchaseOrderDetailPage.tsx").read_text(encoding="utf-8")
    for action in ("confirm", "receive", "bill"):
        _assert(action in detail, f"PO detail missing {action} action")
