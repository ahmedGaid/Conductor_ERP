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

from ..history import record_timeline_page

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100

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


class RecordTimelineView(APIView):
    """``GET /api/audit/timeline/?entity=&id=&page=&page_size=`` — paginated, newest-first
    activity feed for one record.

    Each item: ``{event, actor, at, params, changes, source}``. ``event`` is the raw audit action
    key (frontend humanizes it via an ``audit.events.<key>`` i18n lookup); ``params`` carries
    identity fields for message interpolation (e.g. an order ``number``); ``changes`` is a
    whitelist diff of meaningful scalar fields, old -> new — never a raw snapshot dump; ``source``
    is ``"ai"``/``"import"``/``null``. The pagination metadata nests under ``data`` alongside the
    items (not as sibling keys) so it survives ``apiFetch``'s generic ``{data}`` envelope unwrap.
    RBAC: the caller must hold read access to the module owning ``entity``.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        entity_type = request.query_params.get("entity", "")
        entity_id = request.query_params.get("id", "")
        module = _MODULE_BY_ENTITY.get(entity_type)
        if not module or not entity_id:
            return Response({"detail": "unknown entity or missing id"}, status=400)
        if module not in access.accessible_modules(request.user):
            return Response({"detail": "forbidden"}, status=403)

        page = max(int(request.query_params.get("page", 1) or 1), 1)
        page_size = min(
            max(int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE), 1),
            MAX_PAGE_SIZE,
        )
        items, total = record_timeline_page(entity_type, entity_id, page=page, page_size=page_size)
        return Response({"data": {"items": items, "page": page, "page_size": page_size, "total": total}})
