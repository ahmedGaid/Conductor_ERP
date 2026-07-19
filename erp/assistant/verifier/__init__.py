"""L1 verifier — deterministic invariant packs (os-foundations FILE_02).

After any agent write, a pack (not the model) checks the books: "the model narrates; it never
computes." Packs are pure **read-only** functions of a ``scope`` dict the caller builds from the
records the action just touched — they never fix anything (compensation is FILE_03's job) and never
call the LLM. This module owns the registry and ``run``; the six packs live in ``packs.py``.

``scope`` shape (built by the confirm flow in FILE_03; hand-built in tests here):
``{"links": [{"type": "order"|"journalEntry"|"stockTransfer"|..., "value": ...}], "payload": {...},
"actor": <user>}`` — ``links`` mirror the result-card links each ``execute()`` returns.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    """One pack's verdict on the touched records."""
    pack: str
    ok: bool
    message: str          # human, blame-free, English (i18n happens at the card layer, FILE_03/05)
    data: dict = field(default_factory=dict)  # machine detail: {account, expected, actual, ...}


@dataclass(frozen=True)
class Report:
    ok: bool                        # AND of all findings
    findings: tuple[Finding, ...]


# name -> pack callable ``(scope) -> Finding``. Populated by the ``@pack`` decorator in packs.py.
PACKS: dict[str, Callable[[dict], Finding]] = {}


def pack(name: str) -> Callable[[Callable[[dict], Finding]], Callable[[dict], Finding]]:
    """Register a pack function under ``name``."""
    def deco(fn: Callable[[dict], Finding]) -> Callable[[dict], Finding]:
        PACKS[name] = fn
        return fn
    return deco


def run(names, scope: dict) -> Report:
    """Run each named pack against ``scope`` and AND the findings.

    Never raises (defense in depth): an unknown name becomes a failing finding; a pack that throws
    becomes a failing finding carrying only the exception class (traces stay out of user text).
    """
    findings: list[Finding] = []
    for name in names:
        fn = PACKS.get(name)
        if fn is None:
            findings.append(Finding(name, False, f"Unknown check '{name}'.",
                                    {"error": "unknown_pack"}))
            continue
        try:
            findings.append(fn(scope))
        except Exception as exc:  # a broken pack must not break the write's report
            findings.append(Finding(name, False, "This check could not be completed.",
                                    {"error": type(exc).__name__}))
    return Report(ok=all(f.ok for f in findings), findings=tuple(findings))


# Import the pack functions so decorating populates PACKS. Placed last: the names above must exist
# before packs.py does ``from . import pack``.
from . import packs  # noqa: E402,F401
