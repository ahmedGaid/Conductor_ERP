"""AI provider seam.

Single construction point so (a) tests monkeypatch ``get_client`` / ``get_gemini_client`` and
gates never make live calls, and (b) an install without an SDK or an API key still runs — the
assistant is optional and everything checks ``enabled()`` first.

Four providers behind one seam: Anthropic (Claude), Google (Gemini), Mistral, Groq. Every key that
is set joins an automatic FAILOVER CHAIN (``provider_chain()``): the JSON/stream helpers try the
preferred provider first and fall to the next available one when it is down / rate-limited /
erroring. ``ASSISTANT_PROVIDER`` forces one to the front; otherwise the built-in ``PROVIDER_ORDER``
(strongest first) decides. ``provider()`` is just the head of the chain, kept for the callers that
only need the primary (model defaulting, the Gemini-only embedding path).
"""
from __future__ import annotations

import base64

from django.conf import settings

DEFAULT_MODELS = {
    "anthropic": "claude-opus-4-8",
    "gemini": "gemini-2.5-flash",
    "mistral": "mistral-small-latest",  # OpenAI-compatible; vision (Pixtral family) + JSON mode
    "groq": "meta-llama/llama-4-scout-17b-16e-instruct",  # multimodal (image) on Groq
}

# Which settings key holds each provider's credential.
PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
}

# Default preference (strongest / most reliable first). A configured ASSISTANT_PROVIDER jumps ahead
# of this; task-aware ordering (e.g. prefer a vision model for an image turn) is a later refinement.
PROVIDER_ORDER = ["anthropic", "gemini", "mistral", "groq"]

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MISTRAL_BASE_URL = "https://api.mistral.ai/v1"


def enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_ENABLED", False))


def _has_key(name: str) -> bool:
    return bool(getattr(settings, PROVIDER_KEYS.get(name, ""), ""))


def provider_chain() -> list[str]:
    """The ordered list of providers to try this request: a forced ``ASSISTANT_PROVIDER`` first (even
    without a key — tests monkeypatch its client), then every other provider that has a key, in
    ``PROVIDER_ORDER``. Never empty — falls back to a deterministic ``["anthropic"]`` for a flag-on,
    no-key setup so the path stays predictable."""
    configured = getattr(settings, "ASSISTANT_PROVIDER", "")
    chain: list[str] = []
    if configured:
        chain.append(configured)
    for name in PROVIDER_ORDER:
        if name not in chain and _has_key(name):
            chain.append(name)
    return chain or ["anthropic"]


def provider() -> str:
    """The primary provider — the head of the failover chain."""
    return provider_chain()[0]


def model_id(prov: str | None = None) -> str:
    """The model for a given provider (default: the primary). ``ASSISTANT_MODEL`` applies only to the
    primary provider — a fallback provider always uses its own default model, so we never send, say, a
    Claude model id to Mistral mid-failover."""
    prov = prov or provider()
    if settings.ASSISTANT_MODEL and prov == provider():
        return settings.ASSISTANT_MODEL
    return DEFAULT_MODELS.get(prov, DEFAULT_MODELS["anthropic"])


def get_client():
    import anthropic  # deferred: package is only needed when this provider is active

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def get_gemini_client(timeout_s: float | None = None):
    from google import genai  # deferred: package is only needed when this provider is active
    from google.genai import types

    # Disable the SDK's own retry: on a transient 429/503 its tenacity loop reuses an already-closed
    # httpx client and raises a misleading "client has been closed" RuntimeError. We retry at the
    # service layer with a fresh client instead (erp.assistant.services.extraction._extract_gemini).
    http_kwargs: dict = {}
    if timeout_s is not None:  # T2.2 per-task-class ceiling; None = SDK default (existing callers)
        http_kwargs["timeout"] = int(timeout_s * 1000)  # SDK wants milliseconds
    try:
        http_kwargs["retry_options"] = types.HttpRetryOptions(attempts=1)
    except Exception:  # pragma: no cover - older SDK without retry_options
        pass
    http_options = types.HttpOptions(**http_kwargs) if http_kwargs else None
    return genai.Client(api_key=settings.GEMINI_API_KEY, http_options=http_options)


def groq_chat(messages: list, *, model: str, max_tokens: int, json_mode: bool = True,
              timeout: float = 60.0, feature: str | None = None, actor=None, conversation_id=None,
              prompt_ref: str = "") -> dict:
    """One OpenAI-compatible chat completion against Groq. Returns the parsed JSON response.

    A thin function (not an SDK) so there's no extra dependency and tests can monkeypatch this
    single seam. Raises on any non-2xx (the caller maps it to the blame-free retryable error).

    ``feature`` (optional) opens a trace for this call — used only by callers that hit Groq
    directly (bypassing ``llm.complete_json``, which traces its own runners); omit it here when
    a caller already wraps the whole call in its own trace, to avoid a duplicate Trace row.
    """
    import httpx

    from .services.tracing import null_trace, trace_call

    cm = (trace_call(feature, actor=actor, conversation_id=conversation_id, prompt_ref=prompt_ref)
          if feature else null_trace())
    with cm as handle:
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = httpx.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        usage = body.get("usage") or {}
        if usage:
            handle.usage(provider="groq", model=model, input_tokens=usage.get("prompt_tokens", 0),
                         output_tokens=usage.get("completion_tokens", 0))
        return body


def mistral_chat(messages: list, *, model: str, max_tokens: int, json_mode: bool = True,
                 timeout: float = 60.0) -> dict:
    """One OpenAI-compatible chat completion against Mistral. Same thin shape as ``groq_chat`` (no
    SDK, one monkeypatchable seam); raises on any non-2xx for the caller to map."""
    import httpx

    payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    resp = httpx.post(
        f"{MISTRAL_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
        json=payload,
        timeout=timeout,
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


def _stream_anthropic(messages: list, system: str | None, media: list | None = None,
                      prov: str | None = None, timeout: float | None = None):
    if media:
        messages = _inject_blocks(messages, media, _anthropic_media_block)
    kwargs = dict(model=model_id(prov), max_tokens=settings.ASSISTANT_MAX_TOKENS, messages=messages)
    if system:
        kwargs["system"] = system
    if timeout is not None:  # T2.2 per-task-class ceiling
        kwargs["timeout"] = timeout
    with get_client().messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            if text:
                yield text


def _stream_gemini(messages: list, system: str | None, media: list | None = None,
                   prov: str | None = None, timeout: float | None = None):
    from google.genai import types

    cfg = dict(max_output_tokens=settings.ASSISTANT_MAX_TOKENS)
    if system:
        cfg["system_instruction"] = system
    try:  # thinking off — whole budget to the answer (mirrors gateway.core._gemini)
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:  # pragma: no cover - older SDK/model without thinking support
        pass
    if media:
        text = "\n".join(m["content"] for m in messages if isinstance(m["content"], str))
        contents = [types.Part.from_bytes(data=m["data"], mime_type=m["media_type"]) for m in media]
        contents.append(text)
    else:
        contents = [m["content"] for m in messages]
    for chunk in get_gemini_client(timeout_s=timeout).models.generate_content_stream(
        model=model_id(prov), contents=contents, config=types.GenerateContentConfig(**cfg)
    ):
        text = getattr(chunk, "text", "") or ""
        if text:
            yield text


def _openai_image_block(m: dict):
    """An OpenAI-compatible image content block (Groq + Mistral share the shape). PDF isn't shown on
    this path — the vision models here read images, not PDFs."""
    if m["media_type"] == "application/pdf":
        return None
    return {"type": "image_url",
            "image_url": {"url": f'data:{m["media_type"]};base64,{_b64(m["data"])}'}}


# Back-compat name (llm.py imports it); the block shape is provider-neutral.
_groq_media_block = _openai_image_block
_mistral_media_block = _openai_image_block


def _stream_openai_compatible(base_url: str, api_key: str, messages: list, system: str | None,
                              media: list | None, prov: str | None, timeout: float | None = None):
    """Shared SSE stream for the OpenAI-compatible providers (Groq, Mistral): same request shape,
    same ``choices[].delta.content`` deltas — only the base URL + key differ."""
    import json as _json

    import httpx

    if media:
        msgs_in = [dict(m) for m in messages]
        last = msgs_in[-1]
        text = last["content"] if isinstance(last["content"], str) else ""
        blocks = [b for b in (_openai_image_block(m) for m in media) if b is not None]
        last["content"] = [{"type": "text", "text": text}, *blocks]
        messages = msgs_in
    msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
    payload = {
        "model": model_id(prov), "messages": msgs,
        "max_tokens": settings.ASSISTANT_MAX_TOKENS, "temperature": 0, "stream": True,
    }
    with httpx.stream(
        "POST", f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload, timeout=timeout or 60.0,
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


def _stream_groq(messages: list, system: str | None, media: list | None = None,
                 prov: str | None = None, timeout: float | None = None):
    yield from _stream_openai_compatible(
        GROQ_BASE_URL, settings.GROQ_API_KEY, messages, system, media, prov, timeout)


def _stream_mistral(messages: list, system: str | None, media: list | None = None,
                    prov: str | None = None, timeout: float | None = None):
    yield from _stream_openai_compatible(
        MISTRAL_BASE_URL, settings.MISTRAL_API_KEY, messages, system, media, prov, timeout)


_STREAM_RUNNERS = {
    "anthropic": _stream_anthropic,
    "gemini": _stream_gemini,
    "groq": _stream_groq,
    "mistral": _stream_mistral,
}


# The provider-chain dispatch loop that used to live here (``complete_stream``) moved to
# ``gateway.core`` (Phase 2, T2.1) — it's dispatch logic, not a raw SDK call. ``_STREAM_RUNNERS``
# and the per-provider runners above stay here as the raw seam the gateway calls.


# --- knowledge-base embeddings (rag plan session 03) -------------------------------------------
# Optional semantic ranking for document search. Gemini-only (the SDK is already a dependency);
# any other provider or a failure returns None and search falls back to full-text alone.

EMBEDDING_MODEL = "text-embedding-004"


def embed_text(text: str, *, actor=None, conversation_id=None) -> list[float] | None:
    """One embedding vector, or None when embeddings are off/unavailable. Never raises.

    Always traced as ``feature="embed"`` — every caller gets automatic tracing with no code
    change (this function has exactly one purpose, unlike the multi-feature call sites)."""
    if not getattr(settings, "ASSISTANT_RAG_EMBEDDINGS", False) or not settings.GEMINI_API_KEY:
        return None
    from .services.tracing import estimate_tokens, trace_call

    with trace_call("embed", actor=actor, conversation_id=conversation_id) as handle:
        try:
            resp = get_gemini_client().models.embed_content(
                model=EMBEDDING_MODEL, contents=text[:8000],
            )
            handle.usage(provider="gemini", model=EMBEDDING_MODEL, estimated=True,
                         input_tokens=estimate_tokens(text[:8000]), output_tokens=0)
            return list(resp.embeddings[0].values)
        except Exception as exc:  # embeddings are an enhancement — search must survive their outage
            handle.fail_from_exception(exc)
            return None
