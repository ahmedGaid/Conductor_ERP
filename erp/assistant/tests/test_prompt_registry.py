"""Prompt registry (ai-reliability T1.4): every system prompt is a versioned file, loaded once at
import, with a stable ``ref`` traces can record."""
from __future__ import annotations

import pytest

from erp.assistant.services import prompt_registry

EXPECTED_IDS = {
    "identity", "persona", "sources", "router", "answer_tone", "agent_loop", "extraction",
    "import_inspect",
}


def test_registry_loads_all_files():
    assert EXPECTED_IDS <= set(prompt_registry._REGISTRY.keys())
    for prompt_id in EXPECTED_IDS:
        prompt = prompt_registry.get(prompt_id)
        assert prompt.id == prompt_id
        assert prompt.template.strip()
        assert prompt.version
        assert prompt.changelog
        assert prompt.ref == f"{prompt_id}@{prompt.version}#{prompt.ref.rsplit('#', 1)[1]}"
        assert len(prompt.ref.rsplit("#", 1)[1]) == 8


def test_ref_is_stable_across_lookups():
    a = prompt_registry.get("router")
    b = prompt_registry.get("router")
    assert a is b
    assert a.ref == b.ref


def test_unknown_id_raises():
    with pytest.raises(prompt_registry.PromptNotFoundError):
        prompt_registry.get("does-not-exist")


def test_render_missing_placeholder_raises():
    prompt = prompt_registry.get("router")
    with pytest.raises(prompt_registry.PromptRenderError):
        prompt.render()  # router needs catalog + query_grammar


def test_render_fills_placeholders():
    prompt = prompt_registry.get("agent_loop")
    text = prompt.render(catalog="CATALOG", query_grammar="GRAMMAR", action_catalog="ACTIONS")
    assert "CATALOG" in text
    assert "GRAMMAR" in text
    assert "ACTIONS" in text
    # doubled braces in the template collapse to literal single braces after render
    assert '{"action": "tool"' in text


def test_render_without_placeholders_is_a_no_op():
    prompt = prompt_registry.get("identity")
    assert prompt.render() == prompt.template
