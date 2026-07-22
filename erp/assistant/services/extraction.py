"""Document → draft-invoice extraction (plan session 02, part 1).

A supplier invoice (photo or PDF, Arabic and/or English) goes to Claude under a **strict JSON
schema**, then the extracted supplier + line items are fuzzy-matched against existing records.
The result is a *proposal* the user reviews and edits — this module never writes business data;
the confirm step posts through the normal purchasing endpoint as the user.

Prompt-injection defense: the document is **data, not instructions** — it travels in a user-role
content block; the system prompt is a frozen constant; the model's output is schema-validated and
only ever mapped to typed fields.
"""
from __future__ import annotations

import base64
import json
import re
import time
from difflib import SequenceMatcher

from django.conf import settings

from erp.audit import services as audit
from erp.inventory import contracts as inventory
from erp.purchasing import contracts as purchasing

from ..client import get_client, get_gemini_client, groq_chat, mistral_chat, model_id, provider
from ..errors import ExtractionFailedError
from .prompt_registry import get as get_prompt

# Media types the endpoint accepts (mirrors the Session-00 import posture: allowlist, no sniffing).
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
PDF_TYPE = "application/pdf"
ALLOWED_TYPES = IMAGE_TYPES | {PDF_TYPE}

# Everything the model may return — strict: unknown keys are rejected, all fields required
# (nullable where the document may simply not carry the value).
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "readable": {
            "type": "boolean",
            "description": "false when the document is not a supplier invoice/receipt or is too "
                           "blurry/cropped to extract reliably",
        },
        "supplier_name": {"type": ["string", "null"]},
        "supplier_tax_id": {"type": ["string", "null"]},
        "invoice_number": {"type": ["string", "null"]},
        "invoice_date": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD"},
        "currency": {"type": ["string", "null"], "description": "ISO 4217, e.g. EGP"},
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "quantity": {"type": "string", "description": "decimal as string, e.g. '2' or '1.5'"},
                    "unit_price_minor": {
                        "type": "integer",
                        "description": "unit price in MINOR units (piasters for EGP): 12.50 EGP -> 1250",
                    },
                },
                "required": ["description", "quantity", "unit_price_minor"],
                "additionalProperties": False,
            },
        },
        "subtotal_minor": {"type": ["integer", "null"]},
        "vat_minor": {"type": ["integer", "null"]},
        "total_minor": {"type": ["integer", "null"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "issues": {
            "type": "array",
            "items": {"type": "string"},
            "description": "anything unreadable/ambiguous, stated plainly (user-facing)",
        },
    },
    "required": [
        "readable", "supplier_name", "supplier_tax_id", "invoice_number", "invoice_date",
        "currency", "lines", "subtotal_minor", "vat_minor", "total_minor", "confidence", "issues",
    ],
    "additionalProperties": False,
}

_extraction_prompt = get_prompt("extraction")

_SYSTEM = _extraction_prompt.template

_INSTRUCTION = "Extract the invoice fields from this document."


def _content_block(data: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(data).decode("ascii")
    if media_type == PDF_TYPE:
        return {"type": "document", "source": {"type": "base64", "media_type": PDF_TYPE, "data": b64}}
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}


# --- fuzzy matching against existing records ---------------------------------------------------

_ARABIC_NORM = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي", "ـ": None})


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_ARABIC_NORM).casefold().strip())


def _rank(name: str, candidates: list, key) -> list[tuple[float, object]]:
    """Candidates scored by name similarity, best first."""
    target = _norm(name)
    scored = [(SequenceMatcher(None, target, _norm(key(c))).ratio(), c) for c in candidates]
    return sorted(scored, key=lambda pair: pair[0], reverse=True)


def _match_supplier(name: str | None) -> dict:
    """Best supplier match + runners-up the user can pick from instead."""
    out: dict = {"matched_code": None, "candidates": []}
    if not name:
        return out
    ranked = _rank(name, purchasing.list_suppliers(), lambda s: s.name)
    if ranked and ranked[0][0] >= 0.85:
        out["matched_code"] = ranked[0][1].code
    out["candidates"] = [
        {"code": s.code, "name": s.name, "score": round(score, 2)}
        for score, s in ranked[:3]
        if score >= 0.5
    ]
    return out


def _match_line(description: str, items: list, supplier_code: str | None = None) -> dict:
    """One invoice-line description → best item match + runners-up.

    The authoritative match comes from ``inventory.resolve_item`` with the recognised supplier's
    code: a barcode/part-number/SKU in the description, or a name this supplier taught us before,
    resolves deterministically (``matched_via`` names the winning tier). Only when the resolver finds
    nothing do we fall back to a fuzzy name auto-match. The candidate list stays fuzzy either way, so
    the reviewer always has near-misses to pick from — the resolver's name tier is exact-only."""
    out: dict = {"matched_sku": None, "matched_via": None, "candidates": []}
    if not description:
        return out
    resolution = inventory.resolve_item(supplier_code=(supplier_code or ""),
                                        code=description, name=description)
    ranked = _rank(description, items, lambda i: i.name)
    if resolution.item is not None:
        out["matched_sku"] = resolution.item.sku
        out["matched_via"] = resolution.method
    elif ranked and ranked[0][0] >= 0.85:
        out["matched_sku"] = ranked[0][1].sku
        out["matched_via"] = "fuzzy"
    out["candidates"] = [
        {"sku": i.sku, "name": i.name, "score": round(score, 2)}
        for score, i in ranked[:3]
        if score >= 0.5
    ]
    return out


# --- the service --------------------------------------------------------------------------------


_UNREADABLE = {"readable": False, "lines": [], "confidence": "low",
               "issues": ["truncated_or_refused"]}


def extract_document(*, data: bytes, media_type: str, filename: str, actor) -> dict:
    """One document in → one reviewed-draft proposal out. Read-only; audit-logged."""
    from .tracing import estimate_tokens, trace_call

    prov = provider()
    with trace_call("extract", actor=actor, prompt_ref=_extraction_prompt.ref) as handle:
        if prov == "gemini":
            extracted = _extract_gemini(data, media_type)
        elif prov == "groq":
            extracted = _extract_groq(data, media_type)
        elif prov == "mistral":
            extracted = _extract_mistral(data, media_type)
        else:
            extracted = _extract_anthropic(data, media_type)
        handle.usage(provider=prov, model=model_id(prov), estimated=True, input_tokens=0,
                     output_tokens=estimate_tokens(json.dumps(extracted, ensure_ascii=False)))
    return _proposal(extracted, filename, actor)


def _extract_anthropic(data: bytes, media_type: str) -> dict:
    try:
        response = get_client().messages.create(
            model=model_id(),
            max_tokens=settings.ASSISTANT_MAX_TOKENS,
            system=_SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
            messages=[{
                "role": "user",
                "content": [_content_block(data, media_type), {"type": "text", "text": _INSTRUCTION}],
            }],
        )
    except Exception as exc:  # network/auth/rate-limit — blame-free, retryable
        raise ExtractionFailedError(data={"reason": exc.__class__.__name__}) from exc

    if getattr(response, "stop_reason", None) not in ("end_turn", None):
        # refusal / max_tokens — treat as an unreadable document, never a 500
        return dict(_UNREADABLE)

    try:
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)
    except (StopIteration, ValueError) as exc:
        raise ExtractionFailedError(data={"reason": "unparseable_model_output"}) from exc


def _gemini_schema(node):
    """Translate our strict JSON schema to Gemini's response_schema dialect: no type unions
    (``["string","null"]`` → ``nullable: true``) and no ``additionalProperties``."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "additionalProperties":
                continue
            if key == "type" and isinstance(value, list):
                out["type"] = next(t for t in value if t != "null")
                out["nullable"] = True
                continue
            out[key] = _gemini_schema(value)
        return out
    if isinstance(node, list):
        return [_gemini_schema(item) for item in node]
    return node


def _gemini_config(types):
    cfg = dict(
        system_instruction=_SYSTEM,
        response_mime_type="application/json",
        response_schema=_gemini_schema(EXTRACTION_SCHEMA),
        max_output_tokens=settings.ASSISTANT_MAX_TOKENS,
    )
    # 2.5-flash is a "thinking" model: reasoning tokens draw down max_output_tokens and can leave
    # nothing for the answer on a dense invoice. Turn thinking off for this structured-extraction
    # task so the whole budget goes to the JSON. (Older models reject the field — ignore then.)
    try:
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:  # pragma: no cover - SDK/model without thinking support
        pass
    return types.GenerateContentConfig(**cfg)


def _extract_gemini(data: bytes, media_type: str) -> dict:
    from google.genai import types

    # The SDK's internal retry is disabled (see get_gemini_client) because it crashes on transient
    # 429/503. We retry here with a FRESH client and a short backoff, which smooths the low
    # per-minute limits on free-tier keys.
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = get_gemini_client().models.generate_content(
                model=model_id(),
                contents=[types.Part.from_bytes(data=data, mime_type=media_type), _INSTRUCTION],
                config=_gemini_config(types),
            )
            break
        except Exception as exc:  # network/auth/rate-limit — blame-free, retryable
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    else:
        raise ExtractionFailedError(data={"reason": last_exc.__class__.__name__}) from last_exc

    text = getattr(response, "text", None)
    if not text:
        # safety-blocked / empty candidate — treat as an unreadable document, never a 500
        return dict(_UNREADABLE)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ExtractionFailedError(data={"reason": "unparseable_model_output"}) from exc


# Groq's Llama-4 vision is image-only (no native PDF) and JSON-object mode (no schema param), so we
# spell the shape out in the prompt and validate on our side.
_GROQ_SCHEMA_HINT = (
    " Respond with a single JSON object, no prose, with exactly these keys: "
    "readable (bool), supplier_name (str|null), supplier_tax_id (str|null), invoice_number "
    "(str|null), invoice_date (str|null, YYYY-MM-DD), currency (str|null), lines (array of "
    "{description:str, quantity:str, unit_price_minor:int}), subtotal_minor (int|null), vat_minor "
    "(int|null), total_minor (int|null), confidence ('high'|'medium'|'low'), issues (array of str)."
)


def _extract_openai_compatible(chat, prov: str, data: bytes, media_type: str) -> dict:
    """Shared image→JSON extraction for the OpenAI-compatible providers (Groq, Mistral): image-only
    vision, json-object mode (the shape is spelled into the system prompt), retry then surface a
    blame-free error. ``chat`` is the provider's chat seam; ``prov`` selects its default model."""
    if media_type == PDF_TYPE:
        # These vision models read images, not native PDF — ask for a photo instead (blame-free).
        return {**_UNREADABLE, "issues": ["pdf_unsupported_on_this_provider"]}

    b64 = base64.standard_b64encode(data).decode("ascii")
    messages = [
        {"role": "system", "content": _SYSTEM + _GROQ_SCHEMA_HINT},
        {"role": "user", "content": [
            {"type": "text", "text": _INSTRUCTION},
            {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}},
        ]},
    ]

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            body = chat(messages, model=model_id(prov), max_tokens=settings.ASSISTANT_MAX_TOKENS)
            break
        except Exception as exc:  # network/auth/rate-limit — blame-free, retryable
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    else:
        raise ExtractionFailedError(data={"reason": last_exc.__class__.__name__}) from last_exc

    try:
        text = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return dict(_UNREADABLE)
    if not text:
        return dict(_UNREADABLE)
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ExtractionFailedError(data={"reason": "unparseable_model_output"}) from exc


def _extract_groq(data: bytes, media_type: str) -> dict:
    return _extract_openai_compatible(groq_chat, "groq", data, media_type)


def _extract_mistral(data: bytes, media_type: str) -> dict:
    return _extract_openai_compatible(mistral_chat, "mistral", data, media_type)


def _proposal(extracted: dict, filename: str, actor) -> dict:
    lines = extracted.get("lines") or []
    items = inventory.list_items() if lines else []
    supplier = {
        "name": extracted.get("supplier_name"),
        "tax_id": extracted.get("supplier_tax_id"),
        **_match_supplier(extracted.get("supplier_name")),
    }
    # A recognised supplier lets item resolution consult the aliases that supplier has taught us.
    supplier_code = supplier.get("matched_code")
    proposal = {
        "readable": bool(extracted.get("readable")),
        "confidence": extracted.get("confidence", "low"),
        "issues": extracted.get("issues", []),
        "supplier": supplier,
        "invoice": {
            "number": extracted.get("invoice_number"),
            "date": extracted.get("invoice_date"),
            "currency": extracted.get("currency") or "EGP",
            "subtotal_minor": extracted.get("subtotal_minor"),
            "vat_minor": extracted.get("vat_minor"),
            "total_minor": extracted.get("total_minor"),
        },
        "lines": [
            {
                "description": ln.get("description", ""),
                "quantity": ln.get("quantity", ""),
                "unit_price_minor": ln.get("unit_price_minor"),
                **_match_line(ln.get("description", ""), items, supplier_code),
            }
            for ln in lines
        ],
    }
    audit.record(
        module="assistant", action="extract_document", entity_type="Document",
        entity_id=filename, actor=actor,
        after={"readable": proposal["readable"], "confidence": proposal["confidence"],
               "supplier_matched": proposal["supplier"]["matched_code"],
               "line_count": len(proposal["lines"])},
    )
    return proposal
