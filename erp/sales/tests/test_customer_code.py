"""Auto-generated customer code must never collide (regression, 2026-07-09).

`create_customer(code="")` picks the next free `C-000NN`. The old version ordered codes as strings
and trusted the top row, so imported mixed-width codes (`C-9003`, `C-1050`, a prior auto-gen
`C-09003`) made it hand back a code that already existed — an IntegrityError surfaced to the user as
"That could not be created just now".
"""
from __future__ import annotations

import pytest

from erp.sales import contracts as sales
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def test_auto_code_steps_past_a_taken_same_number_in_another_width():
    Customer.objects.create(code="C-9003", name="nine-thousand-three")
    Customer.objects.create(code="C-09003", name="padded-nine-thousand-three")
    info = sales.create_customer(name="Fresh Customer")
    assert info.code not in {"C-9003", "C-09003"}
    assert info.code == "C-09004"  # numeric max 9003 -> 9004, and 9004 is free


def test_auto_code_uses_numeric_not_string_order():
    # "C-10000" sorts BELOW "C-9999" as a string but is the true numeric max.
    Customer.objects.create(code="C-9999", name="a")
    Customer.objects.create(code="C-10000", name="b")
    info = sales.create_customer(name="c")
    assert info.code == "C-10001"


def test_auto_code_ignores_non_numeric_suffixes():
    Customer.objects.create(code="C-VIP", name="vip")  # not a numbered code
    info = sales.create_customer(name="first-numbered")
    assert info.code == "C-00001"
