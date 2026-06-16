"""E-invoicing ORM models.

An ``ETAInvoice`` is the compliance record for a posted sales invoice: it captures the invoice's
business data (by **business key** — invoice number, customer code — never a cross-module FK) and
tracks the Egyptian Tax Authority (ETA) submission lifecycle. Money is integer minor units.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel


class ETAStatus(models.TextChoices):
    DRAFT = "draft", "Draft"            # recorded from the invoice, not yet sent
    SUBMITTED = "submitted", "Submitted"  # sent to ETA, awaiting validation
    VALID = "valid", "Valid"            # ETA accepted/validated
    REJECTED = "rejected", "Rejected"  # ETA rejected
    CANCELLED = "cancelled", "Cancelled"


class ETAInvoice(AuditedModel):
    # Business keys into the source sales invoice — no FK crosses the module boundary.
    invoice_number = models.CharField(max_length=32, unique=True)
    order_number = models.CharField(max_length=32, blank=True, default="")
    customer_code = models.CharField(max_length=32, blank=True, default="")
    customer_name = models.CharField(max_length=200, blank=True, default="")
    issue_date = models.DateField()
    currency = models.CharField(max_length=3, default="EGP")
    tax_code = models.CharField(max_length=16, blank=True, default="")
    net_minor = models.BigIntegerField(default=0)
    tax_minor = models.BigIntegerField(default=0)
    total_minor = models.BigIntegerField(default=0)
    # ETA submission lifecycle.
    status = models.CharField(max_length=16, choices=ETAStatus.choices, default=ETAStatus.DRAFT)
    uuid = models.CharField(max_length=64, blank=True, default="")        # assigned by ETA on submit
    document_hash = models.CharField(max_length=64, blank=True, default="")  # sha256 of the document
    submitted_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    error_text = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "einvoice_eta_invoice"
        ordering = ["-issue_date", "-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["customer_code"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"ETA[{self.invoice_number}]"
