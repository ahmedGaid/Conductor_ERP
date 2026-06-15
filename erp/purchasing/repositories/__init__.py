"""Data-access boundary for purchasing."""
from __future__ import annotations

from django.db.models import Sum

from erp.core.repository import Repository

from ..domain.models import PurchaseOrder, Supplier


class SupplierRepository(Repository[Supplier]):
    model = Supplier

    def by_code(self, code: str) -> Supplier | None:
        return self.model._default_manager.filter(code=code).first()

    def payable_minor(self, supplier) -> int:
        agg = PurchaseOrder.objects.filter(supplier=supplier).aggregate(
            billed=Sum("billed_minor"), paid=Sum("paid_minor")
        )
        return (agg["billed"] or 0) - (agg["paid"] or 0)


class OrderRepository(Repository[PurchaseOrder]):
    model = PurchaseOrder


suppliers = SupplierRepository()
orders = OrderRepository()
