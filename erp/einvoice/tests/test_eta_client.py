"""ETA identity client (einvoice-eta-live FILE_01) — configuration presence, token caching, and
the secret-never-leaks discipline.

No real ETA call happens here: the network layer (``_post_form``) is monkeypatched, so these pin
the contract we build ON TOP of ETA's OAuth2 (caching, expiry, failure shapes, redaction) without
credentials. The live sandbox handshake is the one part of FILE_01 that stays unverified until real
credentials exist — see the plan file's "Done when".
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from erp.einvoice.services import eta_client

CONFIGURED = {
    "ETA_ENV": "sandbox",
    "ETA_IDENTITY_URL": "https://id.preprod.eta.gov.eg",
    "ETA_API_BASE_URL": "https://api.preprod.invoicing.eta.gov.eg",
    "ETA_CLIENT_ID": "client-abc",
    "ETA_CLIENT_SECRET": "super-secret-value",
    "ETA_RIN": "123456789",
}


@pytest.fixture(autouse=True)
def _clean_cache():
    eta_client.reset_cache()
    yield
    eta_client.reset_cache()


def _configure(settings, **overrides):
    for name, value in {**CONFIGURED, **overrides}.items():
        setattr(settings, name, value)


# --- configuration presence ---------------------------------------------------------------------

def test_unconfigured_by_default(settings):
    """A stock install has no ETA credentials and must say so calmly — this is the normal state,
    not an error: the simulated adapter keeps working."""
    for name in eta_client.REQUIRED_SETTINGS:
        setattr(settings, name, "")

    assert eta_client.is_configured() is False
    assert set(eta_client.missing_settings()) == set(eta_client.REQUIRED_SETTINGS)

    report = eta_client.status_report()
    assert report["configured"] is False
    assert report["last_auth_ok_at"] is None
    assert report["detail"] == "using simulated adapter"


def test_partial_configuration_is_not_configured(settings):
    """Four of five present is still unusable — a half-configured install must never be treated as
    ready, or the first real invoice discovers the gap."""
    _configure(settings, ETA_CLIENT_SECRET="")

    assert eta_client.is_configured() is False
    assert eta_client.missing_settings() == ["ETA_CLIENT_SECRET"]


def test_whitespace_only_value_counts_as_missing(settings):
    """A var set to spaces in a .env is a configuration mistake, not a credential."""
    _configure(settings, ETA_RIN="   ")

    assert eta_client.is_configured() is False
    assert eta_client.missing_settings() == ["ETA_RIN"]


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",              # would turn a token request into a local file read
    "http://id.preprod.eta.gov.eg",    # would put the client secret on the wire in clear text
    "ftp://id.preprod.eta.gov.eg",
])
def test_non_https_identity_url_is_rejected(settings, monkeypatch, url):
    """``urlopen`` honours whatever scheme it is given, so the https requirement is enforced rather
    than assumed — a typo'd or hostile identity URL must fail before any request is built."""
    _configure(settings, ETA_IDENTITY_URL=url)
    called: list = []
    monkeypatch.setattr(eta_client, "_post_form", lambda *a, **k: called.append(1) or {})

    with pytest.raises(eta_client.ETAConfigError):
        eta_client.fetch_token()
    assert called == []  # nothing was ever sent


def test_fetch_token_without_config_raises_config_error(settings):
    """The caller can distinguish 'not set up' (fall back to the stub) from 'ETA refused us'."""
    for name in eta_client.REQUIRED_SETTINGS:
        setattr(settings, name, "")

    with pytest.raises(eta_client.ETAConfigError):
        eta_client.fetch_token()


# --- token acquisition + caching ----------------------------------------------------------------

def test_token_is_fetched_then_cached(settings, monkeypatch):
    """One network round trip per token lifetime — a second call reuses the cache."""
    _configure(settings)
    calls: list[dict] = []

    def _fake_post(url, payload):
        calls.append({"url": url, "payload": payload})
        return {"access_token": "tok-1", "expires_in": 3600}

    monkeypatch.setattr(eta_client, "_post_form", _fake_post)

    assert eta_client.fetch_token() == "tok-1"
    assert eta_client.fetch_token() == "tok-1"
    assert len(calls) == 1

    # The request shape is ETA's documented OAuth2 client_credentials call.
    assert calls[0]["url"] == "https://id.preprod.eta.gov.eg/connect/token"
    assert calls[0]["payload"]["grant_type"] == "client_credentials"
    assert calls[0]["payload"]["scope"] == "InvoicingAPI"
    assert calls[0]["payload"]["client_id"] == "client-abc"


def test_force_refetches_even_with_a_live_token(settings, monkeypatch):
    tokens = iter(["tok-1", "tok-2"])
    _configure(settings)
    monkeypatch.setattr(eta_client, "_post_form",
                        lambda url, payload: {"access_token": next(tokens), "expires_in": 3600})

    assert eta_client.fetch_token() == "tok-1"
    assert eta_client.fetch_token(force=True) == "tok-2"


def test_expired_token_is_refetched(settings, monkeypatch):
    """Expiry is honoured, not assumed — a stale token must never ride along on a submission."""
    tokens = iter(["tok-1", "tok-2"])
    _configure(settings)
    monkeypatch.setattr(eta_client, "_post_form",
                        lambda url, payload: {"access_token": next(tokens), "expires_in": 3600})

    assert eta_client.fetch_token() == "tok-1"
    eta_client._CACHE.expires_at = timezone.now() - timedelta(seconds=1)  # force it stale

    assert eta_client.fetch_token() == "tok-2"


def test_token_expiry_applies_a_refresh_skew(settings, monkeypatch):
    """The cached expiry sits ~a minute BEFORE ETA's own, so a request can't begin on a token that
    dies mid-flight."""
    _configure(settings)
    monkeypatch.setattr(eta_client, "_post_form",
                        lambda url, payload: {"access_token": "tok", "expires_in": 3600})

    before = timezone.now()
    eta_client.fetch_token()
    lifetime = (eta_client._CACHE.expires_at - before).total_seconds()

    assert lifetime < 3600  # skewed early
    assert lifetime > 3000  # but still most of the hour


@pytest.mark.parametrize("payload", [
    {"access_token": "tok"},                       # no expires_in at all
    {"access_token": "tok", "expires_in": None},   # null
    {"access_token": "tok", "expires_in": "abc"},  # garbage
    {"access_token": "tok", "expires_in": 0},      # zero
])
def test_missing_or_garbage_expiry_never_mints_an_immortal_token(settings, monkeypatch, payload):
    """A malformed ``expires_in`` must fail SHORT (re-auth soon), never long. Caching a token
    forever because ETA omitted a field would keep using a credential long after it died."""
    _configure(settings)
    monkeypatch.setattr(eta_client, "_post_form", lambda url, payload_: payload)

    eta_client.fetch_token()
    lifetime = (eta_client._CACHE.expires_at - timezone.now()).total_seconds()

    assert 0 < lifetime <= 61  # one short refresh cycle, not an hour and not forever


def test_empty_access_token_is_an_auth_error(settings, monkeypatch):
    """A 200 with no token is still a failure — never cache an empty bearer."""
    _configure(settings)
    monkeypatch.setattr(eta_client, "_post_form", lambda url, payload: {"access_token": ""})

    with pytest.raises(eta_client.ETAAuthError):
        eta_client.fetch_token()
    assert eta_client._CACHE.token == ""


# --- the secret never leaks ---------------------------------------------------------------------

def test_status_report_never_contains_the_secret(settings, monkeypatch):
    """The operator panel is the most likely place for a credential to escape — it must carry
    presence and timestamps only."""
    _configure(settings)
    monkeypatch.setattr(eta_client, "_post_form",
                        lambda url, payload: {"access_token": "tok", "expires_in": 3600})
    eta_client.fetch_token()

    report = eta_client.status_report()
    blob = repr(report)

    assert CONFIGURED["ETA_CLIENT_SECRET"] not in blob
    assert "tok" not in blob
    assert report["configured"] is True
    assert report["environment"] == "sandbox"
    assert report["last_auth_ok_at"] is not None


def test_auth_failure_message_never_echoes_the_secret(settings, monkeypatch):
    """An ETA error body can quote submitted parameters, so failures surface status only."""
    import urllib.error

    _configure(settings)

    def _boom(url, data=None, **kwargs):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(eta_client.urllib.request, "urlopen", _boom)

    with pytest.raises(eta_client.ETAAuthError) as exc:
        eta_client.fetch_token()

    assert CONFIGURED["ETA_CLIENT_SECRET"] not in str(exc.value)
    assert "401" in str(exc.value)


def test_unreachable_identity_service_is_an_auth_error(settings, monkeypatch):
    """An offline/air-gapped install must get a clear reason, not a raw socket traceback."""
    import urllib.error

    _configure(settings)

    def _boom(url, data=None, **kwargs):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(eta_client.urllib.request, "urlopen", _boom)

    with pytest.raises(eta_client.ETAAuthError) as exc:
        eta_client.fetch_token()
    assert "unreachable" in str(exc.value)
