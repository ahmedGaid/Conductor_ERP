"""Write + send the weekly AI ops report (ai-reliability T1.9).

Thin wrapper over ``erp.assistant.services.send_weekly_report`` — same shape as
``send_ai_digests.py``. Aggregates the last 7 days of Trace rows (volume, cost, error mix) plus
the offline eval delta, writes ``Docs/ops/ai-week-<isoweek>.md``, and notifies every System Admin
(same dispatch path as the morning digest). The Celery beat entry (``assistant.send_ai_weekly_report``,
see ``CELERY_BEAT_SCHEDULE`` in settings) fires this once a week; useful for a manual run/ops check
outside the scheduler.
    .\\.venv\\Scripts\\python.exe manage.py ai_weekly_report
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from erp.assistant.services import send_weekly_report


class Command(BaseCommand):
    help = "Write and send the weekly AI ops report to every System Admin."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="lookback window in days")

    def handle(self, *args, **options) -> None:
        path = send_weekly_report(days=options["days"])
        self.stdout.write(self.style.SUCCESS(f"AI weekly report written: {path}"))
