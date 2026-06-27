"""Data-access boundary for pricing."""
from __future__ import annotations

from erp.core.repository import Repository

from ..domain.models import CustomerItemPrice, CustomerPriceList, PriceList, PriceListLine


class PriceListRepository(Repository[PriceList]):
    model = PriceList

    def by_code(self, code: str) -> PriceList | None:
        return self.model._default_manager.filter(code=code).first()

    def default(self) -> PriceList | None:
        return self.model._default_manager.filter(is_default=True, is_active=True).first()


class PriceListLineRepository(Repository[PriceListLine]):
    model = PriceListLine

    def for_item(self, price_list: PriceList, item_sku: str):
        return self.model._default_manager.filter(price_list=price_list, item_sku=item_sku)


class CustomerPriceListRepository(Repository[CustomerPriceList]):
    model = CustomerPriceList

    def for_customer(self, customer_code: str) -> CustomerPriceList | None:
        return self.model._default_manager.filter(customer_code=customer_code).first()


class CustomerItemPriceRepository(Repository[CustomerItemPrice]):
    model = CustomerItemPrice

    def for_customer_item(self, customer_code: str, item_sku: str):
        return self.model._default_manager.filter(customer_code=customer_code, item_sku=item_sku)


price_lists = PriceListRepository()
price_list_lines = PriceListLineRepository()
customer_price_lists = CustomerPriceListRepository()
customer_item_prices = CustomerItemPriceRepository()
