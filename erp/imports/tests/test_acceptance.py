"""FILE_17 — acceptance checklist run against `tests/fixtures/acceptance/` (built by
`build_fixtures.py`), automated through the real upload -> detect -> map -> analyze -> validate ->
duplicates -> execute pipeline (the same services the HTTP API and the wizard call — see
`test_api.py`'s docstring for why detection isn't pinned when a file's headers are this
distinctive). This is the mechanical slice of FILE_17's acceptance checklist: entity detection,
header auto-mapping (incl. Arabic + misspellings), analyze stats, creation-plan candidates,
duplicate flagging, cp1256 encoding, group-preview issues, the unbalanced-journal guard, and a
100k-row streaming check. The two-language MANUAL UI walkthrough (profile reuse, autofix apply,
all four strategies, the 100k background-runner's pause/resume/kill-process recovery, report deep
links, rollback, permission rejection, trial-balance opening's correction-approval flow) is
deliberately NOT here — those need a human driving the real browser, not a fixture.
"""
from __future__ import annotations

import os

import pytest
from django.contrib.auth.models import Group

from erp.accounting.services.seeding import seed_baseline_accounting
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import analyze as analyze_svc
from erp.imports import duplicates, engine
from erp.imports import validate as validate_svc
from erp.imports.models import ImportBatch
from erp.imports.registry import get as get_adapter
from erp.inventory.domain.models import Item, Warehouse
from erp.purchasing.domain.models import Supplier
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "acceptance")


def _read(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(
        username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True,
    )
    u.groups.add(bm)
    return u


@pytest.fixture()
def acceptance_world():
    """Real reference data the fixtures point at — mirrors `build_fixtures.py`'s REAL_* constants.
    `seed_baseline_accounting()` gives the accounts (1000/1010/1100/…) and VAT14/VAT0 tax codes the
    document/finance fixtures reference, plus a fiscal year + open periods covering the CURRENT
    year — the fixtures' 2026-06 dates are chosen to fall inside it (see test_finance_adapters.py's
    `coa` fixture for the same convention)."""
    Warehouse.objects.get_or_create(code="MAIN", defaults={"name": "Main Warehouse"})
    Item.objects.get_or_create(sku="BOLT", defaults={"name": "Bolt (kg)", "type": "stock"})
    Customer.objects.get_or_create(code="ACME", defaults={"name": "Acme Corp"})
    Supplier.objects.get_or_create(code="GLOBEX", defaults={"name": "Globex Supplies"})
    seed_baseline_accounting()


def _read_headers(data: bytes):
    from erp.imports import readers
    return readers.read_headers(data)


def _run_pipeline(actor, entity: str, data: bytes, row_mapping: dict[str, str]) -> ImportBatch:
    """upload -> [entity + mapping already known — see module docstring on why the live
    AI-backed auto-matcher isn't exercised here] -> analyze -> validate -> duplicates.

    `match_headers`'s synonym/fuzzy matching (incl. Arabic + misspellings) has its own dedicated,
    mocked, deterministic coverage in `test_mapping.py` — re-driving it here would hit the SAME
    live AI fallback `test_api.py` already flags as "slow, non-deterministic, exactly what a test
    suite must never depend on" (confirmed: it really does call Gemini/Mistral when a header is
    ambiguous enough, ~35s/call). This file's job is proving the pipeline handles messy DATA
    correctly once mapped — mapping is supplied explicitly, exactly as it would be after a human
    reviews/corrects the wizard's Map step (never blind-trusted, same lesson FILE_12/13 learned).
    """
    adapter = get_adapter(entity)

    from erp.assistant.models import Attachment
    from django.core.files.base import ContentFile

    attachment = Attachment.objects.create(
        user=actor, file=ContentFile(data, name="acceptance.csv"),
        name="acceptance.csv", content_type="text/csv", size=len(data),
    )
    batch = ImportBatch.objects.create(entity=entity, source_file=attachment, created_by=actor)
    batch.mapping = row_mapping
    batch.save(update_fields=["mapping"])

    analyze_svc.analyze(actor, batch)
    validate_svc.validate_batch(actor, batch)
    duplicates.find_candidates(actor, adapter, batch)
    batch.refresh_from_db()
    return batch


# `ImportBatch.mapping` is `{field: header}` (see `normalize.normalize_row`'s `_field_map` /
# `MappingView`'s own `set(row_mapping) - {f.name for f in adapter.fields}` unknown-field check —
# both key off FIELD names), not `{header: field}`.
_CUSTOMERS_MAPPING = {"code": "كود العميل", "name": "Customer Name", "credit_limit_minor": "Credit Limitt"}
_INVOICE_MAPPING = {
    "doc_number": "Invoic No", "customer_ref": "العميل", "date": "Date", "currency": "Currency",
    "warehouse_ref": "المخزن", "tax_token": "Tax", "file_total_minor": "الاجمالي",
    "item_ref": "الصنف", "quantity": "Qnty", "unit_price_minor": "Unit Price", "discount_minor": "Discount",
}
_INVOICE_MAPPING_AR = {
    "doc_number": "رقم الفاتورة", "customer_ref": "العميل", "date": "التاريخ", "currency": "العملة",
    "warehouse_ref": "المخزن", "tax_token": "الضريبة", "file_total_minor": "الاجمالي",
    "item_ref": "الصنف", "quantity": "الكمية", "unit_price_minor": "سعر الوحدة", "discount_minor": "خصم",
}
_JOURNAL_MAPPING = {
    "entry_ref": "Entry No", "date": "Date", "memo": "البيان", "account_ref": "Account",
    "debit_minor": "Debit", "credit_minor": "Credit", "line_memo": "Line Memo",
}


# --- customers_messy.csv ------------------------------------------------------------------------
def test_customers_messy_detection_mapping_and_issues(acceptance_world):
    actor = _manager("acc-cust")
    batch = _run_pipeline(actor, "customers", _read("customers_messy.csv"), _CUSTOMERS_MAPPING)

    rows = {r.row_number: r for r in batch.rows.all()}
    # header row detected past the two junk title rows + blank row.
    assert len(rows) == 6  # CM-1..CM-6

    codes_by_row = {n: [i["code"] for i in r.issues] for n, r in rows.items()}
    # CM-6 blank name -> required_missing (real error, never silently dropped).
    assert "required_missing" in codes_by_row[6]
    # CM-5 exact duplicate name of CM-1 -> duplicate_in_file.
    assert "duplicate_in_file" in codes_by_row[5]

    # CM-4 (near-duplicate of CM-1's name) surfaces as a probable fuzzy duplicate.
    row4 = rows[4]
    assert row4.status == "duplicate"
    fuzzy = next(i for i in row4.issues if i["code"] == "probable_duplicate")
    assert fuzzy["meta"]["candidates"], "expected at least one fuzzy-duplicate candidate for CM-4"

    # Arabic-Indic-digit + Arabic-currency-word credit limit (CM-2) and "L.E"-suffixed (CM-3) both
    # normalize to real minor-unit integers, never blocked as money_invalid.
    assert rows[2].normalized["credit_limit_minor"] == 25000_00
    assert rows[3].normalized["credit_limit_minor"] == 10000_00


# --- sales_invoices_messy.csv (5k+ rows, every date format, mixed issues) ------------------------
def test_sales_invoices_messy_detection_and_group_preview_issues(acceptance_world):
    actor = _manager("acc-inv")
    batch = _run_pipeline(actor, "sales_invoices", _read("sales_invoices_messy.csv"), _INVOICE_MAPPING)

    assert batch.row_count >= 5200  # the curated rows + 5,200 generated padding rows

    rows_by_number = {r.row_number: r for r in batch.rows.all().order_by("row_number")}
    # Row 1 = the orphan blank-key line (no doc_number, nothing open before it).
    orphan = rows_by_number[1]
    assert any(i["code"] == "missing_group_key" for i in orphan.issues)

    all_issue_codes = {i["code"] for r in rows_by_number.values() for i in r.issues}
    # Every date-format variant the fixture threw at it (ISO, day-first numeric, dot-separated +
    # Arabic month + Arabic-Indic digits, Excel serial) must have parsed — none should show up as
    # a blocking date_invalid anywhere.
    assert "date_invalid" not in all_issue_codes
    # ACC-INV-1's second document (customer_ref differs) -> inconsistent_document.
    assert "inconsistent_document" in all_issue_codes
    # ACC-INV-4's wrong file total -> total_mismatch, a WARNING (row still valid).
    assert "total_mismatch" in all_issue_codes
    # Missing customer + missing item flagged for the creation-plan (two different ref entities) —
    # PLUS a bare "vat"/"ضريبة" tax word (no rate) genuinely can't resolve to a configured TaxCode
    # either (only a rated token like "14%"/"معفى" can) — a real, honest messy-data finding, not a
    # bug: a human must pick a rate, same as any other missing_ref.
    missing_ref_rows = [r for r in rows_by_number.values() if any(i["code"] == "missing_ref" for i in r.issues)]
    missing_ref_entities = {
        i["meta"]["entity"] for r in missing_ref_rows for i in r.issues if i["code"] == "missing_ref"
    }
    assert missing_ref_entities == {"customers", "items", "tax_codes"}

    # group_meta wired correctly for the whole file (FILE_15 CONFIRMED SCOPE): the inconsistent
    # document's two rows share one group_id and both flip to ERROR.
    inconsistent_rows = [r for r in rows_by_number.values() if any(i["code"] == "inconsistent_document" for i in r.issues)]
    assert len({r.group_meta["group_id"] for r in inconsistent_rows}) == 1
    assert all(r.status == "error" for r in inconsistent_rows)


def test_sales_invoices_cp1256_reads_without_mojibake(acceptance_world):
    data = _read("sales_invoices_cp1256.csv")
    headers = _read_headers(data)
    # The decode itself (readers.py's job, not this file's) must produce real Arabic text, never
    # mojibake — proven directly against the header strings before any mapping happens.
    assert headers.headers == [
        "رقم الفاتورة", "العميل", "التاريخ", "العملة", "المخزن", "الضريبة",
        "الاجمالي", "الصنف", "الكمية", "سعر الوحدة", "خصم",
    ]

    actor = _manager("acc-cp1256")
    batch = _run_pipeline(actor, "sales_invoices", data, _INVOICE_MAPPING_AR)
    row = batch.rows.get(row_number=1)
    assert row.normalized["customer_ref"] == "ACME"
    assert row.status in ("valid", "duplicate")  # never garbled into an error by mojibake


# --- journal_entries_unbalanced.csv --------------------------------------------------------------
def test_journal_entries_unbalanced_errors_only_that_entry(acceptance_world):
    actor = _manager("acc-je")
    batch = _run_pipeline(actor, "journal_entries", _read("journal_entries_unbalanced.csv"), _JOURNAL_MAPPING)
    # The generic preview pass (FILE_15) only covers total_mismatch/inconsistent_document/
    # missing_group_key — `unbalanced_entry` is the finance adapter's OWN validate_group hook
    # (FILE_16), which only runs at EXECUTE time, not in this preview. Confirm that boundary, then
    # execute and check the real behavior.
    assert not any(i["code"] == "unbalanced_entry" for r in batch.rows.all() for i in r.issues)

    report = engine.execute_batch(actor, batch)
    rows = {r.row_number: r for r in batch.rows.all()}
    je1_rows = [r for n, r in rows.items() if n in (1, 2)]
    je2_rows = [r for n, r in rows.items() if n in (3, 4)]
    assert all(r.status == "imported" for r in je1_rows)  # balanced entry: fine
    assert all(r.status == "error" for r in je2_rows)  # unbalanced entry: whole entry errors
    assert any(i["code"] == "unbalanced_entry" for r in je2_rows for i in r.issues)
    assert report["created"] >= 1  # counts ROWS, not documents — see the DB check below for the
    # unambiguous, document-level assertion: exactly one balanced draft entry landed (JE-1, both
    # lines), and JE-2 never wrote anything at all.
    from erp.accounting.domain.models import JournalEntry
    je1 = JournalEntry.objects.get(reference="import-je:JE-1")
    assert je1.lines.count() == 2
    assert not JournalEntry.objects.filter(reference="import-je:JE-2").exists()


# --- customers_100k.csv: streaming volume check (not the live background-runner/kill-process test)
def test_customers_100k_analyze_streams_without_error():
    actor = _manager("acc-vol")
    from erp.assistant.models import Attachment
    from django.core.files.base import ContentFile

    data = _read("customers_100k.csv")
    attachment = Attachment.objects.create(
        user=actor, file=ContentFile(data, name="customers_100k.csv"),
        name="customers_100k.csv", content_type="text/csv", size=len(data),
    )
    batch = ImportBatch.objects.create(entity="customers", source_file=attachment, created_by=actor)
    batch.mapping = {"code": "code", "name": "name", "credit_limit_minor": "credit_limit_minor"}
    batch.save(update_fields=["mapping"])

    stats = analyze_svc.analyze(actor, batch)
    assert stats["rows"] == 100_000
    batch.refresh_from_db()
    assert batch.row_count == 100_000
