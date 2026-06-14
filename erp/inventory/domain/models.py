"""Inventory ORM models.

Quantities are exact `Decimal` (items may be fractional, e.g. kg); monetary value is integer
**minor units** (same convention as accounting). A `StockBalance` holds the running on-hand quantity
and total value per item+warehouse; weighted-average unit cost is derived as value / quantity.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel, TimeStampedModel


class ItemType(models.TextChoices):
    STOCK = "stock", "Stock"
    SERVICE = "service", "Service"


class MovementType(models.TextChoices):
    RECEIPT = "receipt", "Receipt"
    ISSUE = "issue", "Issue"
    TRANSFER = "transfer", "Transfer"


class Category(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )

    class Meta:
        db_table = "inventory_category"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class Item(AuditedModel):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="items"
    )
    uom = models.CharField(max_length=16, default="unit")  # unit of measure
    type = models.CharField(max_length=16, choices=ItemType.choices, default=ItemType.STOCK)
    is_active = models.BooleanField(default=True)
    reorder_point = models.DecimalField(max_digits=18, decimal_places=4, default=0)

    class Meta:
        db_table = "inventory_item"
        ordering = ["sku"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.sku} — {self.name}"


class Warehouse(AuditedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "inventory_warehouse"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class StockBalance(models.Model):
    """Running on-hand quantity and total value per item+warehouse (weighted average)."""

    id = models.BigAutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="balances")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="balances")
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    value_minor = models.BigIntegerField(default=0)  # total value, minor units

    class Meta:
        db_table = "inventory_stock_balance"
        unique_together = [("item", "warehouse")]
        indexes = [models.Index(fields=["item"]), models.Index(fields=["warehouse"])]


class StockMovement(AuditedModel):
    """An immutable stock event. Receipts carry a unit cost; issues value at weighted average."""

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    # For transfers: the destination warehouse.
    dest_warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    type = models.CharField(max_length=16, choices=MovementType.choices)
    date = models.DateField()
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = models.BigIntegerField(default=0)  # receipts only
    value_minor = models.BigIntegerField(default=0)  # cost moved by this event
    reference = models.CharField(max_length=128, blank=True, default="")
    memo = models.CharField(max_length=255, blank=True, default="")
    # The GL journal this movement posted (entry number), if any.
    journal_number = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "inventory_stock_movement"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["item"]), models.Index(fields=["type"])]
