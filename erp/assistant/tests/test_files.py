"""Chat attachments — upload, file understanding, claiming (plan session 07).

The model seam stays mocked (gates make no live calls); we exercise the real upload endpoint, the
CSV/text describe helpers, ownership on claim, and that a chat with an attachment links it.
"""
from __future__ import annotations

import json

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.api import views
from erp.assistant.models import Attachment
from erp.assistant.services import ask, files
from erp.identity.models import User

pytestmark = pytest.mark.django_db

ATTACH_URL = "/api/assistant/attachments"
CHAT_URL = "/api/assistant/chat"


def _client(username: str = "att_user") -> tuple[APIClient, User]:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


def _conversation(client: APIClient) -> int:
    return client.post("/api/assistant/conversations", {}, format="json").json()["data"]["id"]


def _drain(resp) -> list[dict]:
    body = b"".join(resp.streaming_content).decode()
    out = []
    for frame in body.split("\n\n"):
        frame = frame.strip()
        if frame.startswith("data:"):
            out.append(json.loads(frame[len("data:"):].strip()))
    return out


# --- file understanding ------------------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_csv_describe_headers_rows_and_cap(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _, user = _client()
    rows = "\n".join(f"row{i},{i * 10}" for i in range(1, 26))  # 25 data rows
    csv = f"name,total\n{rows}\n"
    att = Attachment.objects.create(
        user=user, file=ContentFile(csv.encode(), name="clients.csv"),
        name="clients.csv", content_type="text/csv", size=len(csv),
    )

    text = files.describe_for_model(att)["text"]
    assert "name | total" in text          # header row
    assert "2 columns, 25 data rows" in text  # true count, not the sample size
    assert "row20" in text and "row21" not in text  # capped at the sample size
    assert "5 more rows)" in text


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_text_file_truncated_to_budget(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _, user = _client()
    big = "x" * (files.TEXT_BUDGET + 500)
    att = Attachment.objects.create(
        user=user, file=ContentFile(big.encode(), name="n.txt"),
        name="notes.txt", content_type="text/plain", size=len(big),
    )
    text = files.describe_for_model(att)["text"]
    assert "truncated" in text
    assert len(text) < len(big)


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_image_describe_returns_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _, user = _client()
    att = Attachment.objects.create(
        user=user, file=ContentFile(b"\x89PNG\r\n", name="s.png"),
        name="shot.png", content_type="image/png", size=6,
    )
    described = files.describe_for_model(att)
    assert described["media"]["media_type"] == "image/png"
    assert described["media"]["data"] == b"\x89PNG\r\n"


# --- upload endpoint ---------------------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upload_stores_and_returns_descriptor(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client, _ = _client()
    upload = SimpleUploadedFile("p.csv", b"a,b\n1,2\n", content_type="text/csv")
    resp = client.post(ATTACH_URL, {"file": upload}, format="multipart")
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["name"] == "p.csv" and data["content_type"] == "text/csv"
    assert Attachment.objects.filter(id=data["id"], message__isnull=True).exists()


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upload_oversize_rejected(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    monkeypatch.setattr(views, "MAX_UPLOAD_BYTES", 8)
    client, _ = _client()
    upload = SimpleUploadedFile("big.txt", b"way too many bytes", content_type="text/plain")
    resp = client.post(ATTACH_URL, {"file": upload}, format="multipart")
    assert resp.status_code == 400


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upload_unsupported_type_rejected(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client, _ = _client()
    upload = SimpleUploadedFile("a.zip", b"PK\x03\x04", content_type="application/zip")
    resp = client.post(ATTACH_URL, {"file": upload}, format="multipart")
    assert resp.status_code == 400


# --- ownership + claim -------------------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_claiming_foreign_attachment_404(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _, owner = _client("att_owner")
    _, intruder = _client("att_intruder")
    att = Attachment.objects.create(
        user=owner, file=ContentFile(b"a,b\n", name="o.csv"),
        name="o.csv", content_type="text/csv", size=4,
    )
    with pytest.raises(Http404):
        files.fetch_unclaimed([att.id], user=intruder)


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_chat_with_attachment_persists_link(settings, tmp_path, monkeypatch):
    settings.MEDIA_ROOT = str(tmp_path)
    client, user = _client()
    cid = _conversation(client)
    att = Attachment.objects.create(
        user=user, file=ContentFile(b"name,total\nx,10\n", name="d.csv"),
        name="d.csv", content_type="text/csv", size=16,
    )
    monkeypatch.setattr(
        ask, "complete_json",
        lambda *a, **k: {"tool": "none", "period": None, "query": None, "limit": None},
    )
    monkeypatch.setattr(ask, "complete_stream", lambda messages, **_: iter(["ok"]))

    resp = client.post(
        CHAT_URL, {"conversation_id": cid, "message": "what's in this?", "attachment_ids": [att.id]},
        format="json",
    )
    assert resp.status_code == 200
    _drain(resp)

    att.refresh_from_db()
    assert att.message is not None and att.message.role == "user"
    assert att.message.meta["attachments"][0]["id"] == att.id


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_chat_with_foreign_attachment_404_before_stream(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    client, _ = _client()
    _, other = _client("att_other")
    cid = _conversation(client)
    att = Attachment.objects.create(
        user=other, file=ContentFile(b"a\n", name="x.csv"),
        name="x.csv", content_type="text/csv", size=2,
    )
    resp = client.post(
        CHAT_URL, {"conversation_id": cid, "message": "hi", "attachment_ids": [att.id]},
        format="json",
    )
    assert resp.status_code == 404
