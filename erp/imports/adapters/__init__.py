"""Import adapters — one module per business app, registered at app ``ready()``.

Master-data entities WITHOUT a real module service create-path are deliberately not built here
(FILE_05 Before-You-Start rule: STOP on a model-only entity rather than invent a second write-path
from the imports app): ``item_categories`` and ``warehouses`` (``erp.inventory`` only has inline
``Model.objects.create`` in its API view, no contract function), ``price_lists`` (same in
``erp.pricing``), and ``units`` (no ``UnitOfMeasure`` model exists at all — ``Item.uom`` is a free
-text field). Recorded as a blocker in ``erp-status``; the registry makes adding them trivial once
each module grows the service.
"""
from __future__ import annotations

from . import crm, inventory, purchasing, sales  # noqa: F401  (import registers each adapter)

__all__: list[str] = []
