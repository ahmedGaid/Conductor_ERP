"""ETA document serialization — the canonical string a signature is computed over.

Before an invoice is signed, ETA does **not** sign the raw JSON. It signs a *canonical
serialization* of the document, and the signature is only valid if our serialization is
byte-for-byte what ETA's own serializer produces. Get one character wrong and the Tax
Authority rejects the document as ``INVALID`` — a failure only visible at live submission.
So this module implements ETA's published algorithm exactly, and is pinned by golden tests.

**The algorithm** (https://sdk.invoicing.eta.gov.eg/document-serialization-approach/, verified
2026-07-21):

* Every **property name** is emitted in double quotes, converted to *culture-invariant
  uppercase* — ``id`` → ``"ID"``.
* An **object** is the concatenation of its properties, each ``"NAME"`` immediately followed
  by the serialization of its value, in document order.
* A **simple value** (string, number, bool) is emitted verbatim — exactly as it appears on
  the wire — enclosed in double quotes: ``100.0`` → ``"100.0"``, ``"Widget"`` → ``"Widget"``.
* An **array** repeats the property name once as the array marker and then **again before
  each element**::

      "TAXABLEITEMS" "TAXABLEITEMS" <item-1>  "TAXABLEITEMS" <item-2> …

  (The reference desktop signer serialized from XML, where the child tag is *singular*
  — ``TAXABLEITEM``. Our transport is JSON, so the **plural** property name repeats. This is
  the one place the two variants diverge, and the reason we follow the JSON spec, not the
  XML one.)
* Quotes inside a value are escaped ``\\"`` — standard JSON string escaping.

**The signatures array is excluded.** A document is serialized *without* its ``signatures``
property (you cannot sign the signature), matching the reference signer that cut the
serialized string off at ``"SIGNATURES"``.

Numbers are rendered with :func:`json.dumps`, the same encoder :mod:`eta_client` uses to put
the document on the wire, so the serialized token and the submitted token can never drift.
"""
from __future__ import annotations

import hashlib
import json


def _quote(text: str) -> str:
    """Enclose ``text`` in double quotes with JSON-standard escaping of ``\\`` and ``"``."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _leaf_token(value) -> str:
    """A simple value as its quoted canonical token.

    Strings carry through :func:`json.dumps` (which already quotes and escapes them, and keeps
    non-ASCII characters intact). Numbers and booleans are rendered to their **wire** token —
    the exact text ETA receives — and then wrapped in quotes, because ETA encloses simple
    values of every type in double quotes (``14.0`` → ``"14.0"``, ``true`` → ``"true"``)."""
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        # A null-valued property should not reach serialization (build_document omits empties);
        # if one does, treat it as an empty string so the output stays deterministic.
        return '""'
    return _quote(json.dumps(value))


def _serialize_value(value) -> str:
    if isinstance(value, dict):
        return _serialize_object(value)
    if isinstance(value, (list, tuple)):
        # A bare nested list (no property name of its own) — concatenate its serialized
        # elements. Our documents never nest arrays this way; handled only for completeness.
        return "".join(_serialize_value(item) for item in value)
    return _leaf_token(value)


def _serialize_object(node: dict) -> str:
    out: list[str] = []
    for key, value in node.items():
        marker = _quote(str(key).upper())
        if isinstance(value, (list, tuple)):
            out.append(marker)                       # the array marker …
            for item in value:
                out.append(marker)                   # … repeated before every element
                out.append(_serialize_value(item))
        else:
            out.append(marker)
            out.append(_serialize_value(value))
    return "".join(out)


def serialize_document(document: dict) -> str:
    """Return ETA's canonical serialized string for ``document`` (its ``signatures`` excluded)."""
    body = {k: v for k, v in document.items() if str(k).lower() != "signatures"}
    return _serialize_object(body)


def signing_hash(document: dict) -> bytes:
    """SHA-256 of the UTF-8 canonical serialization — the digest a CAdES signature covers."""
    return hashlib.sha256(serialize_document(document).encode("utf-8")).digest()
