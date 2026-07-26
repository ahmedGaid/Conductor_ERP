"""ai-reliability T3.4 — exhaustive unit tests for the shared Arabic normalizer.

Pure function, no DB — every transform (tatweel/diacritic strip, alef unify, ya unify, ta-marbuta
preservation, Latin lowercase) gets its own case with real Arabic samples, plus edge cases
(empty/None/whitespace/mixed-script/idempotency) and the documented module examples verbatim.
"""
from __future__ import annotations

from erp.assistant.textnorm import MERGE_TA_MARBUTA, normalize_ar


def test_merge_ta_marbuta_defaults_off():
    # The whole "keep ة distinct by default" contract hinges on this flag being False; if a future
    # session flips it, this test documents that ta-marbuta assertions below need revisiting.
    assert MERGE_TA_MARBUTA is False


# --- tatweel + diacritics -------------------------------------------------------------------------

def test_strips_tatweel():
    assert normalize_ar("الـــضريبة") == "الضريبة"
    assert normalize_ar("مـرحبـا") == "مرحبا"


def test_strips_standard_harakat():
    # fatha, damma, kasra, shadda, sukun, fathatan, dammatan, kasratan
    assert normalize_ar("اَلْمُوَظَّفُونَ") == "الموظفون"
    assert normalize_ar("كِتَابٌ") == "كتاب"
    assert normalize_ar("مُدَرِّسَةٌ") == "مدرسة"  # shadda + tanwin, ta marbuta untouched


def test_strips_dagger_alif():
    assert normalize_ar("هَـٰذَا") == "هذا"


def test_diacritics_and_tatweel_combined():
    assert normalize_ar("اَلْـتَّـقْرِيرْ") == "التقرير"


# --- alef-hamza / madda unification -----------------------------------------------------------

def test_unifies_alef_hamza_above():
    assert normalize_ar("أحمد") == "احمد"


def test_unifies_alef_hamza_below():
    assert normalize_ar("إحسان") == "احسان"


def test_unifies_alef_madda():
    assert normalize_ar("آمن") == "امن"


def test_unifies_alef_wasla():
    assert normalize_ar("ٱلرحمن") == "الرحمن"


def test_bare_alef_untouched():
    assert normalize_ar("امين") == "امين"


def test_alef_hamza_unified_mid_word_too():
    # The alef-hamza-above codepoint (U+0623) is the same letter form whether it opens a word or
    # sits mid-word — the unification is a character-level map, not position-aware, on purpose.
    assert normalize_ar("سأل") == "سال"
    assert normalize_ar("مسألة") == "مسالة"  # ta marbuta still untouched


# --- alef maksura -> ya ---------------------------------------------------------------------------

def test_unifies_alef_maksura_word_final():
    assert normalize_ar("على") == "علي"
    assert normalize_ar("إلى") == "الي"
    assert normalize_ar("المستشفى") == "المستشفي"


def test_regular_ya_untouched():
    assert normalize_ar("يوم") == "يوم"


# --- ta marbuta stays distinct by default -------------------------------------------------------

def test_ta_marbuta_preserved_by_default():
    assert normalize_ar("مدرسة") == "مدرسة"
    assert normalize_ar("مطالبة") == "مطالبة"
    assert normalize_ar("فاتورة") == "فاتورة"


def test_ta_marbuta_distinct_from_ha():
    normalized_ta = normalize_ar("مدرسة")
    normalized_ha = normalize_ar("مدرسه")
    assert normalized_ta != normalized_ha  # ة and ه remain two different characters


# --- Latin passthrough, lowercased ----------------------------------------------------------------

def test_latin_text_lowercased():
    assert normalize_ar("Invoice VAT-2024") == "invoice vat-2024"
    assert normalize_ar("SOP") == "sop"


def test_latin_punctuation_and_digits_untouched():
    assert normalize_ar("PO#123-A") == "po#123-a"


def test_mixed_arabic_and_latin():
    assert normalize_ar("فاتورة VAT رقم 123") == "فاتورة vat رقم 123"


# --- module docstring examples, verbatim ----------------------------------------------------------

def test_docstring_examples():
    assert normalize_ar("أَحْمَد") == "احمد"
    assert normalize_ar("عَلَىٰ") == "علي"
    assert normalize_ar("مطالبة") == "مطالبة"
    assert normalize_ar("الـــضريبة") == "الضريبة"
    assert normalize_ar("Invoice VAT-2024") == "invoice vat-2024"


# --- edge cases -------------------------------------------------------------------------------

def test_empty_and_none_input():
    assert normalize_ar("") == ""
    assert normalize_ar(None) == ""


def test_whitespace_only_preserved():
    assert normalize_ar("   ") == "   "


def test_whitespace_between_words_preserved():
    assert normalize_ar("سياسة   الاسترجاع") == "سياسة   الاسترجاع"


def test_idempotent():
    samples = [
        "اَلْمُوَظَّفُونَ", "أحمد إحسان آمن ٱلرحمن", "على المستشفى", "مدرسة فاتورة",
        "الـــضريبة", "Invoice VAT-2024", "فاتورة VAT رقم 123", "",
    ]
    for s in samples:
        once = normalize_ar(s)
        assert normalize_ar(once) == once


def test_real_erp_domain_sentence():
    # a realistic sentence combining diacritics, tatweel, hamza-alef, and alef maksura all at once
    raw = "يَجِبُ عَلَـى الْمُسَجَّلِ تَقْدِيمُ الْإِقْرَارِ الضَّرِيبِيِّ إِلَـى مَصْلَحَةِ الضَّرَائِبِ"
    normalized = normalize_ar(raw)
    assert "َ" not in normalized and "ّ" not in normalized and "ـ" not in normalized
    assert normalized.startswith("يجب علي")
    assert "الي مصلحه" not in normalized  # ta marbuta of مصلحة must NOT have merged to ه
    assert "مصلحة" in normalized
