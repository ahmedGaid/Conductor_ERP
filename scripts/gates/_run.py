"""Gate harness.

Usage:
    python scripts/gates/_run.py 00
    python scripts/gates/_run.py all

Each gate module ``gateNN`` exports ``def check() -> None`` that raises on any failure.
The harness runs it, prints ``GATE NN PASSED`` and exits 0, or prints the failure and exits 1.
No interactivity — the green gate is the approval to advance.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALL_GATES = ["00", "01"]  # extended as later phases land


def _bootstrap_django() -> None:
    sys.path.insert(0, str(REPO_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    import django

    django.setup()


def run_one(phase: str) -> bool:
    try:
        module = importlib.import_module(f"scripts.gates.gate{phase}")
    except ModuleNotFoundError:
        print(f"GATE {phase} MISSING: no scripts/gates/gate{phase}.py")
        return False
    try:
        module.check()
    except Exception as exc:  # noqa: BLE001
        print(f"GATE {phase} FAILED: {type(exc).__name__}: {exc}")
        return False
    print(f"GATE {phase} PASSED")
    return True


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/gates/_run.py <NN|all>")
        return 2
    _bootstrap_django()
    phases = ALL_GATES if argv[1] == "all" else [argv[1]]
    for phase in phases:
        if not run_one(phase):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
