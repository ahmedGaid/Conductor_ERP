"""Import intelligence (plan session 14): inspect → map → preview → confirm → report.

The N-rows sibling of ``services.actions``: the same propose→confirm→execute discipline, at
spreadsheet scale. Three actor-scoped phases over an uploaded CSV/XLSX attachment:

  inspect  — one model call maps the file's headers onto a target's fields; code validates the map.
  preview  — dry-run every row through parse + duplicate checks, WITHOUT writing.
  execute  — create the valid, non-duplicate rows one by one via the module contract, AS the actor.

Targets are the three list records a business seeds first: customers, suppliers, items. Each row is
created through the very contract a single manual create uses (never ``bulk_create`` around
validation), so RBAC, business rules and audit hold identically to typing the record in by hand.

None of the three targets reference another record at create time (a customer/supplier is a name; an
item's unit-of-measure is a free string, not an FK — there is no UoM or warehouse dependency on
``Item``). So there is no missing-reference guided detour here, unlike the plan's generic note: a bad
row is a plain, listed error and a matching row a listed skip. The blocker/suggestion vocabulary
stays owned by ``actions``/``suggestions`` for the single-record write path.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

from erp.audit import services as audit
from erp.identity.roles import BRANCH_MANAGER
from erp.inventory import contracts as inventory
from erp.purchasing import contracts as purchasing
from erp.sales import contracts as sales

from ..gateway.core import complete_json
from .actions import _can, _refused
from .files import read_table
from .prompt_registry import get as get_prompt

# How many sample rows the inspector shows the model (headers + these → a header→field mapping).
INSPECT_SAMPLE = 5
# How many parsed rows the preview card shows (counts cover the whole file; this is just the peek).
PREVIEW_ROWS = 20


@dataclass(frozen=True)
class Field:
    key: str
    label: str          # human English — shown on the card and given to the model
    required: bool = False
    kind: str = "text"  # text | money | decimal


@dataclass(frozen=True)
class Target:
    key: str
    fields: tuple[Field, ...]
    natural_key: str                    # the field whose value dedupes a row
    exists: Callable[..., bool]         # (actor, value) -> already present?
    create: Callable[..., dict]         # (actor, values) -> EntityLink {type, value, label}


# --- per-target duplicate + create bridges (thin wrappers over the module contracts) ------------

def _customer_exists(actor, name: str) -> bool:
    return sales.customer_name_exists(actor, name)


def _create_customer(actor, values: dict) -> dict:
    info = sales.create_customer(
        name=values["name"], code=values.get("code", ""),
        credit_limit_minor=values.get("credit_limit_minor", 0), actor=actor,
    )
    return {"type": "customer", "value": info.code, "label": info.name}


def _supplier_exists(actor, name: str) -> bool:
    return purchasing.supplier_name_exists(name)


def _create_supplier(actor, values: dict) -> dict:
    info = purchasing.create_supplier(name=values["name"], code=values.get("code", ""), actor=actor)
    return {"type": "supplier", "value": info.code, "label": info.name}


def _item_exists(actor, sku: str) -> bool:
    return inventory.item_sku_exists(sku)


def _create_item(actor, values: dict) -> dict:
    info = inventory.create_item(
        sku=values["sku"], name=values["name"], uom=values.get("uom", "unit"),
        reorder_point=values.get("reorder_point", 0), actor=actor,
    )
    return {"type": "item", "value": info.sku, "label": info.name}


TARGETS: dict[str, Target] = {
    "customers": Target(
        "customers",
        (Field("name", "Customer name", required=True),
         Field("code", "Customer code"),
         Field("credit_limit_minor", "Credit limit", kind="money")),
        natural_key="name", exists=_customer_exists, create=_create_customer,
    ),
    "suppliers": Target(
        "suppliers",
        (Field("name", "Supplier name", required=True),
         Field("code", "Supplier code")),
        natural_key="name", exists=_supplier_exists, create=_create_supplier,
    ),
    "items": Target(
        "items",
        (Field("sku", "SKU", required=True),
         Field("name", "Item name", required=True),
         Field("uom", "Unit of measure"),
         Field("reorder_point", "Reorder point", kind="decimal")),
        natural_key="sku", exists=_item_exists, create=_create_item,
    ),
}

# Union of every field key across targets — the (fixed) shape the inspector model fills.
_ALL_FIELD_KEYS = tuple(dict.fromkeys(f.key for t in TARGETS.values() for f in t.fields))

_inspect_prompt = get_prompt("import_inspect")

_INSPECT_SYSTEM = _inspect_prompt.template

_INSPECT_SCHEMA = {
    "type": "object",
    "properties": {
        "target": {"type": "string", "enum": list(TARGETS.keys())},
        "mapping": {
            "type": "object",
            "properties": {k: {"type": ["string", "null"]} for k in _ALL_FIELD_KEYS},
            "required": list(_ALL_FIELD_KEYS),
            "additionalProperties": False,
        },
    },
    "required": ["target", "mapping"],
    "additionalProperties": False,
}


def _sample_dicts(header: list[str], rows: list[list], limit: int) -> list[dict]:
    """The first ``limit`` rows as ``{header: cell}`` dicts (blank cells → "")."""
    out: list[dict] = []
    for row in rows[:limit]:
        out.append({h: ("" if i >= len(row) or row[i] is None else str(row[i]))
                    for i, h in enumerate(header)})
    return out


def _clean_mapping(target: Target, raw_mapping: dict, header: list[str]) -> dict:
    """Keep only this target's fields, mapped to headers that actually exist. A field the model left
    null gets a light exact-name fallback (header equals the field key or label, case-insensitive)."""
    header_by_key = {h.casefold().strip(): h for h in header}
    mapping: dict[str, str | None] = {}
    for f in target.fields:
        col = raw_mapping.get(f.key)
        if isinstance(col, str) and col in header:
            mapping[f.key] = col
            continue
        # Fallback: a header literally named like the field.
        guess = header_by_key.get(f.key.casefold()) or header_by_key.get(f.label.casefold())
        mapping[f.key] = guess
    return mapping


def _card_fields(target: Target) -> list[dict]:
    return [{"key": f.key, "label": f.label, "required": f.required} for f in target.fields]


def inspect(actor, attachment, target_hint: str | None = None) -> dict:
    """Sniff a tabular attachment and propose a header→field mapping for one target.

    One ``complete_json`` call maps headers to fields (the model also picks the target unless
    ``target_hint`` names a valid one); code then validates the mapping against the field spec.
    Returns ``{target, fields, columns, mapping, sample, row_count, issues}`` — or ``{error}`` when
    the actor can't create records or the file has no rows.
    """
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    header, rows = read_table(attachment)
    if not header or not rows:
        return {"error": "That file has no rows to import. Attach a CSV or Excel file with a header "
                         "row and at least one data row."}

    hint = (target_hint or "").strip().lower()
    result = complete_json(
        _INSPECT_SYSTEM,
        json.dumps({"columns": header, "sample_rows": _sample_dicts(header, rows, INSPECT_SAMPLE),
                    "target_hint": hint or None}, ensure_ascii=False),
        _INSPECT_SCHEMA,
    )
    target_key = hint if hint in TARGETS else (result.get("target") or "").strip().lower()
    target = TARGETS.get(target_key)
    if target is None:  # model returned nothing usable and no valid hint — ask which list this is
        return {"error": "I couldn't tell what this spreadsheet is a list of. Tell me whether it's "
                         "customers, suppliers, or items."}

    mapping = _clean_mapping(target, result.get("mapping") or {}, header)
    issues = [f"No column maps to {f.label}." for f in target.fields
              if f.required and not mapping.get(f.key)]
    return {
        "target": target.key,
        "fields": _card_fields(target),
        "columns": header,
        "mapping": mapping,
        "sample": _sample_dicts(header, rows, INSPECT_SAMPLE),
        "row_count": len(rows),
        "issues": issues,
    }


def as_card(inspected: dict, attachment_id: int) -> dict:
    """Wrap an ``inspect`` result into the stepped card persisted in a message's ``meta`` (the loop
    and the inspect endpoint both start the card here, at the mapping stage)."""
    return {**inspected, "attachment_id": attachment_id, "stage": "mapping"}


# --- row parsing ---------------------------------------------------------------------------------

def _to_minor(raw: str) -> int | None:
    try:
        return int((Decimal(raw) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        return None


def _cell(header_idx: dict, row: list, col: str | None) -> str:
    if not col or col not in header_idx:
        return ""
    i = header_idx[col]
    if i >= len(row) or row[i] is None:
        return ""
    return str(row[i]).strip()


def _parse_row(target: Target, mapping: dict, header_idx: dict, row: list) -> tuple[dict, list[dict]]:
    """One raw row → ``(typed_values, field_errors)`` against the target's field spec. Errors carry
    the field key + a blame-free message; a valid row's values are ready for the create contract."""
    values: dict = {}
    errors: list[dict] = []
    for f in target.fields:
        raw = _cell(header_idx, row, mapping.get(f.key))
        if not raw:
            if f.required:
                errors.append({"field": f.key, "message": f"{f.label} is missing."})
            continue
        if f.kind == "money":
            minor = _to_minor(raw)
            if minor is None:
                errors.append({"field": f.key, "message": f"{f.label} isn't a valid amount."})
            else:
                values[f.key] = minor
        elif f.kind == "decimal":
            try:
                values[f.key] = str(Decimal(raw))
            except InvalidOperation:
                errors.append({"field": f.key, "message": f"{f.label} isn't a valid number."})
        else:
            values[f.key] = raw
    return values, errors


def _prepare(actor, attachment, mapping: dict, target: Target):
    """Shared read + per-row classification for preview and execute. Yields, per data row (1-based):
    ``(row_no, values, errors, dup_reason)`` where ``dup_reason`` is "file"/"exists"/None. Duplicate
    detection uses the natural key, in-file first (a key seen earlier this file) then the database."""
    header, rows = read_table(attachment)
    header_idx = {h: i for i, h in enumerate(header)}
    seen: set[str] = set()
    for n, row in enumerate(rows, start=1):
        values, errors = _parse_row(target, mapping, header_idx, row)
        dup: str | None = None
        if not errors:
            key = (values.get(target.natural_key) or "").casefold()
            if key in seen:
                dup = "file"
            elif target.exists(actor, values[target.natural_key]):
                dup = "exists"
            else:
                seen.add(key)
        yield n, values, errors, dup


def preview(actor, attachment, mapping: dict, target_key: str) -> dict:
    """Dry-run every row: parse, validate, and duplicate-check WITHOUT writing. Returns
    ``{valid, errors, duplicates, rows}`` — counts over the whole file, ``rows`` the first parsed
    peek. ``errors`` are ``{row, field, message}``; ``duplicates`` ``{row, key}`` (all default-skip)."""
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    target = TARGETS.get(target_key)
    if target is None:
        return {"error": "Unknown import target."}
    mapping = {f.key: mapping.get(f.key) for f in target.fields}

    valid = 0
    errors: list[dict] = []
    duplicates: list[dict] = []
    rows: list[dict] = []
    for n, values, row_errors, dup in _prepare(actor, attachment, mapping, target):
        if row_errors:
            errors.extend({"row": n, **e} for e in row_errors)
            continue
        if dup:
            duplicates.append({"row": n, "key": values[target.natural_key]})
            continue
        valid += 1
        if len(rows) < PREVIEW_ROWS:
            rows.append({"row": n, **values})
    return {"valid": valid, "errors": errors, "duplicates": duplicates, "rows": rows}


def execute(actor, attachment, mapping: dict, target_key: str) -> dict:
    """Create the valid, non-duplicate rows one by one via the module contract, as the actor. Error
    and duplicate rows are skipped and reported, never written. One ``audit.record`` stamps the batch.
    Returns ``{created, skipped, errors, report, links}`` — ``report`` a per-row outcome list (drives
    the downloadable CSV), ``links`` a sample of created records."""
    if not _can(actor, BRANCH_MANAGER):
        return _refused()
    target = TARGETS.get(target_key)
    if target is None:
        return {"error": "Unknown import target."}
    mapping = {f.key: mapping.get(f.key) for f in target.fields}

    created = 0
    skipped = 0
    errors: list[dict] = []
    report: list[dict] = []
    links: list[dict] = []
    for n, values, row_errors, dup in _prepare(actor, attachment, mapping, target):
        if row_errors:
            skipped += 1
            errors.extend({"row": n, **e} for e in row_errors)
            report.append({"row": n, "status": "error", "key": values.get(target.natural_key, ""),
                           "message": "; ".join(e["message"] for e in row_errors)})
            continue
        if dup:
            skipped += 1
            report.append({"row": n, "status": "skipped", "key": values[target.natural_key],
                           "message": "Already exists" if dup == "exists" else "Duplicate in file"})
            continue
        try:
            link = target.create(actor, values)
        except Exception:  # a contract-level rejection — skip the row, keep the batch going
            skipped += 1
            errors.append({"row": n, "field": target.natural_key, "message": "Could not be created."})
            report.append({"row": n, "status": "error", "key": values[target.natural_key],
                           "message": "Could not be created."})
            continue
        created += 1
        report.append({"row": n, "status": "created", "key": link["value"], "message": ""})
        if len(links) < 5:
            links.append(link)

    audit.record(module="assistant", action="import", entity_type="Import", entity_id=target.key,
                 actor=actor, after={"created": created, "skipped": skipped, "target": target.key})
    return {"created": created, "skipped": skipped, "errors": errors, "report": report, "links": links}
