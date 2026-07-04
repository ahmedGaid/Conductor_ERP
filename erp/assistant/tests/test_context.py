"""System-prompt envelope (plan session 03) — identity/user/page/company sections.

Session 08 extends it: page filters/dirty-form-warning, company branch/warehouse/fiscal-period
facts, and a recent-AI-actions block sourced from the conversation's proposal messages.
"""
from __future__ import annotations

import datetime

import pytest
from django.contrib.auth.models import Group

from erp.accounting.domain.models import FiscalYear, Period, PeriodStatus
from erp.assistant.models import Conversation, Message
from erp.assistant.services import context
from erp.core.models import Branch
from erp.identity import services as identity_services
from erp.identity.models import RolePermission, User
from erp.inventory.domain.models import Warehouse

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


def test_page_language_instructs_english_when_ui_is_english():
    user = _user()
    page = {"module": "sales", "path": "/sales/orders", "record": None, "language": "en",
            "recent": []}

    prompt = context.build_system_prompt(user, page=page)

    assert "interface is currently set to English" in prompt
    assert "answer in English" in prompt


def test_page_language_instructs_arabic_when_ui_is_arabic():
    user = _user()
    page = {"module": "sales", "path": "/sales/orders", "record": None, "language": "ar",
            "recent": []}

    prompt = context.build_system_prompt(user, page=page)

    assert "interface is currently set to Arabic" in prompt


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


def test_prompt_names_the_four_sources():
    user = _user()

    prompt = context.build_system_prompt(user, page=None)

    assert "data tools" in prompt
    assert "document search" in prompt
    assert "never a source of business facts" in prompt
    assert "Never invent" in prompt


def test_prompt_orders_sources_after_persona():
    user = _user()

    prompt = context.build_system_prompt(user, page=None)

    assert prompt.index("Adopt the expert lens") < prompt.index("Sources of truth")


def test_prompt_carries_arabic_provenance_phrase():
    user = _user()

    prompt = context.build_system_prompt(user, page=None)

    assert "من مستندات الشركة" in prompt


def test_filters_rendered_and_capped():
    user = _user()
    page = {"module": "sales", "path": "/sales/orders", "record": None, "language": "ar",
             "recent": [], "filters": {f"k{i}": str(i) for i in range(12)}}

    prompt = context.build_system_prompt(user, page=page)

    assert "Active list filters:" in prompt
    rendered = prompt.split("Active list filters:")[1].split(".")[0]
    assert rendered.count("=") == 10


def test_dirty_flag_warns_about_unsaved_changes():
    user = _user()
    page = {"module": "sales", "path": "/sales/orders/new", "record": None, "language": "ar",
             "recent": [], "dirty": True}

    prompt = context.build_system_prompt(user, page=page)

    assert "UNSAVED form changes" in prompt


def test_company_block_includes_branch_warehouse_and_fiscal_period():
    branch = Branch.objects.create(code="CAI", name="Cairo Branch")
    user = _user()
    user.branch = branch
    user.save(update_fields=["branch"])
    Warehouse.objects.create(code="WH-MAIN", name="Main Warehouse")
    today = datetime.date.today()
    year = FiscalYear.objects.create(
        code=str(today.year), start_date=today.replace(month=1, day=1),
        end_date=today.replace(month=12, day=31),
    )
    Period.objects.create(
        fiscal_year=year, code=f"{today.year}-{today.month:02d}",
        start_date=today.replace(day=1), end_date=today.replace(day=28),
        status=PeriodStatus.OPEN,
    )

    prompt = context.build_system_prompt(user, page=None)

    assert "Cairo Branch" in prompt
    assert "Default warehouse: WH-MAIN" in prompt
    assert f"Current accounting period: {today.year}-{today.month:02d}" in prompt


def test_recent_actions_block_lists_proposals():
    user = _user()
    conversation = Conversation.objects.create(user=user)
    Message.objects.create(conversation=conversation, role="user", content="add a customer")
    Message.objects.create(
        conversation=conversation, role="assistant", content="Here is a draft.",
        meta={"proposal": {"action": "create_customer", "status": "pending"}},
    )
    Message.objects.create(
        conversation=conversation, role="assistant", content="Done.",
        meta={"proposal": {"action": "create_sales_order_draft", "status": "confirmed"}},
    )

    prompt = context.build_system_prompt(user, page=None, conversation=conversation)

    assert "create_customer (pending)" in prompt
    assert "create_sales_order_draft (confirmed)" in prompt


def test_prompt_without_conversation_unchanged():
    user = _user()

    with_none = context.build_system_prompt(user, page=None, conversation=None)
    without_kwarg = context.build_system_prompt(user, page=None)

    assert with_none == without_kwarg
    assert "Previous AI actions" not in with_none
