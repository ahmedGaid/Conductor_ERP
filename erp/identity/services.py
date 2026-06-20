"""Identity services: authentication, JWT issuance, and TOTP 2FA.

Business logic lives here (not in views). Views are thin and validate input only.
"""
from __future__ import annotations

import pyotp
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from erp.audit import services as audit
from erp.core.errors import ValidationError

from .models import OrgPreferences, UserPreferences

User = get_user_model()

ISSUER = "General ERP"


def issue_tokens(user) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def authenticate_user(username: str, password: str):
    """Return the user on valid credentials, else None."""
    return authenticate(username=username, password=password)


# --- TOTP 2FA ---

def provision_totp(user) -> str:
    """Generate (or reset) a TOTP secret for the user and return the otpauth:// URI."""
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.save(update_fields=["totp_secret"])
    return pyotp.totp.TOTP(secret).provisioning_uri(name=user.email or user.username, issuer_name=ISSUER)


def verify_totp(user, code: str) -> bool:
    if not user.totp_secret:
        return False
    return pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)


def enable_2fa(user, code: str) -> None:
    if not verify_totp(user, code):
        raise ValidationError("Invalid 2FA code")
    user.is_2fa_enabled = True
    user.save(update_fields=["is_2fa_enabled"])


def login(username: str, password: str, otp_code: str | None = None) -> dict:
    """Single entry point for login.

    Returns either {"twofa_required": True} (when 2FA is on and no/invalid code yet) or the token
    pair. Records an audit entry for every attempt.
    """
    user = authenticate_user(username, password)
    if user is None:
        audit.record(
            module="identity",
            action="login",
            entity_type="User",
            entity_id=username,
            result="failure",
            after={"reason": "bad_credentials"},
        )
        raise ValidationError("Invalid username or password")

    if user.is_2fa_enabled:
        if not otp_code or not verify_totp(user, otp_code):
            audit.record(
                module="identity",
                action="login_2fa_challenge",
                entity_type="User",
                entity_id=user.pk,
                actor=user,
            )
            return {"twofa_required": True}

    tokens = issue_tokens(user)
    audit.record(
        module="identity",
        action="login",
        entity_type="User",
        entity_id=user.pk,
        actor=user,
    )
    return tokens


# --- Personalization ---------------------------------------------------------------------------
#
# Preference rows are created lazily so existing users (and the auth path) are unaffected. The
# "effective" view merges org defaults under the user's personal overrides — the shape the
# frontend applies to <html data-*> on load.

# Personal fields that inherit from the org row when left blank.
_INHERITABLE = {
    "preferred_language": "default_language",
    "theme": "default_theme",
    "accent_color": "default_accent",
    "default_landing": "default_landing",
}


def get_org_preferences() -> OrgPreferences:
    """The single org-defaults row (pk=1), created on first access."""
    org, _ = OrgPreferences.objects.get_or_create(pk=1)
    return org


def get_preferences(user) -> UserPreferences:
    """The user's personalization row, created with product defaults on first access."""
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    return prefs


def update_preferences(user, changes: dict) -> UserPreferences:
    prefs = get_preferences(user)
    for field, value in changes.items():
        setattr(prefs, field, value)
    prefs.save()
    audit.record(
        module="identity",
        action="update_preferences",
        entity_type="UserPreferences",
        entity_id=user.pk,
        actor=user,
        after={"fields": sorted(changes)},
    )
    return prefs


def update_org_preferences(actor, changes: dict) -> OrgPreferences:
    org = get_org_preferences()
    for field, value in changes.items():
        setattr(org, field, value)
    org.save()
    audit.record(
        module="identity",
        action="update_org_preferences",
        entity_type="OrgPreferences",
        entity_id=org.pk,
        actor=actor,
        after={"fields": sorted(changes)},
    )
    return org


def effective_preferences(user) -> dict:
    """Personal preferences with org defaults filled in for blank inheritable fields."""
    from .serializers import UserPreferencesSerializer  # local import avoids a cycle

    prefs = get_preferences(user)
    org = get_org_preferences()
    data = UserPreferencesSerializer(prefs).data
    for personal_field, org_field in _INHERITABLE.items():
        if not data.get(personal_field):
            data[personal_field] = getattr(org, org_field)
    if not data.get("default_landing"):
        data["default_landing"] = "/"
    return data
