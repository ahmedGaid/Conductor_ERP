"""In-app license verification: ``verify(key)`` against the configured public keys.

Thin wrapper over ``core.verify_with`` — the only thing it adds is where the public keys come
from (``keys.PUBLIC_KEYS``). Enforcement and the install/trial state live in later files.
"""
from __future__ import annotations

from . import keys
from .core import LicenseInfo, public_key_from_b64, verify_with


def configured_public_keys() -> list:
    return [public_key_from_b64(k) for k in keys.PUBLIC_KEYS]


def verify(key: str, *, public_keys: list | None = None) -> LicenseInfo:
    """``LicenseInfo`` for a genuine key; raises a ``core.LicenseKeyError`` subclass otherwise.

    ``public_keys`` overrides the configured ones (tests use a throwaway keypair).
    """
    return verify_with(key, configured_public_keys() if public_keys is None else public_keys)
