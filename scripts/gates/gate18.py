"""Gate 18 -- memory containment (ai-reliability T4.6, BLOCKING from day one).

Runs the ``blocking``-marked memory suite (``erp/assistant/tests/test_memory_leakage.py`` plus the
write-path invariant) and fails the gate on any failure. Unlike the eval gate (15), this one is a
hard blocker immediately: a leak between users, or a new call site writing the memory tables behind
the service, is a privacy defect, not a quality regression.

The suite also runs inside the ordinary ``pytest`` job -- this gate exists so a gate-only run
(``python scripts/gates/_run.py all``) can never advance while containment is broken.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SUITE = (
    "erp/assistant/tests/test_memory_leakage.py",
    "erp/assistant/tests/test_memory_write_path.py",
)


def check() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *SUITE, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    tail = "\n".join(result.stdout.strip().splitlines()[-12:])
    print(f"GATE 18 memory containment:\n{tail}")
    if result.returncode != 0:
        raise AssertionError(
            "memory containment suite failed -- one user's memory can reach another, or a module "
            "outside services/memory.py writes the memory tables. Fix the leak; never relax the test."
        )
