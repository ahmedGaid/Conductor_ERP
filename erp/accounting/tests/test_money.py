"""Money value object — exact integer-minor-unit arithmetic, no floats."""
from __future__ import annotations

import pytest

from erp.accounting.domain.money import CurrencyMismatch, Money


def test_format_renders_minor_units():
    assert Money(1050).format() == "10.50 EGP"
    assert Money(5).format() == "0.05 EGP"
    assert Money(-1050).format() == "-10.50 EGP"


def test_addition_and_subtraction():
    assert (Money(100) + Money(50)).minor == 150
    assert (Money(100) - Money(150)).minor == -50


def test_currency_mismatch_raises():
    with pytest.raises(CurrencyMismatch):
        Money(100, "EGP") + Money(100, "USD")


def test_floats_are_rejected():
    with pytest.raises(TypeError):
        Money(10.5)  # type: ignore[arg-type]


def test_bad_currency_rejected():
    with pytest.raises(ValueError):
        Money(100, "EGPP")
