"""Header recognition — matching a file's columns to an adapter's target fields (plan session 03).

The engine's rule (index decision 3) is *deterministic first, model as fallback*. So this module has
two layers, and the cheap one always runs before the expensive one:

* ``match_headers`` — a pure, offline matcher: normalize each header (Arabic letter/diacritic/digit
  folding included), then try exact-synonym → prefix/contains → fuzzy (Levenshtein ≤ 2) against the
  adapter's per-field synonym lists. Every column gets a ``{field, confidence, method}``; anything it
  can't place stays ``ignore`` for the wizard to resolve.
* ``suggest_with_model`` — only for the columns the deterministic pass left unmapped, one
  ``complete_json`` call proposing field assignments, each validated against the adapter's field set
  (an unknown field is dropped) and capped at confidence 80 so model guesses always read as
  overridable in the UI.

``apply_profile`` is the third path: a saved ``ImportProfile`` re-applies a human-confirmed mapping
directly, no matching needed. Vocabularies live on each adapter's ``FieldSpec`` (registry) — this
module never hardcodes an entity's words.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

from erp.assistant.errors import AssistantUnavailableError
from erp.assistant.gateway.core import complete_json

# --- Header normalization --------------------------------------------------------------------
# Arabic-Indic (٠..٩ U+0660) and Extended Arabic-Indic (۰..۹ U+06F0) digits → ASCII 0..9.
_DIGITS = {ord("٠") + i: str(i) for i in range(10)}
_DIGITS.update({ord("۰") + i: str(i) for i in range(10)})
# teh-marbuta → heh, alef-maksura → yeh, drop tatweel. (Hamza forms أإآؤئ fold via NFKD below.)
_AR_LETTERS = str.maketrans({"ة": "ه", "ى": "ي", "ـ": ""})
_PUNCT_RE = re.compile(r"[#.:;،؛/\\_\-()\[\]{}|\"'`*+=?!<>@$%^&~]")
_WS_RE = re.compile(r"\s+")


def normalize_header(h: str) -> str:
    """Fold a raw header to a comparison key: lowercased, space-collapsed, punctuation-stripped,
    diacritic-free, with Arabic letters and Arabic-Indic digits unified. NFKD + combining-mark strip
    handles both Latin accents (é→e) and Arabic hamza-carriers (أإآ→ا, ؤ→و, ئ→ي)."""
    s = str(h or "").strip().lower().translate(_DIGITS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.translate(_AR_LETTERS)
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def levenshtein(a: str, b: str, max_distance: int = 3) -> int:
    """Edit distance with an early exit: returns ``max_distance + 1`` the moment it's provably over,
    so a far-apart pair costs O(max_distance) rows, not O(len)."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > max_distance:
        return max_distance + 1
    if la > lb:  # keep the inner loop over the longer string
        a, b, la, lb = b, a, lb, la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        ca = a[i - 1]
        row_min = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if ca == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if cur[j] < row_min:
                row_min = cur[j]
        if row_min > max_distance:
            return max_distance + 1
        prev = cur
    return prev[lb] if prev[lb] <= max_distance else max_distance + 1


# --- Result shapes ---------------------------------------------------------------------------
# Match methods, strongest first — also the confidence order the UI colours by.
METHOD_EXACT = "exact"
METHOD_PREFIX = "prefix"
METHOD_FUZZY = "fuzzy"
METHOD_MODEL = "model"
METHOD_PROFILE = "profile"
METHOD_IGNORE = "ignore"


@dataclass
class ColumnMapping:
    """One header's resolution: which target ``field`` (or None), how sure, and how it was found."""

    field: str | None
    confidence: int  # 0–100
    method: str


@dataclass
class MappingResult:
    columns: dict[str, ColumnMapping]  # source header → mapping

    def field_map(self) -> dict[str, str]:
        """Target field → the header that best fills it (highest confidence wins ties)."""
        out: dict[str, str] = {}
        best: dict[str, int] = {}
        for header, m in self.columns.items():
            if m.field is None:
                continue
            if m.field not in out or m.confidence > best[m.field]:
                out[m.field] = header
                best[m.field] = m.confidence
        return out

    def unmapped(self) -> list[str]:
        return [h for h, m in self.columns.items() if m.field is None]


# --- Deterministic matcher (Task A) ----------------------------------------------------------
def _synonym_index(adapter) -> list[tuple[str, str]]:
    """(normalized synonym, field name) pairs for an adapter — the field's own name counts too."""
    index: list[tuple[str, str]] = []
    for f in adapter.fields:
        words = [f.name, *f.synonyms_en, *f.synonyms_ar]
        for w in words:
            n = normalize_header(w)
            if n:
                index.append((n, f.name))
    return index


def _best_match(hn: str, index: list[tuple[str, str]]) -> ColumnMapping:
    if not hn:
        return ColumnMapping(field=None, confidence=0, method=METHOD_IGNORE)
    for syn, field in index:  # exact
        if syn == hn:
            return ColumnMapping(field=field, confidence=100, method=METHOD_EXACT)
    best: ColumnMapping | None = None  # prefix / contains
    for syn, field in index:
        if not syn:
            continue
        edge = hn.startswith(syn) or syn.startswith(hn)
        if edge or syn in hn or hn in syn:
            score = 85 if edge else 80
            if best is None or score > best.confidence:
                best = ColumnMapping(field=field, confidence=score, method=METHOD_PREFIX)
    if best is not None:
        return best
    best_dist, best_field = 3, None  # fuzzy (≤ 2)
    for syn, field in index:
        d = levenshtein(hn, syn, max_distance=2)
        if d < best_dist:
            best_dist, best_field = d, field
    if best_field is not None and best_dist <= 2:
        return ColumnMapping(field=best_field, confidence=80 - best_dist * 10, method=METHOD_FUZZY)
    return ColumnMapping(field=None, confidence=0, method=METHOD_IGNORE)


def match_headers(headers, adapter) -> MappingResult:
    """Deterministic, offline column→field mapping. Runs first; the model never sees a header this
    pass could place. Unmapped headers come back as ``ignore``."""
    index = _synonym_index(adapter)
    columns = {h: _best_match(normalize_header(h), index) for h in headers}
    return MappingResult(columns=columns)


# --- AI-assisted fallback (Task C) -----------------------------------------------------------
_SUGGEST_SYSTEM = (
    "You map spreadsheet columns to a fixed set of target fields for one entity. "
    "For each given header, choose the single best target field from the allowed list, or null if "
    "none fits. Use the sample values as evidence. Reply as JSON only, no prose."
)


def _suggest_schema(fields: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "header": {"type": "string"},
                        "field": {"type": ["string", "null"], "enum": [*fields, None]},
                    },
                    "required": ["header", "field"],
                },
            },
        },
        "required": ["mappings"],
    }


def suggest_with_model(actor, headers, sample_rows, adapter) -> MappingResult:
    """Run the deterministic pass, then ask the model to place only what's left. Each proposal is
    validated against ``adapter.fields`` (unknown field → dropped) and pinned to confidence 80,
    method ``model`` — always overridable. A model outage leaves the deterministic result intact."""
    result = match_headers(headers, adapter)
    unmapped = result.unmapped()
    if not unmapped:
        return result
    valid = {f.name for f in adapter.fields}
    payload = {
        "headers": unmapped,
        "sample_rows": [_row_subset(r, unmapped) for r in (sample_rows or [])[:5]],
        "allowed_fields": sorted(valid),
    }
    try:
        raw = complete_json(_SUGGEST_SYSTEM,
                            json.dumps(payload, ensure_ascii=False, default=str),
                            _suggest_schema(sorted(valid)))
    except AssistantUnavailableError:
        return result  # deterministic mapping stands; the wizard lets the user finish by hand
    for item in (raw or {}).get("mappings", []) or []:
        header = item.get("header")
        field = item.get("field")
        if header in result.columns and field in valid:
            result.columns[header] = ColumnMapping(field=field, confidence=80, method=METHOD_MODEL)
    return result


def _row_subset(row: dict, headers: list[str]) -> dict:
    return {h: row.get(h) for h in headers} if isinstance(row, dict) else {}


# --- Profile application (Task D) ------------------------------------------------------------
def apply_profile(profile, headers) -> MappingResult:
    """Re-apply a saved ``{header: field}`` mapping. Headers present in the profile map at
    confidence 100 (``profile``); headers the profile doesn't cover stay ``ignore`` so the wizard
    flags them — this is exactly the intersection when the file's columns have drifted."""
    saved = dict(getattr(profile, "mapping", None) or {})
    columns: dict[str, ColumnMapping] = {}
    for h in headers:
        field = saved.get(h)
        if field:
            columns[h] = ColumnMapping(field=field, confidence=100, method=METHOD_PROFILE)
        else:
            columns[h] = ColumnMapping(field=None, confidence=0, method=METHOD_IGNORE)
    return MappingResult(columns=columns)
