"""Context budget manager (ai-reliability T3.6): the envelope assembles within an explicit token
budget so ``context_overflow`` becomes structurally impossible.

Callers register ``Section``s (system/persona, page snapshot, retrieval, history, ...) with a
priority and an optional ``degrade_fn``; ``assemble()`` measures each with the shared token
heuristic (``tracing.estimate_tokens``), keeps them in priority order until the budget runs out,
degrading the first section that doesn't fit before dropping it outright. One manager, reused by
``context.py`` (system-prompt sections) and ``agent.py`` (history section) — never two truncation
policies drifting apart.

Section ORDER passed in is priority order (lower number = kept first); it is NOT reordered here.
A caller that also uses this order to render the final prompt gets stable sections first for free
(the T3.6 precondition for provider prompt caching, T7.5) — document that at the call site, not
here, since this module doesn't know what "first" means for a given prompt shape.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .tracing import estimate_tokens

# model id -> provider-documented API context window (tokens). These are the actual ceiling the
# provider's API enforces today, not a marketing "max" claim (e.g. Groq caps Llama 4 Scout's
# context at 128K on its API even though the model itself is trained for far more) — an unlisted
# model never guesses a number (see ``_UNKNOWN_WINDOW``), matching ``tracing.PRICING``'s
# cost_unknown discipline.
CONTEXT_WINDOWS: dict[str, int] = {
    "claude-opus-4-8": 1_000_000,
    "gemini-2.5-flash": 1_048_576,
    "mistral-small-latest": 256_000,
    "meta-llama/llama-4-scout-17b-16e-instruct": 128_000,
}

# The smallest window any of the four current providers actually offers — a safe floor for a model
# missing from the table above (never guessed higher; a too-small budget only over-trims, a
# too-large one risks a real overflow).
_UNKNOWN_WINDOW = 32_000

# Held back from the window on top of the reply's own ``max_tokens`` ceiling — the ``len // 3``
# heuristic and each provider's real tokenizer disagree by a few percent; this is the buffer
# against that drift, not a tuning knob.
_SAFETY_MARGIN = 0.10


def context_window(model: str) -> int:
    return CONTEXT_WINDOWS.get(model, _UNKNOWN_WINDOW)


def budget_for(model: str, max_tokens: int) -> int:
    """Tokens available for the envelope: window − reply ``max_tokens`` − 10% margin, floored at 0
    (a ``max_tokens`` larger than the window can't push this negative)."""
    window = context_window(model)
    return max(0, window - max_tokens - round(window * _SAFETY_MARGIN))


@dataclass
class Section:
    name: str
    # Lower = kept longer. Trimming walks sections in ascending priority order, so the
    # HIGHEST-numbered (lowest-priority) sections are the first candidates once the budget runs out.
    priority: int
    content: str
    # Fraction of the total budget this section may use even if the overall budget would allow
    # more — keeps one oversized section (a big retrieval dump) from crowding out its neighbours.
    max_share: float = 1.0
    # Returns a shorter form of ``content``, or ``None``/the same string back to say "no shorter
    # form left" — the caller drops the section in that case rather than looping forever.
    degrade_fn: Callable[[str], str | None] | None = None


def assemble(sections: list[Section], *, model: str, max_tokens: int) -> tuple[dict[str, str], dict]:
    """Fit ``sections`` inside the model's budget.

    Returns ``(kept, meta)``:
    - ``kept`` maps section name → its final (possibly degraded) content, in priority order,
      omitting anything trimmed to nothing. Empty-content sections passed in are skipped entirely
      (never appear in either return value) — there is nothing to budget.
    - ``meta`` is the per-section ``{tokens, trimmed, dropped}`` record for
      ``Trace.meta.envelope``.

    Never exceeds ``budget_for(model, max_tokens)`` by construction: each section is only added to
    the running total after it's confirmed to fit.
    """
    budget = budget_for(model, max_tokens)
    live = [s for s in sections if s.content]
    kept: dict[str, str] = {}
    meta: dict[str, dict] = {}
    total = 0
    for section in sorted(live, key=lambda s: s.priority):
        content = section.content
        tokens = estimate_tokens(content)
        cap = round(budget * section.max_share)
        trimmed = False
        if tokens > cap or total + tokens > budget:
            shorter = _degrade(section)
            if shorter is not None:
                content = shorter
                tokens = estimate_tokens(content)
                trimmed = True
        if tokens > cap or total + tokens > budget:
            meta[section.name] = {"tokens": tokens, "trimmed": trimmed, "dropped": True}
            continue
        kept[section.name] = content
        total += tokens
        meta[section.name] = {"tokens": tokens, "trimmed": trimmed, "dropped": False}
    return kept, meta


def _degrade(section: Section) -> str | None:
    if section.degrade_fn is None:
        return None
    shorter = section.degrade_fn(section.content)
    if not shorter or shorter == section.content:
        return None
    return shorter
