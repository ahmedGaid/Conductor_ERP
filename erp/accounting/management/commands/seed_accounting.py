"""Seed a baseline Chart of Accounts + the current fiscal year with 12 open monthly periods.

Thin wrapper over ``erp.accounting.services.seeding.seed_baseline_accounting`` (the same provisioning
the first-run setup wizard calls). Idempotent. For dev/demo use.
    .\\.venv\\Scripts\\python.exe manage.py seed_accounting
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from erp.accounting.services.seeding import seed_baseline_accounting


class Command(BaseCommand):
    help = "Seed a baseline Chart of Accounts and the current fiscal year/periods."

    def handle(self, *args, **options) -> None:
        summary = seed_baseline_accounting()
        self.stdout.write(
            self.style.SUCCESS(f"accounting seeded: {summary['accounts']} accounts, current fiscal year, 12 periods")
        )
