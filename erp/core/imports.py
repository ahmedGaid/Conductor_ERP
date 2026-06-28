"""Generic CSV import engine — the thin batch layer over the existing DRF serializers.

A new company arrives with its customers / suppliers / products already in Excel. This module turns
a messy, real-world CSV (Arabic-from-Excel encodings, Arabic-Indic digits, human money) into clean
master rows, reusing each entity's existing serializer as the single source of truth for field
validation. It owns only what single-create lacks: encoding normalisation, header mapping,
business-key existence resolution, and a row-level outcome report.

The rulings this implements are recorded in DECISIONS.md "Phase 2.0 — CSV import friction decisions".
Each list (Customers, Suppliers, Items, ...) declares an :class:`ImportSpec`; the engine does the
rest. Preview and commit run the SAME code path (``dry_run`` only gates the final write) so a preview
can never lie.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable

from django.db import transaction

# ── Encoding + text normalisation ────────────────────────────────────────────
# Egyptian SMBs "Save As CSV" from Arabic Excel, which writes Windows-1256 (legacy code page);
# "CSV UTF-8" prepends a UTF-8 BOM. utf-8-sig strips the BOM and decodes plain UTF-8; cp1256 maps
# every byte so it never raises — the right last resort for a legacy Arabic file.
_ENCODINGS = ("utf-8-sig", "cp1256")

# Arabic-Indic (٠-٩) and Eastern/Persian (۰-۹) digits → ASCII; Arabic decimal (٫) / thousands (٬).
_DIGIT_MAP = str.maketrans(
    {
        **{ord("٠") + i: str(i) for i in range(10)},
        **{ord("۰") + i: str(i) for i in range(10)},
        ord("٫"): ".",
        ord("٬"): "",
        ord(" "): "",  # non-breaking space (Excel thousands)
    }
)


def decode_csv(raw: bytes) -> str:
    """Decode uploaded bytes to text, tolerating Arabic-from-Excel encodings and a stray BOM."""
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _sniff_delimiter(sample: str) -> str:
    # Arabic/European Excel writes ';'; tab-separated also shows up. Default to ','.
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        return ","


def read_table(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Parse uploaded CSV bytes into (headers, rows). Rows are dicts keyed by the trimmed header."""
    text = unicodedata.normalize("NFC", decode_csv(raw))
    sample = "\n".join(text.splitlines()[:10])
    reader = csv.DictReader(io.StringIO(text), delimiter=_sniff_delimiter(sample))
    headers = [(h or "").strip() for h in (reader.fieldnames or [])]
    rows: list[dict[str, str]] = []
    for raw_row in reader:
        # csv.DictReader puts overflow columns under the None key; ignore them.
        rows.append({(k or "").strip(): (v or "").strip() for k, v in raw_row.items() if k is not None})
    return headers, rows


def _fold(s: str) -> str:
    """Lower-case + strip diacritics + collapse spaces — for header/alias matching only."""
    decomposed = unicodedata.normalize("NFKD", s)
    no_marks = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(no_marks.lower().split())


# ── Field + value coercion ───────────────────────────────────────────────────
FieldKind = str  # "text" | "int" | "money" | "decimal" | "bool"

_TRUE = {"1", "true", "yes", "y", "t", "نعم", "صح", "فعال", "نشط"}
_FALSE = {"0", "false", "no", "n", "f", "لا", "خطأ", "غير فعال", "متوقف", ""}


def _parse_decimal(raw: str) -> Decimal:
    """Parse a human number: Arabic-Indic digits, Arabic/European separators, thousands grouping."""
    s = raw.translate(_DIGIT_MAP).strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(",", "")            # comma is the thousands group, dot is the decimal
    elif "," in s:
        s = s.replace(",", ".")           # lone comma is a European decimal separator
    return Decimal(s)


@dataclass(frozen=True)
class ImportField:
    """One canonical column. ``target`` is the serializer key (defaults to ``name``)."""

    name: str
    label_en: str
    label_ar: str
    kind: FieldKind = "text"
    required: bool = False
    target: str = ""
    aliases: tuple[str, ...] = ()
    example: str = ""

    @property
    def serializer_key(self) -> str:
        return self.target or self.name

    def match_terms(self) -> set[str]:
        terms = {self.name, self.label_en, self.label_ar, *self.aliases}
        return {_fold(t) for t in terms if t}


def coerce(field_: ImportField, raw: str) -> tuple[object, str | None]:
    """Convert a raw cell to the serializer's expected type. Returns (value, error_message)."""
    raw = raw.strip()
    if field_.kind == "text":
        return raw, None
    if field_.kind == "bool":
        token = _fold(raw)
        if token in _TRUE:
            return True, None
        if token in _FALSE:
            return False, None
        return None, "not a yes/no value"
    # Numeric kinds share one parser; empty optional cells fall through to the serializer default.
    if raw == "":
        return "", None
    try:
        dec = _parse_decimal(raw)
    except (InvalidOperation, ValueError):
        return None, "not a number"
    if field_.kind == "int":
        return int(dec), None
    if field_.kind == "money":
        # Human major units (pounds) → integer minor units, at the edge (the money rule).
        return int((dec * 100).to_integral_value(rounding="ROUND_HALF_UP")), None
    if field_.kind == "decimal":
        return dec, None
    return raw, None


# ── Spec + results ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ImportSpec:
    """Everything the engine needs to import one list end-to-end."""

    key: str                                   # business-key field name (unique: code / sku)
    model: type                                # Django model for existence + persistence
    serializer: type                           # DRF serializer reused for field validation
    fields: tuple[ImportField, ...]
    # Map validated serializer data → model create/update kwargs. Default = pass through. May append
    # row errors (e.g. an FK code that resolves to nothing) by mutating ``errors``.
    to_kwargs: Callable[[dict, list[dict]], dict] | None = None
    # When True, skip the DB existence check and always create (for entities without a single-column
    # unique business key, e.g. price-list lines scoped to a specific list).
    skip_existence_check: bool = False
    # When set, in-file deduplication uses the concatenation of these data field values (joined by
    # "|") instead of the single ``key`` field. Use for compound-keyed rows (e.g. sku + min_quantity).
    composite_dedup_fields: tuple[str, ...] | None = None

    def field_by_name(self, name: str) -> ImportField | None:
        return next((f for f in self.fields if f.name == name), None)


@dataclass
class RowResult:
    row: int                                   # 1-based source row number (header = row 1)
    outcome: str                               # created | updated | skipped | failed
    errors: list[dict] = field(default_factory=list)
    key: str = ""


@dataclass
class ImportResult:
    headers: list[str]
    mapping: dict[str, str]
    rows: list[RowResult]
    committed: bool

    @property
    def summary(self) -> dict[str, int]:
        s = {"total": len(self.rows), "created": 0, "updated": 0, "skipped": 0, "failed": 0}
        for r in self.rows:
            s[r.outcome] = s.get(r.outcome, 0) + 1
        return s


def auto_map(headers: list[str], spec: ImportSpec) -> dict[str, str]:
    """Propose {canonical_field_name: source_header} by folding both sides (Arabic-insensitive)."""
    folded = {_fold(h): h for h in headers if h}
    mapping: dict[str, str] = {}
    for f in spec.fields:
        for term in f.match_terms():
            if term in folded:
                mapping[f.name] = folded[term]
                break
    return mapping


# ── The engine ───────────────────────────────────────────────────────────────
def run_import(
    spec: ImportSpec,
    headers: list[str],
    rows: list[dict[str, str]],
    mapping: dict[str, str],
    *,
    mode: str = "create",      # "create" (skip existing) | "upsert" (update existing)
    dry_run: bool = True,
    user=None,
) -> ImportResult:
    """Validate + (optionally) persist every row independently, returning a row-level report.

    Same code path for preview and commit — ``dry_run`` only gates the final write. Each row is
    isolated in its own savepoint so one bad row can't poison the batch (partial success).
    """
    results: list[RowResult] = []
    seen_keys: dict[str, int] = {}             # business key → first row number, for in-file dupes

    for offset, row in enumerate(rows):
        row_no = offset + 2                     # +1 for 0-based, +1 for the header line
        errors: list[dict] = []
        data: dict = {}

        # 1. Coerce each mapped field to the serializer's expected type.
        for f in spec.fields:
            source = mapping.get(f.name)
            raw = (row.get(source, "") if source else "").strip()
            if raw == "":
                if f.required:
                    errors.append({"field": f.name, "message": "required"})
                continue
            value, err = coerce(f, raw)
            if err:
                errors.append({"field": f.name, "message": err})
            else:
                data[f.serializer_key] = value

        # 2. Field validation through the entity's own serializer (one source of truth).
        if not errors:
            ser = spec.serializer(data=data)
            if ser.is_valid():
                data = dict(ser.validated_data)
            else:
                for fname, msgs in ser.errors.items():
                    errors.append({"field": fname, "message": "; ".join(str(m) for m in msgs)})

        if errors:
            results.append(RowResult(row_no, "failed", errors))
            continue

        # 3a. Compute the dedup key (composite or single field).
        if spec.composite_dedup_fields:
            key_value = "|".join(str(data.get(f, "") or "") for f in spec.composite_dedup_fields)
        else:
            key_value = str(data.get(spec.key, "")).strip()

        # 3b. Duplicate within the same file (the first wins; later ones are reported, not silent).
        if key_value in seen_keys:
            results.append(RowResult(
                row_no, "failed", key=key_value,
                errors=[{"field": spec.key, "message": f"duplicate of row {seen_keys[key_value]}"}],
            ))
            continue
        seen_keys[key_value] = row_no

        # 4. Resolve any FKs / build model kwargs (a missing reference is a row error, not a null).
        if spec.to_kwargs is not None:
            kwargs = spec.to_kwargs(data, errors)
            if errors:
                results.append(RowResult(row_no, "failed", errors, key=key_value))
                continue
        else:
            kwargs = dict(data)

        # 5. Existence by business key drives the outcome; never blind-insert.
        if spec.skip_existence_check:
            existing = None
            outcome = "created"
        else:
            existing = spec.model.objects.filter(**{spec.key: key_value}).first()
            if existing and mode != "upsert":
                results.append(RowResult(row_no, "skipped", key=key_value))
                continue
            outcome = "updated" if existing else "created"
        if not dry_run:
            try:
                with transaction.atomic():     # per-row savepoint
                    _persist(spec, existing, kwargs, user)
            except Exception as exc:           # noqa: BLE001 — surface, isolate, continue
                results.append(RowResult(
                    row_no, "failed", key=key_value,
                    errors=[{"field": spec.key, "message": str(exc)}],
                ))
                continue
        results.append(RowResult(row_no, outcome, key=key_value))

    return ImportResult(headers, mapping, results, committed=not dry_run)


def _persist(spec: ImportSpec, existing, kwargs: dict, user) -> None:
    if existing:
        for attr, value in kwargs.items():
            setattr(existing, attr, value)
        existing.save()
    else:
        create_kwargs = dict(kwargs)
        if user is not None and getattr(user, "is_authenticated", False):
            create_kwargs.setdefault("created_by", user)
        spec.model.objects.create(**create_kwargs)


# Synchronous cap for v1 — larger files get documented chunking later, not a v1 async pipeline.
MAX_ROWS = 5000


class ImportError_(ValueError):
    """A whole-file problem (bad encoding result, no rows, too many rows) — not a per-row error."""


def import_from_upload(
    spec: ImportSpec,
    raw: bytes,
    mapping: dict[str, str] | None,
    *,
    mode: str = "create",
    commit: bool = False,
    user=None,
) -> ImportResult:
    """Read the upload, resolve the column mapping, and run the import (preview or commit)."""
    headers, rows = read_table(raw)
    if not headers:
        raise ImportError_("the file has no header row")
    if len(rows) > MAX_ROWS:
        raise ImportError_(f"too many rows ({len(rows)}); split into files of {MAX_ROWS} or fewer")
    resolved = mapping or auto_map(headers, spec)
    return run_import(spec, headers, rows, resolved, mode=mode, dry_run=not commit, user=user)


def result_payload(result: ImportResult) -> dict:
    """JSON-serialisable response body for the import endpoint."""
    return {
        "headers": result.headers,
        "mapping": result.mapping,
        "summary": result.summary,
        "committed": result.committed,
        "rows": [
            {"row": r.row, "outcome": r.outcome, "key": r.key, "errors": r.errors}
            for r in result.rows
        ],
    }


def template_csv(spec: ImportSpec) -> bytes:
    """A UTF-8 (BOM) template: canonical headers + one example row, so the columns are obvious."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f.name for f in spec.fields])
    writer.writerow([f.example for f in spec.fields])
    return buf.getvalue().encode("utf-8-sig")   # BOM so Excel opens it as UTF-8
