"""Purchasing ORM models.

Mirrors Sales: Supplier + PurchaseOrder. Items referenced by SKU string, warehouse by code (no
cross-module FKs). Money is integer minor units; quantities Decimal. Lines track ordered vs received
quantity to drive the 3-way match before billing.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel


class Supplier(AuditedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "purchasing_supplier"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class POStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"
    RECEIVED = "received", "Received"
    BILLED = "billed", "Billed"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


class PurchaseOrder(AuditedModel):
    number = models.CharField(max_length=32, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="orders")
    order_date = models.DateField()
    warehouse_code = models.CharField(max_length=32)
    currency = models.CharField(max_length=3, default="EGP")
    status = models.CharField(max_length=16, choices=POStatus.choices, default=POStatus.DRAFT)
    subtotal_minor = models.BigIntegerField(default=0)  # ordered value
    received_minor = models.BigIntegerField(default=0)  # value actually received
    billed_minor = models.BigIntegerField(default=0)
    paid_minor = models.BigIntegerField(default=0)
    bill_number = models.CharField(max_length=32, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "purchasing_order"
        ordering = ["-order_date", "-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["supplier"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.number

    @property
    def outstanding_minor(self) -> int:
        return self.billed_minor - self.paid_minor


class PurchaseOrderLine(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="lines")
    line_no = models.IntegerField()
    item_sku = models.CharField(max_length=64)
    description = models.CharField(max_length=200, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)  # ordered
    received_qty = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    unit_cost_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        db_table = "purchasing_order_line"
        ordering = ["order", "line_no"]
        unique_together = [("order", "line_no")]
