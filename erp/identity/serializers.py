"""Identity serializers (request validation + read shapes)."""
from __future__ import annotations

from rest_framework import serializers

from .models import OrgPreferences, UserPreferences


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


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        exclude = ["id", "user"]
        read_only_fields = ["updated_at"]


class OrgPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgPreferences
        exclude = ["id"]
        # is_setup_complete is exposed for reads but only the setup service may flip it.
        read_only_fields = ["updated_at", "is_setup_complete"]


# --- User management (Increment 3) ---

class CreateUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    role = serializers.CharField(required=False, allow_blank=True)
    branch = serializers.CharField(required=False, allow_blank=True)
    department = serializers.CharField(required=False, allow_blank=True)
    team = serializers.CharField(required=False, allow_blank=True)


class UpdateUserSerializer(serializers.Serializer):
    role = serializers.CharField(required=False, allow_blank=True)
    branch = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    department = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    team = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True)
    # Personal profile text (lives on UserPreferences). Blank clears the field.
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    job_title = serializers.CharField(required=False, allow_blank=True, max_length=120)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=40)


class BulkUsersSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["suspend", "activate", "archive", "assign_role"])
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    role = serializers.CharField(required=False, allow_blank=True)


# --- Role editor (Increment 4) ---

class CreateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    copy_from = serializers.CharField(required=False, allow_blank=True)


class SetRolePermissionSerializer(serializers.Serializer):
    code = serializers.CharField()
    scope = serializers.CharField(required=False, allow_blank=True)
    granted = serializers.BooleanField()


class SetApprovalLimitSerializer(serializers.Serializer):
    """Set one document type's ceiling. Exactly one of: a ``limit_minor`` ceiling,
    ``unlimited`` (null limit), or ``remove`` (drop the row entirely)."""

    document_type = serializers.CharField()
    limit_minor = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    unlimited = serializers.BooleanField(required=False, default=False)
    remove = serializers.BooleanField(required=False, default=False)
