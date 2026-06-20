"""Data-scope enforcement (Increment 5) — CRM.

create_lead stamps the actor's branch; scope_queryset isolates a BRANCH-scoped manager to their
own branch while leaving unstamped/NULL leads visible.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.core.models import Branch
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.crm import services
from erp.crm.domain.models import Lead, LeadStatus

pytestmark = pytest.mark.django_db

VIEW = "crm.lead.view"


def _manager(username: str, branch: Branch) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": "branch"})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def test_branch_scope_isolates_leads():
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("crm_a", a)
    mgr_b = _manager("crm_b", b)

    lead_a = services.create_lead(name="Lead A", actor=mgr_a)
    lead_b = services.create_lead(name="Lead B", actor=mgr_b)
    lead_null = Lead.objects.create(code="LEAD-NULL", name="Legacy", status=LeadStatus.NEW)

    assert lead_a.branch_id == a.id
    seen = set(scope_queryset(mgr_a, Lead.objects.all(), VIEW).values_list("id", flat=True))
    assert seen == {lead_a.id, lead_null.id}
    assert lead_b.id not in seen
