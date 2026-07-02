"""Pricing ORM models — an Oracle-EBS-*core* price model (lists, tiers, customer overrides).

Pricing owns price lists and customer price assignments. It references **items by SKU string** and
**customers by code string** (never a FK into sales/inventory), and reads tax rates only through the
accounting *contract* — keeping module boundaries clean, exactly as sales does. Prices are integer
minor units in the price list's currency; quantities are Decimal.

The model is deliberately the *core* of EBS pricing: price-list headers + lines with quantity breaks
and effective dates, a per-customer default list (qualifier-lite), and per-customer item overrides
(modifier-lite). Formulas, promotional modifier stacking, and agreement pricing are out of scope and
can layer on later without reshaping these tables. See DECISIONS.md "Pricing engine — Oracle-EBS-core".
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel


class PriceList(AuditedModel):
    """A named set of prices in one currency. Exactly one active list is the default fallback."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=3, default="EGP")
    # Do this list's prices already include VAT? If so the resolver's caller backs it out to net.
    tax_inclusive = models.BooleanField(default=False)
    # The fallback list when a customer has no assignment. The service enforces a single active default.
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "pricing_price_list"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class PriceListLine(AuditedModel):
    """One item's price on a list, with a quantity break and an effective window.

    Overlaps are allowed; the resolver picks the best match deterministically (highest break ≤ qty,
    then latest ``valid_from``, then lowest price). ``valid_from``/``valid_to`` null = open-ended.
    """

    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name="lines")
    item_sku = models.CharField(max_length=64)
    uom = models.CharField(max_length=16, default="unit")
    unit_price_minor = models.BigIntegerField()  # in the list's currency, minor units
    # Quantity break: this price applies when ordered qty >= min_quantity (0 = any qty).
    min_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "pricing_price_list_line"
        ordering = ["price_list", "item_sku", "-min_quantity"]
        indexes = [models.Index(fields=["price_list", "item_sku"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.price_list.code}:{self.item_sku} @ {self.unit_price_minor}"


class CustomerPriceList(AuditedModel):
    """Assigns a customer a default price list (qualifier-lite). One assignment per customer."""

    customer_code = models.CharField(max_length=32, unique=True)
    price_list = models.ForeignKey(PriceList, on_delete=models.PROTECT, related_name="customers")

    class Meta:
        db_table = "pricing_customer_price_list"
        ordering = ["customer_code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer_code} -> {self.price_list.code}"


class CustomerItemPrice(AuditedModel):
    """A negotiated price for one customer + item (modifier-lite). Highest resolution precedence."""

    customer_code = models.CharField(max_length=32)
    item_sku = models.CharField(max_length=64)
    uom = models.CharField(max_length=16, default="unit")
    unit_price_minor = models.BigIntegerField()
    tax_inclusive = models.BooleanField(default=False)
    min_quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "pricing_customer_item_price"
        ordering = ["customer_code", "item_sku", "-min_quantity"]
        indexes = [models.Index(fields=["customer_code", "item_sku"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.customer_code}:{self.item_sku} @ {self.unit_price_minor}"
