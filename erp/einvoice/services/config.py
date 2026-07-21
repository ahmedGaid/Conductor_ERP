"""Effective ETA connection configuration — database first, environment as fallback.

The admin-config pivot (2026-07-21) lets a System Admin enter ETA credentials in-app. Those live in
the :class:`~erp.einvoice.domain.models.ETASettings` singleton (secret encrypted). This module is the
single place that decides which configuration is *in force*:

1. The ``ETASettings`` row when it is **enabled** — the in-app configuration wins.
2. Otherwise ``settings.ETA_*`` from the environment — the legacy path, still fully supported so an
   ops-seeded ``.env`` keeps working with no UI interaction.

Everything downstream (``eta_client`` auth, the operator panel, the future submission adapter) reads
config through :func:`effective_config` and never touches ``settings.ETA_*`` or the model directly —
so there is exactly one resolution rule to reason about.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from django.conf import settings

# The fields that must all be present before ETA can authenticate. ``api_base_url`` is deliberately
# not here — it is needed to *submit* a document (FILE_02+), not to acquire a token, so an install
# can prove its credentials (Test connection) before the submission adapter exists.
REQUIRED_FIELDS = ("environment", "identity_url", "client_id", "client_secret", "rin")

# Maps an internal field name to its historical ``ETA_*`` env/setting name, so operator-panel and
# test output keep speaking the names ops already know from ``.env.example``.
FIELD_TO_SETTING = {
    "environment": "ETA_ENV",
    "identity_url": "ETA_IDENTITY_URL",
    "api_base_url": "ETA_API_BASE_URL",
    "client_id": "ETA_CLIENT_ID",
    "client_secret": "ETA_CLIENT_SECRET",
    "rin": "ETA_RIN",
}


@dataclass(frozen=True)
class ETAConfig:
    environment: str = ""
    identity_url: str = ""
    api_base_url: str = ""
    client_id: str = ""
    client_secret: str = ""   # plaintext, in-process only — never serialized, never logged
    rin: str = ""
    source: str = "none"      # "database" | "environment" | "none"
    # --- issuer tax profile (FILE_02) ----------------------------------------------------------
    # Static company identity the ETA document requires on every invoice (issuer block +
    # activity code). Not a secret, so it is always env-sourced for now (no DB columns yet — a
    # follow-up admin-config slice may move it into ``ETASettings``). Env fills it in both DB and
    # env config modes so an in-app connection still emits a complete document.
    issuer_name: str = ""
    activity_code: str = ""
    branch_id: str = ""
    country: str = "EG"
    governate: str = ""
    region_city: str = ""
    street: str = ""
    building_number: str = ""


def _issuer_profile_from_env() -> dict:
    """The issuer tax-profile fields, read from settings. Static, non-secret company identity."""
    g = lambda name, default="": str(getattr(settings, name, "") or default).strip()  # noqa: E731
    return {
        "issuer_name": g("ETA_ISSUER_NAME"),
        "activity_code": g("ETA_ACTIVITY_CODE"),
        "branch_id": g("ETA_BRANCH_ID"),
        "country": g("ETA_ISSUER_COUNTRY", "EG") or "EG",
        "governate": g("ETA_ISSUER_GOVERNATE"),
        "region_city": g("ETA_ISSUER_REGION_CITY"),
        "street": g("ETA_ISSUER_STREET"),
        "building_number": g("ETA_ISSUER_BUILDING_NO"),
    }


def _from_env() -> ETAConfig:
    return ETAConfig(
        environment=str(getattr(settings, "ETA_ENV", "") or "").strip(),
        identity_url=str(getattr(settings, "ETA_IDENTITY_URL", "") or "").strip(),
        api_base_url=str(getattr(settings, "ETA_API_BASE_URL", "") or "").strip(),
        client_id=str(getattr(settings, "ETA_CLIENT_ID", "") or "").strip(),
        client_secret=str(getattr(settings, "ETA_CLIENT_SECRET", "") or "").strip(),
        rin=str(getattr(settings, "ETA_RIN", "") or "").strip(),
        source="environment",
        **_issuer_profile_from_env(),
    )


def _from_row(row) -> ETAConfig:
    # A decrypt failure (key rotated with no ETA_SECRET_KEY set) surfaces as a *missing* secret so
    # the panel stays calm and the fix is obvious: re-enter it. See secrets.py's documented tradeoff.
    from .secrets import ETASecretError

    try:
        secret = row.get_secret()
    except ETASecretError:
        secret = ""
    return ETAConfig(
        environment=(row.environment or "").strip(),
        identity_url=(row.identity_url or "").strip(),
        api_base_url=(row.api_base_url or "").strip(),
        client_id=(row.client_id or "").strip(),
        client_secret=secret,
        rin=(row.rin or "").strip(),
        source="database",
        # The issuer profile has no DB columns yet — always read it from env so the in-app
        # (DB-enabled) path still produces a complete ETA document.
        **_issuer_profile_from_env(),
    )


def effective_config() -> ETAConfig:
    """The ETA configuration in force right now (database row if enabled, else environment)."""
    from ..domain.models import ETASettings

    row = ETASettings.objects.filter(pk=ETASettings._SINGLETON_PK).first()
    if row is not None and row.enabled:
        return _from_row(row)

    env = _from_env()
    if not missing_fields(env):
        return env
    # Nothing usable configured — keep env values (all likely blank) but tell callers to stay on the
    # simulated adapter.
    return replace(env, source="none")


def missing_fields(cfg: ETAConfig) -> list[str]:
    """Internal field names still blank on ``cfg`` (auth-required only)."""
    return [f for f in REQUIRED_FIELDS if not str(getattr(cfg, f) or "").strip()]


def missing_setting_names(cfg: ETAConfig) -> list[str]:
    """The ``ETA_*`` names of the still-blank required fields — the operator-panel vocabulary."""
    return [FIELD_TO_SETTING[f] for f in missing_fields(cfg)]


# --- admin write path ---------------------------------------------------------------------------

_PLAIN_FIELDS = ("environment", "identity_url", "api_base_url", "client_id", "rin")


def apply_admin_update(data: dict, actor=None) -> "object":
    """Save validated admin input onto the singleton and return the fresh row.

    ``client_secret`` (if a non-empty value is present) is encrypted before storage; an absent or
    empty ``client_secret`` leaves the stored one untouched, and ``clear_secret`` removes it. Any
    change resets the in-process token cache so the next call re-authenticates with the new values.
    """
    from ..domain.models import ETASettings
    from . import eta_client

    row = ETASettings.load()
    for field in _PLAIN_FIELDS:
        if field in data:
            setattr(row, field, (data[field] or "").strip())
    if "enabled" in data:
        row.enabled = bool(data["enabled"])

    if data.get("clear_secret"):
        row.client_secret_encrypted = ""
    elif data.get("client_secret"):
        row.set_secret(data["client_secret"])

    row.save()
    # Credentials or environment may have changed — a cached token from the old config must not ride
    # along on the next request.
    eta_client.reset_cache()
    return row


def test_connection() -> dict:
    """Attempt an ETA token acquisition with the config in force. Returns an outcome dict carrying a
    reason code and a human detail — never a token, never the secret. On success, stamps
    ``last_test_ok_at`` on the row when the database is the config source."""
    from django.utils import timezone

    from ..domain.models import ETASettings
    from . import eta_client

    eta_client.reset_cache()
    try:
        eta_client.fetch_token(force=True)
    except eta_client.ETAConfigError as exc:
        return {"ok": False, "reason": "not_configured", "detail": str(exc)}
    except eta_client.ETAAuthError as exc:
        return {"ok": False, "reason": "auth_failed", "detail": str(exc)}

    row = ETASettings.objects.filter(pk=ETASettings._SINGLETON_PK).first()
    if row is not None and row.enabled:
        row.last_test_ok_at = timezone.now()
        row.save(update_fields=["last_test_ok_at", "updated_at"])
    return {"ok": True, "reason": "ok", "detail": "authenticated"}
