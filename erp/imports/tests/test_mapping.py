"""Header matcher: normalization, fuzzy edit distance, deterministic mapping, model fallback,
profile application. No DB, no network — the model call is monkeypatched at the module seam."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from erp.imports import mapping
from erp.imports.mapping import (
    ColumnMapping,
    apply_profile,
    levenshtein,
    match_headers,
    normalize_header,
    suggest_with_model,
)
from erp.imports.registry import FieldSpec


def _adapter(fields):
    return SimpleNamespace(entity="t", fields=fields)


# Mirrors the FILE_03 seed vocabulary so the deterministic table stays consistent with session 05.
INVOICE_FIELDS = [
    FieldSpec(name="invoice_number", required=True,
              synonyms_en=["invoice no", "invoice #", "doc number"], synonyms_ar=["رقم الفاتورة"]),
    FieldSpec(name="customer", required=True,
              synonyms_en=["customer", "client", "buyer"], synonyms_ar=["العميل"]),
    FieldSpec(name="quantity", kind="number",
              synonyms_en=["qty", "quantity"], synonyms_ar=["الكمية"]),
    FieldSpec(name="unit_price", kind="money",
              synonyms_en=["price", "unit price", "rate"], synonyms_ar=["السعر"]),
    FieldSpec(name="item", synonyms_en=["item", "product", "sku", "material"], synonyms_ar=["الصنف"]),
]


# --- normalize_header -------------------------------------------------------------------------
def test_normalize_lowercases_trims_and_collapses_spaces():
    assert normalize_header("  Invoice   No  ") == "invoice no"


def test_normalize_strips_punctuation():
    assert normalize_header("Invoice #No.") == "invoice no"


def test_normalize_folds_arabic_hamza_and_teh_marbuta():
    # أ/إ/آ → ا (via NFKD), ة → ه — two spellings of the same word collapse.
    assert normalize_header("الإجمالي") == normalize_header("الاجمالي")


def test_normalize_unifies_arabic_indic_digits():
    assert normalize_header("رقم ٢") == "رقم 2"


# --- levenshtein ------------------------------------------------------------------------------
def test_levenshtein_zero_and_one():
    assert levenshtein("customer", "customer") == 0
    assert levenshtein("custmer", "customer") == 1


def test_levenshtein_early_exit_returns_over_budget():
    # far apart, capped at 2 → returns 3 (max_distance + 1), not the true distance.
    assert levenshtein("abcdefgh", "zzzz", max_distance=2) == 3


# --- match_headers (deterministic) ------------------------------------------------------------
@pytest.mark.parametrize("header,field", [
    ("invoice no", "invoice_number"),
    ("invoice #", "invoice_number"),
    ("doc number", "invoice_number"),
    ("رقم الفاتورة", "invoice_number"),
    ("customer", "customer"),
    ("client", "customer"),
    ("العميل", "customer"),
    ("qty", "quantity"),
    ("الكمية", "quantity"),
    ("unit price", "unit_price"),
    ("السعر", "unit_price"),
    ("sku", "item"),
    ("الصنف", "item"),
])
def test_synonyms_map_in_both_languages(header, field):
    result = match_headers([header], _adapter(INVOICE_FIELDS))
    assert result.columns[header].field == field
    assert result.columns[header].confidence == 100


def test_mixed_language_file_maps_every_column():
    headers = ["رقم الفاتورة", "customer", "الكمية", "price"]
    fm = match_headers(headers, _adapter(INVOICE_FIELDS)).field_map()
    assert fm == {
        "invoice_number": "رقم الفاتورة",
        "customer": "customer",
        "quantity": "الكمية",
        "unit_price": "price",
    }


def test_fuzzy_catches_misspelled_english_header_with_lower_confidence():
    result = match_headers(["Invoce No"], _adapter(INVOICE_FIELDS))
    m = result.columns["Invoce No"]
    assert m.field == "invoice_number"
    assert m.method == "fuzzy"
    assert m.confidence < 100


def test_unrecognized_header_is_ignored():
    result = match_headers(["random gibberish xyz"], _adapter(INVOICE_FIELDS))
    m = result.columns["random gibberish xyz"]
    assert m.field is None
    assert m.method == "ignore"


# --- suggest_with_model (fallback) ------------------------------------------------------------
def test_model_fills_only_unmapped_and_caps_confidence(monkeypatch):
    fields = [FieldSpec(name="name", required=True, synonyms_ar=["الاسم"]),
              FieldSpec(name="phone", synonyms_en=["phone"])]
    fake = Mock(return_value={"mappings": [{"header": "mobile 01", "field": "phone"}]})
    monkeypatch.setattr(mapping, "complete_json", fake)

    result = suggest_with_model(None, ["الاسم", "mobile 01"], [], _adapter(fields))

    assert result.columns["الاسم"].field == "name"      # deterministic, untouched
    assert result.columns["mobile 01"].field == "phone"  # model-filled
    assert result.columns["mobile 01"].method == "model"
    assert result.columns["mobile 01"].confidence == 80
    fake.assert_called_once()


def test_model_proposing_unknown_field_is_dropped(monkeypatch):
    fields = [FieldSpec(name="name", required=True, synonyms_ar=["الاسم"])]
    monkeypatch.setattr(mapping, "complete_json",
                        Mock(return_value={"mappings": [{"header": "junk", "field": "not_a_field"}]}))

    result = suggest_with_model(None, ["الاسم", "junk"], [], _adapter(fields))

    assert result.columns["junk"].field is None
    assert result.columns["junk"].method == "ignore"


def test_model_not_called_when_everything_mapped(monkeypatch):
    fake = Mock(side_effect=AssertionError("model must not be called when the pass is complete"))
    monkeypatch.setattr(mapping, "complete_json", fake)

    result = suggest_with_model(None, ["invoice no", "customer"], [], _adapter(INVOICE_FIELDS))

    assert result.columns["invoice no"].field == "invoice_number"
    fake.assert_not_called()


# --- apply_profile ----------------------------------------------------------------------------
def test_profile_applies_saved_mapping_directly():
    profile = SimpleNamespace(mapping={"الاسم": "name", "الهاتف": "phone"})
    result = apply_profile(profile, ["الاسم", "الهاتف"])
    assert result.columns["الاسم"] == ColumnMapping(field="name", confidence=100, method="profile")
    assert result.columns["الهاتف"].confidence == 100


def test_profile_flags_headers_it_does_not_cover():
    profile = SimpleNamespace(mapping={"الاسم": "name"})
    result = apply_profile(profile, ["الاسم", "surprise column"])
    assert result.columns["الاسم"].method == "profile"
    assert result.columns["surprise column"].field is None  # drifted header → flagged
    assert result.columns["surprise column"].method == "ignore"
