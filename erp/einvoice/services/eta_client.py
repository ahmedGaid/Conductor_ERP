"""ETA identity client — OAuth2 token acquisition for real e-invoice submission.

This is the credential half of the ETA integration (einvoice-eta-live FILE_01). It answers exactly
one question — *can we authenticate as the registered integrator?* — and caches the resulting
bearer token for its lifetime. Document submission itself lives in the adapter (FILE_02+); nothing
here submits anything.

**Contract source.** ETA's auth is OAuth2 ``client_credentials`` against its identity service, with
scope ``InvoicingAPI`` and a token that lasts about an hour. Verified 2026-07-20 against the
official SDK (https://sdk.invoicing.eta.gov.eg/faq/ for environment URLs). The endpoint path
``/connect/token`` follows the same IdentityServer convention ETA's own portal uses. Treat all of
it as volatile: re-verify against current ETA docs before go-live, and prefer overriding
``ETA_IDENTITY_URL`` in env over editing this file.

**No new dependency.** Deliberately stdlib ``urllib.request``: ``httpx``/``requests`` are present in
the lockfile only *transitively* (via ``anthropic``/``google-genai``), so importing one here would
promote it to a direct dependency — a STOP-gate under this plan's locked decision #5. A single
form-encoded POST does not justify that ask. If FILE_02 needs pooling/retry/timeout policy across
many document calls, promoting ``httpx`` becomes a real, separate decision.

**Secrets.** The client secret is read from settings (env-only) and never logged, never returned,
never included in any error message or status payload. Failures surface the HTTP status and a short
reason, never the request body.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

# ETA tokens last ~1 hour. Refresh a little early so a long request can't start on a token that
# expires mid-flight.
_EXPIRY_SKEW_SECONDS = 60
_TIMEOUT_SECONDS = 20
_SCOPE = "InvoicingAPI"
_TOKEN_PATH = "/connect/token"

# The five settings that must all be present before any ETA call is possible. Names only — these
# are safe to expose (the operator panel reports presence by name); values never leave this module.
REQUIRED_SETTINGS = ("ETA_ENV", "ETA_IDENTITY_URL", "ETA_CLIENT_ID", "ETA_CLIENT_SECRET", "ETA_RIN")


class ETAConfigError(RuntimeError):
    """ETA credentials/endpoints are absent or incomplete — the caller should stay on the stub."""


class ETAAuthError(RuntimeError):
    """The identity service refused or could not be reached. Never carries the secret."""


@dataclass
class _TokenCache:
    """Process-local cache of the current bearer token. Not shared across workers by design — a
    token request is cheap and hourly, so a per-process token avoids putting a live credential in
    Redis where the backup/observability surface would reach it."""

    token: str = ""
    expires_at: object = None  # datetime | None
    last_auth_ok_at: object = None  # datetime | None — the operator panel's freshness signal
    lock: threading.Lock = field(default_factory=threading.Lock)

    def valid(self) -> bool:
        if not self.token or self.expires_at is None:
            return False
        return timezone.now() < self.expires_at


_CACHE = _TokenCache()


def is_configured() -> bool:
    """True only when every required setting is non-empty. Presence, never validity — the values
    are proven correct by :func:`fetch_token`, not by this check."""
    return all(str(getattr(settings, name, "") or "").strip() for name in REQUIRED_SETTINGS)


def missing_settings() -> list[str]:
    """The names (never values) of the required settings that are still blank."""
    return [name for name in REQUIRED_SETTINGS
            if not str(getattr(settings, name, "") or "").strip()]


def _token_url() -> str:
    """The identity token endpoint, with the scheme enforced.

    ``https`` is required, not assumed: ``urlopen`` honours whatever scheme it is handed, so a
    typo'd or hostile ``ETA_IDENTITY_URL`` of ``file:///...`` would otherwise turn a token request
    into a local file read, and a ``http://`` one would put the client secret on the wire in clear
    text. ETA serves https only, so anything else is a configuration error worth failing on.
    """
    base = str(settings.ETA_IDENTITY_URL or "").strip().rstrip("/")
    if not base.lower().startswith("https://"):
        raise ETAConfigError("ETA_IDENTITY_URL must be an https:// URL.")
    return f"{base}{_TOKEN_PATH}"


def _post_form(url: str, payload: dict) -> dict:
    """One form-encoded POST returning parsed JSON. Raises :class:`ETAAuthError` on any failure,
    with a message that never echoes the request body (which holds the secret)."""
    body = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 — https URL comes from operator config, not user input
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Status only. An ETA error body can echo submitted parameters, so it is not surfaced.
        raise ETAAuthError(f"ETA identity service refused the request (HTTP {exc.code}).") from None
    except urllib.error.URLError as exc:
        raise ETAAuthError(f"ETA identity service unreachable: {exc.reason}") from None
    except json.JSONDecodeError:
        raise ETAAuthError("ETA identity service returned a non-JSON response.") from None


def fetch_token(*, force: bool = False) -> str:
    """Return a valid bearer token, using the cached one unless it is expired or ``force``.

    Raises :class:`ETAConfigError` when credentials are absent (the caller should fall back to the
    simulated adapter) and :class:`ETAAuthError` when ETA rejects or cannot be reached.
    """
    if not is_configured():
        raise ETAConfigError(
            "ETA is not configured. Missing: " + ", ".join(missing_settings()))

    with _CACHE.lock:
        if not force and _CACHE.valid():
            return _CACHE.token

        data = _post_form(_token_url(), {
            "grant_type": "client_credentials",
            "client_id": str(settings.ETA_CLIENT_ID).strip(),
            "client_secret": str(settings.ETA_CLIENT_SECRET).strip(),
            "scope": _SCOPE,
        })

        token = str(data.get("access_token") or "").strip()
        if not token:
            raise ETAAuthError("ETA identity service returned no access_token.")

        try:
            lifetime = int(data.get("expires_in") or 0)
        except (TypeError, ValueError):
            lifetime = 0
        # An absent/garbage expires_in must not mint an immortal token — fall back to one refresh
        # cycle so the next call re-authenticates rather than reusing something possibly dead.
        lifetime = max(lifetime - _EXPIRY_SKEW_SECONDS, _EXPIRY_SKEW_SECONDS)

        now = timezone.now()
        _CACHE.token = token
        _CACHE.expires_at = now + timedelta(seconds=lifetime)
        _CACHE.last_auth_ok_at = now
        return token


def reset_cache() -> None:
    """Drop the cached token — used by tests and by a config change at runtime."""
    with _CACHE.lock:
        _CACHE.token = ""
        _CACHE.expires_at = None
        _CACHE.last_auth_ok_at = None


def status_report() -> dict:
    """Operator-panel view of ETA readiness: names and timestamps only, never a credential value."""
    configured = is_configured()
    last_ok = _CACHE.last_auth_ok_at
    return {
        "configured": configured,
        "environment": str(getattr(settings, "ETA_ENV", "") or "") if configured else "",
        "missing_settings": missing_settings(),
        "last_auth_ok_at": last_ok.isoformat() if last_ok else None,
        "detail": "using simulated adapter" if not configured else "credentials present",
    }
