"""Sales ORM models.

Sales owns Customer and the Sales Order. It references items by **SKU string** (not a FK into the
inventory module) and posts to the GL via the accounting contract — keeping module boundaries clean.
Money is integer minor units; quantities are Decimal.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel


class Customer(AuditedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    # Credit limit in minor units; 0 means unlimited.
    credit_limit_minor = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sales_customer"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    CONFIRMED = "confirmed", "Confirmed"
    DELIVERED = "delivered", "Delivered"
    INVOICED = "invoiced", "Invoiced"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


class SalesOrder(AuditedModel):
    number = models.CharField(max_length=32, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    order_date = models.DateField()
    # Warehouse to deliver from — referenced by code (inventory module owns warehouses).
    warehouse_code = models.CharField(max_length=32)
    currency = models.CharField(max_length=3, default="EGP")
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    subtotal_minor = models.BigIntegerField(default=0)
    invoiced_minor = models.BigIntegerField(default=0)
    paid_minor = models.BigIntegerField(default=0)
    invoice_number = models.CharField(max_length=32, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "sales_order"
        ordering = ["-order_date", "-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["customer"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.number

    @property
    def outstanding_minor(self) -> int:
        return self.invoiced_minor - self.paid_minor


class SalesOrderLine(models.Model):
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")
    line_no = models.IntegerField()
    item_sku = models.CharField(max_length=64)  # business key into inventory
    description = models.CharField(max_length=200, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_price_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        db_table = "sales_order_line"
        ordering = ["order", "line_no"]
        unique_together = [("order", "line_no")]
