"""Root URL configuration.

Each module owns its own urls.py and is mounted here under a stable prefix.
"""
from django.contrib import admin
from django.urls import include, path

from .spa import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health / monitoring (no auth) — Stage 0.
    path("", include("erp.monitoring.urls")),
    # Identity / auth API — Stage 1 (skeleton mounted now).
    path("api/identity/", include("erp.identity.urls")),
    # Cross-module helpers (business-key → id resolver for universal entity links).
    path("api/core/", include("erp.core.resolve_api")),
    # Workflow / instance API — Stage 4 (platform screens backend).
    path("api/workflow/", include("erp.workflow.urls")),
    # Accounting / GL API — Stage 5.
    path("api/accounting/", include("erp.accounting.api.urls")),
    # Inventory API — Stage 5c.
    path("api/inventory/", include("erp.inventory.api.urls")),
    # Pricing (price lists + resolution) API — Growth 3.1b.
    path("api/pricing/", include("erp.pricing.api.urls")),
    # Sales API — Stage 5d.
    path("api/sales/", include("erp.sales.api.urls")),
    # Purchasing API — Stage 5e.
    path("api/purchasing/", include("erp.purchasing.api.urls")),
    # CRM API — Stage 5f.
    path("api/crm/", include("erp.crm.api.urls")),
    # E-invoicing (ETA) API — Stage 6 (compliance).
    path("api/einvoice/", include("erp.einvoice.api.urls")),
    # Notifications & integration adapters — Phase 8.
    path("api/", include("erp.notifications.api.urls")),
    # First-run self-serve setup wizard — Growth Phase 1.
    path("api/setup/", include("erp.setup.urls")),
    # Built React SPA at the site root (Phase 11). Last, so admin/api/health win; the HashRouter
    # keeps every client route in the URL fragment, so only "" ever reaches the server.
    path("", spa_index, name="spa"),
]
