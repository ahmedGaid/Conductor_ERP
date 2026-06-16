"""Accounting API routes."""
from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    path("accounts", views.AccountListCreateView.as_view(), name="account-list"),
    path("fiscal-years", views.FiscalYearListCreateView.as_view(), name="fiscal-year-list"),
    path("periods", views.PeriodListCreateView.as_view(), name="period-list"),
    path("periods/<str:code>/close", views.PeriodCloseView.as_view(), name="period-close"),
    path("journals", views.JournalListPostView.as_view(), name="journal-list"),
    path("journals/<uuid:entry_id>", views.JournalDetailView.as_view(), name="journal-detail"),
    path("reports/trial-balance", views.TrialBalanceView.as_view(), name="trial-balance"),
    path("reports/general-ledger", views.GeneralLedgerView.as_view(), name="general-ledger"),
    path("reports/income-statement", views.IncomeStatementView.as_view(), name="income-statement"),
    path("reports/balance-sheet", views.BalanceSheetView.as_view(), name="balance-sheet"),
    path("reports/cash-flow", views.CashFlowView.as_view(), name="cash-flow"),
    path("reports/vat-return", views.VatReturnView.as_view(), name="vat-return"),
    path("reports/asset-register", views.AssetRegisterView.as_view(), name="asset-register"),
    path("tax-codes", views.TaxCodeListView.as_view(), name="tax-code-list"),
    path("cost-centers", views.CostCenterListCreateView.as_view(), name="cost-center-list"),
    path("bank-statements", views.BankStatementListCreateView.as_view(), name="bank-statement-list"),
    path("bank-statements/<uuid:statement_id>", views.BankStatementDetailView.as_view(), name="bank-statement-detail"),
    path("bank-statements/<uuid:statement_id>/auto-match", views.BankStatementAutoMatchView.as_view(), name="bank-statement-auto-match"),
    path("bank-statements/<uuid:statement_id>/adjustment", views.BankStatementAdjustmentView.as_view(), name="bank-statement-adjustment"),
    path("bank-statements/<uuid:statement_id>/reconcile", views.BankStatementReconcileView.as_view(), name="bank-statement-reconcile"),
    path("bank-statements/<uuid:statement_id>/candidates", views.BankStatementCandidatesView.as_view(), name="bank-statement-candidates"),
    path("bank-statement-lines/<uuid:line_id>/match", views.BankLineMatchView.as_view(), name="bank-line-match"),
    path("assets", views.FixedAssetListCreateView.as_view(), name="asset-list"),
    path("assets/depreciation-run", views.DepreciationRunView.as_view(), name="depreciation-run"),
    path("assets/<str:code>", views.FixedAssetDetailView.as_view(), name="asset-detail"),
    path("assets/<str:code>/dispose", views.FixedAssetDisposeView.as_view(), name="asset-dispose"),
]
