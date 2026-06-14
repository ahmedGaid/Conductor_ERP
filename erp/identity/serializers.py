"""Identity serializers (request validation + read shapes)."""
from __future__ import annotations

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
    otp_code = serializers.CharField(required=False, allow_blank=True)


class Verify2FASerializer(serializers.Serializer):
    code = serializers.CharField()


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    roles = serializers.ListField(child=serializers.CharField())
    is_2fa_enabled = serializers.BooleanField()
    branch = serializers.SerializerMethodField()

    def get_branch(self, obj) -> str | None:
        return obj.branch.code if obj.branch_id else None
