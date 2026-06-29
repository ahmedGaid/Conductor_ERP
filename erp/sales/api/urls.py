"""Sales API routes."""
from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("customers", views.CustomerListCreateView.as_view(), name="customer-list"),
    path("customers/import", views.CustomerImportView.as_view(), name="customer-import"),
    path(
        "customers/import/template",
        views.CustomerImportTemplateView.as_view(),
        name="customer-import-template",
    ),
    path("orders", views.OrderListCreateView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>", views.OrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/history", views.OrderHistoryView.as_view(), name="order-history"),
    path("orders/<uuid:order_id>/approve", views.OrderApproveView.as_view(), name="order-approve"),
    path("orders/<uuid:order_id>/confirm", views.OrderConfirmView.as_view(), name="order-confirm"),
    path("orders/<uuid:order_id>/deliver", views.OrderDeliverView.as_view(), name="order-deliver"),
    path("orders/<uuid:order_id>/invoice", views.OrderInvoiceView.as_view(), name="order-invoice"),
    path("orders/<uuid:order_id>/return", views.OrderReturnView.as_view(), name="order-return"),
    path("orders/<uuid:order_id>/cancel", views.OrderCancelView.as_view(), name="order-cancel"),
    path("orders/<uuid:order_id>/complete", views.OrderCompleteView.as_view(), name="order-complete"),
    path("orders/<uuid:order_id>/payment", views.OrderPaymentView.as_view(), name="order-payment"),
    path("quotations", views.QuotationListCreateView.as_view(), name="quotation-list"),
    path("quotations/<uuid:quote_id>", views.QuotationDetailView.as_view(), name="quotation-detail"),
    path("quotations/<uuid:quote_id>/submit", views.QuotationSubmitView.as_view(), name="quotation-submit"),
    path("quotations/<uuid:quote_id>/approve", views.QuotationApproveView.as_view(), name="quotation-approve"),
    path("quotations/<uuid:quote_id>/reject", views.QuotationRejectView.as_view(), name="quotation-reject"),
    path("quotations/<uuid:quote_id>/convert", views.QuotationConvertView.as_view(), name="quotation-convert"),
]
