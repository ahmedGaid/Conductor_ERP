"""First-run setup API views — thin; validation + delegation to services.

The endpoint group the self-serve wizard hangs off. Today it carries setup *state* (status +
finish); the per-step provisioning calls (chart of accounts, tax, invite users) are added by the
later wizard slices and wrap the existing seed/COA/tax/user services rather than re-implementing
them.
"""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from . import services


def _envelope(data) -> Response:
    return Response({"data": data})


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


class SetupCompleteView(APIView):
    """Mark first-run setup finished. System Admin only."""

    permission_classes = [IsAuthenticated, HasAnyRole.require(SYSTEM_ADMIN)]

    def post(self, request: Request) -> Response:
        return _envelope(services.mark_complete(request.user))
