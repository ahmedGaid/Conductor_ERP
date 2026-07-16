"""Customer go-live provisioning: one command that cannot produce an unsafe install.

    manage.py provision_customer [--admin-password-env VAR]
    manage.py provision_customer --verify

Replaces the manual go-live sequence (migrate -> seed_identity -> seed_accounting -> change
admin password by hand) with a single command that refuses to run against anything but a
brand-new, empty database, forces a real admin password (never the dev default), and prints a
go-live report. ``--verify`` re-runs the same report against an already-provisioned install
without touching data — this is what the handover gate (delivery-readiness FILE_07) calls.
"""
from __future__ import annotations

import getpass
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from erp.accounting.domain.models import JournalEntry
from erp.crm.domain.models import Lead
from erp.monitoring.checks import run_all
from erp.pricing.domain.models import PriceList
from erp.pricing.services.management import ensure_default_price_list
from erp.purchasing.domain.models import PurchaseOrder
from erp.sales.domain.models import SalesOrder

User = get_user_model()

ADMIN_USERNAME = "admin"
MIN_PASSWORD_LENGTH = 12
# Known dev/demo passwords that must never reach a customer tenant (seed_identity's DEMO_PASSWORD
# chief among them) — checked case-insensitively in addition to Django's own validators.
BLOCKED_PASSWORDS = {"dev12345!", "password", "password123", "admin", "changeme", "welcome1"}
# Where the nightly backup task (deploy/backup/register-backup-task.ps1) writes its dumps —
# see Docs/RUNBOOK.md section 5. Missing is a warning, not a provisioning failure.
BACKUP_DIR = Path(r"C:\ConductorBackups")


def _business_rows() -> dict[str, int]:
    """Counts of transactional rows a fresh tenant must NOT have."""
    return {
        "sales orders": SalesOrder.objects.count(),
        "purchase orders": PurchaseOrder.objects.count(),
        "journal entries": JournalEntry.objects.count(),
        "leads": Lead.objects.count(),
    }


def _password_errors(password: str) -> list[str]:
    errors = []
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f"must be at least {MIN_PASSWORD_LENGTH} characters")
    if password.lower() in BLOCKED_PASSWORDS:
        errors.append("is a known default/demo password — choose a different one")
    try:
        validate_password(password)
    except ValidationError as exc:
        errors.extend(exc.messages)
    return errors


class Command(BaseCommand):
    help = "Provision a clean customer install, or verify one already provisioned (--verify)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--verify",
            action="store_true",
            help="Verify an existing install's go-live checks instead of provisioning a new one.",
        )
        parser.add_argument(
            "--admin-password-env",
            help="Env var holding the new admin password. Omit to be prompted interactively (twice).",
        )

    def handle(self, *args, **options):
        if options["verify"]:
            self._verify()
        else:
            self._provision(options)

    # --- provision -----------------------------------------------------------------------------

    def _provision(self, options) -> None:
        call_command("migrate", verbosity=0)

        dirty = {name: n for name, n in _business_rows().items() if n}
        if User.objects.exists() or dirty:
            raise CommandError(
                "Refusing: this database is not empty (it already has users and/or business "
                "records). provision_customer only runs against a brand-new database — never "
                "against a clone of dev or an existing install. Create a fresh database and "
                "point .env at it, then try again."
            )

        password = self._collect_admin_password(options)

        call_command("seed_identity", verbosity=0)  # admin-only path — never --demo-users here
        call_command("seed_accounting", verbosity=0)
        ensure_default_price_list()

        admin = User.objects.get(username=ADMIN_USERNAME)
        admin.set_password(password)
        admin.save(update_fields=["password"])

        self.stdout.write(
            self.style.SUCCESS(
                "Provisioned: roles, HQ branch, admin user, chart of accounts, default price list."
            )
        )
        self.stdout.write(
            f"Sign in as '{ADMIN_USERNAME}' with the password you just set, then enroll "
            "two-factor authentication from Settings -> Security before inviting other users."
        )
        self.stdout.write("")
        self._print_report(self._collect_report())

    def _collect_admin_password(self, options) -> str:
        env_var = options.get("admin_password_env")
        if env_var:
            password = os.environ.get(env_var)
            if not password:
                raise CommandError(f"Env var {env_var} is not set (or empty).")
        else:
            password = getpass.getpass("New admin password: ")
            confirm = getpass.getpass("Confirm admin password: ")
            if password != confirm:
                raise CommandError("Passwords did not match.")

        errors = _password_errors(password)
        if errors:
            raise CommandError("Admin password rejected: " + "; ".join(errors))
        return password

    # --- verify --------------------------------------------------------------------------------

    def _verify(self) -> None:
        report = self._collect_report()
        self._print_report(report)
        if not report["ok"]:
            raise CommandError("Go-live verification failed — see report above.")

    # --- shared report ---------------------------------------------------------------------------

    def _collect_report(self) -> dict:
        health = run_all()
        dirty_rows = {name: n for name, n in _business_rows().items() if n}

        default_lists = list(PriceList.objects.filter(is_default=True, is_active=True))

        extra_users = list(User.objects.exclude(username=ADMIN_USERNAME).values_list("username", flat=True))

        weak_password_users = []
        blocklist = BLOCKED_PASSWORDS | {"dev12345!"}
        for user in User.objects.all():
            if any(user.check_password(candidate) for candidate in blocklist):
                weak_password_users.append(user.username)

        backup_configured = BACKUP_DIR.exists()

        ok = (
            health["status"] != "critical"
            and not dirty_rows
            and len(default_lists) == 1
            and not extra_users
            and not weak_password_users
        )

        return {
            "ok": ok,
            "health": health,
            "dirty_rows": dirty_rows,
            "default_price_lists": len(default_lists),
            "extra_users": extra_users,
            "weak_password_users": weak_password_users,
            "backup_configured": backup_configured,
        }

    def _print_report(self, report: dict) -> None:
        health = report["health"]
        self.stdout.write(f"system-check: {health['status']}")
        for name, comp in health["components"].items():
            if comp["status"] != "healthy":
                self.stdout.write(f"  - {name}: {comp['status']} ({comp['detail']})")

        if report["dirty_rows"]:
            for name, count in report["dirty_rows"].items():
                self.stdout.write(self.style.ERROR(f"books not empty: {count} {name}"))
        else:
            self.stdout.write("books empty: yes")

        if report["default_price_lists"] == 1:
            self.stdout.write("default price list: exactly one")
        else:
            self.stdout.write(
                self.style.ERROR(f"default price list: expected exactly 1, found {report['default_price_lists']}")
            )

        if report["extra_users"]:
            self.stdout.write(
                self.style.ERROR(f"non-admin users present: {', '.join(report['extra_users'])}")
            )
        else:
            self.stdout.write("demo users: none")

        if report["weak_password_users"]:
            self.stdout.write(
                self.style.ERROR(
                    f"users with a known/weak password: {', '.join(report['weak_password_users'])}"
                )
            )
        else:
            self.stdout.write("password check: no known/weak passwords in use")

        if report["backup_configured"]:
            self.stdout.write(f"backup: configured ({BACKUP_DIR})")
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"backup: {BACKUP_DIR} not found — register the nightly backup task "
                    "(Docs/RUNBOOK.md section 5) before go-live"
                )
            )

        self.stdout.write(self.style.SUCCESS("OK") if report["ok"] else self.style.ERROR("FAILED"))
