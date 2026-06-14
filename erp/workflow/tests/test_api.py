"""Stage 4 — workflow DRF API tests.

Proves the canvas round-trip (save a graph, reload, get an identical structure), instance
lifecycle through the engine (start -> waiting -> approve/reject), node-level execution logs in the
viewer payload, and dashboard metrics computed from real data.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _client() -> APIClient:
    user = User.objects.create_user(username="wf_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# A small approval workflow: start -> approve(human) -> condition -> end_ok / end_no.
APPROVAL_GRAPH = {
    "name": "Purchase Approval",
    "nodes": [
        {"key": "start", "type": "start", "config": {}, "position": {"x": 0, "y": 0}},
        {"key": "approve", "type": "approval", "config": {}, "position": {"x": 200, "y": 0}},
        {"key": "gate", "type": "condition", "config": {}, "position": {"x": 400, "y": 0}},
        {"key": "end_ok", "type": "end", "config": {}, "position": {"x": 600, "y": -80}},
        {"key": "end_no", "type": "end", "config": {}, "position": {"x": 600, "y": 80}},
    ],
    "edges": [
        {"source": "start", "target": "approve", "condition": None, "ordering": 0},
        {"source": "approve", "target": "gate", "condition": None, "ordering": 0},
        {
            "source": "gate",
            "target": "end_ok",
            "condition": {"var": "approve.approved"},
            "ordering": 0,
        },
        {"source": "gate", "target": "end_no", "condition": None, "ordering": 1},
    ],
}


def _create(client) -> dict:
    res = client.post("/api/workflow/workflows", APPROVAL_GRAPH, format="json")
    assert res.status_code == 201, res.data
    return res.data["data"]


def test_save_graph_round_trips():
    client = _client()
    created = _create(client)
    wf_id = created["id"]

    reloaded = client.get(f"/api/workflow/workflows/{wf_id}").data["data"]

    def norm(graph):
        nodes = sorted(
            ((n["key"], n["type"], n["config"], n["position"]) for n in graph["nodes"])
        )
        edges = sorted(
            ((e["source"], e["target"], e["ordering"], _key(e["condition"])) for e in graph["edges"])
        )
        return nodes, edges

    def _key(cond):
        import json

        return json.dumps(cond, sort_keys=True)

    assert norm(created) == norm(reloaded)
    # The structure we sent survived the round-trip.
    sent = norm({"nodes": APPROVAL_GRAPH["nodes"], "edges": APPROVAL_GRAPH["edges"]})
    assert sent == norm(reloaded)


def test_update_graph_bumps_version_and_upserts():
    client = _client()
    created = _create(client)
    wf_id = created["id"]
    assert created["version"] == 1

    edited = {**APPROVAL_GRAPH, "name": "Purchase Approval v2"}
    res = client.put(f"/api/workflow/workflows/{wf_id}", edited, format="json")
    assert res.status_code == 200, res.data
    assert res.data["data"]["version"] == 2
    assert res.data["data"]["name"] == "Purchase Approval v2"


def test_reject_invalid_graph_two_start_nodes():
    client = _client()
    bad = {
        "name": "bad",
        "nodes": [
            {"key": "s1", "type": "start"},
            {"key": "s2", "type": "start"},
            {"key": "e", "type": "end"},
        ],
        "edges": [{"source": "s1", "target": "e", "ordering": 0}],
    }
    res = client.post("/api/workflow/workflows", bad, format="json")
    assert res.status_code == 400


def test_instance_lifecycle_approve_shows_node_logs():
    client = _client()
    wf_id = _create(client)["id"]

    # Start: should pause at the approval node.
    start = client.post(f"/api/workflow/workflows/{wf_id}/start", {"payload": {}}, format="json")
    assert start.status_code == 201, start.data
    inst = start.data["data"]
    assert inst["status"] == "waiting"
    assert inst["current_node"] == "approve"
    instance_id = inst["id"]

    # Detail carries the node-level timeline with logs (execution viewer payload).
    detail = client.get(f"/api/workflow/instances/{instance_id}").data["data"]
    assert any(run["node_key"] == "approve" for run in detail["node_runs"])
    assert any(run["logs"] for run in detail["node_runs"]), "expected node-level logs"

    # Approve -> condition picks the approved branch -> completes.
    res = client.post(
        f"/api/workflow/instances/{instance_id}/decision", {"decision": "approve"}, format="json"
    )
    assert res.status_code == 200, res.data
    final = res.data["data"]
    assert final["status"] == "completed"
    keys = [run["node_key"] for run in final["node_runs"]]
    assert "end_ok" in keys and "end_no" not in keys


def test_instance_lifecycle_reject_takes_fallback_branch():
    client = _client()
    wf_id = _create(client)["id"]
    instance_id = client.post(
        f"/api/workflow/workflows/{wf_id}/start", {"payload": {}}, format="json"
    ).data["data"]["id"]

    final = client.post(
        f"/api/workflow/instances/{instance_id}/decision", {"decision": "reject"}, format="json"
    ).data["data"]
    assert final["status"] == "completed"
    keys = [run["node_key"] for run in final["node_runs"]]
    assert "end_no" in keys and "end_ok" not in keys


def test_instance_list_filters_by_status():
    client = _client()
    wf_id = _create(client)["id"]
    client.post(f"/api/workflow/workflows/{wf_id}/start", {"payload": {}}, format="json")

    rows = client.get("/api/workflow/instances?status=waiting").data["data"]
    assert len(rows) == 1
    assert rows[0]["status"] == "waiting"
    assert client.get("/api/workflow/instances?status=completed").data["data"] == []


def test_dashboard_metrics_reflect_real_data():
    client = _client()
    wf_id = _create(client)["id"]
    client.post(f"/api/workflow/workflows/{wf_id}/start", {"payload": {}}, format="json")

    metrics = client.get("/api/workflow/dashboard/metrics").data["data"]
    assert metrics["workflows_total"] == 1
    assert metrics["workflows_active"] == 1
    assert metrics["instances_total"] == 1
    assert metrics["instances_waiting"] == 1
    assert metrics["instances_by_status"]["waiting"] == 1


def test_requires_authentication():
    res = APIClient().get("/api/workflow/workflows")
    assert res.status_code == 401
