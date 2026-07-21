"""Credential-gated ETA pre-production submission smoke (einvoice-eta-live FILE_02 acceptance).

This is the *validation against the sandbox* step the plan's locked decision #3 calls for. It cannot
run without the company's real ETA pre-production credentials + tax profile (the STOP-gate), so it is
**opt-in and credential-gated**: with ETA not configured it prints why and exits 0 (nothing to prove
yet); with ETA configured + enabled it performs one real round-trip against the pre-production portal
and reports exactly what came back.

    .\\.venv\\Scripts\\python.exe manage.py eta_sandbox_smoke                # uses/creates a seeded probe invoice
    .\\.venv\\Scripts\\python.exe manage.py eta_sandbox_smoke --invoice INV-123   # submit an existing recorded invoice
    .\\.venv\\Scripts\\python.exe manage.py eta_sandbox_smoke --poll         # also poll the document's ETA status

Safety: this SUBMITS a document to ETA pre-production. It refuses to run against ``ETA_ENV=production``
unless ``--allow-production`` is passed, so an accidental run can never file a real invoice. The
client secret is never printed; only the returned UUID / long ID / status / rejection reason are.
"""
from __future__ import annotations

import datetime as dt

from django.core.management.base import BaseCommand, CommandError

from erp.einvoice.domain.models import ETAInvoice
from erp.einvoice.services import EInvoiceInput, eta_adapter, poll_invoice, record_invoice, submit_invoice
from erp.einvoice.services import config as eta_config

_PROBE_INVOICE = "ETA-SANDBOX-SMOKE"


class Command(BaseCommand):
    help = "Run one real ETA pre-production submission to validate the live adapter (credential-gated)."

    def add_arguments(self, parser):
        parser.add_argument("--invoice", default="", help="submit an existing recorded invoice number instead of the probe")
        parser.add_argument("--poll", action="store_true", help="after submit, poll the document's ETA status")
        parser.add_argument("--allow-production", action="store_true", help="permit running against ETA_ENV=production (dangerous)")

    def handle(self, *args, **options):
        if not eta_adapter.is_live():
            cfg = eta_config.effective_config()
            missing = ", ".join(eta_config.missing_setting_names(cfg)) or "ETA_API_BASE_URL"
            self.stdout.write(self.style.WARNING(
                "ETA is not live — the adapter is on the simulated stub, so there is nothing to submit.\n"
                f"Missing configuration: {missing}.\n"
                "Enter credentials in Settings -> E-Invoicing (and enable), or set the ETA_* env vars, then re-run."))
            return

        cfg = eta_config.effective_config()
        if cfg.environment == "production" and not options["allow_production"]:
            raise CommandError(
                "Refusing to run against ETA_ENV=production — this submits a real invoice. "
                "Point at pre-production, or pass --allow-production if you truly mean to.")

        self.stdout.write(f"ETA environment: {cfg.environment or '(unset)'}   source: {cfg.source}")

        invoice_number = options["invoice"].strip()
        if invoice_number:
            eta = ETAInvoice.objects.filter(invoice_number=invoice_number).first()
            if eta is None:
                raise CommandError(f"No recorded ETA invoice with number {invoice_number!r}.")
        else:
            eta = record_invoice(EInvoiceInput(
                invoice_number=f"{_PROBE_INVOICE}-{dt.date.today():%Y%m%d}",
                issue_date=dt.date.today(), customer_code="SANDBOX", customer_name="Sandbox Probe",
                currency="EGP", tax_code="VAT14", net_minor=100_00, tax_minor=14_00, total_minor=114_00))
            self.stdout.write(f"Recorded probe invoice {eta.invoice_number}.")

        self.stdout.write("Submitting to ETA …")
        eta = submit_invoice(eta)
        eta.refresh_from_db()

        if eta.status == "submitted" and eta.uuid:
            self.stdout.write(self.style.SUCCESS(
                f"ACCEPTED — status={eta.status}  uuid={eta.uuid}  long_id={eta.long_id or '(none)'}  "
                f"submission_uuid={eta.submission_uuid or '(none)'}"))
        elif eta.status == "rejected":
            self.stdout.write(self.style.ERROR(f"REJECTED by ETA — {eta.error_text}"))
        else:
            # Transient: the invoice stayed submittable rather than being marked rejected.
            self.stdout.write(self.style.WARNING(
                f"NOT SUBMITTED (transient) — status={eta.status}  reason={eta.error_text or '(none)'}  "
                "safe to retry."))

        if options["poll"] and eta.uuid:
            self.stdout.write("Polling ETA for the document status …")
            eta = poll_invoice(eta)
            eta.refresh_from_db()
            self.stdout.write(f"Poll result — status={eta.status}"
                              + (f"  validated_at={eta.validated_at.isoformat()}" if eta.validated_at else ""))
