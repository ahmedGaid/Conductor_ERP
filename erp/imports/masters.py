"""Automatic master-data creation from `missing_ref` issues — plan session 08.

``validate.py`` already stamps a row's unresolved reference as a ``missing_ref`` issue carrying
``{entity, value}`` (session 06). ``build_creation_plan`` turns every DISTINCT ``(entity, value)``
pair across a batch into ONE proposed record — never one confirm per row (spec step 7 / STRATEGY
§3 mechanic 3: writes are human-in-the-loop, auto-create is auto-PROPOSED, one-click-confirmed,
never silent). When an existing record scores >= the fuzzy-duplicate threshold (``duplicates.py``,
session 07) against the missing value, the entry proposes LINKING to it instead of creating a
near-duplicate. Nothing is written until ``execute_creation_plan`` runs the caller-approved subset.

No registered adapter has a "ref" field yet (FILE_05/06 note: document adapters — sales orders
referencing customers, purchase orders referencing suppliers, etc. — land in FILE_15/16), so this
module has no real caller in the current codebase; it's exercised the same way ``test_validate.py``
exercises the ref/missing-ref path, against a throwaway ref-bearing test adapter. The registry-
driven design needs no changes once a real ref-bearing adapter is registered.

``item_categories``/``warehouses``/``price_lists``/``units`` have no import adapter at all yet
(same FILE_05 blocker) — a missing_ref pointing at one of those entities gets a
``blocked_unsupported`` plan entry instead of crashing on ``registry.get``.
"""
from __future__ import annotations

from .duplicates import SCORE_THRESHOLD, similarity
from .models import ImportBatch, ImportRow
from .registry import get as get_adapter
from .validate import revalidate_rows

# A ref entity that ITSELF has ref fields must be created before whatever references it (e.g. a
# unit/category before the item that names it). No registered adapter has a ref-of-a-ref today, so
# this is a documented seam for FILE_15/16, not dead code — entities not listed here sort after the
# listed ones, in encounter order (stable sort).
_DEPENDENCY_ORDER: tuple[str, ...] = ("units", "categories", "warehouses", "items")


def build_creation_plan(actor, batch: ImportBatch) -> dict:
    """Scan ``batch``'s ``missing_ref`` issues into one proposed entry per DISTINCT
    ``(entity, value)``: ``{entity, value, action: "create"|"link"|"blocked_unsupported",
    proposed?, link_pk?, editable}``. Saved onto ``batch.stats["creation_plan"]``."""
    entries = [_plan_entry(actor, entity, value) for entity, value in _distinct_missing_refs(batch)]
    entries.sort(key=lambda e: (_dependency_rank(e["entity"]), e["entity"], e["value"]))

    stats = dict(batch.stats or {})
    stats["creation_plan"] = entries
    batch.stats = stats
    batch.save(update_fields=["stats"])
    return {"entries": entries}


def execute_creation_plan(actor, batch: ImportBatch, approved: list[dict]) -> dict:
    """Create/link exactly the entries in ``approved`` (matched by ``entity``+``value`` against the
    stored plan), in dependency order. An entity the actor can't write gets marked
    ``blocked_permission`` and is skipped, not attempted (Task B) — it stays a ``missing_ref``
    blocker. Every row whose ``missing_ref`` now resolves is revalidated so it flips to ``valid``
    without a re-upload (Task A)."""
    stats = dict(batch.stats or {})
    entries = stats.get("creation_plan", [])
    approved_keys = {(a["entity"], a["value"]) for a in approved}
    by_key = {(e["entity"], e["value"]): e for e in entries}

    ordered = sorted(
        (by_key[k] for k in approved_keys if k in by_key and by_key[k]["action"] in ("create", "link")),
        key=lambda e: (_dependency_rank(e["entity"]), e["entity"], e["value"]),
    )

    created_masters: list[dict] = list(stats.get("created_masters", []))
    resolved_keys: set[tuple[str, str]] = set()

    for entry in ordered:
        entity, value = entry["entity"], entry["value"]
        if entry["action"] == "link":
            entry["outcome"] = "linked"
            resolved_keys.add((entity, value))
            continue
        adapter = get_adapter(entity)
        try:
            record = adapter.write(actor, entry["proposed"])
        except PermissionError:
            entry["action"] = "blocked_permission"
            entry["editable"] = False
            continue
        pk = getattr(record, "pk", None) or getattr(record, "id", None) or value
        created_masters.append({"entity": entity, "value": value, "pk": str(pk)})
        entry["outcome"] = "created"
        resolved_keys.add((entity, value))

    stats["creation_plan"] = entries
    stats["created_masters"] = created_masters
    batch.stats = stats
    batch.save(update_fields=["stats"])

    revalidated = _revalidate_affected_rows(actor, batch, resolved_keys)
    return {"resolved": len(resolved_keys), "revalidated": revalidated}


def _distinct_missing_refs(batch: ImportBatch) -> list[tuple[str, str]]:
    seen: dict[tuple[str, str], None] = {}
    for row in batch.rows.filter(status=ImportRow.Status.ERROR):
        for issue in row.issues:
            if issue.get("code") != "missing_ref":
                continue
            meta = issue.get("meta") or {}
            entity, value = meta.get("entity"), meta.get("value")
            if entity and value:
                seen.setdefault((entity, value), None)
    return list(seen)


def _dependency_rank(entity: str) -> int:
    return _DEPENDENCY_ORDER.index(entity) if entity in _DEPENDENCY_ORDER else len(_DEPENDENCY_ORDER)


def _plan_entry(actor, entity: str, value: str) -> dict:
    try:
        adapter = get_adapter(entity)
    except KeyError:
        return {"entity": entity, "value": value, "action": "blocked_unsupported", "editable": False}

    link_pk = _fuzzy_link(actor, adapter, value)
    if link_pk is not None:
        return {"entity": entity, "value": value, "action": "link", "link_pk": str(link_pk), "editable": True}

    return {
        "entity": entity, "value": value, "action": "create",
        "proposed": _default_record(adapter, value), "editable": True,
    }


def _fuzzy_link(actor, adapter, value: str):
    """The strongest existing-record match >= the duplicate threshold, or None — same scoring
    pass as ``duplicates.find_candidates``, just against one incoming value instead of a batch."""
    best_pk, best_score = None, 0
    for pk, label in adapter.existing_labels(actor):
        score = similarity(value, label)
        if score >= SCORE_THRESHOLD and score > best_score:
            best_pk, best_score = pk, score
    return best_pk


def _default_record(adapter, value: str) -> dict:
    """The proposed record: every natural-key field gets ``value`` (there's exactly one missing
    value to work with), then any OTHER required field still unset also falls back to ``value`` —
    an editable placeholder, never a write that KeyErrors on a field we simply don't have data for.
    ``IMPORTS_DEFAULTS`` fills everything else."""
    proposed = dict(getattr(adapter, "defaults", {}) or {})
    for field_name in adapter.natural_key:
        proposed.setdefault(field_name, value)
    for field_spec in adapter.fields:
        if field_spec.required and field_spec.name not in proposed:
            proposed[field_spec.name] = value
    return proposed


def _revalidate_affected_rows(actor, batch: ImportBatch, resolved_keys: set[tuple[str, str]]) -> dict:
    if not resolved_keys:
        return {"valid": 0, "error": 0, "duplicate": 0}
    row_ids = []
    for row in batch.rows.filter(status=ImportRow.Status.ERROR):
        for issue in row.issues:
            if issue.get("code") != "missing_ref":
                continue
            meta = issue.get("meta") or {}
            if (meta.get("entity"), meta.get("value")) in resolved_keys:
                row_ids.append(row.id)
                break
    return revalidate_rows(actor, batch, row_ids)
