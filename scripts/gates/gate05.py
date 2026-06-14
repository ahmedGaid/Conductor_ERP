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

    # 6. The double-entry invariant point exists and rejects imbalance.
    _assert("UnbalancedEntryError" in posting_src, "posting does not enforce the balanced invariant")
