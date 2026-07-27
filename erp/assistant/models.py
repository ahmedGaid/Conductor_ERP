"""Conversation storage for the AI workspace.

A Conversation belongs to one user (single-tenant, but conversations are private to their owner).
Messages are append-only; edits create new messages so the transcript stays honest.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ai_conversations")
    title = models.CharField(max_length=200, blank=True, default="")
    pinned = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pinned", "-updated_at"]


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField(blank=True, default="")
    # citations / tool steps / action proposals ride along as structured JSON (session 09/10 fill these)
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Attachment(models.Model):
    """A file the user attached to a chat turn (image/PDF/CSV/XLSX/JSON/XML/TXT).

    Uploaded on its own first (so the composer shows a chip while the file transfers), then *claimed*
    by the send that references it — ``message`` stays null until then. Private to its uploader; a
    claim only ever links the uploader's own still-unclaimed attachments.
    """

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments", null=True, blank=True,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to="assistant/%Y/%m/")
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class KnowledgeDocument(models.Model):
    """One uploaded company document (SOP, policy, catalog, manual) in the knowledge base.

    Ingestion is synchronous and bounded; a failure lands on the row (status=failed +
    error_text) blame-free, never as an exception to the uploader.
    """

    STATUS_CHOICES = [("processing", "processing"), ("ready", "ready"), ("failed", "failed")]

    title = models.CharField(max_length=200)
    filename = models.CharField(max_length=255)
    media_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="processing")
    error_text = models.CharField(max_length=255, blank=True, default="")
    chunk_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class KnowledgeChunk(models.Model):
    """One searchable slice of a document. ``search`` is a maintained tsvector (config
    "simple" — language-neutral, works for Arabic + English); ``embedding`` is filled only
    when ASSISTANT_RAG_EMBEDDINGS is on (session 03)."""

    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks")
    seq = models.PositiveIntegerField()
    text = models.TextField()
    search = SearchVectorField(null=True)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["document_id", "seq"]
        indexes = [GinIndex(fields=["search"])]
        constraints = [
            models.UniqueConstraint(fields=["document", "seq"], name="uniq_chunk_per_doc_seq"),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.seq}"


class Trace(models.Model):
    """One AI provider/feature call. Payload policy: sizes and outcomes only — never full
    prompts, completions, or tool result rows (see TraceStep.detail)."""

    class Feature(models.TextChoices):
        CHAT = "chat"
        ASK = "ask"
        AGENT = "agent"
        EXTRACT = "extract"
        DIGEST = "digest"
        SUGGEST = "suggest"
        EMBED = "embed"
        EVAL = "eval"
        WORKFLOW = "workflow"  # an action run as a step inside a workflow (assistant_action node)
        RERANK = "rerank"  # ai-reliability T3.5 — LLM relevance scoring over fused retrieval candidates

    class Status(models.TextChoices):
        OK = "ok"
        ERROR = "error"
        TIMEOUT = "timeout"
        CANCELLED = "cancelled"
        GUARDRAIL_BLOCKED = "guardrail_blocked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ai_traces",
    )
    feature = models.CharField(max_length=12, choices=Feature.choices)
    conversation = models.ForeignKey(
        Conversation, null=True, blank=True, on_delete=models.SET_NULL, related_name="traces",
    )
    provider = models.CharField(max_length=40, blank=True, default="")
    model = models.CharField(max_length=80, blank=True, default="")
    prompt_ref = models.CharField(max_length=120, blank=True, default="")
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)
    cost_microcents = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OK)
    error_class = models.CharField(max_length=40, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["feature", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.feature}:{self.id}"


class TraceStep(models.Model):
    """One step inside a Trace's run (llm call, tool call, retrieval, guardrail check,
    validation). ``detail`` carries sizes/flags only — never full arguments or result rows."""

    class Kind(models.TextChoices):
        LLM = "llm"
        TOOL = "tool"
        RETRIEVAL = "retrieval"
        GUARDRAIL = "guardrail"
        VALIDATION = "validation"

    trace = models.ForeignKey(Trace, on_delete=models.CASCADE, related_name="steps")
    seq = models.PositiveIntegerField()
    kind = models.CharField(max_length=12, choices=Kind.choices)
    name = models.CharField(max_length=100, blank=True, default="")
    latency_ms = models.PositiveIntegerField(default=0)
    ok = models.BooleanField(default=True)
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["trace_id", "seq"]
        indexes = [models.Index(fields=["trace", "seq"])]

    def __str__(self) -> str:
        return f"{self.trace_id}#{self.seq}:{self.kind}"


class ResponseCache(models.Model):
    """Exact-match response cache (ai-reliability T2.5): one row per unique gateway input for a
    cache-enabled task class. ``key`` hashes (task, prompt_ref, model, system, user, schema,
    media hashes); ``input_version`` snapshots the task's version counter at write time, so a
    ``gateway.cache.bump(task)`` makes every older row invisible without a delete sweep.
    ``created_at`` is set explicitly on every (re)write — TTL counts from the latest write, not
    the first insert."""

    key = models.CharField(max_length=64, unique=True)
    task = models.CharField(max_length=20)
    response = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)
    hit_count = models.PositiveIntegerField(default=0)
    input_version = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["task", "created_at"])]

    def __str__(self) -> str:
        return f"{self.task}:{self.key[:12]}"


class ResponseCacheVersion(models.Model):
    """Per-task version counter behind ``gateway.cache.bump`` — data-changing services bump it
    to invalidate every cached response for that task at once (see gateway/cache.py)."""

    task = models.CharField(max_length=20, unique=True)
    version = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.task}@v{self.version}"


class SemanticCache(models.Model):
    """Near-duplicate knowledge Q&A reuse (ai-reliability T2.8): one row per verified answer,
    scoped to the asking user — answers are permission-scoped, never shared across users in v1.
    ``knowledge_version`` snapshots ``ResponseCacheVersion(task="knowledge")`` at write time, so a
    ``knowledge.ingest_document`` bump makes older rows invisible to lookup without a delete sweep
    (same mechanism as ``ResponseCache.input_version``, see ``gateway/cache.py``)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    question_text = models.CharField(max_length=500)
    question_embedding = models.JSONField()
    answer = models.TextField()
    citations = models.JSONField(default=list)
    knowledge_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    hit_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["user", "knowledge_version"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.question_text[:30]}"


class Budget(models.Model):
    """A spend ceiling (ai-reliability T2.7): one row per scope. ``request`` is checked against a
    single call's estimated cost; ``user`` and ``org`` are checked against ``SpendRollup`` (every
    user shares the same per-user ceiling — there is no per-user override in v1, matching the
    plan's "protect against runaway, not against usage" intent). ``action`` = ``block`` raises
    ``BudgetExceeded``; ``notify`` only logs and lets the call through."""

    class Scope(models.TextChoices):
        REQUEST = "request"
        USER = "user"
        ORG = "org"

    class Action(models.TextChoices):
        BLOCK = "block"
        NOTIFY = "notify"

    scope = models.CharField(max_length=10, choices=Scope.choices, unique=True)
    limit_microcents = models.BigIntegerField()
    action = models.CharField(max_length=10, choices=Action.choices, default=Action.BLOCK)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.scope}<={self.limit_microcents}({self.action})"


class SpendRollup(models.Model):
    """Atomic running spend for a ``user`` or ``org`` scope over one period (ai-reliability T2.7).
    ``period`` is date-keyed: the calendar day for ``user`` (resets at midnight), the first of the
    month for ``org`` (resets on the 1st) — see ``gateway/budgets.py::_period_start``.
    ``scope_key`` is the user id as a string for ``user`` rows, or the constant ``"org"`` for the
    single org-wide row (single-tenant deployment — no real org id needed)."""

    scope = models.CharField(max_length=10, choices=Budget.Scope.choices)
    scope_key = models.CharField(max_length=64)
    period = models.DateField()
    spend_microcents = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scope", "scope_key", "period"],
                                    name="uniq_spend_rollup_scope_key_period"),
        ]
        indexes = [models.Index(fields=["scope", "period"])]

    def __str__(self) -> str:
        return f"{self.scope}:{self.scope_key}@{self.period}={self.spend_microcents}"
