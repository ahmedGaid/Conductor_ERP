"""Identity API views — thin; validation + delegation to services."""
from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView  # noqa: F401 (re-exported in urls)

from . import services
from .permissions import HasAnyRole
from .roles import ACCOUNTANT, BRANCH_MANAGER
from .serializers import LoginSerializer, UserSerializer, Verify2FASerializer


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
