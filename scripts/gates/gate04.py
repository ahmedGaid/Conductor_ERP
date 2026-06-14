"""Gate 04 — platform screens + workflow/instance DRF API.

Asserts:
- the workflow API test suite passes — this is the machine proof of the stage's contract:
  a saved graph round-trips (save -> reload -> identical structure), an instance runs through the
  engine (start -> waiting -> approve/reject), the execution payload carries node-level logs, and
  dashboard metrics reflect real data;
- the API is actually mounted on the project URLconf;
- the React platform screens exist and are wired: a React Flow canvas, an execution viewer that
  renders node-level logs, the typed API client, and the router.

The frontend's build / i18n-parity / token-and-logical-CSS discipline (which also covers these new
screens) is enforced by gate03's full `npm run build` + static scans, so it is not duplicated here.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

API_TESTS = ["erp/workflow/tests/test_api.py"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _read_web(rel: str) -> str:
    return (WEB_SRC / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. The backend API contract (round-trip + lifecycle + node logs + metrics) is test-proven.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *API_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 4 API tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. The workflow API is mounted.
    root_urls = _read("config/urls.py")
    _assert(
        "erp.workflow.urls" in root_urls,
        "workflow API is not mounted in config/urls.py",
    )
    wf_urls = _read("erp/workflow/urls.py")
    for route in ("workflows", "instances", "decision", "dashboard/metrics", "start"):
        _assert(route in wf_urls, f"workflow urls.py missing route fragment: {route!r}")

    # 3. Screens exist and are wired.
    for rel in (
        "App.tsx",
        "api/client.ts",
        "api/workflows.ts",
        "auth/AuthContext.tsx",
        "pages/WorkflowListPage.tsx",
        "pages/WorkflowCanvasPage.tsx",
        "pages/canvas/NodeConfigPanel.tsx",
        "pages/ExecutionViewerPage.tsx",
        "pages/DashboardPage.tsx",
    ):
        _assert((WEB_SRC / rel).is_file(), f"missing frontend file: src/{rel}")

    # 4. The canvas uses React Flow (the planned graph editor).
    canvas = _read_web("pages/WorkflowCanvasPage.tsx")
    _assert("@xyflow/react" in canvas, "canvas does not use React Flow (@xyflow/react)")
    _assert("onConnect" in canvas and "save" in canvas, "canvas missing connect/save wiring")

    # 5. The execution viewer renders the node-level timeline with logs and approve/reject.
    viewer = _read_web("pages/ExecutionViewerPage.tsx")
    _assert("node_runs" in viewer, "execution viewer does not render the node timeline")
    _assert("run.logs" in viewer or ".logs" in viewer, "execution viewer does not render node logs")
    _assert(
        'decide("approve")' in viewer and 'decide("reject")' in viewer,
        "execution viewer missing approve/reject actions",
    )

    # 6. Routing is wired through react-router with the canvas + viewer routes.
    app = _read_web("App.tsx")
    for route in ("/workflows", "/workflows/:id", "/instances/:id"):
        _assert(route in app, f"App.tsx missing route: {route}")

    # 7. Dashboard reads real data from the API (not static text).
    dashboard = _read_web("pages/DashboardPage.tsx")
    _assert(
        "../api/" in dashboard and ("incomeStatement" in dashboard or "getMetrics" in dashboard),
        "dashboard does not load real data from the API",
    )
