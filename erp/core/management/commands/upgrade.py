"""Upgrade a running install to the current code version: `manage.py upgrade [--yes]`.

Runs any pending, version-registered data fixes (see `erp.core.upgrades`) after migrating, each
in its own transaction and recorded in `AppliedUpgradeStep` so a re-run is a clean no-op. This is
what a customer operator runs after pulling a new release — see Docs/RUNBOOK.md "Upgrading to a
new release".
"""
from __future__ import annotations

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from erp.accounting.services.reports import trial_balance
from erp.core import upgrades
from erp.core.models import AppliedUpgradeStep
from erp.monitoring.checks import run_all


class Command(BaseCommand):
    help = "Migrate + apply pending upgrade steps for the current release, then run post-checks."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
        parser.add_argument(
            "--skip-backup-check",
            action="store_true",
            help="Skip the backup reminder (you have already taken one).",
        )

    def handle(self, *args, **options):
        version = settings.APP_VERSION
        applied = set(AppliedUpgradeStep.objects.values_list("version", "name"))
        pending = [s for s in upgrades.REGISTRY if (s.version, s.name) not in applied]

        self.stdout.write(f"Upgrading to {version} — {len(pending)} pending step(s).")
        if not options["yes"]:
            answer = input("Continue? Type 'yes' to proceed: ")
            if answer.strip().lower() != "yes":
                raise CommandError("Aborted.")

        if not options["skip_backup_check"]:
            self.stdout.write(
                self.style.WARNING(
                    "Have you taken a backup? See Docs/RUNBOOK.md section 5 (pg_dump) — do this "
                    "before continuing if you have not. Pass --skip-backup-check once you have."
                )
            )

        call_command("migrate", verbosity=0)

        for step in pending:
            try:
                with transaction.atomic():
                    step.run()
                    AppliedUpgradeStep.objects.create(version=step.version, name=step.name)
            except Exception as exc:  # noqa: BLE001
                raise CommandError(
                    f"Upgrade step '{step.version}/{step.name}' failed: {exc}. Nothing after it "
                    "was applied; fix the cause and re-run — completed steps are not repeated."
                ) from exc
            self.stdout.write(f"  applied: {step.version}/{step.name}")

        if pending:
            self.stdout.write(self.style.SUCCESS(f"Applied {len(pending)} step(s)."))
        else:
            self.stdout.write("No pending steps — already up to date.")

        self._post_checks(version)

    def _post_checks(self, version: str) -> None:
        health = run_all()
        tb = trial_balance()
        self.stdout.write(f"version: {version}")
        self.stdout.write(f"system-check: {health['status']}")
        for name, comp in health["components"].items():
            if comp["status"] != "healthy":
                self.stdout.write(f"  - {name}: {comp['status']} ({comp['detail']})")
        self.stdout.write(
            f"trial balance: {'balanced' if tb.is_balanced else 'NOT BALANCED'} "
            f"(debit={tb.total_debit}, credit={tb.total_credit})"
        )
        if health["status"] == "critical" or not tb.is_balanced:
            raise CommandError("Post-upgrade checks failed — see report above.")
        self.stdout.write(self.style.SUCCESS("OK"))
