"""The AI gateway (Phase 2, T2.1): the ONLY module that calls ``client.py``.

Every service (``ask``, ``agent``, ``imports``, ``knowledge``, …) gets its provider access through
``complete_json`` / ``complete_stream`` / ``embed_text`` here instead of importing ``client``
directly — one front door for routing, retries, failover and caching to land in later T2.x tasks
without touching every caller again. ``client.py`` stays the raw provider seam (SDK calls, the
per-provider runners); this module owns the provider-chain dispatch loop and the traced seam
(``trace_call`` wrapping lives in exactly one place: here).

v1 (T2.1) is a pure relocation of ``services.llm.complete_json`` and ``client.complete_stream``:
behavior is byte-identical, no routing table yet — ``feature`` is today's stand-in for the "task
class" the architecture doc describes; T2.3/T2.4 formalize it into ``ASSISTANT_ROUTING``.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable

from django.conf import settings

from ..client import (
    _anthropic_media_block,
    _groq_media_block,
    _STREAM_RUNNERS,
    embed_text,
    gemini_http_options,
    get_client,
    get_gemini_client,
    groq_chat,
    mistral_chat,
    model_id,
    provider,
    provider_chain,
)
from . import breaker, budgets, cache, retry
from ..errors import AllProvidersDown, AssistantUnavailableError, BudgetExceeded, classify_exception

__all__ = ["complete_json", "complete_stream", "embed_text", "model_id", "provider",
           "provider_chain"]


# --- JSON completion (moved from services.llm) --------------------------------------------------

def _schema_hint(schema: dict) -> str:
    # Groq is JSON-object mode only (no schema param) — spell the shape out in the prompt instead.
    return " Respond with a single JSON object only, no prose, matching this schema: " + json.dumps(schema)


def _anthropic(system: str, user: str, schema: dict, media: list | None = None,
               model: str | None = None, timeout: float | None = None) -> str:
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
        **({"timeout": timeout} if timeout is not None else {}),
    )
    if getattr(resp, "stop_reason", None) not in ("end_turn", None):
        return ""
    return next((b.text for b in resp.content if b.type == "text"), "")


def _gemini(system: str, user: str, schema: dict, media: list | None = None,
            model: str | None = None, timeout: float | None = None) -> str:
    from google.genai import types

    # Lazy: reuse the strict→Gemini schema translation without importing the services package at
    # module load (services/__init__ imports agent, which imports this module back).
    from ..services.extraction import _gemini_schema

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
    http_options = gemini_http_options(timeout)  # per-call, not on the Client — see get_gemini_client
    if http_options is not None:
        cfg["http_options"] = http_options
    parts = [types.Part.from_bytes(data=m["data"], mime_type=m["media_type"]) for m in (media or [])]
    gen_config = types.GenerateContentConfig(**cfg)

    # A defensive retry-with-fresh-client stays here in case the SDK's own httpx transport ever
    # goes stale mid-process for an unrelated reason (idle connection reuse, etc) — cheap, and
    # gateway.retry classifies this message as retryable too for the provider-chain backoff loop.
    try:
        resp = get_gemini_client().models.generate_content(
            model=model or model_id("gemini"), contents=[*parts, user], config=gen_config,
        )
    except RuntimeError as exc:
        if "client has been closed" not in str(exc).lower():
            raise
        resp = get_gemini_client().models.generate_content(
            model=model or model_id("gemini"), contents=[*parts, user], config=gen_config,
        )
    return getattr(resp, "text", "") or ""


def _openai_compatible(chat, api_key_provider: str, system: str, user: str, schema: dict,
                       media: list | None, model: str | None,
                       timeout: float | None = None) -> str:
    """Shared JSON path for the OpenAI-compatible providers (Groq, Mistral): a vision image block per
    media item, the schema spelled into the system prompt (json-object mode only), one chat call."""
    blocks = [b for b in ((_groq_media_block(m)) for m in (media or [])) if b is not None]
    user_content = [{"type": "text", "text": user}, *blocks] if blocks else user
    body = chat(
        [{"role": "system", "content": system + _schema_hint(schema)},
         {"role": "user", "content": user_content}],
        model=model or model_id(api_key_provider), max_tokens=settings.ASSISTANT_MAX_TOKENS,
        timeout=timeout or 60.0,
    )
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _groq(system: str, user: str, schema: dict, media: list | None = None,
          model: str | None = None, timeout: float | None = None) -> str:
    return _openai_compatible(groq_chat, "groq", system, user, schema, media, model, timeout)


def _mistral(system: str, user: str, schema: dict, media: list | None = None,
             model: str | None = None, timeout: float | None = None) -> str:
    return _openai_compatible(mistral_chat, "mistral", system, user, schema, media, model, timeout)


_RUNNERS = {"anthropic": _anthropic, "gemini": _gemini, "groq": _groq, "mistral": _mistral}


def _task_timeout(feature: str | None) -> float:
    """The SDK timeout ceiling (seconds) for a task class (T2.2) — an unlisted or missing
    ``feature`` (untraced calls, e.g. the agent loop) falls back to the settings default."""
    timeouts = getattr(settings, "ASSISTANT_TASK_TIMEOUTS", {})
    default = getattr(settings, "ASSISTANT_DEFAULT_TIMEOUT_S", 60)
    return timeouts.get(feature, default)


def complete_json(system: str, user: str, schema: dict, *, media: list | None = None,
                  retries: int = retry.MAX_RETRIES + 1, feature: str | None = None, actor=None,
                  conversation_id=None, prompt_ref: str = "") -> dict:
    """One prompt → one parsed JSON dict, failing over across the provider chain.

    ``media`` (optional) is a list of ``{"media_type", "data": bytes}`` (see services.files) —
    images/PDF injected into the user turn so a vision-capable provider reads them while it decides
    (the agent planner passes attachments here so "create a PO from the attached image" extracts real
    lines instead of guessing). Each provider in ``provider_chain()`` is retried a few times with a
    short backoff (free-tier keys have low per-minute limits); if it still fails, or returns empty /
    unparseable output, the next available provider is tried. Raises ``AllProvidersDown``
    (blame-free, retryable — subclasses ``AssistantUnavailableError``) only when every provider is
    exhausted or breaker-open (T2.3).

    ``feature`` (optional) opens a trace for this call — omit it and the call is untraced,
    exactly as before (see ``services.tracing``).
    """
    from ..services.tracing import estimate_tokens, null_trace, trace_call

    cm = (trace_call(feature, actor=actor, conversation_id=conversation_id, prompt_ref=prompt_ref)
          if feature else null_trace())
    timeout_s = _task_timeout(feature)
    with cm as handle:
        last_exc: Exception | None = None
        chain = provider_chain()
        # T2.5: deterministic system tasks (settings allowlist; chat/agent_*/extract hard-denied
        # in gateway/cache.py) check the exact-match cache before any provider is tried. The key
        # hashes the full input against the chain head's model — the routing intent, computed
        # before breaker filtering so the key is stable across transient outages. A hit is a real
        # answer at cost 0; the step marker makes the hit rate visible in ops.
        cache_key = (cache.make_key(feature, prompt_ref, model_id(chain[0]), system, user,
                                    schema, media)
                     if cache.enabled(feature) else None)
        if cache_key is not None:
            cached = cache.get(feature, cache_key)
            if cached is not None:
                handle.step(kind="llm", name="cache", detail={"cache": "exact"})
                handle.usage(provider="cache")
                return cached
        # T2.7: a cache miss (or an uncached task) is about to cost real money — check the
        # request/user-day/org-month budgets against the estimated cost of the chain head's model
        # before any provider is tried. A cache hit above never reaches here (correctly free).
        estimated_cost = budgets.estimate_cost_microcents(
            model_id(chain[0]), estimate_tokens(system + user), settings.ASSISTANT_MAX_TOKENS)
        try:
            budgets.check(estimated_cost=estimated_cost, actor=actor)
        except BudgetExceeded:
            handle.fail("budget_exceeded")
            raise
        # T2.3: a provider with 5 consecutive retryable failures in the last 60s is skipped for a
        # 30s cooldown rather than tried again (gateway/breaker.py). ``routing`` is a local dict
        # mutated in place as the walk progresses; it's only attached to the trace (handle.meta)
        # when this call is traced, so an untraced call never writes into the shared null handle.
        usable = [p for p in chain if not breaker.is_open(p)]
        skipped: list[dict] = [{"provider": p, "reason": "breaker_open"} for p in chain if p not in usable]
        routing = {"chain": chain, "chosen": None, "skipped": skipped}
        if feature:
            handle.meta["routing"] = routing
        if not usable:
            handle.fail("provider_error")
            raise AllProvidersDown(data={"reason": "all_providers_breaker_open"})
        for i, prov in enumerate(usable):
            runner = _RUNNERS.get(prov, _anthropic)
            model = model_id(prov)
            # Fail fast while a fallback remains: a provider that is down should hand off
            # immediately, not burn the whole retry+backoff budget first. Only the LAST provider
            # (no fallback left) gets the full retries — that's where waiting out a transient
            # rate-limit is worth it. Within that budget, only errors retry.is_retryable() calls
            # transient (429/5xx/connection/timeout) get a backoff+retry — a permanent error
            # (401/403/400) fails this provider immediately (T2.2).
            attempts = retries if i == len(usable) - 1 else 1
            text = ""
            succeeded = False
            provider_exc: Exception | None = None
            for attempt in range(attempts):
                _t0 = time.monotonic()
                try:
                    text = runner(system, user, schema, media, model, timeout=timeout_s)
                    succeeded = True
                    break
                except Exception as exc:  # network / auth / rate-limit — maybe retry, then fail over
                    last_exc = exc
                    provider_exc = exc
                    latency_ms = int((time.monotonic() - _t0) * 1000)
                    error_class = classify_exception(exc)
                    if attempt < attempts - 1 and retry.is_retryable(exc):
                        handle.step(kind="llm", name=prov, ok=False, latency_ms=latency_ms,
                                    detail={"retry": attempt + 1, "error_class": error_class})
                        time.sleep(retry.backoff_seconds(attempt))
                        continue
                    handle.step(kind="llm", name=prov, ok=False, latency_ms=latency_ms,
                                detail={"error_class": error_class, "final": True})
                    break
            if not succeeded:
                # Only a retryable exception counts toward the breaker — a bad key or malformed
                # request isn't an outage, and retrying it later would never help either.
                if provider_exc is not None and retry.is_retryable(provider_exc):
                    breaker.record_failure(prov)
                skipped.append({"provider": prov,
                                "reason": classify_exception(provider_exc) if provider_exc else "error"})
                continue  # this provider exhausted its attempts (or hit a permanent error)
            if not text:
                last_exc = AssistantUnavailableError(data={"reason": "empty_model_output"})
                skipped.append({"provider": prov, "reason": "empty_output"})
                continue  # empty output — try the next provider rather than fail outright
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                last_exc = exc  # garbage JSON — try the next provider
                skipped.append({"provider": prov, "reason": "invalid_json"})
                continue
            breaker.record_success(prov)
            routing["chosen"] = prov
            handle.usage(provider=prov, model=model, estimated=True,
                         input_tokens=estimate_tokens(system + user),
                         output_tokens=estimate_tokens(text))
            if cache_key is not None:
                cache.put(feature, cache_key, parsed)
            return parsed
        if last_exc is not None:
            # Classify the real failure (e.g. "timeout", "rate_limited") onto the trace before it
            # gets wrapped into the blame-free error below — trace_call won't overwrite a
            # handle.error_class that's already set (see services.tracing.trace_call).
            handle.fail_from_exception(last_exc)
        else:
            handle.fail("provider_error")
        raise AllProvidersDown(
            data={"reason": last_exc.__class__.__name__ if last_exc else "no_provider"}) from last_exc


# --- streaming completion (moved from client.py) -------------------------------------------------

_CONTINUE_INSTRUCTION = (
    "Continue your answer from exactly where you left off. Do not repeat any earlier text or "
    "acknowledge the interruption."
)


def complete_stream(messages: list, *, system: str | None = None, media: list | None = None,
                    feature: str | None = None, actor=None, conversation_id=None,
                    prompt_ref: str = "", on_retry: Callable[[], None] | None = None):
    """Yield answer text chunks, failing over across the provider chain.

    Each provider is tried in ``provider_chain()`` order; if one raises *before* its first token (down
    / auth / rate-limit) the next is tried. ``media`` is a list of ``{"media_type", "data": bytes}``
    injected into the user turn for a vision provider.

    ``feature`` (optional) opens a trace for this call, recording TTFT and total latency; token
    counts are estimated (see ``services.tracing.estimate_tokens`` — these providers' streaming
    paths don't return usage, only the final non-streamed call does). Omit ``feature`` and the
    call is untraced, exactly as before.

    Zero-byte failures (before any token is yielded) get the same retry.is_retryable() backoff
    budget as ``complete_json`` — only the last provider in the chain, per the same fail-fast-while-
    a-fallback-remains rule (T2.2).

    T2.6: a failure *after* the first token (mid-stream) no longer ends the answer while a
    provider remains. It's recorded as a TraceStep, ``on_retry()`` fires if given (a client-facing
    caller uses it to surface a calm "retrying" notice; a caller that doesn't stream to a network
    client may omit it), and the turn restarts on the next usable provider with the partial folded
    in as an assistant turn plus an instruction to continue without repeating or narrating the
    interruption. ``handle.meta["stream_recovered"]`` marks a trace that needed this. Exhausting
    every remaining provider mid-stream still ends the answer — the partial already yielded is the
    caller's to persist, same as before.
    """
    from ..services.tracing import estimate_tokens, null_trace, trace_call

    cm = (trace_call(feature, actor=actor, conversation_id=conversation_id, prompt_ref=prompt_ref)
          if feature else null_trace())
    timeout_s = _task_timeout(feature)
    with cm as handle:
        out_parts: list[str] = []
        last_exc: Exception | None = None
        chain = provider_chain()
        # T2.7: same pre-call budget gate as complete_json — no cache to check first here (the
        # stream path is never cache-eligible), so this runs right after the chain is known.
        stream_input_text = (system or "") + "".join(
            m.get("content", "") for m in messages if isinstance(m.get("content"), str))
        estimated_cost = budgets.estimate_cost_microcents(
            model_id(chain[0]), estimate_tokens(stream_input_text), settings.ASSISTANT_MAX_TOKENS)
        try:
            budgets.check(estimated_cost=estimated_cost, actor=actor)
        except BudgetExceeded:
            handle.fail("budget_exceeded")
            raise
        # T2.3: same breaker skip/record as complete_json — see the comment there.
        usable = [p for p in chain if not breaker.is_open(p)]
        skipped: list[dict] = [{"provider": p, "reason": "breaker_open"} for p in chain if p not in usable]
        routing = {"chain": chain, "chosen": None, "skipped": skipped}
        if feature:
            handle.meta["routing"] = routing
        if not usable:
            handle.fail("provider_error")
            raise AllProvidersDown(data={"reason": "all_providers_breaker_open"})
        turn_messages = messages
        recovering = False
        i = 0
        while i < len(usable):
            prov = usable[i]
            runner = _STREAM_RUNNERS.get(prov, _STREAM_RUNNERS["anthropic"])
            attempts = retry.MAX_RETRIES + 1 if i == len(usable) - 1 else 1
            first = None
            gen = None
            empty = False
            provider_exc: Exception | None = None
            for attempt in range(attempts):
                _t0 = time.monotonic()
                gen = runner(turn_messages, system, media, prov, timeout=timeout_s)
                try:
                    first = next(gen)
                    break
                except StopIteration:
                    empty = True
                    break  # provider succeeded but produced nothing — an empty answer, not a failure
                except Exception as exc:  # provider down before any token — maybe retry, then fail over
                    last_exc = exc
                    provider_exc = exc
                    first = None
                    latency_ms = int((time.monotonic() - _t0) * 1000)
                    error_class = classify_exception(exc)
                    if attempt < attempts - 1 and retry.is_retryable(exc):
                        handle.step(kind="llm", name=prov, ok=False, latency_ms=latency_ms,
                                    detail={"retry": attempt + 1, "error_class": error_class})
                        time.sleep(retry.backoff_seconds(attempt))
                        continue
                    handle.step(kind="llm", name=prov, ok=False, latency_ms=latency_ms,
                                detail={"error_class": error_class, "final": True})
                    break
            if empty:
                breaker.record_success(prov)  # the provider responded, just produced nothing
                routing["chosen"] = prov
                return
            if first is None:
                if provider_exc is not None and retry.is_retryable(provider_exc):
                    breaker.record_failure(prov)
                skipped.append({"provider": prov,
                                "reason": classify_exception(provider_exc) if provider_exc else "error"})
                i += 1
                continue  # this provider exhausted its attempts (or hit a permanent error)
            breaker.record_success(prov)
            routing["chosen"] = prov
            handle.usage(provider=prov, model=model_id(prov))
            handle.mark_ttft()
            if recovering:
                handle.step(kind="llm", name=prov, ok=True, detail={"recovered": True})
                recovering = False
            out_parts.append(first)
            yield first
            try:
                for chunk in gen:
                    out_parts.append(chunk)
                    yield chunk
            except Exception as exc:  # mid-stream failure — recover onto the next provider (T2.6)
                error_class = classify_exception(exc)
                handle.step(kind="llm", name=prov, ok=False,
                            detail={"error_class": error_class, "mid_stream": True})
                if i + 1 >= len(usable):
                    handle.fail_from_exception(exc)
                    raise AllProvidersDown(data={"reason": exc.__class__.__name__}) from exc
                handle.meta["stream_recovered"] = True
                if on_retry is not None:
                    try:
                        on_retry()
                    except Exception:
                        pass
                turn_messages = messages + [
                    {"role": "assistant", "content": "".join(out_parts)},
                    {"role": "user", "content": _CONTINUE_INSTRUCTION},
                ]
                recovering = True
                i += 1
                continue
            input_text = (system or "") + "".join(
                m.get("content", "") for m in messages if isinstance(m.get("content"), str))
            handle.usage(estimated=True, input_tokens=estimate_tokens(input_text),
                         output_tokens=estimate_tokens("".join(out_parts)))
            return
        if last_exc is not None:
            handle.fail_from_exception(last_exc)  # classify the real failure before the wrap below
        else:
            handle.fail("provider_error")
        raise AllProvidersDown(
            data={"reason": last_exc.__class__.__name__ if last_exc else "no_provider"})


# ``embed_text`` has no provider chain (Gemini-only) and is already one small monkeypatchable seam
# on ``client`` — re-exported here (see ``__all__``) so ``gateway.embed_text`` exists per the T2.1
# goal; callers may keep going through ``client.embed_text`` directly until they migrate (tracked:
# ``services.knowledge`` still does, since its tests patch ``knowledge.client.embed_text``).
