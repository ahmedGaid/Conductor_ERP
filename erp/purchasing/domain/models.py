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
    PARTIALLY_RECEIVED = "partially_received", "Partially received"
    RECEIVED = "received", "Received"
    BILLED = "billed", "Billed"
    PAID = "paid", "Paid"
    RETURNED = "returned", "Returned"
    CANCELLED = "cancelled", "Cancelled"


class PurchaseOrder(AuditedModel):
    number = models.CharField(max_length=32, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="orders")
    order_date = models.DateField()
    warehouse_code = models.CharField(max_length=32)
    currency = models.CharField(max_length=3, default="EGP")
    status = models.CharField(max_length=24, choices=POStatus.choices, default=POStatus.DRAFT)
    # Input VAT: tax code is opt-in; blank ⇒ no VAT. tax_minor is the recoverable VAT booked at bill.
    tax_code = models.CharField(max_length=16, blank=True, default="")
    subtotal_minor = models.BigIntegerField(default=0)  # ordered value (net of tax)
    received_minor = models.BigIntegerField(default=0)  # value actually received (net)
    tax_minor = models.BigIntegerField(default=0)       # input VAT booked at bill
    billed_minor = models.BigIntegerField(default=0)    # gross billed (net + tax)
    paid_minor = models.BigIntegerField(default=0)
    returned_minor = models.BigIntegerField(default=0)
    # Amount-threshold approval gate: orders above the threshold must be approved before confirm.
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    bill_number = models.CharField(max_length=32, blank=True, default="")
    debit_note_number = models.CharField(max_length=32, blank=True, default="")
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
    returned_qty = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    unit_cost_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        db_table = "purchasing_order_line"
        ordering = ["order", "line_no"]
        unique_together = [("order", "line_no")]


class PRStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"  # awaiting approval (above threshold)
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CONVERTED = "converted", "Converted"  # turned into a purchase order
    CANCELLED = "cancelled", "Cancelled"


class PurchaseRequest(AuditedModel):
    """A purchase requisition: draft → submit → approve/reject → convert to a PurchaseOrder.

    Above an amount threshold it needs explicit approval; at/below it, submission auto-approves.
    Conversion reuses the proven purchase order lifecycle (no PO logic duplicated).
    """

    number = models.CharField(max_length=32, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="requests")
    request_date = models.DateField()
    warehouse_code = models.CharField(max_length=32)
    currency = models.CharField(max_length=3, default="EGP")
    status = models.CharField(max_length=16, choices=PRStatus.choices, default=PRStatus.DRAFT)
    subtotal_minor = models.BigIntegerField(default=0)
    approved_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_reason = models.CharField(max_length=255, blank=True, default="")
    converted_order_number = models.CharField(max_length=32, blank=True, default="")
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "purchasing_request"
        ordering = ["-request_date", "-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["supplier"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.number


class PurchaseRequestLine(models.Model):
    id = models.BigAutoField(primary_key=True)
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="lines")
    line_no = models.IntegerField()
    item_sku = models.CharField(max_length=64)
    description = models.CharField(max_length=200, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        db_table = "purchasing_request_line"
        ordering = ["request", "line_no"]
        unique_together = [("request", "line_no")]
