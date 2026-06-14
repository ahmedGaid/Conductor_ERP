"""Accounting API serializers. Amounts are integer minor units throughout (no floats on the wire)."""
from __future__ import annotations

from rest_framework import serializers

from ..domain.accounts import AccountType
from ..domain.models import PeriodStatus


class AccountSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=AccountType.choices)
    parent_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_postable = serializers.BooleanField(required=False, default=True)
    is_active = serializers.BooleanField(required=False, default=True)
    is_cash = serializers.BooleanField(required=False, default=False)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "type": obj.type,
            "parent_code": obj.parent.code if obj.parent_id else None,
            "is_postable": obj.is_postable,
            "is_active": obj.is_active,
            "is_cash": obj.is_cash,
            "currency": obj.currency,
        }


class FiscalYearSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=16)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_closed = serializers.BooleanField(read_only=True)


class PeriodSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    fiscal_year_code = serializers.CharField()
    code = serializers.CharField(max_length=16)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    status = serializers.ChoiceField(choices=PeriodStatus.choices, required=False)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "fiscal_year_code": obj.fiscal_year.code,
            "code": obj.code,
            "start_date": obj.start_date,
            "end_date": obj.end_date,
            "status": obj.status,
        }


class JournalLineInputSerializer(serializers.Serializer):
    account_code = serializers.CharField(max_length=32)
    debit = serializers.IntegerField(min_value=0, default=0)
    credit = serializers.IntegerField(min_value=0, default=0)
    memo = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class JournalPostSerializer(serializers.Serializer):
    date = serializers.DateField()
    memo = serializers.CharField(required=False, allow_blank=True, default="")
    reference = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    source = serializers.CharField(max_length=32, required=False, default="manual")
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    period_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    lines = JournalLineInputSerializer(many=True)


class JournalLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    account_code = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    debit = serializers.IntegerField()
    credit = serializers.IntegerField()
    memo = serializers.CharField()

    def get_account_code(self, obj) -> str:
        return obj.account.code

    def get_account_name(self, obj) -> str:
        return obj.account.name


class JournalEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    date = serializers.DateField()
    period_code = serializers.SerializerMethodField()
    currency = serializers.CharField()
    memo = serializers.CharField()
    reference = serializers.CharField()
    source = serializers.CharField()
    status = serializers.CharField()
    posted_at = serializers.DateTimeField()
    lines = serializers.SerializerMethodField()

    def get_period_code(self, obj) -> str:
        return obj.period.code

    def get_lines(self, obj) -> list:
        return JournalLineSerializer(obj.lines.select_related("account").order_by("line_no"), many=True).data
