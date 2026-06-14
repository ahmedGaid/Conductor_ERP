"""Idempotency key derivation for external-write nodes."""
from __future__ import annotations

import hashlib


def key_for(instance_id, node_id, attempt: int) -> str:
    """sha256 hex of instanceId|nodeId|attempt — stable across retries of the same attempt."""
    raw = f"{instance_id}|{node_id}|{attempt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
