"""Universal ⌘K search endpoint — find-by-name, Arabic folding, and permission gating.

These are the invariants behind Charter R10 (keyboard-first, Arabic-tolerant search) and R2 (results
respect the modules a user can reach).
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="search_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _hits(resp):
    assert resp.status_code == 200, resp.data
    return resp.data["data"]


def test_finds_customer_by_name_with_route():
    client = _admin_client()
    Customer.objects.create(code="ACME", name="Acme Trading")
    hits = _hits(client.get("/api/core/search", {"q": "acme"}))
    match = [h for h in hits if h["type"] == "customer" and h["to"] == "/sales/customers/ACME"]
    assert match, hits
    assert match[0]["label"] == "Acme Trading"


def test_arabic_folding_matches_misspelled_query():
    client = _admin_client()
    # Stored with taa-marbuta + hamza; the user types the common bare forms (ه, ا).
    Customer.objects.create(code="C-AR", name="شركة الفاتورة")
    hits = _hits(client.get("/api/core/search", {"q": "شركه الفاتوره"}))
    assert any(h["to"] == "/sales/customers/C-AR" for h in hits), hits


def test_short_query_returns_empty():
    client = _admin_client()
    Customer.objects.create(code="ACME", name="Acme Trading")
    assert _hits(client.get("/api/core/search", {"q": "a"})) == []


def test_results_are_gated_by_accessible_modules():
    # An authenticated user with no roles/permissions can reach no module, so even though customers
    # exist, search leaks nothing (R2: context respects permission).
    Customer.objects.create(code="ACME", name="Acme Trading")
    user = User.objects.create_user(username="nobody", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    assert _hits(client.get("/api/core/search", {"q": "acme"})) == []


def test_requires_authentication():
    assert APIClient().get("/api/core/search", {"q": "acme"}).status_code in (401, 403)
