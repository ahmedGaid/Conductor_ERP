from erp.workflow.templates import TEMPLATE_CATALOG, expand


def test_catalog_has_five_templates():
    ids = {t["id"] for t in TEMPLATE_CATALOG}
    assert ids == {
        "approval_above_amount", "low_stock_alert", "overdue_invoice_reminder",
        "new_lead_followup", "ticket_escalation",
    }


def test_approval_above_amount_expands_to_a_valid_graph():
    result = expand("approval_above_amount", {
        "amount_minor": 500000, "approver_role": "finance_manager",
    })
    node_keys = {n["key"] for n in result["nodes"]}
    assert node_keys == {"start", "check_amount", "ask_approval", "end"}
    condition_node = next(n for n in result["nodes"] if n["key"] == "check_amount")
    assert condition_node["type"] == "condition"
    approval_node = next(n for n in result["nodes"] if n["key"] == "ask_approval")
    assert approval_node["config"]["approver_role"] == "finance_manager"
    assert result["trigger"]["condition"] == {">": [{"var": "amount_minor"}, 500000]}


def test_unknown_template_raises():
    import pytest
    from erp.core.errors import ValidationError

    with pytest.raises(ValidationError):
        expand("not_a_real_template", {})
