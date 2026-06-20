"""Production WSGI entrypoint via waitress (Phase 11).

Why waitress: it is a pure-python, production-grade WSGI server that runs natively on Windows
(gunicorn/uwsgi are POSIX-only). WhiteNoise is already wired into the Django middleware under the
prod settings, so this one process serves the API, the Django admin/DRF static, AND the built React
bundle — no second web server needed for a single-tenant install. Put IIS/Nginx in front only for
TLS termination + a public hostname.

Run directly:
    set DJANGO_SETTINGS_MODULE=config.settings.prod
    .venv\\Scripts\\python.exe deploy\\serve_waitress.py

Tunables (env): CONDUCTOR_HOST (default 127.0.0.1), CONDUCTOR_PORT (default 8000),
CONDUCTOR_THREADS (default 8). Bind to 127.0.0.1 when a reverse proxy fronts it; 0.0.0.0 only for
a direct LAN install.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the repo root is importable. When launched as `python deploy/serve_waitress.py` (directly
# or via the NSSM service), sys.path[0] is this file's directory (deploy/), NOT the repo root, so
# `import config` would fail regardless of the working directory. Put the repo root first.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Default to prod, but let the service definition / shell override it.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

from waitress import serve  # noqa: E402

from config.wsgi import application  # noqa: E402


def main() -> None:
    host = os.environ.get("CONDUCTOR_HOST", "127.0.0.1")
    port = int(os.environ.get("CONDUCTOR_PORT", "8000"))
    threads = int(os.environ.get("CONDUCTOR_THREADS", "8"))
    print(f"Conductor: waitress serving config.wsgi on {host}:{port} ({threads} threads)")
    serve(application, host=host, port=port, threads=threads)


if __name__ == "__main__":
    main()
