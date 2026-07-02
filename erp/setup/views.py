"""First-run setup API views — thin; validation + delegation to services.

The endpoint group the self-serve wizard hangs off. Today it carries setup *state* (status +
finish); the per-step provisioning calls (chart of accounts, tax, invite users) are added by the
later wizard slices and wrap the existing seed/COA/tax/user services rather than re-implementing
them.
"""
from __future__ import annotations

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from . import services


def _envelope(data) -> Response:
    return Response({"data": data})


class TaxSettingsSerializer(serializers.Serializer):
    vat_rate_bps = serializers.IntegerField(required=False, min_value=0, max_value=10000)
    einvoice_enabled = serializers.BooleanField(required=False)


class InviteUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    role = serializers.CharField(required=False, allow_blank=True)


class SetupStatusView(APIView):
    """Whether first-run setup is done. Any authenticated user may read (the route guard calls it)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope(services.get_status())


class SetupChartOfAccountsView(APIView):
    """Provision the baseline chart of accounts (wizard step). System Admin only."""

    permission_classes = [IsAuthenticated, HasAnyRole.require(SYSTEM_ADMIN)]

    def post(self, request: Request) -> Response:
        return _envelope(services.seed_chart_of_accounts())


class SetupTaxView(APIView):
    """Set the standard VAT rate and the e-invoicing toggle (wizard step). System Admin only."""

    permission_classes = [IsAuthenticated, HasAnyRole.require(SYSTEM_ADMIN)]

    def post(self, request: Request) -> Response:
        s = TaxSettingsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return _envelope(services.set_tax_settings(request.user, **s.validated_data))


class SetupInviteUserView(APIView):
    """Invite a team member with a role (wizard step). System Admin only."""

    permission_classes = [IsAuthenticated, HasAnyRole.require(SYSTEM_ADMIN)]

    def post(self, request: Request) -> Response:
        s = InviteUserSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        result = services.invite_user(
            request.user, username=d["username"], email=d["email"], role=d.get("role") or None
        )
        return Response({"data": result}, status=201)


class SetupCompleteView(APIView):
    """Mark first-run setup finished. System Admin only."""

    permission_classes = [IsAuthenticated, HasAnyRole.require(SYSTEM_ADMIN)]

    def post(self, request: Request) -> Response:
        return _envelope(services.mark_complete(request.user))
