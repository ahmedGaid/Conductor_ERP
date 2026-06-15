"""Sales API routes."""
from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("customers", views.CustomerListCreateView.as_view(), name="customer-list"),
    path("orders", views.OrderListCreateView.as_view(), name="order-list"),
    path("orders/<uuid:order_id>", views.OrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/confirm", views.OrderConfirmView.as_view(), name="order-confirm"),
    path("orders/<uuid:order_id>/deliver", views.OrderDeliverView.as_view(), name="order-deliver"),
    path("orders/<uuid:order_id>/invoice", views.OrderInvoiceView.as_view(), name="order-invoice"),
    path("orders/<uuid:order_id>/payment", views.OrderPaymentView.as_view(), name="order-payment"),
]
