"""System-prompt envelope (plan session 03) — identity/user/page/company sections."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.assistant.services import context
from erp.identity import services as identity_services
from erp.identity.models import RolePermission, User

pytestmark = pytest.mark.django_db


def _user(username: str = "envelope_user", display_name: str = "Nadia Fathy") -> User:
    user = User.objects.create_user(
        username=username, email=f"{username}@example.test", password="Dev12345!",
    )
    identity_services.update_preferences(user, {"display_name": display_name})
    return user


def _grant(user: User, code: str, scope: str = "all") -> None:
    group, _ = Group.objects.get_or_create(name=f"role-{code}")
    RolePermission.objects.update_or_create(role=group, code=code, defaults={"scope": scope})
    user.groups.add(group)


def test_prompt_contains_username_role_and_modules():
    user = _user()
    _grant(user, "sales.order.view")

    prompt = context.build_system_prompt(user, page=None)

    assert user.username in prompt
    assert "role-sales.order.view" in prompt
    assert "Accessible modules: sales." in prompt


def test_page_section_renders_record_line_when_given():
    user = _user()
    page = {
        "module": "sales", "path": "/sales/orders/42",
        "record": {"type": "sales.orders", "id": "42", "label": "SO-2026-000042"},
        "language": "ar", "recent": [],
    }

    prompt = context.build_system_prompt(user, page=page)

    assert "SO-2026-000042" in prompt
    assert "sales" in prompt


def test_page_section_absent_when_no_page():
    user = _user()

    prompt = context.build_system_prompt(user, page=None)

    assert "Page:" not in prompt


def test_arabic_lexicon_block_always_present():
    user = _user()

    prompt = context.build_system_prompt(user, page=None)

    for term in ("عميل", "مورد", "صنف", "أمر بيع", "فاتورة"):
        assert term in prompt


def test_user_without_sales_permission_prompt_states_not_accessible():
    user = _user()
    _grant(user, "inventory.item.view")

    prompt = context.build_system_prompt(user, page=None)

    assert "Accessible modules: inventory." in prompt
    assert "outside the user's access" in prompt
