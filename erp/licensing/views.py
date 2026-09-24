"""License API: any signed-in user reads the state; only System Admin installs a key."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import ValidationError as AppValidationError
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from .core import LicenseKeyError
from .serializers import InstallLicenseSerializer, state_payload
from .services import install_key
from .state import current_state


def _envelope(data) -> Response:
    return Response({"data": data})


class LicenseView(APIView):
    """GET: state + edition + dates, no key text. POST: paste a key (System Admin only)."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasAnyRole.require(SYSTEM_ADMIN)()]
        return [IsAuthenticated()]

    def get(self, request: Request) -> Response:
        return _envelope(state_payload(current_state()))

    def post(self, request: Request) -> Response:
        s = InstallLicenseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            install_key(s.validated_data["key"], actor=request.user)
        except LicenseKeyError as exc:
            raise AppValidationError(f"License rejected ({exc.reason}).", data={"reason": exc.reason}) from exc
        return _envelope(state_payload(current_state()))
