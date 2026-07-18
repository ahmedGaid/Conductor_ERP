"""ApprovalRequest lifecycle: created when a run halts at an ``approval`` node, RBAC-checked
decisions resume it. Kept out of ``engine.py`` (domain-agnostic) and ``services.py`` (imports
``engine`` for ``resume``) to avoid a module-load-time import cycle — this module is imported by
both, and only reaches back into ``engine`` with a local import inside ``decide()``.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.errors import ConflictError, PermissionError as AppPermissionError
from erp.identity.access import is_superadmin
from erp.notifications.contracts import notify

from .models import ApprovalRequest, ApprovalStatus, WorkflowInstance, WorkflowNode


def create_approval_request(instance: WorkflowInstance, node: WorkflowNode) -> ApprovalRequest:
    """Called by the engine the moment a run enters ``waiting`` at an approval node."""
    config = node.config or {}
    req = ApprovalRequest.objects.create(
        instance=instance,
        node=node,
        approver_user_id=config.get("approver_user_id") or None,
        approver_role=config.get("approver_role", ""),
        title=config.get("title", ""),
        message=config.get("message", ""),
    )
    _notify(req)
    return req


def _recipients(req: ApprovalRequest) -> list[str]:
    from erp.identity.models import User

    if req.approver_user_id:
        user = User.objects.filter(id=req.approver_user_id).first()
        return [user.username] if user else []
    if req.approver_role:
        return list(
            User.objects.filter(groups__name=req.approver_role).values_list("username", flat=True)
        )
    return []  # unscoped approval — no specific recipient to notify


def _notify(req: ApprovalRequest) -> None:
    subject = req.title or "Approval requested"
    body = req.message or f"A workflow step needs your approval ({req.instance.workflow.name})."
    for username in _recipients(req):
        notify(
            channel="inapp",
            recipient=username,
            subject=subject,
            body=body,
            reference=str(req.instance_id),
        )


def can_decide(actor, req: ApprovalRequest) -> bool:
    """Whether ``actor`` may decide this request — a superadmin always may; otherwise only the
    named approver (specific user or anyone holding the configured role); unscoped = anyone."""
    if is_superadmin(actor):
        return True
    if not req.approver_user_id and not req.approver_role:
        return True
    if req.approver_user_id and getattr(actor, "id", None) == req.approver_user_id:
        return True
    if req.approver_role and req.approver_role in set(getattr(actor, "roles", [])):
        return True
    return False


@transaction.atomic
def decide(*, actor, request_id, decision: str, comment: str = "") -> WorkflowInstance:
    """RBAC-checked approve/reject; records the decision, audits it, then resumes the run."""
    from .engine import engine

    req = ApprovalRequest.objects.select_for_update().get(id=request_id)
    if req.status != ApprovalStatus.PENDING:
        raise ConflictError("This approval was already decided")
    if not can_decide(actor, req):
        raise AppPermissionError("Only the assigned approver may decide this request")

    req.status = ApprovalStatus.APPROVED if decision == "approve" else ApprovalStatus.REJECTED
    req.decided_by = actor if getattr(actor, "is_authenticated", False) else None
    req.comment = comment
    req.decided_at = timezone.now()
    req.save(update_fields=["status", "decided_by", "comment", "decided_at"])

    audit.record(
        module="workflow",
        action="approval_decide",
        entity_type="ApprovalRequest",
        entity_id=str(req.id),
        actor=actor,
        after={"decision": decision, "comment": comment},
    )
    return engine.resume(req.instance_id, decision=decision)
