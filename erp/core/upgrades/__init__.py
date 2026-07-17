"""Upgrade step registry: each release's data fixes, applied in order by `manage.py upgrade`.

Every entry is (version, name, run) where `run` performs the fix and MUST be idempotent — the
command may retry after a failure, so a step must be safe to execute more than once. Future
release steps are appended here (or imported from a per-version module, e.g. `v1_1_0.py`,
mirroring Twenty's `upgrade-version-command/<version>/` layout); there are none yet.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class UpgradeStep:
    version: str
    name: str
    run: Callable[[], None]


REGISTRY: list[UpgradeStep] = []
