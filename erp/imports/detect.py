"""Dataset detection — "what IS this file a list of?" (plan session 03).

Given a file's headers and a few sample rows, rank the registered entities by how well the columns
fit each one. Deterministic first (index decision 3): score every adapter by weighted coverage of
its *required* fields via :func:`erp.imports.mapping.match_headers`. A clear winner (top ≥ 70 and a
≥ 20 gap over the runner-up) settles it with zero model calls. Only a genuinely ambiguous file — no
clear leader — spends one ``complete_json`` call, and even then the model must name a **registered**
entity or its answer is discarded and the deterministic ranking stands.

The result is a ranked candidate list: the wizard shows the top one when confident, a choice when
not.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from erp.assistant.errors import AssistantUnavailableError
from erp.assistant.gateway.core import complete_json

from . import registry
from .mapping import match_headers

# Deterministic-confidence thresholds for "don't bother asking the model".
CLEAR_MIN = 70   # the leader must be at least this strong …
CLEAR_GAP = 20   # … and this far ahead of the runner-up.

# Coverage weighting: required fields carry the entity's identity; optionals only break ties.
_REQUIRED_WEIGHT = 85
_OPTIONAL_WEIGHT = 15


@dataclass
class Candidate:
    entity: str
    confidence: int  # 0–100


@dataclass
class DetectResult:
    candidates: list[Candidate]  # ranked, highest confidence first
    method: str  # "deterministic" | "model"

    @property
    def top(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None


def _score(headers, adapter) -> int:
    """0–100 fit of these headers to one adapter: fraction of required fields covered (dominant)
    plus a small optional-coverage tiebreaker."""
    fm = match_headers(headers, adapter).field_map()
    required = [f.name for f in adapter.fields if f.required]
    optional = [f.name for f in adapter.fields if not f.required]
    req_cov = (sum(1 for f in required if f in fm) / len(required)) if required else 1.0
    opt_cov = (sum(1 for f in optional if f in fm) / len(optional)) if optional else 0.0
    return round(req_cov * _REQUIRED_WEIGHT + opt_cov * _OPTIONAL_WEIGHT)


def _is_clear_winner(candidates: list[Candidate]) -> bool:
    if not candidates or candidates[0].confidence < CLEAR_MIN:
        return False
    if len(candidates) == 1:
        return True
    return candidates[0].confidence - candidates[1].confidence >= CLEAR_GAP


def detect_entity(actor, headers, sample_rows) -> DetectResult:
    """Rank registered entities for this file. Deterministic when a clear leader exists; otherwise
    one model call breaks the tie (validated against the registry)."""
    scored = [Candidate(entity=e, confidence=_score(headers, registry.get(e)))
              for e in registry.entities()]
    scored.sort(key=lambda c: c.confidence, reverse=True)
    scored = [c for c in scored if c.confidence > 0]

    if _is_clear_winner(scored):
        return DetectResult(candidates=scored, method="deterministic")

    pick = _detect_with_model(actor, headers, sample_rows,
                              [c.entity for c in scored] or registry.entities())
    if pick is None:
        return DetectResult(candidates=scored, method="deterministic")
    return DetectResult(candidates=_apply_model_pick(scored, pick), method="model")


# --- Model fallback --------------------------------------------------------------------------
_DETECT_SYSTEM = (
    "You identify which business entity a spreadsheet's rows represent. "
    "Pick exactly one entity from the candidate list, or null if none fits. "
    "Weigh the column headers and the sample values. Reply as JSON only, no prose."
)


def _detect_schema(candidates: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "entity": {"type": ["string", "null"], "enum": [*candidates, None]},
            "confidence": {"type": "number"},
            "reason": {"type": "string"},
        },
        "required": ["entity"],
    }


def _detect_with_model(actor, headers, sample_rows, candidates) -> Candidate | None:
    """One ``complete_json`` call to break a tie. Returns a Candidate only if the model names a
    registered entity; any outage or off-list answer returns None (deterministic ranking wins)."""
    if not candidates:
        return None
    payload = {"headers": list(headers), "sample_rows": list(sample_rows or [])[:5],
               "candidates": list(candidates)}
    try:
        raw = complete_json(_DETECT_SYSTEM,
                            json.dumps(payload, ensure_ascii=False, default=str),
                            _detect_schema(list(candidates)))
    except AssistantUnavailableError:
        return None
    entity = (raw or {}).get("entity")
    if entity not in registry.REGISTER:  # off-list or null → discarded (index decision 3)
        return None
    try:
        conf = int(round(float(raw.get("confidence"))))
    except (TypeError, ValueError):
        conf = 60
    return Candidate(entity=entity, confidence=max(0, min(conf, 100)))


def _apply_model_pick(scored: list[Candidate], pick: Candidate) -> list[Candidate]:
    """Fold the model's choice into the ranking: boost it to at least its stated confidence (never
    lower a stronger deterministic score) and re-sort so the UI surfaces it on top."""
    by_entity = {c.entity: c for c in scored}
    if pick.entity in by_entity:
        by_entity[pick.entity].confidence = max(by_entity[pick.entity].confidence, pick.confidence)
    else:
        scored.append(pick)
    scored.sort(key=lambda c: c.confidence, reverse=True)
    return scored
