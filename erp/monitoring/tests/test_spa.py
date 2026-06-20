"""Phase 11 — the built React SPA is served at the site root.

The frontend uses a HashRouter, so the server only ever serves ``/`` (the SPA shell) and lets the
client own every route in the URL fragment. These tests prove the root view returns that shell when
the bundle is built, and degrades to a clear "not built" hint (503) instead of a 500 when it isn't —
without standing up waitress/WhiteNoise.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client

from config.spa import _DIST_INDEX

pytestmark = pytest.mark.django_db

_DIST_BUILT = _DIST_INDEX.exists()


def test_root_serves_spa_shell_when_built() -> None:
    if not _DIST_BUILT:
        pytest.skip("apps/web/dist not built in this environment")
    resp = Client().get("/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # The Vite build references its hashed bundle from /assets and mounts into #root.
    assert '<div id="root">' in body
    assert "/assets/" in body


def test_root_degrades_gracefully_without_a_build(tmp_path: Path, monkeypatch) -> None:
    # Point the view at a non-existent index to simulate an un-built box: 503 + a build hint,
    # never a 500.
    monkeypatch.setattr("config.spa._DIST_INDEX", tmp_path / "nope" / "index.html")
    resp = Client().get("/")
    assert resp.status_code == 503
    assert "not built" in resp.content.decode("utf-8").lower()


def test_api_and_health_take_precedence_over_the_spa_root() -> None:
    # The catch-nothing root pattern is mounted last, so real routes still resolve.
    assert Client().get("/health").status_code == 200
    # An unauthenticated API call is rejected by DRF (401/403), not swallowed by the SPA view.
    assert Client().get("/api/accounting/accounts").status_code in (401, 403)
