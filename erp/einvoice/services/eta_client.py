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

from django.utils import timezone

# ETA tokens last ~1 hour. Refresh a little early so a long request can't start on a token that
# expires mid-flight.
_EXPIRY_SKEW_SECONDS = 60
_TIMEOUT_SECONDS = 20
_SCOPE = "InvoicingAPI"
_TOKEN_PATH = "/connect/token"
# Document API paths, verified 2026-07-21 against the official ETA SDK
# (https://sdk.invoicing.eta.gov.eg/einvoicingapi/01-submit-documents/ and .../11-get-document-details/).
# Volatile — re-verify at go-live; override the base via ``ETA_API_BASE_URL`` rather than editing here.
_SUBMIT_PATH = "/api/v1.0/documentsubmissions/"
_DETAILS_PATH = "/api/v1.0/documents/{uuid}/details"
# The document API can take longer than a token request (it validates structure), so it gets a
# more generous read timeout than the identity call.
_DOC_TIMEOUT_SECONDS = 60

# The five settings that must all be present before any ETA call is possible. Names only — these
# are safe to expose (the operator panel reports presence by name); values never leave this module.
# The values themselves are resolved through ``config.effective_config`` (database-first, env
# fallback) so this module never has to know *where* the credentials came from.
REQUIRED_SETTINGS = ("ETA_ENV", "ETA_IDENTITY_URL", "ETA_CLIENT_ID", "ETA_CLIENT_SECRET", "ETA_RIN")


class ETAConfigError(RuntimeError):
    """ETA credentials/endpoints are absent or incomplete — the caller should stay on the stub."""


class ETAAuthError(RuntimeError):
    """The identity service refused or could not be reached. Never carries the secret."""


class ETASubmissionError(RuntimeError):
    """The document API refused or could not be reached (FILE_02).

    ``retryable`` distinguishes a transient failure (network down, 5xx, throttling) — where the
    invoice should stay submittable and be retried — from a permanent one (malformed document,
    forbidden). The message never carries the client secret (the secret only ever rides the token
    request, never a document call)."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


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
    """True only when every required credential is present (from database or env). Presence, never
    validity — the values are proven correct by :func:`fetch_token`, not by this check."""
    from . import config

    return not config.missing_fields(config.effective_config())


def missing_settings() -> list[str]:
    """The ``ETA_*`` names (never values) of the required credentials that are still blank."""
    from . import config

    return config.missing_setting_names(config.effective_config())


def _token_url(identity_url: str) -> str:
    """The identity token endpoint, with the scheme enforced.

    ``https`` is required, not assumed: ``urlopen`` honours whatever scheme it is handed, so a
    typo'd or hostile identity URL of ``file:///...`` would otherwise turn a token request into a
    local file read, and a ``http://`` one would put the client secret on the wire in clear text.
    ETA serves https only, so anything else is a configuration error worth failing on.
    """
    base = str(identity_url or "").strip().rstrip("/")
    if not base.lower().startswith("https://"):
        raise ETAConfigError("The ETA identity URL must be an https:// URL.")
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
    from . import config

    cfg = config.effective_config()
    if config.missing_fields(cfg):
        raise ETAConfigError(
            "ETA is not configured. Missing: " + ", ".join(config.missing_setting_names(cfg)))

    with _CACHE.lock:
        if not force and _CACHE.valid():
            return _CACHE.token

        data = _post_form(_token_url(cfg.identity_url), {
            "grant_type": "client_credentials",
            "client_id": cfg.client_id,
            "client_secret": cfg.client_secret,
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


# --- document API (FILE_02) ----------------------------------------------------------------------


def _api_base() -> str:
    """The document API base URL, https enforced (same reasoning as :func:`_token_url`)."""
    from . import config

    base = str(config.effective_config().api_base_url or "").strip().rstrip("/")
    if not base:
        raise ETAConfigError("The ETA API base URL is not configured.")
    if not base.lower().startswith("https://"):
        raise ETAConfigError("The ETA API base URL must be an https:// URL.")
    return base


def _error_detail(body: str) -> str:
    """A short, blame-free reason pulled from an ETA error body — code + message only.

    The document API's error body carries ``{"error": {"code", "message", "details"...}}``. Unlike
    the token request, a *document* body never contains the client secret, so surfacing the error
    text is safe and is what the operator needs to fix a rejection. We still extract only the
    code/message, never echo the whole payload (which can be large and may quote submitted data)."""
    try:
        data = json.loads(body or "")
    except (json.JSONDecodeError, TypeError):
        return ""
    err = data.get("error") if isinstance(data, dict) else None
    if not isinstance(err, dict):
        return ""
    code = str(err.get("code") or "").strip()
    message = str(err.get("message") or "").strip()
    if code and message:
        return f"[{code}] {message}"
    return message or code


def _request_json(url: str, *, method: str, token: str, payload: dict | None = None) -> dict:
    """One authenticated JSON request to the document API. Raises :class:`ETASubmissionError` on any
    failure, classifying transient (retryable) vs permanent by HTTP status."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310 — https base from operator config
    try:
        with urllib.request.urlopen(request, timeout=_DOC_TIMEOUT_SECONDS) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        try:
            detail = _error_detail(exc.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 — a malformed error body must not mask the HTTP status
            detail = ""
        # 5xx and 429 (throttle) are transient; 4xx (bad structure/forbidden/duplicate) are not.
        retryable = exc.code >= 500 or exc.code == 429
        suffix = f" {detail}" if detail else ""
        raise ETASubmissionError(
            f"ETA document API returned HTTP {exc.code}.{suffix}", retryable=retryable) from None
    except urllib.error.URLError as exc:
        raise ETASubmissionError(f"ETA document API unreachable: {exc.reason}", retryable=True) from None
    except json.JSONDecodeError:
        raise ETASubmissionError("ETA document API returned a non-JSON response.", retryable=True) from None


def submit_document(document: dict) -> dict:
    """Submit one prepared ETA document and return the parsed submission response.

    The response carries ``submissionUUID`` plus ``acceptedDocuments`` / ``rejectedDocuments`` —
    the adapter maps those to an invoice state. Raises :class:`ETAConfigError` when the API base or
    credentials are absent, :class:`ETASubmissionError` on a refusal or network failure."""
    token = fetch_token()
    return _request_json(_api_base() + _SUBMIT_PATH, method="POST", token=token,
                         payload={"documents": [document]})


def get_document(uuid: str) -> dict:
    """Fetch a submitted document's details (status + validation results) by its ETA UUID."""
    token = fetch_token()
    path = _DETAILS_PATH.format(uuid=urllib.parse.quote(str(uuid), safe=""))
    return _request_json(_api_base() + path, method="GET", token=token)


def status_report() -> dict:
    """Operator-panel view of ETA readiness: names and timestamps only, never a credential value."""
    from . import config

    cfg = config.effective_config()
    configured = not config.missing_fields(cfg)
    last_ok = _CACHE.last_auth_ok_at
    return {
        "configured": configured,
        "environment": cfg.environment if configured else "",
        "source": cfg.source,  # "database" | "environment" | "none"
        "missing_settings": config.missing_setting_names(cfg),
        "last_auth_ok_at": last_ok.isoformat() if last_ok else None,
        "detail": "using simulated adapter" if not configured else "credentials present",
    }
