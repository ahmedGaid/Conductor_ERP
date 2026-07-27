"""Context budget manager (ai-reliability T3.6): pure Section/assemble() logic — no DB, no model
calls. ``model="claude-opus-4-8"`` (a real key in ``envelope.CONTEXT_WINDOWS``) is used throughout
so ``budget_for`` doesn't fall back to the conservative unknown-model window."""
from __future__ import annotations

from erp.assistant.services import envelope

_MODEL = "claude-opus-4-8"
# Not in CONTEXT_WINDOWS on purpose — falls back to the conservative 32K floor, so a modest
# max_tokens produces a budget small enough to actually exercise trimming/dropping in these tests.
_SMALL_MODEL = "unpriced-small-window-test-model"


def test_budget_for_is_window_minus_max_tokens_minus_margin():
    window = envelope.CONTEXT_WINDOWS[_MODEL]
    budget = envelope.budget_for(_MODEL, max_tokens=1000)
    assert budget == window - 1000 - round(window * 0.10)


def test_budget_for_unknown_model_uses_conservative_floor():
    budget = envelope.budget_for("some-future-model-nobody-priced-yet", max_tokens=1000)
    window = envelope._UNKNOWN_WINDOW
    assert budget == window - 1000 - round(window * 0.10)


def test_budget_for_never_goes_negative():
    assert envelope.budget_for(_MODEL, max_tokens=10_000_000) == 0


def test_assemble_keeps_everything_when_well_under_budget():
    sections = [
        envelope.Section("system", 0, "You are Conductor."),
        envelope.Section("page", 1, "The user is on the Sales Orders page."),
    ]
    kept, meta = envelope.assemble(sections, model=_MODEL, max_tokens=1000)
    assert list(kept.keys()) == ["system", "page"]
    assert kept["system"] == "You are Conductor."
    assert all(not m["dropped"] and not m["trimmed"] for m in meta.values())


def test_assemble_skips_empty_sections():
    sections = [
        envelope.Section("system", 0, "You are Conductor."),
        envelope.Section("page", 1, ""),  # empty content — never enters kept or meta
    ]
    kept, meta = envelope.assemble(sections, model=_MODEL, max_tokens=1000)
    assert "page" not in kept
    assert "page" not in meta


def test_assemble_preserves_priority_order_in_kept():
    # Insertion order into `kept` must be priority order regardless of the input list's order.
    sections = [
        envelope.Section("sources", 5, "sources text"),
        envelope.Section("system", 0, "system text"),
        envelope.Section("page", 2, "page text"),
    ]
    kept, _ = envelope.assemble(sections, model=_MODEL, max_tokens=1000)
    assert list(kept.keys()) == ["system", "page", "sources"]


def test_assemble_drops_lowest_priority_section_first_when_over_budget():
    big = "word " * 20_000  # ~33k tokens at the len//3 heuristic — over the ~27.8k small budget
    sections = [
        envelope.Section("system", 0, "short system text"),
        envelope.Section("history", 9, big),  # lowest priority — first to go
    ]
    kept, meta = envelope.assemble(sections, model=_SMALL_MODEL, max_tokens=1000)
    assert "system" in kept
    assert "history" not in kept
    assert meta["history"]["dropped"] is True
    assert meta["system"]["dropped"] is False


def test_assemble_degrades_before_dropping():
    calls: list[str] = []

    def shrink(content: str) -> str | None:
        calls.append(content)
        return "short form"

    sections = [envelope.Section("history", 0, "word " * 20_000, degrade_fn=shrink)]
    kept, meta = envelope.assemble(sections, model=_SMALL_MODEL, max_tokens=1000)

    assert calls == ["word " * 20_000]  # degrade_fn was tried
    assert kept["history"] == "short form"
    assert meta["history"]["trimmed"] is True
    assert meta["history"]["dropped"] is False


def test_assemble_drops_when_degrade_fn_cannot_shrink_enough():
    def shrink(content: str) -> str | None:
        return "still word " * 20_000  # "shorter" form that's actually still huge

    sections = [envelope.Section("history", 0, "word " * 20_000, degrade_fn=shrink)]
    kept, meta = envelope.assemble(sections, model=_SMALL_MODEL, max_tokens=1000)

    assert "history" not in kept
    assert meta["history"]["dropped"] is True
    assert meta["history"]["trimmed"] is True  # it DID try before giving up


def test_assemble_degrade_fn_returning_none_or_same_content_means_no_shorter_form():
    sections = [
        envelope.Section("a", 0, "word " * 20_000, degrade_fn=lambda c: None),
        envelope.Section("b", 1, "word " * 20_000, degrade_fn=lambda c: c),  # unchanged = no-op
    ]
    kept, meta = envelope.assemble(sections, model=_SMALL_MODEL, max_tokens=1000)
    assert kept == {}
    assert meta["a"]["trimmed"] is False
    assert meta["b"]["trimmed"] is False


def test_assemble_never_exceeds_budget():
    sections = [envelope.Section(f"s{i}", i, "word " * 500) for i in range(50)]
    budget = envelope.budget_for(_MODEL, max_tokens=4096)
    kept, meta = envelope.assemble(sections, model=_MODEL, max_tokens=4096)
    total = sum(envelope.estimate_tokens(c) for c in kept.values())
    assert total <= budget
    # every kept section really is marked not-dropped, every excluded one really is dropped
    for name, m in meta.items():
        assert (name in kept) == (not m["dropped"])


def test_assemble_respects_per_section_max_share_even_with_room_in_the_total_budget():
    # The total budget (real model, small max_tokens) has plenty of room for this section's ~16.6k
    # tokens — only its own max_share=0.01 cap (a few hundred tokens) is what drops it.
    budget = envelope.budget_for(_MODEL, max_tokens=1000)
    sections = [envelope.Section("hog", 0, "word " * 10_000, max_share=0.01)]
    kept, meta = envelope.assemble(sections, model=_MODEL, max_tokens=1000)
    assert envelope.estimate_tokens("word " * 10_000) < budget  # would fit the TOTAL budget alone
    assert "hog" not in kept
    assert meta["hog"]["dropped"] is True
