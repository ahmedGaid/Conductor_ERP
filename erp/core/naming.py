"""Bilingual record names.

Reference data the user reads by name — chart-of-accounts nodes, branches, departments, price
lists — carries `name` (canonical English) plus `name_ar`. The wire format sends **both** so the
client picks by its own active language; the server never guesses a locale from headers.

`localized_name` is the server-side fallback for the places that must render a single string
(exports, PDFs, notification bodies) rather than hand a pair to a client.
"""
from __future__ import annotations


def localized_name(obj, lang: str = "en") -> str:
    """The record's name in `lang`, falling back to the canonical name when the Arabic one is blank."""
    if lang == "ar":
        return getattr(obj, "name_ar", "") or obj.name
    return obj.name


def name_fields(obj) -> dict[str, str]:
    """The `{name, name_ar}` pair every bilingual-name serializer puts on the wire."""
    return {"name": obj.name, "name_ar": getattr(obj, "name_ar", "") or ""}
