"""FILE_10 — the assistant-action node: actor scoping, the drafts-only validator, output flow,
and the AI-off soft failure.

The node runs a catalog action **as the run's triggering actor**, so the tests below prove the
permission boundary from the outside: the same graph, started by two different people, behaves
differently — and neither ever borrows a superuser.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.exceptions import ValidationError

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.workflow import services
from erp.workflow.engine import engine
from erp.workflow.executors.assistant_action import AI_OFF_BLOCKER
from erp.workflow.models import InstanceStatus, NodeType

from .factories import make_workflow

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _assistant_on(settings):
    """These tests exercise the node, not the provider — no model call happens (the catalog
    actions are plain Python), but the node refuses to run at all with the assistant switched off.
    """
    settings.ASSISTANT_ENABLED = True


def _user(username: str, *roles: str) -> User:
    user = User.objects.create_user(username=username, password="Dev12345!")
    for role in roles:
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
    return user


def _agent_wf(name="agent", *, config=None, with_approval=True):
    """start -> agent(create_customer) -> [approval] -> end."""
    nodes = [
        ("start", NodeType.START, {}),
        ("agent", NodeType.ASSISTANT_ACTION, config or {
            "action": "create_customer",
            "inputs": {"query": "{{ ctx.customer_name }}"},
        }),
        ("end", NodeType.END, {}),
    ]
    edges = [("start", "agent", None, 0)]
    if with_approval:
        nodes.insert(2, ("approve", NodeType.APPROVAL, {}))
        edges += [("agent", "approve", None, 0), ("approve", "end", None, 0)]
    else:
        edges += [("agent", "end", None, 0)]
    return make_workflow(name, nodes=nodes, edges=edges)


# --- Task A: the action runs, its output flows on ------------------------------------------------

def test_action_runs_as_trigger_and_output_reaches_next_node():
    manager = _user("wf_manager", BRANCH_MANAGER)
    wf = _agent_wf()

    inst = engine.start_instance(wf, {"customer_name": "Nile Trading"}, user=manager)

    # Halts at the approval that guards the draft — the drafts-only shape, running.
    assert inst.status == InstanceStatus.WAITING
    step = inst.context["agent"]
    assert step["action"] == "create_customer"
    assert step["links"], "the created draft should be linked from the run step"
    assert step["links"][0]["value"], "the link carries the new customer code"

    from erp.sales.models import Customer

    assert Customer.objects.filter(name="Nile Trading").exists()

    final = engine.resume(inst.id, decision="approve")
    assert final.status == InstanceStatus.COMPLETED


def test_output_key_nests_the_result():
    manager = _user("wf_manager_key", BRANCH_MANAGER)
    wf = _agent_wf("agent-key", config={
        "action": "create_customer",
        "inputs": {"query": "Delta Foods"},
        "output_key": "draft",
    })
    inst = engine.start_instance(wf, {}, user=manager)
    assert inst.context["agent"]["draft"]["action"] == "create_customer"


def test_trace_id_recorded_on_the_step():
    manager = _user("wf_manager_trace", BRANCH_MANAGER)
    inst = engine.start_instance(_agent_wf("agent-trace"), {"customer_name": "Cairo Mills"},
                                 user=manager)
    from erp.assistant.models import Trace

    trace_id = inst.context["agent"]["trace_id"]
    assert trace_id, "the run step must link to the gateway trace"
    assert Trace.objects.filter(id=trace_id, feature=Trace.Feature.WORKFLOW).exists()


# --- Task D/E: permission is the triggering actor's, never a system superuser --------------------

def test_actor_without_the_role_gets_a_permission_failure():
    clerk = _user("wf_clerk")  # no Branch Manager role
    inst = engine.start_instance(_agent_wf("agent-rbac"), {"customer_name": "Suez Supply"},
                                 user=clerk)

    assert inst.status == InstanceStatus.FAILED
    assert "permission" in inst.error.lower()

    from erp.sales.models import Customer

    assert not Customer.objects.filter(name="Suez Supply").exists()


def test_run_without_a_triggering_user_does_not_escalate():
    inst = engine.start_instance(_agent_wf("agent-anon"), {"customer_name": "Ghost Co"})
    assert inst.status == InstanceStatus.FAILED
    assert "started the run" in inst.error


def test_assistant_off_fails_soft_with_a_blocker(settings):
    settings.ASSISTANT_ENABLED = False
    manager = _user("wf_manager_off", BRANCH_MANAGER)
    inst = engine.start_instance(_agent_wf("agent-off"), {"customer_name": "Luxor Ltd"},
                                 user=manager)
    assert inst.status == InstanceStatus.FAILED
    assert inst.error == AI_OFF_BLOCKER


def test_workflow_without_an_assistant_node_is_unaffected_by_ai_being_off(settings):
    settings.ASSISTANT_ENABLED = False
    wf = make_workflow(
        "plain",
        nodes=[("start", NodeType.START, {}), ("end", NodeType.END, {})],
        edges=[("start", "end", None, 0)],
    )
    assert engine.start_instance(wf, {}).status == InstanceStatus.COMPLETED


# --- Task B: the drafts-only validator (save time) -----------------------------------------------

def _graph(nodes, edges):
    return (
        [{"key": k, "type": t, "config": c, "position": {}} for k, t, c in nodes],
        [{"source": s, "target": tg, "condition": cond, "ordering": o} for s, tg, cond, o in edges],
    )


AGENT_CONFIG = {"action": "create_customer", "inputs": {"query": "x"}}


def test_validator_rejects_a_draft_action_with_no_approval_after_it():
    nodes, edges = _graph(
        [("start", NodeType.START, {}), ("agent", NodeType.ASSISTANT_ACTION, AGENT_CONFIG),
         ("end", NodeType.END, {})],
        [("start", "agent", None, 0), ("agent", "end", None, 0)],
    )
    with pytest.raises(ValidationError) as exc:
        services.save_graph(name="bad", nodes=nodes, edges=edges)
    assert "approval" in str(exc.value)


def test_validator_rejects_when_only_one_branch_approves():
    """A condition after the agent: one branch approves, the other runs straight to the end."""
    nodes, edges = _graph(
        [("start", NodeType.START, {}), ("agent", NodeType.ASSISTANT_ACTION, AGENT_CONFIG),
         ("gate", NodeType.CONDITION, {}), ("approve", NodeType.APPROVAL, {}),
         ("end_ok", NodeType.END, {}), ("end_skip", NodeType.END, {})],
        [("start", "agent", None, 0), ("agent", "gate", None, 0),
         ("gate", "approve", {"==": [1, 1]}, 0), ("gate", "end_skip", None, 1),
         ("approve", "end_ok", None, 0)],
    )
    with pytest.raises(ValidationError) as exc:
        services.save_graph(name="half", nodes=nodes, edges=edges)
    assert "end_skip" in str(exc.value)


def test_validator_rejects_a_post_before_the_approval():
    """An external write (api_call write=true) may not sit between the draft and the human."""
    nodes, edges = _graph(
        [("start", NodeType.START, {}), ("agent", NodeType.ASSISTANT_ACTION, AGENT_CONFIG),
         ("send", NodeType.API_CALL, {"write": True, "url_template": "https://x", "method": "POST"}),
         ("approve", NodeType.APPROVAL, {}), ("end", NodeType.END, {})],
        [("start", "agent", None, 0), ("agent", "send", None, 0),
         ("send", "approve", None, 0), ("approve", "end", None, 0)],
    )
    with pytest.raises(ValidationError) as exc:
        services.save_graph(name="posts", nodes=nodes, edges=edges)
    assert "posts or sends" in str(exc.value)


def test_validator_accepts_an_approved_draft_graph():
    nodes, edges = _graph(
        [("start", NodeType.START, {}), ("agent", NodeType.ASSISTANT_ACTION, AGENT_CONFIG),
         ("approve", NodeType.APPROVAL, {}), ("end", NodeType.END, {})],
        [("start", "agent", None, 0), ("agent", "approve", None, 0), ("approve", "end", None, 0)],
    )
    wf = services.save_graph(name="good", nodes=nodes, edges=edges)
    assert wf.nodes.filter(type=NodeType.ASSISTANT_ACTION).count() == 1


def test_validator_rejects_an_unknown_action():
    nodes, edges = _graph(
        [("start", NodeType.START, {}),
         ("agent", NodeType.ASSISTANT_ACTION, {"action": "post_everything"}),
         ("approve", NodeType.APPROVAL, {}), ("end", NodeType.END, {})],
        [("start", "agent", None, 0), ("agent", "approve", None, 0), ("approve", "end", None, 0)],
    )
    with pytest.raises(ValidationError) as exc:
        services.save_graph(name="unknown", nodes=nodes, edges=edges)
    assert "does not exist" in str(exc.value)


def test_validator_rejects_an_unset_action():
    nodes, edges = _graph(
        [("start", NodeType.START, {}), ("agent", NodeType.ASSISTANT_ACTION, {}),
         ("approve", NodeType.APPROVAL, {}), ("end", NodeType.END, {})],
        [("start", "agent", None, 0), ("agent", "approve", None, 0), ("approve", "end", None, 0)],
    )
    with pytest.raises(ValidationError) as exc:
        services.save_graph(name="empty", nodes=nodes, edges=edges)
    assert "no action chosen" in str(exc.value)


def test_catalog_endpoint_lists_actions():
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=_user("wf_catalog", BRANCH_MANAGER))
    res = client.get("/api/workflow/assistant-actions")
    assert res.status_code == 200
    names = [row["name"] for row in res.json()["data"]]
    assert "create_customer" in names
