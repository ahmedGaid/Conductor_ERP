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
]
