from __future__ import annotations

from rest_framework import serializers


class InstallLicenseSerializer(serializers.Serializer):
    key = serializers.CharField(trim_whitespace=False, max_length=8192)


def state_payload(state) -> dict:
    """GET /api/license/ shape. Never includes ``key_text`` — the DB row's raw key never leaves
    the server."""
    return {
        "status": state.status,
        "edition": state.edition,
        "modules": list(state.modules),
        "max_branches": state.max_branches,
        "maintenance_active": state.maintenance_active,
        "maintenance_until": state.maintenance_until,
        "ai_active": state.ai_active,
        "ai_until": state.ai_until,
        "trial_days_left": state.trial_days_left,
        "invalid_reason": state.invalid_reason,
    }
