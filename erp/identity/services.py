"""Identity services: authentication, JWT issuance, and TOTP 2FA.

Business logic lives here (not in views). Views are thin and validate input only.
"""
from __future__ import annotations

import pyotp
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from erp.audit import services as audit
from erp.core.errors import ValidationError

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
