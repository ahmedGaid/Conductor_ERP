"""Generic per-record activity timeline: read-side diffing + the module-access gate on the API."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.audit import services as audit
from erp.audit.history import record_timeline
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


def test_record_timeline_diffs_scalar_fields_against_the_prior_snapshot():
    actor = User.objects.create_user(username="hist_u1", password="Dev12345!")
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-1",
                 actor=actor, after={"number": "SO-1", "status": "draft", "outstanding_minor": 1000})
    audit.record(module="sales", action="confirm_order", entity_type="SalesOrder", entity_id="SO-1",
                 actor=actor, after={"number": "SO-1", "status": "confirmed", "outstanding_minor": 1000})
    audit.record(module="sales", action="invoice_order", entity_type="SalesOrder", entity_id="SO-1",
                 actor=actor, after={"number": "SO-1", "status": "invoiced", "outstanding_minor": 1000,
                                     "invoice_number": "INV-1"})

    rows = record_timeline("SalesOrder", "SO-1")

    # Newest first.
    assert [r["action"] for r in rows] == ["invoice_order", "confirm_order", "create_order"]
    assert all(r["actor_name"] == "hist_u1" for r in rows)
    # Creation has nothing to diff against.
    assert rows[-1]["changes"] == []
    # "number" is identity, never a reported change; "status" and the new field both are.
    invoice_changes = {c["field"]: (c["old"], c["new"]) for c in rows[0]["changes"]}
    assert invoice_changes["status"] == ("confirmed", "invoiced")
    assert invoice_changes["invoice_number"] == (None, "INV-1")
    assert "outstanding_minor" not in invoice_changes  # unchanged between the two snapshots
    assert "number" not in invoice_changes


def test_record_history_endpoint_returns_the_timeline_for_an_accessible_module():
    actor = User.objects.create_user(username="hist_u2", password="Dev12345!")
    _grant(actor, "sales.order.view")
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-2",
                 actor=actor, after={"number": "SO-2", "status": "draft"})

    res = _client(actor).get("/api/audit/history?entity_type=SalesOrder&entity_id=SO-2")
    assert res.status_code == 200, res.data
    assert res.data["data"][0]["action"] == "create_order"


def test_record_history_endpoint_denies_a_module_the_user_cannot_reach():
    actor = User.objects.create_user(username="hist_u3", password="Dev12345!")
    _grant(actor, "inventory.item.view")  # inventory only — not sales
    audit.record(module="sales", action="create_order", entity_type="SalesOrder", entity_id="SO-3",
                 actor=actor, after={"number": "SO-3", "status": "draft"})

    res = _client(actor).get("/api/audit/history?entity_type=SalesOrder&entity_id=SO-3")
    assert res.status_code == 403


def test_record_history_endpoint_rejects_an_unknown_entity_type():
    actor = User.objects.create_user(username="hist_u4", password="Dev12345!")
    res = _client(actor).get("/api/audit/history?entity_type=Nope&entity_id=1")
    assert res.status_code == 400


def test_record_history_endpoint_requires_authentication():
    res = APIClient().get("/api/audit/history?entity_type=SalesOrder&entity_id=SO-1")
    assert res.status_code == 401
