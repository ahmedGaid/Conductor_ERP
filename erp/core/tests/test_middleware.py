"""CSP middleware — header on when a policy is configured, off (and non-clobbering) otherwise."""
from __future__ import annotations

from django.http import HttpResponse

from erp.core.middleware import ContentSecurityPolicyMiddleware


def _mw(settings, policy: str) -> ContentSecurityPolicyMiddleware:
    settings.CSP_POLICY = policy
    return ContentSecurityPolicyMiddleware(lambda request: HttpResponse("ok"))


def test_csp_header_set_from_settings(settings):
    resp = _mw(settings, "default-src 'self'")(None)
    assert resp["Content-Security-Policy"] == "default-src 'self'"


def test_csp_disabled_when_policy_empty(settings):
    resp = _mw(settings, "")(None)
    assert "Content-Security-Policy" not in resp


def test_csp_leaves_an_existing_header_alone(settings):
    def view(request):
        resp = HttpResponse("ok")
        resp["Content-Security-Policy"] = "sandbox"
        return resp

    settings.CSP_POLICY = "default-src 'self'"
    resp = ContentSecurityPolicyMiddleware(view)(None)
    assert resp["Content-Security-Policy"] == "sandbox"
