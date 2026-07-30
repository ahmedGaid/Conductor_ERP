"""Memory-lift, paired (ai-reliability T4.5): does remembering actually change the outcome?

Twelve paired cases (six Arabic, six English), each run twice against the REAL envelope builder —
once with the memory seeded, once with an identical user who has none. A case only passes when the
remembered value is present in the first prompt AND absent from the second: presence alone would
also pass if the envelope leaked the value from somewhere else, so causality is what's asserted.

Case ids mirror the ``memory_lift_*`` rows added to ``evals/datasets/golden_v1.jsonl`` — those rows
grade the model's *answer* once a recording exists (the offline runner skips unrecorded cases);
these tests grade the wiring that feeds it, with no provider involved.
"""
from __future__ import annotations

import pytest

from erp.assistant.services import context, memory as memory_service
from erp.identity.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    monkeypatch.setattr(memory_service.gateway, "embed_text", lambda text: None)


def _user(username: str) -> User:
    return User.objects.create_user(username=username, email=f"{username}@example.test",
                                    password="Dev12345!")


# (case_id, message, kind, slot key, value, the string the prompt must carry)
CASES = [
    ("memory_lift_warehouse_ar", "اعمل أمر شراء لموّرد النيل", "slot", "default_warehouse",
     "WH-31", "- default_warehouse: WH-31"),
    ("memory_lift_warehouse_en", "raise a purchase order for Nile Supplies", "slot",
     "default_warehouse", "WH-31", "- default_warehouse: WH-31"),
    ("memory_lift_branch_ar", "ما مبيعات فرعي هذا الشهر؟", "slot", "default_branch", "BR-GIZA",
     "- default_branch: BR-GIZA"),
    ("memory_lift_branch_en", "what are my branch's sales this month?", "slot", "default_branch",
     "BR-GIZA", "- default_branch: BR-GIZA"),
    ("memory_lift_language_ar", "sales summary", "slot", "language", "ar", "- language: ar"),
    ("memory_lift_language_en", "ملخص المبيعات", "slot", "language", "en", "- language: en"),
    ("memory_lift_digest_ar", "متى يوصلني الملخص اليومي؟", "slot", "digest_time", "07:30",
     "- digest_time: 07:30"),
    ("memory_lift_digest_en", "when does my daily digest arrive?", "slot", "digest_time", "07:30",
     "- digest_time: 07:30"),
    ("memory_lift_fact_supplier_ar", "من الموّرد المفضّل للأرز؟", "fact", "",
     "The user buys rice from Nile Supplies only.", "Nile Supplies only"),
    ("memory_lift_fact_supplier_en", "who is our preferred rice supplier?", "fact", "",
     "The user buys rice from Nile Supplies only.", "Nile Supplies only"),
    ("memory_lift_fact_closing_ar", "هل أقفل الشهر؟", "fact", "",
     "The user closes the accounting period on the third working day.", "third working day"),
    ("memory_lift_fact_closing_en", "should I close the period?", "fact", "",
     "The user closes the accounting period on the third working day.", "third working day"),
]


@pytest.mark.parametrize("case_id,message,kind,key,value,marker", CASES,
                         ids=[c[0] for c in CASES])
def test_seeded_memory_changes_the_envelope_and_its_absence_changes_it_back(
        case_id, message, kind, key, value, marker):
    remembering = _user(f"{case_id}_with"[:150])
    forgetting = _user(f"{case_id}_without"[:150])
    memory_service.remember(remembering, scope="user", kind=kind, key=key, value=value)

    with_memory, with_meta = context.build_system_prompt_with_meta(
        remembering, page=None, message=message)
    without_memory, without_meta = context.build_system_prompt_with_meta(
        forgetting, page=None, message=message)

    assert marker in with_memory, f"{case_id}: the remembered value never reached the envelope"
    assert marker not in without_memory, f"{case_id}: the value appeared without any memory"
    # Ops visibility (T4.5 step 3): the section is measured, so its tokens show up in
    # ``Trace.meta.envelope.memory`` for the ops page.
    assert with_meta["memory"]["tokens"] > 0
    assert "memory" not in without_meta
