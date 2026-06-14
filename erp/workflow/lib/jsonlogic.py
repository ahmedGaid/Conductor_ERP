"""Minimal, safe JSON-logic evaluator.

Self-contained (no external dependency, no eval/exec) so it is auditable and deterministic — used
for both Condition-edge selection and the Script node. Supports the operator subset the ERP needs.

Reference shape: {"==": [{"var": "a.b"}, 5]}.
"""
from __future__ import annotations

from typing import Any


def _get_var(path: str, data: dict, default: Any = None) -> Any:
    if path == "" or path is None:
        return data
    cur: Any = data
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, (list, tuple)):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return cur


def _truthy(v: Any) -> bool:
    return bool(v)


def jsonlogic(rule: Any, data: dict | None = None) -> Any:
    """Evaluate a JSON-logic rule against ``data``."""
    data = data or {}

    # Primitives evaluate to themselves.
    if not isinstance(rule, dict):
        return rule

    if len(rule) != 1:
        raise ValueError(f"Invalid JSON-logic node (expected one operator): {rule!r}")

    op, args = next(iter(rule.items()))
    if not isinstance(args, list):
        args = [args]

    if op == "var":
        path = jsonlogic(args[0], data) if args else ""
        default = jsonlogic(args[1], data) if len(args) > 1 else None
        return _get_var(path, data, default)

    # Evaluate arguments lazily where it matters (and/or/if), eagerly otherwise.
    if op == "and":
        result: Any = True
        for a in args:
            result = jsonlogic(a, data)
            if not _truthy(result):
                return result
        return result
    if op == "or":
        result = False
        for a in args:
            result = jsonlogic(a, data)
            if _truthy(result):
                return result
        return result
    if op == "if":
        # if(cond, then, [cond2, then2, ...], else)
        i = 0
        while i + 1 < len(args):
            if _truthy(jsonlogic(args[i], data)):
                return jsonlogic(args[i + 1], data)
            i += 2
        return jsonlogic(args[i], data) if i < len(args) else None

    ev = [jsonlogic(a, data) for a in args]

    if op in ("==", "==="):
        return ev[0] == ev[1]
    if op in ("!=", "!=="):
        return ev[0] != ev[1]
    if op == ">":
        return ev[0] > ev[1]
    if op == ">=":
        return ev[0] >= ev[1]
    if op == "<":
        return ev[0] < ev[1]
    if op == "<=":
        return ev[0] <= ev[1]
    if op == "!":
        return not _truthy(ev[0])
    if op == "!!":
        return _truthy(ev[0])
    if op == "+":
        return sum(ev)
    if op == "-":
        return ev[0] - ev[1] if len(ev) > 1 else -ev[0]
    if op == "*":
        result = 1
        for v in ev:
            result *= v
        return result
    if op == "/":
        return ev[0] / ev[1]
    if op == "%":
        return ev[0] % ev[1]
    if op == "in":
        return ev[0] in ev[1]

    raise ValueError(f"Unsupported JSON-logic operator: {op!r}")
