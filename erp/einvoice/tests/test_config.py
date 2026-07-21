"""In-app ETA configuration (einvoice-eta-live, admin-config pivot 2026-07-21).

Covers the four halves of the pivot: the at-rest encryption of the client secret, the
database-first / env-fallback resolver, the admin API (secret write-only, admin-gated), and the
Test-connection outcome mapping. No real ETA call happens — the token fetch is monkeypatched.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.einvoice.domain.models import ETASettings
from erp.einvoice.services import config, eta_client, secrets
from erp.identity.models import User
from erp.identity.roles import ACCOUNTANT, SYSTEM_ADMIN

pytestmark = pytest.mark.django_db

SECRET = "super-secret-value"
GOOD = {
    "environment": "sandbox",
    "identity_url": "https://id.preprod.eta.gov.eg",
    "api_base_url": "https://api.preprod.invoicing.eta.gov.eg",
    "client_id": "client-abc",
    "rin": "123456789",
}


@pytest.fixture(autouse=True)
def _clean_cache():
    eta_client.reset_cache()
    yield
    eta_client.reset_cache()


def _user(username: str, role: str) -> User:
    grp, _ = Group.objects.get_or_create(name=role)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(grp)
    return u


def _client(user: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _blank_env(settings):
    for name in eta_client.REQUIRED_SETTINGS + ("ETA_API_BASE_URL",):
        setattr(settings, name, "")


# --- encryption at rest -------------------------------------------------------------------------

def test_secret_encrypts_and_round_trips():
    token = secrets.encrypt(SECRET)
    assert token and token != SECRET               # actually ciphertext, not the plaintext
    assert secrets.decrypt(token) == SECRET


def test_empty_secret_is_empty_both_ways():
    assert secrets.encrypt("") == ""
    assert secrets.decrypt("") == ""


def test_ciphertext_undecryptable_under_a_different_key_raises(settings):
    token = secrets.encrypt(SECRET)
    # Simulate a rotated key with no explicit ETA_SECRET_KEY: change the derivation source.
    settings.SECRET_KEY = "a-totally-different-secret-key"
    settings.ETA_SECRET_KEY = ""
    with pytest.raises(secrets.ETASecretError):
        secrets.decrypt(token)


def test_model_stores_ciphertext_never_plaintext():
    row = ETASettings.load()
    row.set_secret(SECRET)
    row.save()
    row.refresh_from_db()
    assert SECRET not in row.client_secret_encrypted
    assert row.has_secret is True
    assert row.get_secret() == SECRET


# --- resolver: database first, env fallback -----------------------------------------------------

def test_enabled_db_row_wins_over_env(settings):
    for name, value in {**GOOD}.items():
        setattr(settings, config.FIELD_TO_SETTING[name], "ENV-" + value)
    settings.ETA_CLIENT_SECRET = "env-secret"

    row = ETASettings.load()
    for f, v in GOOD.items():
        setattr(row, f, v)
    row.set_secret(SECRET)
    row.enabled = True
    row.save()

    cfg = config.effective_config()
    assert cfg.source == "database"
    assert cfg.client_id == "client-abc"       # DB value, not the ENV- one
    assert cfg.client_secret == SECRET


def test_disabled_db_row_falls_back_to_env(settings):
    for name, value in GOOD.items():
        setattr(settings, config.FIELD_TO_SETTING[name], value)
    settings.ETA_CLIENT_SECRET = "env-secret"

    row = ETASettings.load()
    for f, v in GOOD.items():
        setattr(row, f, "db-" + v)
    row.enabled = False       # not enabled → env wins
    row.save()

    cfg = config.effective_config()
    assert cfg.source == "environment"
    assert cfg.client_id == "client-abc"
    assert cfg.client_secret == "env-secret"


def test_nothing_configured_reports_source_none(settings):
    _blank_env(settings)
    cfg = config.effective_config()
    assert cfg.source == "none"
    assert set(config.missing_setting_names(cfg)) == set(eta_client.REQUIRED_SETTINGS)
    assert eta_client.is_configured() is False


def test_undecryptable_db_secret_reads_as_missing_not_crash(settings):
    """A rotated key must degrade calmly: the panel says 'secret missing', not a 500."""
    row = ETASettings.load()
    for f, v in GOOD.items():
        setattr(row, f, v)
    row.set_secret(SECRET)
    row.enabled = True
    row.save()

    settings.SECRET_KEY = "rotated-key-no-eta-secret-key"
    settings.ETA_SECRET_KEY = ""

    cfg = config.effective_config()
    assert cfg.client_secret == ""
    assert "ETA_CLIENT_SECRET" in config.missing_setting_names(cfg)


# --- admin API ----------------------------------------------------------------------------------

def test_config_get_requires_system_admin():
    accountant = _user("acct", ACCOUNTANT)
    assert _client(accountant).get("/api/einvoice/config").status_code == 403


def test_config_put_saves_and_get_never_returns_the_secret(settings):
    _blank_env(settings)
    admin = _user("admin1", SYSTEM_ADMIN)
    c = _client(admin)

    res = c.put("/api/einvoice/config", {**GOOD, "client_secret": SECRET, "enabled": True}, format="json")
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["has_secret"] is True
    assert body["enabled"] is True
    assert body["configured"] is True
    assert body["source"] == "database"
    assert body["simulated"] is False                # fully configured + enabled → the adapter is live (FILE_02)
    assert SECRET not in res.content.decode()

    got = c.get("/api/einvoice/config").json()["data"]
    assert "client_secret" not in got
    assert SECRET not in c.get("/api/einvoice/config").content.decode()
    assert got["client_id"] == "client-abc"


def test_empty_secret_on_put_leaves_the_stored_one_unchanged(settings):
    _blank_env(settings)
    admin = _user("admin2", SYSTEM_ADMIN)
    c = _client(admin)
    c.put("/api/einvoice/config", {**GOOD, "client_secret": SECRET, "enabled": True}, format="json")

    # A later save that only flips a flag must not wipe the secret.
    c.put("/api/einvoice/config", {"enabled": False}, format="json")
    row = ETASettings.load()
    assert row.get_secret() == SECRET
    assert row.enabled is False


def test_clear_secret_removes_it(settings):
    _blank_env(settings)
    admin = _user("admin3", SYSTEM_ADMIN)
    c = _client(admin)
    c.put("/api/einvoice/config", {**GOOD, "client_secret": SECRET, "enabled": True}, format="json")

    c.put("/api/einvoice/config", {"clear_secret": True}, format="json")
    assert ETASettings.load().has_secret is False


def test_non_https_url_is_rejected(settings):
    _blank_env(settings)
    admin = _user("admin4", SYSTEM_ADMIN)
    res = _client(admin).put(
        "/api/einvoice/config", {"identity_url": "http://id.preprod.eta.gov.eg"}, format="json")
    assert res.status_code == 400


# --- test connection ----------------------------------------------------------------------------

def _configure_enabled():
    row = ETASettings.load()
    for f, v in GOOD.items():
        setattr(row, f, v)
    row.set_secret(SECRET)
    row.enabled = True
    row.save()


def test_test_connection_success_stamps_last_test_ok(settings, monkeypatch):
    _blank_env(settings)
    _configure_enabled()
    monkeypatch.setattr(eta_client, "fetch_token", lambda *a, **k: "tok")

    admin = _user("admin5", SYSTEM_ADMIN)
    res = _client(admin).post("/api/einvoice/config/test", {}, format="json")
    body = res.json()["data"]
    assert body["ok"] is True
    assert "tok" not in res.content.decode()
    assert ETASettings.load().last_test_ok_at is not None


def test_test_connection_maps_auth_failure(settings, monkeypatch):
    _blank_env(settings)
    _configure_enabled()

    def _boom(*a, **k):
        raise eta_client.ETAAuthError("ETA identity service refused the request (HTTP 401).")

    monkeypatch.setattr(eta_client, "fetch_token", _boom)
    admin = _user("admin6", SYSTEM_ADMIN)
    body = _client(admin).post("/api/einvoice/config/test", {}, format="json").json()["data"]
    assert body["ok"] is False
    assert body["reason"] == "auth_failed"
    assert SECRET not in str(body)


def test_test_connection_reports_not_configured(settings):
    _blank_env(settings)   # nothing set, DB row absent
    admin = _user("admin7", SYSTEM_ADMIN)
    body = _client(admin).post("/api/einvoice/config/test", {}, format="json").json()["data"]
    assert body["ok"] is False
    assert body["reason"] == "not_configured"


def test_test_connection_requires_system_admin():
    accountant = _user("acct2", ACCOUNTANT)
    assert _client(accountant).post("/api/einvoice/config/test", {}, format="json").status_code == 403
