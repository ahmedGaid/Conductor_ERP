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
