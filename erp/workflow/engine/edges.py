"""Deterministic edge selection.

Edges are always read in (ordering ASC, id ASC). A Condition node selects exactly one winning
out-edge by evaluating each edge's JSON-logic condition against context. Zero or >=2 winners is a
hard failure (never guess). A non-condition node must have exactly one out-edge.
"""
from __future__ import annotations

from ..lib.jsonlogic import jsonlogic
from ..models import NodeType, WorkflowEdge, WorkflowNode
from .types import EdgeSelectionError


def _ordered_out_edges(node: WorkflowNode) -> list[WorkflowEdge]:
    return list(node.out_edges.all().order_by("ordering", "id"))


def select_edge(node: WorkflowNode, context: dict) -> WorkflowEdge:
    """Return the single winning out-edge for ``node`` given ``context``."""
    edges = _ordered_out_edges(node)
    if not edges:
        raise EdgeSelectionError(f"node '{node.key}' has no out-edges")

    if node.type == NodeType.CONDITION:
        # Guards carry an explicit JSON-logic condition; a null/True edge is the else-fallback.
        guards = [e for e in edges if e.condition not in (None, {}, True)]
        fallbacks = [e for e in edges if e.condition in (None, {}, True)]
        truthy = [e for e in guards if bool(jsonlogic(e.condition, context))]
        if len(truthy) == 1:
            return truthy[0]
        if len(truthy) >= 2:
            raise EdgeSelectionError(
                f"condition node '{node.key}' selected {len(truthy)} edges (expected exactly 1)"
            )
        # Zero guards matched -> take the single fallback if present.
        if len(fallbacks) == 1:
            return fallbacks[0]
        raise EdgeSelectionError(
            f"condition node '{node.key}' selected 0 edges (expected exactly 1)"
        )

    # Non-condition node: exactly one out-edge allowed.
    if len(edges) != 1:
        raise EdgeSelectionError(
            f"non-condition node '{node.key}' has {len(edges)} out-edges (expected exactly 1)"
        )
    return edges[0]
