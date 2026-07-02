"""Pricing API views — thin: validate, delegate to repositories/services, return {data}.

RBAC: managing price lists requires a Branch Manager (System Admin / superuser bypass). Resolving a
price (the order/quotation line lookup) only needs an authenticated user — anyone who can write an order.
"""
from __future__ import annotations

from decimal import Decimal

from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.accounting.contracts import find_tax_code
from erp.core.import_api import run_import_request, template_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from ..domain.models import CustomerItemPrice, CustomerPriceList, PriceList, PriceListLine
from ..imports import make_price_list_line_import
from ..services.management import ensure_default_price_list, set_single_default
from ..services.resolve import net_of_tax, resolve_unit_price
from .serializers import (
    CustomerItemPriceSerializer,
    CustomerPriceListSerializer,
    PriceListLineSerializer,
    PriceListSerializer,
    PriceListUpdateSerializer,
)

_CanManage = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _actor(request: Request):
    return request.user if request.user.is_authenticated else None


# ── Price lists ───────────────────────────────────────────────────────────────────────────────────
class PriceListListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def get(self, request: Request) -> Response:
        lists = PriceList.objects.annotate(line_count=Count("lines"))
        return _envelope(PriceListSerializer(lists, many=True).data)

    def post(self, request: Request) -> Response:
        s = PriceListSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        price_list = PriceList.objects.create(
            code=v["code"], name=v["name"], currency=v.get("currency", "EGP"),
            tax_inclusive=v.get("tax_inclusive", False), is_active=v.get("is_active", True),
            created_by=_actor(request),
        )
        if v.get("is_default"):
            set_single_default(price_list)
        return _envelope(PriceListSerializer(price_list).data, status=201)


class PriceListDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def get(self, request: Request, list_id) -> Response:
        price_list = get_object_or_404(PriceList, pk=list_id)
        return _envelope(PriceListSerializer(price_list).data)

    def patch(self, request: Request, list_id) -> Response:
        price_list = get_object_or_404(PriceList, pk=list_id)
        s = PriceListUpdateSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        for field in ("name", "currency", "tax_inclusive", "is_active"):
            if field in v:
                setattr(price_list, field, v[field])
        price_list.updated_by = _actor(request)
        price_list.save()
        if v.get("is_default"):
            set_single_default(price_list)
        return _envelope(PriceListSerializer(price_list).data)


# ── Price-list lines (nested under a list) ──────────────────────────────────────────────────────────
class PriceListLinesView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def get(self, request: Request, list_id) -> Response:
        price_list = get_object_or_404(PriceList, pk=list_id)
        return _envelope(PriceListLineSerializer(price_list.lines.all(), many=True).data)

    def post(self, request: Request, list_id) -> Response:
        price_list = get_object_or_404(PriceList, pk=list_id)
        s = PriceListLineSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        line = PriceListLine.objects.create(
            price_list=price_list, item_sku=v["item_sku"], uom=v.get("uom", "unit"),
            unit_price_minor=v["unit_price_minor"], min_quantity=v.get("min_quantity", 0),
            valid_from=v.get("valid_from"), valid_to=v.get("valid_to"), created_by=_actor(request),
        )
        return _envelope(PriceListLineSerializer(line).data, status=201)


class PriceListLineDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def patch(self, request: Request, line_id) -> Response:
        line = get_object_or_404(PriceListLine, pk=line_id)
        s = PriceListLineSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        for field, value in s.validated_data.items():
            setattr(line, field, value)
        line.updated_by = _actor(request)
        line.save()
        return _envelope(PriceListLineSerializer(line).data)

    def delete(self, request: Request, line_id) -> Response:
        line = get_object_or_404(PriceListLine, pk=line_id)
        line.delete()
        return _envelope(None, status=204)


# ── Customer → price-list assignment ────────────────────────────────────────────────────────────────
class CustomerAssignmentListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def get(self, request: Request) -> Response:
        rows = CustomerPriceList.objects.select_related("price_list")
        return _envelope(CustomerPriceListSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        s = CustomerPriceListSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        price_list = get_object_or_404(PriceList, code=v["price_list_code"])
        # One assignment per customer — upsert so re-assigning just moves the customer.
        row, _ = CustomerPriceList.objects.update_or_create(
            customer_code=v["customer_code"],
            defaults={"price_list": price_list, "updated_by": _actor(request)},
        )
        return _envelope(CustomerPriceListSerializer(row).data, status=201)


class CustomerAssignmentDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def delete(self, request: Request, assignment_id) -> Response:
        row = get_object_or_404(CustomerPriceList, pk=assignment_id)
        row.delete()
        return _envelope(None, status=204)


# ── Per-customer item overrides ─────────────────────────────────────────────────────────────────────
class CustomerItemPriceListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def get(self, request: Request) -> Response:
        rows = CustomerItemPrice.objects.all()
        return _envelope(CustomerItemPriceSerializer(rows, many=True).data)

    def post(self, request: Request) -> Response:
        s = CustomerItemPriceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        row = CustomerItemPrice.objects.create(
            customer_code=v["customer_code"], item_sku=v["item_sku"], uom=v.get("uom", "unit"),
            unit_price_minor=v["unit_price_minor"], tax_inclusive=v.get("tax_inclusive", False),
            min_quantity=v.get("min_quantity", 0), valid_from=v.get("valid_from"),
            valid_to=v.get("valid_to"), created_by=_actor(request),
        )
        return _envelope(CustomerItemPriceSerializer(row).data, status=201)


class CustomerItemPriceDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanManage]

    def delete(self, request: Request, price_id) -> Response:
        row = get_object_or_404(CustomerItemPrice, pk=price_id)
        row.delete()
        return _envelope(None, status=204)


# ── Resolve (the order/quotation line lookup) ───────────────────────────────────────────────────────
class ResolveView(APIView):
    """Resolve the best unit price for a customer+item, backed out to NET if the source is
    tax-inclusive and a tax_code is supplied. Returns {data: null} when nothing applies."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        customer = request.query_params.get("customer", "")
        sku = request.query_params.get("sku", "")
        if not customer or not sku:
            return _envelope(None)
        qty_raw = request.query_params.get("qty")
        quantity = Decimal(qty_raw) if qty_raw else None
        on_raw = request.query_params.get("date")
        currency = request.query_params.get("currency", "EGP")
        from datetime import date as _date

        on = _date.fromisoformat(on_raw) if on_raw else None
        res = resolve_unit_price(customer, sku, on=on, quantity=quantity, currency=currency)
        if res is None:
            return _envelope(None)

        unit_price_minor = res.unit_price_minor
        tax_code = request.query_params.get("tax_code")
        if res.tax_inclusive and tax_code:
            info = find_tax_code(tax_code)
            rate = info.rate_bps if info else 0
            unit_price_minor = net_of_tax(res.unit_price_minor, rate)
        return _envelope(
            {
                "unit_price_minor": unit_price_minor,
                "source": res.source,
                "price_list_code": res.price_list_code,
                "tax_inclusive": res.tax_inclusive,
            }
        )


class PriceListLineImportView(APIView):
    """CSV import for price-list lines — POST to preview, re-post with commit=true to apply."""

    permission_classes = [IsAuthenticated, _CanManage]

    def post(self, request: Request, list_id) -> Response:
        price_list = get_object_or_404(PriceList, pk=list_id)
        spec = make_price_list_line_import(price_list)
        return _envelope(run_import_request(spec, request))


class PriceListLineImportTemplateView(APIView):
    """Download a CSV template (canonical headers + one example row)."""

    permission_classes = [IsAuthenticated, _CanManage]

    def get(self, request: Request, list_id) -> HttpResponse:
        price_list = get_object_or_404(PriceList, pk=list_id)
        spec = make_price_list_line_import(price_list)
        return template_response(spec, f"price-lines-{price_list.code}.csv")


class EnsureDefaultView(APIView):
    """Create the default 'Standard prices' list if the org has none yet — manager-only convenience."""

    permission_classes = [IsAuthenticated, _CanManage]

    def post(self, request: Request) -> Response:
        price_list = ensure_default_price_list()
        return _envelope(PriceListSerializer(price_list).data, status=201)
