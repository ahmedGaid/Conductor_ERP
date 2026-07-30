"""Assistant memory (ai-reliability Phase 4): the one door in and the one door out.

Nothing else in the codebase writes ``UserMemory``/``OrgMemory`` — ``tests/test_memory_write_path.py``
is an AST invariant that fails the build if another module imports those models to write them. Every
write here is governed:

- **whitelist only** — ``explicit`` (the user asked, through a confirm card), ``pattern`` (a
  deterministic detector proposed it, the user confirmed the card), ``settings`` (the Memory page).
  There is NO path from raw chat content to a memory row, so a knowledge chunk or uploaded file
  saying "remember that…" cannot write anything (see ``tests/test_memory_leakage.py``).
- **audited** — ``remember``/``forget`` both call ``audit.record``; ``forget`` records the event
  without the content, since forgetting must actually forget.
- **scoped** — ``recall`` only ever reads the actor's own rows plus org rows. No global memory.

Slots vs facts: a slot is one value under an enumerated key (``SLOT_KEYS``) that deterministically
decides behaviour; a fact is a short sentence recalled by similarity. Superseding keeps history —
a new slot value never overwrites the old row.
"""
from __future__ import annotations

import json
from datetime import timedelta

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from erp.audit import services as audit
from erp.core.errors import ValidationError
from erp.identity.roles import SYSTEM_ADMIN

from ..gateway import core as gateway
from ..models import (
    Message,
    MemoryKind,
    MemorySource,
    OrgMemory,
    SemanticCache,
    UserMemory,
)
from .knowledge import _cosine  # same similarity maths retrieval already uses — one definition
from .tracing import estimate_tokens

SCOPE_USER = "user"
SCOPE_ORG = "org"
SCOPES = (SCOPE_USER, SCOPE_ORG)

# The enumerated slots. Adding one is a deliberate act: a slot changes behaviour, so it needs a
# reader somewhere (envelope line, default, digest schedule) before it earns a key here.
SLOT_KEYS: dict[str, str] = {
    "language": "preferred reply language",
    "number_format": "preferred number rendering",
    "default_branch": "branch code to assume when none is given",
    "default_warehouse": "warehouse code to assume when none is given",
    "digest_time": "local time of day for the daily digest (HH:MM)",
}

# Slots whose value is a closed set — anything else is a typo, not a preference.
_SLOT_ENUMS: dict[str, set[str]] = {
    "language": {"ar", "en"},
    "number_format": {"arabic", "western"},
}

# A remembered sentence is a sentence, not a document: long enough for real context, short enough
# that ten of them never dominate the envelope.
MAX_VALUE_CHARS = 300

# Internal control rows (proposal suppression + the one-a-day throttle) live in the same table so
# they expire with the same machinery, but they are never recalled and never shown on the Memory
# page — a reserved ``_`` key namespace marks them.
_CONTROL_PREFIX = "_"
_SUPPRESS_DAYS = 90
_PROPOSAL_THROTTLE = timedelta(days=1)

# Pattern detectors (T4.3) need this many repeats before they say anything at all.
PATTERN_MIN_OCCURRENCES = 3
PATTERN_WINDOW = timedelta(days=30)

# Confirmed-proposal payload key → the slot it maps to. Only these are slot-mappable; a payload
# field with no slot is not a preference, it's an argument.
_PAYLOAD_SLOT_MAP: dict[str, str] = {
    "warehouse_code": "default_warehouse",
    "branch_code": "default_branch",
}

# Deterministic language-correction markers (T4.3 detector b) — the user telling the assistant
# which language to answer in, in either language. No model call decides this.
_LANGUAGE_CORRECTIONS: dict[str, tuple[str, ...]] = {
    "ar": ("بالعربي", "بالعربية", "اجب بالعربية", "جاوب بالعربي", "answer in arabic",
           "reply in arabic", "in arabic please"),
    "en": ("بالانجليزي", "بالإنجليزي", "بالانجليزية", "answer in english", "reply in english",
           "in english please"),
}


class MemoryNotFound(LookupError):
    """No such memory row for this actor — indistinguishable from absent, like every other
    out-of-scope record in Conductor."""


def _is_admin(actor) -> bool:
    if not getattr(actor, "is_authenticated", False):
        return False
    if getattr(actor, "is_superuser", False):
        return True
    return SYSTEM_ADMIN in set(getattr(actor, "roles", ()) or ())


def _clean_value(value: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValidationError("There is nothing to remember.")
    if len(text) > MAX_VALUE_CHARS:
        raise ValidationError("That is too long to remember. Keep it to one short sentence.",
                              data={"max_chars": MAX_VALUE_CHARS})
    return text


def _validate_slot(key: str, value: str) -> None:
    if key not in SLOT_KEYS:
        raise ValidationError("That is not something the assistant keeps as a setting.",
                              data={"known_slots": sorted(SLOT_KEYS)})
    allowed = _SLOT_ENUMS.get(key)
    if allowed is not None and value not in allowed:
        raise ValidationError("That value isn't one of the accepted options.",
                              data={"slot": key, "allowed": sorted(allowed)})


def _embed(text: str) -> list[float] | None:
    """Best-effort embedding for a fact. Fails open: without a vector the fact is still
    remembered, it just can't be similarity-ranked (recall falls back to recency)."""
    try:
        return gateway.embed_text(text)
    except Exception:  # provider off/unavailable — never block a write the user confirmed
        return None


def _active(queryset):
    now = timezone.now()
    return queryset.filter(superseded_by__isnull=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now))


def _visible_facts(queryset):
    """Active facts a human would recognise — control rows excluded."""
    return _active(queryset).filter(kind=MemoryKind.FACT).exclude(key__startswith=_CONTROL_PREFIX)


# --- write path ---------------------------------------------------------------------------------

@transaction.atomic
def remember(actor, *, scope: str, kind: str, value: str, key: str = "",
             source: str = MemorySource.EXPLICIT) -> UserMemory | OrgMemory:
    """Write one memory. The ONLY write path (invariant-tested).

    Slots supersede their previous value (history preserved through ``superseded_by``); facts are
    appended and embedded. Org scope requires an admin — a non-admin asking to write org memory is
    refused, not silently downgraded to personal.
    """
    if scope not in SCOPES:
        raise ValidationError("Memory is either personal or organization-wide.")
    if kind not in (MemoryKind.SLOT, MemoryKind.FACT):
        raise ValidationError("A memory is either a setting or a fact.")
    if source not in MemorySource.values:
        raise ValidationError("Unknown memory source.")
    if scope == SCOPE_ORG and not _is_admin(actor):
        raise PermissionError("Only a System Admin can write organization memory.")
    text = _clean_value(value)
    key = (key or "").strip()
    if kind == MemoryKind.SLOT:
        _validate_slot(key, text)
    elif key and not key.startswith(_CONTROL_PREFIX):
        raise ValidationError("A remembered fact has no setting name.")

    model = UserMemory if scope == SCOPE_USER else OrgMemory
    extra = {"user": actor} if scope == SCOPE_USER else {"written_by": actor}
    embedding = _embed(text) if kind == MemoryKind.FACT and not key else None

    superseded: list[int] = []
    if kind == MemoryKind.SLOT:
        # Retire the older active rows BEFORE inserting the new one — the unique-active constraint
        # allows exactly one live row per slot, and it is not deferrable. Parking them on
        # themselves is the "no longer active" marker; the real pointer lands once the new row has
        # an id, so the chain still reads new ← old.
        prior = model.objects.filter(kind=MemoryKind.SLOT, key=key, superseded_by__isnull=True)
        if scope == SCOPE_USER:
            prior = prior.filter(user=actor)
        superseded = list(prior.values_list("pk", flat=True))
        model.objects.filter(pk__in=superseded).update(superseded_by=models.F("pk"),
                                                       updated_at=timezone.now())

    row = model.objects.create(kind=kind, key=key, value=text, source=source,
                               embedding=embedding, **extra)
    if superseded:
        model.objects.filter(pk__in=superseded).update(superseded_by=row)
    _forget_semantic_cache(actor, scope)
    audit.record(module="assistant", action="remember_memory",
                 entity_type=model.__name__, entity_id=row.pk, actor=actor,
                 after={"scope": scope, "kind": kind, "key": key, "value": text, "source": source})
    return row


def forget(actor, memory_id: int, *, scope: str = SCOPE_USER) -> None:
    """Hard-delete one memory's content. The audit trail keeps the event, never the sentence —
    a user who asks to be forgotten is forgotten."""
    row = get_for_actor(actor, memory_id, scope=scope)
    before = {"scope": scope, "kind": row.kind, "key": row.key, "source": row.source}
    entity_type = type(row).__name__
    row.delete()
    _forget_semantic_cache(actor, scope)
    audit.record(module="assistant", action="forget_memory", entity_type=entity_type,
                 entity_id=memory_id, actor=actor, before=before)


def get_for_actor(actor, memory_id: int, *, scope: str = SCOPE_USER) -> UserMemory | OrgMemory:
    """Fetch one row the actor is allowed to touch, else ``MemoryNotFound``. Personal rows are
    own-only (never another user's); org rows need admin."""
    if scope == SCOPE_USER:
        row = UserMemory.objects.filter(pk=memory_id, user=actor).first()
    elif scope == SCOPE_ORG:
        if not _is_admin(actor):
            raise PermissionError("Only a System Admin can change organization memory.")
        row = OrgMemory.objects.filter(pk=memory_id).first()
    else:
        raise ValidationError("Memory is either personal or organization-wide.")
    if row is None or row.key.startswith(_CONTROL_PREFIX):
        raise MemoryNotFound(str(memory_id))
    return row


def _forget_semantic_cache(actor, scope: str) -> None:
    """A changed memory can change the right answer, so the near-duplicate answer cache (T2.8)
    must stop serving the old one: drop this user's rows (whole cache for an org-wide change)."""
    if scope == SCOPE_ORG:
        SemanticCache.objects.all().delete()
    elif getattr(actor, "pk", None):
        SemanticCache.objects.filter(user=actor).delete()


# --- read path ---------------------------------------------------------------------------------

def list_for_actor(actor) -> dict[str, list[dict]]:
    """Everything remembered that this actor may see, shaped for the Memory page."""
    if not getattr(actor, "is_authenticated", False):
        return {"personal": [], "org": []}
    personal = _active(UserMemory.objects.filter(user=actor)).exclude(
        key__startswith=_CONTROL_PREFIX)
    org = _active(OrgMemory.objects.all()).exclude(key__startswith=_CONTROL_PREFIX)
    return {"personal": _ordered(personal), "org": _ordered(org)}


def _ordered(queryset) -> list[dict]:
    """Settings first (they decide behaviour and read as a short labelled list), then the
    remembered sentences, newest first within each group — a slot buried between two paragraphs is
    hard to scan for."""
    rows = sorted(queryset, key=lambda r: (r.kind != MemoryKind.SLOT, -r.created_at.timestamp()))
    return [_row_dict(r) for r in rows]


def _row_dict(row) -> dict:
    return {"id": row.id, "kind": row.kind, "key": row.key, "value": row.value,
            "source": row.source, "confidence": row.confidence,
            "created_at": row.created_at.isoformat()}


def slots_for(actor) -> dict[str, str]:
    """Active slot values for the actor: org defaults, overridden by the user's own.

    An actor with no account (anonymous) has no memory at all — org rows included. Memory is only
    ever read on behalf of a signed-in member.
    """
    if not getattr(actor, "is_authenticated", False):
        return {}
    values: dict[str, str] = {}
    for row in _active(OrgMemory.objects.filter(kind=MemoryKind.SLOT)):
        values[row.key] = row.value
    for row in _active(UserMemory.objects.filter(user=actor, kind=MemoryKind.SLOT)):
        values[row.key] = row.value
    return {k: v for k, v in values.items() if k in SLOT_KEYS}


# Above this many facts, recall ranks by similarity to the message instead of injecting all of
# them (facts per user are naturally few — a capped Python scan is enough, no pgvector needed).
SIMILARITY_THRESHOLD = 10
MAX_RECALLED_FACTS = 10


def recall(actor, message_text: str = "", budget_tokens: int | None = None) -> str:
    """The envelope-ready memory block for this actor, or ``""`` when nothing is remembered.

    Slots always come first as compact ``key: value`` lines (they decide behaviour, so they are
    never the part that gets dropped); facts follow, ranked by similarity to ``message_text`` once
    there are more than ``SIMILARITY_THRESHOLD`` of them. ``budget_tokens`` trims facts from the
    end — the envelope manager (T3.6) still owns the final say.
    """
    if not getattr(actor, "is_authenticated", False):
        return ""
    slots = slots_for(actor)
    facts = list(_visible_facts(UserMemory.objects.filter(user=actor))) + \
        list(_visible_facts(OrgMemory.objects.all()))
    if not slots and not facts:
        return ""
    if len(facts) > SIMILARITY_THRESHOLD:
        facts = _rank_facts(facts, message_text)
    facts = facts[:MAX_RECALLED_FACTS]

    lines = ["Remembered about this user (they asked you to keep this; never repeat it back "
             "unprompted):"]
    for key in sorted(slots):
        lines.append(f"- {key}: {slots[key]}")
    for fact in facts:
        lines.append(f"- {fact.value}")
    block = "\n".join(lines)
    if budget_tokens is not None:
        while estimate_tokens(block) > budget_tokens and len(lines) > 1:
            lines.pop()
            block = "\n".join(lines)
        if len(lines) == 1:
            return ""
    return block


def _rank_facts(facts: list, message_text: str) -> list:
    """Most relevant first. Without a query vector (embeddings off/unavailable) recency wins —
    never a random order."""
    query = _embed(message_text) if message_text else None
    if not query:
        return sorted(facts, key=lambda f: f.created_at, reverse=True)
    return sorted(facts, key=lambda f: (_cosine(f.embedding, query) if f.embedding else -1.0),
                  reverse=True)


def degrade_block(text: str) -> str | None:
    """Envelope degrade step: drop the free facts, keep the header and the slot lines (behaviour
    over colour). Returns ``None`` when there is nothing left to drop."""
    lines = text.split("\n")
    kept = [lines[0]] + [ln for ln in lines[1:] if _is_slot_line(ln)]
    return "\n".join(kept) if len(kept) < len(lines) and len(kept) > 1 else None


def _is_slot_line(line: str) -> bool:
    body = line[2:] if line.startswith("- ") else line
    head, sep, _ = body.partition(": ")
    return bool(sep) and head in SLOT_KEYS


# --- pattern detectors (T4.3) -------------------------------------------------------------------

def detect_repeated_slot_choice(user, *, now=None) -> dict | None:
    """The same slot-mappable value confirmed ``PATTERN_MIN_OCCURRENCES``+ times inside the window
    (e.g. always the same warehouse on POs) → one proposal. Read-only over the user's own confirmed
    proposals; no LLM, no writes."""
    now = now or timezone.now()
    counts: dict[tuple[str, str], int] = {}
    messages = Message.objects.filter(
        conversation__user=user, role=Message.Role.ASSISTANT,
        created_at__gte=now - PATTERN_WINDOW,
    ).order_by("-created_at")[:200]
    for message in messages:
        proposal = (message.meta or {}).get("proposal") or {}
        if proposal.get("status") != "confirmed":
            continue
        payload = proposal.get("payload") or {}
        for field, slot in _PAYLOAD_SLOT_MAP.items():
            value = payload.get(field)
            if value:
                counts[(slot, str(value))] = counts.get((slot, str(value)), 0) + 1
    current = slots_for(user)
    for (slot, value), count in sorted(counts.items(), key=lambda kv: -kv[1]):
        if count >= PATTERN_MIN_OCCURRENCES and current.get(slot) != value:
            return {"slot": slot, "value": value, "occurrences": count, "detector": "repeated_choice"}
    return None


def detect_language_correction(user, *, now=None) -> dict | None:
    """The user told the assistant which language to answer in twice inside the window → propose
    the ``language`` slot. Marker matching only (``_LANGUAGE_CORRECTIONS``) — deterministic."""
    now = now or timezone.now()
    counts = {"ar": 0, "en": 0}
    messages = Message.objects.filter(
        conversation__user=user, role=Message.Role.USER,
        created_at__gte=now - PATTERN_WINDOW,
    ).order_by("-created_at")[:200]
    for message in messages:
        text = (message.content or "").lower()
        for lang, markers in _LANGUAGE_CORRECTIONS.items():
            if any(marker in text for marker in markers):
                counts[lang] += 1
    current = slots_for(user).get("language")
    for lang, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        if count >= 2 and current != lang:
            return {"slot": "language", "value": lang, "occurrences": count,
                    "detector": "language_correction"}
    return None


DETECTORS = (detect_repeated_slot_choice, detect_language_correction)


def next_proposal(user, *, now=None) -> dict | None:
    """At most ONE memory proposal per user per day, none for a slot they already dismissed
    (calm > clever). Returns the proposal dict, or ``None``.

    Once shown, the SAME proposal keeps coming back for the rest of the day — the cap is one
    proposal, not one read. Anything else makes the card vanish on a refetch (a remount, a second
    tab, a pull-to-refresh) and leaves the user with no way to answer it. It stops coming back when
    they act on it: confirming sets the slot (so the stored proposal no longer differs from the
    current value) and dismissing suppresses it.
    """
    now = now or timezone.now()
    shown = _control_row(user, "_proposal_shown", now=now)
    if shown is not None:
        return _still_open(user, _decode_proposal(shown.value), now=now)
    for detector in DETECTORS:
        proposal = detector(user, now=now)
        if proposal and _control_row(user, _suppress_key(proposal["slot"]), now=now) is None:
            return proposal
    return None


def _decode_proposal(raw: str) -> dict | None:
    try:
        proposal = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return proposal if isinstance(proposal, dict) and proposal.get("slot") else None


def _still_open(user, proposal: dict | None, *, now) -> dict | None:
    """A stored proposal is only worth re-showing while it is still unanswered."""
    if proposal is None:
        return None
    if _control_row(user, _suppress_key(proposal["slot"]), now=now) is not None:
        return None  # dismissed
    if slots_for(user).get(proposal["slot"]) == proposal["value"]:
        return None  # confirmed (or set by hand since)
    return proposal


def mark_proposal_shown(user, proposal: dict | None = None, *, now=None) -> None:
    """Start the one-a-day clock, remembering WHICH proposal was shown so re-reads return it
    unchanged instead of silently swallowing it."""
    now = now or timezone.now()
    _control_set(user, "_proposal_shown", expires_at=now + _PROPOSAL_THROTTLE, now=now,
                 value=json.dumps(proposal, ensure_ascii=False) if proposal else "")


def suppress_proposal(user, slot: str, *, now=None) -> None:
    """The user dismissed this proposal — don't raise it again for 90 days (stored as an expiring
    control fact, so the suppression forgets itself)."""
    if slot not in SLOT_KEYS:
        raise ValidationError("That is not something the assistant keeps as a setting.")
    now = now or timezone.now()
    _control_set(user, _suppress_key(slot), expires_at=now + timedelta(days=_SUPPRESS_DAYS),
                 now=now)


def _suppress_key(slot: str) -> str:
    return f"_suppress:{slot}"[:48]


def _control_row(user, key: str, *, now=None):
    now = now or timezone.now()
    return UserMemory.objects.filter(user=user, key=key).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)).first()


def _control_set(user, key: str, *, expires_at, now=None, value: str = "") -> None:
    """Control rows are replaced, not superseded — they are bookkeeping, not remembered belief,
    so there is no history worth keeping and no audit event to raise. ``value`` carries the row's
    payload (the shown proposal, as JSON) or the key itself when there is nothing to store."""
    UserMemory.objects.filter(user=user, key=key).delete()
    UserMemory.objects.create(user=user, kind=MemoryKind.FACT, key=key,
                              value=value or key, source=MemorySource.PATTERN,
                              expires_at=expires_at)
