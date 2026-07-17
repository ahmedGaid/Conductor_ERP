"""Deterministic auto-fix pass (FILE_11 Task B) — required-field defaults, the date-ambiguous
accept-as-is, a dayfirst retry on a genuinely invalid date, and a fuzzy currency-token fix.

None of the four registered master adapters have a field that can produce every fixable code in
anger (no adapter's own ``validate()`` calls ``normalize_currency``, and ``parse_date``'s
ambiguous-day branch always succeeds — see the module docstring's note on FieldSpec.default), so
this exercises the mechanism against a throwaway test adapter, same pattern as
``test_validate.py``/``test_masters.py``. The currency_unknown and date_ambiguous cases run
through the REAL analyze/validate pipeline (a real trigger exists via ``adapter.validate``); the
date_invalid dayfirst-retry is exercised directly against ``_propose`` since ``parse_date``'s
ambiguous-day branch never actually fails one way while succeeding the other (both orderings are
always valid day numbers) — the retry is a real, wired seam, just not naturally reachable today.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from erp.assistant.models import Attachment
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import autofix, registry
from erp.imports.analyze import analyze
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.normalize import normalize_currency
from erp.imports.registry import FieldSpec, Issue
from erp.imports.validate import validate_batch

pytestmark = pytest.mark.django_db


def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


class _GadgetAdapter:
    """label has a FieldSpec.default (none of the real adapters do); currency's own ``validate``
    calls ``normalize_currency`` directly, the same way a real adapter COULD."""

    entity = "gadgets"
    label_key = "imports.entity.gadgets"
    fields = [
        FieldSpec(name="code", required=True, kind="text"),
        FieldSpec(name="label", required=True, kind="text", default="Unnamed"),
        FieldSpec(name="currency", kind="text"),
        FieldSpec(name="received", kind="date"),
    ]
    natural_key = ["code"]
    group_by = None

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        issues = []
        currency = row.get("currency")
        if currency and isinstance(normalize_currency(currency), Issue):
            issues.append(Issue(field="currency", code="currency_unknown", message="imports.issues.currencyUnknown"))
        return issues

    def write(self, actor, row: dict):
        return row

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []


@pytest.fixture()
def gadget_adapter():
    adapter = _GadgetAdapter()
    registry.register(adapter)
    try:
        yield adapter
    finally:
        registry.REGISTER.pop("gadgets", None)


def _csv(rows) -> bytes:
    text = "\n".join(",".join("" if c is None else str(c) for c in r) for r in rows)
    return text.encode("utf-8")


def _analyzed_batch(actor, rows, mapping) -> ImportBatch:
    upload = SimpleUploadedFile("data.csv", _csv(rows), content_type="text/csv")
    attachment = Attachment.objects.create(user=actor, file=upload, name="data.csv", content_type="text/csv", size=upload.size)
    batch = ImportBatch.objects.create(entity="gadgets", source_file=attachment, mapping=mapping)
    analyze(actor, batch)
    validate_batch(actor, batch)
    return batch


# --- required_missing -> FieldSpec.default -----------------------------------------------------
def test_required_missing_proposes_the_field_default(gadget_adapter):
    actor = _manager("a1")
    batch = _analyzed_batch(actor, [["Code", "Label"], ["G1", ""]], {"code": "Code", "label": "Label"})
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "required_missing" and i["field"] == "label" for i in row.issues)

    fixes = autofix.preview_fixes(batch)

    assert fixes == [{"row_id": row.id, "row": 1, "field": "label", "from": None, "to": "Unnamed", "code": "required_missing"}]


def test_required_missing_with_no_default_proposes_nothing(gadget_adapter):
    actor = _manager("a2")
    batch = _analyzed_batch(actor, [["Code", "Label"], ["", "L1"]], {"code": "Code", "label": "Label"})

    fixes = autofix.preview_fixes(batch)

    assert fixes == []  # "code" is required with no FieldSpec.default -> nothing to propose


# --- date_ambiguous -> accept the day-first reading ---------------------------------------------
def test_date_ambiguous_is_proposed_as_accept_the_day_first_reading(gadget_adapter):
    actor = _manager("a3b")
    # 05/06/2026: both 5 and 6 are <= 12 -> genuinely ambiguous; parse_date resolves day-first
    # (Egypt convention) and flags date_ambiguous rather than failing.
    batch = _analyzed_batch(
        actor, [["Code", "Label", "Received"], ["G1", "Widget", "05/06/2026"]],
        {"code": "Code", "label": "Label", "received": "Received"},
    )
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "date_ambiguous" for i in row.issues)
    assert row.normalized["received"] == "2026-06-05"  # day=5, month=6 — already usable

    fixes = autofix.preview_fixes(batch)

    assert fixes == [{
        "row_id": row.id, "row": 1, "field": "received",
        "from": "2026-06-05", "to": "2026-06-05", "code": "date_ambiguous",
    }]

    counts = autofix.apply_fixes(actor, batch, fixes)
    assert counts["valid"] == 1
    row.refresh_from_db()
    assert row.status == ImportRow.Status.VALID


def test_currency_unknown_proposes_the_nearest_known_currency_word(gadget_adapter):
    actor = _manager("a3")
    batch = _analyzed_batch(
        actor, [["Code", "Label", "Currency"], ["G1", "Widget", "dolars"]],
        {"code": "Code", "label": "Label", "currency": "Currency"},
    )
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "currency_unknown" for i in row.issues)

    fixes = autofix.preview_fixes(batch)

    assert fixes == [{"row_id": row.id, "row": 1, "field": "currency", "from": "dolars", "to": "USD", "code": "currency_unknown"}]


def test_currency_unknown_too_far_from_any_known_word_proposes_nothing(gadget_adapter):
    actor = _manager("a4")
    batch = _analyzed_batch(
        actor, [["Code", "Label", "Currency"], ["G1", "Widget", "moonbucks"]],
        {"code": "Code", "label": "Label", "currency": "Currency"},
    )

    fixes = autofix.preview_fixes(batch)

    assert fixes == []


# --- date_invalid -> dayfirst retry (wired seam; direct unit test — see module docstring) -------
def test_date_invalid_retries_with_dayfirst_false(monkeypatch):
    import datetime as _dt

    from erp.imports.registry import FieldSpec as FS

    def _fake_parse_date(value, dayfirst=True, warnings=None):
        if dayfirst:
            return Issue(field="received", code="date_invalid", message="x")
        return _dt.date(2026, 3, 4)

    monkeypatch.setattr(autofix, "parse_date", _fake_parse_date)
    spec = FS(name="received", kind="date")

    fixed = autofix._propose(spec, "date_invalid", None, "some raw cell")

    assert fixed == "2026-03-04"


def test_date_invalid_with_no_raw_value_proposes_nothing():
    from erp.imports.registry import FieldSpec as FS

    spec = FS(name="received", kind="date")
    assert autofix._propose(spec, "date_invalid", None, None) is None


# --- whitespace trim fallback --------------------------------------------------------------------
def test_whitespace_is_trimmed_as_a_last_resort(gadget_adapter):
    actor = _manager("a5")
    batch = ImportBatch.objects.create(entity="gadgets", mapping={"code": "Code", "label": "Label"})
    row = ImportRow.objects.create(
        batch=batch, row_number=1, raw={"Code": "G1", "Label": " Widget "},
        normalized={"code": "G1", "label": " Widget "},  # bypasses normalize_row's own trim on purpose
        status=ImportRow.Status.ERROR,
        issues=[{"field": "label", "code": "some_other_code", "message": "x"}],
    )

    fixes = autofix.preview_fixes(batch)

    assert fixes == [{"row_id": row.id, "row": 1, "field": "label", "from": " Widget ", "to": "Widget", "code": "some_other_code"}]


# --- apply_fixes end-to-end -----------------------------------------------------------------------
def test_apply_fixes_clears_the_issue_and_revalidates_to_valid(gadget_adapter):
    actor = _manager("a6")
    batch = _analyzed_batch(actor, [["Code", "Label"], ["G1", ""]], {"code": "Code", "label": "Label"})
    row = batch.rows.get(row_number=1)
    fixes = autofix.preview_fixes(batch)

    counts = autofix.apply_fixes(actor, batch, fixes)

    assert counts["valid"] == 1
    row.refresh_from_db()
    assert row.status == ImportRow.Status.VALID
    assert row.normalized["label"] == "Unnamed"
    assert not any(i["code"] == "required_missing" for i in row.issues)


def test_apply_fixes_with_nothing_accepted_is_a_noop(gadget_adapter):
    actor = _manager("a7")
    batch = _analyzed_batch(actor, [["Code", "Label"], ["G1", ""]], {"code": "Code", "label": "Label"})

    counts = autofix.apply_fixes(actor, batch, [])

    assert counts == {"valid": 0, "error": 0, "duplicate": 0}
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
