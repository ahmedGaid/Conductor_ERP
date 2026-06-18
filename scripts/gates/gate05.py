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
    for route in ("income-statement", "balance-sheet", "cash-flow", "vat-return", "tax-codes"):
        _assert(route in wf_urls, f"statement endpoint not mounted: {route}")

    # 5c. Tax (VAT): a tax service computes tax and a VAT return nets output VAT against
    #     recoverable input (purchase) VAT.
    taxes_src = _read("erp/accounting/services/taxes.py")
    _assert("def compute_tax" in taxes_src, "tax service missing compute_tax")
    _assert("input_account_code" in taxes_src, "tax code must expose the input (recoverable) VAT account")
    reports_src = _read("erp/accounting/services/reports.py")
    _assert("def vat_return" in reports_src, "reports missing vat_return")
    _assert("input_vat" in reports_src, "vat_return must net output VAT against input (purchase) VAT")

    # 5d. Report exports: a shared CSV/XLSX renderer + the report endpoints serve downloads via
    #     the ?export= param (note: not ?format=, which DRF reserves), and the React export toolbar
    #     is wired on a report screen. (PDF is the browser's print-to-PDF — see styles/print.css.)
    exports_src = _read("erp/core/exports.py")
    for fn in ("def to_csv", "def to_xlsx", "def export_response"):
        _assert(fn in exports_src, f"core exports missing {fn}")
    views_src = _read("erp/accounting/api/views.py")
    _assert('request.query_params.get("export")' in views_src,
            "report views must serve downloads via the ?export= param")
    _assert((WEB_SRC / "components" / "ExportButtons.tsx").is_file(), "missing components/ExportButtons.tsx")
    _assert((WEB_SRC / "styles" / "print.css").is_file(), "missing styles/print.css (print-to-PDF)")
    _assert("ExportButtons" in _read("apps/web/src/pages/accounting/TrialBalancePage.tsx"),
            "trial balance screen missing the export toolbar")

    # 5e. Fixed assets: the sub-ledger service posts acquisition/depreciation/disposal through
    #     post_journal, the endpoints are mounted, and the React screens are wired.
    assets_src = _read("erp/accounting/services/assets.py")
    for fn in ("def acquire_asset", "def run_depreciation", "def dispose_asset", "def asset_register"):
        _assert(fn in assets_src, f"assets service missing {fn}")
    _assert("post_journal" in assets_src, "assets must post to the GL via post_journal")
    for route in ("assets", "assets/depreciation-run", "reports/asset-register"):
        _assert(route in wf_urls, f"fixed-asset endpoint not mounted: {route}")
    for rel in ("pages/accounting/FixedAssetsPage.tsx", "pages/accounting/FixedAssetDetailPage.tsx"):
        _assert((WEB_SRC / rel).is_file(), f"missing fixed-asset screen: src/{rel}")
    _assert("/accounting/assets" in _read("apps/web/src/App.tsx"), "App.tsx missing the fixed-assets route")

    # 5f. Cost centers: an optional reporting dimension on journal lines, the income statement can be
    #     filtered by it, the master endpoint is mounted, and the React screen is wired.
    _assert("class CostCenter" in models_src, "missing CostCenter model")
    _assert("cost_center_code" in models_src, "JournalLine missing the cost_center_code dimension")
    _assert("cost_center" in stmt_src, "income_statement cannot filter by cost center")
    _assert("cost-centers" in wf_urls, "cost-centers endpoint not mounted")
    _assert((WEB_SRC / "pages" / "accounting" / "CostCentersPage.tsx").is_file(),
            "missing cost-center screen: src/pages/accounting/CostCentersPage.tsx")
    _assert("/accounting/cost-centers" in _read("apps/web/src/App.tsx"),
            "App.tsx missing the cost-centers route")

    # 5g. Bank reconciliation: the service matches statement lines to the cash GL and books bank-only
    #     items via post_journal; the endpoints are mounted and the React screens are wired.
    bank_src = _read("erp/accounting/services/bank_rec.py")
    for fn in ("def create_statement", "def auto_match", "def post_adjustment",
               "def reconciliation", "def mark_reconciled"):
        _assert(fn in bank_src, f"bank_rec service missing {fn}")
    _assert("post_journal" in bank_src, "bank adjustments must post to the GL via post_journal")
    for route in ("bank-statements", "auto-match", "adjustment", "reconcile"):
        _assert(route in wf_urls, f"bank-rec endpoint not mounted: {route}")
    for rel in ("pages/accounting/BankReconciliationPage.tsx", "pages/accounting/BankStatementDetailPage.tsx"):
        _assert((WEB_SRC / rel).is_file(), f"missing bank-rec screen: src/{rel}")
    _assert("/accounting/bank-reconciliation" in _read("apps/web/src/App.tsx"),
            "App.tsx missing the bank-reconciliation route")

    # 5h. Budgets: the service computes budget-vs-actual from the posted GL (variance = actual −
    #     budget), the endpoints are mounted, and the React screens are wired.
    budgets_src = _read("erp/accounting/services/budgets.py")
    for fn in ("def create_budget", "def set_budget_line", "def budget_vs_actual"):
        _assert(fn in budgets_src, f"budgets service missing {fn}")
    _assert("variance_minor" in budgets_src, "budget report missing the variance figure")
    for route in ("budgets", "variance"):
        _assert(route in wf_urls, f"budget endpoint not mounted: {route}")
    for rel in ("pages/accounting/BudgetsPage.tsx", "pages/accounting/BudgetDetailPage.tsx"):
        _assert((WEB_SRC / rel).is_file(), f"missing budget screen: src/{rel}")
    _assert("/accounting/budgets" in _read("apps/web/src/App.tsx"), "App.tsx missing the budgets route")

    # 5i. Custom report builder + scheduled reports: a saved definition runs over the GL and exports;
    #     the scheduler is a Celery task registered on the beat schedule.
    rb_src = _read("erp/accounting/services/report_builder.py")
    for fn in ("def run_definition", "def run_scheduled", "def is_due"):
        _assert(fn in rb_src, f"report_builder missing {fn}")
    for route in ("report-definitions", "/run"):
        _assert(route in wf_urls, f"report-builder endpoint not mounted: {route}")
    tasks_src = _read("erp/accounting/tasks.py")
    _assert("run_scheduled_reports" in tasks_src, "missing the scheduled-reports Celery task")
    settings_src = _read("config/settings/base.py")
    _assert("CELERY_BEAT_SCHEDULE" in settings_src and "accounting.run_scheduled_reports" in settings_src,
            "scheduled-reports task is not registered on the Celery beat schedule")
    _assert((WEB_SRC / "pages" / "accounting" / "ReportBuilderPage.tsx").is_file(),
            "missing report-builder screen: src/pages/accounting/ReportBuilderPage.tsx")
    _assert("/accounting/report-builder" in _read("apps/web/src/App.tsx"),
            "App.tsx missing the report-builder route")

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
        "pages/accounting/VatReturnPage.tsx",
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
        "/accounting/vat-return",
    ):
        _assert(route in app, f"App.tsx missing accounting route: {route}")

    # The journal entry form must post via the typed client and guard balance client-side.
    entry = (WEB_SRC / "pages" / "accounting" / "JournalEntryPage.tsx").read_text(encoding="utf-8")
    _assert("postJournal" in entry, "journal entry form does not post via the API client")
    _assert("balanced" in entry, "journal entry form does not surface a balance check")
