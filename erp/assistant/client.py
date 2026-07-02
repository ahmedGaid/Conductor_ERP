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
}


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
    # Flag forced on with no key (tests, dry setups): keep a deterministic path.
    return "anthropic"


def model_id() -> str:
    return settings.ASSISTANT_MODEL or DEFAULT_MODELS[provider()]


def get_client():
    import anthropic  # deferred: package is only needed when this provider is active

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def get_gemini_client():
    from google import genai  # deferred: package is only needed when this provider is active

    return genai.Client(api_key=settings.GEMINI_API_KEY)
