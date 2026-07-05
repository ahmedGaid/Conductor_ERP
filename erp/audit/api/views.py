"""Audit API views — read-only access to the immutable audit trail.

RBAC: the caller must hold access to whichever module owns the entity being inspected — the
per-record timeline never surfaces entries outside modules the user can already reach.
"""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity import access

from ..history import record_timeline

# Which module owns each entity type that a detail page's timeline may ask about. Entity types not
# listed here (or entries with no module owner) are refused with 400 rather than silently empty.
_MODULE_BY_ENTITY: dict[str, str] = {
    "SalesOrder": "sales",
    "Quotation": "sales",
    "Customer": "sales",
    "PurchaseOrder": "purchasing",
    "PurchaseRequest": "purchasing",
    "Supplier": "purchasing",
    "Item": "inventory",
    "Warehouse": "inventory",
    "StockMovement": "inventory",
    "JournalEntry": "accounting",
    "ETAInvoice": "einvoice",
    "Ticket": "crm",
    "Activity": "crm",
    "Opportunity": "crm",
    "Lead": "crm",
    "Campaign": "crm",
    "User": "identity",
    "Role": "identity",
    "Notification": "notifications",
}


class RecordHistoryView(APIView):
    """``GET /api/audit/history?entity_type=&entity_id=`` — last 30 activity entries for one record."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        entity_type = request.query_params.get("entity_type", "")
        entity_id = request.query_params.get("entity_id", "")
        module = _MODULE_BY_ENTITY.get(entity_type)
        if not module or not entity_id:
            return Response({"detail": "unknown entity_type or missing entity_id"}, status=400)
        if module not in access.accessible_modules(request.user):
            return Response({"detail": "forbidden"}, status=403)
        return Response({"data": record_timeline(entity_type, entity_id)})
