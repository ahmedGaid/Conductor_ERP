"""Assistant API — the simulation endpoint (os-foundations FILE_05 T5.1 + T5.3).

``POST /api/assistant/simulate`` dry-runs a plan of write-actions and returns the FILE_04 diff.
It is gated on ``IsAuthenticated`` ONLY (no ``ASSISTANT_ENABLED`` — simulation is a pure DB
dry-run, no model hop), so none of these tests toggle the AI feature flag. RBAC still holds: the
steps run as the caller, so a step the actor can't run comes back ``ok: false`` with nothing
written.
"""
from __future__ import annotations

import datetime as _dt

import pytest
from rest_framework.test import APIClient

from erp.accounting.domain.models import FiscalYear, Period, PeriodStatus
from erp.assistant.models import Conversation, Message
from erp.assistant.services import actions
from erp.identity.models import User
from erp.inventory.domain.models import Item, Warehouse
from erp.sales.domain.models import Customer, SalesOrder

pytestmark = pytest.mark.django_db

SIM_URL = "/api/assistant/simulate"


def _admin(username: str = "sim_api_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True  # full create rights — every step's role gate passes
    u.save(update_fields=["is_superuser"])
    return u


def _nobody(username: str = "sim_api_nobody") -> User:
    """Authenticated but role-less → cannot create any document."""
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _seed_sales():
    Customer.objects.create(code="C-1", name="Nile Traders")
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    Warehouse.objects.create(code="WH-1", name="Main")


def _seed_open_period():
    today = _dt.date.today()
    fy = FiscalYear.objects.create(code=f"{today.year}-API", start_date=today.replace(month=1, day=1),
                                   end_date=today.replace(month=12, day=31))
    Period.objects.create(fiscal_year=fy, code=f"{today.year}-API", start_date=fy.start_date,
                          end_date=fy.end_date, status=PeriodStatus.OPEN)


def _sales_args():
    # References "Delta Co" — only resolvable in a plan whose earlier step creates that customer.
    return {"customer": "Delta Co", "items": [{"item": "SKU-1", "quantity": "3"}],
            "warehouse": "WH-1"}


def _seeded_sales_args():
    # References the seeded customer, so a standalone proposal builds without a plan ahead of it.
    return {"customer": "Nile Traders", "items": [{"item": "SKU-1", "quantity": "3"}],
            "warehouse": "WH-1"}


# --- T5.1: the steps contract -------------------------------------------------------------------

def test_simulate_happy_two_step_plan_returns_diff_and_persists_nothing():
    admin = _admin()
    _seed_sales()
    _seed_open_period()
    client = APIClient()
    client.force_authenticate(user=admin)

    resp = client.post(SIM_URL, {"steps": [
        {"action": "create_customer", "args": {"query": "Delta Co"}},
        {"action": "create_sales_order_draft", "args": _sales_args()},
    ]}, format="json")

    assert resp.status_code == 200
    diff = resp.json()["data"]
    assert diff["ok"] is True
    assert [s["ok"] for s in diff["steps"]] == [True, True]
    assert diff["creates"] == {"customer": 1, "sales_order": 1}
    # The dry run rolled back — the second step resolved the first step's customer, but neither row
    # survives the request.
    assert Customer.objects.filter(name="Delta Co").count() == 0
    assert SalesOrder.objects.count() == 0


def test_simulate_unknown_action_is_400():
    client = APIClient()
    client.force_authenticate(user=_admin())

    resp = client.post(SIM_URL, {"steps": [{"action": "no_such_action", "args": {}}]},
                       format="json")

    assert resp.status_code == 400


def test_simulate_over_ten_steps_is_400():
    client = APIClient()
    client.force_authenticate(user=_admin())

    steps = [{"action": "create_customer", "args": {"query": f"C{i}"}} for i in range(11)]
    resp = client.post(SIM_URL, {"steps": steps}, format="json")

    assert resp.status_code == 400


def test_simulate_empty_body_is_400():
    client = APIClient()
    client.force_authenticate(user=_admin())

    resp = client.post(SIM_URL, {"steps": []}, format="json")

    assert resp.status_code == 400


def test_simulate_requires_authentication():
    resp = APIClient().post(SIM_URL, {"steps": [{"action": "create_customer", "args": {}}]},
                            format="json")

    assert resp.status_code in (401, 403)


def test_simulate_actor_without_rights_fails_the_step_and_writes_nothing():
    nobody = _nobody()
    _seed_sales()
    client = APIClient()
    client.force_authenticate(user=nobody)

    resp = client.post(SIM_URL, {"steps": [
        {"action": "create_customer", "args": {"query": "Refused Co"}},
    ]}, format="json")

    assert resp.status_code == 200  # the endpoint answers; the *step* is what refuses
    diff = resp.json()["data"]
    assert diff["ok"] is False
    assert diff["steps"][0]["ok"] is False
    assert Customer.objects.filter(name="Refused Co").count() == 0


# --- T5.3: preview one pending proposal by message_id -------------------------------------------

def _pending_proposal_message(user, action, args):
    proposal = actions.build(user, action, args)  # built as the same actor that will preview
    conv = Conversation.objects.create(user=user)
    return Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                  meta={"proposal": {**proposal, "status": "pending"}})


def test_simulate_by_message_id_previews_stored_proposal():
    admin = _admin()
    _seed_sales()
    _seed_open_period()
    msg = _pending_proposal_message(admin, "create_sales_order_draft", _seeded_sales_args())
    client = APIClient()
    client.force_authenticate(user=admin)

    resp = client.post(SIM_URL, {"message_id": msg.id}, format="json")

    assert resp.status_code == 200
    diff = resp.json()["data"]
    assert diff["ok"] is True
    assert diff["creates"] == {"sales_order": 1}
    assert SalesOrder.objects.count() == 0  # previewing the confirm persisted nothing


def test_simulate_by_message_id_own_checks_the_conversation():
    owner = _admin("sim_owner")
    stranger = _admin("sim_stranger")
    _seed_sales()
    _seed_open_period()
    msg = _pending_proposal_message(owner, "create_sales_order_draft", _sales_args())
    client = APIClient()
    client.force_authenticate(user=stranger)

    resp = client.post(SIM_URL, {"message_id": msg.id}, format="json")

    assert resp.status_code == 404  # a foreign message is indistinguishable from absent
