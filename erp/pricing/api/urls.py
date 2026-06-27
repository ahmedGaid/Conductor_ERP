"""Pricing API routes."""
from django.urls import path

from . import views

app_name = "pricing"

urlpatterns = [
    path("price-lists", views.PriceListListCreateView.as_view(), name="price-list-list"),
    path("price-lists/ensure-default", views.EnsureDefaultView.as_view(), name="price-list-ensure-default"),
    path("price-lists/<uuid:list_id>", views.PriceListDetailView.as_view(), name="price-list-detail"),
    path("price-lists/<uuid:list_id>/lines", views.PriceListLinesView.as_view(), name="price-list-lines"),
    path("lines/<uuid:line_id>", views.PriceListLineDetailView.as_view(), name="line-detail"),
    path("customer-assignments", views.CustomerAssignmentListCreateView.as_view(), name="assignment-list"),
    path("customer-assignments/<uuid:assignment_id>", views.CustomerAssignmentDetailView.as_view(), name="assignment-detail"),
    path("customer-prices", views.CustomerItemPriceListCreateView.as_view(), name="customer-price-list"),
    path("customer-prices/<uuid:price_id>", views.CustomerItemPriceDetailView.as_view(), name="customer-price-detail"),
    path("resolve", views.ResolveView.as_view(), name="resolve"),
]
