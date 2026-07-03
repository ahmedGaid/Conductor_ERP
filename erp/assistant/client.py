"""AI provider seam.

Single construction point so (a) tests monkeypatch ``get_client`` / ``get_gemini_client`` and
gates never make live calls, and (b) an install without an SDK or an API key still runs — the
assistant is optional and everything checks ``enabled()`` first.

Two providers behind the same extraction contract: Anthropic (Claude) and Google (Gemini).
``provider()`` picks by explicit ``ASSISTANT_PROVIDER`` or by whichever key is present.
"""
from __future__ import annotations

import base64

from django.conf import settings

DEFAULT_MODELS = {
    "anthropic": "claude-opus-4-8",
    "gemini": "gemini-2.5-flash",
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",  # multimodal (image) on Groq
}

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_ENABLED", False))


def provider() -> str:
    configured = getattr(settings, "ASSISTANT_PROVIDER", "")
    if configured:
        return configured
    if settings.ANTHROPIC_API_KEY:
        return "anthropic"
    if settings.GEMINI_API_KEY:
        return "gemini"
    if settings.GROQ_API_KEY:
        return "groq"
    # Flag forced on with no key (tests, dry setups): keep a deterministic path.
    return "anthropic"


def model_id() -> str:
    return settings.ASSISTANT_MODEL or DEFAULT_MODELS[provider()]


def get_client():
    import anthropic  # deferred: package is only needed when this provider is active

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def get_gemini_client():
    from google import genai  # deferred: package is only needed when this provider is active
    from google.genai import types

    # Disable the SDK's own retry: on a transient 429/503 its tenacity loop reuses an already-closed
    # httpx client and raises a misleading "client has been closed" RuntimeError. We retry at the
    # service layer with a fresh client instead (erp.assistant.services.extraction._extract_gemini).
    http_options = None
    try:
        http_options = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1))
    except Exception:  # pragma: no cover - older SDK without retry_options
        pass
    return genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)


def groq_chat(messages: list, *, model: str, max_tokens: int, json_mode: bool = True) -> dict:
    """One OpenAI-compatible chat completion against Groq. Returns the parsed JSON response.

    A thin function (not an SDK) so there's no extra dependency and tests can monkeypatch this
    single seam. Raises on any non-2xx (the caller maps it to the blame-free retryable error).
    """
    import httpx

    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = httpx.post(
        f"{GROQ_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json=payload,
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()


# --- Streaming (plan session 02) ---------------------------------------------------------------
# The natural-language answer step can stream its prose token-by-token so the chat UI renders as
# the model writes. Same key/config plumbing as the JSON path; only the transport differs. Any
# provider without a real streaming path falls back to one yield of the whole completion, so the
# SSE contract above (``complete_stream``) is identical for callers regardless of provider.


# --- attached files (plan session 07) ---------------------------------------------------------
# Chat can carry images/PDF to a vision-capable provider. Each media item is normalized to
# ``{"media_type", "data": bytes}`` (see services.files) and injected into the single user message
# per the active provider's content shape. Text/tabular files are already folded into the prompt
# text upstream, so they never reach here.


def _b64(data: bytes) -> str:
    return base64.standard_b64encode(data).decode("ascii")


def _anthropic_media_block(m: dict) -> dict:
    b64 = _b64(m["data"])
    if m["media_type"] == "application/pdf":
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    return {"type": "image",
            "source": {"type": "base64", "media_type": m["media_type"], "data": b64}}


def _inject_blocks(messages: list, media: list, block_for) -> list:
    """Rebuild the last user message so its text is preceded by the media content blocks."""
    msgs = [dict(m) for m in messages]
    last = msgs[-1]
    text = last["content"] if isinstance(last["content"], str) else ""
    blocks = [b for b in (block_for(m) for m in media) if b is not None]
    last["content"] = [*blocks, {"type": "text", "text": text}]
    return msgs


def _stream_anthropic(messages: list, system: str | None, media: list | None = None):
    if media:
        messages = _inject_blocks(messages, media, _anthropic_media_block)
    kwargs = dict(model=model_id(), max_tokens=settings.ASSISTANT_MAX_TOKENS, messages=messages)
    if system:
        kwargs["system"] = system
    with get_client().messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            if text:
                yield text


def _stream_gemini(messages: list, system: str | None, media: list | None = None):
    from google.genai import types

    cfg = dict(max_output_tokens=settings.ASSISTANT_MAX_TOKENS)
    if system:
        cfg["system_instruction"] = system
    try:  # thinking off — whole budget to the answer (mirrors services.llm._gemini)
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:  # pragma: no cover - older SDK/model without thinking support
        pass
    if media:
        text = "\n".join(m["content"] for m in messages if isinstance(m["content"], str))
        contents = [types.Part.from_bytes(data=m["data"], mime_type=m["media_type"]) for m in media]
        contents.append(text)
    else:
        contents = [m["content"] for m in messages]
    for chunk in get_gemini_client().models.generate_content_stream(
        model=model_id(), contents=contents, config=types.GenerateContentConfig(**cfg)
    ):
        text = getattr(chunk, "text", "") or ""
        if text:
            yield text


def _groq_media_block(m: dict):
    if m["media_type"] == "application/pdf":
        return None  # Llama-4 vision can't read PDF; the file simply isn't shown
    return {"type": "image_url",
            "image_url": {"url": f'data:{m["media_type"]};base64,{_b64(m["data"])}'}}


def _stream_groq(messages: list, system: str | None, media: list | None = None):
    import json as _json

    import httpx

    if media:
        msgs_in = [dict(m) for m in messages]
        last = msgs_in[-1]
        text = last["content"] if isinstance(last["content"], str) else ""
        blocks = [b for b in (_groq_media_block(m) for m in media) if b is not None]
        last["content"] = [{"type": "text", "text": text}, *blocks]
        messages = msgs_in
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    payload = {
        "model": model_id(), "messages": msgs,
        "max_tokens": settings.ASSISTANT_MAX_TOKENS, "temperature": 0, "stream": True,
    }
    with httpx.stream(
        "POST", f"{GROQ_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
        json=payload, timeout=60.0,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                delta = _json.loads(data)["choices"][0]["delta"].get("content")
            except (KeyError, IndexError, ValueError, TypeError):
                continue
            if delta:
                yield delta


def complete_stream(messages: list, *, system: str | None = None, media: list | None = None):
    """Yield answer text chunks from the active provider.

    ``media`` (optional) is a list of ``{"media_type", "data": bytes}`` — images/PDF injected into
    the user turn for a vision-capable provider (see services.files). Falls back to a single yield of
    the full completion for any provider without a streaming path yet — callers never need to know
    the difference.
    """
    runner = {"gemini": _stream_gemini, "groq": _stream_groq}.get(provider(), _stream_anthropic)
    yield from runner(messages, system, media)
