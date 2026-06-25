"""Identity API views — thin; validation + delegation to services."""
from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401 (re-exported in urls)

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from . import roles_admin, services, users as user_svc
from .models import Department, Team
from .permissions import HasAnyRole, HasModulePermission
from .roles import ACCOUNTANT, BRANCH_MANAGER, SYSTEM_ADMIN
from .serializers import (
    BulkUsersSerializer,
    CreateRoleSerializer,
    CreateUserSerializer,
    LoginSerializer,
    OrgPreferencesSerializer,
    SetApprovalLimitSerializer,
    SetRolePermissionSerializer,
    UpdateUserSerializer,
    UserPreferencesSerializer,
    UserSerializer,
    Verify2FASerializer,
)

User = get_user_model()


def _can(action: str):
    """RBAC for the admin user-management surface: administration.user.<action>."""
    return HasModulePermission.require(f"administration.user.{action}")


def _envelope(data) -> Response:
    return Response({"data": data})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.login(
            s.validated_data["username"],
            s.validated_data["password"],
            s.validated_data.get("otp_code") or None,
        )
        return _envelope(result)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(UserSerializer(request.user).data)


class Provision2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        uri = services.provision_totp(request.user)
        return _envelope({"otpauth_uri": uri})


class Enable2FAView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        s = Verify2FASerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.enable_2fa(request.user, s.validated_data["code"])
        return _envelope({"is_2fa_enabled": True})


class FinanceSampleView(APIView):
    """RBAC demonstration endpoint — requires an accounting-capable role."""

    permission_classes = [IsAuthenticated, HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)]

    def get(self, request: Request) -> Response:
        return _envelope({"ok": True, "scope": "finance", "user": request.user.username})


class PreferencesView(APIView):
    """The signed-in user's personalization. GET reads; PATCH partially updates."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        prefs = services.get_preferences(request.user)
        return _envelope(UserPreferencesSerializer(prefs).data)

    def patch(self, request: Request) -> Response:
        prefs = services.get_preferences(request.user)
        s = UserPreferencesSerializer(prefs, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        prefs = services.update_preferences(request.user, s.validated_data)
        return _envelope(UserPreferencesSerializer(prefs).data)


class EffectivePreferencesView(APIView):
    """Personal preferences with org defaults filled in — what the UI applies on load."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(services.effective_preferences(request.user))


class OrgPreferencesView(APIView):
    """Organization-wide defaults. Anyone authenticated may read; only System Admin may change."""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasAnyRole.require(SYSTEM_ADMIN)()]
        return [IsAuthenticated()]

    def get(self, request: Request) -> Response:
        org = services.get_org_preferences()
        return _envelope(OrgPreferencesSerializer(org).data)

    def patch(self, request: Request) -> Response:
        org = services.get_org_preferences()
        s = OrgPreferencesSerializer(org, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        org = services.update_org_preferences(request.user, s.validated_data)
        return _envelope(OrgPreferencesSerializer(org).data)


# --- User management (Increment 3) ---

class UsersView(APIView):
    """List + filter users, or create (invite) one."""

    def get_permissions(self):
        return [IsAuthenticated(), _can("create" if self.request.method == "POST" else "view")()]

    def get(self, request: Request) -> Response:
        qs = User.objects.select_related("branch", "department").order_by("username")
        p = request.query_params
        if p.get("search"):
            from django.db.models import Q
            term = p["search"]
            qs = qs.filter(Q(username__icontains=term) | Q(email__icontains=term))
        if p.get("role"):
            qs = qs.filter(groups__name=p["role"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("branch"):
            qs = qs.filter(branch__code=p["branch"])
        if p.get("department"):
            qs = qs.filter(department__code=p["department"])
        return _envelope([user_svc.serialize_list(u) for u in qs.distinct()])

    def post(self, request: Request) -> Response:
        s = CreateUserSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        branch = _branch(d.get("branch"))
        user, temp_password = user_svc.create_user(
            username=d["username"], email=d["email"], role=d.get("role") or None,
            branch=branch, department=d.get("department") or None, team=d.get("team") or None,
            actor=request.user,
        )
        result = user_svc.serialize_detail(user)
        result["temp_password"] = temp_password
        return Response({"data": result}, status=201)


class UserDetailView(APIView):
    """Full profile, or update role/branch/department/team/status."""

    def get_permissions(self):
        return [IsAuthenticated(), _can("edit" if self.request.method == "PATCH" else "view")()]

    def get(self, request: Request, pk: int) -> Response:
        return _envelope(user_svc.serialize_detail(_get_user(pk)))

    def patch(self, request: Request, pk: int) -> Response:
        s = UpdateUserSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        kwargs = {"actor": request.user}
        if "role" in d:
            kwargs["role"] = d["role"] or None
        if "branch" in d:
            kwargs["branch"] = _branch(d["branch"]) if d["branch"] else None
        if "department" in d:
            kwargs["department"] = d["department"] or ""
        if "team" in d:
            kwargs["team"] = d["team"] or ""
        if "status" in d and d["status"]:
            kwargs["status"] = d["status"]
        if "display_name" in d:
            kwargs["display_name"] = d["display_name"]
        if "job_title" in d:
            kwargs["job_title"] = d["job_title"]
        if "phone" in d:
            kwargs["phone"] = d["phone"]
        user = user_svc.update_user(_get_user(pk), **kwargs)
        return _envelope(user_svc.serialize_detail(user))


class UserResetPasswordView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), _can("edit")()]

    def post(self, request: Request, pk: int) -> Response:
        temp_password = user_svc.reset_password(_get_user(pk), actor=request.user)
        return _envelope({"temp_password": temp_password})


class UserRevokeSessionsView(APIView):
    """Revoke all of a user's sessions (force sign-out on every device)."""

    def get_permissions(self):
        return [IsAuthenticated(), _can("edit")()]

    def post(self, request: Request, pk: int) -> Response:
        from . import sessions
        revoked = sessions.revoke_all_sessions(_get_user(pk), actor=request.user)
        return _envelope({"revoked": revoked})


class UserRevokeSessionView(APIView):
    """Revoke a single session (one device) by its outstanding-token id."""

    def get_permissions(self):
        return [IsAuthenticated(), _can("edit")()]

    def post(self, request: Request, pk: int, token_id: int) -> Response:
        from . import sessions
        ok = sessions.revoke_session(_get_user(pk), token_id, actor=request.user)
        if not ok:
            from rest_framework.exceptions import NotFound
            raise NotFound("Session not found")
        return _envelope(user_svc.serialize_detail(_get_user(pk)))


class UsersBulkView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), _can("edit")()]

    def post(self, request: Request) -> Response:
        s = BulkUsersSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        count = user_svc.bulk(d["action"], d["ids"], role=d.get("role") or None, actor=request.user)
        return _envelope({"affected": count})


class OrgUnitsView(APIView):
    """Departments + teams + roles + branches — the option lists the Users UI needs."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from erp.core.models import Branch
        return _envelope({
            "roles": list(Group.objects.order_by("name").values_list("name", flat=True)),
            "branches": [
                {"code": b.code, "name": b.name} for b in Branch.objects.filter(is_active=True)
            ],
            "departments": [
                {"code": d.code, "name": d.name} for d in Department.objects.filter(is_active=True)
            ],
            "teams": [{"code": t.code, "name": t.name} for t in Team.objects.filter(is_active=True)],
        })


# --- Role editor (Increment 4) ---

def _can_role(action: str):
    """RBAC for the role-editor surface: administration.role.<action>."""
    return HasModulePermission.require(f"administration.role.{action}")


class RolesView(APIView):
    """List all roles, or create a new (optionally duplicated) custom role."""

    def get_permissions(self):
        return [IsAuthenticated(), _can_role("create" if self.request.method == "POST" else "view")()]

    def get(self, request: Request) -> Response:
        return _envelope(roles_admin.list_roles())

    def post(self, request: Request) -> Response:
        s = CreateRoleSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        result = roles_admin.create_role(
            d["name"], copy_from=d.get("copy_from") or None, actor=request.user
        )
        return Response({"data": result}, status=201)


class RoleRegistryView(APIView):
    """The vocabulary the editor renders: modules→entities, actions, scopes, document types."""

    def get_permissions(self):
        return [IsAuthenticated(), _can_role("view")()]

    def get(self, request: Request) -> Response:
        return _envelope(roles_admin.registry())


class RoleDetailView(APIView):
    """A role's full grant set, or delete a custom role."""

    def get_permissions(self):
        return [IsAuthenticated(), _can_role("delete" if self.request.method == "DELETE" else "view")()]

    def get(self, request: Request, name: str) -> Response:
        return _envelope(roles_admin.role_detail(name))

    def delete(self, request: Request, name: str) -> Response:
        roles_admin.delete_role(name, actor=request.user)
        return _envelope({"deleted": name})


class RolePermissionView(APIView):
    """Grant or revoke one permission code (with its data scope) on a role."""

    def get_permissions(self):
        return [IsAuthenticated(), _can_role("edit")()]

    def post(self, request: Request, name: str) -> Response:
        s = SetRolePermissionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        result = roles_admin.set_permission(
            name, d["code"], d.get("scope") or "all", d["granted"], actor=request.user
        )
        return _envelope(result)


class RoleApprovalLimitView(APIView):
    """Set, make unlimited, or remove a role's approval ceiling for a document type."""

    def get_permissions(self):
        return [IsAuthenticated(), _can_role("edit")()]

    def post(self, request: Request, name: str) -> Response:
        s = SetApprovalLimitSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if d.get("remove"):
            value = "remove"
        elif d.get("unlimited"):
            value = None  # unlimited
        else:
            value = d.get("limit_minor") or 0
        result = roles_admin.set_approval_limit(name, d["document_type"], value, actor=request.user)
        return _envelope(result)


def _get_user(pk: int):
    from rest_framework.exceptions import NotFound
    try:
        return User.objects.get(pk=pk)
    except User.DoesNotExist:
        raise NotFound("User not found")


def _branch(code: str | None):
    if not code:
        return None
    from rest_framework.exceptions import ValidationError as DRFValidationError
    from erp.core.models import Branch
    try:
        return Branch.objects.get(code=code)
    except Branch.DoesNotExist:
        raise DRFValidationError(f"Unknown branch: {code}")
