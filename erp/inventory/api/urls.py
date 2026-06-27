"""Inventory API routes."""
from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("items", views.ItemListCreateView.as_view(), name="item-list"),
    path("items/import", views.ItemImportView.as_view(), name="item-import"),
    path("items/import/template", views.ItemImportTemplateView.as_view(), name="item-import-template"),
    path("categories", views.CategoryListCreateView.as_view(), name="category-list"),
    path("warehouses", views.WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("movements", views.MovementListView.as_view(), name="movement-list"),
    path("movements/receive", views.ReceiveView.as_view(), name="movement-receive"),
    path("movements/issue", views.IssueView.as_view(), name="movement-issue"),
    path("movements/transfer", views.TransferView.as_view(), name="movement-transfer"),
    path("reports/stock-on-hand", views.StockOnHandView.as_view(), name="stock-on-hand"),
    path("reports/batches", views.BatchesView.as_view(), name="batches"),
    path("counts", views.StockCountListCreateView.as_view(), name="count-list"),
    path("counts/<uuid:count_id>", views.StockCountDetailView.as_view(), name="count-detail"),
    path("counts/<uuid:count_id>/post", views.StockCountPostView.as_view(), name="count-post"),
    path("count-lines/<uuid:line_id>/set", views.StockCountLineSetView.as_view(), name="count-line-set"),
]
