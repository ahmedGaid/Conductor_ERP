"""License key format v1 — pure, dependency-light, Django-free.

A key is ``CND1.<payload>.<signature>``: base64url (no padding) of the canonical JSON payload,
then base64url of an Ed25519 signature over those exact payload bytes. The public key ships in
``keys.py``; the private key never leaves the founder's machine (``tools/license/``).

This module imports nothing from Django or the rest of ``erp`` on purpose: the founder-only issuer
tool imports it directly, outside any Django process. ``erp.licensing.verify`` is the in-app entry
point that adds the configured public keys.
"""
from __future__ import annotations

import base64
import binascii
import datetime as _dt
import json
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

PREFIX = "CND1"
PAYLOAD_VERSION = 1
# A real key is ~400 bytes; anything far larger is garbage or an attempt to make us parse a lot.
MAX_KEY_LENGTH = 8192

# Must equal ``erp.identity.rbac.MODULE_NAMES`` — duplicated so this file stays Django-free;
# ``tests/test_core.py`` fails the build if the two ever drift apart.
LICENSABLE_MODULES: tuple[str, ...] = (
    "accounting", "inventory", "sales", "purchasing", "crm", "einvoice",
    "notifications", "workflow", "administration",
)

def _in_registry_order(names: set[str]) -> tuple[str, ...]:
    return tuple(m for m in LICENSABLE_MODULES if m in names)


_BASIC = {"accounting", "inventory", "sales", "purchasing", "einvoice", "notifications",
          "administration"}
# Edition = a named default for the issuer. The verifier never trusts the edition name — only the
# signed ``modules`` list and ``max_branches`` shape what an install may do.
EDITIONS: dict[str, dict] = {
    "basic": {"modules": _in_registry_order(_BASIC), "max_branches": 1},
    "integrated": {"modules": _in_registry_order(_BASIC | {"crm", "workflow"}), "max_branches": 5},
    "enterprise": {"modules": LICENSABLE_MODULES, "max_branches": None},
}

_FIELDS = frozenset({
    "v", "license_id", "company_name", "tax_id", "edition", "modules", "max_branches",
    "issued_at", "maintenance_until", "ai_until",
})


class LicenseKeyError(Exception):
    """Why a key was rejected. ``reason`` is a stable machine code the app maps to calm copy."""

    reason = "invalid"

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(f"{self.reason}: {detail}" if detail else self.reason)


class MalformedKey(LicenseKeyError):
    reason = "malformed"


class BadSignature(LicenseKeyError):
    reason = "bad_signature"


class UnsupportedVersion(LicenseKeyError):
    reason = "unsupported_version"


class InvalidPayload(LicenseKeyError):
    reason = "invalid_payload"


class NoPublicKey(LicenseKeyError):
    reason = "no_public_key"


@dataclass(frozen=True)
class LicenseInfo:
    license_id: str
    company_name: str
    tax_id: str
    edition: str
    modules: tuple[str, ...]
    max_branches: int | None  # None = unlimited
    issued_at: _dt.date
    maintenance_until: _dt.date
    ai_until: _dt.date | None  # None = no AI add-on


# --- encoding -------------------------------------------------------------------------------------

def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


_B64_ALPHABET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def _b64decode(text: str) -> bytes:
    if not text or any(c not in _B64_ALPHABET for c in text):
        raise MalformedKey("not base64url")
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as exc:
        raise MalformedKey("not base64url") from exc


def canonical_bytes(payload: dict) -> bytes:
    """The one byte form that gets signed: sorted keys, no whitespace, UTF-8 (Arabic kept as-is)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _no_duplicate_keys(pairs: list[tuple]) -> dict:
    seen: dict = {}
    for key, value in pairs:
        if key in seen:
            raise InvalidPayload(f"duplicate field {key!r}")
        seen[key] = value
    return seen


# --- payload validation ---------------------------------------------------------------------------

def _text(payload: dict, name: str, max_len: int) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip() or len(value) > max_len:
        raise InvalidPayload(f"{name} must be a non-empty string (max {max_len})")
    return value.strip()


def _optional_date(payload: dict, name: str) -> _dt.date | None:
    return None if payload.get(name) is None else _date(payload, name)


def _date(payload: dict, name: str) -> _dt.date:
    value = payload.get(name)
    if not isinstance(value, str):
        raise InvalidPayload(f"{name} must be an ISO date")
    try:
        return _dt.date.fromisoformat(value)
    except ValueError as exc:
        raise InvalidPayload(f"{name} must be an ISO date") from exc


def payload_to_info(payload: dict) -> LicenseInfo:
    """Strictly validate a decoded payload. Unknown or missing fields are rejected — a v1 key
    means exactly this shape, so a later format can never be half-read as v1."""
    if not isinstance(payload, dict):
        raise InvalidPayload("payload must be an object")
    if payload.get("v") != PAYLOAD_VERSION:
        raise UnsupportedVersion(f"payload version {payload.get('v')!r}")
    keys = set(payload)
    if keys != _FIELDS:
        missing, extra = sorted(_FIELDS - keys), sorted(keys - _FIELDS)
        raise InvalidPayload(f"fields missing={missing} unexpected={extra}")

    modules = payload["modules"]
    if (not isinstance(modules, list) or not modules
            or not all(isinstance(m, str) for m in modules) or len(set(modules)) != len(modules)):
        raise InvalidPayload("modules must be a non-empty list of unique names")
    unknown = sorted(set(modules) - set(LICENSABLE_MODULES))
    if unknown:
        raise InvalidPayload(f"unknown modules {unknown}")

    max_branches = payload["max_branches"]
    # bool is an int subclass — reject it explicitly so `true` can't mean "1 branch".
    if max_branches is not None and (
        isinstance(max_branches, bool) or not isinstance(max_branches, int) or max_branches < 1
    ):
        raise InvalidPayload("max_branches must be a positive integer or null")

    issued_at = _date(payload, "issued_at")
    maintenance_until = _date(payload, "maintenance_until")
    ai_until = _optional_date(payload, "ai_until")
    if maintenance_until < issued_at:
        raise InvalidPayload("maintenance_until is before issued_at")

    return LicenseInfo(
        license_id=_text(payload, "license_id", 64),
        company_name=_text(payload, "company_name", 200),
        tax_id=_text(payload, "tax_id", 32),
        edition=_text(payload, "edition", 32),
        # Kept in canonical registry order so two keys with the same modules compare equal.
        modules=_in_registry_order(set(modules)),
        max_branches=max_branches,
        issued_at=issued_at,
        maintenance_until=maintenance_until,
        ai_until=ai_until,
    )


def info_to_payload(info: LicenseInfo) -> dict:
    return {
        "v": PAYLOAD_VERSION,
        "license_id": info.license_id,
        "company_name": info.company_name,
        "tax_id": info.tax_id,
        "edition": info.edition,
        "modules": list(info.modules),
        "max_branches": info.max_branches,
        "issued_at": info.issued_at.isoformat(),
        "maintenance_until": info.maintenance_until.isoformat(),
        "ai_until": info.ai_until.isoformat() if info.ai_until else None,
    }


# --- sign / verify --------------------------------------------------------------------------------

def sign(info: LicenseInfo, private_key: Ed25519PrivateKey) -> str:
    """Issue a key string. Round-trips the payload through validation first, so the issuer can
    never mint a key the verifier would reject."""
    # Validate AND normalise (module order) first, so the signed bytes are exactly what the
    # verifier hands back — a key round-trips to an equal LicenseInfo.
    raw = canonical_bytes(info_to_payload(payload_to_info(info_to_payload(info))))
    return f"{PREFIX}.{_b64encode(raw)}.{_b64encode(private_key.sign(raw))}"


def public_key_from_b64(text: str) -> Ed25519PublicKey:
    raw = _b64decode(text.strip())
    if len(raw) != 32:
        raise ValueError("an Ed25519 public key is 32 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)


def public_key_to_b64(key: Ed25519PublicKey) -> str:
    from cryptography.hazmat.primitives import serialization

    return _b64encode(key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def verify_with(key: str, public_keys: list[Ed25519PublicKey] | tuple[Ed25519PublicKey, ...]) -> LicenseInfo:
    """Verify ``key`` against any of ``public_keys`` (several allowed for key rotation).

    Pure: no clock, no DB. Dates are returned for the caller to compare. Raises a
    ``LicenseKeyError`` subclass on every failure — never a raw traceback.
    """
    if not public_keys:
        raise NoPublicKey("no license public key is configured")
    if not isinstance(key, str):
        raise MalformedKey("key must be text")
    key = "".join(key.split())  # tolerate line wraps / spaces from copy-paste or a .lic file
    if len(key) > MAX_KEY_LENGTH:
        raise MalformedKey("key too long")
    parts = key.split(".")
    if len(parts) != 3 or parts[0] != PREFIX:
        raise MalformedKey(f"expected {PREFIX}.<payload>.<signature>")
    raw, signature = _b64decode(parts[1]), _b64decode(parts[2])

    # Signature BEFORE parsing: unsigned bytes never reach the JSON parser.
    for public_key in public_keys:
        try:
            public_key.verify(signature, raw)
            break
        except InvalidSignature:
            continue
    else:
        raise BadSignature("signature does not match")

    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidPayload("payload is not JSON") from exc
    return payload_to_info(payload)
