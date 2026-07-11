"""Tracing seam: every provider call self-reports to Trace/TraceStep without changing any
caller's behavior.

One ``trace_call(feature, ...)`` context manager wraps a call site; the yielded ``TraceHandle``
collects usage/steps as the call runs, and the Trace row (+ any TraceSteps) is written on exit.
If tracing itself fails (DB down, bug in this module), the AI call it observes must still
succeed — same philosophy as ``client.embed_text``'s try/except. Every handle method and the
final write are wrapped so a tracing bug can never propagate into a caller.
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager

from .. import models as assistant_models
from ..errors import classify_exception

logger = logging.getLogger(__name__)

# Taxonomy buckets (ai-reliability T1.9) that get their own Trace.Status rather than the generic
# ERROR — everything else classify_exception returns still lands on Trace.Status.ERROR.
_STATUS_BY_ERROR_CLASS = {
    "timeout": assistant_models.Trace.Status.TIMEOUT,
    "cancelled": assistant_models.Trace.Status.CANCELLED,
    "guardrail_blocked": assistant_models.Trace.Status.GUARDRAIL_BLOCKED,
}

# model id -> (input microcents per 1K tokens, output microcents per 1K tokens). Unknown models
# cost 0 and set meta.cost_unknown=true rather than guessing.
PRICING: dict[str, tuple[int, int]] = {
    "claude-opus-4-8": (1_500, 7_500),
    "gemini-2.5-flash": (30, 250),
    "mistral-small-latest": (100, 300),
    "meta-llama/llama-4-scout-17b-16e-instruct": (11, 34),
    "text-embedding-004": (1, 0),
}


def estimate_tokens(text: str) -> int:
    """Heuristic fallback when a provider doesn't return usage — documented as approximate for
    Arabic-heavy text (FILE_01 decision point)."""
    return max(1, len(text or "") // 3)


def _cost_microcents(model: str, input_tokens: int, output_tokens: int) -> tuple[int, bool]:
    price = PRICING.get(model)
    if not price:
        return 0, True
    in_price, out_price = price
    cost = round(input_tokens * in_price / 1000 + output_tokens * out_price / 1000)
    return cost, False


class TraceHandle:
    """Mutable recorder passed into a traced call site. Every method swallows its own errors —
    a tracing bug must never break the AI call it's observing."""

    def __init__(self, feature: str, *, actor=None, conversation_id=None, prompt_ref: str = ""):
        self.feature = feature
        self.actor = actor
        self.conversation_id = conversation_id
        self.prompt_ref = prompt_ref
        self.provider = ""
        self.model = ""
        self.input_tokens = 0
        self.output_tokens = 0
        self.tokens_estimated = False
        self.status = assistant_models.Trace.Status.OK
        self.error_class = ""
        self.meta: dict = {}
        self.steps: list[dict] = []
        self._start = time.monotonic()
        self._ttft_recorded = False

    def usage(self, *, provider: str = "", model: str = "", input_tokens: int | None = None,
              output_tokens: int | None = None, estimated: bool = False) -> None:
        try:
            if provider:
                self.provider = provider
            if model:
                self.model = model
            if input_tokens is not None:
                self.input_tokens = input_tokens
            if output_tokens is not None:
                self.output_tokens = output_tokens
            if estimated:
                self.tokens_estimated = True
        except Exception:
            logger.exception("tracing: usage() failed")

    def mark_ttft(self) -> None:
        """Record time-to-first-token, once, in ``meta.ttft_ms``."""
        try:
            if not self._ttft_recorded:
                self._ttft_recorded = True
                self.meta["ttft_ms"] = int((time.monotonic() - self._start) * 1000)
        except Exception:
            logger.exception("tracing: mark_ttft() failed")

    def fail(self, error_class: str, *, status: str = assistant_models.Trace.Status.ERROR) -> None:
        """Record a failure the caller is handling itself (e.g. swallowed for a blame-free
        fallback) — use when the exception won't propagate through ``trace_call``'s own except."""
        try:
            self.status = status
            self.error_class = error_class
        except Exception:
            logger.exception("tracing: fail() failed")

    def fail_from_exception(self, exc: BaseException) -> None:
        """Same as ``fail()`` but classifies a real exception through the closed taxonomy
        (``errors.classify_exception``) instead of taking a caller-chosen string — use when a
        call site catches its own exception (e.g. an optional enhancement degrading gracefully)
        rather than letting it propagate through ``trace_call``'s own except block."""
        try:
            error_class = classify_exception(exc)
            self.status = _STATUS_BY_ERROR_CLASS.get(error_class, assistant_models.Trace.Status.ERROR)
            self.error_class = error_class
            self.meta.setdefault("raw_error_class", exc.__class__.__name__)
        except Exception:
            logger.exception("tracing: fail_from_exception() failed")

    def step(self, *, kind: str, name: str = "", ok: bool = True, detail: dict | None = None,
             latency_ms: int = 0) -> None:
        try:
            self.steps.append(
                {"kind": kind, "name": name, "ok": ok, "detail": detail or {},
                 "latency_ms": latency_ms}
            )
        except Exception:
            logger.exception("tracing: step() failed")


class _NullHandle:
    """No-op stand-in used when a call site has no ``feature`` (tracing off for that call)."""

    def usage(self, **kw):
        pass

    def mark_ttft(self):
        pass

    def fail(self, *a, **kw):
        pass

    def fail_from_exception(self, *a, **kw):
        pass

    def step(self, **kw):
        pass


@contextmanager
def trace_call(feature: str, *, actor=None, conversation_id=None, prompt_ref: str = ""):
    """Wrap one AI call. Yields a ``TraceHandle``; writes exactly one Trace row (+ TraceSteps) on
    exit, success or failure. Never raises from its own bookkeeping — only re-raises the
    caller's original exception, unchanged."""
    handle = TraceHandle(feature, actor=actor, conversation_id=conversation_id, prompt_ref=prompt_ref)
    try:
        yield handle
    except Exception as exc:
        # A call site that already classified its own failure via handle.fail()/fail_from_exception()
        # before re-raising a different, typed exception (T2.2: complete_json/complete_stream re-raise
        # the real provider error as a blame-free AssistantUnavailableError) wins — don't clobber the
        # specific reason with a generic classification of the wrapper exception.
        if not handle.error_class:
            error_class = classify_exception(exc)
            handle.status = _STATUS_BY_ERROR_CLASS.get(error_class, assistant_models.Trace.Status.ERROR)
            handle.error_class = error_class
            handle.meta.setdefault("raw_error_class", exc.__class__.__name__)
        raise
    finally:
        _write(handle)


def mark_cancelled(handle: TraceHandle) -> None:
    """Flag a handle as cancelled — for callers that intercept ``GeneratorExit`` themselves and
    call the ``trace_call`` context manager's ``__exit__`` directly (see ``services.agent.run``),
    bypassing ``trace_call``'s own except block above."""
    handle.status = assistant_models.Trace.Status.CANCELLED
    handle.error_class = "cancelled"


NULL_HANDLE = _NullHandle()  # stateless — safe to share as a default "tracing off" handle


@contextmanager
def null_trace():
    yield NULL_HANDLE


def _write(handle: TraceHandle) -> None:
    try:
        latency_ms = int((time.monotonic() - handle._start) * 1000)
        cost, cost_unknown = _cost_microcents(handle.model, handle.input_tokens, handle.output_tokens)
        meta = dict(handle.meta)
        if handle.tokens_estimated:
            meta["tokens_estimated"] = True
        if cost_unknown and handle.model:
            meta["cost_unknown"] = True
        trace = assistant_models.Trace.objects.create(
            actor=handle.actor, feature=handle.feature, conversation_id=handle.conversation_id,
            provider=handle.provider, model=handle.model, prompt_ref=handle.prompt_ref,
            input_tokens=handle.input_tokens, output_tokens=handle.output_tokens,
            latency_ms=latency_ms, cost_microcents=cost, status=handle.status,
            error_class=handle.error_class, meta=meta,
        )
        if handle.steps:
            assistant_models.TraceStep.objects.bulk_create(
                assistant_models.TraceStep(
                    trace=trace, seq=i, kind=s["kind"], name=s["name"], ok=s["ok"],
                    detail=s["detail"], latency_ms=s["latency_ms"],
                )
                for i, s in enumerate(handle.steps)
            )
        if cost:
            # T2.7: lazy import — gateway/core.py imports this module's functions lazily to avoid
            # the reverse circular import, so budgets closes the loop the same way here.
            from ..gateway import budgets as gateway_budgets

            gateway_budgets.record_spend(actor=handle.actor, cost_microcents=cost)
    except Exception:
        logger.exception("tracing: write failed — AI call unaffected")
