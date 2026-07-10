"""Gateway invariant (Phase 2, T2.1): ``client.py`` is the raw provider seam, ``gateway/`` is the
only module that dispatches across it. Everything else routes through ``gateway.core``.

A handful of files are allowlisted because they aren't provider *dispatch* — they read a config
flag (``client.enabled()``) or haven't been migrated yet for a documented reason:

- ``api/views.py``, ``management/commands/record_evals.py``, ``management/commands/calibrate_judge.py``,
  ``management/commands/eval_routing.py`` — only call ``client.enabled()``, a settings check, not a call.
- ``services/extraction.py`` — its own single-provider (no failover) retry design, structurally
  different from the gateway's chain-walk; migrating it is future work, not a T2.1 rename.
- ``services/knowledge.py`` — still calls ``client.embed_text`` directly (its tests monkeypatch
  ``knowledge.client.embed_text``); tracked for a later embed-cache task (T2.8).
"""
from __future__ import annotations

import ast
from pathlib import Path

ASSISTANT_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_DIRECT_CLIENT_IMPORTS = {
    "api/views.py",
    "management/commands/record_evals.py",
    "management/commands/calibrate_judge.py",
    "management/commands/eval_routing.py",
    "services/extraction.py",
    "services/knowledge.py",
}

_EXCLUDED_DIRS = {"gateway", "tests", "migrations", "__pycache__"}


def _imports_client_module(tree: ast.AST) -> bool:
    """True if the parsed module imports ``erp.assistant.client`` (any relative/absolute spelling)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in ("erp.assistant.client", "client") and node.level >= 0:
                if module == "client" and node.level == 0:
                    continue  # an unrelated top-level `client` package, not ours
                return True
            if module in ("erp.assistant", "") and node.level >= 1:
                if any(alias.name == "client" for alias in node.names):
                    return True
            if module == "erp.assistant" and node.level == 0:
                if any(alias.name == "client" for alias in node.names):
                    return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "erp.assistant.client":
                    return True
    return False


def _find_violations() -> list[str]:
    violations = []
    for path in ASSISTANT_ROOT.rglob("*.py"):
        rel = path.relative_to(ASSISTANT_ROOT)
        if rel.name == "client.py" and len(rel.parts) == 1:
            continue
        if any(part in _EXCLUDED_DIRS for part in rel.parts[:-1]):
            continue
        posix = rel.as_posix()
        if posix in ALLOWED_DIRECT_CLIENT_IMPORTS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _imports_client_module(tree):
            violations.append(posix)
    return violations


def test_only_gateway_and_allowlisted_files_import_client():
    violations = _find_violations()
    assert violations == [], (
        f"these files import erp.assistant.client directly, bypassing the gateway: {violations} "
        "— route them through erp.assistant.gateway.core instead, or add them to "
        "ALLOWED_DIRECT_CLIENT_IMPORTS with a reason."
    )


def test_checker_flags_a_relative_client_import():
    tree = ast.parse("from ..client import complete_json\n")
    assert _imports_client_module(tree) is True


def test_checker_flags_a_from_package_import():
    tree = ast.parse("from .. import client\n")
    assert _imports_client_module(tree) is True


def test_checker_flags_an_absolute_import():
    tree = ast.parse("from erp.assistant.client import model_id\n")
    assert _imports_client_module(tree) is True


def test_checker_ignores_unrelated_imports():
    tree = ast.parse("from . import files\nfrom ..errors import AssistantUnavailableError\n")
    assert _imports_client_module(tree) is False
