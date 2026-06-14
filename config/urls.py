"""Root URL configuration.

Each module owns its own urls.py and is mounted here under a stable prefix.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Health / monitoring (no auth) — Stage 0.
    path("", include("erp.monitoring.urls")),
    # Identity / auth API — Stage 1 (skeleton mounted now).
    path("api/identity/", include("erp.identity.urls")),
    # Workflow / instance API — Stage 4 (platform screens backend).
    path("api/workflow/", include("erp.workflow.urls")),
    # Accounting / GL API — Stage 5.
    path("api/accounting/", include("erp.accounting.api.urls")),
    # Inventory API — Stage 5c.
    path("api/inventory/", include("erp.inventory.api.urls")),
]
