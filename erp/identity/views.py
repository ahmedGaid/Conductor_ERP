"""Identity API views — thin; validation + delegation to services."""
from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401 (re-exported in urls)

from . import services
from .permissions import HasAnyRole
from .roles import ACCOUNTANT, BRANCH_MANAGER, SYSTEM_ADMIN
from .serializers import (
    LoginSerializer,
    OrgPreferencesSerializer,
    UserPreferencesSerializer,
    UserSerializer,
    Verify2FASerializer,
)


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
