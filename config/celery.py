"""Celery application for background jobs (imports/exports/reporting/notifications/workflow).

All long-running operations run here and must be retryable, observable, and recoverable
(see the engineering charter). The broker/result backend is Redis (Memurai on Windows).
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("erp")
# All Celery config lives in Django settings under the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")
# Discover tasks.py in every installed module.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:  # pragma: no cover - diagnostics helper
    print(f"Request: {self.request!r}")
