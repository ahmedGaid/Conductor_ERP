"""Lead → opportunity → win cross-module flow, and the pipeline guards."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.crm.domain.models import LeadStatus, OppStage
from erp.crm.errors import (
    EmptyOpportunityError,
    InvalidTransitionError,
    LeadAlreadyConvertedError,
    UnknownCustomerError,
)
from erp.crm.services import (
    OppLineInput,
    advance_stage,
    convert_lead,
    create_lead,
    create_opportunity,
    lose_opportunity,
    set_lead_status,
    win_opportunity,
)
from erp.sales.domain.models import OrderStatus, SalesOrder

from .factories import make_customer, make_item

pytestmark = pytest.mark.django_db


def _opp_with_lines(customer_code="CUST1"):
    return create_opportunity(
        name="Big deal", customer_code=customer_code, warehouse_code="MAIN",
        lines=[OppLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )


def test_lead_lifecycle_and_convert_creates_opportunity():
    lead = create_lead(name="Jane Doe", company="Initech", source="web")
    assert lead.status == LeadStatus.NEW
    set_lead_status(lead, LeadStatus.QUALIFIED)
    assert lead.status == LeadStatus.QUALIFIED

    opp = convert_lead(lead, opportunity_name="Initech rollout", customer_code="CUST1")
    lead.refresh_from_db()
    assert lead.status == LeadStatus.CONVERTED
    assert opp.is_open
    assert opp.lead_id == lead.id


def test_converted_lead_cannot_convert_again():
    lead = create_lead(name="Repeat")
    convert_lead(lead)
    with pytest.raises(LeadAlreadyConvertedError):
        convert_lead(lead)
    with pytest.raises(LeadAlreadyConvertedError):
        set_lead_status(lead, LeadStatus.CONTACTED)


def test_advance_stage_only_between_open_stages():
    opp = _opp_with_lines()
    advance_stage(opp, OppStage.PROPOSAL)
    assert opp.stage == OppStage.PROPOSAL
    advance_stage(opp, OppStage.NEGOTIATION)
    assert opp.stage == OppStage.NEGOTIATION
    with pytest.raises(InvalidTransitionError):
        advance_stage(opp, OppStage.WON)  # won goes through win_opportunity


def test_win_creates_sales_order_via_contract():
    make_customer()
    make_item()
    opp = _opp_with_lines()
    assert opp.amount_minor == 1500_00

    win_opportunity(opp)
    opp.refresh_from_db()
    assert opp.stage == OppStage.WON
    assert opp.probability == 100
    assert opp.closed_at is not None
    assert opp.sales_order_number.startswith("SO-")

    # The order really exists in Sales, as a draft, with a matching subtotal — created purely
    # through the sales public contract (no CRM→sales ORM coupling).
    so = SalesOrder.objects.get(number=opp.sales_order_number)
    assert so.status == OrderStatus.DRAFT
    assert so.subtotal_minor == opp.amount_minor
    assert so.customer.code == "CUST1"


def test_win_with_unknown_customer_is_rejected():
    make_item()  # item exists but no sales customer "CUST1"
    opp = _opp_with_lines()
    with pytest.raises(UnknownCustomerError):
        win_opportunity(opp)
    opp.refresh_from_db()
    assert opp.is_open  # nothing changed
    assert SalesOrder.objects.count() == 0


def test_win_with_no_lines_requires_order_is_rejected():
    make_customer()
    opp = create_opportunity(name="Service deal", customer_code="CUST1")
    with pytest.raises(EmptyOpportunityError):
        win_opportunity(opp)


def test_win_without_sales_order_just_closes():
    opp = create_opportunity(name="Consulting", customer_code="CUST1")
    win_opportunity(opp, create_sales_order=False)
    opp.refresh_from_db()
    assert opp.stage == OppStage.WON
    assert opp.sales_order_number == ""
    assert SalesOrder.objects.count() == 0


def test_lose_opportunity_closes_pipeline():
    opp = _opp_with_lines()
    lose_opportunity(opp, reason="Budget cut")
    opp.refresh_from_db()
    assert opp.stage == OppStage.LOST
    assert opp.probability == 0
    with pytest.raises(InvalidTransitionError):
        win_opportunity(opp, create_sales_order=False)
