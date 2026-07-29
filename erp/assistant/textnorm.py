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


# ai-reliability T3.9 — query-side only. The tsvector is built with config "simple", which has NO
# stopword dictionary, and the query side uses websearch_to_tsquery, which ANDs every bare term.
# Together that means a natural question ("what is the refund policy?" / "ايه هي سياسة الاسترجاع؟")
# only matches a chunk that literally contains "what", "is" and "the" as well — so real questions
# fell through the FTS arm entirely and landed in the score-0.0 icontains fallback. Stripping the
# function words before the SearchQuery restores AND-matching on the words that carry the meaning.
#
# Deliberately query-side ONLY: the index keeps every word (a stored chunk must stay searchable by
# exact phrase, and dropping words from the tsvector would lose the "simple" config's phrase
# ordering). This is not a second normalizer — it runs AFTER ``normalize_ar`` on its output, so
# both ends still share the one transform in this module.
#
# Conservative by design: question words, pronouns, prepositions, conjunctions and auxiliaries in
# both languages — nothing that could name a business concept. Arabic entries are written in their
# ALREADY-NORMALIZED form (bare alef, ya for alef-maksura), since that is what they look like by
# the time this runs.
_QUERY_STOPWORDS = frozenset("""
what which who whom whose when where why how
is are am was were be been being do does did done
the a an of in on at to for from by with about into over after before
and or but if so than then that this these those there here
i we you he she it they me us my our your his her its their
can could will would shall should may might must
please tell show give list find get need want know
""".split()) | frozenset("""
ما ماذا من في علي عن الي مع هل كيف متي اين لماذا لمن
هي هو هم هن انا نحن انت انتم
هذا هذه ذلك تلك التي الذي الذين
و او ثم لكن بل قد كان كانت يكون تكون
كل بعض اي عند بعد قبل عند لدي
يوجد هناك ايه ازاي فين امتي ليه مين
عايز عاوز ممكن لو اذا مش لا نعم
""".split())


def is_query_stopword(word: str | None) -> bool:
    """Whether one word is a query function word. Takes RAW or normalized input — it normalizes
    and trims punctuation itself, so callers matching against raw document text (the icontains
    fallback in ``services/knowledge.py``) can filter their raw terms without normalizing them."""
    if not word:
        return True
    return normalize_ar(word).strip("؟?!.,;:\"'()[]") in _QUERY_STOPWORDS


def strip_query_stopwords(text: str | None) -> str:
    """Drop function words from an ALREADY-``normalize_ar``-ed query so the FTS arm ANDs only the
    meaning-bearing terms (see ``_QUERY_STOPWORDS`` for why). Pure function.

    Returns the input unchanged when every term is a stopword — a query like "how do i?" has no
    content left, and an empty tsquery would match nothing at all, which is strictly worse than the
    original behavior. Punctuation is left to ``websearch_to_tsquery``; only whitespace splitting
    happens here, so quoted phrases keep their quotes and still bind as phrases.
    """
    if not text:
        return text or ""
    terms = text.split()
    kept = [t for t in terms if not is_query_stopword(t)]
    return " ".join(kept) if kept else text
