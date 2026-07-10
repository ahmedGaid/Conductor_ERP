"""Circuit breaker unit tests (ai-reliability T2.3): a provider opens after enough consecutive
failures, stays open for a cooldown, then gets exactly one half-open probe."""
from __future__ import annotations

from erp.assistant.gateway import breaker


def test_closed_by_default():
    assert breaker.state("anthropic") == "closed"
    assert breaker.is_open("anthropic") is False


def test_stays_closed_below_threshold():
    for _ in range(breaker.FAILURE_THRESHOLD - 1):
        breaker.record_failure("anthropic")
    assert breaker.state("anthropic") == "closed"


def test_opens_after_threshold_consecutive_failures():
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")
    assert breaker.state("anthropic") == "open"
    assert breaker.is_open("anthropic") is True


def test_success_resets_the_failure_streak():
    for _ in range(breaker.FAILURE_THRESHOLD - 1):
        breaker.record_failure("anthropic")
    breaker.record_success("anthropic")
    for _ in range(breaker.FAILURE_THRESHOLD - 1):
        breaker.record_failure("anthropic")
    assert breaker.state("anthropic") == "closed"  # the reset streak never reached threshold again


def test_half_open_after_cooldown(monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(breaker.time, "time", lambda: clock["t"])
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("gemini")
    assert breaker.state("gemini") == "open"
    clock["t"] += breaker.COOLDOWN_S - 1
    assert breaker.state("gemini") == "open"
    clock["t"] += 2
    assert breaker.state("gemini") == "half_open"
    assert breaker.is_open("gemini") is False  # half-open lets exactly one probe through


def test_success_in_half_open_closes_the_breaker(monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(breaker.time, "time", lambda: clock["t"])
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("mistral")
    clock["t"] += breaker.COOLDOWN_S
    assert breaker.state("mistral") == "half_open"
    breaker.record_success("mistral")
    assert breaker.state("mistral") == "closed"


def test_failure_in_half_open_reopens_the_breaker(monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(breaker.time, "time", lambda: clock["t"])
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("groq")
    clock["t"] += breaker.COOLDOWN_S
    assert breaker.state("groq") == "half_open"
    breaker.record_failure("groq")  # the probe failed too
    assert breaker.state("groq") == "open"


def test_breakers_are_independent_per_provider():
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")
    assert breaker.state("anthropic") == "open"
    assert breaker.state("gemini") == "closed"
