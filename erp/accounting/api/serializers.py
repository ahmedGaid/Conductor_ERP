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


class FixedAssetSerializer(serializers.Serializer):
    """Read representation of a fixed asset (amounts integer minor units)."""

    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField(allow_blank=True)
    acquisition_date = serializers.DateField()
    in_service_date = serializers.DateField()
    cost_minor = serializers.IntegerField()
    salvage_minor = serializers.IntegerField()
    useful_life_months = serializers.IntegerField()
    accumulated_depreciation_minor = serializers.IntegerField()
    net_book_value_minor = serializers.IntegerField()
    months_depreciated = serializers.IntegerField()
    status = serializers.CharField()
    acquire_journal_number = serializers.CharField()
    disposed_date = serializers.DateField(allow_null=True)
    disposal_proceeds_minor = serializers.IntegerField(allow_null=True)
    disposal_gain_loss_minor = serializers.IntegerField(allow_null=True)
    disposal_journal_number = serializers.CharField(allow_blank=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "category": obj.category,
            "acquisition_date": obj.acquisition_date,
            "in_service_date": obj.in_service_date,
            "cost_minor": obj.cost_minor,
            "salvage_minor": obj.salvage_minor,
            "useful_life_months": obj.useful_life_months,
            "accumulated_depreciation_minor": obj.accumulated_depreciation_minor,
            "net_book_value_minor": obj.net_book_value_minor,
            "months_depreciated": obj.months_depreciated,
            "status": obj.status,
            "acquire_journal_number": obj.acquire_journal_number,
            "disposed_date": obj.disposed_date,
            "disposal_proceeds_minor": obj.disposal_proceeds_minor,
            "disposal_gain_loss_minor": obj.disposal_gain_loss_minor,
            "disposal_journal_number": obj.disposal_journal_number,
        }


class FixedAssetCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    acquisition_date = serializers.DateField()
    in_service_date = serializers.DateField(required=False, allow_null=True)
    cost_minor = serializers.IntegerField(min_value=1)
    salvage_minor = serializers.IntegerField(min_value=0, required=False, default=0)
    useful_life_months = serializers.IntegerField(min_value=1)
    funding_account_code = serializers.CharField(max_length=32, required=False, default="1000")


class DepreciationRunSerializer(serializers.Serializer):
    period_code = serializers.CharField(max_length=16)
    date = serializers.DateField()


class AssetDisposeSerializer(serializers.Serializer):
    disposed_date = serializers.DateField()
    proceeds_minor = serializers.IntegerField(min_value=0)
    proceeds_account_code = serializers.CharField(max_length=32, required=False, default="1000")


class CostCenterSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    is_active = serializers.BooleanField(required=False, default=True)

    def to_representation(self, obj) -> dict:
        return {"id": str(obj.id), "code": obj.code, "name": obj.name, "is_active": obj.is_active}


class ReportDefinitionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=200)
    account_type = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    account_codes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to = serializers.DateField(required=False, allow_null=True)
    group_by = serializers.ChoiceField(choices=["account", "period"], required=False, default="account")
    schedule = serializers.ChoiceField(choices=["none", "daily", "weekly", "monthly"],
                                       required=False, default="none")
    last_run_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id), "name": obj.name, "account_type": obj.account_type,
            "account_codes": obj.account_codes, "date_from": obj.date_from, "date_to": obj.date_to,
            "group_by": obj.group_by, "schedule": obj.schedule, "last_run_at": obj.last_run_at,
        }


class BudgetSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=200)
    fiscal_year_code = serializers.CharField(max_length=16)
    is_active = serializers.BooleanField(required=False, default=True)

    def to_representation(self, obj) -> dict:
        return {"id": str(obj.id), "name": obj.name,
                "fiscal_year_code": obj.fiscal_year_code, "is_active": obj.is_active}


class BudgetLineSetSerializer(serializers.Serializer):
    account_code = serializers.CharField(max_length=32)
    period_code = serializers.CharField(max_length=16)
    amount_minor = serializers.IntegerField(min_value=0)


class BankLineInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount_minor = serializers.IntegerField()  # signed
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class BankStatementCreateSerializer(serializers.Serializer):
    account_code = serializers.CharField(max_length=32)
    statement_date = serializers.DateField()
    opening_balance_minor = serializers.IntegerField(required=False, default=0)
    closing_balance_minor = serializers.IntegerField()
    reference = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    lines = BankLineInputSerializer(many=True, required=False, default=list)


class BankAdjustmentSerializer(serializers.Serializer):
    amount_minor = serializers.IntegerField()  # signed, non-zero
    contra_account_code = serializers.CharField(max_length=32)
    memo = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    date = serializers.DateField(required=False, allow_null=True)


class BankMatchSerializer(serializers.Serializer):
    journal_line_id = serializers.IntegerField()


class JournalLineInputSerializer(serializers.Serializer):
    account_code = serializers.CharField(max_length=32)
    debit = serializers.IntegerField(min_value=0, default=0)
    credit = serializers.IntegerField(min_value=0, default=0)
    memo = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    cost_center_code = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


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
    cost_center_code = serializers.CharField()

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
    party_type = serializers.CharField()
    party_code = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_period_code(self, obj) -> str:
        return obj.period.code

    def get_lines(self, obj) -> list:
        # Read from the prefetched, ordered, account-joined cache (see _LINES_PREFETCH in the views)
        # so listing many entries doesn't issue a query per entry.
        return JournalLineSerializer(obj.lines.all(), many=True).data
