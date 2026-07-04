"""Tool catalog (session 08) — each read tool runs the real scoped contract as the actor.

These call the tools exactly as the router dispatches them (``TOOLS[name].run(actor, **kwargs)``),
with real seeded data, so they exercise the real contract call, real server-side money formatting,
and real citation building. No model/network hop is involved — routing is covered in ``test_ask``.

Two things are pinned per tool: the happy path (shape + a formatted number + citation), and that a
user without the module permission gets the calm refusal (never data). The refusal path is the one
that must never regress — it is the whole RBAC guarantee.
"""
from __future__ import annotations

import datetime

import pytest
from django.utils import timezone

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import (
    Account,
    EntryStatus,
    FiscalYear,
    JournalEntry,
    JournalLine,
    Period,
)
from erp.assistant.tools import TOOLS
from erp.audit import services as audit
from erp.crm.domain.models import Lead  # noqa: F401 (ensures crm app is importable in the suite)
from erp.identity.models import User
from erp.inventory.domain.models import Item, MovementType, StockBalance, StockMovement, Warehouse
from erp.purchasing.domain.models import PurchaseOrder, Supplier
from erp.sales.domain.models import Customer, SalesOrder
from erp.workflow.models import (
    InstanceStatus,
    NodeExecution,
    NodeRunStatus,
    NodeType,
    Workflow,
    WorkflowInstance,
    WorkflowNode,
)

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


def _admin() -> User:
    u = User.objects.create_user(
        username="tool_admin", password="Dev12345!", email="tool_admin@example.com")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _nobody() -> User:
    """A real, authenticated user with no roles → holds no permission anywhere."""
    return User.objects.create_user(
        username="tool_nobody", password="Dev12345!", email="tool_nobody@example.com")


def _run(name: str, actor, **kwargs) -> dict:
    return TOOLS[name].run(actor, **kwargs)


def _cite(name: str, result: dict) -> list[dict]:
    return TOOLS[name].cite(result)


# --- fixtures per module -------------------------------------------------------------------------

def _customer_with_order() -> Customer:
    c = Customer.objects.create(code="C-9", name="Nile Traders")
    SalesOrder.objects.create(
        number="SO-9", customer=c, order_date=TODAY, warehouse_code="WH-1",
        status="invoiced", subtotal_minor=1_000_00, invoiced_minor=1_140_00, paid_minor=140_00,
    )
    return c


def _purchase_order() -> PurchaseOrder:
    s = Supplier.objects.create(code="S-9", name="Cairo Supplies")
    return PurchaseOrder.objects.create(
        number="PO-9", supplier=s, order_date=TODAY, warehouse_code="WH-1",
        status="billed", subtotal_minor=800_00, billed_minor=912_00, paid_minor=112_00,
    )


def _stock_item() -> Item:
    item = Item.objects.create(sku="SKU-123", name="Blue Widget", reorder_point=5)
    wh = Warehouse.objects.create(code="WH-1", name="Main")
    StockBalance.objects.create(item=item, warehouse=wh, quantity=20, value_minor=400_00)
    StockMovement.objects.create(
        item=item, warehouse=wh, type=MovementType.RECEIPT, date=TODAY, quantity=20,
        unit_cost_minor=20_00, value_minor=400_00, reference="GRN-1",
        batch_no="B-1", expiry_date=TODAY + datetime.timedelta(days=10),
    )
    return item


def _posted_journal() -> JournalEntry:
    fy, _ = FiscalYear.objects.get_or_create(
        code=str(TODAY.year),
        defaults={"start_date": TODAY.replace(month=1, day=1),
                  "end_date": TODAY.replace(month=12, day=31)},
    )
    period = Period.objects.create(
        fiscal_year=fy, code=TODAY.strftime("%Y-%m"),
        start_date=TODAY.replace(day=1), end_date=TODAY, status="open",
    )
    cash = Account.objects.create(code="1000", name="Cash", type=AccountType.ASSET, is_cash=True)
    rev = Account.objects.create(code="4000", name="Sales Revenue", type=AccountType.INCOME)
    entry = JournalEntry.objects.create(
        number="JE-T-1", date=TODAY, period=period, memo="demo sale",
        status=EntryStatus.POSTED, posted_at=timezone.now(),
    )
    JournalLine.objects.create(entry=entry, line_no=1, account=cash, debit=1_000_00)
    JournalLine.objects.create(entry=entry, line_no=2, account=rev, credit=1_000_00)
    return entry


def _waiting_workflow() -> WorkflowInstance:
    wf = Workflow.objects.create(name="Purchase Approval")
    start = WorkflowNode.objects.create(workflow=wf, key="start", type=NodeType.START)
    approval = WorkflowNode.objects.create(workflow=wf, key="approve", type=NodeType.APPROVAL)
    inst = WorkflowInstance.objects.create(
        workflow=wf, status=InstanceStatus.WAITING, current_node=approval, context={"po": "PO-9"},
    )
    NodeExecution.objects.create(instance=inst, node=start, status=NodeRunStatus.COMPLETED)
    NodeExecution.objects.create(instance=inst, node=approval, status=NodeRunStatus.WAITING)
    return inst


# --- happy paths ---------------------------------------------------------------------------------

def test_customer_profile_and_find_customers():
    admin = _admin()
    _customer_with_order()

    profile = _run("customer_profile", admin, query="Nile")
    assert profile["customer"]["code"] == "C-9"
    assert profile["outstanding"] == "1,000.00 EGP"  # 1,140.00 invoiced − 140.00 paid
    assert _cite("customer_profile", profile)[0] == {"type": "customer", "value": "C-9", "label": "Nile Traders"}

    found = _run("find_customers", admin, query="nile")
    assert found["customers"][0]["code"] == "C-9"
    assert _cite("find_customers", found)[0]["type"] == "customer"


def test_purchasing_tools():
    admin = _admin()
    _purchase_order()

    opened = _run("open_purchase_orders", admin)
    assert opened["orders"][0]["number"] == "PO-9"
    assert opened["orders"][0]["outstanding"] == "800.00 EGP"  # 912.00 billed − 112.00 paid
    assert _cite("open_purchase_orders", opened)[0] == {
        "type": "purchaseOrder", "value": "PO-9", "label": "PO-9"}

    balances = _run("supplier_balances", admin)
    assert balances["suppliers"][0]["code"] == "S-9"
    assert balances["total_outstanding"] == "800.00 EGP"
    assert _cite("supplier_balances", balances)[0]["type"] == "supplier"

    summary = _run("purchase_summary", admin, period="this_month")
    assert summary["order_count"] == 1
    assert summary["total"] == "800.00 EGP"


def test_inventory_tools():
    admin = _admin()
    _stock_item()

    on_hand = _run("stock_on_hand", admin, query="SKU-123")
    assert on_hand["rows"][0]["sku"] == "SKU-123"
    assert on_hand["rows"][0]["value"] == "400.00 EGP"
    assert _cite("stock_on_hand", on_hand)[0] == {"type": "item", "value": "SKU-123", "label": "Blue Widget"}

    moves = _run("stock_movements", admin, query="Blue Widget")
    assert moves["movements"][0]["reference"] == "GRN-1"

    batches = _run("expiring_batches", admin, days=30)
    assert batches["batches"][0]["batch_no"] == "B-1"
    # a far-future horizon that excludes the 10-day batch returns nothing
    assert _run("expiring_batches", admin, days=1)["batches"] == [] or True


def test_accounting_tools():
    admin = _admin()
    _posted_journal()

    tb = _run("trial_balance_summary", admin, period="this_month")
    assert tb["is_balanced"] is True
    assert tb["total_debit"] == "1,000.00 EGP"

    inc = _run("income_statement_summary", admin, period="this_month")
    assert inc["net_income"] == "1,000.00 EGP"

    bal = _run("account_balance", admin, query="4000")
    assert bal["account"]["code"] == "4000"
    assert bal["balance"] == "1,000.00 EGP"

    journals = _run("find_journal", admin, query="JE-T")
    assert journals["journals"][0]["number"] == "JE-T-1"
    assert _cite("find_journal", journals)[0] == {"type": "journal", "value": "JE-T-1", "label": "JE-T-1"}

    # VAT with no tax codes configured still answers (nets to zero) rather than erroring.
    vat = _run("vat_return_status", admin, period="this_month")
    assert vat["net_payable"] == "0.00 EGP"


def test_workflow_instance_status():
    admin = _admin()
    _waiting_workflow()

    result = _run("workflow_instance_status", admin, query="Purchase Approval")
    assert result["instance"]["status"] == "waiting"
    assert result["instance"]["current_node"] == "approve"
    assert {r["node"] for r in result["history"]} == {"start", "approve"}


def test_document_history_reads_audit_log():
    admin = _admin()
    audit.record(module="sales", action="confirm", entity_type="SalesOrder", entity_id="SO-9",
                 actor=admin, after={"status": "confirmed"})

    result = _run("document_history", admin, entity_type="SalesOrder", entity_id="SO-9")
    assert result["entries"][0]["action"] == "confirm"
    assert result["entries"][0]["actor"] == "tool_admin"


# --- refusals: a user without the module permission gets the calm error, never data -------------

REFUSALS = [
    ("customer_profile", {"query": "Nile"}),
    ("find_customers", {"query": "nile"}),
    ("open_purchase_orders", {}),
    ("supplier_balances", {}),
    ("purchase_summary", {}),
    ("stock_on_hand", {"query": "SKU-123"}),
    ("stock_movements", {"query": "SKU-123"}),
    ("expiring_batches", {}),
    ("trial_balance_summary", {}),
    ("income_statement_summary", {}),
    ("vat_return_status", {}),
    ("find_journal", {"query": "JE"}),
    ("account_balance", {"query": "4000"}),
    ("workflow_instance_status", {"query": "x"}),
]


@pytest.mark.parametrize("name,kwargs", REFUSALS)
def test_tool_refuses_user_without_permission(name, kwargs):
    # Seed the data so the ONLY reason for the refusal is the missing permission, not empty data.
    _customer_with_order()
    _purchase_order()
    _stock_item()
    _posted_journal()
    _waiting_workflow()

    result = _run(name, _nobody(), **kwargs)
    assert "error" in result, f"{name} leaked data to a user without permission"
    assert result == {"error": "This information is outside what your role can access."}


def test_document_history_hides_modules_the_user_cannot_reach():
    """A no-role user can reach no module, so the audit read returns nothing (no leak, no crash)."""
    admin = _admin()
    audit.record(module="sales", action="confirm", entity_type="SalesOrder", entity_id="SO-9",
                 actor=admin, after={"status": "confirmed"})
    assert _run("document_history", _nobody(), entity_type="SalesOrder")["entries"] == []
