"""System Confidence panel API (arp-roadmap track P, item 1) — any authenticated user, read-only.

The positive complement to the dashboard's "Needs attention today" panel: instead of surfacing
problems, it reassures with a calm status strip. Every signal is honestly computed from real state
(never a fabricated "all good") and pairs its colour with a word, per the brand's monochrome-chrome
rule — colour lives inside the panel, never decoration for its own sake.
"""
from __future__ import annotations

import datetime

from django.conf import settings
from django.utils import timezone
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.accounting.contracts import current_fiscal_period, trial_balance_summary
from erp.assistant import client as assistant_client
from erp.inventory.contracts import low_stock

from .status_api import _backup_report

OK = "ok"
WARN = "warn"


def _books_signal() -> dict:
    tb = trial_balance_summary()
    status = OK if tb["is_balanced"] else WARN
    return {"key": "books", "status": status}


def _vat_signal() -> dict:
    period = current_fiscal_period()
    status = OK if period is not None and period["period_status"] == "open" else WARN
    return {"key": "vat", "status": status}


def _backups_signal() -> dict:
    report = _backup_report()
    if not report["configured"] or report["last_backup_at"] is None:
        return {"key": "backups", "status": WARN}
    age = timezone.now() - datetime.datetime.fromisoformat(report["last_backup_at"])
    status = OK if age <= datetime.timedelta(hours=48) else WARN
    return {"key": "backups", "status": status}


def _stock_signal() -> dict:
    low = low_stock(limit=1)
    return {"key": "stock", "status": OK if not low else WARN}


def _assistant_signal() -> dict:
    # provider_chain() always falls back to ["anthropic"] even with no key set (see its docstring),
    # so "chain non-empty" alone can't prove a provider is actually usable — check a real key exists.
    has_key = any(getattr(settings, key, "") for key in assistant_client.PROVIDER_KEYS.values())
    connected = assistant_client.enabled() and has_key
    return {"key": "assistant", "status": OK if connected else WARN}


class ConfidenceView(APIView):
    """``GET /api/dashboard/confidence/`` — the System Confidence panel's 5 trust signals."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        # Each signal is computed defensively — a module a role can't reach, or a check that
        # errors, degrades to "warn" rather than breaking the whole panel (same defensive spirit
        # as the dashboard's AttentionPanel).
        checks = (
            ("books", _books_signal),
            ("vat", _vat_signal),
            ("backups", _backups_signal),
            ("stock", _stock_signal),
            ("assistant", _assistant_signal),
        )
        signals = []
        for key, fn in checks:
            try:
                signals.append(fn())
            except Exception:  # noqa: BLE001 — a signal must never take the panel down
                signals.append({"key": key, "status": WARN})
        return Response({"data": {"signals": signals}})


urlpatterns = [
    path("confidence/", ConfidenceView.as_view(), name="dashboard-confidence"),
]
