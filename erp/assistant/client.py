"""AI provider seam.

Single construction point so (a) tests monkeypatch ``get_client`` / ``get_gemini_client`` and
gates never make live calls, and (b) an install without an SDK or an API key still runs — the
assistant is optional and everything checks ``enabled()`` first.

Two providers behind the same extraction contract: Anthropic (Claude) and Google (Gemini).
``provider()`` picks by explicit ``ASSISTANT_PROVIDER`` or by whichever key is present.
"""
from __future__ import annotations

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
