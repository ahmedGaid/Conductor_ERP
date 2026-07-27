"""Rolling conversation summaries (ai-reliability T3.7): trigger logic, the refresh call itself
(monkeypatched, no live provider), and the fire-and-forget Celery hand-off."""
from __future__ import annotations

import pytest

from erp.assistant import tasks
from erp.assistant.models import Conversation
from erp.assistant.services import summarize
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _user(username: str = "summary_user") -> User:
    return User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test")


def _seed(conversation, n: int, *, content: str = "word " * 100) -> None:
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        conversation.messages.create(role=role, content=f"{content} {i}")


def test_should_refresh_false_below_tail_message_count():
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES)  # exactly the tail — nothing older exists yet
    assert summarize.should_refresh(conv) is False


def test_should_refresh_false_when_pending_gap_too_small():
    conv = Conversation.objects.create(user=_user())
    # A few messages older than the tail, but fewer than STALE_MESSAGE_GAP — not stale yet.
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP - 1)
    assert summarize.should_refresh(conv) is False


def test_should_refresh_false_when_pending_tokens_below_trigger():
    conv = Conversation.objects.create(user=_user())
    # Enough OLDER messages to clear the staleness gap, but each is tiny — total tokens stay low.
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP, content="hi")
    assert summarize.should_refresh(conv) is False


def test_should_refresh_true_when_stale_and_over_token_trigger():
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP)  # ~500-char messages
    assert summarize.should_refresh(conv) is True


def test_should_refresh_only_counts_messages_after_summary_upto():
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP)
    older = list(conv.messages.order_by("id"))[:-summarize.TAIL_MESSAGES]
    # Already summarized up to the last "older" message — nothing new pending, even though the
    # raw older bucket is the same size as the case above.
    conv.summary = "prior summary"
    conv.summary_upto_message = older[-1]
    conv.save()
    assert summarize.should_refresh(conv) is False


def test_refresh_summary_calls_model_and_persists(monkeypatch):
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP)
    older = list(conv.messages.order_by("id"))[:-summarize.TAIL_MESSAGES]

    captured = {}

    def fake_complete_json(system, user, schema, **kwargs):
        captured["system"] = system
        captured["feature"] = kwargs.get("feature")
        return {"summary": "the user asked about SO-1042 and is waiting on a reply"}

    monkeypatch.setattr(summarize, "complete_json", fake_complete_json)
    summarize.refresh_summary(conv)

    conv.refresh_from_db()
    assert conv.summary == "the user asked about SO-1042 and is waiting on a reply"
    assert conv.summary_upto_message_id == older[-1].id
    assert captured["feature"] == "digest"
    # The prompt actually carried the pending turns' content verbatim, not just a placeholder.
    assert older[0].content in captured["system"]
    assert older[-1].content in captured["system"]


def test_refresh_summary_no_op_when_nothing_pending():
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES)  # nothing older than the tail
    summarize.refresh_summary(conv)  # would raise if it tried to call the model with no pending
    conv.refresh_from_db()
    assert conv.summary == ""
    assert conv.summary_upto_message_id is None


def test_refresh_summary_keeps_prior_summary_on_provider_failure(monkeypatch):
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP)
    conv.summary = "old summary"
    conv.save()

    def boom(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(summarize, "complete_json", boom)
    summarize.refresh_summary(conv)  # must not raise

    conv.refresh_from_db()
    assert conv.summary == "old summary"
    assert conv.summary_upto_message_id is None


def test_maybe_trigger_enqueues_when_due(monkeypatch):
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP)

    calls = []
    monkeypatch.setattr(tasks.refresh_thread_summary, "delay", lambda cid: calls.append(cid))
    summarize.maybe_trigger(conv)
    assert calls == [conv.id]


def test_maybe_trigger_does_nothing_when_not_due(monkeypatch):
    conv = Conversation.objects.create(user=_user())
    _seed(conv, 3)  # far below the tail — nothing to summarize

    calls = []
    monkeypatch.setattr(tasks.refresh_thread_summary, "delay", lambda cid: calls.append(cid))
    summarize.maybe_trigger(conv)
    assert calls == []


def test_refresh_thread_summary_task_runs_real_refresh(monkeypatch):
    conv = Conversation.objects.create(user=_user())
    _seed(conv, summarize.TAIL_MESSAGES + summarize.STALE_MESSAGE_GAP)
    monkeypatch.setattr(summarize, "complete_json",
                        lambda *a, **k: {"summary": "task-driven summary"})

    ok = tasks.refresh_thread_summary(conv.id)

    assert ok is True
    conv.refresh_from_db()
    assert conv.summary == "task-driven summary"


def test_refresh_thread_summary_task_missing_conversation_returns_false():
    assert tasks.refresh_thread_summary(999999) is False
