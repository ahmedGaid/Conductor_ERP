"""Write-path invariant (ai-reliability T4.1, same shape as the T2.1 gateway invariant).

``services/memory.py`` is the only module allowed to touch ``UserMemory``/``OrgMemory`` directly.
Anything else — a view, another service, a management command — goes through ``remember``/``forget``/
``recall`` so the whitelist, the audit event and the actor scope can never be bypassed by a new call
site. Tests and migrations are excluded (they assert on, and create, the tables by definition).
"""
from __future__ import annotations

import ast
from pathlib import Path

ERP_ROOT = Path(__file__).resolve().parent.parent.parent

MEMORY_MODELS = {"UserMemory", "OrgMemory"}
ALLOWED_MEMORY_MODEL_IMPORTS = {"assistant/services/memory.py"}
_EXCLUDED_DIRS = {"migrations", "__pycache__"}


def _imports_memory_models(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if any(alias.name in MEMORY_MODELS for alias in node.names):
                return True
        elif isinstance(node, ast.Attribute):
            # ``models.UserMemory.objects...`` — the module-import spelling of the same thing.
            if node.attr in MEMORY_MODELS:
                return True
    return False


def _find_violations() -> list[str]:
    violations = []
    for path in ERP_ROOT.rglob("*.py"):
        rel = path.relative_to(ERP_ROOT)
        parts = rel.parts
        if any(part in _EXCLUDED_DIRS for part in parts[:-1]):
            continue
        if "tests" in parts or rel.name.startswith("test_"):
            continue
        if rel.name == "models.py":
            continue  # where the models are defined
        posix = rel.as_posix()
        if posix in ALLOWED_MEMORY_MODEL_IMPORTS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _imports_memory_models(tree):
            violations.append(posix)
    return violations


def test_only_the_memory_service_touches_the_memory_models():
    violations = _find_violations()
    assert violations == [], (
        f"these modules reach the memory tables directly: {violations} — go through "
        "erp.assistant.services.memory (remember/forget/recall) so the write whitelist, the audit "
        "event and the actor scope still hold."
    )


def test_checker_flags_a_direct_model_import():
    assert _imports_memory_models(ast.parse("from ..models import UserMemory\n")) is True


def test_checker_flags_a_module_attribute_write():
    assert _imports_memory_models(
        ast.parse("from .. import models\nmodels.OrgMemory.objects.create()\n")) is True


def test_checker_ignores_the_service_api():
    assert _imports_memory_models(
        ast.parse("from .memory import recall, remember\nrecall(actor)\n")) is False
