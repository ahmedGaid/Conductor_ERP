"""FILE_09 — ApprovalRequest lifecycle: creation on wait-entry, RBAC-checked decisions,
notification dispatch, audit trail, and durability across an engine restart."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.audit.models import AuditEntry
from erp.core.errors import ConflictError, PermissionError as AppPermissionError
from erp.identity.models import User
from erp.notifications.domain.models import Notification
from erp.workflow import approvals
from erp.workflow.engine import engine
from erp.workflow.models import ApprovalRequest, ApprovalStatus, InstanceStatus, NodeType

from .factories import make_workflow

pytestmark = pytest.mark.django_db


def _approval_wf(config=None):
    return make_workflow(
        "approval-rbac",
        nodes=[
            ("start", NodeType.START, {}),
            ("approve", NodeType.APPROVAL, config or {}),
            ("gate", NodeType.CONDITION, {}),
            ("end_ok", NodeType.END, {}),
            ("end_no", NodeType.END, {}),
        ],
        edges=[
            ("start", "approve", None, 0),
            ("approve", "gate", None, 0),
            ("gate", "end_ok", {"==": [{"var": "approve.approved"}, True]}, 0),
            ("gate", "end_no", None, 1),
        ],
    )


def test_wait_entry_creates_approval_request():
    wf = _approval_wf({"title": "Sign off", "message": "Please review"})
    inst = engine.start_instance(wf, {})
    assert inst.status == InstanceStatus.WAITING

    req = ApprovalRequest.objects.get(instance=inst)
    assert req.status == ApprovalStatus.PENDING
    assert req.title == "Sign off"
    assert req.message == "Please review"
    assert req.node.key == "approve"


def test_unscoped_approval_anyone_may_decide():
    wf = _approval_wf()  # no approver_user_id / approver_role
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)
    someone = User.objects.create_user(username="anyone", password="Dev12345!")

    final = approvals.decide(actor=someone, request_id=req.id, decision="approve")
    assert final.status == InstanceStatus.COMPLETED
    req.refresh_from_db()
    assert req.status == ApprovalStatus.APPROVED
    assert req.decided_by_id == someone.id


def test_scoped_approval_rejects_wrong_user():
    approver = User.objects.create_user(
        username="approver1", email="approver1@erp.local", password="Dev12345!"
    )
    other = User.objects.create_user(
        username="not_the_approver", email="not_the_approver@erp.local", password="Dev12345!"
    )
    wf = _approval_wf({"approver_user_id": approver.id})
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)

    with pytest.raises(AppPermissionError):
        approvals.decide(actor=other, request_id=req.id, decision="approve")

    # unaffected — still pending, run still waiting
    req.refresh_from_db()
    assert req.status == ApprovalStatus.PENDING
    inst.refresh_from_db()
    assert inst.status == InstanceStatus.WAITING


def test_scoped_approval_accepts_named_user():
    approver = User.objects.create_user(username="approver2", password="Dev12345!")
    wf = _approval_wf({"approver_user_id": approver.id})
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)

    final = approvals.decide(actor=approver, request_id=req.id, decision="approve")
    assert final.status == InstanceStatus.COMPLETED


def test_role_scoped_approval_accepts_any_holder_of_the_role():
    group = Group.objects.create(name="finance_manager")
    holder = User.objects.create_user(
        username="fin_mgr", email="fin_mgr@erp.local", password="Dev12345!"
    )
    holder.groups.add(group)
    outsider = User.objects.create_user(
        username="outsider", email="outsider@erp.local", password="Dev12345!"
    )

    wf = _approval_wf({"approver_role": "finance_manager"})
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)

    with pytest.raises(AppPermissionError):
        approvals.decide(actor=outsider, request_id=req.id, decision="reject")

    final = approvals.decide(actor=holder, request_id=req.id, decision="reject")
    assert final.status == InstanceStatus.COMPLETED
    assert final.context["approve"]["approved"] is False


def test_superadmin_bypasses_approver_scope():
    approver = User.objects.create_user(username="approver3", password="Dev12345!")
    admin = User.objects.create_superuser(username="wf_admin_su", email="a@x.com", password="Dev12345!")
    wf = _approval_wf({"approver_user_id": approver.id})
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)

    final = approvals.decide(actor=admin, request_id=req.id, decision="approve")
    assert final.status == InstanceStatus.COMPLETED


def test_deciding_an_already_decided_request_conflicts():
    wf = _approval_wf()
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)
    someone = User.objects.create_user(username="decider", password="Dev12345!")

    approvals.decide(actor=someone, request_id=req.id, decision="approve")
    with pytest.raises(ConflictError):
        approvals.decide(actor=someone, request_id=req.id, decision="approve")


def test_decide_records_audit_entry():
    wf = _approval_wf()
    inst = engine.start_instance(wf, {})
    req = ApprovalRequest.objects.get(instance=inst)
    someone = User.objects.create_user(username="auditee", password="Dev12345!")

    approvals.decide(actor=someone, request_id=req.id, decision="reject", comment="not today")

    entry = AuditEntry.objects.filter(
        module="workflow", action="approval_decide", entity_id=str(req.id)
    ).first()
    assert entry is not None
    assert entry.after["decision"] == "reject"
    assert entry.after["comment"] == "not today"


def test_decide_notifies_the_named_approver():
    approver = User.objects.create_user(username="notify_me", password="Dev12345!")
    wf = _approval_wf({"approver_user_id": approver.id, "title": "Needs sign-off"})
    engine.start_instance(wf, {})

    note = Notification.objects.filter(recipient="notify_me", subject="Needs sign-off").first()
    assert note is not None


def test_durable_across_restart_decision_still_works():
    """Simulates a process restart: fetch fresh from the DB, decide with no in-memory state."""
    wf = _approval_wf()
    inst = engine.start_instance(wf, {})
    instance_id = inst.id

    # "restart" — nothing but the id survives; re-fetch everything from the DB.
    from erp.workflow.models import WorkflowInstance

    reloaded = WorkflowInstance.objects.get(id=instance_id)
    assert reloaded.status == InstanceStatus.WAITING
    req = ApprovalRequest.objects.get(instance_id=instance_id)
    someone = User.objects.create_user(username="post_restart", password="Dev12345!")

    final = approvals.decide(actor=someone, request_id=req.id, decision="approve")
    assert final.status == InstanceStatus.COMPLETED
