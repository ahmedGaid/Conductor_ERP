"""Data-access boundary for sales."""
from __future__ import annotations

from django.db.models import Sum

from erp.core.repository import Repository

from ..domain.models import Customer, SalesOrder


class CustomerRepository(Repository[Customer]):
    model = Customer

    def by_code(self, code: str) -> Customer | None:
        return self.model._default_manager.filter(code=code).first()

    def outstanding_minor(self, customer) -> int:
        agg = SalesOrder.objects.filter(customer=customer).aggregate(
            inv=Sum("invoiced_minor"), paid=Sum("paid_minor")
        )
        return (agg["inv"] or 0) - (agg["paid"] or 0)


class OrderRepository(Repository[SalesOrder]):
    model = SalesOrder


customers = CustomerRepository()
orders = OrderRepository()
