"""Send the ambient AI morning digest to every due, opted-in user.

Thin wrapper over ``erp.assistant.services.send_digests`` — the same call the Celery beat entry
(``assistant.send_ai_digests``) fires daily. Useful for a manual run/ops check outside the scheduler.
    .\\.venv\\Scripts\\python.exe manage.py send_ai_digests
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from erp.assistant.services import send_digests


class Command(BaseCommand):
    help = "Send the morning AI digest to every active user due today."

    def handle(self, *args, **options) -> None:
        count = send_digests()
        self.stdout.write(self.style.SUCCESS(f"AI digests sent: {count}"))
