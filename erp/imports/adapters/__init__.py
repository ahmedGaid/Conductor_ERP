"""Import adapters — one module per business app, registered at app ``ready()``.

Entities WITHOUT a GL-correct, drafts-only module service write-path are deliberately not built here
(Before-You-Start STOP rule: STOP rather than invent a second write-path or one that misstates the
books; recorded as blockers in ``erp-status``, trivial to add once each module grows the service):

* Master data (FILE_05): ``item_categories`` / ``warehouses`` (``erp.inventory`` only has inline
  ``Model.objects.create`` in its API view, no contract function), ``price_lists`` (same in
  ``erp.pricing``), ``units`` (no ``UnitOfMeasure`` model — ``Item.uom`` is free text).
* Finance (FILE_16): ``payments`` / ``receipts`` (only order-attached write-paths, which POST to
  the GL and need an already-invoiced/billed order — no standalone/unallocated payment model), and
  ``inventory_opening`` / ``inventory_transactions`` (no draft inventory-opening service;
  ``receive``/``adjust`` post immediately and would double-count the Inventory control account
  ``account_opening`` books, and weighted-average costing has no as-of-date for backdated
  movements). See ``adapters/accounting.py`` for the full reasoning.
"""
from __future__ import annotations

# Importing each module runs its ``register(...)`` calls — that import IS the registration.
from . import accounting, crm, inventory, purchasing, sales  # noqa: F401

__all__: list[str] = []
