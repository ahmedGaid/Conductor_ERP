"""Data-cleaning normalizers — messy human cells → typed, canonical values (plan session 04).

Every uploaded cell is a human artefact: Arabic-Indic digits (١٢٣), the Egyptian date order
(day-first), a currency written five different ways (EGP / L.E / جنيه), a phone with spaces and a
country code, a price with either separator style ("1,250.50" *or* "1.250,50"). This module turns
each into the one shape the rest of the engine trusts — and it stays **pure and DB-free**: canonical
tokens (currency/unit/tax) are strings that an adapter's ``lookup`` resolves to real records later
(index decision 3, 9). Pure means fast tests and reuse straight from the live preview.

Two return styles:

* **Blocking** problems come back as an :class:`~erp.imports.registry.Issue` (bad data the engine
  cannot use) — the caller checks ``isinstance(result, Issue)``. Nothing here ever raises.
* **Warnings** (the value is usable but worth flagging — an ambiguous date, an odd-length tax id)
  ride an optional ``warnings`` list the caller passes in; the value itself is still returned.

``normalize_row`` is the row-level pipeline: it dispatches each mapped column by its ``FieldSpec``
kind (text/number/money/date/ref/enum) and collects issues. The semantic normalizers
(``normalize_phone``/``_currency``/``_unit``/``_tax``/``_email``/``_tax_id``/``_code``) are the
public toolkit each master adapter (FILE_05) calls on its own text fields.
"""
from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from erp.accounting.domain.money import MINOR_UNIT_DIGITS
from erp.imports.mapping import normalize_header
from erp.imports.readers import _repair_mojibake
from erp.imports.registry import Issue

# --- Issue codes + i18n message keys ---------------------------------------------------------
# Issue.message is an i18n KEY the frontend translates (blame-free wording per the Directive) —
# never a hardcoded English sentence.
_KEYS = {
    "date_invalid": "imports.issues.dateInvalid",
    "date_ambiguous": "imports.issues.dateAmbiguous",
    "money_invalid": "imports.issues.moneyInvalid",
    "number_invalid": "imports.issues.numberInvalid",
    "currency_unknown": "imports.issues.currencyUnknown",
    "phone_invalid": "imports.issues.phoneInvalid",
    "email_invalid": "imports.issues.emailInvalid",
    "tax_id_invalid": "imports.issues.taxIdInvalid",
    "tax_id_length": "imports.issues.taxIdLength",
    "required_missing": "imports.issues.requiredMissing",
}


def _issue(code: str, field: str = "") -> Issue:
    return Issue(field=field, code=code, message=_KEYS[code])


# --- Digit + separator folding ---------------------------------------------------------------
# Arabic-Indic (٠..٩ U+0660) and Extended Arabic-Indic (۰..۹ U+06F0) digits → ASCII; Arabic decimal
# (٫ U+066B) and thousands (٬ U+066C) marks → their Latin equivalents so number parsing is uniform.
_DIGIT_MAP = {ord("٠") + i: str(i) for i in range(10)}
_DIGIT_MAP.update({ord("۰") + i: str(i) for i in range(10)})
_DIGIT_MAP.update({ord("٫"): ".", ord("٬"): ",", ord("،"): ","})


def _fold_digits(s: str) -> str:
    return s.translate(_DIGIT_MAP)


# --- Text pass (Task A) ----------------------------------------------------------------------
# Punctuation variants a human/Excel sprinkles in that we fold to their plain form for STORED text.
_PUNCT_VARIANTS = {
    ord("’"): "'", ord("‘"): "'", ord("“"): '"', ord("”"): '"',
    ord("–"): "-", ord("—"): "-", ord("‐"): "-", ord(" "): " ",
}
_ZERO_WIDTH = "﻿​‌‍‎‏‪‫‬‭‮"
_ZW_TABLE = {ord(c): None for c in _ZERO_WIDTH}
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS_RE = re.compile(r"\s+")


def clean_text(v) -> Optional[str]:
    """Trim, collapse internal whitespace, drop zero-width/control chars, repair cp1256 mojibake and
    fold punctuation variants. Non-string cells (int/float/date/bool) pass through untouched — typed
    parsing owns them. Arabic letters are kept AS-IS for the stored name; matching folds a copy."""
    if v is None:
        return None
    if not isinstance(v, str):
        return v
    s = _CONTROL_RE.sub("", v.translate(_ZW_TABLE)).translate(_PUNCT_VARIANTS)
    s = _repair_mojibake(s)
    s = _WS_RE.sub(" ", s).strip()
    return s or None


def match_key(v) -> str:
    """A folded key for MATCHING only — Arabic letters/diacritics/digits unified, lowercased,
    punctuation flattened. Never stored; used to compare a value against a canonical vocabulary."""
    return normalize_header(str(v or ""))


# --- Numbers + money (Task B) ----------------------------------------------------------------
def _to_decimal(text: str) -> Optional[Decimal]:
    """Parse a human number to Decimal, resolving thousands vs decimal separators.

    Both separators present → the LAST one is the decimal point (handles "1,250.50" and "1.250,50").
    A lone comma is thousands when it groups three trailing digits (Egyptian "1,250"), else decimal.
    A lone dot is the decimal point unless it repeats ("1.250.000" → thousands).
    """
    s = _fold_digits(str(text)).strip()
    neg = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    # Drop currency letters/symbols, then any separators they left dangling at the edges (the "."
    # in "L.E 10.50" must not read as a decimal point).
    s = re.sub(r"[^0-9,.]", "", s).strip(",.")
    if not re.search(r"\d", s):
        return None
    has_dot, has_comma = "." in s, "," in s
    if has_dot and has_comma:
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif has_comma:
        parts = s.split(",")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and parts[0]):
            s = s.replace(",", "")  # thousands
        else:
            s = s.replace(",", ".")  # decimal
    elif has_dot and s.count(".") > 1:
        s = s.replace(".", "")  # 1.250.000 → thousands
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return -d if neg else d


def parse_number(v):
    """Human number → Decimal, or Issue ``number_invalid``. Numeric cells pass straight through."""
    if isinstance(v, bool) or v is None or (isinstance(v, str) and not v.strip()):
        return _issue("number_invalid")
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    d = _to_decimal(v)
    return d if d is not None else _issue("number_invalid")


def parse_money(v, currency_minor_digits: int = MINOR_UNIT_DIGITS):
    """Human price → integer **minor units** (the money rule), or Issue ``money_invalid``.

    A numeric cell is already major units ("1250.50" → 125050). Strings are cleaned of currency
    symbols/words first, then the separator heuristic in ``_to_decimal`` decides the decimal point.
    """
    if isinstance(v, bool) or v is None or (isinstance(v, str) and not v.strip()):
        return _issue("money_invalid")
    if isinstance(v, (int, float)):
        d = Decimal(str(v))
    else:
        d = _to_decimal(v)
    if d is None:
        return _issue("money_invalid")
    scale = Decimal(10) ** currency_minor_digits
    return int((d * scale).to_integral_value(rounding=ROUND_HALF_UP))


# --- Dates (Task B) --------------------------------------------------------------------------
_EXCEL_EPOCH = _dt.date(1899, 12, 30)  # Excel's day 1 is 1900-01-01, minus its 1900-leap-year bug.
_EXCEL_SERIAL_MAX = 2958465  # 9999-12-31
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
    "nov": 11, "november": 11, "dec": 12, "december": 12,
    # Egyptian Arabic month names (already Arabic-letter-folded by match_key: ة→ه, ى→ي).
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "مايو": 5, "يونيو": 6,
    "يوليو": 7, "اغسطس": 8, "سبتمبر": 9, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
}
_DATE_SPLIT_RE = re.compile(r"[\/.\-\s]+")


def _pivot_year(y: int) -> int:
    """Two-digit years pivot at 50: 00–49 → 2000s, 50–99 → 1900s."""
    if y < 100:
        return 2000 + y if y < 50 else 1900 + y
    return y


def _build_date(y: int, m: int, d: int) -> Optional[_dt.date]:
    try:
        return _dt.date(_pivot_year(y), m, d)
    except ValueError:
        return None


def parse_date(v, dayfirst: bool = True, warnings: Optional[list] = None):
    """Messy date → ``datetime.date``, or Issue ``date_invalid``.

    Handles ISO (2026-02-01), Egyptian day-first numeric (01/02/2026, 02.01.26), spelled months
    (1 Feb 2026, يناير), Excel serial numbers, and Arabic-Indic digits (١/٢/٢٠٢٦). When day and month
    are both ≤ 12 the order is genuinely ambiguous: it resolves day-first (Egypt convention) and, if
    a ``warnings`` list was passed, appends a non-blocking ``date_ambiguous`` flag for the preview.
    """
    if isinstance(v, bool) or v is None or (isinstance(v, str) and not v.strip()):
        return _issue("date_invalid")
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, (int, float)):  # Excel serial
        n = int(v)
        if 1 <= n <= _EXCEL_SERIAL_MAX:
            return _EXCEL_EPOCH + _dt.timedelta(days=n)
        return _issue("date_invalid")

    s = _fold_digits(clean_text(v) or "")
    parts = [p for p in _DATE_SPLIT_RE.split(s) if p]

    # All-numeric: Y-M-D when a 4-digit year leads/trails, else day/month with the dayfirst default.
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        a, b, c = (int(p) for p in parts)
        if len(parts[0]) == 4:
            return _build_date(a, b, c) or _issue("date_invalid")
        year = c
        ambiguous = False
        if a > 12 and b <= 12:
            d, m = a, b
        elif b > 12 and a <= 12:
            d, m = b, a
        else:
            ambiguous = a <= 12 and b <= 12
            d, m = (a, b) if dayfirst else (b, a)
        out = _build_date(year, m, d)
        if out is None:
            return _issue("date_invalid")
        if ambiguous and warnings is not None:
            warnings.append(_issue("date_ambiguous"))
        return out

    # Spelled month: "1 Feb 2026", "Feb 1 2026", "12 يناير 2026".
    month = None
    nums: list[int] = []
    for tok in re.split(r"[\s,]+", s):
        key = match_key(tok.strip("."))
        if key in _MONTHS:
            month = _MONTHS[key]
        elif tok.isdigit():
            nums.append(int(tok))
    if month is not None and len(nums) == 2:
        if nums[0] > 31:
            year, day = nums
        else:
            day, year = nums
        return _build_date(year, month, day) or _issue("date_invalid")

    return _issue("date_invalid")


# --- Currency / unit / tax canonical tokens (Task B) -----------------------------------------
# Folded keys (via match_key) → ISO code. Symbols £/$/€ are scanned on the raw value first, because
# match_key flattens most punctuation.
_CURRENCY_WORDS = {
    "egp": "EGP", "le": "EGP", "l e": "EGP", "egyptian pound": "EGP",
    "جنيه": "EGP", "جنيه مصري": "EGP", "ج م": "EGP", "جم": "EGP", "£": "EGP",
    "usd": "USD", "us dollar": "USD", "dollar": "USD", "dollars": "USD", "دولار": "USD",
    "eur": "EUR", "euro": "EUR", "يورو": "EUR",
    "sar": "SAR", "ريال": "SAR", "ريال سعودي": "SAR",
    "aed": "AED", "درهم": "AED",
}


def normalize_currency(v):
    """Currency word/symbol → ISO code (EGP/USD/EUR/…), or Issue ``currency_unknown``."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return _issue("currency_unknown")
    raw = str(v)
    if "$" in raw:
        return "USD"
    if "€" in raw:
        return "EUR"
    key = match_key(raw)
    if key in _CURRENCY_WORDS:
        return _CURRENCY_WORDS[key]
    # Substring fallback only for words long enough to be safe (a 2-char "le" would hit "wobble").
    for word, iso in _CURRENCY_WORDS.items():
        if len(word) >= 3 and word in key:
            return iso
    return _issue("currency_unknown")


# Canonical unit tokens. Unknown input is never blocking — it returns an upper-cased fallback token
# the adapter can still map or the user can correct in the wizard.
_UNIT_WORDS = {
    "pcs": "PCS", "pc": "PCS", "piece": "PCS", "pieces": "PCS", "each": "PCS", "ea": "PCS",
    "unit": "PCS", "units": "PCS", "قطعه": "PCS", "قطع": "PCS", "حبه": "PCS", "عدد": "PCS",
    "kg": "KG", "kilo": "KG", "kilogram": "KG", "kgs": "KG", "كيلو": "KG", "كجم": "KG",
    "g": "G", "gram": "G", "grams": "G", "جرام": "G",
    "l": "L", "liter": "L", "litre": "L", "liters": "L", "لتر": "L",
    "box": "BOX", "carton": "BOX", "ctn": "BOX", "كرتونه": "BOX", "علبه": "BOX", "صندوق": "BOX",
    "m": "M", "meter": "M", "metre": "M", "متر": "M",
    "dozen": "DOZEN", "dz": "DOZEN", "دسته": "DOZEN", "دزينه": "DOZEN",
}


def normalize_unit(v) -> str:
    """Unit-of-measure word → canonical token (PCS/KG/G/L/BOX/M/DOZEN). Unknown → upper fallback."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return ""
    key = match_key(v)
    if key in _UNIT_WORDS:
        return _UNIT_WORDS[key]
    return (clean_text(v) or "").upper()


@dataclass
class TaxToken:
    """A canonical tax reading an adapter resolves to a real tax record. ``rate`` is a percent
    integer or None when the word carried no number (the adapter fills its default)."""

    kind: str  # "vat" | "exempt" | "wht" | "none"
    rate: Optional[int] = None


_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%?")
_EXEMPT_WORDS = ("exempt", "معفي", "معفى", "لا ضريبه", "no tax", "none", "zero rated")
_VAT_WORDS = ("vat", "value added tax", "ضريبه", "ضريبه القيمه المضافه", "ق م", "tax", "sales tax")
_WHT_WORDS = ("wht", "withholding", "خصم واضافه", "خصم و اضافه")


def normalize_tax(v) -> TaxToken:
    """Tax word/percent → :class:`TaxToken`. "14%" → vat 14; "VAT" → vat (rate None);
    معفى/exempt → exempt 0; withholding → wht. Empty/unknown → none. Never blocks."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return TaxToken(kind="none")
    key = match_key(v)
    folded = _fold_digits(str(v))
    m = _PERCENT_RE.search(folded)
    rate = None
    if m:
        try:
            rate = int(round(float(m.group(1))))
        except ValueError:
            rate = None
        if rate is not None and rate > 100:  # guard against a stray year/id being read as a rate
            rate = None
    if any(w in key for w in _EXEMPT_WORDS):
        return TaxToken(kind="exempt", rate=0)
    if any(w in key for w in _WHT_WORDS):
        return TaxToken(kind="wht", rate=rate)
    if rate == 0:
        return TaxToken(kind="exempt", rate=0)
    if any(w in key for w in _VAT_WORDS) or rate is not None:
        return TaxToken(kind="vat", rate=rate)
    return TaxToken(kind="none")


# --- Phone / email / tax-id / code (Task B) --------------------------------------------------
_EG_MOBILE_RE = re.compile(r"^1[0125]\d{8}$")  # 10 significant digits: 1 + operator + 8


def normalize_phone(v, default_country: str = "EG"):
    """Egyptian phone → E.164 ``+20…`` form (spaces/dashes/parens removed), or Issue
    ``phone_invalid``. Accepts 01012345678, +201012345678, 00201012345678, 201012345678."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return _issue("phone_invalid")
    digits = re.sub(r"\D", "", _fold_digits(str(v)))
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("20"):
        national = digits[2:]
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        national = digits
    if default_country == "EG" and _EG_MOBILE_RE.match(national):
        return "+20" + national
    return _issue("phone_invalid")


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(v):
    """Trim + lowercase an email, or Issue ``email_invalid``."""
    if v is None:
        return _issue("email_invalid")
    s = (clean_text(v) or "").strip().lower()
    return s if _EMAIL_RE.match(s) else _issue("email_invalid")


EG_TAX_ID_LEN = 9  # Egyptian tax registration number is 9 digits.


def normalize_tax_id(v, warnings: Optional[list] = None):
    """Tax id → digits only, or Issue ``tax_id_invalid`` when it has no digits. A wrong length is a
    WARNING (appended to ``warnings`` if given), never blocking — some legacy records are imperfect."""
    if v is None:
        return _issue("tax_id_invalid")
    digits = re.sub(r"\D", "", _fold_digits(str(v)))
    if not digits:
        return _issue("tax_id_invalid")
    if len(digits) != EG_TAX_ID_LEN and warnings is not None:
        warnings.append(_issue("tax_id_length"))
    return digits


_CODE_DASH_RE = re.compile(r"[‐-‒–—―]")  # unify the many Unicode dashes to ASCII hyphen


def normalize_code(v) -> str:
    """Item/customer code → trimmed, upper-cased, dashes unified. Never blocks."""
    s = clean_text(v) or ""
    return _CODE_DASH_RE.sub("-", s).upper().strip()


# --- Row pipeline (Task C) -------------------------------------------------------------------
def _is_blank(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _field_map(mapping) -> dict:
    """Accept either a ``MappingResult`` or a plain ``{field: header}`` dict."""
    if hasattr(mapping, "field_map"):
        return mapping.field_map()
    return dict(mapping or {})


def normalize_row(adapter, mapping, raw: dict):
    """Normalize one raw row into ``(normalized: dict, issues: list[Issue])``.

    Each of the adapter's fields is filled from its mapped source column and dispatched by
    ``FieldSpec.kind``. Unmapped columns are dropped. A required field that's absent/blank yields a
    ``required_missing`` issue; an optional field falls back to its ``default``. Blocking parse
    failures land in ``issues`` (value left unset); warnings are collected too. Never raises.
    """
    fmap = _field_map(mapping)
    normalized: dict = {}
    issues: list[Issue] = []

    for spec in adapter.fields:
        header = fmap.get(spec.name)
        value = raw.get(header) if header is not None else None

        if header is None or _is_blank(value):
            if spec.required:
                issues.append(_issue("required_missing", spec.name))
            elif spec.default is not None:
                normalized[spec.name] = spec.default
            continue

        warns: list[Issue] = []
        result = _dispatch(spec, value, warns)
        for w in warns:
            w.field = spec.name
            issues.append(w)
        if isinstance(result, Issue):
            result.field = spec.name
            issues.append(result)
        else:
            normalized[spec.name] = result

    return normalized, issues


def _dispatch(spec, value, warns: list):
    """Route one cell through the normalizer for its ``FieldSpec.kind``."""
    kind = spec.kind
    if kind == "money":
        return parse_money(value)
    if kind == "date":
        return parse_date(value, dayfirst=True, warnings=warns)
    if kind == "number":
        return parse_number(value)
    # text / ref / enum: clean for storage + matching; ref resolution + enum membership run later.
    return clean_text(value)
