"""`{{ ctx.path }}` template resolver (no eval).

Resolves `{{ ctx.amount }}` / `{{ in.foo.bar }}` against a scope dict. A missing path raises a
clear error rather than silently injecting `undefined`/empty (engine determinism + safety).
"""
from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")

_MISSING = object()


def _resolve_path(path: str, scope: dict) -> Any:
    cur: Any = scope
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return _MISSING
    return cur


def render(template: str, scope: dict) -> str:
    """Render a string template, substituting tokens with stringified values."""

    def repl(m: re.Match) -> str:
        path = m.group(1)
        value = _resolve_path(path, scope)
        if value is _MISSING:
            raise KeyError(f"template path not found: {path}")
        return str(value)

    return _TOKEN.sub(repl, template)


def render_value(value: Any, scope: dict) -> Any:
    """Recursively render strings inside dicts/lists; non-strings pass through.

    A string that is exactly one token resolves to the *typed* value (not stringified) so numbers
    and booleans survive templating.
    """
    if isinstance(value, str):
        m = _TOKEN.fullmatch(value.strip())
        if m:
            resolved = _resolve_path(m.group(1), scope)
            if resolved is _MISSING:
                raise KeyError(f"template path not found: {m.group(1)}")
            return resolved
        return render(value, scope)
    if isinstance(value, dict):
        return {k: render_value(v, scope) for k, v in value.items()}
    if isinstance(value, list):
        return [render_value(v, scope) for v in value]
    return value
