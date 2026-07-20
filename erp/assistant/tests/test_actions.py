"""Safe write actions (plan session 10) — propose → confirm → execute → report.

The registry (``actions.build`` / ``actions.execute``) is exercised with real seeded data, so a
confirm runs the real module contract and creates a real draft. The endpoint
(``/api/assistant/actions/execute``) is exercised for the confirm/dismiss/single-use/permission
posture. No model hop is involved — proposals are built directly (the loop's planner is faked in
``test_agent``/``test_chat_stream``), so these pin the write path, not the routing.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import Conversation, Message
from erp.assistant.services import actions, agent
from erp.audit.models import AuditEntry
from erp.identity.models import OrgPreferences, User
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER
from erp.inventory.domain.models import Item, StockBalance, StockCount, StockTransfer, Warehouse
from erp.purchasing.domain.models import PurchaseOrder, PurchaseRequest, Supplier
from erp.purchasing.services.requests import RequestLineInput as PRLineInput
from erp.purchasing.services.requests import create_request as purchasing_create_request
from erp.purchasing.services.requests import submit_request as purchasing_submit_request
from erp.sales.domain.models import Customer, Quotation, QuotationStatus, SalesOrder
from erp.sales.services import quotations as quotation_services
from erp.sales.services.orders import OrderLineInput
from erp.sales.services.orders import create_order as sales_create_order

pytestmark = pytest.mark.django_db

EXEC_URL = "/api/assistant/actions/execute"


def _admin(username: str = "act_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True  # full create rights — the role gate passes
    u.save(update_fields=["is_superuser"])
    return u


def _nobody(username: str = "act_nobody") -> User:
    """Authenticated but role-less → cannot create any document."""
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _seed_sales():
    Customer.objects.create(code="C-1", name="Nile Traders")
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    Warehouse.objects.create(code="WH-1", name="Main")


def _seed_open_period():
    """An open fiscal period covering today — only the confirm-endpoint tests need this: since
    FILE_03, ``period_open`` runs for real on every sales-order/journal confirm."""
    import datetime as _dt

    from erp.accounting.domain.models import FiscalYear, Period, PeriodStatus

    today = _dt.date.today()
    fy = FiscalYear.objects.create(code=f"{today.year}-VT", start_date=today.replace(month=1, day=1),
                                   end_date=today.replace(month=12, day=31))
    Period.objects.create(fiscal_year=fy, code=f"{today.year}-VT", start_date=fy.start_date,
                          end_date=fy.end_date, status=PeriodStatus.OPEN)


def _sales_decision():
    return {"customer": "Nile Traders", "items": [{"item": "SKU-1", "quantity": "3"}],
            "warehouse": "WH-1"}


# --- registry: build + execute ------------------------------------------------------------------

def test_build_then_execute_creates_sales_order_draft():
    admin = _admin()
    _seed_sales()

    proposal = actions.build(admin, "create_sales_order_draft", _sales_decision())
    assert "error" not in proposal
    assert proposal["action"] == "create_sales_order_draft"
    # The card carries real record links before anything is written.
    kinds = {r["type"] for r in proposal["records"]}
    assert {"customer", "item"} <= kinds
    assert SalesOrder.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_sales_order_draft", proposal["payload"])
    order = SalesOrder.objects.get()
    assert order.status == "draft"
    assert order.customer.code == "C-1"
    assert result["links"][0]["value"] == str(order.id)


def test_build_purchase_request_from_low_stock_and_execute():
    admin = _admin()
    Supplier.objects.create(code="S-1", name="Cairo Supplies")
    item = Item.objects.create(sku="SKU-2", name="Red Gadget", reorder_point=10)
    wh = Warehouse.objects.create(code="WH-1", name="Main")
    # On-hand below reorder → low_stock surfaces it.
    from erp.inventory.domain.models import StockBalance
    StockBalance.objects.create(item=item, warehouse=wh, quantity=2, value_minor=100)

    proposal = actions.build(admin, "create_purchase_request_draft",
                             {"supplier": "Cairo Supplies", "from_low_stock": True})
    assert "error" not in proposal
    assert any(r["type"] == "item" and r["value"] == "SKU-2" for r in proposal["records"])

    actions.execute(admin, "create_purchase_request_draft", proposal["payload"])
    req = PurchaseRequest.objects.get()
    assert req.supplier.code == "S-1"
    assert req.status == "draft"


def test_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_sales()

    proposal = actions.build(nobody, "create_sales_order_draft", _sales_decision())
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_sales_order_draft",
                        {"customer_code": "C-1", "warehouse_code": "WH-1",
                         "lines": [{"item_sku": "SKU-1", "quantity": "1", "unit_price_minor": 0}]})
    assert SalesOrder.objects.count() == 0


def test_create_customer_exact_duplicate_blocks_near_duplicate_warns():
    admin = _admin()
    Customer.objects.create(code="C-1", name="Nile Traders")

    exact = actions.build(admin, "create_customer", {"query": "Nile Traders"})
    assert "error" in exact and "already exists" in exact["error"]

    near = actions.build(admin, "create_customer", {"query": "Nile Traders Corp"})
    assert "error" not in near
    assert near["risks"], "a close name should surface a risk line, not a silent create"

    actions.execute(admin, "create_customer", near["payload"])
    assert Customer.objects.filter(name="Nile Traders Corp").exists()


# --- endpoint: confirm / dismiss / single-use / ownership ---------------------------------------

def _proposal_message(user, payload_decision, action="create_sales_order_draft"):
    """A conversation + assistant message carrying a real pending proposal for ``user``."""
    admin_view = user  # built as the same actor that will confirm
    proposal = actions.build(admin_view, action, payload_decision)
    conv = Conversation.objects.create(user=user)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    return msg


@override_settings(ASSISTANT_ENABLED=True)
def test_confirm_creates_draft_and_is_single_use():
    admin = _admin()
    _seed_sales()
    _seed_open_period()
    msg = _proposal_message(admin, _sales_decision())
    client = APIClient()
    client.force_authenticate(user=admin)

    ok = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert ok.status_code == 200
    assert ok.json()["data"]["status"] == "confirmed"
    assert SalesOrder.objects.count() == 1
    assert AuditEntry.objects.filter(module="assistant",
                                     action="create_sales_order_draft").exists()

    # Single-use: the proposal is stamped consumed, a second confirm 409s and creates nothing more.
    again = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert again.status_code == 409
    assert SalesOrder.objects.count() == 1


@override_settings(ASSISTANT_ENABLED=True)
def test_dismiss_executes_nothing():
    admin = _admin()
    _seed_sales()
    msg = _proposal_message(admin, _sales_decision())
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "dismiss"}, format="json")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "dismissed"
    assert SalesOrder.objects.count() == 0
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "dismissed"


@override_settings(ASSISTANT_ENABLED=True)
def test_confirm_without_permission_is_forbidden():
    # The proposal was prepared by an admin, but the confirming user holds no create role.
    admin = _admin()
    _seed_sales()
    msg = _proposal_message(admin, _sales_decision())
    # Re-home the conversation onto a role-less owner, then confirm as them.
    owner = _nobody()
    msg.conversation.user = owner
    msg.conversation.save(update_fields=["user"])
    client = APIClient()
    client.force_authenticate(user=owner)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert res.status_code == 403
    assert SalesOrder.objects.count() == 0


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_loop_propose_emits_proposal_and_persists_it(monkeypatch):
    """The loop's fourth verb: a propose decision builds a card, emits a proposal event, ends the
    turn, and persists the proposal (pending) in the answer's meta — creating nothing."""
    admin = _admin()
    _seed_sales()
    conv = Conversation.objects.create(user=admin)

    decisions = iter([
        {"action": "propose", "name": "create_sales_order_draft", "why": "Preparing order",
         "customer": "Nile Traders", "items": [{"item": "SKU-1", "quantity": "2", "unit_cost": None}],
         "warehouse": "WH-1"},
    ])
    monkeypatch.setattr(agent, "complete_json", lambda *a, **k: next(decisions))
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **k: iter(["A draft is ready."]))

    events = list(agent.run(actor=admin, conversation=conv, question="make an order", page=None))

    kinds = [e["type"] for e in events]
    assert "proposal" in kinds and kinds[-1] == "done"
    prop = next(e for e in events if e["type"] == "proposal")
    assert prop["proposal"]["action"] == "create_sales_order_draft"
    assert prop["proposal"]["status"] == "pending"
    assert SalesOrder.objects.count() == 0  # a proposal writes nothing

    msg = conv.messages.get(role="assistant")
    assert msg.meta["proposal"]["status"] == "pending"
    assert msg.id == prop["message_id"]


# --- declarative confirmation registry (plan session 10) ---------------------------------------

def test_every_action_declares_kind_and_confirm():
    known_kinds = {"create", "update", "delete", "approve", "post", "reverse", "cancel",
                  "close_period", "bulk", "adjust"}
    for action in actions.ACTIONS.values():
        assert action.kind in known_kinds
        assert action.requires_confirm is True


def test_destructive_kind_without_confirm_is_impossible():
    fake = actions.Action(
        "fake_delete_everything", "test only", {}, lambda actor, **_: {}, lambda actor, payload: {},
        kind="delete", requires_confirm=False,
    )
    with pytest.raises(AssertionError):
        assert fake.requires_confirm or fake.kind not in actions.DESTRUCTIVE_KINDS, (
            f"action {fake.name}: destructive kind '{fake.kind}' must require confirmation")


def test_proposal_kind_rides_in_payload():
    admin = _admin()
    _seed_sales()
    proposal = actions.build(admin, "create_sales_order_draft", _sales_decision())
    assert proposal["kind"] == "create"


def test_execute_reruns_permission_check():
    admin = _admin()
    _seed_sales()
    proposal = actions.build(admin, "create_sales_order_draft", _sales_decision())
    assert "error" not in proposal

    stripped = _nobody("act_stripped")
    with pytest.raises(PermissionError):
        actions.execute(stripped, "create_sales_order_draft", proposal["payload"])
    assert SalesOrder.objects.count() == 0


def test_execute_revalidates_before_write():
    admin = _admin()
    _seed_sales()
    proposal = actions.build(admin, "create_sales_order_draft", _sales_decision())
    assert "error" not in proposal

    Customer.objects.filter(code="C-1").delete()  # entity vanished between build and execute
    with pytest.raises(ValueError):
        actions.execute(admin, "create_sales_order_draft", proposal["payload"])
    assert SalesOrder.objects.count() == 0


@override_settings(ASSISTANT_ENABLED=True)
def test_foreign_message_is_not_found():
    admin = _admin()
    _seed_sales()
    msg = _proposal_message(admin, _sales_decision())
    other = APIClient()
    other.force_authenticate(user=_nobody("stranger"))

    res = other.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert res.status_code == 404


# --- quotation + edit-order actions (agent-actions FILE_01) --------------------------------------

def _quote_decision():
    return {"customer": "Nile Traders", "items": [{"item": "SKU-1", "quantity": "3"}],
            "warehouse": "WH-1"}


def test_build_then_execute_creates_quotation_draft():
    admin = _admin()
    _seed_sales()

    proposal = actions.build(admin, "create_quotation_draft", _quote_decision())
    assert "error" not in proposal
    assert proposal["action"] == "create_quotation_draft"
    kinds = {r["type"] for r in proposal["records"]}
    assert {"customer", "item"} <= kinds
    assert Quotation.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_quotation_draft", proposal["payload"])
    quote = Quotation.objects.get()
    assert quote.status == QuotationStatus.DRAFT
    assert quote.customer.code == "C-1"
    assert result["links"][0]["value"] == str(quote.id)


def test_quotation_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_sales()

    proposal = actions.build(nobody, "create_quotation_draft", _quote_decision())
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_quotation_draft",
                        {"customer_code": "C-1", "warehouse_code": "WH-1",
                         "lines": [{"item_sku": "SKU-1", "quantity": "1", "unit_price_minor": 0}]})
    assert Quotation.objects.count() == 0


def _approved_quotation(customer: Customer) -> Quotation:
    quote = quotation_services.create_quotation(
        customer=customer, warehouse_code="WH-1",
        lines=[quotation_services.QuoteLineInput(item_sku="SKU-1", quantity=3, unit_price_minor=1000)],
    )
    return quotation_services.submit_quotation(quote)  # auto-approves (below threshold)


def test_convert_approved_quotation_creates_order_draft():
    admin = _admin()
    _seed_sales()
    customer = Customer.objects.get(code="C-1")
    quote = _approved_quotation(customer)

    proposal = actions.build(admin, "convert_quotation", {"query": quote.number})
    assert "error" not in proposal
    assert proposal["action"] == "convert_quotation"
    assert not proposal["risks"]
    assert SalesOrder.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "convert_quotation", proposal["payload"])
    order = SalesOrder.objects.get()
    assert order.customer.code == "C-1"
    quote.refresh_from_db()
    assert quote.status == QuotationStatus.CONVERTED
    assert result["links"][0]["value"] == str(order.id)


def test_convert_quotation_not_approved_surfaces_risk_and_fails_on_confirm():
    admin = _admin()
    _seed_sales()
    customer = Customer.objects.get(code="C-1")
    quote = quotation_services.create_quotation(
        customer=customer, warehouse_code="WH-1",
        lines=[quotation_services.QuoteLineInput(item_sku="SKU-1", quantity=3, unit_price_minor=1000)],
    )  # still draft, never submitted

    proposal = actions.build(admin, "convert_quotation", {"query": quote.number})
    assert "error" not in proposal  # still a card — the risk line warns, it doesn't block
    assert proposal["risks"]

    with pytest.raises(Exception):
        actions.execute(admin, "convert_quotation", proposal["payload"])
    assert SalesOrder.objects.count() == 0


def test_convert_quotation_unknown_query_is_a_blocker():
    admin = _admin()
    _seed_sales()

    proposal = actions.build(admin, "convert_quotation", {"query": "QUO-9999-000000"})
    assert "blocker" in proposal


def test_edit_draft_order_updates_lines():
    admin = _admin()
    _seed_sales()
    Item.objects.create(sku="SKU-2", name="Red Gadget")
    customer = Customer.objects.get(code="C-1")
    order = sales_create_order(
        customer=customer, warehouse_code="WH-1",
        lines=[OrderLineInput(item_sku="SKU-1", quantity=3, unit_price_minor=1000)],
    )

    proposal = actions.build(admin, "edit_sales_order_draft",
                             {"query": order.number,
                              "items": [{"item": "SKU-2", "quantity": "5", "unit_price": 2000}]})
    assert "error" not in proposal
    assert proposal["action"] == "edit_sales_order_draft"

    result = actions.execute(admin, "edit_sales_order_draft", proposal["payload"])
    order.refresh_from_db()
    assert order.lines.count() == 1
    line = order.lines.get()
    assert line.item_sku == "SKU-2"
    assert line.quantity == 5
    assert result["links"][0]["value"] == str(order.id)


def test_edit_non_draft_order_returns_error_no_card():
    admin = _admin()
    _seed_sales()
    customer = Customer.objects.get(code="C-1")
    order = sales_create_order(
        customer=customer, warehouse_code="WH-1",
        lines=[OrderLineInput(item_sku="SKU-1", quantity=3, unit_price_minor=1000)],
    )
    order.status = "confirmed"
    order.save(update_fields=["status"])

    proposal = actions.build(admin, "edit_sales_order_draft",
                             {"query": order.number,
                              "items": [{"item": "SKU-1", "quantity": "1", "unit_price": 1000}]})
    assert "error" in proposal
    assert "action" not in proposal  # never a card for a non-draft order


def test_edit_sales_order_permission_refused_at_both_stages():
    admin = _admin()
    _seed_sales()
    customer = Customer.objects.get(code="C-1")
    order = sales_create_order(
        customer=customer, warehouse_code="WH-1",
        lines=[OrderLineInput(item_sku="SKU-1", quantity=3, unit_price_minor=1000)],
    )
    nobody = _nobody()

    proposal = actions.build(nobody, "edit_sales_order_draft",
                             {"query": order.number,
                              "items": [{"item": "SKU-1", "quantity": "1", "unit_price": 1000}]})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "edit_sales_order_draft",
                        {"order_number": order.number,
                         "lines": [{"item_sku": "SKU-1", "quantity": "1", "unit_price_minor": 1000}]})


# --- purchasing actions (agent-actions FILE_02) --------------------------------------------------

def _seed_purchasing():
    Supplier.objects.create(code="S-1", name="Cairo Supplies")
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    Warehouse.objects.create(code="WH-1", name="Main")


def _po_decision():
    return {"supplier": "Cairo Supplies",
            "items": [{"item": "SKU-1", "quantity": "3", "unit_cost": 1000}],
            "warehouse": "WH-1"}


def test_build_then_execute_creates_purchase_order_draft():
    admin = _admin()
    _seed_purchasing()

    proposal = actions.build(admin, "create_purchase_order_draft", _po_decision())
    assert "error" not in proposal
    assert proposal["action"] == "create_purchase_order_draft"
    kinds = {r["type"] for r in proposal["records"]}
    assert {"supplier", "item"} <= kinds
    assert not proposal["risks"]  # a real cost was given
    assert PurchaseOrder.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_purchase_order_draft", proposal["payload"])
    order = PurchaseOrder.objects.get()
    assert order.status == "draft"
    assert order.supplier.code == "S-1"
    assert result["links"][0]["value"] == str(order.id)


def test_purchase_order_item_without_cost_is_a_risk_and_still_confirmable():
    admin = _admin()
    _seed_purchasing()

    proposal = actions.build(admin, "create_purchase_order_draft",
                             {"supplier": "Cairo Supplies",
                              "items": [{"item": "SKU-1", "quantity": "3"}], "warehouse": "WH-1"})
    assert "error" not in proposal
    assert proposal["risks"]  # no cost on record — flagged, not blocked

    actions.execute(admin, "create_purchase_order_draft", proposal["payload"])
    assert PurchaseOrder.objects.count() == 1


def test_purchase_order_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_purchasing()

    proposal = actions.build(nobody, "create_purchase_order_draft", _po_decision())
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_purchase_order_draft",
                        {"supplier_code": "S-1", "warehouse_code": "WH-1",
                         "lines": [{"item_sku": "SKU-1", "quantity": "1", "unit_cost_minor": 1000}]})
    assert PurchaseOrder.objects.count() == 0


def _approved_request(supplier: Supplier) -> PurchaseRequest:
    req = purchasing_create_request(
        supplier=supplier, warehouse_code="WH-1",
        lines=[PRLineInput(item_sku="SKU-1", quantity=3, unit_cost_minor=1000)],
    )
    return purchasing_submit_request(req)  # auto-approves (below threshold)


def test_convert_approved_purchase_request_creates_order_draft():
    admin = _admin()
    _seed_purchasing()
    supplier = Supplier.objects.get(code="S-1")
    req = _approved_request(supplier)

    proposal = actions.build(admin, "convert_purchase_request", {"query": req.number})
    assert "error" not in proposal
    assert proposal["action"] == "convert_purchase_request"
    assert not proposal["risks"]
    assert PurchaseOrder.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "convert_purchase_request", proposal["payload"])
    order = PurchaseOrder.objects.get()
    assert order.supplier.code == "S-1"
    req.refresh_from_db()
    assert req.status == "converted"
    assert result["links"][0]["value"] == str(order.id)


def test_convert_purchase_request_not_approved_surfaces_risk_and_fails_on_confirm():
    admin = _admin()
    _seed_purchasing()
    supplier = Supplier.objects.get(code="S-1")
    req = purchasing_create_request(
        supplier=supplier, warehouse_code="WH-1",
        lines=[PRLineInput(item_sku="SKU-1", quantity=3, unit_cost_minor=1000)],
    )  # still draft, never submitted

    proposal = actions.build(admin, "convert_purchase_request", {"query": req.number})
    assert "error" not in proposal  # still a card — the risk line warns, it doesn't block
    assert proposal["risks"]

    with pytest.raises(Exception):
        actions.execute(admin, "convert_purchase_request", proposal["payload"])
    assert PurchaseOrder.objects.count() == 0


def test_convert_purchase_request_unknown_query_is_a_blocker():
    admin = _admin()
    _seed_purchasing()

    proposal = actions.build(admin, "convert_purchase_request", {"query": "PR-9999-000000"})
    assert "blocker" in proposal


def test_convert_purchase_request_permission_refused_at_both_stages():
    admin = _admin()
    _seed_purchasing()
    supplier = Supplier.objects.get(code="S-1")
    req = _approved_request(supplier)
    nobody = _nobody()

    proposal = actions.build(nobody, "convert_purchase_request", {"query": req.number})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "convert_purchase_request", {"request_number": req.number})
    assert PurchaseOrder.objects.count() == 0


def test_create_supplier_exact_duplicate_blocks_near_duplicate_warns():
    admin = _admin()
    Supplier.objects.create(code="S-1", name="Cairo Supplies")

    exact = actions.build(admin, "create_supplier", {"query": "Cairo Supplies"})
    assert "error" in exact and "already exists" in exact["error"]

    near = actions.build(admin, "create_supplier", {"query": "Cairo Supplies Co"})
    assert "error" not in near
    assert near["risks"], "a close name should surface a risk line, not a silent create"

    actions.execute(admin, "create_supplier", near["payload"])
    assert Supplier.objects.filter(name="Cairo Supplies Co").exists()


def test_create_supplier_permission_refused_at_both_stages():
    nobody = _nobody()

    proposal = actions.build(nobody, "create_supplier", {"query": "New Supplier"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_supplier", {"name": "New Supplier"})
    assert Supplier.objects.count() == 0


# --- inventory actions (agent-actions FILE_03) ----------------------------------------------------

def _seed_inventory():
    item = Item.objects.create(sku="SKU-1", name="Blue Widget")
    wh_a = Warehouse.objects.create(code="WH-A", name="North")
    wh_b = Warehouse.objects.create(code="WH-B", name="South")
    StockBalance.objects.create(item=item, warehouse=wh_a, quantity=Decimal("50"), value_minor=5000)
    return item, wh_a, wh_b


def _transfer_decision():
    return {"item": "SKU-1", "quantity": "20", "from_warehouse": "WH-A", "to_warehouse": "WH-B"}


def test_build_then_execute_creates_stock_transfer_draft():
    admin = _admin()
    _seed_inventory()

    proposal = actions.build(admin, "create_stock_transfer_draft", _transfer_decision())
    assert "error" not in proposal
    assert proposal["action"] == "create_stock_transfer_draft"
    assert not proposal["risks"]  # 20 of 50 on hand — no risk
    assert StockTransfer.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_stock_transfer_draft", proposal["payload"])
    transfer = StockTransfer.objects.get()
    assert transfer.status == "draft"
    assert transfer.source.code == "WH-A"
    assert transfer.destination.code == "WH-B"
    assert transfer.quantity == Decimal("20")
    # A draft never moves stock or hits the GL.
    from erp.inventory.domain.models import StockMovement

    assert StockMovement.objects.count() == 0
    balance = StockBalance.objects.get(item__sku="SKU-1", warehouse__code="WH-A")
    assert balance.quantity == Decimal("50")
    assert result["links"][0]["value"] == str(transfer.id)
    assert AuditEntry.objects.filter(module="inventory", action="create_transfer_draft").exists()


def test_stock_transfer_over_on_hand_is_a_risk_and_still_confirmable():
    admin = _admin()
    _seed_inventory()

    proposal = actions.build(admin, "create_stock_transfer_draft",
                             {"item": "SKU-1", "quantity": "999",
                              "from_warehouse": "WH-A", "to_warehouse": "WH-B"})
    assert "error" not in proposal
    assert proposal["risks"]  # exceeds on-hand — flagged, not blocked

    actions.execute(admin, "create_stock_transfer_draft", proposal["payload"])
    assert StockTransfer.objects.count() == 1


def test_stock_transfer_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_inventory()

    proposal = actions.build(nobody, "create_stock_transfer_draft", _transfer_decision())
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_stock_transfer_draft",
                        {"item_sku": "SKU-1", "source_code": "WH-A", "destination_code": "WH-B",
                         "quantity": "20"})
    assert StockTransfer.objects.count() == 0


def test_build_then_execute_creates_stock_count_draft():
    admin = _admin()
    _seed_inventory()

    proposal = actions.build(admin, "create_stock_count_draft", {"warehouse": "WH-A"})
    assert "error" not in proposal
    assert proposal["action"] == "create_stock_count_draft"
    assert proposal["affected"] == 1  # one item has a balance at WH-A
    assert StockCount.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_stock_count_draft", proposal["payload"])
    count = StockCount.objects.get()
    assert count.status == "counting"
    assert count.warehouse.code == "WH-A"
    assert count.lines.count() == 1
    assert count.lines.get().system_quantity == Decimal("50")
    assert result["links"][0]["value"] == str(count.id)


def test_stock_count_empty_warehouse_is_an_error_no_card():
    admin = _admin()
    _seed_inventory()

    proposal = actions.build(admin, "create_stock_count_draft", {"warehouse": "WH-B"})
    assert "error" in proposal
    assert "action" not in proposal


def test_stock_count_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_inventory()

    proposal = actions.build(nobody, "create_stock_count_draft", {"warehouse": "WH-A"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_stock_count_draft", {"warehouse_code": "WH-A"})
    assert StockCount.objects.count() == 0


def test_set_reorder_point_updates_master_and_audits():
    admin = _admin()
    item, _, _ = _seed_inventory()
    assert item.reorder_point == 0

    proposal = actions.build(admin, "set_reorder_point", {"item": "SKU-1", "reorder_point": "50"})
    assert "error" not in proposal
    assert proposal["action"] == "set_reorder_point"
    assert proposal["kind"] == "update"

    result = actions.execute(admin, "set_reorder_point", proposal["payload"])
    item.refresh_from_db()
    assert item.reorder_point == 50
    assert result["links"][0]["value"] == "SKU-1"
    assert AuditEntry.objects.filter(module="inventory", action="set_reorder_point").exists()


def test_set_reorder_point_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_inventory()

    proposal = actions.build(nobody, "set_reorder_point", {"item": "SKU-1", "reorder_point": "50"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "set_reorder_point", {"sku": "SKU-1", "reorder_point": "50"})
    Item.objects.get(sku="SKU-1").reorder_point == 0


# --- accounting actions (agent-actions FILE_04) ---------------------------------------------------

from erp.accounting.domain.models import Account, JournalEntry
from erp.accounting.tests.factories import make_coa, make_period


def _seed_accounting():
    make_coa()
    make_period()  # code "2026-06", open, covers 2026-06-01..2026-06-30


def _journal_decision():
    return {"lines": [{"account": "Rent Expense", "debit": 5000},
                      {"account": "Cash", "credit": 5000}],
            "date": "2026-06-15"}


def test_build_then_execute_creates_journal_entry_draft():
    admin = _admin()
    _seed_accounting()

    proposal = actions.build(admin, "create_journal_entry_draft", _journal_decision())
    assert "error" not in proposal
    assert proposal["action"] == "create_journal_entry_draft"
    kinds = {r["type"] for r in proposal["records"]}
    assert kinds == {"account"}
    assert JournalEntry.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_journal_entry_draft", proposal["payload"])
    entry = JournalEntry.objects.get()
    assert entry.status == "draft"
    assert entry.lines.count() == 2
    assert result["links"][0]["value"] == str(entry.id)
    assert AuditEntry.objects.filter(module="accounting", action="create_draft_journal").exists()


def test_unbalanced_journal_is_an_error_no_card():
    admin = _admin()
    _seed_accounting()

    proposal = actions.build(admin, "create_journal_entry_draft",
                             {"lines": [{"account": "Rent Expense", "debit": 5000},
                                       {"account": "Cash", "credit": 4000}],
                              "date": "2026-06-15"})
    assert "error" in proposal
    assert "action" not in proposal
    assert JournalEntry.objects.count() == 0


def test_journal_unknown_account_is_an_error_no_card():
    admin = _admin()
    _seed_accounting()

    proposal = actions.build(admin, "create_journal_entry_draft",
                             {"lines": [{"account": "Not A Real Account Name At All", "debit": 5000},
                                       {"account": "Cash", "credit": 5000}],
                              "date": "2026-06-15"})
    assert "error" in proposal
    assert "action" not in proposal


def test_journal_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_accounting()

    proposal = actions.build(nobody, "create_journal_entry_draft", _journal_decision())
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_journal_entry_draft",
                        {"lines": [{"account_code": "5100", "debit": 5000, "credit": 0},
                                   {"account_code": "1000", "debit": 0, "credit": 5000}],
                         "date": "2026-06-15", "reference": ""})
    assert JournalEntry.objects.count() == 0


# --- post a drafted journal entry (agent-posting FILE_02, the first risk="post" action) ----------

def _make_draft(actor):
    """A DRAFT journal entry to post: Dr Rent Expense 50.00 / Cr Cash 50.00 (challenge = 50.00 EGP)."""
    import datetime as dt
    from erp.accounting import contracts as acc
    return acc.create_journal_entry_draft(
        acc.JournalInput(date=dt.date(2026, 6, 15), lines=[
            acc.LineInput(account_code="5100", debit=5000),
            acc.LineInput(account_code="1000", credit=5000)]),
        actor=actor,
    )


def test_post_journal_draft_build_carries_challenge():
    admin = _admin()
    _seed_accounting()
    entry = _make_draft(admin)
    _set_posting_enabled(True)

    proposal = actions.build(admin, "post_journal_entry_draft", {"query": entry.number})
    assert proposal["action"] == "post_journal_entry_draft"
    assert proposal["challenge"] == {"label": "50.00 EGP", "minor": 5000}
    assert {r["type"] for r in proposal["records"]} == {"journalEntry"}
    assert JournalEntry.objects.get(id=entry.id).status == "draft"  # building posts nothing


def test_post_journal_draft_refused_when_posting_disabled():
    admin = _admin()
    _seed_accounting()
    entry = _make_draft(admin)
    _set_posting_enabled(False)

    proposal = actions.build(admin, "post_journal_entry_draft", {"query": entry.number})
    assert "action" not in proposal
    assert "Settings" in proposal["error"]  # points a fixer at the toggle


def test_post_journal_draft_refused_for_wrong_role():
    _seed_accounting()
    admin = _admin()
    entry = _make_draft(admin)
    _set_posting_enabled(True)

    nobody = _nobody()
    proposal = actions.build(nobody, "post_journal_entry_draft", {"query": entry.number})
    assert "action" not in proposal
    assert "permission" in proposal["error"].lower()


def test_post_journal_draft_on_already_posted_is_calm_error_no_card():
    admin = _admin()
    _seed_accounting()
    entry = _make_draft(admin)
    _set_posting_enabled(True)

    from erp.accounting import contracts as acc
    acc.post_draft_journal_entry(acc.get_journal_entry(admin, str(entry.id)), actor=admin)

    proposal = actions.build(admin, "post_journal_entry_draft", {"query": entry.number})
    assert "action" not in proposal  # no draft matches once it's posted — a calm note, no card
    assert "error" in proposal


@override_settings(ASSISTANT_ENABLED=True)
def test_post_journal_draft_confirm_posts_to_ledger():
    """The real action through the real confirm endpoint: right retype → the draft posts, one
    audit row, the card flips to confirmed."""
    admin = _admin()
    _seed_accounting()
    entry = _make_draft(admin)
    _set_posting_enabled(True)

    proposal = actions.build(admin, "post_journal_entry_draft", {"query": entry.number})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 5000}, format="json")
    assert res.status_code == 200, res.data
    entry.refresh_from_db()
    assert entry.status == "posted"
    assert AuditEntry.objects.filter(
        module="accounting", action="post_journal", entity_id=entry.number
    ).count() == 1
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"


# --- receive a purchase order (agent-posting FILE_03, pattern replication of FILE_02) -------------

def _make_po(confirm: bool = True, qty: str = "5", cost: int = 100_00) -> PurchaseOrder:
    from erp.purchasing.services import POLineInput, confirm_order, create_order
    from erp.purchasing.tests.factories import make_item as make_po_item
    from erp.purchasing.tests.factories import make_supplier as make_po_supplier
    from erp.purchasing.tests.factories import make_warehouse as make_po_warehouse
    from erp.purchasing.tests.factories import make_books as make_po_books

    make_po_books()
    make_po_item()
    supplier = make_po_supplier()
    wh = make_po_warehouse()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )
    if confirm:
        confirm_order(order)
        order.refresh_from_db()
    return order


def test_receive_po_build_carries_challenge():
    from erp.accounting.domain.money import Money

    admin = _admin()
    order = _make_po(qty="5", cost=100_00)
    _set_posting_enabled(True)

    proposal = actions.build(admin, "receive_purchase_order", {"query": order.number})
    assert proposal["action"] == "receive_purchase_order"
    assert proposal["challenge"] == {"label": Money(50000, "EGP").format(), "minor": 50000}
    assert proposal["records"] == [
        {"type": "purchaseOrder", "value": str(order.id), "label": order.number}]
    order.refresh_from_db()
    assert order.status == "confirmed"  # building receives nothing


def test_receive_po_refused_when_posting_disabled():
    admin = _admin()
    order = _make_po()
    _set_posting_enabled(False)

    proposal = actions.build(admin, "receive_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert "Settings" in proposal["error"]


def test_receive_po_refused_for_wrong_role():
    order = _make_po()
    _set_posting_enabled(True)
    nobody = _nobody()

    proposal = actions.build(nobody, "receive_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert "permission" in proposal["error"].lower()


def test_receive_po_on_draft_is_calm_error_no_card():
    admin = _admin()
    order = _make_po(confirm=False)  # still draft — not confirmed yet
    _set_posting_enabled(True)

    proposal = actions.build(admin, "receive_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert order.number in proposal["error"]
    assert "confirmed" in proposal["error"]


@override_settings(ASSISTANT_ENABLED=True)
def test_receive_po_confirm_receives_and_is_single_use():
    """The real action through the real confirm endpoint: right retype → the order receives in
    full, one audit row, stock on hand increases; a second confirm 409s and moves nothing more."""
    admin = _admin()
    order = _make_po(qty="5", cost=100_00)
    _set_posting_enabled(True)

    proposal = actions.build(admin, "receive_purchase_order", {"query": order.number})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 50000}, format="json")
    assert res.status_code == 200, res.data
    order.refresh_from_db()
    assert order.status == "received"
    line = order.lines.get()
    assert line.received_qty == Decimal("5")
    balance = StockBalance.objects.get(item__sku="WIDGET", warehouse__code=order.warehouse_code)
    assert balance.quantity == Decimal("5")
    assert AuditEntry.objects.filter(
        module="purchasing", action="receive_order", entity_id=order.number
    ).count() == 1
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"

    # Single-use: a second confirm of the same card 409s and moves nothing more.
    again = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                   "typed_minor": 50000}, format="json")
    assert again.status_code == 409
    line.refresh_from_db()
    assert line.received_qty == Decimal("5")


# --- bill a purchase order (agent-posting FILE_04, pattern replication of FILE_03) ----------------

def _billable_po(qty: str = "5", cost: int = 100_00, tax_code: str = "",
                 received: dict[int, Decimal] | None = None) -> PurchaseOrder:
    from erp.purchasing.services import POLineInput, confirm_order, create_order, receive_order
    from erp.purchasing.tests.factories import make_item as make_po_item
    from erp.purchasing.tests.factories import make_supplier as make_po_supplier
    from erp.purchasing.tests.factories import make_warehouse as make_po_warehouse
    from erp.purchasing.tests.factories import make_books as make_po_books

    make_po_books()
    make_po_item()
    supplier = make_po_supplier()
    wh = make_po_warehouse()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, tax_code=tax_code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )
    confirm_order(order)
    receive_order(order, received=received)
    order.refresh_from_db()
    return order


def test_bill_po_build_shows_net_vat_gross():
    from erp.accounting.domain.money import Money

    admin = _admin()
    order = _billable_po(qty="5", cost=100_00, tax_code="VAT14")  # net 500.00, VAT14 → 70.00
    _set_posting_enabled(True)

    proposal = actions.build(admin, "bill_purchase_order", {"query": order.number})
    assert proposal["action"] == "bill_purchase_order"
    assert proposal["challenge"] == {"label": Money(57000, "EGP").format(), "minor": 57000}
    order.refresh_from_db()
    assert order.status == "received"  # building bills nothing


def test_bill_po_refused_when_posting_disabled():
    admin = _admin()
    order = _billable_po()
    _set_posting_enabled(False)

    proposal = actions.build(admin, "bill_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert "Settings" in proposal["error"]


def test_bill_po_refused_for_wrong_role():
    order = _billable_po()
    _set_posting_enabled(True)
    nobody = _nobody()

    proposal = actions.build(nobody, "bill_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert "permission" in proposal["error"].lower()


def test_bill_po_on_partial_receipt_is_calm_error_no_card():
    admin = _admin()
    order = _billable_po(qty="5", received={1: Decimal("2")})  # short 3 of 5
    _set_posting_enabled(True)

    proposal = actions.build(admin, "bill_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert order.number in proposal["error"]
    assert "2.0000 of 5.0000" in proposal["error"]
    assert "partially received" in proposal["error"].lower()


@override_settings(ASSISTANT_ENABLED=True)
def test_bill_po_confirm_bills_and_posts_gl():
    """The real action through the real confirm endpoint: right retype → the order bills, one
    audit row, a GRNI/VAT-input/AP journal entry posts."""
    admin = _admin()
    order = _billable_po(qty="5", cost=100_00, tax_code="VAT14")
    _set_posting_enabled(True)

    proposal = actions.build(admin, "bill_purchase_order", {"query": order.number})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 57000}, format="json")
    assert res.status_code == 200, res.data
    order.refresh_from_db()
    assert order.status == "billed"
    assert order.bill_number
    entry = JournalEntry.objects.get(number=order.bill_number)
    accounts = {ln.account.code for ln in entry.lines.all()}
    assert accounts == {"2150", "1190", "2000"}  # GRNI, VAT input, AP
    assert AuditEntry.objects.filter(
        module="purchasing", action="bill_order", entity_id=order.number
    ).count() == 1
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"


def test_bill_po_over_approval_limit_surfaces_calm_apperror():
    """An actor whose role has a configured 'invoice' ceiling below the bill's gross gets the
    underlying ApprovalLimitExceededError, flowing through ActionExecuteView's existing AppError
    path unchanged — this action needs no translation of its own."""
    from erp.identity.models import ApprovalLimit, RolePermission
    from erp.identity.rbac import DataScope

    manager = _with_role("bill_capped", BRANCH_MANAGER)
    role = Group.objects.get(name=BRANCH_MANAGER)
    # A bare test role has no RolePermission rows, so scope_for defaults to OWN — grant view-all so
    # find_orders can see an order this actor didn't create (mirrors what seed_identity grants).
    RolePermission.objects.update_or_create(
        role=role, code="purchasing.order.view", defaults={"scope": DataScope.ALL},
    )
    order = _billable_po(qty="5", cost=100_00)  # net 500.00, no VAT → gross 500.00
    ApprovalLimit.objects.update_or_create(
        role=role, document_type="invoice",
        defaults={"limit_minor": 10_000},  # 100.00 ceiling; this bill is 500.00
    )
    _set_posting_enabled(True)

    proposal = actions.build(manager, "bill_purchase_order", {"query": order.number})
    conv = Conversation.objects.create(user=manager)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=manager)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 50000}, format="json")
    assert res.status_code == 422, res.data
    order.refresh_from_db()
    assert order.status == "received"  # nothing posted
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "pending"  # unconsumed — the card stays usable


# --- pay a purchase order (agent-posting FILE_05, pattern replication of FILE_04) -----------------

def _billed_po(qty: str = "5", cost: int = 100_00, tax_code: str = "") -> PurchaseOrder:
    from erp.purchasing.services import (
        POLineInput, bill_order, confirm_order, create_order, receive_order,
    )
    from erp.purchasing.tests.factories import make_item as make_po_item
    from erp.purchasing.tests.factories import make_supplier as make_po_supplier
    from erp.purchasing.tests.factories import make_warehouse as make_po_warehouse
    from erp.purchasing.tests.factories import make_books as make_po_books

    make_po_books()
    make_po_item()
    supplier = make_po_supplier()
    wh = make_po_warehouse()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, tax_code=tax_code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    order.refresh_from_db()
    return order


def test_pay_po_build_defaults_to_full_outstanding():
    from erp.accounting.domain.money import Money

    admin = _admin()
    order = _billed_po(qty="5", cost=100_00)  # billed 500.00, no VAT
    _set_posting_enabled(True)

    proposal = actions.build(admin, "pay_purchase_order", {"query": order.number})
    assert proposal["action"] == "pay_purchase_order"
    assert proposal["challenge"] == {"label": Money(50000, "EGP").format(), "minor": 50000}
    order.refresh_from_db()
    assert order.status == "billed"  # building pays nothing


def test_pay_po_build_with_partial_amount():
    admin = _admin()
    order = _billed_po(qty="5", cost=100_00)  # 500.00 outstanding
    _set_posting_enabled(True)

    proposal = actions.build(admin, "pay_purchase_order", {"query": order.number, "amount": 20000})
    assert proposal["challenge"]["minor"] == 20000


def test_pay_po_amount_over_outstanding_is_calm_error_no_card():
    admin = _admin()
    order = _billed_po(qty="5", cost=100_00)  # 500.00 outstanding
    _set_posting_enabled(True)

    proposal = actions.build(admin, "pay_purchase_order", {"query": order.number, "amount": 99999999})
    assert "action" not in proposal
    assert order.number in proposal["error"]


def test_pay_po_refused_when_posting_disabled():
    admin = _admin()
    order = _billed_po()
    _set_posting_enabled(False)

    proposal = actions.build(admin, "pay_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert "Settings" in proposal["error"]


def test_pay_po_refused_for_wrong_role():
    order = _billed_po()
    _set_posting_enabled(True)
    nobody = _nobody()

    proposal = actions.build(nobody, "pay_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert "permission" in proposal["error"].lower()


def test_pay_po_not_yet_billed_is_calm_error_no_card():
    from erp.purchasing.services import POLineInput, confirm_order, create_order
    from erp.purchasing.tests.factories import make_item as make_po_item
    from erp.purchasing.tests.factories import make_supplier as make_po_supplier
    from erp.purchasing.tests.factories import make_warehouse as make_po_warehouse
    from erp.purchasing.tests.factories import make_books as make_po_books

    admin = _admin()
    make_po_books()
    make_po_item()
    supplier = make_po_supplier()
    wh = make_po_warehouse()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("5"), unit_cost_minor=100_00)],
    )
    confirm_order(order)  # confirmed, not received or billed
    _set_posting_enabled(True)

    proposal = actions.build(admin, "pay_purchase_order", {"query": order.number})
    assert "action" not in proposal
    assert order.number in proposal["error"]
    assert "billed" in proposal["error"].lower()


@override_settings(ASSISTANT_ENABLED=True)
def test_pay_po_confirm_pays_partial_then_full_and_is_single_use():
    """The real action through the real confirm endpoint: a partial payment leaves the order
    'billed' with reduced outstanding, one GL entry (AP debit / Cash credit), one audit row; a
    second confirm of the same card 409s and pays nothing more."""
    admin = _admin()
    order = _billed_po(qty="5", cost=100_00)  # billed 500.00
    _set_posting_enabled(True)

    proposal = actions.build(admin, "pay_purchase_order", {"query": order.number, "amount": 20000})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 20000}, format="json")
    assert res.status_code == 200, res.data
    order.refresh_from_db()
    assert order.status == "billed"  # not fully paid yet
    assert order.paid_minor == 20000
    entry = JournalEntry.objects.filter(reference=order.number, memo__icontains="Payment").get()
    accounts = {ln.account.code for ln in entry.lines.all()}
    assert accounts == {"2000", "1000"}  # AP debit, Cash credit
    assert AuditEntry.objects.filter(
        module="purchasing", action="pay_order", entity_id=order.number
    ).count() == 1
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"

    # Single-use: a second confirm of the same card 409s and pays nothing more.
    again = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                   "typed_minor": 20000}, format="json")
    assert again.status_code == 409
    order.refresh_from_db()
    assert order.paid_minor == 20000

    # Paying the remaining outstanding flips the order to fully paid.
    proposal2 = actions.build(admin, "pay_purchase_order", {"query": order.number})
    assert proposal2["challenge"]["minor"] == 30000
    msg2 = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                  meta={"proposal": {**proposal2, "status": "pending"}})
    res2 = client.post(EXEC_URL, {"message_id": msg2.id, "decision": "confirm",
                                  "typed_minor": 30000}, format="json")
    assert res2.status_code == 200, res2.data
    order.refresh_from_db()
    assert order.status == "paid"
    assert order.paid_minor == 50000


# --- approve a purchase request (agent-posting FILE_06, pattern replication of FILE_04/05) --------

def _submitted_request(supplier: Supplier) -> PurchaseRequest:
    """Above the auto-approval threshold (10,000.00 EGP) — submit leaves it 'submitted', awaiting
    a manager, instead of auto-approving."""
    req = purchasing_create_request(
        supplier=supplier, warehouse_code="WH-1",
        lines=[PRLineInput(item_sku="SKU-1", quantity=200, unit_cost_minor=10000)],  # 20,000.00 EGP
    )
    return purchasing_submit_request(req)


def test_approve_pr_build_shows_subtotal_challenge():
    from erp.accounting.domain.money import Money

    admin = _admin()
    _seed_purchasing()
    supplier = Supplier.objects.get(code="S-1")
    req = _submitted_request(supplier)
    _set_posting_enabled(True)

    proposal = actions.build(admin, "approve_purchase_request", {"query": req.number})
    assert proposal["action"] == "approve_purchase_request"
    assert proposal["challenge"] == {"label": Money(2_000_000, "EGP").format(), "minor": 2_000_000}
    req.refresh_from_db()
    assert req.status == "submitted"  # building approves nothing


def test_approve_pr_on_draft_or_approved_is_calm_error_no_card():
    admin = _admin()
    _seed_purchasing()
    supplier = Supplier.objects.get(code="S-1")
    _set_posting_enabled(True)

    draft = purchasing_create_request(
        supplier=supplier, warehouse_code="WH-1",
        lines=[PRLineInput(item_sku="SKU-1", quantity=3, unit_cost_minor=1000)],
    )  # still draft, never submitted
    proposal = actions.build(admin, "approve_purchase_request", {"query": draft.number})
    assert "action" not in proposal
    assert draft.number in proposal["error"]
    assert "draft" in proposal["error"].lower()

    approved = _approved_request(Supplier.objects.create(code="S-2", name="Delta Supplies"))
    proposal2 = actions.build(admin, "approve_purchase_request", {"query": approved.number})
    assert "action" not in proposal2
    assert approved.number in proposal2["error"]
    assert "approved" in proposal2["error"].lower()


def test_approve_pr_refused_when_posting_disabled():
    admin = _admin()
    _seed_purchasing()
    req = _submitted_request(Supplier.objects.get(code="S-1"))
    _set_posting_enabled(False)

    proposal = actions.build(admin, "approve_purchase_request", {"query": req.number})
    assert "action" not in proposal
    assert "Settings" in proposal["error"]


def test_approve_pr_refused_for_wrong_role():
    _seed_purchasing()
    req = _submitted_request(Supplier.objects.get(code="S-1"))
    _set_posting_enabled(True)
    nobody = _nobody()

    proposal = actions.build(nobody, "approve_purchase_request", {"query": req.number})
    assert "action" not in proposal
    assert "permission" in proposal["error"].lower()


@override_settings(ASSISTANT_ENABLED=True)
def test_approve_pr_confirm_approves_and_is_single_use():
    """The real action through the real confirm endpoint: right retype → the request approves, one
    audit row, approved_at/approved_by set; a second confirm 409s and changes nothing more."""
    admin = _admin()
    _seed_purchasing()
    req = _submitted_request(Supplier.objects.get(code="S-1"))
    _set_posting_enabled(True)

    proposal = actions.build(admin, "approve_purchase_request", {"query": req.number})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 2_000_000}, format="json")
    assert res.status_code == 200, res.data
    req.refresh_from_db()
    assert req.status == "approved"
    assert req.approved_at is not None
    assert req.approved_by_id == admin.id
    assert AuditEntry.objects.filter(
        module="purchasing", action="approve_request", entity_id=req.number
    ).count() == 1
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"

    # Single-use: a second confirm of the same card 409s and changes nothing more.
    again = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                   "typed_minor": 2_000_000}, format="json")
    assert again.status_code == 409
    req.refresh_from_db()
    assert req.status == "approved"


def test_approve_pr_over_approval_limit_surfaces_calm_apperror():
    """An actor whose role has a configured 'purchase_request' ceiling below the request's subtotal
    gets the underlying ApprovalLimitExceededError, flowing through ActionExecuteView's existing
    AppError path unchanged — this action needs no translation of its own."""
    from erp.identity.models import ApprovalLimit, RolePermission
    from erp.identity.rbac import DataScope

    manager = _with_role("approve_pr_capped", BRANCH_MANAGER)
    role = Group.objects.get(name=BRANCH_MANAGER)
    # A bare test role has no RolePermission rows, so scope_for defaults to OWN — grant view-all so
    # find_requests can see a request this actor didn't create (mirrors the bill/pay precedent).
    RolePermission.objects.update_or_create(
        role=role, code="purchasing.request.view", defaults={"scope": DataScope.ALL},
    )
    _seed_purchasing()
    req = _submitted_request(Supplier.objects.get(code="S-1"))  # subtotal 20,000.00 EGP
    ApprovalLimit.objects.update_or_create(
        role=role, document_type="purchase_request",
        defaults={"limit_minor": 10_000},  # 100.00 ceiling; this request is 20,000.00
    )
    _set_posting_enabled(True)

    proposal = actions.build(manager, "approve_purchase_request", {"query": req.number})
    conv = Conversation.objects.create(user=manager)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=manager)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 2_000_000}, format="json")
    assert res.status_code == 422, res.data
    req.refresh_from_db()
    assert req.status == "submitted"  # nothing approved
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "pending"  # unconsumed — the card stays usable


# --- issue stock entry (agent-posting FILE_07, pattern replication of FILE_02-06) -----------------

def _seed_issue_stock() -> tuple[Item, Warehouse]:
    item = Item.objects.create(sku="SKU-3", name="Green Gizmo")
    wh = Warehouse.objects.create(code="WH-C", name="Central")
    StockBalance.objects.create(item=item, warehouse=wh, quantity=Decimal("50"), value_minor=5000)
    return item, wh


def test_issue_stock_build_shows_estimated_value():
    admin = _admin()
    _seed_issue_stock()
    _set_posting_enabled(True)

    proposal = actions.build(admin, "issue_stock_entry",
                             {"item": "SKU-3", "quantity": "20", "warehouse": "WH-C"})
    assert proposal["action"] == "issue_stock_entry"
    # 5000 value_minor / 50 qty * 20 issued = 2000 estimated value.
    assert proposal["challenge"] == {"label": "20.00 EGP", "minor": 2000}
    from erp.inventory.domain.models import StockMovement

    assert StockMovement.objects.count() == 0  # building writes nothing


def test_issue_stock_over_on_hand_is_calm_error_no_card():
    admin = _admin()
    _seed_issue_stock()
    _set_posting_enabled(True)

    proposal = actions.build(admin, "issue_stock_entry",
                             {"item": "SKU-3", "quantity": "999", "warehouse": "WH-C"})
    assert "action" not in proposal
    assert "50" in proposal["error"]


def test_issue_stock_refused_when_posting_disabled():
    admin = _admin()
    _seed_issue_stock()
    _set_posting_enabled(False)

    proposal = actions.build(admin, "issue_stock_entry",
                             {"item": "SKU-3", "quantity": "20", "warehouse": "WH-C"})
    assert "action" not in proposal
    assert "Settings" in proposal["error"]


def test_issue_stock_refused_for_wrong_role():
    _seed_issue_stock()
    _set_posting_enabled(True)
    nobody = _nobody()

    proposal = actions.build(nobody, "issue_stock_entry",
                             {"item": "SKU-3", "quantity": "20", "warehouse": "WH-C"})
    assert "action" not in proposal
    assert "permission" in proposal["error"].lower()


@override_settings(ASSISTANT_ENABLED=True)
def test_issue_stock_confirm_reduces_balance_and_posts_gl_then_is_single_use():
    """The real action through the real confirm endpoint: right retype → stock on hand drops by the
    issued quantity, one StockMovement (type=ISSUE), one COGS/Inventory GL entry matching the
    ACTUAL posted value; a second confirm of the same card 409s and moves nothing more."""
    from erp.accounting.domain.models import JournalEntry
    from erp.inventory.domain.models import MovementType, StockMovement

    from erp.inventory.tests.factories import make_gl

    admin = _admin()
    item, wh = _seed_issue_stock()
    make_gl()  # GL accounts (1200 Inventory, 5000 COGS) + a period covering all of 2026
    _set_posting_enabled(True)

    proposal = actions.build(admin, "issue_stock_entry",
                             {"item": "SKU-3", "quantity": "20", "warehouse": "WH-C"})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 2000}, format="json")
    assert res.status_code == 200, res.data
    balance = StockBalance.objects.get(item=item, warehouse=wh)
    assert balance.quantity == Decimal("30")
    movement = StockMovement.objects.get()
    assert movement.type == MovementType.ISSUE
    assert movement.quantity == Decimal("20")
    entry = JournalEntry.objects.filter(reference="", memo__icontains="Issue").get()
    accounts = {ln.account.code for ln in entry.lines.all()}
    assert accounts == {"5000", "1200"}  # COGS debit, Inventory credit
    assert AuditEntry.objects.filter(
        module="inventory", action="issue_stock", entity_id=str(movement.id)
    ).count() == 1
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"

    # Single-use: a second confirm of the same card 409s and moves nothing more.
    again = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                   "typed_minor": 2000}, format="json")
    assert again.status_code == 409
    balance.refresh_from_db()
    assert balance.quantity == Decimal("30")
    assert StockMovement.objects.count() == 1


def test_create_account_and_execute():
    admin = _admin()
    _seed_accounting()

    proposal = actions.build(admin, "create_account",
                             {"name": "Marketing Expense", "type": "expense"})
    assert "error" not in proposal
    assert proposal["action"] == "create_account"
    assert Account.objects.filter(name="Marketing Expense").count() == 0  # building writes nothing

    result = actions.execute(admin, "create_account", proposal["payload"])
    account = Account.objects.get(name="Marketing Expense")
    assert account.type == "expense"
    assert result["links"][0]["value"] == account.code
    assert AuditEntry.objects.filter(module="accounting", action="create_account").exists()


def test_create_account_duplicate_name_is_a_risk_and_still_confirmable():
    admin = _admin()
    _seed_accounting()

    proposal = actions.build(admin, "create_account", {"name": "Cash", "type": "asset"})
    assert "error" not in proposal
    assert proposal["risks"], "a duplicate name should surface a risk line, not block silently"

    actions.execute(admin, "create_account", proposal["payload"])
    assert Account.objects.filter(name="Cash").count() == 2


def test_create_account_duplicate_code_is_an_error():
    admin = _admin()
    _seed_accounting()  # "1000" (Cash) already taken

    proposal = actions.build(admin, "create_account",
                             {"name": "Petty Cash", "type": "asset", "code": "1000"})
    assert "error" in proposal and "already in use" in proposal["error"]


def test_create_account_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_accounting()

    proposal = actions.build(nobody, "create_account", {"name": "Marketing", "type": "expense"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_account",
                        {"name": "Marketing", "type": "expense", "code": "", "parent_code": ""})
    assert Account.objects.filter(name="Marketing").count() == 0


# --- CRM actions (agent-actions FILE_05) -------------------------------------------------------

from erp.crm.domain.models import Activity, Opportunity


def _seed_crm():
    Customer.objects.create(code="C-1", name="Nile Traders")


def test_build_then_execute_creates_opportunity_draft():
    admin = _admin()
    _seed_crm()

    proposal = actions.build(admin, "create_opportunity",
                             {"customer": "Nile Traders", "name": "New Deal", "value": 50000})
    assert "error" not in proposal
    assert proposal["action"] == "create_opportunity"
    kinds = {r["type"] for r in proposal["records"]}
    assert kinds == {"customer"}
    assert Opportunity.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "create_opportunity", proposal["payload"])
    opp = Opportunity.objects.get()
    assert opp.customer_code == "C-1"
    assert opp.name == "New Deal"
    assert opp.stage == "qualifying"  # new opps start in qualifying
    assert result["links"][0]["value"] == str(opp.id)
    assert AuditEntry.objects.filter(module="crm", action="create_opportunity").exists()


def test_create_opportunity_unknown_customer_is_a_blocker():
    admin = _admin()
    _seed_crm()

    proposal = actions.build(admin, "create_opportunity",
                             {"customer": "Unknown Customer", "name": "Deal"})
    assert "blocker" in proposal


def test_create_opportunity_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_crm()

    proposal = actions.build(nobody, "create_opportunity",
                             {"customer": "Nile Traders", "name": "Deal"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "create_opportunity",
                        {"customer_code": "C-1", "name": "Deal", "amount_minor": 0,
                         "expected_close": None})
    assert Opportunity.objects.count() == 0


def test_advance_opportunity_stage_and_execute():
    admin = _admin()
    _seed_crm()
    opp = Opportunity.objects.create(number="OPP-2026-000001", name="Big Deal",
                                     customer_code="C-1", stage="qualifying")

    proposal = actions.build(admin, "advance_opportunity_stage",
                             {"query": opp.number, "stage": "proposal"})
    assert "error" not in proposal
    assert proposal["action"] == "advance_opportunity_stage"
    assert not proposal["risks"]  # advancing forward is no risk

    result = actions.execute(admin, "advance_opportunity_stage", proposal["payload"])
    opp.refresh_from_db()
    assert opp.stage == "proposal"
    assert result["links"][0]["value"] == str(opp.id)
    assert AuditEntry.objects.filter(module="crm", action="advance_stage").exists()


def test_advance_opportunity_backward_is_a_risk_and_still_confirmable():
    admin = _admin()
    _seed_crm()
    opp = Opportunity.objects.create(number="OPP-2026-000001", name="Big Deal",
                                     customer_code="C-1", stage="proposal")

    proposal = actions.build(admin, "advance_opportunity_stage",
                             {"query": opp.number, "stage": "qualifying"})
    assert "error" not in proposal
    assert proposal["risks"]  # moving backward is flagged as a risk

    actions.execute(admin, "advance_opportunity_stage", proposal["payload"])
    opp.refresh_from_db()
    assert opp.stage == "qualifying"


def test_advance_opportunity_unknown_query_is_a_blocker():
    admin = _admin()
    _seed_crm()

    proposal = actions.build(admin, "advance_opportunity_stage",
                             {"query": "OPP-9999-000000", "stage": "proposal"})
    assert "blocker" in proposal


def test_advance_opportunity_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_crm()
    opp = Opportunity.objects.create(number="OPP-2026-000001", name="Big Deal",
                                     customer_code="C-1", stage="qualifying")

    proposal = actions.build(nobody, "advance_opportunity_stage",
                             {"query": opp.number, "stage": "proposal"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "advance_opportunity_stage",
                        {"opportunity_number": opp.number, "stage": "proposal"})
    opp.refresh_from_db()
    assert opp.stage == "qualifying"


def test_log_activity_and_execute():
    admin = _admin()
    _seed_crm()
    opp = Opportunity.objects.create(number="OPP-2026-000001", name="Big Deal",
                                     customer_code="C-1", stage="qualifying")

    proposal = actions.build(admin, "log_activity",
                             {"query": opp.number, "note": "Discussed pricing",
                              "type": "call"})
    assert "error" not in proposal
    assert proposal["action"] == "log_activity"
    assert Activity.objects.count() == 0  # building writes nothing

    result = actions.execute(admin, "log_activity", proposal["payload"])
    activity = Activity.objects.get()
    assert activity.type == "call"
    assert activity.subject == "Discussed pricing"
    assert activity.related_type == "opportunity"
    assert activity.related_ref == opp.number
    assert result["links"][0]["value"] == opp.number
    assert AuditEntry.objects.filter(module="crm", action="log_activity").exists()


def test_log_activity_against_customer():
    admin = _admin()
    _seed_crm()

    proposal = actions.build(admin, "log_activity",
                             {"query": "Nile Traders", "note": "Renewal call",
                              "type": "call"})
    assert "error" not in proposal

    actions.execute(admin, "log_activity", proposal["payload"])
    activity = Activity.objects.get()
    assert activity.type == "call"
    assert activity.related_type == "customer"
    assert activity.related_ref == "C-1"


def test_log_activity_permission_refused_at_both_stages():
    nobody = _nobody()
    _seed_crm()
    opp = Opportunity.objects.create(number="OPP-2026-000001", name="Big Deal",
                                     customer_code="C-1", stage="qualifying")

    proposal = actions.build(nobody, "log_activity",
                             {"query": opp.number, "note": "A note"})
    assert "error" in proposal and "permission" in proposal["error"].lower()

    with pytest.raises(PermissionError):
        actions.execute(nobody, "log_activity",
                        {"related_type": "opportunity", "related_ref": opp.number,
                         "subject": "A note", "type": "note"})
    assert Activity.objects.count() == 0


# --- L0 action graph schema (os-foundations FILE_01) --------------------------------------------

def _toy_action(**overrides) -> actions.Action:
    fields = dict(name="toy_action", description="test only", args={},
                  build_proposal=lambda actor, **_: {}, execute=lambda actor, payload: {})
    fields.update(overrides)
    return actions.Action(**fields)


def test_validator_rejects_destructive_risk_without_confirm():
    with pytest.raises(AssertionError):
        actions._validate_action(_toy_action(risk="destructive", requires_confirm=False))


def test_validator_rejects_posting_effect_with_draft_risk():
    with pytest.raises(AssertionError):
        actions._validate_action(_toy_action(
            effects=(actions.Effect("journal_entry", "create", gl="posts"),), risk="draft"))


def test_validator_rejects_unknown_risk_and_unregistered_compensation():
    with pytest.raises(AssertionError):
        actions._validate_action(_toy_action(risk="explosive"))
    with pytest.raises(AssertionError):
        actions._validate_action(_toy_action(compensation="no_such_action"))


def test_every_action_passes_validation_and_archetypes_declare_semantics():
    for action in actions.ACTIONS.values():
        actions._validate_action(action)
    so = actions.ACTIONS["create_sales_order_draft"]
    assert so.effects[0].entity == "sales_order"
    assert so.requires == ("customer", "item", "warehouse")
    assert so.invariants == ("doc_totals", "period_open")
    assert actions.ACTIONS["create_journal_entry_draft"].effects[0].gl == "draft"
    assert actions.ACTIONS["create_stock_transfer_draft"].invariants == ("stock_non_negative",)
    assert actions.ACTIONS["create_customer"].idempotency == ("name",)


def test_catalog_text_carries_risk_class():
    text = actions.catalog_text()
    assert "[risk: draft]" in text
    for line in text.splitlines()[1:]:
        assert "[risk: " in line


# --- verifier wiring (os-foundations FILE_03) ----------------------------------------------------

from erp.assistant import verifier as verifier_module  # noqa: E402


@override_settings(ASSISTANT_ENABLED=True)
def test_confirm_runs_declared_invariants_and_reports_ok():
    admin = _admin()
    _seed_accounting()
    msg = _proposal_message(admin, _journal_decision(), action="create_journal_entry_draft")
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["verifier"]["ok"] is True
    assert set(body["verifier"]["packs"]) == {"journal_balanced", "period_open"}
    msg.refresh_from_db()
    assert msg.meta["proposal"]["verifier"]["ok"] is True


@override_settings(ASSISTANT_ENABLED=True)
def test_confirm_without_declared_invariants_carries_no_verifier_key():
    """Regression (Accept c): an invariant-less action confirms exactly as before."""
    admin = _admin()
    msg = _proposal_message(admin, {"query": "Acme Corp"}, action="create_customer")
    client = APIClient()
    client.force_authenticate(user=admin)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert res.status_code == 200
    assert "verifier" not in res.json()["data"]
    msg.refresh_from_db()
    assert "verifier" not in msg.meta["proposal"]


@override_settings(ASSISTANT_ENABLED=True)
def test_verifier_failure_rolls_back_write_and_leaves_proposal_pending(monkeypatch):
    admin = _admin()
    _seed_accounting()
    msg = _proposal_message(admin, _journal_decision(), action="create_journal_entry_draft")
    client = APIClient()
    client.force_authenticate(user=admin)

    def _forced_failure(scope):
        return verifier_module.Finding("journal_balanced", False, "forced failure for the test", {})
    monkeypatch.setitem(verifier_module.PACKS, "journal_balanced", _forced_failure)

    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm"}, format="json")
    assert res.status_code == 422
    assert JournalEntry.objects.count() == 0  # the atomic write was undone
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "pending"  # reusable, never stamped confirmed
    assert AuditEntry.objects.filter(module="assistant", action="verifier_failed").exists()


@override_settings(ASSISTANT_ENABLED=True)
def test_confirm_dedupes_repeat_of_same_action_across_two_cards():
    admin = _admin()
    _seed_sales()
    _seed_open_period()
    decision = _sales_decision()
    msg1 = _proposal_message(admin, decision)
    msg2 = _proposal_message(admin, decision)
    client = APIClient()
    client.force_authenticate(user=admin)

    first = client.post(EXEC_URL, {"message_id": msg1.id, "decision": "confirm"}, format="json")
    assert first.status_code == 200
    assert SalesOrder.objects.count() == 1

    second = client.post(EXEC_URL, {"message_id": msg2.id, "decision": "confirm"}, format="json")
    assert second.status_code == 200
    assert second.json()["data"]["deduplicated"] is True
    assert SalesOrder.objects.count() == 1  # the second card executed nothing
    assert AuditEntry.objects.filter(module="assistant", action="confirm_deduplicated").exists()
    msg2.refresh_from_db()
    assert msg2.meta["proposal"]["status"] == "confirmed"


# --- guard infrastructure: org toggle + typed retype-confirm (agent-posting-plan FILE_01) --------

def _with_role(username: str, role: str) -> User:
    Group.objects.get_or_create(name=role)
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.groups.add(Group.objects.get(name=role))
    return u


def _set_posting_enabled(value: bool) -> None:
    OrgPreferences.objects.update_or_create(pk=1, defaults={"assistant_posting_enabled": value})


def test_can_post_gates_on_toggle_and_role():
    manager = _with_role("post_mgr", BRANCH_MANAGER)

    _set_posting_enabled(False)
    assert actions._can_post(manager, BRANCH_MANAGER) is False  # toggle off, right role

    _set_posting_enabled(True)
    wrong_role = _with_role("post_wrong_role", ACCOUNTANT)
    assert actions._can_post(wrong_role, BRANCH_MANAGER) is False  # toggle on, wrong role

    assert actions._can_post(manager, BRANCH_MANAGER) is True  # toggle on, right role


def test_challenge_formats_label_and_carries_minor():
    # Money.format has no thousands grouping (erp/accounting/domain/money.py) — the label is plain.
    assert actions.challenge(4523000) == {"label": "45230.00 EGP", "minor": 4523000}


@override_settings(ASSISTANT_ENABLED=True)
def test_post_risk_action_guard_end_to_end(monkeypatch):
    """A monkeypatched toy risk="post" action (no real posting action exists yet — FILE_02+) proves
    the org toggle + typed retype-confirm through the real confirm endpoint, not just in isolation."""
    admin = _admin()
    calls: list[int] = []

    def _toy_build(actor, **_):
        return {"action": "toy_post", "summary": ["Toy post"], "records": [], "risks": [],
                "total": None, "affected": 0, "payload": {}, "challenge": actions.challenge(100000)}

    def _toy_execute(actor, payload):
        # Mirrors the Task C pattern every real risk="post" action's execute will use.
        if not actions._can_post(actor, BRANCH_MANAGER):
            raise PermissionError
        calls.append(1)
        return {"summary": "Posted.", "links": []}

    toy = actions.Action(
        name="toy_post", description="test only", args={},
        build_proposal=_toy_build, execute=_toy_execute,
        kind="post", risk="post",
    )
    monkeypatch.setitem(actions.ACTIONS, "toy_post", toy)

    proposal = actions.build(admin, "toy_post", {})
    assert proposal["challenge"] == {"label": "1000.00 EGP", "minor": 100000}
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    # Toggle off: the typed value is right, but the toy execute's own _can_post refuses — calm
    # 403, card stays pending, nothing runs.
    _set_posting_enabled(False)
    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 100000}, format="json")
    assert res.status_code == 403
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "pending"
    assert calls == []

    # Toggle on, wrong typed_minor: refused before execute() ever runs — never consumed.
    _set_posting_enabled(True)
    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 1}, format="json")
    assert res.status_code == 400
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "pending"
    assert calls == []

    # Toggle on, right typed_minor: executes for real, card flips to confirmed.
    res = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                 "typed_minor": 100000}, format="json")
    assert res.status_code == 200
    assert calls == [1]
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "confirmed"


# --- posting guard: edge cases beyond the end-to-end test above (FILE_01 Task F) ---------------

def test_posting_refusals_name_the_specific_gate_that_closed():
    """Task C mandates two DIFFERENT call shapes at build time so the message is accurate: a
    toggle-off refusal points at Settings, a role refusal does not (a user who cannot fix it must
    not be sent to a page they cannot use). Collapsing these into one message misinforms one case."""
    assert "System Admin" in actions._refused_posting_disabled()["error"]
    assert "Settings" in actions._refused_posting_disabled()["error"]
    assert "permission" in actions._refused()["error"]
    assert "System Admin" not in actions._refused()["error"]


def test_challenge_label_survives_the_frontend_parser():
    """The label is literally what the card tells the user to retype, so it must satisfy the
    frontend's ``parseToMinor`` regex ``^-?\d+(\.\d{1,2})?$`` — no thousands separators. A
    grouped label ("45,230.00") would parse to null and wedge Confirm permanently disabled."""
    assert "," not in actions.challenge(4523000)["label"]
    assert "," not in actions.challenge(123456789)["label"]


@override_settings(ASSISTANT_ENABLED=True)
@pytest.mark.parametrize("typed", [None, "100000", 100000.0, True])
def test_non_integer_or_missing_retype_fails_shut(monkeypatch, typed):
    """The confirm check is ``isinstance(typed_minor, int)`` equality. An absent value, the right
    number as a string, and a float all fail shut. ``True`` is included deliberately: Python's
    ``bool`` IS an ``int``, so a JSON ``true`` reaching a challenge whose minor is 1 would slip
    through the isinstance arm — this pins that the equality arm still rejects it."""
    admin = _admin()
    calls: list[int] = []

    def _toy_build(actor, **_):
        return {"action": "toy_post", "summary": ["Toy post"], "records": [], "risks": [],
                "total": None, "affected": 0, "payload": {}, "challenge": actions.challenge(100000)}

    def _toy_execute(actor, payload):
        calls.append(1)
        return {"summary": "Posted.", "links": []}

    monkeypatch.setitem(actions.ACTIONS, "toy_post", actions.Action(
        name="toy_post", description="test only", args={}, build_proposal=_toy_build,
        execute=_toy_execute, kind="post", risk="post"))
    _set_posting_enabled(True)

    proposal = actions.build(admin, "toy_post", {})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    body = {"message_id": msg.id, "decision": "confirm"}
    if typed is not None:
        body["typed_minor"] = typed
    res = client.post(EXEC_URL, body, format="json")

    assert res.status_code == 400
    assert calls == []
    msg.refresh_from_db()
    assert msg.meta["proposal"]["status"] == "pending"  # a typo never consumes the card


@override_settings(ASSISTANT_ENABLED=True)
def test_confirmed_post_card_cannot_be_replayed(monkeypatch):
    """Single-use must hold for posting too: a correct retype spends the card exactly once, so a
    replayed confirm 409s instead of posting a second time."""
    admin = _admin()
    calls: list[int] = []

    def _toy_build(actor, **_):
        return {"action": "toy_post", "summary": ["Toy post"], "records": [], "risks": [],
                "total": None, "affected": 0, "payload": {}, "challenge": actions.challenge(100000)}

    def _toy_execute(actor, payload):
        calls.append(1)
        return {"summary": "Posted.", "links": []}

    monkeypatch.setitem(actions.ACTIONS, "toy_post", actions.Action(
        name="toy_post", description="test only", args={}, build_proposal=_toy_build,
        execute=_toy_execute, kind="post", risk="post"))
    _set_posting_enabled(True)

    proposal = actions.build(admin, "toy_post", {})
    conv = Conversation.objects.create(user=admin)
    msg = Message.objects.create(conversation=conv, role=Message.Role.ASSISTANT, content="Ready.",
                                 meta={"proposal": {**proposal, "status": "pending"}})
    client = APIClient()
    client.force_authenticate(user=admin)

    ok = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                "typed_minor": 100000}, format="json")
    assert ok.status_code == 200
    again = client.post(EXEC_URL, {"message_id": msg.id, "decision": "confirm",
                                   "typed_minor": 100000}, format="json")
    assert again.status_code == 409
    assert calls == [1]  # the replay posted nothing
