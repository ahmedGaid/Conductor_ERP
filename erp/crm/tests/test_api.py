"""CRM DRF API — lead/opportunity/ticket endpoints, RBAC, auth."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_customer, make_item

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="crm_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_lead_convert_and_win_flow_via_api():
    make_customer()
    make_item()
    client = _admin_client()

    lead = client.post("/api/crm/leads", {"name": "Jane", "company": "Initech"}, format="json")
    assert lead.status_code == 201, lead.data
    lid = lead.data["data"]["id"]

    opp = client.post(
        f"/api/crm/leads/{lid}/convert",
        {"opportunity_name": "Initech deal", "customer_code": "CUST1"},
        format="json",
    )
    assert opp.status_code == 201, opp.data
    oid = opp.data["data"]["id"]

    # Add lines by creating a fresh opportunity with lines (convert makes an empty one).
    full = client.post(
        "/api/crm/opportunities",
        {"name": "With lines", "customer_code": "CUST1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_price": 150_00}]},
        format="json",
    )
    assert full.status_code == 201, full.data
    fid = full.data["data"]["id"]
    assert full.data["data"]["amount_minor"] == 1500_00

    won = client.post(f"/api/crm/opportunities/{fid}/win", {}, format="json")
    assert won.status_code == 200, won.data
    assert won.data["data"]["stage"] == "won"
    assert won.data["data"]["sales_order_number"].startswith("SO-")

    assert oid  # the converted opportunity exists too


def test_ticket_sla_flow_via_api():
    client = _admin_client()
    created = client.post(
        "/api/crm/tickets",
        {"subject": "Login broken", "priority": "urgent", "customer_code": "CUST1"},
        format="json",
    )
    assert created.status_code == 201, created.data
    tid = created.data["data"]["id"]
    assert created.data["data"]["sla_due_at"]

    assert client.post(f"/api/crm/tickets/{tid}/start").data["data"]["status"] == "in_progress"
    resolved = client.post(f"/api/crm/tickets/{tid}/resolve", {"resolution": "fixed"}, format="json")
    assert resolved.data["data"]["status"] == "resolved"
    assert resolved.data["data"]["is_breached"] is False


def test_crm_requires_role():
    plain = User.objects.create_user(username="nobody_crm", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/crm/leads").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/crm/leads").status_code == 401
