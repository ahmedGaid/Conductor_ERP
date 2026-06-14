"""Inventory API routes."""
from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("items", views.ItemListCreateView.as_view(), name="item-list"),
    path("categories", views.CategoryListCreateView.as_view(), name="category-list"),
    path("warehouses", views.WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("movements", views.MovementListView.as_view(), name="movement-list"),
    path("movements/receive", views.ReceiveView.as_view(), name="movement-receive"),
    path("movements/issue", views.IssueView.as_view(), name="movement-issue"),
    path("movements/transfer", views.TransferView.as_view(), name="movement-transfer"),
    path("reports/stock-on-hand", views.StockOnHandView.as_view(), name="stock-on-hand"),
]
