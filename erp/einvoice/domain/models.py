"""E-invoicing ORM models.

An ``ETAInvoice`` is the compliance record for a posted sales invoice: it captures the invoice's
business data (by **business key** — invoice number, customer code — never a cross-module FK) and
tracks the Egyptian Tax Authority (ETA) submission lifecycle. Money is integer minor units.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel, TimeStampedModel


class ETAEnvironment(models.TextChoices):
    SANDBOX = "sandbox", "Pre-production"   # ETA's preprod/sandbox — safe to submit test invoices
    PRODUCTION = "production", "Production"  # live Tax Authority — real invoices


class ETASettings(TimeStampedModel):
    """Singleton ETA connection configuration, editable in-app by a System Admin.

    This is the admin-config pivot (2026-07-21): every ETA connection value that used to live in
    ``.env`` now lives here so an admin can enter, test, and switch it from the settings screen —
    no server access, no restart. The one exception is the **client secret**, which is stored
    *encrypted* (:mod:`erp.einvoice.services.secrets`) and never leaves the server in clear text.

    Env settings remain a valid fallback: if this row is not ``enabled`` the resolver
    (:mod:`erp.einvoice.services.config`) drops back to ``settings.ETA_*``. That keeps existing
    env-configured installs working and lets ops pre-seed credentials without a UI.

    Singleton: there is one tax profile per install, so the row is pinned to ``pk`` fixed by
    :meth:`load`. ``enabled`` gates whether the app talks to ETA at all — off keeps it on the
    simulated adapter, exactly as an unconfigured install behaves today.
    """

    environment = models.CharField(max_length=16, choices=ETAEnvironment.choices, blank=True, default="")
    identity_url = models.CharField(max_length=255, blank=True, default="")   # OAuth2 issuer (https)
    api_base_url = models.CharField(max_length=255, blank=True, default="")   # document API base (https)
    client_id = models.CharField(max_length=128, blank=True, default="")
    rin = models.CharField(max_length=32, blank=True, default="")             # taxpayer registration number
    # Fernet ciphertext of the client secret — never plaintext, never serialized to a client.
    client_secret_encrypted = models.TextField(blank=True, default="")
    # Master switch: off = stay on the simulated adapter / env fallback, never call ETA with this row.
    enabled = models.BooleanField(default=False)
    # When admin last proved these credentials authenticate against ETA (Test connection succeeded).
    last_test_ok_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "einvoice_eta_settings"
        verbose_name = "ETA settings"
        verbose_name_plural = "ETA settings"

    def __str__(self) -> str:  # pragma: no cover
        return f"ETASettings[{self.environment or 'unconfigured'}]"

    @classmethod
    def load(cls) -> "ETASettings":
        """Return the one settings row, creating it empty on first access."""
        obj, _ = cls.objects.get_or_create(pk=cls._SINGLETON_PK)
        return obj

    # A fixed pk so the row is a true singleton (get_or_create can never make a second).
    _SINGLETON_PK = "00000000-0000-0000-0000-000000000001"

    def set_secret(self, raw: str) -> None:
        """Encrypt and store a new client secret (does not save)."""
        from erp.einvoice.services import secrets

        self.client_secret_encrypted = secrets.encrypt(raw)

    def get_secret(self) -> str:
        """Decrypt the stored client secret (in-process only). Empty if none stored."""
        from erp.einvoice.services import secrets

        return secrets.decrypt(self.client_secret_encrypted)

    @property
    def has_secret(self) -> bool:
        return bool(self.client_secret_encrypted)


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
    # ETA receiver identity — a business customer carries a tax registration number (receiver type
    # "B"); an individual carries their national ID instead (type "P"). Both optional: a walk-in/cash
    # customer under the ETA reporting threshold (EGP 50,000) needs neither.
    customer_tax_registration_number = models.CharField(max_length=32, blank=True, default="")
    customer_national_id = models.CharField(max_length=14, blank=True, default="")
    issue_date = models.DateField()
    currency = models.CharField(max_length=3, default="EGP")
    tax_code = models.CharField(max_length=16, blank=True, default="")
    net_minor = models.BigIntegerField(default=0)
    tax_minor = models.BigIntegerField(default=0)
    total_minor = models.BigIntegerField(default=0)
    # ETA submission lifecycle.
    status = models.CharField(max_length=16, choices=ETAStatus.choices, default=ETAStatus.DRAFT)
    uuid = models.CharField(max_length=64, blank=True, default="")        # ETA document UUID (26 chars live; 64-char local hash while simulated)
    long_id = models.CharField(max_length=64, blank=True, default="")     # ETA long ID (42 chars) — the human-visible/printable document identifier
    submission_uuid = models.CharField(max_length=32, blank=True, default="")  # ETA batch submission UUID (26 chars) for traceability
    document_hash = models.CharField(max_length=64, blank=True, default="")  # sha256 of the document
    submitted_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    error_text = models.CharField(max_length=255, blank=True, default="")
    # FILE_04 status reconciliation: how many times the beat sweep (or a manual poll) has asked ETA
    # for a verdict and gotten none yet. Reset to 0 the moment a verdict lands (valid/rejected/etc).
    poll_attempts = models.PositiveIntegerField(default=0)
    # Next automatic sweep eligibility (exponential backoff) — null means "eligible now". A manual
    # poll from the UI ignores this and always asks immediately.
    next_poll_at = models.DateTimeField(null=True, blank=True)
    # Set once poll_attempts exceeds the cap with still no verdict — an operator-visible alert
    # (not a silent hang). The beat sweep skips stalled rows; a manual poll can still retry one.
    poll_stalled = models.BooleanField(default=False)

    class Meta:
        db_table = "einvoice_eta_invoice"
        ordering = ["-issue_date", "-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["customer_code"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"ETA[{self.invoice_number}]"
