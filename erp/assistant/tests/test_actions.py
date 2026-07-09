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
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import Conversation, Message
from erp.assistant.services import actions, agent
from erp.audit.models import AuditEntry
from erp.identity.models import User
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

from erp.crm.domain.models import Opportunity, Activity


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
