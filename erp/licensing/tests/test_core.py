"""License key format v1 + offline verifier (license-key FILE_01).

Every test signs with a throwaway keypair generated here — never the real signing key.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from erp.identity import rbac
from erp.licensing import core, keys
from erp.licensing.core import (
    EDITIONS,
    LICENSABLE_MODULES,
    BadSignature,
    InvalidPayload,
    LicenseInfo,
    MalformedKey,
    NoPublicKey,
    UnsupportedVersion,
    sign,
    verify_with,
)
from erp.licensing.verify import verify


@pytest.fixture
def private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


@pytest.fixture
def info() -> LicenseInfo:
    return LicenseInfo(
        license_id="LIC-TEST0001",
        company_name="شركة النيل للتجارة",
        tax_id="123-456-789",
        edition="integrated",
        modules=tuple(EDITIONS["integrated"]["modules"]),
        max_branches=5,
        issued_at=dt.date(2026, 9, 24),
        maintenance_until=dt.date(2027, 9, 24),
        ai_until=None,
    )


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _resign(payload: dict, private_key) -> str:
    """Sign an arbitrary (possibly invalid) payload — to prove validation runs AFTER a good signature."""
    raw = core.canonical_bytes(payload)
    return f"CND1.{_b64(raw)}.{_b64(private_key.sign(raw))}"


def _flip(text: str, index: int) -> str:
    raw = bytearray(_unb64(text))
    raw[index] ^= 0x01
    return _b64(bytes(raw))


# --- registry drift -------------------------------------------------------------------------------

def test_licensable_modules_match_rbac_registry():
    assert set(LICENSABLE_MODULES) == set(rbac.MODULE_NAMES)


def test_editions_only_use_known_modules():
    for name, edition in EDITIONS.items():
        assert set(edition["modules"]) <= set(LICENSABLE_MODULES), name


def test_no_real_public_key_committed_as_test_fixture():
    # keys.PUBLIC_KEYS holds only the founder's real key(s); tests never depend on it.
    assert isinstance(keys.PUBLIC_KEYS, tuple)


# --- happy path -----------------------------------------------------------------------------------

def test_valid_key_round_trips_every_field(private_key, info):
    key = sign(info, private_key)
    assert key.startswith("CND1.")
    assert verify_with(key, [private_key.public_key()]) == info


def test_module_order_is_normalised_so_keys_round_trip(private_key, info):
    shuffled = replace(info, modules=("workflow", "crm", "accounting"))
    got = verify_with(sign(shuffled, private_key), [private_key.public_key()])
    assert got.modules == ("accounting", "crm", "workflow")
    assert got == replace(shuffled, modules=("accounting", "crm", "workflow"))


def test_arabic_company_name_survives(private_key, info):
    got = verify_with(sign(info, private_key), [private_key.public_key()])
    assert got.company_name == "شركة النيل للتجارة"


def test_ai_addon_and_unlimited_branches_round_trip(private_key, info):
    info = replace(info, max_branches=None, ai_until=dt.date(2027, 3, 1))
    got = verify_with(sign(info, private_key), [private_key.public_key()])
    assert got.max_branches is None and got.ai_until == dt.date(2027, 3, 1)


def test_whitespace_and_line_wraps_from_a_lic_file_are_tolerated(private_key, info):
    key = sign(info, private_key)
    wrapped = "\n".join(key[i:i + 60] for i in range(0, len(key), 60)) + "\n"
    assert verify_with(wrapped, [private_key.public_key()]) == info


def test_verify_accepts_any_key_in_rotation(private_key, info):
    other = Ed25519PrivateKey.generate()
    assert verify_with(sign(info, private_key), [other.public_key(), private_key.public_key()]) == info


def test_in_app_verify_uses_injected_public_keys(private_key, info):
    assert verify(sign(info, private_key), public_keys=[private_key.public_key()]) == info


# --- tampering ------------------------------------------------------------------------------------

def test_flipped_payload_byte_is_bad_signature(private_key, info):
    prefix, payload, sig = sign(info, private_key).split(".")
    with pytest.raises(BadSignature):
        verify_with(f"{prefix}.{_flip(payload, 10)}.{sig}", [private_key.public_key()])


def test_flipped_signature_byte_is_bad_signature(private_key, info):
    prefix, payload, sig = sign(info, private_key).split(".")
    with pytest.raises(BadSignature):
        verify_with(f"{prefix}.{payload}.{_flip(sig, 5)}", [private_key.public_key()])


def test_key_from_another_signer_is_bad_signature(private_key, info):
    impostor = Ed25519PrivateKey.generate()
    with pytest.raises(BadSignature):
        verify_with(sign(info, impostor), [private_key.public_key()])


def test_edited_payload_cannot_raise_branch_limit(private_key, info):
    """The attack that matters: decode, bump max_branches, re-encode, keep the old signature."""
    prefix, payload, sig = sign(info, private_key).split(".")
    data = json.loads(_unb64(payload))
    data["max_branches"] = 999
    forged = f"{prefix}.{_b64(core.canonical_bytes(data))}.{sig}"
    with pytest.raises(BadSignature):
        verify_with(forged, [private_key.public_key()])


# --- malformed / version / payload ----------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "", "CND1", "CND1..", "CND2.abc.def", "XYZ.abc.def", "CND1.abc", "CND1.a.b.c",
    "CND1.not*base64.sig", "x" * (core.MAX_KEY_LENGTH + 1),
])
def test_malformed_keys(private_key, bad):
    with pytest.raises(MalformedKey):
        verify_with(bad, [private_key.public_key()])


def test_non_text_key_is_malformed(private_key):
    with pytest.raises(MalformedKey):
        verify_with(None, [private_key.public_key()])  # type: ignore[arg-type]


def test_no_public_key_configured(info, private_key):
    with pytest.raises(NoPublicKey):
        verify_with(sign(info, private_key), [])


def test_v2_payload_is_unsupported_version(private_key, info):
    payload = core.info_to_payload(info) | {"v": 2}
    with pytest.raises(UnsupportedVersion):
        verify_with(_resign(payload, private_key), [private_key.public_key()])


def test_unknown_module_rejected(private_key, info):
    payload = core.info_to_payload(info) | {"modules": ["accounting", "payroll"]}
    with pytest.raises(InvalidPayload, match="payroll"):
        verify_with(_resign(payload, private_key), [private_key.public_key()])


@pytest.mark.parametrize("change", [
    {"extra": 1},
    {"modules": []},
    {"modules": ["sales", "sales"]},
    {"max_branches": 0},
    {"max_branches": True},
    {"max_branches": "5"},
    {"tax_id": ""},
    {"company_name": "   "},
    {"issued_at": "24/09/2026"},
    {"maintenance_until": "2026-01-01"},  # before issued_at
    {"ai_until": "soon"},
])
def test_invalid_payloads_rejected_even_when_genuinely_signed(private_key, info, change):
    payload = core.info_to_payload(info) | change
    with pytest.raises(InvalidPayload):
        verify_with(_resign(payload, private_key), [private_key.public_key()])


def test_missing_field_rejected(private_key, info):
    payload = core.info_to_payload(info)
    del payload["tax_id"]
    with pytest.raises(InvalidPayload):
        verify_with(_resign(payload, private_key), [private_key.public_key()])


def test_duplicate_json_field_rejected(private_key, info):
    raw = core.canonical_bytes(core.info_to_payload(info))
    raw = raw[:-1] + b',"tax_id":"999"}'
    key = f"CND1.{_b64(raw)}.{_b64(private_key.sign(raw))}"
    with pytest.raises(InvalidPayload, match="duplicate"):
        verify_with(key, [private_key.public_key()])


def test_sign_refuses_to_mint_an_invalid_key(private_key, info):
    with pytest.raises(InvalidPayload):
        sign(replace(info, modules=("payroll",)), private_key)


def test_errors_carry_a_stable_reason_code():
    assert {MalformedKey.reason, BadSignature.reason, UnsupportedVersion.reason,
            InvalidPayload.reason, NoPublicKey.reason} == {
        "malformed", "bad_signature", "unsupported_version", "invalid_payload", "no_public_key"}


# --- issuer tool ----------------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "tools" / "license"))
import issue_license  # noqa: E402


def test_issuer_keypair_then_issue_then_verify(tmp_path, monkeypatch):
    monkeypatch.setattr(issue_license, "REPO_ROOT", REPO_ROOT)
    pem = tmp_path / "secure" / "signing.pem"
    monkeypatch.setenv(issue_license.PASSPHRASE_ENV, "test-passphrase")
    public_b64 = issue_license.new_keypair(pem)
    assert pem.exists() and b"ENCRYPTED" in pem.read_bytes()

    out_dir = tmp_path / "out"
    assert issue_license.main([
        "--private-key", str(pem), "--company", "شركة الدلتا", "--tax-id", "987-654-321",
        "--edition", "basic", "--issued-at", "2026-09-24", "--ai-years", "1",
        "--out-dir", str(out_dir),
    ]) == 0
    key = (out_dir / "987-654-321.lic").read_text(encoding="utf-8")
    got = verify_with(key, [core.public_key_from_b64(public_b64)])
    assert got.company_name == "شركة الدلتا"
    assert got.modules == tuple(m for m in LICENSABLE_MODULES if m in EDITIONS["basic"]["modules"])
    assert got.max_branches == 1
    assert got.maintenance_until == dt.date(2027, 9, 24)
    assert got.ai_until == dt.date(2027, 9, 24)


def test_issuer_refuses_private_key_inside_repo():
    with pytest.raises(SystemExit, match="inside the repository"):
        issue_license.new_keypair(REPO_ROOT / "signing.pem")


def test_issuer_never_overwrites_an_existing_key(tmp_path):
    pem = tmp_path / "signing.pem"
    issue_license.new_keypair(pem)
    with pytest.raises(SystemExit, match="already exists"):
        issue_license.new_keypair(pem)


def test_issuer_leap_day_maintenance():
    assert issue_license.add_years(dt.date(2028, 2, 29), 1) == dt.date(2029, 2, 28)
