"""FILE_03 — ETA CAdES-BES document signing.

Signing correctness is pass/fail against ETA's validator, which we cannot reach offline. These tests
prove the *structure* is exactly the recipe (digestedData contentType, messageDigest == the canonical
hash, SigningCertificateV2, no signingTime, detached, cert embedded) and that the signature is a
real RSA/SHA-256 signature over the signed attributes — verified back with the public key, and shown
to break when a byte is tampered. A self-signed cert is generated in-memory so no key material lives
in the repo.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib

import pytest
from django.test import override_settings

from erp.einvoice.services import canonical, signing
from erp.einvoice.services.eta_adapter import build_document

asn1crypto_cms = pytest.importorskip("asn1crypto.cms")
from asn1crypto import cms  # noqa: E402
from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import padding, rsa  # noqa: E402
from cryptography.hazmat.primitives.serialization import pkcs12 as _pkcs12mod  # noqa: E402
from cryptography.x509.oid import NameOID  # noqa: E402


def _self_signed():
    """An in-memory RSA key + self-signed cert — test-only material, never persisted."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ETA Signing Test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime(2026, 1, 1))
        .not_valid_after(dt.datetime(2030, 1, 1))
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _pkcs12(key, cert) -> bytes:
    return _pkcs12mod.serialize_key_and_certificates(
        name=b"eta", key=key, cert=cert, cas=None,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _attr(signer_info, attr_type):
    for attr in signer_info["signed_attrs"]:
        if attr["type"].native == attr_type:
            return attr["values"]
    return None


# --- CMS structure (the recipe) ------------------------------------------------------------------

def test_cades_bes_structure_matches_recipe():
    key, cert = _self_signed()
    digest = hashlib.sha256(b"canonical-string").digest()

    der = signing.build_cades_bes(digest, key, cert)
    ci = cms.ContentInfo.load(der)
    assert ci["content_type"].native == "signed_data"

    sd = ci["content"]
    eci = sd["encap_content_info"]
    # The ETA quirk: content type is digestedData, not id-data — on both the eContentType …
    assert eci["content_type"].dotted == signing.DIGESTED_DATA_OID
    assert eci["content"].native is None            # detached — no embedded content
    assert len(sd["certificates"]) == 1             # signer cert embedded

    si = sd["signer_infos"][0]
    # … and the signed contentType attribute.
    assert _attr(si, "content_type")[0].dotted == signing.DIGESTED_DATA_OID
    assert _attr(si, "message_digest")[0].native == digest
    assert _attr(si, "signing_certificate_v2") is not None
    assert _attr(si, "signing_time") is None        # BES — no timestamp
    assert si["signature_algorithm"]["algorithm"].native == "rsassa_pkcs1v15"
    assert si["digest_algorithm"]["algorithm"].native == "sha256"


def test_signature_verifies_and_tamper_breaks_it():
    key, cert = _self_signed()
    digest = hashlib.sha256(b"the-canonical-serialization").digest()

    si = cms.ContentInfo.load(signing.build_cades_bes(digest, key, cert))["content"]["signer_infos"][0]
    # Re-encode the signed attributes as the SET OF (0x31) that was actually signed, and verify.
    signed_der = si["signed_attrs"].untag().dump()
    cert.public_key().verify(si["signature"].native, signed_der, padding.PKCS1v15(), hashes.SHA256())

    with pytest.raises(Exception):
        cert.public_key().verify(
            si["signature"].native, signed_der + b"\x00", padding.PKCS1v15(), hashes.SHA256())


def test_message_digest_is_the_canonical_hash():
    # messageDigest must equal signing_hash of the exact document body ETA serializes.
    key, cert = _self_signed()
    doc = {"internalId": "INV-9", "totalAmount": 100.0, "signatures": []}
    digest = canonical.signing_hash(doc)

    si = cms.ContentInfo.load(signing.build_cades_bes(digest, key, cert))["content"]["signer_infos"][0]
    assert _attr(si, "message_digest")[0].native == digest


# --- configuration gate --------------------------------------------------------------------------

def test_unconfigured_yields_no_signatures():
    # No cert configured → signing skipped, signatures empty (simulated/unconfigured path).
    assert signing.is_configured() is False
    assert signing.build_signatures({"internalId": "INV-1"}) == []


def test_sign_hash_without_cert_raises():
    with pytest.raises(signing.ETASigningError):
        signing.sign_hash(hashlib.sha256(b"x").digest())


def _cfg():
    from types import SimpleNamespace
    return SimpleNamespace(rin="123456789", issuer_name="Acme LLC", activity_code="4610",
                           branch_id="0", country="EG")


def _inv():
    return dict(invoice="INV-1", customer="CUST1", customer_name="Beta Co", date="2026-06-16",
                currency="EGP", net=1500_00, tax=210_00, total=1710_00)


def test_build_document_signs_when_configured():
    key, cert = _self_signed()
    pfx_b64 = base64.b64encode(_pkcs12(key, cert)).decode("ascii")

    with override_settings(ETA_SIGNING_PFX_BASE64=pfx_b64, ETA_SIGNING_PFX_PASSWORD=""):
        assert signing.is_configured() is True
        doc = build_document(_inv(), _cfg())

        assert len(doc["signatures"]) == 1
        sig = doc["signatures"][0]
        assert sig["signatureType"] == "I"

        # The embedded signature is a real CAdES-BES CMS over this document's canonical hash.
        si = cms.ContentInfo.load(base64.b64decode(sig["value"]))["content"]["signer_infos"][0]
        expected = canonical.signing_hash({k: v for k, v in doc.items() if k != "signatures"})
        assert _attr(si, "message_digest")[0].native == expected


def test_build_document_unsigned_when_not_configured():
    # The pure-mapping default: no cert → the shape/totals tests keep seeing signatures == [].
    assert build_document(_inv(), _cfg())["signatures"] == []
