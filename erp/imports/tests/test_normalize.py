"""Normalizers: exhaustive tables per pure function, plus the row-pipeline round-trip.

No DB, no network — every function here is pure, so these run instantly and double as the spec of
what each cell shape means. Arabic-Indic digits, both separator styles, and Egyptian conventions are
first-class rows, not an afterthought."""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from types import SimpleNamespace

import pytest

from erp.imports.normalize import (
    EG_TAX_ID_LEN,
    TaxToken,
    clean_text,
    normalize_code,
    normalize_currency,
    normalize_email,
    normalize_phone,
    normalize_row,
    normalize_tax,
    normalize_tax_id,
    normalize_unit,
    parse_date,
    parse_money,
    parse_number,
)
from erp.imports.registry import FieldSpec, Issue


def _is_issue(v, code=None) -> bool:
    return isinstance(v, Issue) and (code is None or v.code == code)


# --- clean_text ------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("  hello   world  ", "hello world"),
    ("line​with‌zero‍width", "linewithzerowidth"),
    ("tab\tand\nnewline", "tab and newline"),
    ("“curly” ‘quotes’", '"curly" \'quotes\''),
    ("em—dash", "em-dash"),
    ("", None),
    ("    ", None),
])
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected


def test_clean_text_passes_typed_cells_through():
    assert clean_text(1250) == 1250
    d = _dt.date(2026, 2, 1)
    assert clean_text(d) is d
    assert clean_text(None) is None


def test_clean_text_keeps_arabic_letters_for_storage():
    # ة/ى are NOT folded in stored text (folding is matching-only).
    assert clean_text("شركة الأهرام") == "شركة الأهرام"


# --- parse_number ----------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("1250", Decimal("1250")),
    ("1,250.50", Decimal("1250.50")),
    ("1.250,50", Decimal("1250.50")),
    ("1,250", Decimal("1250")),      # lone comma, 3 trailing → thousands
    ("1,5", Decimal("1.5")),          # lone comma, non-3 trailing → decimal
    ("1.250.000", Decimal("1250000")),
    ("١٢٥٠", Decimal("1250")),        # Arabic-Indic digits
    ("١٢٥٠٫٥٠", Decimal("1250.50")),  # Arabic decimal mark
    ("-42", Decimal("-42")),
    ("(42)", Decimal("-42")),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


def test_parse_number_typed():
    assert parse_number(1250) == Decimal("1250")
    assert parse_number(12.5) == Decimal("12.5")


@pytest.mark.parametrize("raw", ["", "   ", "abc", None, True])
def test_parse_number_garbage(raw):
    assert _is_issue(parse_number(raw), "number_invalid")


# --- parse_money -----------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("1,250.50", 125050),
    ("1.250,50", 125050),
    ("EGP 1250", 125000),
    ("1250", 125000),
    ("١٢٥٠٫٥٠", 125050),      # Arabic digits + decimal mark → minor units
    ("L.E 10.50", 1050),
    ("0.50", 50),
])
def test_parse_money(raw, expected):
    assert parse_money(raw) == expected


def test_parse_money_numeric_is_major_units():
    assert parse_money(1250.50) == 125050
    assert parse_money(1250) == 125000


def test_parse_money_minor_digits_override():
    # A 3-minor-digit currency (e.g. BHD) scales by 1000.
    assert parse_money("1.500", currency_minor_digits=3) == 1500


@pytest.mark.parametrize("raw", ["", "  ", "abc", None, True])
def test_parse_money_garbage(raw):
    assert _is_issue(parse_money(raw), "money_invalid")


# --- parse_date ------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("2026-02-01", _dt.date(2026, 2, 1)),
    ("01/02/2026", _dt.date(2026, 2, 1)),   # dayfirst (Egypt)
    ("1 Feb 2026", _dt.date(2026, 2, 1)),
    ("Feb 1, 2026", _dt.date(2026, 2, 1)),
    ("02.01.26", _dt.date(2026, 1, 2)),     # two-digit year pivots to 2026
    ("١/٢/٢٠٢٦", _dt.date(2026, 2, 1)),      # Arabic-Indic digits
    ("12 يناير 2026", _dt.date(2026, 1, 12)),  # Arabic month name
    ("25/12/2026", _dt.date(2026, 12, 25)),  # day > 12 disambiguates
    ("2026/2/1", _dt.date(2026, 2, 1)),
])
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


def test_parse_date_typed():
    assert parse_date(_dt.date(2026, 2, 1)) == _dt.date(2026, 2, 1)
    assert parse_date(_dt.datetime(2026, 2, 1, 9, 30)) == _dt.date(2026, 2, 1)


def test_parse_date_excel_serial():
    # Excel serial 46054 == 2026-02-01.
    assert parse_date(46054) == _dt.date(2026, 2, 1)


def test_parse_date_ambiguous_flags_warning():
    warns: list = []
    out = parse_date("03/04/2026", warnings=warns)
    assert out == _dt.date(2026, 4, 3)  # dayfirst
    assert len(warns) == 1 and warns[0].code == "date_ambiguous"


def test_parse_date_unambiguous_no_warning():
    warns: list = []
    parse_date("25/12/2026", warnings=warns)
    assert warns == []


@pytest.mark.parametrize("raw", ["", "not a date", "99/99/9999", None, True, "13/13/2026"])
def test_parse_date_garbage(raw):
    assert _is_issue(parse_date(raw), "date_invalid")


# --- normalize_currency ----------------------------------------------------------------------
@pytest.mark.parametrize("raw,iso", [
    ("EGP", "EGP"), ("L.E", "EGP"), ("LE", "EGP"), ("le", "EGP"),
    ("جنيه", "EGP"), ("ج.م", "EGP"), ("جنيه مصري", "EGP"),
    ("$", "USD"), ("USD", "USD"), ("dollar", "USD"), ("دولار", "USD"),
    ("€", "EUR"), ("EUR", "EUR"), ("يورو", "EUR"),
])
def test_normalize_currency(raw, iso):
    assert normalize_currency(raw) == iso


@pytest.mark.parametrize("raw", ["", "  ", "wobble", None])
def test_normalize_currency_unknown(raw):
    assert _is_issue(normalize_currency(raw), "currency_unknown")


# --- normalize_unit --------------------------------------------------------------------------
@pytest.mark.parametrize("raw,token", [
    ("PCS", "PCS"), ("Piece", "PCS"), ("Pieces", "PCS"), ("Pc", "PCS"),
    ("Each", "PCS"), ("قطعة", "PCS"), ("عدد", "PCS"),
    ("kg", "KG"), ("كيلو", "KG"), ("gram", "G"),
    ("carton", "BOX"), ("علبة", "BOX"),
])
def test_normalize_unit(raw, token):
    assert normalize_unit(raw) == token


def test_normalize_unit_unknown_falls_back_upper():
    assert normalize_unit("widget") == "WIDGET"
    assert normalize_unit("") == ""


# --- normalize_tax ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,kind,rate", [
    ("14%", "vat", 14),
    ("VAT14", "vat", 14),
    ("VAT", "vat", None),
    ("Value Added Tax", "vat", None),
    ("ضريبة", "vat", None),
    ("exempt", "exempt", 0),
    ("معفى", "exempt", 0),
    ("0%", "exempt", 0),
    ("withholding", "wht", None),
    ("", "none", None),
    ("random", "none", None),
])
def test_normalize_tax(raw, kind, rate):
    tok = normalize_tax(raw)
    assert isinstance(tok, TaxToken)
    assert (tok.kind, tok.rate) == (kind, rate)


# --- normalize_phone -------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("01012345678", "+201012345678"),
    ("+201012345678", "+201012345678"),
    ("00201012345678", "+201012345678"),
    ("201012345678", "+201012345678"),
    ("010 1234 5678", "+201012345678"),
    ("010-1234-5678", "+201012345678"),
    ("٠١٠١٢٣٤٥٦٧٨", "+201012345678"),   # Arabic-Indic digits
    ("+20 (100) 123-4567", "+201001234567"),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["", "123", "0301234567", "notaphone", None])
def test_normalize_phone_invalid(raw):
    assert _is_issue(normalize_phone(raw), "phone_invalid")


# --- normalize_email -------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("  User@Example.COM ", "user@example.com"),
    ("a.b+tag@sub.domain.eg", "a.b+tag@sub.domain.eg"),
])
def test_normalize_email(raw, expected):
    assert normalize_email(raw) == expected


@pytest.mark.parametrize("raw", ["", "no-at-sign", "a@b", "a @b.com", None])
def test_normalize_email_invalid(raw):
    assert _is_issue(normalize_email(raw), "email_invalid")


# --- normalize_tax_id ------------------------------------------------------------------------
def test_normalize_tax_id_digits_only():
    assert normalize_tax_id("123-456-789") == "123456789"
    assert normalize_tax_id("١٢٣٤٥٦٧٨٩") == "123456789"


def test_normalize_tax_id_length_is_warn_not_block():
    warns: list = []
    out = normalize_tax_id("12345", warnings=warns)
    assert out == "12345"  # value still returned
    assert len(warns) == 1 and warns[0].code == "tax_id_length"


def test_normalize_tax_id_good_length_no_warn():
    warns: list = []
    normalize_tax_id("1" * EG_TAX_ID_LEN, warnings=warns)
    assert warns == []


@pytest.mark.parametrize("raw", ["", "abc", None])
def test_normalize_tax_id_invalid(raw):
    assert _is_issue(normalize_tax_id(raw), "tax_id_invalid")


# --- normalize_code --------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("  itm-001 ", "ITM-001"),
    ("sku—12", "SKU-12"),   # em dash unified
    ("cust‐9", "CUST-9"),   # unicode hyphen unified
])
def test_normalize_code(raw, expected):
    assert normalize_code(raw) == expected


# --- normalize_row (Task C round-trip) -------------------------------------------------------
def _customer_adapter():
    return SimpleNamespace(
        entity="customers",
        fields=[
            FieldSpec(name="name", required=True, kind="text"),
            FieldSpec(name="opening_balance", kind="money"),
            FieldSpec(name="since", kind="date"),
            FieldSpec(name="credit_days", kind="number"),
            FieldSpec(name="segment", kind="text", default="retail"),
        ],
    )


def test_normalize_row_happy_path():
    adapter = _customer_adapter()
    mapping = {  # target field → source header
        "name": "Customer Name",
        "opening_balance": "Balance",
        "since": "First Deal",
        "credit_days": "Terms",
    }
    raw = {
        "Customer Name": "  شركة الأهرام ",
        "Balance": "1,250.50",
        "First Deal": "25/12/2026",   # day > 12 → unambiguous
        "Terms": "٣٠",
    }
    normalized, issues = normalize_row(adapter, mapping, raw)
    assert issues == []
    assert normalized == {
        "name": "شركة الأهرام",
        "opening_balance": 125050,
        "since": _dt.date(2026, 12, 25),
        "credit_days": Decimal("30"),
        "segment": "retail",       # default filled for the unmapped optional field
    }


def test_normalize_row_surfaces_date_ambiguity_warning():
    adapter = _customer_adapter()
    mapping = {"name": "N", "since": "D"}
    normalized, issues = normalize_row(adapter, mapping, {"N": "X", "D": "01/02/2026"})
    assert normalized["since"] == _dt.date(2026, 2, 1)  # dayfirst, value still usable
    assert any(i.field == "since" and i.code == "date_ambiguous" for i in issues)


def test_normalize_row_required_missing_is_issue():
    adapter = _customer_adapter()
    normalized, issues = normalize_row(adapter, {"opening_balance": "Bal"}, {"Bal": "100"})
    assert "name" not in normalized
    codes = {(i.field, i.code) for i in issues}
    assert ("name", "required_missing") in codes


def test_normalize_row_collects_parse_issue_with_field():
    adapter = _customer_adapter()
    mapping = {"name": "N", "opening_balance": "B"}
    normalized, issues = normalize_row(adapter, mapping, {"N": "X", "B": "garbage"})
    assert normalized["name"] == "X"
    assert "opening_balance" not in normalized
    assert any(i.field == "opening_balance" and i.code == "money_invalid" for i in issues)


def test_normalize_row_accepts_mapping_result_object():
    adapter = _customer_adapter()
    mapping = SimpleNamespace(field_map=lambda: {"name": "N"})
    normalized, issues = normalize_row(adapter, mapping, {"N": "Acme"})
    assert normalized["name"] == "Acme"
    assert normalized["segment"] == "retail"
