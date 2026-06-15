"""Gate 07 — Sales & Customers (order-to-cash, cross-module).

Asserts:
- the sales test suite passes — full draft→paid flow keeps the trial balance balanced, delivery
  reduces stock and keeps Inventory GL == stock value, credit limit + oversell + overpayment guards;
- the sales API is mounted;
- module boundary: sales talks to other modules ONLY through their contracts — it imports
  `erp.accounting.contracts` + `erp.inventory.contracts`, never their domain/models/services;
- money is integer minor units; transitions are atomic;
- the React sales screens exist and are wired.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SALES = REPO_ROOT / "erp" / "sales"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

SALES_TESTS = ["erp/sales/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *SALES_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 5d sales tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted.
    _assert("erp.sales.api.urls" in _read("config/urls.py"), "sales API not mounted")

    # 3. Module boundary: sales uses ONLY the public contracts of accounting + inventory.
    orders_src = _read("erp/sales/services/orders.py")
    _assert("from erp.accounting.contracts import" in orders_src, "sales must use accounting.contracts")
    _assert("from erp.inventory import contracts" in orders_src or
            "from erp.inventory.contracts import" in orders_src, "sales must use inventory.contracts")
    for forbidden in (
        "erp.accounting.domain", "erp.accounting.models", "erp.accounting.services",
        "erp.inventory.domain", "erp.inventory.models", "erp.inventory.services",
    ):
        _assert(forbidden not in orders_src, f"sales reaches past a contract into {forbidden}")
    _assert("transaction.atomic" in orders_src, "sales transitions are not atomic")
    _assert("CreditLimitExceededError" in orders_src, "credit limit is not enforced")

    # 4. Money is integer minor units (no float columns).
    models_src = _read("erp/sales/domain/models.py")
    _assert("FloatField" not in models_src, "sales must not use FloatField for money")
    _assert("BigIntegerField" in models_src, "money columns must be integer minor units")

    # 5. No raw SQL.
    for path in SALES.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 6. React sales screens exist and are wired.
    for rel in (
        "api/sales.ts",
        "pages/sales/CustomersPage.tsx",
        "pages/sales/OrdersPage.tsx",
        "pages/sales/OrderDetailPage.tsx",
        "pages/sales/NewOrderPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing sales screen: src/{rel}")

    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    for route in ("/sales", "/sales/orders/new", "/sales/orders/:id"):
        _assert(route in app, f"App.tsx missing sales route: {route}")

    detail = (WEB_SRC / "pages" / "sales" / "OrderDetailPage.tsx").read_text(encoding="utf-8")
    for action in ("confirm", "deliver", "invoice"):
        _assert(action in detail, f"order detail missing {action} action")
