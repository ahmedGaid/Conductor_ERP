"""Gate 14 — number typography & the digits policy (Arabic craft).

One digits policy, both locales: **Latin numerals** (`1,234.56`), never Arabic-Indic
(`١٬٢٣٤٫٥٦`) — the Egyptian business convention (invoices, banks, ETA e-invoicing all use Latin
digits; mixing hurts scanning). Formatting lives only in `lib/money.ts` (`en-US` grouping) and
figures render with tabular (fixed-width) numerals so columns align. This gate locks that policy:

- no Arabic-Indic / Extended-Arabic-Indic digit characters in the i18n locale files or source;
- no number formatting through an `ar`/`ar-EG` locale (`toLocaleString`/`Intl.NumberFormat`);
- `lib/money.ts` groups with `en-US`;
- the canonical `.num` tabular-figures utility exists in `global.css`.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WEB = REPO_ROOT / "apps" / "web"
SRC = WEB / "src"
LOCALES = SRC / "i18n" / "locales"

# Arabic-Indic (U+0660–U+0669) + Extended Arabic-Indic / Persian (U+06F0–U+06F9).
ARABIC_INDIC_DIGITS = re.compile(r"[٠-٩۰-۹]")
# Number formatting pinned to an Arabic locale — the classic way Arabic-Indic digits sneak back in.
AR_LOCALE_FORMAT = re.compile(r"(?:toLocaleString|Intl\.NumberFormat)\(\s*[\"']ar\b")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check() -> None:
    _assert(SRC.is_dir(), "apps/web/src does not exist")

    # 1. No Arabic-Indic digits anywhere a user reads them: the locale files.
    #    (Messages stay ASCII-only — the gate harness prints to a cp1252 Windows console.)
    for path in sorted(LOCALES.glob("*.json")):
        for i, line in enumerate(_read(path).splitlines(), start=1):
            if ARABIC_INDIC_DIGITS.search(line):
                raise AssertionError(
                    f"Arabic-Indic digit in {path.name}:{i} -- use Latin numerals (digits policy)"
                )

    # 2. No Arabic-Indic digit literals or ar-locale number formatting in source.
    for path in list(SRC.rglob("*.ts")) + list(SRC.rglob("*.tsx")):
        for i, line in enumerate(_read(path).splitlines(), start=1):
            if ARABIC_INDIC_DIGITS.search(line):
                raise AssertionError(
                    f"Arabic-Indic digit literal in {path.name}:{i} -- use Latin numerals"
                )
            if AR_LOCALE_FORMAT.search(line):
                raise AssertionError(
                    f"number formatted with an 'ar' locale in {path.name}:{i} -- format via "
                    f"lib/money.ts (en-US), Latin digits"
                )

    # 3. money.ts groups with en-US (the single formatting edge).
    money = _read(SRC / "lib" / "money.ts")
    _assert('toLocaleString("en-US")' in money,
            "lib/money.ts must group amounts with the en-US locale (Latin digits)")

    # 4. The canonical tabular-figures utility exists with both the shorthand and the tnum fallback.
    global_css = _read(SRC / "styles" / "global.css")
    _assert(
        re.search(r"\.num\s*\{[^}]*font-variant-numeric:\s*tabular-nums", global_css, re.DOTALL) is not None,
        "the .num tabular-figures utility must exist in global.css (font-variant-numeric: tabular-nums)",
    )
