"""Accounting API views — thin: validate, delegate to services, return the {data} envelope.

RBAC: accounting endpoints require an accounting-capable role (Accountant / Branch Manager);
System Admin and superusers bypass (see identity.permissions.HasAnyRole).
"""
from __future__ import annotations

from dataclasses import asdict

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER

from .. import services
from ..domain.models import Account, FiscalYear, JournalEntry, Period
from ..repositories import accounts as account_repo
from .serializers import (
    AccountSerializer,
    FiscalYearSerializer,
    JournalEntrySerializer,
    JournalPostSerializer,
    PeriodSerializer,
)

_CanAccount = HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class AccountListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = Account.objects.all().order_by("code")
        return _envelope(AccountSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        s = AccountSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        parent = None
        if v.get("parent_code"):
            parent = account_repo.by_code(v["parent_code"])
        account = Account.objects.create(
            code=v["code"],
            name=v["name"],
            type=v["type"],
            parent=parent,
            is_postable=v.get("is_postable", True),
            is_active=v.get("is_active", True),
            currency=v.get("currency", "EGP"),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(AccountSerializer(account).data, status=201)


class FiscalYearListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        return _envelope(FiscalYearSerializer(FiscalYear.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = FiscalYearSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        fy = FiscalYear.objects.create(**s.validated_data)
        return _envelope(FiscalYearSerializer(fy).data, status=201)


class PeriodListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        return _envelope(PeriodSerializer(Period.objects.select_related("fiscal_year"), many=True).data)

    def post(self, request: Request) -> Response:
        s = PeriodSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        fy = get_object_or_404(FiscalYear, code=v["fiscal_year_code"])
        period = Period.objects.create(
            fiscal_year=fy,
            code=v["code"],
            start_date=v["start_date"],
            end_date=v["end_date"],
            status=v.get("status", "open"),
        )
        return _envelope(PeriodSerializer(period).data, status=201)


class PeriodCloseView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, code: str) -> Response:
        period = get_object_or_404(Period, code=code)
        period.status = "closed"
        period.save(update_fields=["status"])
        return _envelope(PeriodSerializer(period).data)


class JournalListPostView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = JournalEntry.objects.select_related("period").order_by("-date", "-number")
        period = request.query_params.get("period")
        if period:
            qs = qs.filter(period__code=period)
        return _envelope(JournalEntrySerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = JournalPostSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        data = services.JournalInput(
            date=v["date"],
            memo=v.get("memo", ""),
            reference=v.get("reference", ""),
            source=v.get("source", "manual"),
            currency=v.get("currency", "EGP"),
            period_code=v.get("period_code") or None,
            lines=[
                services.LineInput(
                    account_code=ln["account_code"],
                    debit=ln["debit"],
                    credit=ln["credit"],
                    memo=ln.get("memo", ""),
                )
                for ln in v["lines"]
            ],
        )
        entry = services.post_journal(data, actor=request.user)
        return _envelope(JournalEntrySerializer(entry).data, status=201)


class JournalDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, entry_id) -> Response:
        entry = get_object_or_404(JournalEntry.objects.select_related("period"), id=entry_id)
        return _envelope(JournalEntrySerializer(entry).data)


class TrialBalanceView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        tb = services.trial_balance(
            period_code=request.query_params.get("period") or None,
            as_of=request.query_params.get("as_of") or None,
        )
        return _envelope(
            {
                "rows": [asdict(r) for r in tb.rows],
                "total_debit": tb.total_debit,
                "total_credit": tb.total_credit,
                "is_balanced": tb.is_balanced,
            }
        )


class GeneralLedgerView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        account_code = request.query_params.get("account")
        if not account_code:
            return _envelope({"detail": "account query param required"}, status=400)
        gl = services.general_ledger(
            account_code, period_code=request.query_params.get("period") or None
        )
        return _envelope(
            {
                "account_code": gl.account_code,
                "account_name": gl.account_name,
                "account_type": gl.account_type,
                "opening_balance": gl.opening_balance,
                "closing_balance": gl.closing_balance,
                "lines": [asdict(ln) for ln in gl.lines],
            }
        )
