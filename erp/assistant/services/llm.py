"""Shared text→JSON completion across the three providers (Anthropic / Gemini / Groq).

The document-extraction path (``extraction.py``) sends an image; the natural-language assistant
(``ask.py``) sends text. Both need the same thing: a JSON object back from whichever provider is
configured. This module is the single place that speaks each provider's JSON dialect for a *text*
prompt, so callers stay provider-agnostic and tests monkeypatch one seam (``ask`` monkeypatches
``complete_json`` directly, so gates never make a live call).
"""
from __future__ import annotations

import json
import time

from django.conf import settings

from ..client import get_client, get_gemini_client, groq_chat, model_id, provider
from ..errors import AssistantUnavailableError
from .extraction import _gemini_schema  # reuse the strict→Gemini schema translation


def _schema_hint(schema: dict) -> str:
    # Groq is JSON-object mode only (no schema param) — spell the shape out in the prompt instead.
    return " Respond with a single JSON object only, no prose, matching this schema: " + json.dumps(schema)


def _anthropic(system: str, user: str, schema: dict) -> str:
    resp = get_client().messages.create(
        model=model_id(),
        max_tokens=settings.ASSISTANT_MAX_TOKENS,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": [{"type": "text", "text": user}]}],
    )
    if getattr(resp, "stop_reason", None) not in ("end_turn", None):
        return ""
    return next((b.text for b in resp.content if b.type == "text"), "")


def _gemini(system: str, user: str, schema: dict) -> str:
    from google.genai import types

    cfg = dict(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=_gemini_schema(schema),
        max_output_tokens=settings.ASSISTANT_MAX_TOKENS,
    )
    try:  # turn thinking off — the whole budget goes to the answer (see extraction._gemini_config)
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:  # pragma: no cover - older SDK/model without thinking support
        pass
    resp = get_gemini_client().models.generate_content(
        model=model_id(), contents=[user], config=types.GenerateContentConfig(**cfg)
    )
    return getattr(resp, "text", "") or ""


def _groq(system: str, user: str, schema: dict) -> str:
    body = groq_chat(
        [{"role": "system", "content": system + _schema_hint(schema)},
         {"role": "user", "content": user}],
        model=model_id(), max_tokens=settings.ASSISTANT_MAX_TOKENS,
    )
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def complete_json(system: str, user: str, schema: dict, *, retries: int = 3) -> dict:
    """One text prompt → one parsed JSON dict, from the configured provider.

    Retries transient failures with a short backoff (free-tier keys have low per-minute limits).
    Raises ``AssistantUnavailableError`` (blame-free, retryable) on repeated failure or garbage.
    """
    prov = provider()
    runner = {"gemini": _gemini, "groq": _groq}.get(prov, _anthropic)

    last_exc: Exception | None = None
    text = ""
    for attempt in range(retries):
        try:
            text = runner(system, user, schema)
            break
        except Exception as exc:  # network / auth / rate-limit — blame-free, retryable
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    else:
        raise AssistantUnavailableError(data={"reason": last_exc.__class__.__name__}) from last_exc

    if not text:
        raise AssistantUnavailableError(data={"reason": "empty_model_output"})
    try:
        return json.loads(text)
    except ValueError as exc:
        raise AssistantUnavailableError(data={"reason": "unparseable_model_output"}) from exc
