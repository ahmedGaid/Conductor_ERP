"""Custom field definitions + values — fields only, NEVER objects (STRATEGY §5).

An entity (currently ``sales.customer`` and ``inventory.item``) may carry admin-defined extra
fields. Definitions are the source of truth for validation, export columns, and the frontend's
dynamic form; values live inline on the owning record's ``custom_data`` JSON column, not in a
side table. Do not generalize this toward dynamic entities/objects — see the plan file's scope
brake.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import models

from erp.core.errors import ValidationError as AppValidationError
from erp.core.exports import Column

ENTITY_CHOICES = (
    ("sales.customer", "Customer"),
    ("inventory.item", "Item"),
)


class FieldType(models.TextChoices):
    TEXT = "TEXT", "Text"
    NUMBER = "NUMBER", "Number"
    DATE = "DATE", "Date"
    CHOICE = "CHOICE", "Choice"
    MONEY = "MONEY", "Money"


class CustomFieldDef(models.Model):
    """One admin-defined field on an entity. ``key`` is immutable once created; deactivating hides
    the field from new writes and from the active-defs endpoint but leaves stored values readable."""

    entity_key = models.CharField(max_length=32, choices=ENTITY_CHOICES)
    key = models.SlugField(max_length=64)
    label_ar = models.CharField(max_length=100)
    label_en = models.CharField(max_length=100)
    type = models.CharField(max_length=16, choices=FieldType.choices)
    required = models.BooleanField(default=False)
    choices = models.JSONField(default=list, blank=True)  # CHOICE type only
    is_active = models.BooleanField(default=True)
    position = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_custom_field_def"
        ordering = ["entity_key", "position", "key"]
        unique_together = [("entity_key", "key")]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.entity_key}.{self.key}"


# --- admin-only service fns (Task A) ------------------------------------------------------------

def create_custom_field_def(
    *, entity_key: str, key: str, label_ar: str, label_en: str, type: str,
    required: bool = False, choices: list | None = None, position: int = 0,
) -> CustomFieldDef:
    if not label_ar or not label_en:
        raise AppValidationError("Both Arabic and English labels are required")
    return CustomFieldDef.objects.create(
        entity_key=entity_key, key=key, label_ar=label_ar, label_en=label_en,
        type=type, required=required, choices=choices or [], position=position,
    )


def update_custom_field_def(def_id, **fields: Any) -> CustomFieldDef:
    """Update a def's editable attributes. ``key``/``entity_key`` are immutable — silently ignored
    if passed (the API layer never sends them; a direct caller passing them is a no-op, not an error)."""
    d = CustomFieldDef.objects.get(pk=def_id)
    fields.pop("key", None)
    fields.pop("entity_key", None)
    for name, value in fields.items():
        setattr(d, name, value)
    d.save()
    return d


def deactivate_custom_field_def(def_id) -> CustomFieldDef:
    """Hide a def from new writes and the active-defs list. Never a hard delete — records that
    already carry this key keep their stored value, readable."""
    d = CustomFieldDef.objects.get(pk=def_id)
    d.is_active = False
    d.save(update_fields=["is_active", "updated_at"])
    return d


def active_defs(entity_key: str):
    return CustomFieldDef.objects.filter(entity_key=entity_key, is_active=True)


# --- values (Task B) -----------------------------------------------------------------------------

def _coerce(field_def: CustomFieldDef, raw: Any) -> Any:
    if field_def.type == FieldType.TEXT:
        return str(raw)
    if field_def.type == FieldType.NUMBER:
        return str(Decimal(str(raw)))  # Decimal-as-str: JSON-safe, no float precision loss
    if field_def.type == FieldType.DATE:
        if isinstance(raw, str):
            dt.date.fromisoformat(raw)  # raises ValueError on a bad format
            return raw
        return raw.isoformat()
    if field_def.type == FieldType.MONEY:
        return int(raw)  # integer minor units
    if field_def.type == FieldType.CHOICE:
        if raw not in (field_def.choices or []):
            raise ValueError(f"{raw!r} is not one of the allowed choices")
        return raw
    raise ValueError(f"unsupported custom field type {field_def.type!r}")


def validate_custom_data(entity_key: str, data: dict[str, Any] | None) -> dict[str, Any]:
    """Clean ``data`` against the entity's *active* defs. Unknown keys are rejected — this also
    covers a deactivated def: once inactive it drops out of the active set, so a new write naming
    it is treated the same as a typo'd key. Reading a record's stored ``custom_data`` never calls
    this — old values under a deactivated key stay visible as-is."""
    data = data or {}
    defs = {d.key: d for d in active_defs(entity_key)}
    errors: dict[str, list[str]] = {}
    cleaned: dict[str, Any] = {}

    for key in data:
        if key not in defs:
            errors[key] = ["Unknown custom field / حقل غير معروف"]

    for key, field_def in defs.items():
        raw = data.get(key)
        if raw in (None, ""):
            if field_def.required:
                errors[key] = [f"{field_def.label_en} is required / {field_def.label_ar} مطلوب"]
            continue
        try:
            cleaned[key] = _coerce(field_def, raw)
        except (TypeError, ValueError, InvalidOperation):
            errors[key] = [
                f"Invalid value for {field_def.label_en} / قيمة غير صالحة لـ {field_def.label_ar}"
            ]

    if errors:
        raise AppValidationError("Custom field validation failed", data={"errors": errors})
    return cleaned


# --- export (Task C) ------------------------------------------------------------------------------

def custom_field_columns(entity_key: str, lang: str = "en") -> list[Column]:
    """Active defs for ``entity_key`` as export columns, in display order."""
    return [
        Column(
            d.key, d.label_ar if lang == "ar" else d.label_en,
            kind="money" if d.type == FieldType.MONEY else "text",
        )
        for d in active_defs(entity_key).order_by("position", "key")
    ]
