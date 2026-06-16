r"""Seed demo Sales/Purchasing data for manual testing of returns + partial flows.

Idempotent: master data uses get_or_create; demo orders are only created if none exist yet.
Run AFTER `seed_identity` + `seed_accounting`:

    .\.venv\Scripts\python.exe scripts\seed_demo.py

Leaves orders parked in states that exercise each new capability (partial deliver/receive, returns).
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from erp.inventory.contracts import receive  # noqa: E402
from erp.inventory.domain.models import Item, Warehouse  # noqa: E402
from erp.purchasing.domain.models import Supplier  # noqa: E402
from erp.purchasing.services import (  # noqa: E402
    POLineInput,
    bill_order,
    confirm_order as po_confirm,
    create_order as po_create,
    receive_order,
)
from erp.sales.domain.models import Customer, SalesOrder  # noqa: E402
from erp.sales.services import (  # noqa: E402
    OrderLineInput,
    QuoteLineInput,
    approve_quotation,
    confirm_order as so_confirm,
    create_order as so_create,
    create_quotation,
    deliver_order,
    invoice_order,
    submit_quotation,
)
from erp.sales.domain.models import Quotation, SalesOrderLine  # noqa: E402
from erp.purchasing.domain.models import PurchaseOrder, PurchaseRequest  # noqa: E402
from erp.purchasing.services import (  # noqa: E402
    RequestLineInput,
    approve_request,
    create_request,
    submit_request,
)


def warehouse(code, name):
    wh, _ = Warehouse.objects.get_or_create(code=code, defaults={"name": name})
    return wh


def item(sku, name, uom="unit"):
    it, _ = Item.objects.get_or_create(sku=sku, defaults={"name": name, "type": "stock", "uom": uom})
    return it


def customer(code, name, limit=0):
    c, _ = Customer.objects.get_or_create(code=code, defaults={"name": name, "credit_limit_minor": limit})
    return c


def supplier(code, name):
    s, _ = Supplier.objects.get_or_create(code=code, defaults={"name": name})
    return s


# --- master data (idempotent) ---------------------------------------------------------------
main = warehouse("MAIN", "Main Warehouse")
cairo = warehouse("CAIRO", "Cairo Branch")

widget = item("WIDGET", "Widget")
gadget = item("GADGET", "Gadget")
bolt = item("BOLT", "Bolt (kg)", uom="kg")

acme = customer("ACME", "Acme Corp")
nile = customer("NILE", "Nile Traders", limit=5000_00)
delta = customer("DELTA", "Delta Co")

globex = supplier("GLOBEX", "Globex Supplies")
orient = supplier("ORIENT", "Orient Imports")

created = []


def seed_orders() -> None:
    # Opening stock so sales can deliver (weighted-average cost established).
    receive("WIDGET", "MAIN", Decimal("100"), 80_00, reference="OPENING", memo="Opening stock")
    receive("GADGET", "MAIN", Decimal("50"), 200_00, reference="OPENING", memo="Opening stock")
    receive("BOLT", "MAIN", Decimal("500"), 5_00, reference="OPENING", memo="Opening stock")

    # SO1 — CONFIRMED: test PARTIAL DELIVERY, then return after invoicing.
    so1 = so_create(customer=acme, warehouse_code="MAIN", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("20"), unit_price_minor=150_00),
        OrderLineInput(item_sku="GADGET", quantity=Decimal("5"), unit_price_minor=300_00),
    ])
    so_confirm(so1)
    created.append(("SO", so1.number, "confirmed — try partial Deliver, then Invoice + Return"))

    # SO2 — INVOICED (delivered in full): test RETURN (credit note) directly.
    so2 = so_create(customer=nile, warehouse_code="MAIN", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00),
    ])
    so_confirm(so2)
    deliver_order(so2)
    invoice_order(so2)
    created.append(("SO", so2.number, "invoiced — try Record return (credit note)"))

    # SO3 — PARTIALLY_DELIVERED: test 'Deliver remaining'.
    so3 = so_create(customer=acme, warehouse_code="MAIN", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("8"), unit_price_minor=150_00),
    ])
    so_confirm(so3)
    deliver_order(so3, delivered={1: Decimal("3")})  # 3 of 8 shipped
    created.append(("SO", so3.number, "partially_delivered (3/8) — try Deliver remaining"))

    # SO4 — DRAFT: test the full lifecycle from the start.
    so4 = so_create(customer=delta, warehouse_code="MAIN", lines=[
        OrderLineInput(item_sku="BOLT", quantity=Decimal("100"), unit_price_minor=8_00),
    ])
    created.append(("SO", so4.number, "draft — Confirm -> Deliver -> Invoice -> Payment"))

    # PO1 — CONFIRMED: test PARTIAL RECEIPT, then receive remaining + bill.
    po1 = po_create(supplier=globex, warehouse_code="MAIN", lines=[
        POLineInput(item_sku="WIDGET", quantity=Decimal("40"), unit_cost_minor=80_00),
    ])
    po_confirm(po1)
    created.append(("PO", po1.number, "confirmed — try partial Receive, then Receive remaining + Bill"))

    # PO2 — BILLED (received in full) WITH input VAT: test RETURN (debit note) + see recoverable VAT.
    po2 = po_create(supplier=orient, warehouse_code="MAIN", tax_code="VAT14", lines=[
        POLineInput(item_sku="GADGET", quantity=Decimal("10"), unit_cost_minor=200_00),
    ])
    po_confirm(po2)
    receive_order(po2)
    bill_order(po2)  # net 2,000.00 + 14% VAT 280.00 (recoverable) = gross 2,280.00
    created.append(("PO", po2.number, "billed (VAT14, input VAT 280.00) — try Record return (debit note)"))

    # PO3 — PARTIALLY_RECEIVED: test 'Receive remaining'.
    po3 = po_create(supplier=globex, warehouse_code="CAIRO", lines=[
        POLineInput(item_sku="BOLT", quantity=Decimal("200"), unit_cost_minor=5_00),
    ])
    po_confirm(po3)
    receive_order(po3, received={1: Decimal("120")})  # 120 of 200 received
    created.append(("PO", po3.number, "partially_received (120/200) — try Receive remaining"))


def seed_quotations_and_requests() -> None:
    # QUO1 — large (> 10,000 threshold) → SUBMITTED, awaits approval; then Approve + Convert.
    q1 = create_quotation(customer=acme, warehouse_code="MAIN", lines=[
        QuoteLineInput(item_sku="WIDGET", quantity=Decimal("100"), unit_price_minor=150_00),
    ])
    submit_quotation(q1)
    created.append(("QUO", q1.number, "submitted (>10k) — try Approve, then Convert to order"))

    # QUO2 — small (<= threshold) → auto-APPROVED on submit; ready to Convert.
    q2 = create_quotation(customer=nile, warehouse_code="MAIN", lines=[
        QuoteLineInput(item_sku="GADGET", quantity=Decimal("5"), unit_price_minor=300_00),
    ])
    submit_quotation(q2)
    created.append(("QUO", q2.number, "approved (auto, <=10k) — try Convert to order"))

    # QUO3 — DRAFT: test Submit from the start.
    q3 = create_quotation(customer=delta, warehouse_code="MAIN", lines=[
        QuoteLineInput(item_sku="BOLT", quantity=Decimal("50"), unit_price_minor=8_00),
    ])
    created.append(("QUO", q3.number, "draft — Submit -> (auto-approve) -> Convert"))

    # PR1 — large → SUBMITTED, awaits approval; then Approve + Convert to PO.
    r1 = create_request(supplier=globex, warehouse_code="MAIN", lines=[
        RequestLineInput(item_sku="WIDGET", quantity=Decimal("200"), unit_cost_minor=80_00),
    ])
    submit_request(r1)
    created.append(("PR", r1.number, "submitted (>10k) — try Approve, then Convert to PO"))

    # PR2 — large → SUBMITTED, then explicitly Approve so it's ready to Convert.
    r2 = create_request(supplier=orient, warehouse_code="MAIN", lines=[
        RequestLineInput(item_sku="GADGET", quantity=Decimal("60"), unit_cost_minor=200_00),
    ])
    submit_request(r2)
    approve_request(r2)
    created.append(("PR", r2.number, "approved — try Convert to PO"))


def seed_discounts_and_approval() -> None:
    # SO-disc — DRAFT with a line discount (net below threshold): confirm directly.
    sod = so_create(customer=acme, warehouse_code="MAIN", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00,
                       discount_minor=200_00),  # gross 1,500 - 200 = 1,300.00 net
    ])
    created.append(("SO", sod.number, "draft, line discount 200.00 — Confirm (no approval needed)"))

    # SO-appr — DRAFT above 10,000 threshold: needs Approve before Confirm.
    soa = so_create(customer=acme, warehouse_code="MAIN", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("100"), unit_price_minor=150_00),
    ])  # 15,000.00 > threshold
    created.append(("SO", soa.number, "draft (15,000 > 10k) — Approve, then Confirm"))

    # PO-appr — DRAFT above threshold: needs Approve before Confirm.
    poa = po_create(supplier=globex, warehouse_code="MAIN", lines=[
        POLineInput(item_sku="WIDGET", quantity=Decimal("200"), unit_cost_minor=80_00),
    ])  # 16,000.00 > threshold
    created.append(("PO", poa.number, "draft (16,000 > 10k) — Approve, then Confirm"))


if SalesOrder.objects.exists():
    print("Demo orders already present — skipping order creation (master data ensured).")
else:
    seed_orders()

if SalesOrderLine.objects.filter(discount_minor__gt=0).exists() or \
        SalesOrder.objects.filter(subtotal_minor__gt=1_000_000).exists():
    print("Demo discount/approval orders already present — skipping.")
else:
    seed_discounts_and_approval()


def seed_vat() -> None:
    # SO-vat — DRAFT taxed at VAT 14%: Confirm -> Deliver -> Invoice posts net + output VAT.
    sov = so_create(customer=acme, warehouse_code="MAIN", tax_code="VAT14", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00),
    ])  # net 1,500.00, VAT 210.00 at invoice
    created.append(("SO", sov.number, "draft, VAT14 — Confirm/Deliver/Invoice posts 210.00 output VAT"))


from erp.accounting.domain.models import TaxCode as _TaxCode  # noqa: E402

if not _TaxCode.objects.filter(code="VAT14").exists():
    print("VAT14 tax code missing — run `manage.py seed_accounting` first; skipping VAT demo.")
elif SalesOrder.objects.exclude(tax_code="").exists():
    print("Demo VAT order already present — skipping.")
else:
    seed_vat()


def seed_einvoice() -> None:
    # A fully-invoiced VAT order — invoicing publishes the sales event, which the e-invoicing module
    # subscribes to and records a draft ETA e-invoice (ready to Submit/poll on the E-invoices screen).
    soe = so_create(customer=nile, warehouse_code="MAIN", tax_code="VAT14", lines=[
        OrderLineInput(item_sku="WIDGET", quantity=Decimal("5"), unit_price_minor=150_00),
    ])
    so_confirm(soe)
    deliver_order(soe)
    invoice_order(soe)
    created.append(("SO", soe.number, f"invoiced VAT14 -> ETA e-invoice recorded ({soe.invoice_number})"))


from erp.einvoice.domain.models import ETAInvoice as _ETAInvoice  # noqa: E402

if not _TaxCode.objects.filter(code="VAT14").exists():
    pass
elif _ETAInvoice.objects.exists():
    print("Demo e-invoice already present — skipping.")
else:
    seed_einvoice()


def seed_input_vat() -> None:
    # A taxed purchase order, received + billed: the bill books recoverable INPUT VAT
    # (Dr GRNI / Dr VAT Input / Cr AP). It nets against the sales OUTPUT VAT on the VAT return.
    pov = po_create(supplier=orient, warehouse_code="MAIN", tax_code="VAT14", lines=[
        POLineInput(item_sku="GADGET", quantity=Decimal("10"), unit_cost_minor=200_00),
    ])  # net 2,000.00, input VAT 280.00 at bill
    po_confirm(pov)
    receive_order(pov)
    bill_order(pov)
    created.append(("PO", pov.number, "billed VAT14 -> input VAT 280.00 recoverable (see VAT return)"))


if not _TaxCode.objects.filter(code="VAT14").exists():
    pass
elif PurchaseOrder.objects.exclude(tax_code="").exists():
    print("Demo input-VAT purchase already present — skipping.")
else:
    seed_input_vat()

if Quotation.objects.exists() or PurchaseRequest.objects.exists():
    print("Demo quotations/requests already present — skipping.")
else:
    seed_quotations_and_requests()


def seed_fixed_assets() -> None:
    # Two assets so the register + depreciation run have something to chew on.
    import datetime as _dt

    from erp.accounting.services import AssetInput, acquire_asset, run_depreciation

    today = _dt.date.today()
    acquire_asset(AssetInput(
        code="FA-VAN", name="Delivery Van", category="Vehicles",
        acquisition_date=today, cost_minor=600_000_00, salvage_minor=60_000_00,
        useful_life_months=60,  # 5 years
    ))
    acquire_asset(AssetInput(
        code="FA-LAPTOP", name="Office Laptops", category="IT Equipment",
        acquisition_date=today, cost_minor=90_000_00, salvage_minor=0,
        useful_life_months=36,  # 3 years
    ))
    # Book one month of depreciation in the current period so the register shows accumulated value.
    period_code = f"{today.year}-{today.month:02d}"
    run_depreciation(period_code, today)
    created.append(("FA", "FA-VAN", "fixed asset — try Run depreciation / Dispose"))
    created.append(("FA", "FA-LAPTOP", "fixed asset — depreciated 1 month"))


from erp.accounting.domain.models import FixedAsset as _FixedAsset  # noqa: E402

if _FixedAsset.objects.exists():
    print("Demo fixed assets already present — skipping.")
else:
    seed_fixed_assets()


def seed_bank_rec() -> None:
    # Two posted movements on the Bank (1010) GL account, plus a statement that shows them and a
    # bank-only fee — so the user can Auto-match, Post the fee adjustment, and Mark reconciled.
    import datetime as _dt

    from erp.accounting.services import (
        BankLineInput,
        JournalInput,
        LineInput,
        create_statement,
        post_journal,
    )

    today = _dt.date.today()
    post_journal(JournalInput(date=today, memo="Owner funds into bank", lines=[
        LineInput("1010", debit=50_000_00), LineInput("3000", credit=50_000_00),
    ]))
    post_journal(JournalInput(date=today, memo="Cash sale banked", lines=[
        LineInput("1010", debit=8_000_00), LineInput("4000", credit=8_000_00),
    ]))
    stmt = create_statement(
        account_code="1010", statement_date=today, closing_balance_minor=57_925_00,
        reference="BANK-DEMO",
        lines=[
            BankLineInput(date=today, amount_minor=50_000_00, description="Owner funds"),
            BankLineInput(date=today, amount_minor=8_000_00, description="Card settlement"),
            BankLineInput(date=today, amount_minor=-75_00, description="Monthly account fee"),
        ],
    )
    created.append(("BANK", str(stmt.id)[:8], "statement — Auto-match, post the 75.00 fee (contra 6100), Reconcile"))


from erp.accounting.domain.models import BankStatement as _BankStatement  # noqa: E402

if _BankStatement.objects.exists():
    print("Demo bank statement already present — skipping.")
else:
    seed_bank_rec()


def seed_budget() -> None:
    # A budget for the current fiscal year with a few P&L targets, so Budget-vs-Actual shows variance
    # against the demo's posted sales/expenses.
    import datetime as _dt

    from erp.accounting.services import BudgetLineInput, create_budget, set_budget_lines

    year = _dt.date.today().year
    month = _dt.date.today().month
    period = f"{year}-{month:02d}"
    budget = create_budget(name=f"{year} Operating Plan", fiscal_year_code=str(year))
    set_budget_lines(budget, [
        BudgetLineInput("4000", period, 50_000_00),   # planned sales revenue
        BudgetLineInput("5000", period, 20_000_00),   # planned COGS
        BudgetLineInput("5100", period, 5_000_00),    # planned rent
        BudgetLineInput("5300", period, 1_000_00),    # planned depreciation
    ])
    created.append(("BUDGET", budget.name[:14], "open it -> Budget vs Actual shows variance"))


from erp.accounting.domain.models import Budget as _Budget  # noqa: E402

if _Budget.objects.exists():
    print("Demo budget already present — skipping.")
else:
    seed_budget()

print("\nDemo data created:")
for kind, number, hint in created:
    print(f"  [{kind}] {number:18s} {hint}")
print("\nSign in at http://localhost:5173 as admin / Dev12345!")
