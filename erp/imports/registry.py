"""Adapter registry — the seam between the module-agnostic engine and each business module.

**The engine never imports a business-module model directly; only adapters do.** Every module that
wants to be importable registers one ``ImportAdapter`` describing its entity: the field spec (with
Arabic/English header synonyms), the natural key used for duplicate/existing matching, and the four
verbs the engine drives — ``lookup`` (resolve a reference), ``validate`` (rules beyond the field
spec), ``write`` (call the module's EXISTING service write-path), and ``exists`` (natural-key
fetch). Import never invents a second write-path and never bulk-creates around validation.

Adapters live in ``erp/imports/adapters/`` (one file per module) and call ``register(...)`` at
import time. The engine only ever touches modules through ``get(entity)`` — so grepping the core
for ``from erp.sales`` etc. returns nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# Field kinds the normalizers (FILE_04) and validators (FILE_06) key off.
FIELD_KINDS = frozenset({"text", "number", "money", "date", "ref", "enum"})


@dataclass
class FieldSpec:
    """One target field of an entity: how to recognize its column and what shape it holds."""

    name: str
    required: bool = False
    kind: str = "text"  # one of FIELD_KINDS
    ref: str | None = None  # registry entity to resolve against, when kind == "ref"
    enum: list[str] = field(default_factory=list)  # allowed values, when kind == "enum"
    synonyms_en: list[str] = field(default_factory=list)
    synonyms_ar: list[str] = field(default_factory=list)
    default: Any = None

    def __post_init__(self) -> None:
        if self.kind not in FIELD_KINDS:
            raise ValueError(
                f"FieldSpec {self.name!r}: unknown kind {self.kind!r} (expected one of {sorted(FIELD_KINDS)})",
            )


@dataclass
class Issue:
    """A single validation problem on a row — carried in ``ImportRow.issues`` as a dict."""

    field: str
    code: str
    message: str  # i18n key or already-translated human line; blame-free (spec)
    # Structured extra data for issues a later step must act on (session 06: "missing_ref" carries
    # {"entity": ..., "value": ...} so session 08's auto-create-masters flow doesn't re-parse the
    # message string). Empty for every other issue code — never required reading.
    meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"field": self.field, "code": self.code, "message": self.message}
        if self.meta:
            d["meta"] = self.meta
        return d


@runtime_checkable
class ImportAdapter(Protocol):
    """What every importable entity must provide. Adapters are stateless singletons."""

    entity: str  # unique registry key, e.g. "customers"
    label_key: str  # i18n key for the human name — never a hardcoded label
    fields: list[FieldSpec]
    natural_key: list[str]  # field names that identify an existing record
    group_by: str | None  # None for masters; header column that groups rows into one document

    def lookup(self, actor: Any, field: str, value: Any) -> Any | None:
        """Resolve a reference value (e.g. customer code) to a DB record, or None."""
        ...

    def validate(self, actor: Any, row: dict) -> list[Issue]:
        """Entity-specific checks beyond the field spec. Return [] when the row is clean."""
        ...

    def write(self, actor: Any, row: dict) -> object:
        """Create/update the record via the module's existing service write-path; return it."""
        ...

    def exists(self, actor: Any, row: dict) -> object | None:
        """Fetch the existing record matching this row's natural key, or None."""
        ...

    # ``exists_many(actor, rows: list[dict]) -> list[object | None]`` is an OPTIONAL, duck-typed
    # batched equivalent (getattr'd in ``validate._build_exists_cache``, exactly like ``update``/
    # ``delete``/``header_fields`` below) — one or two queries for the whole batch instead of one
    # ``exists`` call per row. Results must align 1:1 with the input order. Every adapter whose
    # ``exists`` can plausibly run at import volume (customers, suppliers, items, documents…)
    # implements it; an adapter without one just falls back to the O(rows) per-row loop, correct
    # but the reason a 100k-row validate pass took 100k individual DB round-trips before this was
    # added (FILE_17 acceptance finding).

    def existing_labels(self, actor: Any) -> list[tuple[Any, str]]:
        """(pk, name) pairs for every existing record, RBAC/data-scoped like ``exists`` — the fuzzy
        duplicate pass's one prefetch per entity (session 07). Empty for an entity with no
        name-like field."""
        ...


# The live registry. Keyed by ``adapter.entity``.
REGISTER: dict[str, ImportAdapter] = {}


def register(adapter: ImportAdapter) -> ImportAdapter:
    """Register an adapter. Raises on a duplicate entity key (a wiring bug, never silent)."""
    entity = adapter.entity
    if entity in REGISTER:
        raise ValueError(f"import adapter for entity {entity!r} is already registered")
    REGISTER[entity] = adapter
    return adapter


def get(entity: str) -> ImportAdapter:
    """Return the adapter for ``entity``. Raises KeyError with a clear message if unknown."""
    try:
        return REGISTER[entity]
    except KeyError:
        known = ", ".join(sorted(REGISTER)) or "(none registered)"
        raise KeyError(f"no import adapter for entity {entity!r}; known: {known}") from None


def entities() -> list[str]:
    """All registered entity keys, sorted — for the wizard's entity picker / API listing."""
    return sorted(REGISTER)


# --- grouping (document adapters — FILE_15) ------------------------------------------------------
# A document adapter (``group_by`` set — e.g. ``sales_invoices``) also carries an optional
# ``header_fields: list[str]`` — the field NAMES that are one-per-document (customer, date,
# currency, …) rather than one-per-line (item, qty, price). It is duck-typed via ``getattr`` in
# ``engine.py``, exactly like ``supports_update``/``update``/``delete`` above: no adapter without
# ``group_by`` needs it, so it is never added to the ``ImportAdapter`` Protocol itself (that would
# force every throwaway test adapter and every master adapter to declare an empty list for no
# reason). Absent ``header_fields`` on a grouped adapter simply means the engine skips the
# header-consistency check (every field free to vary row-to-row) — a lesser guarantee, not a crash.


def batch_lookup_code_or_name(
    qs, rows: list[dict], *,
    code_field: str = "code", name_field: str = "name", code_case_insensitive: bool = False,
):
    """Shared ``exists_many`` body for the common "unique code (or email), else case-insensitive
    name" natural key (customers, suppliers, contacts, …) — one query for every distinct code, one
    for every distinct name needing the fallback, then an in-memory dict lookup per row. Reused
    across adapter modules instead of each reimplementing the same batching. ``code_case_insensitive``
    covers fields like email that the single-row ``exists`` matched with ``__iexact``."""
    from django.db.models.functions import Lower

    codes = {(r.get(code_field) or "").strip() for r in rows}
    codes.discard("")
    names = {
        (r.get(name_field) or "").strip().lower()
        for r in rows if not (r.get(code_field) or "").strip()
    }
    names.discard("")

    by_code = {}
    if codes:
        if code_case_insensitive:
            lower_codes = {c.lower() for c in codes}
            matched = qs.annotate(_lcode=Lower(code_field)).filter(_lcode__in=lower_codes)
            by_code = {obj._lcode: obj for obj in matched}
        else:
            by_code = {getattr(obj, code_field): obj for obj in qs.filter(**{f"{code_field}__in": codes})}
    by_name = {}
    if names:
        matched = qs.annotate(_lname=Lower(name_field)).filter(_lname__in=names)
        by_name = {obj._lname: obj for obj in matched}

    results = []
    for r in rows:
        code = (r.get(code_field) or "").strip()
        if code:
            key = code.lower() if code_case_insensitive else code
            results.append(by_code.get(key))
        else:
            results.append(by_name.get((r.get(name_field) or "").strip().lower()))
    return results


def batch_lookup_by_tagged_field(
    qs, groups: list[dict], *, field: str = "notes", prefix: str, key_field: str = "doc_number",
):
    """Shared ``exists_many`` body for the document adapters (quotations/orders/invoices/journal
    entries) that tag their created record with ``{field}=f"{prefix}{doc_number}"`` (``notes`` for
    sales/purchasing documents, ``reference`` for journal entries) — one ``{field}__in`` query for
    the whole batch instead of one ``.filter({field}=...).first()`` per group."""
    tags = {(g.get(key_field) or "").strip() for g in groups}
    tags.discard("")
    by_tag = {}
    if tags:
        wanted = {f"{prefix}{t}" for t in tags}
        by_tag = {getattr(obj, field): obj for obj in qs.filter(**{f"{field}__in": wanted})}
    return [by_tag.get(f"{prefix}{(g.get(key_field) or '').strip()}") for g in groups]


def group_key(adapter, normalized: dict) -> Any | None:
    """The row's group key for a grouped (document) adapter, or ``None`` when ``adapter.group_by``
    is unset (every master adapter today) or the row's group column is blank/whitespace.

    A blank key is never treated as its own key — the engine reads that as "continuation row of
    whatever group came before it" (the flat-Excel merged-cell export pattern: document fields
    filled only on the first line of each document)."""
    if not adapter.group_by:
        return None
    value = normalized.get(adapter.group_by)
    if isinstance(value, str):
        value = value.strip()
    return value or None
