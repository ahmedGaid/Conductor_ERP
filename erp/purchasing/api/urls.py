"""Purchasing API routes."""
from django.urls import path

from . import views

app_name = "purchasing"

urlpatterns = [
    path("suppliers", views.SupplierListCreateView.as_view(), name="supplier-list"),
    path("orders", views.POListCreateView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>", views.PODetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/confirm", views.POConfirmView.as_view(), name="order-confirm"),
    path("orders/<uuid:order_id>/receive", views.POReceiveView.as_view(), name="order-receive"),
    path("orders/<uuid:order_id>/bill", views.POBillView.as_view(), name="order-bill"),
    path("orders/<uuid:order_id>/payment", views.POPaymentView.as_view(), name="order-payment"),
]
