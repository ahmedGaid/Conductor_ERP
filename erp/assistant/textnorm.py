"""Arabic-aware text normalization, shared by ingestion (tsvector) and query preprocessing
(ai-reliability T3.4).

One function, imported everywhere normalization is needed — never two implementations (index-time
and query-time drift is exactly the bug this module exists to prevent). Pure, no DB, no I/O.

``normalize_ar`` applies four transforms, in order:

1. **Strip tatweel + diacritics.** Tatweel (ـ U+0640) is purely decorative letter-elongation with
   no lexical value. The standard harakat (fatha/damma/kasra/shadda/sukun/tanwin, U+064B-U+0652)
   plus the dagger alif (U+0670) carry pronunciation, not identity, for FTS purposes — a document
   written with or without them is the same word.
2. **Unify alef-with-hamza/madda variants to bare alef**: أ إ آ ٱ (U+0623/0625/0622/0671) → ا
   (U+0627). Writers are inconsistent about hamza seat placement at word-initial position; the
   underlying letter is the same alef.
3. **Unify alef maksura to ya**: ى (U+0649) → ي (U+064A). Extremely common spelling variance at
   word endings (على/علي, إلى/الي) and the two glyphs are near-identical in many fonts/keyboards.
4. **Lowercase.** A no-op on Arabic; normalizes any Latin text sharing the same shadow (mixed
   ar/en documents, product codes, etc).

**Ta marbuta (ة) is kept distinct from ha (ه) by default** — unlike the alef/ya merges above,
ة→ه changes MEANING for real words (مطالبة "claim" vs a distinct root with ه), and Arabic writers
get ة right far more reliably than they get hamza-seat placement right. ``MERGE_TA_MARBUTA`` below
flips this on if a future eval run shows the merge helps recall more than it hurts precision — the
decision is data-driven, not assumed at write time.

Examples::

    >>> normalize_ar("أَحْمَد")        # hamza-alef + fatha/sukun diacritics
    'احمد'
    >>> normalize_ar("عَلَىٰ")          # alef maksura + fatha + dagger alif
    'علي'
    >>> normalize_ar("مطالبة")         # ta marbuta — unchanged by default
    'مطالبة'
    >>> normalize_ar("الـــضريبة")     # tatweel-elongated
    'الضريبة'
    >>> normalize_ar("Invoice VAT-2024")
    'invoice vat-2024'

Used at BOTH index time (``services/knowledge.py`` builds the tsvector from the normalized shadow
of each chunk's text — the stored ``text`` column stays raw/untouched) and query time (``search()``
normalizes the query before building the ``SearchQuery``). Embeddings are computed on RAW text at
both ends: the embedding model already handles Arabic morphology natively, and normalizing text fed
to it would only throw away signal the model can use — this module exists purely to help the
lexical (tsvector) matching arm.
"""
from __future__ import annotations

import re

# Flip to True only after an eval run shows merging ة into ه measurably helps Arabic recall more
# than it hurts precision (see module docstring). A top-level constant, not a settings flag,
# because this is a modeling decision made once from data, not an operational toggle.
MERGE_TA_MARBUTA = False

_TATWEEL = "ـ"

# Standard Arabic diacritics (harakat: fathatan, dammatan, kasratan, fatha, damma, kasra, shadda,
# sukun) plus the dagger alif (superscript alef) — combining marks with no lexical value of their
# own. Same canonical set used by pyarabic / CAMeL Tools normalizers.
_DIACRITICS_RE = re.compile("[ً-ْٰ" + _TATWEEL + "]")

_ALEF_YA_MAP = str.maketrans({
    "أ": "ا",  # أ ALEF WITH HAMZA ABOVE -> ا
    "إ": "ا",  # إ ALEF WITH HAMZA BELOW -> ا
    "آ": "ا",  # آ ALEF WITH MADDA ABOVE -> ا
    "ٱ": "ا",  # ٱ ALEF WASLA            -> ا
    "ى": "ي",  # ى ALEF MAKSURA          -> ي
})

_TA_MARBUTA_MAP = str.maketrans({"ة": "ه"})  # ة -> ه — applied only if MERGE_TA_MARBUTA


def normalize_ar(text: str | None) -> str:
    """Normalize Arabic (and lowercase Latin) text for lexical matching. See module docstring for
    the exact transform list and the ta-marbuta decision. Pure function — safe on ``None``/empty/
    mixed-script/punctuation-only input; non-Arabic characters other than casing pass through
    untouched."""
    if not text:
        return text or ""
    result = _DIACRITICS_RE.sub("", text)
    result = result.translate(_ALEF_YA_MAP)
    if MERGE_TA_MARBUTA:
        result = result.translate(_TA_MARBUTA_MAP)
    return result.lower()
