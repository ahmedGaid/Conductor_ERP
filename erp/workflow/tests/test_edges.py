"""Edge selection: exactly one winner; 0 or >=2 is a hard error."""
from __future__ import annotations

import pytest

from erp.workflow.engine.edges import select_edge
from erp.workflow.engine.types import EdgeSelectionError
from erp.workflow.models import NodeType

from .factories import make_workflow

pytestmark = pytest.mark.django_db


def _condition_wf():
    return make_workflow(
        "cond",
        nodes=[
            ("gate", NodeType.CONDITION, {}),
            ("a", NodeType.END, {}),
            ("b", NodeType.END, {}),
        ],
        edges=[
            ("gate", "a", {"==": [{"var": "x"}, 1]}, 0),
            ("gate", "b", {"==": [{"var": "x"}, 2]}, 1),
        ],
    )


def test_exactly_one_winner():
    wf = _condition_wf()
    gate = wf.nodes.get(key="gate")
    edge = select_edge(gate, {"x": 1})
    assert edge.target.key == "a"


def test_zero_winners_fails():
    wf = _condition_wf()
    gate = wf.nodes.get(key="gate")
    with pytest.raises(EdgeSelectionError) as exc:
        select_edge(gate, {"x": 99})
    assert "0 edges" in str(exc.value)


def test_two_winners_fails():
    wf = make_workflow(
        "cond2",
        nodes=[("gate", NodeType.CONDITION, {}), ("a", NodeType.END, {}), ("b", NodeType.END, {})],
        edges=[
            ("gate", "a", {"==": [{"var": "x"}, 1]}, 0),
            ("gate", "b", {"==": [{"var": "x"}, 1]}, 1),
        ],
    )
    gate = wf.nodes.get(key="gate")
    with pytest.raises(EdgeSelectionError) as exc:
        select_edge(gate, {"x": 1})
    assert "2 edges" in str(exc.value)
