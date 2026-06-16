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
    # Depth: partial delivery + customer returns (credit note) via the inventory contract.
    _assert("def return_order" in orders_src, "sales must support returns (return_order)")
    _assert("inventory.return_in" in orders_src, "sales return must put stock back via the contract")
    _assert("delivered" in orders_src and "PARTIALLY_DELIVERED" in orders_src,
            "sales must support partial delivery")
    # Quotation front-end: submit/approve threshold + convert reuses the order service.
    quotes_src = _read("erp/sales/services/quotations.py")
    for fn in ("def submit_quotation", "def approve_quotation", "def convert_quotation"):
        _assert(fn in quotes_src, f"sales quotation service missing {fn}")
    _assert("create_order" in quotes_src, "quotation convert must reuse the order service")
    # Line discounts + the amount-threshold approval gate at confirm.
    _assert("discount_minor" in orders_src, "sales must support line discounts")
    _assert("def approve_order" in orders_src and "ApprovalRequiredError" in orders_src,
            "sales must enforce the order approval gate")
    # VAT on invoices via the accounting tax contract (not its ORM/services).
    _assert("compute_tax" in orders_src and "find_tax_code" in orders_src,
            "sales must apply VAT via the accounting tax contract")

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
        "pages/sales/QuotationsPage.tsx",
        "pages/sales/NewQuotationPage.tsx",
        "pages/sales/QuotationDetailPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing sales screen: src/{rel}")

    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    for route in ("/sales", "/sales/orders/new", "/sales/orders/:id",
                  "/sales/quotations", "/sales/quotations/:id"):
        _assert(route in app, f"App.tsx missing sales route: {route}")

    quote_detail = (WEB_SRC / "pages" / "sales" / "QuotationDetailPage.tsx").read_text(encoding="utf-8")
    for action in ("submitQuotation", "approveQuotation", "convertQuotation"):
        _assert(action in quote_detail, f"quotation detail missing {action} action")

    detail = (WEB_SRC / "pages" / "sales" / "OrderDetailPage.tsx").read_text(encoding="utf-8")
    for action in ("confirm", "deliver", "invoice", "returnOrder", "approveOrder"):
        _assert(action in detail, f"order detail missing {action} action")
