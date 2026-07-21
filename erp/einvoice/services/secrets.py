"""Encryption-at-rest for the ETA client secret (einvoice-eta-live, admin-config pivot).

The client secret is the one ETA setting that must never be stored or returned in clear text. Admin
enters it once through the settings screen; from that moment it lives in the database **encrypted**
and is only ever decrypted in-process, at the moment a token is fetched. It is never serialized back
to the browser, never logged, never placed in an error message.

**Key.** Fernet (AES-128-CBC + HMAC, authenticated) with a key resolved in this order:

1. ``settings.ETA_SECRET_KEY`` — an explicit 44-char url-safe base64 Fernet key from the environment.
   Set this in production so the ciphertext survives a ``DJANGO_SECRET_KEY`` rotation.
2. Otherwise a key **derived** from ``settings.SECRET_KEY`` so a fresh install works with no extra
   configuration. The tradeoff is explicit: rotating ``DJANGO_SECRET_KEY`` then makes the stored
   secret undecryptable (the admin simply re-enters it). Prod installs should set ``ETA_SECRET_KEY``.

``cryptography`` is a direct dependency as of this pivot (DECISIONS 2026-07-21) — the founder chose
encrypted-at-rest storage, and that choice needs a real cipher. It was already present (transitively
via other packages) and is the Python standard for this.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class ETASecretError(RuntimeError):
    """The stored secret could not be decrypted (wrong/rotated key). Never carries the value."""


def _fernet() -> Fernet:
    explicit = str(getattr(settings, "ETA_SECRET_KEY", "") or "").strip()
    if explicit:
        return Fernet(explicit.encode("utf-8"))
    # Derive a stable Fernet key from the Django secret. Namespaced so it can never collide with any
    # other secret-derived key we might add later.
    digest = hashlib.sha256(f"eta-config-secret::{settings.SECRET_KEY}".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(raw: str) -> str:
    """Return the ciphertext (url-safe text) for a plaintext secret. Empty in → empty out."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    return _fernet().encrypt(raw.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Return the plaintext for a stored ciphertext. Empty in → empty out.

    Raises :class:`ETASecretError` if the ciphertext cannot be authenticated with the current key
    (typically because ``DJANGO_SECRET_KEY`` rotated while no ``ETA_SECRET_KEY`` was set).
    """
    token = (token or "").strip()
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        raise ETASecretError(
            "The stored ETA client secret could not be decrypted — re-enter it in settings."
        ) from None
