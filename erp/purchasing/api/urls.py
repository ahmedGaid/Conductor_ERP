"""Purchasing API routes."""
from django.urls import path

from . import views

app_name = "purchasing"

urlpatterns = [
    path("suppliers", views.SupplierListCreateView.as_view(), name="supplier-list"),
    path("suppliers/import", views.SupplierImportView.as_view(), name="supplier-import"),
    path(
        "suppliers/import/template",
        views.SupplierImportTemplateView.as_view(),
        name="supplier-import-template",
    ),
    path("orders", views.POListCreateView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>", views.PODetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/history", views.POHistoryView.as_view(), name="order-history"),
    path("orders/<uuid:order_id>/approve", views.POApproveView.as_view(), name="order-approve"),
    path("orders/<uuid:order_id>/confirm", views.POConfirmView.as_view(), name="order-confirm"),
    path("orders/<uuid:order_id>/receive", views.POReceiveView.as_view(), name="order-receive"),
    path("orders/<uuid:order_id>/bill", views.POBillView.as_view(), name="order-bill"),
    path("orders/<uuid:order_id>/return", views.POReturnView.as_view(), name="order-return"),
    path("orders/<uuid:order_id>/cancel", views.POCancelView.as_view(), name="order-cancel"),
    path("orders/<uuid:order_id>/payment", views.POPaymentView.as_view(), name="order-payment"),
    path("requests", views.RequestListCreateView.as_view(), name="request-list"),
    path("requests/<uuid:req_id>", views.RequestDetailView.as_view(), name="request-detail"),
    path("requests/<uuid:req_id>/submit", views.RequestSubmitView.as_view(), name="request-submit"),
    path("requests/<uuid:req_id>/approve", views.RequestApproveView.as_view(), name="request-approve"),
    path("requests/<uuid:req_id>/reject", views.RequestRejectView.as_view(), name="request-reject"),
    path("requests/<uuid:req_id>/convert", views.RequestConvertView.as_view(), name="request-convert"),
]
