"""ETA canonical serialization — golden vectors.

The signature is only valid if our serialization is byte-for-byte ETA's own. These tests pin
the published algorithm (objects, quoted simple values, the JSON array-name repetition,
uppercased names, signatures-excluded) so a regression is caught here, not at live submission.
Expected strings are computed by hand from the rules in
https://sdk.invoicing.eta.gov.eg/document-serialization-approach/ .
"""
from __future__ import annotations

import hashlib

from erp.einvoice.services import canonical
from erp.einvoice.services.eta_adapter import build_document


def test_object_names_uppercased_and_quoted():
    assert canonical.serialize_document({"type": "B", "id": "1"}) == '"TYPE""B""ID""1"'


def test_nested_object():
    doc = {"issuer": {"type": "B", "id": "1"}}
    assert canonical.serialize_document(doc) == '"ISSUER""TYPE""B""ID""1"'


def test_numbers_are_quoted_with_wire_form():
    # ETA encloses simple values of every type in quotes; the number token is the wire token
    # (json), so 14.0 -> "14.0" and 14 -> "14".
    assert canonical.serialize_document({"amount": 14.0}) == '"AMOUNT""14.0"'
    assert canonical.serialize_document({"qty": 1}) == '"QTY""1"'


def test_array_repeats_property_name_per_element():
    doc = {"taxTotals": [{"taxType": "T1", "amount": 14.0}, {"taxType": "T2", "amount": 5.0}]}
    # marker once, then marker + element for each item
    expected = (
        '"TAXTOTALS"'
        '"TAXTOTALS""TAXTYPE""T1""AMOUNT""14.0"'
        '"TAXTOTALS""TAXTYPE""T2""AMOUNT""5.0"'
    )
    assert canonical.serialize_document(doc) == expected


def test_empty_array_emits_only_the_marker():
    assert canonical.serialize_document({"taxTotals": []}) == '"TAXTOTALS"'


def test_signatures_excluded():
    doc = {"id": "1", "signatures": [{"value": "should-not-appear"}]}
    assert canonical.serialize_document(doc) == '"ID""1"'
    assert "SHOULD-NOT-APPEAR" not in canonical.serialize_document(doc).upper()


def test_quote_inside_value_is_escaped():
    # A double quote in a string value becomes \" (standard JSON escaping).
    assert canonical.serialize_document({"name": 'A"B'}) == '"NAME""A\\"B"'


def test_full_document_golden():
    doc = {
        "issuer": {"type": "B", "id": "1"},
        "invoiceLines": [{"description": "x"}],
        "taxTotals": [{"taxType": "T1", "amount": 14.0}],
        "signatures": [{"value": "ignored"}],
    }
    expected = (
        '"ISSUER""TYPE""B""ID""1"'
        '"INVOICELINES""INVOICELINES""DESCRIPTION""x"'
        '"TAXTOTALS""TAXTOTALS""TAXTYPE""T1""AMOUNT""14.0"'
    )
    assert canonical.serialize_document(doc) == expected


def test_signing_hash_matches_manual_sha256():
    doc = {"id": "1"}
    expected = hashlib.sha256('"ID""1"'.encode("utf-8")).digest()
    assert canonical.signing_hash(doc) == expected
    assert len(canonical.signing_hash(doc)) == 32


def test_serializes_a_real_build_document():
    """The serializer must handle the actual ETA document build_document produces."""
    from types import SimpleNamespace

    inv = {
        "invoice": "INV-1", "date": "2026-07-21", "net": 10000, "tax": 1400,
        "total": 11400, "currency": "EGP", "customer": "C1", "customer_name": "Buyer",
    }
    cfg = SimpleNamespace(
        rin="123456789", issuer_name="Acme", activity_code="4610", branch_id="0",
        country="EG", governate="Cairo", region_city="Nasr City", street="1 Main St",
        building_number="10",
    )
    document = build_document(inv, cfg)
    ser = canonical.serialize_document(document)
    # Deterministic, signatures excluded, and the issuer/receiver/line structure present.
    assert '"SIGNATURES"' not in ser
    assert ser.startswith('"ISSUER"')
    assert '"INVOICELINES"' in ser and '"TAXTOTALS"' in ser
    assert canonical.serialize_document(document) == ser  # stable across calls
