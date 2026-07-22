"""Inventory ORM models.

Quantities are exact `Decimal` (items may be fractional, e.g. kg); monetary value is integer
**minor units** (same convention as accounting). A `StockBalance` holds the running on-hand quantity
and total value per item+warehouse; weighted-average unit cost is derived as value / quantity.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel, TimeStampedModel


class ItemType(models.TextChoices):
    STOCK = "stock", "Stock"
    SERVICE = "service", "Service"


class EtaCodeStatus(models.TextChoices):
    """State of the item's ETA product-identity code (FILE_06). ``ACCEPTED`` is the only status the
    e-invoice adapter may use as a live ``itemCode`` — everything else blocks the invoice line rather
    than send a placeholder to the Tax Authority."""
    NOT_SUBMITTED = "not_submitted", "Not submitted"
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class MovementType(models.TextChoices):
    RECEIPT = "receipt", "Receipt"
    ISSUE = "issue", "Issue"
    TRANSFER = "transfer", "Transfer"
    RETURN_IN = "return_in", "Customer return (in)"
    RETURN_OUT = "return_out", "Supplier return (out)"
    ADJUSTMENT = "adjustment", "Count adjustment"
    OPENING = "opening", "Opening balance"


class PendingStockEntryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPLIED = "applied", "Applied"
    DISCARDED = "discarded", "Discarded"


class PendingStockEntryType(models.TextChoices):
    OPENING = "opening", "Opening balance"


class Category(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )

    class Meta:
        db_table = "inventory_category"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class Item(AuditedModel):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT, related_name="items"
    )
    uom = models.CharField(max_length=16, default="unit")  # unit of measure
    type = models.CharField(max_length=16, choices=ItemType.choices, default=ItemType.STOCK)
    is_active = models.BooleanField(default=True)
    reorder_point = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    # Admin-defined extra fields (erp.core.custom_fields) — validated at write time.
    custom_data = models.JSONField(default=dict, blank=True)
    # ETA product identity (FILE_06, EGS path) — a composite code ETA must approve before it can be
    # used as a live itemCode. gpc_code is the GS1 classification the composition is built from.
    gpc_code = models.CharField(max_length=32, blank=True, default="")
    eta_item_code = models.CharField(max_length=64, blank=True, default="")
    eta_code_status = models.CharField(
        max_length=16, choices=EtaCodeStatus.choices, default=EtaCodeStatus.NOT_SUBMITTED,
    )

    class Meta:
        db_table = "inventory_item"
        ordering = ["sku"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.sku} — {self.name}"


class SupplierItemAlias(AuditedModel):
    """Maps one supplier's own code/name for an item to the canonical Conductor ``Item``.

    The same physical item is bought from several suppliers, each using a different code and name —
    often a different language — for it (supplier A: ``Bearing 6205 ZZ`` / ``B-6205``; supplier B:
    ``رولمان بلي 6205`` / ``7788``). Without a record of those supplier-specific identifiers, AI/import
    ingestion resolves an incoming line by raw name alone and, when the name doesn't match, creates a
    DUPLICATE item. This table is that record: ingestion resolves against it FIRST, and every
    human-confirmed match is written back here so the next document from that supplier resolves
    deterministically.

    Supplier is referenced by ``supplier_code`` string (no cross-module FK — the same module-boundary
    rule pricing/sales/purchasing all follow); the canonical item is a same-module FK. A supplier's
    item code is the strongest signal, so it is uniquely constrained per supplier when present; some
    suppliers give only a name, so the code is optional and the uniqueness is partial.
    """

    class Source(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"   # a human confirmed this match during ingestion
        IMPORTED = "imported", "Imported"      # captured from a bulk import
        MANUAL = "manual", "Manual"            # entered by hand

    supplier_code = models.CharField(max_length=32)
    supplier_item_code = models.CharField(max_length=64, blank=True, default="")
    supplier_item_name = models.CharField(max_length=200, blank=True, default="")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="supplier_aliases")
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.CONFIRMED)

    class Meta:
        db_table = "inventory_supplier_item_alias"
        ordering = ["supplier_code", "supplier_item_code"]
        constraints = [
            # One canonical item per (supplier, supplier code) — but only when a code is present;
            # name-only aliases don't collide on an empty code.
            models.UniqueConstraint(
                fields=["supplier_code", "supplier_item_code"],
                condition=~models.Q(supplier_item_code=""),
                name="uniq_supplier_item_code",
            ),
        ]
        indexes = [
            models.Index(fields=["supplier_code", "supplier_item_code"]),
            models.Index(fields=["item"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        label = self.supplier_item_code or self.supplier_item_name
        return f"{self.supplier_code}:{label} -> {self.item_id}"


class Warehouse(AuditedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "inventory_warehouse"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class StockBalance(models.Model):
    """Running on-hand quantity and total value per item+warehouse (weighted average)."""

    id = models.BigAutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="balances")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="balances")
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    value_minor = models.BigIntegerField(default=0)  # total value, minor units

    class Meta:
        db_table = "inventory_stock_balance"
        unique_together = [("item", "warehouse")]
        indexes = [models.Index(fields=["item"]), models.Index(fields=["warehouse"])]


class StockMovement(AuditedModel):
    """An immutable stock event. Receipts carry a unit cost; issues value at weighted average."""

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    # For transfers: the destination warehouse.
    dest_warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    type = models.CharField(max_length=16, choices=MovementType.choices)
    date = models.DateField()
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = models.BigIntegerField(default=0)  # receipts only
    value_minor = models.BigIntegerField(default=0)  # cost moved by this event
    reference = models.CharField(max_length=128, blank=True, default="")
    memo = models.CharField(max_length=255, blank=True, default="")
    # Optional batch/lot traceability (carried on receipts).
    batch_no = models.CharField(max_length=64, blank=True, default="")
    expiry_date = models.DateField(null=True, blank=True)
    # The GL journal this movement posted (entry number), if any.
    journal_number = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "inventory_stock_movement"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["item"]), models.Index(fields=["type"]),
                   models.Index(fields=["batch_no"]),
                   # The movements list orders by these and filters by reference.
                   models.Index(fields=["-date", "-created_at"]),
                   models.Index(fields=["reference"])]


class CountStatus(models.TextChoices):
    COUNTING = "counting", "Counting"   # snapshot taken, entering counts
    POSTED = "posted", "Posted"         # variances adjusted to stock + GL
    CANCELLED = "cancelled", "Cancelled"


class StockCount(AuditedModel):
    """A physical stock count: a snapshot of system quantities, then counted quantities entered, then
    the variances posted as adjustment movements (keeping Inventory GL == stock value)."""

    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="stock_counts")
    count_date = models.DateField()
    reference = models.CharField(max_length=128, blank=True, default="")
    memo = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=CountStatus.choices, default=CountStatus.COUNTING)

    class Meta:
        db_table = "inventory_stock_count"
        ordering = ["-count_date", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Count {self.warehouse_id} @ {self.count_date}"


class TransferStatus(models.TextChoices):
    DRAFT = "draft", "Draft"      # created, stock not yet moved
    POSTED = "posted", "Posted"   # movement created, balances moved
    CANCELLED = "cancelled", "Cancelled"


class StockTransfer(AuditedModel):
    """A drafted move of one item between two warehouses. While ``draft`` no balance/movement exists
    yet — posting it (a later inventory-module feature) is what actually calls ``transfer_stock``."""

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    source = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="+")
    destination = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    date = models.DateField()
    reference = models.CharField(max_length=128, blank=True, default="")
    memo = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=TransferStatus.choices, default=TransferStatus.DRAFT)

    class Meta:
        db_table = "inventory_stock_transfer"
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Transfer {self.item_id}: {self.source_id} -> {self.destination_id}"


class StockCountLine(TimeStampedModel):
    """One item on a stock count: the system snapshot vs the counted quantity and the posted variance."""

    count = models.ForeignKey(StockCount, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    system_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    counted_quantity = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    variance_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    variance_value_minor = models.BigIntegerField(default=0)  # signed: − shortage / + overage
    movement = models.ForeignKey(
        StockMovement, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "inventory_stock_count_line"
        ordering = ["count", "item__sku"]
        unique_together = [("count", "item")]


class PendingStockEntry(AuditedModel):
    """A draftable inventory opening balance: staged by an import (or, later, the AI assistant)
    instead of posting immediately. ``receive_stock`` can't be reused for an opening — it posts
    Dr Inventory / Cr GRNI (a goods-received-not-invoiced liability, wrong for an opening) and would
    double-count the Inventory control account ``account_opening`` already books from the trial
    balance. Applying calls ``services.pending_stock.apply_pending_stock_opening``, which posts to
    ``suspense_account`` instead of GRNI. See DESIGN_PENDING_PAYMENTS_AND_STOCK.md sub-project 2.
    """

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="pending_stock_entries")
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="pending_stock_entries"
    )
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = models.BigIntegerField()
    date = models.DateField()
    type = models.CharField(
        max_length=16, choices=PendingStockEntryType.choices, default=PendingStockEntryType.OPENING,
    )
    status = models.CharField(
        max_length=16, choices=PendingStockEntryStatus.choices, default=PendingStockEntryStatus.PENDING,
    )
    # The suspense account resolved at creation time (from IMPORTS_DEFAULTS) — applying uses this
    # value, not a fresh settings lookup, so a later config change never changes an already-staged
    # entry's posting.
    suspense_account = models.CharField(max_length=32, blank=True, default="")
    batch_ref = models.CharField(max_length=64, blank=True, default="")
    applied_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inventory_pending_stock_entry"
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.item_id} {self.warehouse_id} {self.quantity} ({self.status})"
