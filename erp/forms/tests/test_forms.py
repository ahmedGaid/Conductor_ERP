"""Forms: schema validation + optional workflow trigger on submit."""
from __future__ import annotations

import pytest

from erp.core.errors import ValidationError
from erp.forms import services
from erp.forms.models import FormDefinition
from erp.workflow.models import InstanceStatus, NodeType
from erp.workflow.tests.factories import make_workflow

pytestmark = pytest.mark.django_db


def _trigger_wf():
    return make_workflow(
        "form-trigger",
        nodes=[
            ("start", NodeType.START, {}),
            ("calc", NodeType.SCRIPT, {"logic": {"var": "amount"}, "output_key": "amt"}),
            ("end", NodeType.END, {}),
        ],
        edges=[("start", "calc", None, 0), ("calc", "end", None, 0)],
    )


SCHEMA = [
    {"key": "amount", "label": "Amount", "type": "number", "required": True},
    {"key": "note", "label": "Note", "type": "text", "required": False},
]


def test_valid_submission_triggers_workflow():
    wf = _trigger_wf()
    form = FormDefinition.objects.create(name="PR", schema=SCHEMA, trigger_workflow=wf)
    sub = services.submit(form, {"amount": 100})
    assert sub.instance is not None
    assert sub.instance.status == InstanceStatus.COMPLETED
    assert sub.instance.context["calc"] == {"amt": 100}


def test_missing_required_field_rejected():
    form = FormDefinition.objects.create(name="PR", schema=SCHEMA)
    with pytest.raises(ValidationError):
        services.submit(form, {"note": "x"})


def test_non_numeric_number_field_rejected():
    form = FormDefinition.objects.create(name="PR", schema=SCHEMA)
    with pytest.raises(ValidationError):
        services.submit(form, {"amount": "abc"})
