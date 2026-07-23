"""Template catalog + create-from-template API — Task 6 of the non-technical workflow builder."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.workflow.models import Workflow, WorkflowTrigger

pytestmark = pytest.mark.django_db


def _client() -> APIClient:
    user = User.objects.create_user(username="wf_template_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_template_catalog_endpoint():
    resp = _client().get("/api/workflow/workflows/templates")
    assert resp.status_code == 200
    ids = {t["id"] for t in resp.json()["data"]}
    assert "approval_above_amount" in ids


def test_create_from_template_creates_workflow_and_trigger():
    resp = _client().post(
        "/api/workflow/workflows/templates/approval_above_amount",
        {"name": "PO approvals over 5000", "params": {"amount_minor": 500000, "approver_role": "finance_manager"}},
        format="json",
    )
    assert resp.status_code == 201
    wf = Workflow.objects.get(name="PO approvals over 5000")
    assert wf.nodes.count() == 4
    assert WorkflowTrigger.objects.filter(workflow=wf).exists()
