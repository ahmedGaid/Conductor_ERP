"""Gate 06 — Inventory & Warehouses (stock control + GL integration).

Asserts:
- the inventory test suite passes — weighted-average costing, balance updates, the oversell guard,
  and the cross-module invariant that the **Inventory GL account balance equals total stock value**;
- the inventory API is mounted;
- inventory posts to the ledger ONLY through the accounting public contract (module boundary):
  services import `erp.accounting.contracts`, never accounting's ORM (`domain`/`models`);
- monetary value is integer minor units (no float columns); stock ops are atomic;
- the React inventory screens exist and are wired.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INV = REPO_ROOT / "erp" / "inventory"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

INVENTORY_TESTS = ["erp/inventory/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *INVENTORY_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 5c inventory tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted.
    _assert("erp.inventory.api.urls" in _read("config/urls.py"), "inventory API not mounted")

    # 3. Module boundary: inventory posts to GL via the accounting CONTRACT only.
    stock_src = _read("erp/inventory/services/stock.py")
    _assert(
        "from erp.accounting.contracts import" in stock_src,
        "inventory must post to the GL via erp.accounting.contracts",
    )
    for forbidden in ("erp.accounting.domain", "erp.accounting.models", "erp.accounting.services"):
        _assert(
            forbidden not in stock_src,
            f"inventory reaches past the accounting contract into {forbidden}",
        )
    _assert("transaction.atomic" in stock_src, "stock operations are not atomic")

    # 4. Money is integer minor units (quantities may be Decimal; value must not be float).
    models_src = _read("erp/inventory/domain/models.py")
    _assert("FloatField" not in models_src, "inventory must not use FloatField for money")
    _assert("value_minor" in models_src and "BigIntegerField" in models_src,
            "stock value must be an integer minor-unit column")

    # 5. No raw SQL in business logic.
    for path in INV.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 6. React inventory screens exist and are wired.
    for rel in (
        "api/inventory.ts",
        "pages/inventory/ItemsPage.tsx",
        "pages/inventory/WarehousesPage.tsx",
        "pages/inventory/StockMovementPage.tsx",
        "pages/inventory/StockOnHandPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing inventory screen: src/{rel}")

    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    for route in ("/inventory", "/inventory/movements", "/inventory/stock-on-hand"):
        _assert(route in app, f"App.tsx missing inventory route: {route}")

    movement = (WEB_SRC / "pages" / "inventory" / "StockMovementPage.tsx").read_text(encoding="utf-8")
    _assert("receiveStock" in movement or "receive" in movement, "movement screen missing receive action")
