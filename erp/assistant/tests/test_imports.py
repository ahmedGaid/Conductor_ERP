"""Import intelligence (plan session 14): inspect → preview → execute, plus the endpoints + loop hook.

The model seam (``imports.complete_json``, the header→field mapper) stays mocked so gates make no live
call — every test drives the real read/validate/create path over a real CSV attachment, so a create
runs the real module contract and lands a real record. Duplicate/error rows are pinned by seeding the
data and dirtying the file.
"""
from __future__ import annotations

import pytest
from django.core.files.base import ContentFile
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import Conversation, Message
from erp.assistant.services import agent, imports
from erp.audit.models import AuditEntry
from erp.identity.models import User
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db

INSPECT_URL = "/api/assistant/imports/inspect"
PREVIEW_URL = "/api/assistant/imports/preview"
EXECUTE_URL = "/api/assistant/imports/execute"

# The mapper's answer for a customers file with `name,code` headers.
_CUSTOMER_MAP = {
    "target": "customers",
    "mapping": {"name": "name", "code": "code", "credit_limit_minor": None,
                "sku": None, "uom": None, "reorder_point": None},
}

# A customers CSV with one DB duplicate (Beta Supplies is seeded), one in-file duplicate (Alpha
# twice), and one broken row (blank name). Rows 1..5 below the header.
_CUSTOMERS_CSV = (
    "name,code\n"
    "Alpha Trading,\n"      # 1 valid
    "Beta Supplies,\n"      # 2 duplicate (exists in DB)
    "Alpha Trading,\n"      # 3 duplicate (in file)
    ",\n"                   # 4 error (name missing)
    "Gamma Co,\n"           # 5 valid
)


def _admin(username: str = "imp_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _nobody(username: str = "imp_nobody") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _csv_attachment(user, body: str, name: str = "customers.csv"):
    from erp.assistant.models import Attachment

    return Attachment.objects.create(
        user=user, file=ContentFile(body.encode(), name=name),
        name=name, content_type="text/csv", size=len(body),
    )


def _mock_mapper(monkeypatch, answer=None):
    monkeypatch.setattr(imports, "complete_json", lambda *a, **k: answer or _CUSTOMER_MAP)


# --- service: inspect --------------------------------------------------------------------------

def test_inspect_maps_headers_to_fields(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_mapper(monkeypatch)
    user = _admin()
    att = _csv_attachment(user, _CUSTOMERS_CSV)

    out = imports.inspect(user, att, target_hint=None)
    assert out["target"] == "customers"
    assert out["mapping"]["name"] == "name"
    assert out["row_count"] == 5
    assert out["issues"] == []  # the required `name` column is mapped
    assert {f["key"] for f in out["fields"]} == {"name", "code", "credit_limit_minor"}


def test_inspect_flags_a_missing_required_column(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    # The model maps nothing → the required `name` field has no column.
    _mock_mapper(monkeypatch, {"target": "customers",
                               "mapping": {k: None for k in imports._ALL_FIELD_KEYS}})
    user = _admin()
    att = _csv_attachment(user, "phone,note\n010,hi\n")

    out = imports.inspect(user, att, None)
    assert any("Customer name" in i for i in out["issues"])


def test_inspect_blocks_unpermitted_actor(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_mapper(monkeypatch)
    nobody = _nobody()
    att = _csv_attachment(nobody, _CUSTOMERS_CSV)

    out = imports.inspect(nobody, att, None)
    assert "error" in out and "permission" in out["error"].lower()


def test_inspect_empty_file_is_a_calm_error(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_mapper(monkeypatch)
    user = _admin()
    att = _csv_attachment(user, "name,code\n")  # header only, no data rows

    out = imports.inspect(user, att, None)
    assert "error" in out


# --- service: preview + execute ----------------------------------------------------------------

def _mapping():
    return {"name": "name", "code": "code"}


def test_preview_counts_valid_errors_and_duplicates(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    # A non "C-" code so it stays out of the auto-code sequence the new rows draw from.
    Customer.objects.create(code="EX-1", name="Beta Supplies")  # seeds the DB duplicate
    att = _csv_attachment(user, _CUSTOMERS_CSV)

    out = imports.preview(user, att, _mapping(), "customers")
    assert out["valid"] == 2                       # Alpha Trading (1), Gamma Co (5)
    assert {d["row"] for d in out["duplicates"]} == {2, 3}   # exists, then in-file
    assert [e["row"] for e in out["errors"]] == [4]          # blank name
    assert Customer.objects.count() == 1           # preview writes nothing


def test_execute_creates_valid_rows_skips_the_rest_and_audits(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    Customer.objects.create(code="EX-1", name="Beta Supplies")
    att = _csv_attachment(user, _CUSTOMERS_CSV)

    out = imports.execute(user, att, _mapping(), "customers")
    assert out["created"] == 2 and out["skipped"] == 3
    assert Customer.objects.filter(name="Alpha Trading").exists()
    assert Customer.objects.filter(name="Gamma Co").exists()
    assert not Customer.objects.filter(name__exact="").exists()
    # A per-row report drives the downloadable CSV; every row is accounted for.
    assert len(out["report"]) == 5
    assert {r["status"] for r in out["report"]} == {"created", "skipped", "error"}
    assert AuditEntry.objects.filter(module="assistant", action="import").exists()


def test_execute_is_idempotent_on_re_run(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    att = _csv_attachment(user, _CUSTOMERS_CSV)

    first = imports.execute(user, att, _mapping(), "customers")
    assert first["created"] == 3  # Alpha, Beta, Gamma (nothing seeded, so Beta is new here)
    # Re-running the same file: every previously-created row is now a DB duplicate → zero new records.
    second = imports.execute(user, att, _mapping(), "customers")
    assert second["created"] == 0
    assert Customer.objects.filter(name__in=["Alpha Trading", "Gamma Co", "Beta Supplies"]).count() == 3


def test_items_import_uses_sku_as_the_natural_key(settings, tmp_path):
    from erp.inventory.domain.models import Item

    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    Item.objects.create(sku="SKU-1", name="Existing Widget")
    csv = "sku,name\nSKU-1,Dup Widget\nSKU-2,Blue Widget\n,Nameless\n"
    att = _csv_attachment(user, csv, name="items.csv")
    mapping = {"sku": "sku", "name": "name"}

    out = imports.execute(user, att, mapping, "items")
    assert out["created"] == 1                     # only SKU-2
    assert Item.objects.filter(sku="SKU-2", name="Blue Widget").exists()
    assert out["skipped"] == 2                      # SKU-1 duplicate, blank-sku error


# --- endpoints: preview + execute over a persisted card ----------------------------------------

def _card_message(user, att, target="customers"):
    """A conversation + assistant message carrying a mapping-stage import card for ``user``."""
    card = imports.as_card(
        {"target": target, "fields": imports._card_fields(imports.TARGETS[target]),
         "columns": ["name", "code"], "mapping": {"name": "name", "code": "code"},
         "sample": [], "row_count": 5, "issues": []},
        att.id,
    )
    conv = Conversation.objects.create(user=user)
    return Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT,
                                  content="Read your file.", meta={"import": card})


@override_settings(ASSISTANT_ENABLED=True)
def test_preview_then_execute_endpoint_flow_and_single_use(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    att = _csv_attachment(user, _CUSTOMERS_CSV)
    msg = _card_message(user, att)
    client = APIClient()
    client.force_authenticate(user=user)

    prev = client.post(PREVIEW_URL, {"message_id": msg.id, "mapping": {"name": "name", "code": "code"}},
                       format="json")
    assert prev.status_code == 200 and prev.json()["data"]["valid"] == 3  # nothing seeded yet

    ok = client.post(EXECUTE_URL, {"message_id": msg.id, "mapping": {"name": "name", "code": "code"}},
                     format="json")
    assert ok.status_code == 200 and ok.json()["data"]["created"] == 3

    # The report is persisted back onto the card (reload-safe) and a second run 409s.
    msg.refresh_from_db()
    assert msg.meta["import"]["stage"] == "report"
    again = client.post(EXECUTE_URL, {"message_id": msg.id, "mapping": {"name": "name", "code": "code"}},
                        format="json")
    assert again.status_code == 409
    assert Customer.objects.count() == 3  # not doubled


@override_settings(ASSISTANT_ENABLED=True)
def test_inspect_endpoint_returns_a_mapping_card(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_mapper(monkeypatch)
    user = _admin()
    att = _csv_attachment(user, _CUSTOMERS_CSV)
    client = APIClient()
    client.force_authenticate(user=user)

    res = client.post(INSPECT_URL, {"attachment_id": att.id, "target": "customers"}, format="json")
    assert res.status_code == 200
    card = res.json()["data"]
    assert card["stage"] == "mapping" and card["attachment_id"] == att.id
    assert card["target"] == "customers" and card["row_count"] == 5


@override_settings(ASSISTANT_ENABLED=True)
def test_import_endpoint_rejects_foreign_message(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    att = _csv_attachment(user, _CUSTOMERS_CSV)
    msg = _card_message(user, att)
    intruder = APIClient()
    intruder.force_authenticate(user=_nobody("imp_stranger"))

    res = intruder.post(PREVIEW_URL, {"message_id": msg.id, "mapping": {"name": "name"}}, format="json")
    assert res.status_code in (403, 404)  # role gate or own-check — never leaks the file


# --- agent loop hook ----------------------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_loop_import_verb_inspects_and_persists_a_card(settings, tmp_path, monkeypatch):
    """The loop's import verb: an attached spreadsheet + 'import these customers' inspects the file,
    ends the turn, emits an `import` event, and persists a mapping-stage card in the answer's meta —
    creating nothing."""
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    conv = Conversation.objects.create(user=user)
    att = _csv_attachment(user, _CUSTOMERS_CSV)
    _mock_mapper(monkeypatch)  # the inspector's model call

    monkeypatch.setattr(agent, "complete_json",
                        lambda *a, **k: {"action": "import", "target": "customers", "why": "Import list"})
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **k: iter(["I read your file."]))

    events = list(agent.run(actor=user, conversation=conv, question="import these customers",
                            page=None, attachment_ids=[att.id]))

    kinds = [e["type"] for e in events]
    assert "import" in kinds and kinds[-1] == "done"
    card = next(e for e in events if e["type"] == "import")["import"]
    assert card["target"] == "customers" and card["stage"] == "mapping"
    assert card["attachment_id"] == att.id
    assert Customer.objects.count() == 0  # inspection writes nothing

    msg = conv.messages.get(role="assistant")
    assert msg.meta["import"]["row_count"] == 5


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_loop_import_without_a_spreadsheet_is_calm(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    user = _admin()
    conv = Conversation.objects.create(user=user)

    monkeypatch.setattr(agent, "complete_json",
                        lambda *a, **k: {"action": "import", "target": "customers", "why": "Import"})
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **k: iter(["No file attached."]))

    events = list(agent.run(actor=user, conversation=conv, question="import customers", page=None))
    kinds = [e["type"] for e in events]
    assert "import" not in kinds and kinds[-1] == "done"  # no card, a calm answer instead
