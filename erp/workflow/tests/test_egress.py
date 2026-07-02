"""SSRF egress guard — workflow REST/webhook adapters must never reach non-public addresses."""
from __future__ import annotations

import socket

import pytest
from django.test import override_settings

from erp.workflow.adapters.egress import EgressBlockedError, assert_public_url
from erp.workflow.adapters.rest import RestAdapter
from erp.workflow.adapters.types import AdapterCall
from erp.workflow.adapters.webhook import WebhookAdapter


def _resolve_to(monkeypatch, ip: str) -> None:
    monkeypatch.setattr(
        "erp.workflow.adapters.egress.socket.getaddrinfo",
        lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))],
    )


def test_egress_blocks_metadata_ip():
    with pytest.raises(EgressBlockedError):
        assert_public_url("http://169.254.169.254/latest/meta-data/")


def test_egress_blocks_rfc1918_and_loopback():
    for url in ("http://10.0.0.5/hook", "https://192.168.1.1/", "http://172.16.0.1/x",
                "http://127.0.0.1:8000/api", "http://0.0.0.0/"):
        with pytest.raises(EgressBlockedError):
            assert_public_url(url)


def test_egress_blocks_dns_rebinding_to_private(monkeypatch):
    _resolve_to(monkeypatch, "10.1.2.3")
    with pytest.raises(EgressBlockedError):
        assert_public_url("https://innocent-looking.example.com/hook")


def test_egress_blocks_non_http_schemes():
    for url in ("ftp://example.com/x", "file:///etc/passwd", "gopher://example.com"):
        with pytest.raises(EgressBlockedError):
            assert_public_url(url)


def test_egress_allows_public_host(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    assert_public_url("https://api.example.com/v1")  # no raise


@override_settings(WORKFLOW_EGRESS_ALLOWLIST=["api.example.com"])
def test_allowlist_pass_and_block(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    assert_public_url("https://api.example.com/v1")  # exact match passes
    assert_public_url("https://eu.api.example.com/v1")  # subdomain passes
    with pytest.raises(EgressBlockedError):
        assert_public_url("https://evil.example.org/v1")  # not on the list


def test_rest_adapter_returns_blocked_result_not_raise():
    res = RestAdapter().call(AdapterCall(config={"method": "GET", "url": "http://127.0.0.1/x"}))
    assert res.ok is False
    assert "egress blocked" in (res.error or "")


def test_webhook_adapter_covered_by_same_guard():
    res = WebhookAdapter().call(
        AdapterCall(config={"url": "http://169.254.169.254/latest"}, payload={"a": 1})
    )
    assert res.ok is False
    assert "egress blocked" in (res.error or "")
