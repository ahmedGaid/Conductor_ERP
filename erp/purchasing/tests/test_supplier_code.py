"""Auto-generated supplier code must never collide (regression, 2026-07-09).

Twin of the customer-code fix: `create_supplier(code="")` picks the next free `S-000NN` by numeric
max, then steps past any code already taken — string ordering mis-ranked mixed-width codes and could
hand back an existing one (IntegrityError → "That could not be created just now").
"""
from __future__ import annotations

import pytest

from erp.purchasing import contracts as purchasing
from erp.purchasing.domain.models import Supplier

pytestmark = pytest.mark.django_db


def test_auto_code_steps_past_a_taken_same_number_in_another_width():
    Supplier.objects.create(code="S-9003", name="nine-thousand-three")
    Supplier.objects.create(code="S-09003", name="padded-nine-thousand-three")
    info = purchasing.create_supplier(name="Fresh Supplier")
    assert info.code not in {"S-9003", "S-09003"}
    assert info.code == "S-09004"


def test_auto_code_uses_numeric_not_string_order():
    Supplier.objects.create(code="S-9999", name="a")
    Supplier.objects.create(code="S-10000", name="b")
    info = purchasing.create_supplier(name="c")
    assert info.code == "S-10001"
