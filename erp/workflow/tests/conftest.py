"""Shared fixtures for erp/workflow tests."""
from __future__ import annotations

import pytest

from erp.inventory.domain.models import Item, StockBalance, Warehouse


@pytest.fixture
def item_below_reorder_point(db) -> Item:
    item = Item.objects.create(sku="LOW-ITEM", name="Low Stock Widget", type="stock", reorder_point=10)
    warehouse = Warehouse.objects.create(code="MAIN", name="Main Warehouse")
    StockBalance.objects.create(item=item, warehouse=warehouse, quantity=2)
    return item
