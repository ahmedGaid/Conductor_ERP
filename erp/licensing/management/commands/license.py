"""``manage.py license install <file-or-key>`` / ``manage.py license status`` — operator tool for
the customer's key. Not shipped as anything else: the founder-only issuer lives separately in
``tools/license/`` and never touches this app's DB."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...core import LicenseKeyError
from ...services import install_key
from ...state import current_state


class Command(BaseCommand):
    help = "Install or check the license key for this install."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="subcommand", required=True)

        install = sub.add_parser("install", help="Verify and install a license key.")
        install.add_argument(
            "key_or_file",
            help="Path to a .lic file, or the CND1.<payload>.<signature> key text itself.",
        )

        sub.add_parser("status", help="Print a human summary of the current license state.")

    def handle(self, *args, **options):
        if options["subcommand"] == "install":
            self._install(options["key_or_file"])
        else:
            self._status()

    def _install(self, key_or_file: str) -> None:
        path = Path(key_or_file)
        key_text = path.read_text(encoding="utf-8") if path.is_file() else key_or_file
        try:
            info = install_key(key_text)
        except LicenseKeyError as exc:
            raise CommandError(f"License rejected ({exc.reason}): {exc.detail or exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            f"Installed: {info.company_name} — {info.edition} edition, {len(info.modules)} "
            f"module(s), maintenance until {info.maintenance_until}."
        ))

    def _status(self) -> None:
        self.stdout.write(describe(current_state()))


def describe(state) -> str:
    """Human summary line for ``license status`` and the go-live report."""
    if state.status == "unmanaged":
        return "unmanaged (LICENSE_MODE=off) — no restrictions."
    if state.status == "trial":
        return f"trial — {state.trial_days_left} day(s) left."
    if state.status == "trial_ended":
        return "trial ended — no key installed."
    if state.status == "active":
        maintenance = "active" if state.maintenance_active else f"ended {state.maintenance_until}"
        branches = "unlimited" if state.max_branches is None else str(state.max_branches)
        ai = "on" if state.ai_active else "off"
        return (
            f"active — {state.edition} edition, {len(state.modules)} module(s), "
            f"max branches {branches}, maintenance {maintenance}, AI {ai}."
        )
    if state.status == "invalid":
        return f"invalid license ({state.invalid_reason})."
    if state.status == "company_mismatch":
        return "license does not match this organization's tax ID."
    return state.status  # pragma: no cover - exhaustive above
