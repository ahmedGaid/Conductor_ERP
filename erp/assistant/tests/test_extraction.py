"""Assistant document extraction — mocked AI clients, no live calls in gates.

Covers: feature flag (status endpoint + 404 when off), upload guards (size/type, checked before
any AI call), the happy path (extract → fuzzy match supplier + items → proposal), the designed
unreadable state (200, never a 500), upstream failure (502 AI-001), the audit record, and the
Gemini provider path (schema translation + parsing).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.services import extraction
from erp.audit.models import AuditEntry
from erp.core.import_api import MAX_UPLOAD_BYTES
from erp.identity.models import User
from erp.inventory.domain.models import Item
from erp.purchasing.domain.models import Supplier

pytestmark = pytest.mark.django_db

STATUS_URL = "/api/assistant/status"
EXTRACT_URL = "/api/assistant/extract-document"

EXTRACTED = {
    "readable": True,
    "supplier_name": "Delta Miills",  # typo on purpose — fuzzy match must still find Delta Mills
    "supplier_tax_id": "123-456-789",
    "invoice_number": "INV-77",
    "invoice_date": "2026-06-30",
    "currency": "EGP",
    "lines": [
        {"description": "Sugar 1kg", "quantity": "10", "unit_price_minor": 2500},
        {"description": "something unknown", "quantity": "1", "unit_price_minor": 100},
    ],
    "subtotal_minor": 25100,
    "vat_minor": 3514,
    "total_minor": 28614,
    "confidence": "high",
    "issues": [],
}


class _FakeClient:
    """Stands in for anthropic.Anthropic — records the request, returns a canned payload."""

    def __init__(self, payload: dict | None = None, stop_reason: str = "end_turn",
                 error: Exception | None = None):
        self.calls: list[dict] = []
        self._payload = payload
        self._stop_reason = stop_reason
        self._error = error
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        if self._error is not None:
            raise self._error
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self._stop_reason,
            content=[SimpleNamespace(type="text", text=json.dumps(self._payload))],
        )


class _FakeGemini:
    """Stands in for google.genai.Client — records the request, returns a canned payload."""

    def __init__(self, payload: dict | None = None):
        self.calls: list[dict] = []
        self._text = None if payload is None else json.dumps(payload)
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self._text)


def _client() -> APIClient:
    user = User.objects.create_user(username="ai_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _post(client: APIClient, data: bytes = b"fake-image-bytes", name: str = "invoice.jpg",
          content_type: str = "image/jpeg"):
    return client.post(
        EXTRACT_URL,
        {"file": SimpleUploadedFile(name, data, content_type=content_type)},
        format="multipart",
    )


@override_settings(ASSISTANT_ENABLED=False)
def test_status_reflects_flag():
    client = _client()
    assert client.get(STATUS_URL).json()["data"] == {"enabled": False, "mode": "full"}
    with override_settings(ASSISTANT_ENABLED=True):
        assert client.get(STATUS_URL).json()["data"] == {"enabled": True, "mode": "full"}


@override_settings(ASSISTANT_ENABLED=False)
def test_disabled_endpoint_is_404():
    assert _post(_client()).status_code == 404


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upload_guards_run_before_any_ai_call(monkeypatch):
    def _boom():
        raise AssertionError("client must not be constructed for rejected uploads")

    monkeypatch.setattr(extraction, "get_client", _boom)
    client = _client()

    too_big = client.post(
        EXTRACT_URL,
        {"file": SimpleUploadedFile("big.jpg", b"x" * (MAX_UPLOAD_BYTES + 1),
                                    content_type="image/jpeg")},
        format="multipart",
    )
    assert too_big.status_code == 400

    wrong_type = _post(client, name="notes.txt", content_type="text/plain")
    assert wrong_type.status_code == 400
    assert client.post(EXTRACT_URL, {}, format="multipart").status_code == 400


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_extract_matches_supplier_and_items(monkeypatch):
    Supplier.objects.create(code="S-1", name="Delta Mills")
    Supplier.objects.create(code="S-2", name="Cairo Supply")
    Item.objects.create(sku="SUG-1", name="Sugar 1kg", type="stock")

    fake = _FakeClient(EXTRACTED)
    monkeypatch.setattr(extraction, "get_client", lambda: fake)

    resp = _post(_client())
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["readable"] is True
    assert data["confidence"] == "high"
    assert data["supplier"]["matched_code"] == "S-1"
    assert data["supplier"]["tax_id"] == "123-456-789"
    assert data["invoice"]["total_minor"] == 28614

    matched, unmatched = data["lines"]
    assert matched["matched_sku"] == "SUG-1"
    assert unmatched["matched_sku"] is None  # surfaced for the user to link or create

    # The model was called under the strict schema, with the document as user-role data.
    (call,) = fake.calls
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["messages"][0]["role"] == "user"
    assert call["messages"][0]["content"][0]["type"] == "image"

    entry = AuditEntry.objects.get(module="assistant", action="extract_document")
    assert entry.after["supplier_matched"] == "S-1"
    assert entry.actor is not None


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_pdf_goes_as_document_block(monkeypatch):
    fake = _FakeClient({**EXTRACTED, "lines": []})
    monkeypatch.setattr(extraction, "get_client", lambda: fake)
    assert _post(_client(), name="bill.pdf", content_type="application/pdf").status_code == 200
    assert fake.calls[0]["messages"][0]["content"][0]["type"] == "document"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_unreadable_document_is_a_designed_state_not_a_500(monkeypatch):
    unreadable = {**EXTRACTED, "readable": False, "lines": [], "confidence": "low",
                  "supplier_name": None, "issues": ["photo too blurry to read the totals"]}
    monkeypatch.setattr(extraction, "get_client", lambda: _FakeClient(unreadable))

    resp = _post(_client())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["readable"] is False
    assert data["issues"] == ["photo too blurry to read the totals"]
    assert data["supplier"]["matched_code"] is None


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_truncated_or_refused_response_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(
        extraction, "get_client", lambda: _FakeClient(EXTRACTED, stop_reason="max_tokens")
    )
    resp = _post(_client())
    assert resp.status_code == 200
    assert resp.json()["data"]["readable"] is False


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upstream_failure_is_502_with_catalog_code(monkeypatch):
    monkeypatch.setattr(
        extraction, "get_client", lambda: _FakeClient(error=RuntimeError("connection reset"))
    )
    resp = _post(_client())
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "AI-001"


# --- Gemini provider path ------------------------------------------------------------------------


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="gemini")
def test_gemini_extracts_with_translated_schema(monkeypatch):
    Supplier.objects.create(code="S-1", name="Delta Mills")

    fake = _FakeGemini(EXTRACTED)
    monkeypatch.setattr(extraction, "get_gemini_client", lambda: fake)

    resp = _post(_client())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["supplier"]["matched_code"] == "S-1"
    assert data["invoice"]["total_minor"] == 28614

    (call,) = fake.calls
    schema = call["config"].response_schema
    # Gemini dialect: type unions become nullable, additionalProperties is stripped.
    assert schema["properties"]["supplier_name"] == {"type": "string", "nullable": True}
    assert "additionalProperties" not in schema
    assert call["config"].response_mime_type == "application/json"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="gemini")
def test_gemini_blocked_response_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(extraction, "get_gemini_client", lambda: _FakeGemini(None))
    resp = _post(_client())
    assert resp.status_code == 200
    assert resp.json()["data"]["readable"] is False


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="gemini")
def test_gemini_upstream_failure_is_502(monkeypatch):
    def _raise():
        raise RuntimeError("connection reset")

    monkeypatch.setattr(extraction, "get_gemini_client", _raise)
    monkeypatch.setattr(extraction.time, "sleep", lambda *_: None)  # no real backoff in tests
    resp = _post(_client())
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "AI-001"


# --- Groq provider path (OpenAI-compatible, Llama-4 vision) --------------------------------------


def _groq_reply(payload: dict) -> dict:
    return {"choices": [{"message": {"content": json.dumps(payload)}}]}


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="groq")
def test_groq_extracts_and_sends_image_url(monkeypatch):
    Supplier.objects.create(code="S-1", name="Delta Mills")
    calls = []

    def fake_groq_chat(messages, **kwargs):
        calls.append((messages, kwargs))
        return _groq_reply(EXTRACTED)

    monkeypatch.setattr(extraction, "groq_chat", fake_groq_chat)

    resp = _post(_client())
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["supplier"]["matched_code"] == "S-1"
    assert data["invoice"]["total_minor"] == 28614

    (messages, kwargs), = calls
    # Image goes as an OpenAI-style data-URL image_url block; JSON mode requested.
    user_parts = messages[1]["content"]
    assert any(p["type"] == "image_url" and p["image_url"]["url"].startswith("data:image/jpeg;base64,")
               for p in user_parts)
    assert kwargs["max_tokens"] > 0


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="groq")
def test_groq_pdf_is_a_designed_unsupported_state(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("PDF must not reach the image-only Groq model")

    monkeypatch.setattr(extraction, "groq_chat", _boom)
    resp = _post(_client(), name="bill.pdf", content_type="application/pdf")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["readable"] is False
    assert "pdf_unsupported_on_this_provider" in data["issues"]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="groq")
def test_groq_upstream_failure_is_502(monkeypatch):
    def _raise(*a, **k):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(extraction, "groq_chat", _raise)
    monkeypatch.setattr(extraction.time, "sleep", lambda *_: None)  # no real backoff in tests
    resp = _post(_client())
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "AI-001"
