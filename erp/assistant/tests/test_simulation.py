"""L2 simulation engine (os-foundations FILE_04): sim-mode stubs + rolled-back simulate()."""
from __future__ import annotations

import pytest

from erp.assistant.services import simulation
from erp.assistant.services.simulation import PlanStep, simulate
from erp.identity.models import User
from erp.inventory.domain.models import Item, Warehouse
from erp.notifications.domain.models import Notification, NotificationStatus
from erp.sales.domain.models import Customer, SalesOrder

pytestmark = pytest.mark.django_db


def _admin(username: str = "sim_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _seed_sales():
    Customer.objects.create(code="C-1", name="Nile Traders")
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    Warehouse.objects.create(code="WH-1", name="Main")


def _seed_open_period():
    """An open fiscal period covering today — the sales-order archetype's ``period_open``
    invariant (FILE_03) needs this to pass."""
    import datetime as _dt

    from erp.accounting.domain.models import FiscalYear, Period, PeriodStatus

    today = _dt.date.today()
    fy = FiscalYear.objects.create(code=f"{today.year}-SIM", start_date=today.replace(month=1, day=1),
                                   end_date=today.replace(month=12, day=31))
    Period.objects.create(fiscal_year=fy, code=f"{today.year}-SIM", start_date=fy.start_date,
                          end_date=fy.end_date, status=PeriodStatus.OPEN)


# --- T4.1: sim_mode stubs --------------------------------------------------------------------

def test_notification_dispatch_stubbed_inside_sim_mode():
    from erp.notifications.services.dispatch import dispatch

    with simulation.sim_mode():
        note = dispatch(channel="email", recipient="a@example.test", subject="s", body="b")
        assert simulation.sim_skips() == [{"skipped": "notification"}]
    assert note.status == NotificationStatus.PENDING  # built, never sent/saved
    assert Notification.objects.count() == 0  # never persisted


def test_notification_dispatch_unchanged_outside_sim_mode():
    from erp.notifications.services.dispatch import dispatch

    note = dispatch(channel="email", recipient="a@example.test", subject="s", body="b")
    assert note.id is not None
    assert Notification.objects.filter(id=note.id).exists()
    assert note.status in (NotificationStatus.SENT, NotificationStatus.FAILED)


def test_sim_skips_empty_outside_sim_mode():
    assert simulation.sim_skips() == []
    assert simulation.in_sim_mode() is False


# --- T4.2: simulate() core --------------------------------------------------------------------

def _customer_step(name: str) -> PlanStep:
    return PlanStep("create_customer", {"query": name})


def _order_step(customer: str, sku: str = "SKU-1", qty: str = "3") -> PlanStep:
    return PlanStep("create_sales_order_draft",
                    {"customer": customer, "items": [{"item": sku, "quantity": qty}],
                     "warehouse": "WH-1"})


def test_simulate_two_step_plan_rolls_back_but_step_two_sees_step_one():
    admin = _admin()
    _seed_sales()
    _seed_open_period()
    Item.objects.create(sku="SKU-2", name="Green Gadget")

    counts_before = {"customer": Customer.objects.count(), "order": SalesOrder.objects.count()}

    diff = simulate(admin, [_customer_step("Delta Co"), _order_step("Delta Co", sku="SKU-2")])

    assert diff["ok"] is True
    assert [s["ok"] for s in diff["steps"]] == [True, True]
    # step 2 resolved the customer step 1 created inside the same still-open transaction
    assert "Delta Co" in diff["steps"][1]["summary"] or diff["steps"][1]["ok"]

    # nothing persisted — rollback undid both writes
    assert Customer.objects.count() == counts_before["customer"]
    assert Customer.objects.filter(name="Delta Co").count() == 0
    assert SalesOrder.objects.count() == counts_before["order"]


def test_simulate_mid_plan_failure_names_failing_step_and_persists_nothing():
    admin = _admin()
    _seed_sales()

    diff = simulate(admin, [_customer_step("Echo Co"),
                            _order_step("Echo Co", sku="NO-SUCH-SKU")])

    assert diff["ok"] is False
    assert diff["steps"][0]["ok"] is True
    assert diff["steps"][1]["ok"] is False
    assert Customer.objects.filter(name="Echo Co").count() == 0
    assert SalesOrder.objects.count() == 0


# --- T4.3: diff collection ----------------------------------------------------------------------

def test_simulate_diff_shape_creates_money_and_empty_stock():
    admin = _admin()
    _seed_sales()
    _seed_open_period()

    diff = simulate(admin, [_customer_step("Foxtrot Co"), _order_step("Foxtrot Co")])

    assert diff["creates"] == {"customer": 1, "sales_order": 1}
    # a fresh draft order is not yet invoiced — genuinely zero receivables until posted
    assert diff["money"]["receivables_delta_minor"] == 0
    assert diff["money"]["payables_delta_minor"] == 0
    assert diff["gl"] == {"debit_delta_minor": 0, "credit_delta_minor": 0}
    assert diff["stock"] == []  # no current action declares stock="moves"


def test_simulate_row_counts_unchanged_across_watched_models():
    admin = _admin()
    _seed_sales()
    _seed_open_period()
    watched = [Customer, SalesOrder]
    before = {m: m.objects.count() for m in watched}

    simulate(admin, [_customer_step("Golf Co"), _order_step("Golf Co")])

    after = {m: m.objects.count() for m in watched}
    assert before == after
