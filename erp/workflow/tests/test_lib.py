"""jsonlogic + template unit tests."""
from __future__ import annotations

import pytest

from erp.workflow.lib import template
from erp.workflow.lib.jsonlogic import jsonlogic


def test_jsonlogic_var_and_compare():
    data = {"check_budget": {"approved": True}, "amount": 100}
    assert jsonlogic({"==": [{"var": "check_budget.approved"}, True]}, data) is True
    assert jsonlogic({"<=": [{"var": "amount"}, 50]}, data) is False
    assert jsonlogic({"and": [{">": [{"var": "amount"}, 10]}, True]}, data) is True


def test_jsonlogic_rejects_unknown_operator():
    with pytest.raises(ValueError):
        jsonlogic({"danger": [1, 2]}, {})


def test_template_typed_single_token():
    scope = {"ctx": {"amount": 100, "supplier": "ACME"}}
    assert template.render_value("{{ctx.amount}}", scope) == 100  # int preserved
    assert template.render("PO for {{ctx.supplier}}", scope) == "PO for ACME"


def test_template_missing_path_raises():
    with pytest.raises(KeyError):
        template.render("{{ctx.nope}}", {"ctx": {}})
