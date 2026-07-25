"""Smart Import Engine REST API — endpoint shells over already-tested services (FILE_11).

The business logic (analyze/validate/duplicates/masters/engine/runner/autofix) is exercised in
its own test file; this one covers what only the HTTP layer can break: auth, ownership scoping,
wrong-state 409s, request/response shape, and one full upload-to-execute lifecycle.

``detect.detect_entity`` is pinned to "customers" for every test in this file (autouse fixture
below): customers/suppliers both have a "name" (+ optional "code") field, so match_headers'
substring fallback covers both at the same score regardless of header wording — a genuine tie in
the current scoring formula, not a fixture problem. Left unpinned, that tie falls through to a
REAL model call to break it (this dev box has live API keys configured) — slow, non-deterministic,
and exactly what a test suite must never depend on. Every test that cares which entity a batch
targets sets it explicitly in the ``/mapping`` call anyway, which always wins over whatever
upload-time detection guessed.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import detect as detect_module
from erp.imports import registry
from erp.imports.detect import Candidate, DetectResult
from erp.imports.models import ImportBatch, ImportProfile
from erp.imports.registry import FieldSpec, Issue
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _pin_detection_to_customers(monkeypatch):
    def _fake(actor, headers, samples):
        return DetectResult(candidates=[Candidate(entity="customers", confidence=100)], method="deterministic")
    monkeypatch.setattr(detect_module, "detect_entity", _fake)


def _manager_client(username: str = "api_mgr") -> tuple[APIClient, User]:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    user = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    user.groups.add(bm)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _plain_client(username: str = "api_clerk") -> tuple[APIClient, User]:
    user = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _admin_client(username: str = "api_admin") -> tuple[APIClient, User]:
    """A superuser bypasses both the ownership check AND `scope_queryset` RBAC data-scoping —
    needed for anything that reads `existing_labels` (the fuzzy-duplicate pass), since a bare
    BRANCH_MANAGER group membership with no seeded RolePermission row sees zero records."""
    user = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _csv(rows) -> bytes:
    text = "\n".join(",".join("" if c is None else str(c) for c in r) for r in rows)
    return text.encode("utf-8")


def _upload(client, rows, filename="data.csv"):
    upload = SimpleUploadedFile(filename, _csv(rows), content_type="text/csv")
    return client.post("/api/imports/upload", {"file": upload}, format="multipart")


class _GizmoApiAdapter:
    """Throwaway adapter for the autofix HTTP round trip (same pattern used across this plan's
    other test files) — a required field with a FieldSpec.default gives a real, fixable issue."""

    entity = "api_gizmos"
    label_key = "imports.entity.apiGizmos"
    fields = [
        FieldSpec(name="code", required=True, kind="text"),
        FieldSpec(name="label", required=True, kind="text", default="Unnamed"),
    ]
    natural_key = ["code"]
    group_by = None

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        return row

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []


@pytest.fixture()
def gizmo_api_adapter():
    adapter = _GizmoApiAdapter()
    registry.register(adapter)
    try:
        yield adapter
    finally:
        registry.REGISTER.pop("api_gizmos", None)


# --- auth / permissions --------------------------------------------------------------------------
def test_upload_requires_authentication():
    client = APIClient()
    resp = _upload(client, [["Customer Name"], ["Acme"]])
    assert resp.status_code == 401


def test_upload_requires_branch_manager_role():
    client, _ = _plain_client()
    resp = _upload(client, [["Customer Name"], ["Acme"]])
    assert resp.status_code == 403


def test_batch_detail_403s_for_a_non_owner_non_elevated_manager():
    owner_client, owner = _manager_client("owner1")
    other_client, _ = _manager_client("other1")
    up = _upload(owner_client, [["Customer Name"], ["Acme"]])
    batch_id = up.data["data"]["batch_id"]

    resp = other_client.get(f"/api/imports/{batch_id}")

    assert resp.status_code == 403


def test_batch_detail_visible_to_a_superuser_regardless_of_owner():
    owner_client, owner = _manager_client("owner2")
    admin_client, admin = _admin_client("admin1")
    up = _upload(owner_client, [["Customer Name"], ["Acme"]])
    batch_id = up.data["data"]["batch_id"]

    resp = admin_client.get(f"/api/imports/{batch_id}")

    assert resp.status_code == 200


def test_unknown_batch_id_404s():
    client, _ = _manager_client("nf1")
    resp = client.get("/api/imports/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# --- full lifecycle --------------------------------------------------------------------------
def test_full_lifecycle_upload_through_execute_and_report():
    client, user = _manager_client("life1")
    rows = [["Customer Name", "Customer Code"], ["Acme Trading", "C1"], ["Nile Foods", "C2"]]

    up = _upload(client, rows)
    assert up.status_code == 201, up.data
    body = up.data["data"]
    batch_id = body["batch_id"]
    assert body["headers"] == ["Customer Name", "Customer Code"]
    assert "customers" in [c["entity"] for c in body["candidates"]]
    assert body["mapping_suggestion"]["Customer Name"]["field"] == "name"
    customers_candidate = next(c for c in body["candidates"] if c["entity"] == "customers")
    assert customers_candidate["label_key"] == "imports.entity.customers"
    customer_fields = {f["name"]: f for f in body["entity_fields"]["customers"]}
    assert customer_fields["name"]["required"] is True
    assert customer_fields["name"]["kind"] == "text"

    mp = client.post(
        f"/api/imports/{batch_id}/mapping",
        {"entity": "customers", "mapping": {"name": "Customer Name", "code": "Customer Code"}}, format="json",
    )
    assert mp.status_code == 200, mp.data
    assert mp.data["data"]["stats"]["rows"] == 2
    # "previewing", not "ready" — validation finishing is not the same as a human confirming the
    # run (FILE_17 acceptance finding: the background runner claims any `ready` batch on sight, so
    # setting `ready` straight out of validation let it auto-execute before the user ever saw the
    # review screen). Only the explicit /execute call below may set `ready`.
    assert mp.data["data"]["batch"]["status"] == "previewing"

    rows_resp = client.get(f"/api/imports/{batch_id}/rows")
    assert rows_resp.data["data"]["total"] == 2
    assert {r["status"] for r in rows_resp.data["data"]["rows"]} == {"valid"}

    plan = client.get(f"/api/imports/{batch_id}/creation-plan")
    assert plan.status_code == 200
    assert plan.data["data"]["entries"] == []  # customers has no "ref" fields -> nothing to create

    ex = client.post(f"/api/imports/{batch_id}/execute", {"strategy": "create_only"}, format="json")
    assert ex.status_code == 200, ex.data
    assert ex.data["data"]["queued"] is False
    report = ex.data["data"]["report"]
    assert report["created"] == 2
    assert Customer.objects.filter(name="Acme Trading").exists()
    assert Customer.objects.filter(name="Nile Foods").exists()

    report_resp = client.get(f"/api/imports/{batch_id}/report")
    assert report_resp.data["data"]["created"] == 2
    assert len(report_resp.data["data"]["row_outcomes"]) == 2

    csv_resp = client.get(f"/api/imports/{batch_id}/report?format=csv")
    assert csv_resp["Content-Type"].startswith("text/csv")
    assert csv_resp.content.splitlines()[0] == b"row,status,model,pk,action"

    rb = client.post(f"/api/imports/{batch_id}/rollback")
    assert rb.status_code == 200, rb.data
    assert rb.data["data"]["reverted"] == 0  # CustomerAdapter exposes no delete path
    assert len(rb.data["data"]["cannot"]) == 2
    assert Customer.objects.filter(name="Acme Trading").exists()  # nothing was actually removed


# --- wrong-state 409s --------------------------------------------------------------------------
def test_execute_while_still_mapping_is_409():
    client, user = _manager_client("state1")
    up = _upload(client, [["Customer Name"], ["Acme"]])
    batch_id = up.data["data"]["batch_id"]  # status is still "mapping" -- /mapping never called

    resp = client.post(f"/api/imports/{batch_id}/execute", {}, format="json")

    assert resp.status_code == 409


def test_execute_with_undecided_duplicate_stays_out_of_ready_status():
    """FILE_17 acceptance regression: `execute` used to flip the batch to `ready` and save it
    BEFORE checking readiness, so a 409 (undecided duplicate) left the row permanently stuck in
    `ready` — a ghost the background runner would later claim and crash on (readiness fails again,
    uncaught). The status must never move off its pre-execute value when execute is refused."""
    client, user = _admin_client("dup2")
    Customer.objects.create(name="Ahmed Trading Co", code="C-EXIST")
    up = _upload(client, [["Customer Name"], ["Ahmed Trading"]])
    batch_id = up.data["data"]["batch_id"]
    client.post(
        f"/api/imports/{batch_id}/mapping",
        {"entity": "customers", "mapping": {"name": "Customer Name"}}, format="json",
    )
    row = client.get(f"/api/imports/{batch_id}/rows").data["data"]["rows"][0]
    assert row["status"] == "duplicate"
    status_before = ImportBatch.objects.get(pk=batch_id).status

    resp = client.post(f"/api/imports/{batch_id}/execute", {}, format="json")

    assert resp.status_code == 409, resp.data
    assert resp.data["error"]["data"]["reasons"][0]["code"] == "undecided_duplicates"
    batch = ImportBatch.objects.get(pk=batch_id)
    assert batch.status == status_before
    assert batch.status != ImportBatch.Status.READY


def test_row_patch_while_running_is_409():
    client, user = _manager_client("state2")
    up = _upload(client, [["Customer Name"], ["Acme"]])
    batch_id = up.data["data"]["batch_id"]
    client.post(
        f"/api/imports/{batch_id}/mapping",
        {"entity": "customers", "mapping": {"name": "Customer Name"}}, format="json",
    )
    batch = ImportBatch.objects.get(pk=batch_id)
    batch.status = ImportBatch.Status.RUNNING
    batch.save(update_fields=["status"])

    resp = client.patch(f"/api/imports/{batch_id}/rows/1", {"edits": {"name": "x"}}, format="json")

    assert resp.status_code == 409


# --- row edit / duplicate decision ------------------------------------------------------------
def test_row_patch_edit_updates_normalized_value():
    client, user = _manager_client("edit1")
    up = _upload(client, [["Customer Name"], ["Acme"]])
    batch_id = up.data["data"]["batch_id"]
    client.post(
        f"/api/imports/{batch_id}/mapping",
        {"entity": "customers", "mapping": {"name": "Customer Name"}}, format="json",
    )

    resp = client.patch(f"/api/imports/{batch_id}/rows/1", {"edits": {"name": "Acme Updated"}}, format="json")

    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["normalized"]["name"] == "Acme Updated"


def test_row_patch_duplicate_decision_create_resolves_to_valid():
    # Superuser: fuzzy dedup reads adapter.existing_labels() -> scope_queryset(), which needs a
    # real RBAC permission row a bare BRANCH_MANAGER-group test user doesn't have.
    client, user = _admin_client("dup1")
    Customer.objects.create(name="Ahmed Trading Co", code="C-EXIST")
    up = _upload(client, [["Customer Name"], ["Ahmed Trading"]])
    batch_id = up.data["data"]["batch_id"]
    client.post(
        f"/api/imports/{batch_id}/mapping",
        {"entity": "customers", "mapping": {"name": "Customer Name"}}, format="json",
    )

    row = client.get(f"/api/imports/{batch_id}/rows").data["data"]["rows"][0]
    assert row["status"] == "duplicate"

    resp = client.patch(f"/api/imports/{batch_id}/rows/1", {"decision": {"duplicate": "create"}}, format="json")

    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["status"] == "valid"


# --- autofix --------------------------------------------------------------------------------
def test_autofix_preview_then_apply_via_api(gizmo_api_adapter):
    client, user = _manager_client("af1")
    up = _upload(client, [["Code", "Label"], ["G1", ""]])
    batch_id = up.data["data"]["batch_id"]
    client.post(
        f"/api/imports/{batch_id}/mapping",
        {"entity": "api_gizmos", "mapping": {"code": "Code", "label": "Label"}}, format="json",
    )

    preview = client.post(f"/api/imports/{batch_id}/autofix")
    assert preview.status_code == 200
    fixes = preview.data["data"]["fixes"]
    assert fixes == [{"row_id": fixes[0]["row_id"], "row": 1, "field": "label", "from": None, "to": "Unnamed", "code": "required_missing"}]

    empty_apply = client.post(f"/api/imports/{batch_id}/autofix/apply", {"fixes": []}, format="json")
    assert empty_apply.status_code == 400  # nothing accepted -> rejected, not silently a no-op

    apply = client.post(f"/api/imports/{batch_id}/autofix/apply", {"fixes": fixes}, format="json")
    assert apply.status_code == 200, apply.data
    assert apply.data["data"]["counts"]["valid"] == 1

    row = client.get(f"/api/imports/{batch_id}/rows").data["data"]["rows"][0]
    assert row["status"] == "valid"
    assert row["normalized"]["label"] == "Unnamed"


# --- profiles ---------------------------------------------------------------------------------
def test_profile_save_then_hits_on_the_next_matching_upload():
    client, user = _manager_client("prof1")

    created = client.post(
        "/api/imports/profiles",
        {
            "name": "My Customer Sheet", "entity": "customers",
            "mapping": {"Customer Name": "name", "Customer Code": "code"},
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    profile_id = created.data["data"]["id"]

    up = _upload(client, [["Customer Name", "Customer Code"], ["Acme", "C1"]])
    hits = up.data["data"]["profile_hits"]
    assert any(h["id"] == profile_id for h in hits)

    deleted = client.delete(f"/api/imports/profiles/{profile_id}")
    assert deleted.status_code == 204
    assert not ImportProfile.objects.filter(pk=profile_id).exists()


def test_mapping_view_applies_a_saved_profile_by_id():
    client, user = _manager_client("prof2")
    profile = ImportProfile.objects.create(
        name="Reuse Me", entity="customers", mapping={"Customer Name": "name"}, created_by=user,
    )
    up = _upload(client, [["Customer Name"], ["Acme"]])
    batch_id = up.data["data"]["batch_id"]

    resp = client.post(
        f"/api/imports/{batch_id}/mapping", {"entity": "customers", "profile_id": str(profile.pk)}, format="json",
    )

    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["batch"]["mapping"] == {"name": "Customer Name"}
