"""arp-roadmap track P item 1 — System Confidence panel: any authenticated user, 5 honest signals,
never breaks even when a check errors.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.monitoring import confidence

pytestmark = pytest.mark.django_db

URL = "/api/dashboard/confidence/"


@pytest.fixture
def user_client() -> APIClient:
    user = User.objects.create_user(username="conf_plain", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_anonymous_is_401_or_403():
    assert APIClient().get(URL).status_code in (401, 403)


def test_any_authenticated_user_sees_the_panel(user_client):
    resp = user_client.get(URL)
    assert resp.status_code == 200
    signals = resp.json()["data"]["signals"]
    assert {s["key"] for s in signals} == {"books", "vat", "backups", "stock", "assistant"}
    assert all(s["status"] in ("ok", "warn") for s in signals)


def test_a_failing_signal_degrades_to_warn_not_500(user_client, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(confidence, "_books_signal", boom)
    resp = user_client.get(URL)
    assert resp.status_code == 200
    books = next(s for s in resp.json()["data"]["signals"] if s["key"] == "books")
    assert books["status"] == "warn"


def test_backups_not_configured_is_warn(user_client, settings):
    settings.BACKUP_DIR = ""
    resp = user_client.get(URL)
    backups = next(s for s in resp.json()["data"]["signals"] if s["key"] == "backups")
    assert backups["status"] == "warn"


def test_assistant_disabled_is_warn(user_client, settings):
    settings.ASSISTANT_ENABLED = False
    resp = user_client.get(URL)
    assistant = next(s for s in resp.json()["data"]["signals"] if s["key"] == "assistant")
    assert assistant["status"] == "warn"
