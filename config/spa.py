"""Serve the built React single-page app at the site root (Phase 11).

The frontend uses a HashRouter, so the server only ever needs to return ``index.html`` at ``/``
— every client route lives in the URL fragment and is never sent to the server. That means no
catch-all rewrite is required: this one exact-root view plus WhiteNoise serving ``/assets/*``
(see ``config.settings.prod``) is the whole story.

Kept as a plain Django view (not WhiteNoise's index-file handling) so it is exercisable through
the Django test client — i.e. the gate can prove the SPA is served without standing up the WSGI
server.
"""
from __future__ import annotations

from pathlib import Path

from django.http import HttpResponse

# config/spa.py -> repo root is two parents up; the Vite build lands in apps/web/dist.
_DIST_INDEX = Path(__file__).resolve().parent.parent / "apps" / "web" / "dist" / "index.html"

_NOT_BUILT = (
    "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
    "<title>Conductor — not built</title></head><body style='font-family:sans-serif;padding:2rem'>"
    "<h1>Conductor frontend is not built yet</h1>"
    "<p>Run <code>cd apps/web &amp;&amp; npm ci &amp;&amp; npm run build</code> to produce "
    "<code>apps/web/dist</code>, then reload. See <code>Docs/RUNBOOK.md</code>.</p>"
    "</body></html>"
)


def spa_index(request) -> HttpResponse:
    """Return the SPA shell (or a build-me hint if the bundle is missing)."""
    if _DIST_INDEX.exists():
        return HttpResponse(_DIST_INDEX.read_bytes(), content_type="text/html; charset=utf-8")
    # Offline-safe: never 500 just because the frontend hasn't been built on this box.
    return HttpResponse(_NOT_BUILT, content_type="text/html; charset=utf-8", status=503)
