"""Gate 02 — workflow engine + forms.

Asserts:
- the engine/adapters/forms test suite passes (crash-resume, idempotency, edge-selection,
  determinism, approval pause/resume, SQL injection-inert, forms trigger);
- the SQL adapter is parameterized only (no string-built SQL);
- the Script node / jsonlogic contain no eval/exec/compile/__import__;
- the engine has no random.* in control flow (determinism).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

STAGE2_TESTS = ["erp/workflow/tests", "erp/forms/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Test suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *STAGE2_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Stage 2 tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. SQL adapter parameterized only — the execute call must bind params, never build SQL.
    sql_src = _read("erp/workflow/adapters/sql.py")
    _assert("cursor.execute(statement, params)" in sql_src, "sql adapter not using bound params")
    for banned in ("execute(f", "execute(\"", "execute('", ".format(", "statement +", "+ statement", "% ("):
        _assert(banned not in sql_src, f"sql.py builds SQL unsafely: {banned!r}")

    # 3. Script node / jsonlogic are sandboxed — no dynamic code execution.
    for rel in ("erp/workflow/executors/script.py", "erp/workflow/lib/jsonlogic.py"):
        src = _read(rel)
        for banned in ("eval(", "exec(", "compile(", "__import__", "globals(", "getattr("):
            _assert(banned not in src, f"{rel} contains banned dynamic-eval token: {banned!r}")

    # 4. Engine determinism — no randomness in control flow.
    engine_src = _read("erp/workflow/engine/engine.py")
    for banned in ("import random", "random.", "from random"):
        _assert(banned not in engine_src, "engine uses random.* (non-deterministic)")
