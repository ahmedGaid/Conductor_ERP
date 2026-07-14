"""Master-data adapters (FILE_05): customers, suppliers, items, contacts.

Only entities backed by a real module service create-path get an adapter this session — see
``erp/imports/adapters/__init__.py`` for why item_categories/warehouses/units/price_lists are
out of scope (recorded as a blocker in erp-status). None of the four adapters here have ``ref``
fields (no lookups are wired into their write-paths yet), so there is no Arabic-spelling-variant
lookup case to cover in this file.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.crm.domain.models import Lead
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import registry
from erp.inventory.domain.models import Item
from erp.purchasing.domain.models import Supplier
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def _manager(username: str = "mgr") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


def _plain_user(username: str = "clerk") -> User:
    return User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")


# --- customers --------------------------------------------------------------------------------

def test_customer_write_creates_real_customer():
    actor = _manager("mgr_c")
    adapter = registry.get("customers")
    adapter.write(actor, {"name": "Acme Trading", "credit_limit_minor": 500_00})
    customer = Customer.objects.get(name="Acme Trading")
    assert customer.credit_limit_minor == 500_00
    assert customer.created_by_id == actor.id


def test_customer_exists_hits_on_normalized_name():
    actor = _manager("mgr_c2")
    adapter = registry.get("customers")
    adapter.write(actor, {"name": "Nile Foods"})
    found = adapter.exists(actor, {"name": "  nile foods  ".strip()})
    assert found is not None
    assert found.name == "Nile Foods"
    assert adapter.exists(actor, {"name": "No Such Customer"}) is None


def test_customer_write_blocked_for_unpermitted_actor():
    actor = _plain_user("clerk_c")
    adapter = registry.get("customers")
    with pytest.raises(PermissionError):
        adapter.write(actor, {"name": "Should Not Exist"})
    assert not Customer.objects.filter(name="Should Not Exist").exists()


# --- suppliers ---------------------------------------------------------------------------------

def test_supplier_write_creates_real_supplier():
    actor = _manager("mgr_s")
    adapter = registry.get("suppliers")
    adapter.write(actor, {"name": "Delta Supplies"})
    assert Supplier.objects.filter(name="Delta Supplies").exists()


def test_supplier_exists_hits_on_normalized_name():
    actor = _manager("mgr_s2")
    adapter = registry.get("suppliers")
    adapter.write(actor, {"name": "Cairo Metals"})
    found = adapter.exists(actor, {"name": "cairo metals"})
    assert found is not None and found.name == "Cairo Metals"


def test_supplier_write_blocked_for_unpermitted_actor():
    actor = _plain_user("clerk_s")
    adapter = registry.get("suppliers")
    with pytest.raises(PermissionError):
        adapter.write(actor, {"name": "Should Not Exist"})


# --- items -------------------------------------------------------------------------------------

def test_item_write_creates_real_item():
    actor = _manager("mgr_i")
    adapter = registry.get("items")
    adapter.write(actor, {"sku": "WIDGET-1", "name": "Widget", "uom": "قطعة"})
    item = Item.objects.get(sku="WIDGET-1")
    assert item.name == "Widget"
    assert item.uom == "قطعة"


def test_item_write_uses_default_uom_when_omitted():
    actor = _manager("mgr_i2")
    adapter = registry.get("items")
    adapter.write(actor, {"sku": "WIDGET-2", "name": "Widget Two"})
    assert Item.objects.get(sku="WIDGET-2").uom == "unit"


def test_item_exists_hits_on_sku():
    actor = _manager("mgr_i3")
    adapter = registry.get("items")
    adapter.write(actor, {"sku": "WIDGET-3", "name": "Widget Three"})
    assert adapter.exists(actor, {"sku": "WIDGET-3"}) is not None
    assert adapter.exists(actor, {"sku": "NOPE"}) is None


def test_item_write_blocked_for_unpermitted_actor():
    actor = _plain_user("clerk_i")
    adapter = registry.get("items")
    with pytest.raises(PermissionError):
        adapter.write(actor, {"sku": "SHOULD-NOT-EXIST", "name": "x"})
    assert not Item.objects.filter(sku="SHOULD-NOT-EXIST").exists()


# --- contacts (crm.Lead) ------------------------------------------------------------------------

def test_contact_write_creates_real_lead():
    actor = _manager("mgr_ct")
    adapter = registry.get("contacts")
    lead = adapter.write(actor, {"name": "Sara Adel", "email": "sara@example.com", "phone": "0100"})
    assert isinstance(lead, Lead)
    stored = Lead.objects.get(email="sara@example.com")
    assert stored.name == "Sara Adel"
    assert stored.branch_id == getattr(actor, "branch_id", None)


def test_contact_write_uses_default_source_when_omitted():
    actor = _manager("mgr_ct2")
    adapter = registry.get("contacts")
    adapter.write(actor, {"name": "Omar Said"})
    assert Lead.objects.get(name="Omar Said").source == "other"


def test_contact_exists_hits_on_email_then_name():
    actor = _manager("mgr_ct3")
    adapter = registry.get("contacts")
    adapter.write(actor, {"name": "Mona Fathy", "email": "mona@example.com"})
    assert adapter.exists(actor, {"name": "anything", "email": "mona@example.com"}) is not None
    assert adapter.exists(actor, {"name": "Mona Fathy"}) is not None
    assert adapter.exists(actor, {"name": "Nobody Here"}) is None


def test_contact_write_blocked_for_unpermitted_actor():
    actor = _plain_user("clerk_ct")
    adapter = registry.get("contacts")
    with pytest.raises(PermissionError):
        adapter.write(actor, {"name": "Should Not Exist"})
    assert not Lead.objects.filter(name="Should Not Exist").exists()


# --- registration --------------------------------------------------------------------------------

def test_all_four_master_adapters_registered():
    for entity in ("customers", "suppliers", "items", "contacts"):
        assert entity in registry.entities()


def test_no_orm_creates_in_adapters_module():
    """Guard: adapters call module services, never ``Model.objects.create`` directly."""
    import pathlib

    adapters_dir = pathlib.Path(__file__).resolve().parents[1] / "adapters"
    for py_file in adapters_dir.glob("*.py"):
        if py_file.name in {"__init__.py", "_rbac.py"}:
            continue
        text = py_file.read_text(encoding="utf-8")
        assert "objects.create" not in text, f"{py_file} writes via ORM directly"
