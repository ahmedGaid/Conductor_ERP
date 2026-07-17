"""TH FILE_19 Task C — system status panel: admin-only, env values never leave the server,
degraded subsystems render as degraded (not silently healthy).
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.identity.roles import SYSTEM_ADMIN
from erp.monitoring import checks, status_api

pytestmark = pytest.mark.django_db

URL = "/api/system/status/"


@pytest.fixture
def admin_client() -> APIClient:
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    user = User.objects.create_user(username="sys_admin", password="Dev12345!")
    user.groups.add(Group.objects.get(name=SYSTEM_ADMIN))
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def plain_client() -> APIClient:
    user = User.objects.create_user(username="sys_plain", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_non_admin_is_403(plain_client):
    assert plain_client.get(URL).status_code == 403


def test_anonymous_is_401_or_403():
    assert APIClient().get(URL).status_code in (401, 403)


def test_admin_sees_the_full_panel(admin_client):
    resp = admin_client.get(URL)
    assert resp.status_code == 200
    data = resp.json()["data"]
    for key in ("version", "uptime_seconds", "status", "database", "redis", "storage",
                "workers", "backup", "env"):
        assert key in data, data


def test_env_values_never_serialized(admin_client, monkeypatch):
    """A known secret VALUE must never appear anywhere in the response body — only NAMES + set/unset."""
    marker = "sk-super-secret-marker-DO-NOT-LEAK"
    monkeypatch.setenv("DJANGO_SECRET_KEY", marker)
    monkeypatch.setenv("ANTHROPIC_API_KEY", marker)

    resp = admin_client.get(URL)
    body = resp.content.decode()

    assert marker not in body
    data = resp.json()["data"]
    assert data["env"]["DJANGO_SECRET_KEY"] == "set"
    assert data["env"]["ANTHROPIC_API_KEY"] == "set"
    # Every reported value is the literal word set/unset — never the underlying env value.
    assert set(data["env"].values()) <= {"set", "unset"}


def test_env_names_catalog_is_exhaustive_names_only(admin_client):
    resp = admin_client.get(URL)
    data = resp.json()["data"]
    assert set(data["env"].keys()) == set(status_api.ENV_VAR_NAMES)


def test_degraded_redis_renders_degraded_state(admin_client, monkeypatch):
    monkeypatch.setattr(checks, "check_redis", lambda: (checks.CRITICAL, "ConnectionError: down"))

    resp = admin_client.get(URL)
    assert resp.status_code == 200  # a data panel, not a liveness probe — it still renders
    data = resp.json()["data"]
    assert data["redis"]["status"] == checks.CRITICAL
    assert data["status"] == checks.CRITICAL  # overall rolls up the worst component


def test_backup_not_configured_by_default(admin_client, settings):
    settings.BACKUP_DIR = ""
    resp = admin_client.get(URL)
    backup = resp.json()["data"]["backup"]
    assert backup["configured"] is False
    assert backup["last_backup_at"] is None


def test_backup_reports_latest_snapshot_mtime(admin_client, settings, tmp_path):
    import os
    import time

    older = tmp_path / "20260101-020000"
    older.mkdir()
    os.utime(older, (time.time() - 3600, time.time() - 3600))
    latest = tmp_path / "20260102-020000"
    latest.mkdir()
    settings.BACKUP_DIR = str(tmp_path)

    resp = admin_client.get(URL)
    backup = resp.json()["data"]["backup"]
    assert backup["configured"] is True
    assert backup["last_backup_at"] is not None
    assert backup["detail"] == latest.name
