"""Paginated timeline endpoint: page-boundary diff correctness + the module-access RBAC gate."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.audit import services as audit
from erp.audit.history import record_timeline_page
from erp.identity import rbac
from erp.identity.models import RolePermission

User = get_user_model()

pytestmark = pytest.mark.django_db


def _grant(user, code, scope=rbac.DataScope.ALL):
    g, _ = Group.objects.get_or_create(name=f"role-{code}")
    RolePermission.objects.update_or_create(role=g, code=code, defaults={"scope": scope})
    user.groups.add(g)


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_record_timeline_page_diffs_the_first_row_of_a_page_against_the_prior_page():
    actor = User.objects.create_user(username="tl_u1", password="Dev12345!")
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-1",
                 actor=actor, after={"number": "SO-1", "status": "draft"})
    audit.record(module="sales", action="confirm_order", entity_type="SalesOrder", entity_id="SO-1",
                 actor=actor, after={"number": "SO-1", "status": "confirmed"})
    audit.record(module="sales", action="invoice_order", entity_type="SalesOrder", entity_id="SO-1",
                 actor=actor, after={"number": "SO-1", "status": "invoiced", "invoice_number": "INV-1"})

    # page_size=2: page 1 = [invoice_order, confirm_order]; page 2 = [create_order] alone. The
    # first row of page 1 (invoice_order) must still diff against confirm_order's snapshot even
    # though confirm_order itself lives on page 2.
    page1, total = record_timeline_page("SalesOrder", "SO-1", page=1, page_size=2)
    assert total == 3
    assert [r["event"] for r in page1] == ["invoice_order", "confirm_order"]
    invoice_changes = {c["field"]: (c["old"], c["new"]) for c in page1[0]["changes"]}
    assert invoice_changes["status"] == ("confirmed", "invoiced")
    assert invoice_changes["invoice_number"] == (None, "INV-1")

    page2, total = record_timeline_page("SalesOrder", "SO-1", page=2, page_size=2)
    assert total == 3
    assert [r["event"] for r in page2] == ["create_order"]
    assert page2[0]["changes"] == []  # true first entry — nothing to diff against
    assert page2[0]["params"] == {"number": "SO-1"}


def test_record_timeline_page_tags_ai_and_import_caused_entries_by_module():
    actor = User.objects.create_user(username="tl_u6", password="Dev12345!")
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-6",
                 actor=actor, after={"number": "SO-6", "status": "draft"})
    audit.record(module="assistant", action="draft_order", entity_type="SalesOrder", entity_id="SO-6",
                 actor=actor, after={"number": "SO-6", "status": "draft", "notes": "AI note"})
    audit.record(module="imports", action="execute_chunk", entity_type="SalesOrder", entity_id="SO-6",
                 actor=actor, after={"number": "SO-6", "status": "confirmed", "notes": "AI note"})

    items, _total = record_timeline_page("SalesOrder", "SO-6", page=1, page_size=10)
    by_event = {i["event"]: i["source"] for i in items}
    assert by_event["create_order"] is None
    assert by_event["draft_order"] == "ai"
    assert by_event["execute_chunk"] == "import"


def test_record_timeline_page_beyond_available_rows_is_empty_not_an_error():
    actor = User.objects.create_user(username="tl_u2", password="Dev12345!")
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-2",
                 actor=actor, after={"number": "SO-2", "status": "draft"})

    items, total = record_timeline_page("SalesOrder", "SO-2", page=5, page_size=30)
    assert items == []
    assert total == 1


def test_record_timeline_endpoint_returns_a_paginated_envelope_for_an_accessible_module():
    actor = User.objects.create_user(username="tl_u3", password="Dev12345!")
    _grant(actor, "sales.order.view")
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-3",
                 actor=actor, after={"number": "SO-3", "status": "draft"})

    res = _client(actor).get("/api/audit/timeline/?entity=SalesOrder&id=SO-3&page=1&page_size=10")
    assert res.status_code == 200, res.data
    assert res.data["data"]["items"][0]["event"] == "create_order"
    assert res.data["data"]["items"][0]["actor"] == "tl_u3"
    assert res.data["data"]["total"] == 1
    assert res.data["data"]["page"] == 1
    assert res.data["data"]["page_size"] == 10


def test_record_timeline_endpoint_denies_a_module_the_user_cannot_reach():
    actor = User.objects.create_user(username="tl_u4", password="Dev12345!")
    _grant(actor, "inventory.item.view")  # inventory only — not sales
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-4",
                 actor=actor, after={"number": "SO-4", "status": "draft"})

    res = _client(actor).get("/api/audit/timeline/?entity=SalesOrder&id=SO-4")
    assert res.status_code == 403


def test_record_timeline_endpoint_rejects_an_unknown_entity():
    actor = User.objects.create_user(username="tl_u5", password="Dev12345!")
    res = _client(actor).get("/api/audit/timeline/?entity=Nope&id=1")
    assert res.status_code == 400


def test_record_timeline_endpoint_requires_authentication():
    res = APIClient().get("/api/audit/timeline/?entity=SalesOrder&id=SO-1")
    assert res.status_code == 401
