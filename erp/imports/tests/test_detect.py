"""Dataset detection: deterministic wins spend no model call; only a genuinely ambiguous file
consults the model, exactly once, and an off-registry model answer is discarded."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from erp.imports import detect, registry
from erp.imports.detect import detect_entity
from erp.imports.registry import FieldSpec


def _adapter(entity, fields):
    return SimpleNamespace(entity=entity, fields=fields)


CUSTOMERS = _adapter("customers", [
    FieldSpec(name="name", required=True,
              synonyms_en=["name", "customer", "client"], synonyms_ar=["الاسم", "العميل"]),
    FieldSpec(name="phone", required=True, synonyms_en=["phone"], synonyms_ar=["الهاتف"]),
    FieldSpec(name="email", synonyms_en=["email"], synonyms_ar=["البريد"]),
])
INVOICES = _adapter("invoices", [
    FieldSpec(name="invoice_number", required=True,
              synonyms_en=["invoice no"], synonyms_ar=["رقم الفاتورة"]),
    FieldSpec(name="customer", required=True, synonyms_en=["customer"], synonyms_ar=["العميل"]),
    FieldSpec(name="total", synonyms_en=["total", "amount"], synonyms_ar=["الاجمالي"]),
])


@pytest.fixture(autouse=True)
def _registry():
    saved = dict(registry.REGISTER)
    registry.REGISTER.clear()
    registry.register(CUSTOMERS)
    registry.register(INVOICES)
    try:
        yield
    finally:
        registry.REGISTER.clear()
        registry.REGISTER.update(saved)


@pytest.fixture
def no_model(monkeypatch):
    """complete_json is fatal here — proves the deterministic path never touches the model."""
    fake = Mock(side_effect=AssertionError("model must not be called on a clear detection"))
    monkeypatch.setattr(detect, "complete_json", fake)
    return fake


def test_arabic_customer_file_detected_deterministically(no_model):
    result = detect_entity(None, ["الاسم", "الهاتف", "البريد"], [])
    assert result.method == "deterministic"
    assert result.top.entity == "customers"
    assert result.top.confidence >= 70
    no_model.assert_not_called()


def test_invoice_file_detected_deterministically(no_model):
    result = detect_entity(None, ["رقم الفاتورة", "العميل", "الاجمالي"], [])
    assert result.method == "deterministic"
    assert result.top.entity == "invoices"
    no_model.assert_not_called()


def test_ambiguous_file_consults_model_once(monkeypatch):
    fake = Mock(return_value={"entity": "invoices", "confidence": 88, "reason": "has a total"})
    monkeypatch.setattr(detect, "complete_json", fake)

    result = detect_entity(None, ["customer", "amount"], [{"customer": "أحمد", "amount": "500"}])

    fake.assert_called_once()
    assert result.method == "model"
    assert result.top.entity == "invoices"
    assert result.top.confidence == 88


def test_model_naming_unregistered_entity_is_discarded(monkeypatch):
    fake = Mock(return_value={"entity": "spaceships", "confidence": 99})
    monkeypatch.setattr(detect, "complete_json", fake)

    result = detect_entity(None, ["customer", "amount"], [])

    fake.assert_called_once()
    assert result.method == "deterministic"  # off-list answer thrown away
    assert result.top.entity in {"customers", "invoices"}
