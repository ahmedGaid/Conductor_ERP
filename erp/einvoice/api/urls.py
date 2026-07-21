"""E-invoicing API routes."""
from django.urls import path

from . import views

app_name = "einvoice"

urlpatterns = [
    path("config", views.ETAConfigView.as_view(), name="config"),
    path("config/test", views.ETAConfigTestView.as_view(), name="config-test"),
    path("invoices", views.ETAInvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<uuid:eta_id>", views.ETAInvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<uuid:eta_id>/submit", views.ETAInvoiceSubmitView.as_view(), name="invoice-submit"),
    path("invoices/<uuid:eta_id>/poll", views.ETAInvoicePollView.as_view(), name="invoice-poll"),
]
