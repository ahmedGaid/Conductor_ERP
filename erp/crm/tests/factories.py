"""Test helpers for CRM: a sales customer + an inventory item so the won → sales-order flow runs."""
from __future__ import annotations

from erp.inventory.domain.models import Item
from erp.sales.domain.models import Customer


def make_customer(code: str = "CUST1", name: str = "Initech") -> Customer:
    return Customer.objects.create(code=code, name=name)


def make_item(sku: str = "WIDGET") -> Item:
    return Item.objects.create(sku=sku, name="Widget", type="stock")
