"""ETA document signing — CAdES-BES detached CMS over the canonical serialization.

ETA rejects an unsigned Invoice v1.0. A valid document carries a **detached CAdES-BES** signature
computed **not** over the raw JSON but over the canonical serialization (:mod:`canonical`), and its
structure has to match ETA's expectations exactly — a wrong OID or an extra attribute fails
validation the same way a wrong byte in the serialization does.

**The recipe** (verified 2026-07-21 against a production ETA-accepted signer — the Wadi reference in
``Docs/E-Invoice/`` — and recorded in DECISIONS "einvoice:" 2026-07-21):

* The CMS **content** is the UTF-8 canonical serialized string; its SHA-256 is
  :func:`canonical.signing_hash` — the value carried in the ``messageDigest`` signed attribute.
* Signed attributes, and only these (this is *BES* — no unsigned attrs, no timestamp):
  ``contentType`` = **digestedData** OID ``1.2.840.113549.1.7.5`` (ETA's quirk — deliberately *not*
  the default ``id-data``), ``messageDigest``, and ``SigningCertificateV2`` (ESSCertIDv2 / SHA-256).
  **No ``signingTime``** — the reference builds one and then drops it; we never add it.
* ``SHA256withRSA`` over the DER of the signed attributes; the signer certificate is embedded; the
  CMS is **detached** (no eContent). The result is base64-encoded into ``signatures[].value`` with
  ``signatureType = "I"`` (issuer).

**Key material lives outside the repo.** The signer is a PKCS#12 soft certificate (Option A,
founder-approved 2026-07-21 — a server-side soft cert, not the reference's hardware PKCS#11 USB
token, which cannot live on a Django host). It is sourced from settings — a file path
(``ETA_SIGNING_PFX_PATH``) or base64 (``ETA_SIGNING_PFX_BASE64``) plus ``ETA_SIGNING_PFX_PASSWORD``
— never committed, never logged, and kept isolated to this module so the private key never rides on
the config dataclass or the document dict. When no certificate is configured
(:func:`is_configured` is False) signing is skipped and ``signatures`` stays ``[]`` — the
simulated/unconfigured path, exactly as an install with no ETA connection.

We build the CMS with :mod:`asn1crypto` (the ASN.1 structures) and sign with :mod:`cryptography`
(PKCS#12 load + RSA/SHA-256). ``pyhanko`` is not used — it targets PDF signing and would add a large
dependency for structures asn1crypto already models directly.
"""
from __future__ import annotations

import base64
import hashlib

from django.conf import settings

from . import canonical

# The ETA "quirk": the signed contentType (and the detached eContentType) is digestedData, not the
# CMS default id-data. Everything hangs on this OID matching what ETA's validator expects.
DIGESTED_DATA_OID = "1.2.840.113549.1.7.5"


class ETASigningError(Exception):
    """Signing was attempted but the certificate/key material could not be loaded or used."""


def is_configured() -> bool:
    """True when a signing certificate is configured (a PKCS#12 path or base64 blob is present)."""
    return bool(
        str(getattr(settings, "ETA_SIGNING_PFX_BASE64", "") or "").strip()
        or str(getattr(settings, "ETA_SIGNING_PFX_PATH", "") or "").strip()
    )


def _material() -> tuple[bytes | None, bytes | None]:
    """Return ``(pkcs12_bytes, password_bytes)`` from settings, or ``(None, None)`` if unconfigured.

    Key material only — never returned upward past this module, never logged. A base64 blob wins over
    a path so a secret-manager value can override a stale on-disk file."""
    b64 = str(getattr(settings, "ETA_SIGNING_PFX_BASE64", "") or "").strip()
    path = str(getattr(settings, "ETA_SIGNING_PFX_PATH", "") or "").strip()
    password = getattr(settings, "ETA_SIGNING_PFX_PASSWORD", "") or ""

    pfx: bytes | None = None
    if b64:
        try:
            pfx = base64.b64decode(b64)
        except (ValueError, TypeError) as exc:
            raise ETASigningError("ETA_SIGNING_PFX_BASE64 is not valid base64.") from exc
    elif path:
        try:
            with open(path, "rb") as fh:
                pfx = fh.read()
        except OSError as exc:
            raise ETASigningError("The signing certificate at ETA_SIGNING_PFX_PATH could not be read.") from exc

    if pfx is None:
        return None, None
    return pfx, (password.encode("utf-8") if isinstance(password, str) else password)


def _load_signer(pfx: bytes, password: bytes | None):
    """Open the PKCS#12 → ``(private_key, certificate)`` (cryptography objects). Raises on any fault."""
    from cryptography.hazmat.primitives.serialization import pkcs12

    try:
        key, cert, _extra = pkcs12.load_key_and_certificates(pfx, password or None)
    except (ValueError, TypeError) as exc:
        raise ETASigningError("The signing certificate could not be opened (bad file or password).") from exc
    if key is None or cert is None:
        raise ETASigningError("The signing PKCS#12 is missing its private key or certificate.")
    return key, cert


def build_cades_bes(signing_hash: bytes, key, cert) -> bytes:
    """DER-encoded detached CAdES-BES CMS SignedData over ``signing_hash``.

    ``signing_hash`` is the SHA-256 of the canonical serialization — the digest the CMS content
    covers, carried verbatim in the ``messageDigest`` attribute. Pure ASN.1 assembly + one RSA
    signature; no I/O and no settings, so it is unit-testable with any key/cert pair."""
    from asn1crypto import algos, cms, tsp
    from asn1crypto import x509 as asn1_x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import Encoding

    cert_der = cert.public_bytes(Encoding.DER)
    asn1_cert = asn1_x509.Certificate.load(cert_der)
    cert_hash = hashlib.sha256(cert_der).digest()

    # SigningCertificateV2 — binds this exact signer cert into the signed attributes (ESSCertIDv2,
    # SHA-256 over the DER cert, plus the issuer/serial for an unambiguous reference).
    ess_cert_id = tsp.ESSCertIDv2({
        "cert_hash": cert_hash,
        "issuer_serial": tsp.IssuerSerial({
            "issuer": [asn1_x509.GeneralName({"directory_name": asn1_cert.issuer})],
            "serial_number": asn1_cert.serial_number,
        }),
    })
    signing_cert_v2 = tsp.SigningCertificateV2({"certs": [ess_cert_id]})

    # The signed attributes — the exact BES set, in the order ETA's reference emits them.
    signed_attrs = cms.CMSAttributes([
        cms.CMSAttribute({"type": "content_type", "values": [DIGESTED_DATA_OID]}),
        cms.CMSAttribute({"type": "message_digest", "values": [signing_hash]}),
        cms.CMSAttribute({"type": "signing_certificate_v2", "values": [signing_cert_v2]}),
    ])

    # Sign the DER of the SignedAttributes as a SET OF (0x31) — CMSAttributes.dump() yields that
    # universal-SET encoding; the implicit [0] tag is applied only once it is placed in the SignerInfo.
    signature = key.sign(signed_attrs.dump(), padding.PKCS1v15(), hashes.SHA256())

    signer_info = cms.SignerInfo({
        "version": "v1",
        "sid": cms.SignerIdentifier({
            "issuer_and_serial_number": cms.IssuerAndSerialNumber({
                "issuer": asn1_cert.issuer,
                "serial_number": asn1_cert.serial_number,
            }),
        }),
        "digest_algorithm": algos.DigestAlgorithm({"algorithm": "sha256"}),
        "signed_attrs": signed_attrs,
        "signature_algorithm": algos.SignedDigestAlgorithm({"algorithm": "rsassa_pkcs1v15"}),
        "signature": signature,
    })

    signed_data = cms.SignedData({
        "version": "v1",
        "digest_algorithms": [algos.DigestAlgorithm({"algorithm": "sha256"})],
        # Detached: eContentType names digestedData (matching the contentType attr), eContent omitted.
        "encap_content_info": {"content_type": DIGESTED_DATA_OID},
        "certificates": [asn1_cert],
        "signer_infos": [signer_info],
    })
    return cms.ContentInfo({"content_type": "signed_data", "content": signed_data}).dump()


def sign_hash(signing_hash: bytes) -> str:
    """Base64 CAdES-BES CMS over ``signing_hash`` with the configured certificate.

    Raises :class:`ETASigningError` when no certificate is configured — callers guard with
    :func:`is_configured` (or :func:`build_signatures`, which returns ``[]`` instead)."""
    pfx, password = _material()
    if pfx is None:
        raise ETASigningError("No signing certificate is configured.")
    key, cert = _load_signer(pfx, password)
    return base64.b64encode(build_cades_bes(signing_hash, key, cert)).decode("ascii")


def build_signatures(document: dict) -> list[dict]:
    """The ETA ``signatures`` array for ``document``.

    One issuer (``"I"``) CAdES-BES signature over the document's canonical serialization when a
    signing certificate is configured; ``[]`` on the unconfigured/simulated path (an unsigned
    document ETA would reject — but nothing reaches ETA until a certificate is in place)."""
    if not is_configured():
        return []
    return [{"signatureType": "I", "value": sign_hash(canonical.signing_hash(document))}]
