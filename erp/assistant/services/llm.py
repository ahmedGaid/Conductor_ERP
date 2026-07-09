"""Shared text→JSON completion across the four providers (Anthropic / Gemini / Mistral / Groq).

The document-extraction path (``extraction.py``) sends an image; the natural-language assistant
(``ask.py``) sends text. Both need the same thing: a JSON object back from whichever provider is
configured. This module is the single place that speaks each provider's JSON dialect for a *text*
prompt, so callers stay provider-agnostic and tests monkeypatch one seam (``ask`` monkeypatches
``complete_json`` directly, so gates never make a live call). ``complete_json`` fails over across the
provider chain: if the preferred provider is down / rate-limited / returns garbage, the next
available one is tried before the request is declared unavailable.
"""
from __future__ import annotations

import json
import time

from django.conf import settings

from ..client import (
    _anthropic_media_block,
    _groq_media_block,
    get_client,
    get_gemini_client,
    groq_chat,
    mistral_chat,
    model_id,
    provider_chain,
)
from ..errors import AssistantUnavailableError
from .extraction import _gemini_schema  # reuse the strict→Gemini schema translation


def _schema_hint(schema: dict) -> str:
    # Groq is JSON-object mode only (no schema param) — spell the shape out in the prompt instead.
    return " Respond with a single JSON object only, no prose, matching this schema: " + json.dumps(schema)


def _anthropic(system: str, user: str, schema: dict, media: list | None = None,
               model: str | None = None) -> str:
    # Images/PDF precede the instruction text in the user turn (mirrors extraction._extract_anthropic).
    content = ([_anthropic_media_block(m) for m in media] if media else []) + [
        {"type": "text", "text": user}
    ]
    resp = get_client().messages.create(
        model=model or model_id("anthropic"),
        max_tokens=settings.ASSISTANT_MAX_TOKENS,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": content}],
    )
    if getattr(resp, "stop_reason", None) not in ("end_turn", None):
        return ""
    return next((b.text for b in resp.content if b.type == "text"), "")


def _gemini(system: str, user: str, schema: dict, media: list | None = None,
            model: str | None = None) -> str:
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
    parts = [types.Part.from_bytes(data=m["data"], mime_type=m["media_type"]) for m in (media or [])]
    resp = get_gemini_client().models.generate_content(
        model=model or model_id("gemini"), contents=[*parts, user],
        config=types.GenerateContentConfig(**cfg),
    )
    return getattr(resp, "text", "") or ""


def _openai_compatible(chat, api_key_provider: str, system: str, user: str, schema: dict,
                       media: list | None, model: str | None) -> str:
    """Shared JSON path for the OpenAI-compatible providers (Groq, Mistral): a vision image block per
    media item, the schema spelled into the system prompt (json-object mode only), one chat call."""
    blocks = [b for b in ((_groq_media_block(m)) for m in (media or [])) if b is not None]
    user_content = [{"type": "text", "text": user}, *blocks] if blocks else user
    body = chat(
        [{"role": "system", "content": system + _schema_hint(schema)},
         {"role": "user", "content": user_content}],
        model=model or model_id(api_key_provider), max_tokens=settings.ASSISTANT_MAX_TOKENS,
    )
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _groq(system: str, user: str, schema: dict, media: list | None = None,
          model: str | None = None) -> str:
    return _openai_compatible(groq_chat, "groq", system, user, schema, media, model)


def _mistral(system: str, user: str, schema: dict, media: list | None = None,
             model: str | None = None) -> str:
    return _openai_compatible(mistral_chat, "mistral", system, user, schema, media, model)


_RUNNERS = {"anthropic": _anthropic, "gemini": _gemini, "groq": _groq, "mistral": _mistral}


def complete_json(system: str, user: str, schema: dict, *, media: list | None = None,
                  retries: int = 3, feature: str | None = None, actor=None,
                  conversation_id=None, prompt_ref: str = "") -> dict:
    """One prompt → one parsed JSON dict, failing over across the provider chain.

    ``media`` (optional) is a list of ``{"media_type", "data": bytes}`` (see services.files) —
    images/PDF injected into the user turn so a vision-capable provider reads them while it decides
    (the agent planner passes attachments here so "create a PO from the attached image" extracts real
    lines instead of guessing). Each provider in ``provider_chain()`` is retried a few times with a
    short backoff (free-tier keys have low per-minute limits); if it still fails, or returns empty /
    unparseable output, the next available provider is tried. Raises ``AssistantUnavailableError``
    (blame-free, retryable) only when every provider is exhausted.

    ``feature`` (optional) opens a trace for this call — omit it and the call is untraced,
    exactly as before (see ``services.tracing``).
    """
    from .tracing import estimate_tokens, null_trace, trace_call

    cm = (trace_call(feature, actor=actor, conversation_id=conversation_id, prompt_ref=prompt_ref)
          if feature else null_trace())
    with cm as handle:
        last_exc: Exception | None = None
        chain = provider_chain()
        for i, prov in enumerate(chain):
            runner = _RUNNERS.get(prov, _anthropic)
            model = model_id(prov)
            # Fail fast while a fallback remains: a provider that is down should hand off
            # immediately, not burn the whole retry+backoff budget first. Only the LAST provider
            # (no fallback left) gets the full retries — that's where waiting out a transient
            # rate-limit is worth it.
            attempts = retries if i == len(chain) - 1 else 1
            text = ""
            for attempt in range(attempts):
                try:
                    text = runner(system, user, schema, media, model)
                    break
                except Exception as exc:  # network / auth / rate-limit — retry, then fail over
                    last_exc = exc
                    if attempt < attempts - 1:
                        time.sleep(1.5 * (attempt + 1))
            else:
                continue  # this provider exhausted its attempts — try the next in the chain
            if not text:
                last_exc = AssistantUnavailableError(data={"reason": "empty_model_output"})
                continue  # empty output — try the next provider rather than fail outright
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                last_exc = exc  # garbage JSON — try the next provider
                continue
            handle.usage(provider=prov, model=model, estimated=True,
                         input_tokens=estimate_tokens(system + user),
                         output_tokens=estimate_tokens(text))
            return parsed
        if isinstance(last_exc, AssistantUnavailableError):
            raise last_exc
        raise AssistantUnavailableError(
            data={"reason": last_exc.__class__.__name__ if last_exc else "no_provider"}) from last_exc
