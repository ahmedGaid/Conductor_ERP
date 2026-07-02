"""Generic business-key → record-id resolver.

Records expose human keys (an order number, a journal number) in many places across the app, but
their detail routes are keyed by UUID. This endpoint lets any caller link to a record by its human
key without knowing the UUID: ``GET /api/core/resolve?type=sales_order&key=SO-2026-000123`` →
``{"data": {"id": "<uuid>"}}`` (404 if the type is unknown or no record matches).

Models are looked up lazily through the app registry so core stays free of business-module imports.
"""
from __future__ import annotations

from django.apps import apps
from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

# public type → (app_label, model, lookup field). Only number/code-keyed documents whose detail
# route is UUID-keyed need resolving; code-keyed pages (customers, items…) are linked directly.
_TYPES: dict[str, tuple[str, str, str]] = {
    "sales_order": ("sales", "SalesOrder", "number"),
    "purchase_order": ("purchasing", "PurchaseOrder", "number"),
    "journal": ("accounting", "JournalEntry", "number"),
}


class ResolveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        spec = _TYPES.get(request.query_params.get("type", ""))
        key = request.query_params.get("key", "")
        if not spec or not key:
            return Response({"detail": "unknown reference"}, status=404)
        model = apps.get_model(spec[0], spec[1])
        record_id = model.objects.filter(**{spec[2]: key}).values_list("id", flat=True).first()
        if record_id is None:
            return Response({"detail": "not found"}, status=404)
        return Response({"data": {"id": str(record_id)}})


urlpatterns = [path("resolve", ResolveView.as_view(), name="resolve")]
