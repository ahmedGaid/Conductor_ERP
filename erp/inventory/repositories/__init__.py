"""Data-access boundary for inventory."""
from __future__ import annotations

from erp.core.repository import Repository

from ..domain.models import Item, StockBalance, Warehouse


class ItemRepository(Repository[Item]):
    model = Item

    def by_sku(self, sku: str) -> Item | None:
        return self.model._default_manager.filter(sku=sku).first()


class WarehouseRepository(Repository[Warehouse]):
    model = Warehouse

    def by_code(self, code: str) -> Warehouse | None:
        return self.model._default_manager.filter(code=code).first()


class StockBalanceRepository(Repository[StockBalance]):
    model = StockBalance

    def for_pair(self, item, warehouse) -> StockBalance | None:
        return self.model._default_manager.filter(item=item, warehouse=warehouse).first()

    def total_value(self) -> int:
        from django.db.models import Sum

        return self.model._default_manager.aggregate(v=Sum("value_minor"))["v"] or 0


items = ItemRepository()
warehouses = WarehouseRepository()
balances = StockBalanceRepository()
