"""Gate 05 — Accounting & Finance: General Ledger core.

Asserts:
- the accounting test suite passes — the module's acceptance criteria: balanced double-entry
  posting is atomic (unbalanced writes nothing), posting respects period locks and postable
  accounts, the trial balance always balances, and the general ledger running balance is correct;
- the accounting API is mounted;
- money is integer minor units everywhere in the ledger — no float/decimal columns (the recorded
  decision), and no raw-SQL in the module's business logic;
- posting goes through an atomic transaction.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ACCT = REPO_ROOT / "erp" / "accounting"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

ACCOUNTING_TESTS = ["erp/accounting/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance test suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *ACCOUNTING_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 5 accounting tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted.
    _assert("erp.accounting.api.urls" in _read("config/urls.py"), "accounting API not mounted")

    # 3. Money is integer minor units — the ledger models must not use float/decimal columns.
    models_src = _read("erp/accounting/domain/models.py")
    for banned in ("FloatField", "DecimalField"):
        _assert(banned not in models_src, f"accounting models use {banned} (money must be integer minor units)")
    _assert("BigIntegerField" in models_src, "expected integer minor-unit amount columns")

    # 4. No raw SQL in accounting business logic (repository pattern + ORM only).
    for path in ACCT.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 5. Posting is atomic.
    posting_src = _read("erp/accounting/services/posting.py")
    _assert("transaction.atomic" in posting_src, "post_journal is not wrapped in an atomic transaction")

    # 5b. Financial statements exist, the balance sheet enforces the accounting equation, and the
    #     statement endpoints are mounted.
    stmt_src = _read("erp/accounting/services/statements.py")
    for fn in ("def income_statement", "def balance_sheet", "def cash_flow"):
        _assert(fn in stmt_src, f"statements service missing {fn}")
    _assert("is_balanced" in stmt_src, "balance sheet does not assert the accounting equation")
    wf_urls = _read("erp/accounting/api/urls.py")
    for route in ("income-statement", "balance-sheet", "cash-flow"):
        _assert(route in wf_urls, f"statement endpoint not mounted: {route}")

    # 6. The double-entry invariant point exists and rejects imbalance.
    _assert("UnbalancedEntryError" in posting_src, "posting does not enforce the balanced invariant")

    # 7. The React accounting screens exist and are wired (build/parity/CSS scans are gate03's job).
    for rel in (
        "api/accounting.ts",
        "lib/money.ts",
        "pages/accounting/ChartOfAccountsPage.tsx",
        "pages/accounting/JournalEntryPage.tsx",
        "pages/accounting/JournalListPage.tsx",
        "pages/accounting/JournalDetailPage.tsx",
        "pages/accounting/TrialBalancePage.tsx",
        "pages/accounting/GeneralLedgerPage.tsx",
        "pages/accounting/IncomeStatementPage.tsx",
        "pages/accounting/BalanceSheetPage.tsx",
        "pages/accounting/CashFlowStatementPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing accounting screen: src/{rel}")

    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    for route in (
        "/accounting",
        "/accounting/journals/new",
        "/accounting/trial-balance",
        "/accounting/income-statement",
        "/accounting/balance-sheet",
        "/accounting/cash-flow",
    ):
        _assert(route in app, f"App.tsx missing accounting route: {route}")

    # The journal entry form must post via the typed client and guard balance client-side.
    entry = (WEB_SRC / "pages" / "accounting" / "JournalEntryPage.tsx").read_text(encoding="utf-8")
    _assert("postJournal" in entry, "journal entry form does not post via the API client")
    _assert("balanced" in entry, "journal entry form does not surface a balance check")
