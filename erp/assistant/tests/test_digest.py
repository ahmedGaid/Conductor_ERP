"""Ambient AI morning digest (session 11) — composed from the same tool runners the assistant
answers questions with, so RBAC/data-scope hold automatically and no new data access is added.

Pins: silence is the default (no section => no send), a user without a module's permission never
sees that module's section even when the data exists, and the digest follows the recipient's own
language preference.
"""
from __future__ import annotations

import datetime

import pytest
from django.contrib.auth.models import Group

from erp.assistant.services import digest as digest_mod
from erp.identity.models import RolePermission, User, UserPreferences
from erp.inventory.domain.models import Item, MovementType, StockBalance, StockMovement, Warehouse
from erp.purchasing.domain.models import PurchaseOrder, Supplier
from erp.sales.domain.models import Customer, SalesOrder

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()

ALL_MODULE_CODES = ("sales.order.view", "inventory.item.view", "purchasing.order.view")


def _user(username, *, lang="en", frequency="daily", email=None) -> User:
    u = User.objects.create_user(
        username=username, password="Dev12345!", email=email if email is not None else f"{username}@example.com"
    )
    UserPreferences.objects.create(user=u, preferred_language=lang, digest_frequency=frequency)
    return u


def _grant(user: User, *codes: str) -> None:
    g = Group.objects.create(name=f"grp-{user.username}")
    for code in codes:
        RolePermission.objects.create(role=g, code=code, scope="all")
    user.groups.add(g)


def _overdue_customer(code="C-1") -> Customer:
    c = Customer.objects.create(code=code, name="Cairo Traders")
    SalesOrder.objects.create(
        number=f"SO-{code}", customer=c, order_date=TODAY, warehouse_code="WH-1",
        status="invoiced", subtotal_minor=1_000_00, invoiced_minor=1_140_00, paid_minor=140_00,
    )
    return c


def _low_stock_item() -> Item:
    item = Item.objects.create(sku="SKU-L1", name="Low Widget", reorder_point=5)
    wh, _ = Warehouse.objects.get_or_create(code="WH-1", defaults={"name": "Main"})
    StockBalance.objects.create(item=item, warehouse=wh, quantity=2, value_minor=40_00)
    return item


def _expiring_batch() -> Item:
    item = Item.objects.create(sku="SKU-B1", name="Batch Widget", reorder_point=5)
    wh, _ = Warehouse.objects.get_or_create(code="WH-1", defaults={"name": "Main"})
    StockMovement.objects.create(
        item=item, warehouse=wh, type=MovementType.RECEIPT, date=TODAY, quantity=10,
        unit_cost_minor=10_00, value_minor=100_00, reference="GRN-1",
        batch_no="B-EXP", expiry_date=TODAY + datetime.timedelta(days=3),
    )
    return item


def _stuck_purchase_order() -> PurchaseOrder:
    s = Supplier.objects.create(code="S-1", name="Delta Supplies")
    return PurchaseOrder.objects.create(
        number="PO-STUCK", supplier=s, order_date=TODAY - datetime.timedelta(days=20),
        warehouse_code="WH-1", status="confirmed", subtotal_minor=500_00, billed_minor=500_00, paid_minor=0,
    )


# --- build_digest ---------------------------------------------------------------------------------

def test_digest_skips_empty_sections():
    user = _user("digest_partial")
    _grant(user, *ALL_MODULE_CODES)
    _overdue_customer()

    result = digest_mod.build_digest(user)

    assert result is not None
    assert "Overdue receivables" in result["body"]
    assert "Low stock" not in result["body"]
    assert "Batches expiring" not in result["body"]
    assert "Purchase orders open" not in result["body"]


def test_digest_none_when_all_quiet():
    user = _user("digest_quiet")
    _grant(user, *ALL_MODULE_CODES)

    assert digest_mod.build_digest(user) is None


def test_digest_respects_module_access():
    user = _user("digest_scoped")
    _grant(user, "sales.order.view", "purchasing.order.view")  # no inventory.item.view
    _overdue_customer()
    _low_stock_item()
    _expiring_batch()
    _stuck_purchase_order()

    result = digest_mod.build_digest(user)

    assert result is not None
    assert "Overdue receivables" in result["body"]
    assert "Purchase orders open" in result["body"]
    assert "Low stock" not in result["body"]
    assert "Batches expiring" not in result["body"]


def test_digest_language_follows_user_pref():
    user = _user("digest_ar", lang="ar")
    _grant(user, "sales.order.view")
    _overdue_customer()

    result = digest_mod.build_digest(user)

    assert result is not None
    assert result["subject"] == "ملخصك الصباحي"
    assert "مستحقات متأخرة" in result["body"]


# --- send_digests ----------------------------------------------------------------------------------

def test_send_digests_dispatches_per_user(monkeypatch):
    with_email = _user("digest_send_1", email="digest1@example.com")
    _grant(with_email, "sales.order.view")
    _overdue_customer("C-2")

    no_email = _user("digest_send_2", email="")
    _grant(no_email, "inventory.item.view")
    _low_stock_item()

    calls: list[dict] = []

    def _fake_dispatch(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(digest_mod, "dispatch", _fake_dispatch)

    sent = digest_mod.send_digests()

    assert sent == 2
    assert len(calls) == 3  # inapp+email for digest_send_1, inapp only for digest_send_2
    channels = sorted(c["channel"] for c in calls)
    assert channels == ["email", "inapp", "inapp"]


def test_send_digests_skips_opted_out_and_quiet_users(monkeypatch):
    off_user = _user("digest_off", frequency="off")
    _grant(off_user, "sales.order.view")
    _overdue_customer("C-3")

    _user("digest_quiet2")  # daily, but holds no permission -> every section gates off regardless

    calls: list[dict] = []
    monkeypatch.setattr(digest_mod, "dispatch", lambda **kw: calls.append(kw))

    sent = digest_mod.send_digests()

    assert sent == 0
    assert calls == []
