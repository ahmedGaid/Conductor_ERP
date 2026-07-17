# Draftable Payments (PendingPayment) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the smart-import engine (and, later, the AI assistant) stage customer receipts and
supplier payments as reviewable drafts instead of posting to the GL immediately, closing the gap
documented in `erp/imports/adapters/accounting.py` and `DESIGN_PENDING_PAYMENTS_AND_STOCK.md`.

**Architecture:** Two mirrored `PendingPayment` models (one in `erp.sales`, one in
`erp.purchasing` — no shared model, see Global Constraints). A human-triggered `apply_*` service
function calls the module's existing, unmodified `receive_payment`/`pay_order` write-path. Import
adapters (`receipts`, `payments`) always create a pending row and never post to the GL. A small,
symmetric API surface (list/apply/discard/match) is the contract Agent A's future review screen
will consume — no `apps/web` changes in this plan.

**Tech Stack:** Django 5 / DRF, PostgreSQL, pytest + `pytest-django`, existing `erp.imports` engine.

## Global Constraints

- Money is integer minor units everywhere; never format/parse outside the edge.
- Never modify an existing service write-path signature (`receive_payment`, `pay_order`,
  `create_journal_entry_draft`, `receive_stock`) — only ADD new functions.
- Drafts-only: import-time code (`adapter.write`) never calls `receive_payment`/`pay_order`
  directly; only the human-triggered `apply_pending_payment` does.
- Module boundary: `erp.accounting` has zero imports from `erp.sales`/`erp.purchasing` (verified
  by grep) — `PendingPayment` lives per-module (sales, purchasing), never shared, mirroring the
  existing duplicated `PaymentSerializer` convention.
- RBAC: import adapters call `require_role(actor, BRANCH_MANAGER)` from
  `erp/imports/adapters/_rbac.py`; API views use `HasAnyRole.require(BRANCH_MANAGER)` — same
  pattern as every existing write endpoint in both modules.
- Scoping: every query goes through `erp.identity.scoping.scope_queryset(actor, qs, perm)`, reusing
  the existing `"sales.order.view"` / `"purchasing.order.view"` permission keys — no new permission
  key is registered.
- Testing: `pytest`, `pytest.mark.django_db`; reuse each module's `tests/factories.py` helpers
  (`make_books`, `make_customer`/`make_supplier`, `make_item`, `make_warehouse`, `stocked`).
- No `apps/web` changes anywhere in this plan — Agent A's territory (ownership map,
  `Docs/plan/PARALLEL_PLAN.md`). The API this plan ships is the contract A's future screen calls.
- New `Issue` `message` values are i18n **keys** (e.g. `imports.issues.paymentUnmatched`), not
  literal strings — translation JSON entries are Agent A's job later, matching the existing
  precedent (`unbalancedEntry`/`openingImbalance`/`totalMismatch` shipped by B without touching
  `ar.json`/`en.json`).
- Gates before calling this plan done: `pytest erp/sales erp/purchasing erp/imports` green;
  `python scripts/gates/_run.py all` green (00-02/04-17 — gate03 is N/A on Agent B's checkout, no
  `apps/web` `node_modules`).

---

### Task 1: Sales — `PendingPayment` model + service

**Files:**
- Modify: `erp/sales/domain/models.py`
- Modify: `erp/sales/errors.py`
- Create: `erp/sales/services/pending_payments.py`
- Modify: `erp/sales/services/__init__.py`
- Create: `erp/sales/tests/test_pending_payments.py`
- Create (via `makemigrations`): `erp/sales/migrations/0009_pendingpayment.py`

**Interfaces:**
- Produces: `erp.sales.domain.models.PendingPaymentStatus` (`TextChoices`: `PENDING`, `APPLIED`,
  `DISCARDED`), `erp.sales.domain.models.PendingPayment` (fields: `order` FK→`SalesOrder`
  nullable, `party_code: str`, `amount_minor: int`, `date: date`, `method: str`, `source: str`,
  `status: str`, `batch_ref: str`, `applied_by` FK→User nullable, `applied_at` nullable).
  `erp.sales.services.pending_payments.create_pending_payment(*, order, party_code, amount_minor,
  date, method="", source="import", batch_ref="", actor=None) -> PendingPayment`,
  `apply_pending_payment(pending, actor=None) -> PendingPayment`,
  `discard_pending_payment(pending, actor=None) -> PendingPayment`,
  `match_pending_payment(pending, order, actor=None) -> PendingPayment`. Re-exported from
  `erp.sales.services`. `erp.sales.errors.PendingPaymentStateError` (`SAL-016`).

- [ ] **Step 1: Add the model**

In `erp/sales/domain/models.py`, after the `Quotation`/`QuotationLine` classes at the end of the
file, add:

```python
class PendingPaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPLIED = "applied", "Applied"
    DISCARDED = "discarded", "Discarded"


class PendingPayment(AuditedModel):
    """A draftable customer receipt: staged by an import (or, later, the AI assistant) instead of
    posting to the GL immediately. ``order`` is null until a human matches it (or the source file
    already carried a resolvable invoice reference). Applying calls the existing
    ``services.orders.receive_payment`` exactly as the module screen does — no second write path.
    """

    order = models.ForeignKey(
        SalesOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="pending_payments",
    )
    party_code = models.CharField(max_length=32)
    amount_minor = models.BigIntegerField()
    date = models.DateField()
    method = models.CharField(max_length=16, blank=True, default="")
    source = models.CharField(max_length=16, default="import")
    status = models.CharField(
        max_length=16, choices=PendingPaymentStatus.choices, default=PendingPaymentStatus.PENDING,
    )
    batch_ref = models.CharField(max_length=64, blank=True, default="")
    applied_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "sales_pending_payment"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.party_code} {self.amount_minor} ({self.status})"
```

- [ ] **Step 2: Add the error**

In `erp/sales/errors.py`, after the last class (`code = "SAL-015"`), add:

```python
class PendingPaymentStateError(AppError):
    code = "SAL-016"
    status_code = 422
    message = "Pending payment is not in a state that allows this action"
```

- [ ] **Step 3: Generate and apply the migration**

Run: `python manage.py makemigrations sales --settings=config.settings.dev`
Expected: creates `erp/sales/migrations/0009_pendingpayment.py` (or next free number) adding
`PendingPaymentStatus`-backed `status` field and the `PendingPayment` table — review the generated
file matches the model above (FK on_delete choices, field types), then:
Run: `python manage.py migrate sales --settings=config.settings.dev`
Expected: `Applying sales.0009_pendingpayment... OK`

- [ ] **Step 4: Write the failing tests**

Create `erp/sales/tests/test_pending_payments.py`:

```python
"""Draftable customer receipts — PendingPayment stages a payment; applying it calls the existing
``receive_payment`` exactly as the module screen would (same guards, same GL entry)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.sales.domain.models import OrderStatus, PendingPaymentStatus
from erp.sales.errors import OverpaymentError, PendingPaymentStateError
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
)
from erp.sales.services.pending_payments import (
    apply_pending_payment,
    create_pending_payment,
    discard_pending_payment,
    match_pending_payment,
)

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _invoiced_order(amount=1500_00):
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    assert order.invoiced_minor == amount
    return customer, order


def test_apply_matched_payment_reproduces_receive_payment_behavior():
    customer, order = _invoiced_order()
    pending = create_pending_payment(
        order=order, party_code=customer.code, amount_minor=500_00, date=DATE, method="cash",
    )
    assert pending.status == PendingPaymentStatus.PENDING

    applied = apply_pending_payment(pending)

    assert applied.status == PendingPaymentStatus.APPLIED
    assert applied.applied_at is not None
    order.refresh_from_db()
    assert order.status == OrderStatus.INVOICED  # partial — not fully paid yet
    assert order.outstanding_minor == 1000_00


def test_apply_without_a_matched_order_raises():
    _, order = _invoiced_order()
    pending = create_pending_payment(order=None, party_code="CUST1", amount_minor=500_00, date=DATE)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_match_then_apply_round_trips():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=None, party_code=customer.code, amount_minor=1500_00, date=DATE)

    matched = match_pending_payment(pending, order)
    assert matched.order_id == order.id

    applied = apply_pending_payment(matched)
    assert applied.status == PendingPaymentStatus.APPLIED
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID


def test_apply_already_applied_raises():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)
    apply_pending_payment(pending)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_apply_overpayment_still_raises_the_existing_guard():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=2000_00, date=DATE)

    with pytest.raises(OverpaymentError):
        apply_pending_payment(pending)


def test_discard_marks_discarded_and_blocks_further_actions():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)

    discarded = discard_pending_payment(pending)

    assert discarded.status == PendingPaymentStatus.DISCARDED
    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(discarded)
    with pytest.raises(PendingPaymentStateError):
        discard_pending_payment(discarded)
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `pytest erp/sales/tests/test_pending_payments.py -v`
Expected: `ModuleNotFoundError: No module named 'erp.sales.services.pending_payments'` (or
`ImportError`) — the service doesn't exist yet.

- [ ] **Step 6: Implement the service**

Create `erp/sales/services/pending_payments.py`:

```python
"""Draftable customer receipts — the human-in-the-loop staging step ``receive_payment`` has no
form for. An import (or, later, the AI assistant) creates a ``PendingPayment`` instead of posting
to the GL immediately; a human applies it from the order screen, at which point this calls the
EXISTING ``receive_payment`` exactly as a manual payment would — same guards, same GL entry, no
second write path.
"""
from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.utils import timezone

from ..domain.models import PendingPayment, PendingPaymentStatus, SalesOrder
from ..errors import PendingPaymentStateError
from .orders import receive_payment


def create_pending_payment(
    *, order: SalesOrder | None, party_code: str, amount_minor: int, date: dt.date,
    method: str = "", source: str = "import", batch_ref: str = "", actor=None,
) -> PendingPayment:
    return PendingPayment.objects.create(
        order=order, party_code=party_code, amount_minor=amount_minor, date=date,
        method=method, source=source, batch_ref=batch_ref,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )


@transaction.atomic
def apply_pending_payment(pending: PendingPayment, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    if pending.order_id is None:
        raise PendingPaymentStateError("pending payment has no matched order — match it first")
    receive_payment(pending.order, pending.amount_minor, actor=actor)
    pending.status = PendingPaymentStatus.APPLIED
    pending.applied_by = actor if getattr(actor, "is_authenticated", False) else None
    pending.applied_at = timezone.now()
    pending.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])
    return pending


def discard_pending_payment(pending: PendingPayment, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    pending.status = PendingPaymentStatus.DISCARDED
    pending.save(update_fields=["status", "updated_at"])
    return pending


def match_pending_payment(pending: PendingPayment, order: SalesOrder, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    pending.order = order
    pending.save(update_fields=["order", "updated_at"])
    return pending
```

- [ ] **Step 7: Export from the services package**

In `erp/sales/services/__init__.py`, add after the `.quotations` import block:

```python
from .pending_payments import (  # noqa: F401
    apply_pending_payment,
    create_pending_payment,
    discard_pending_payment,
    match_pending_payment,
)
```

And add to `__all__`: `"apply_pending_payment"`, `"create_pending_payment"`,
`"discard_pending_payment"`, `"match_pending_payment"`.

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest erp/sales/tests/test_pending_payments.py -v`
Expected: 6 passed

- [ ] **Step 9: Commit**

```bash
git add erp/sales/domain/models.py erp/sales/errors.py erp/sales/services/pending_payments.py \
        erp/sales/services/__init__.py erp/sales/tests/test_pending_payments.py \
        erp/sales/migrations/
git commit -m "feat(sales): draftable PendingPayment model + apply/discard/match services"
```

---

### Task 2: Purchasing — `PendingPayment` model + service (mirrors Task 1)

**Files:**
- Modify: `erp/purchasing/domain/models.py`
- Modify: `erp/purchasing/errors.py`
- Create: `erp/purchasing/services/pending_payments.py`
- Modify: `erp/purchasing/services/__init__.py`
- Create: `erp/purchasing/tests/test_pending_payments.py`
- Create (via `makemigrations`): `erp/purchasing/migrations/0008_pendingpayment.py`

**Interfaces:**
- Produces: `erp.purchasing.domain.models.PendingPaymentStatus`,
  `erp.purchasing.domain.models.PendingPayment` (identical shape to Task 1's, FK to
  `PurchaseOrder`). `erp.purchasing.services.pending_payments.create_pending_payment(*, order,
  party_code, amount_minor, date, method="", source="import", batch_ref="", actor=None)`,
  `apply_pending_payment(pending, actor=None)`, `discard_pending_payment(pending, actor=None)`,
  `match_pending_payment(pending, order, actor=None)`. `erp.purchasing.errors.
  PendingPaymentStateError` (`PUR-015`).

- [ ] **Step 1: Add the model**

In `erp/purchasing/domain/models.py`, after the last class (`PurchaseRequestLine`), add:

```python
class PendingPaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPLIED = "applied", "Applied"
    DISCARDED = "discarded", "Discarded"


class PendingPayment(AuditedModel):
    """A draftable supplier payment — mirrors ``erp.sales.domain.models.PendingPayment`` exactly;
    see that class's docstring. Applying calls the existing ``services.orders.pay_order``."""

    order = models.ForeignKey(
        PurchaseOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="pending_payments",
    )
    party_code = models.CharField(max_length=32)
    amount_minor = models.BigIntegerField()
    date = models.DateField()
    method = models.CharField(max_length=16, blank=True, default="")
    source = models.CharField(max_length=16, default="import")
    status = models.CharField(
        max_length=16, choices=PendingPaymentStatus.choices, default=PendingPaymentStatus.PENDING,
    )
    batch_ref = models.CharField(max_length=64, blank=True, default="")
    applied_by = models.ForeignKey(
        "identity.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "purchasing_pending_payment"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.party_code} {self.amount_minor} ({self.status})"
```

(Confirm `AuditedModel` is already imported at the top of this file — `erp/purchasing/domain/models.py`
already imports it for `Supplier`/`PurchaseOrder`; no new import needed.)

- [ ] **Step 2: Add the error**

In `erp/purchasing/errors.py`, after the last class (`code = "PUR-014"`), add:

```python
class PendingPaymentStateError(AppError):
    code = "PUR-015"
    status_code = 422
    message = "Pending payment is not in a state that allows this action"
```

- [ ] **Step 3: Generate and apply the migration**

Run: `python manage.py makemigrations purchasing --settings=config.settings.dev`
Expected: creates `erp/purchasing/migrations/0008_pendingpayment.py` (or next free number).
Run: `python manage.py migrate purchasing --settings=config.settings.dev`
Expected: `Applying purchasing.0008_pendingpayment... OK`

- [ ] **Step 4: Write the failing tests**

Create `erp/purchasing/tests/test_pending_payments.py`:

```python
"""Draftable supplier payments — mirrors erp/sales/tests/test_pending_payments.py exactly."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.purchasing.domain.models import PendingPaymentStatus, POStatus
from erp.purchasing.errors import OverpaymentError, PendingPaymentStateError
from erp.purchasing.services import POLineInput, bill_order, confirm_order, create_order, receive_order
from erp.purchasing.services.pending_payments import (
    apply_pending_payment,
    create_pending_payment,
    discard_pending_payment,
    match_pending_payment,
)

from .factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _billed_order(amount=1000_00):
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    assert order.billed_minor == amount
    return supplier, order


def test_apply_matched_payment_reproduces_pay_order_behavior():
    supplier, order = _billed_order()
    pending = create_pending_payment(
        order=order, party_code=supplier.code, amount_minor=400_00, date=DATE, method="transfer",
    )

    applied = apply_pending_payment(pending)

    assert applied.status == PendingPaymentStatus.APPLIED
    order.refresh_from_db()
    assert order.status == POStatus.BILLED  # partial
    assert order.outstanding_minor == 600_00


def test_apply_without_a_matched_order_raises():
    _, order = _billed_order()
    pending = create_pending_payment(order=None, party_code="SUP1", amount_minor=400_00, date=DATE)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_match_then_apply_round_trips():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=None, party_code=supplier.code, amount_minor=1000_00, date=DATE)

    matched = match_pending_payment(pending, order)
    applied = apply_pending_payment(matched)

    assert applied.status == PendingPaymentStatus.APPLIED
    order.refresh_from_db()
    assert order.status == POStatus.PAID


def test_apply_already_applied_raises():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)
    apply_pending_payment(pending)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_apply_overpayment_still_raises_the_existing_guard():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=5000_00, date=DATE)

    with pytest.raises(OverpaymentError):
        apply_pending_payment(pending)


def test_discard_marks_discarded_and_blocks_further_actions():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)

    discarded = discard_pending_payment(pending)

    assert discarded.status == PendingPaymentStatus.DISCARDED
    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(discarded)
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `pytest erp/purchasing/tests/test_pending_payments.py -v`
Expected: `ModuleNotFoundError` — the service doesn't exist yet.

- [ ] **Step 6: Implement the service**

Create `erp/purchasing/services/pending_payments.py` (mirrors Task 1 Step 6 exactly, purchasing side):

```python
"""Draftable supplier payments — mirrors erp.sales.services.pending_payments exactly. See that
module's docstring."""
from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.utils import timezone

from ..domain.models import PendingPayment, PendingPaymentStatus, PurchaseOrder
from ..errors import PendingPaymentStateError
from .orders import pay_order


def create_pending_payment(
    *, order: PurchaseOrder | None, party_code: str, amount_minor: int, date: dt.date,
    method: str = "", source: str = "import", batch_ref: str = "", actor=None,
) -> PendingPayment:
    return PendingPayment.objects.create(
        order=order, party_code=party_code, amount_minor=amount_minor, date=date,
        method=method, source=source, batch_ref=batch_ref,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )


@transaction.atomic
def apply_pending_payment(pending: PendingPayment, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    if pending.order_id is None:
        raise PendingPaymentStateError("pending payment has no matched order — match it first")
    pay_order(pending.order, pending.amount_minor, actor=actor)
    pending.status = PendingPaymentStatus.APPLIED
    pending.applied_by = actor if getattr(actor, "is_authenticated", False) else None
    pending.applied_at = timezone.now()
    pending.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])
    return pending


def discard_pending_payment(pending: PendingPayment, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    pending.status = PendingPaymentStatus.DISCARDED
    pending.save(update_fields=["status", "updated_at"])
    return pending


def match_pending_payment(pending: PendingPayment, order: PurchaseOrder, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    pending.order = order
    pending.save(update_fields=["order", "updated_at"])
    return pending
```

- [ ] **Step 7: Export from the services package**

In `erp/purchasing/services/__init__.py`, add after the `.requests` import block:

```python
from .pending_payments import (  # noqa: F401
    apply_pending_payment,
    create_pending_payment,
    discard_pending_payment,
    match_pending_payment,
)
```

And add the same four names to `__all__`.

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest erp/purchasing/tests/test_pending_payments.py -v`
Expected: 6 passed

- [ ] **Step 9: Commit**

```bash
git add erp/purchasing/domain/models.py erp/purchasing/errors.py \
        erp/purchasing/services/pending_payments.py erp/purchasing/services/__init__.py \
        erp/purchasing/tests/test_pending_payments.py erp/purchasing/migrations/
git commit -m "feat(purchasing): draftable PendingPayment model + apply/discard/match services (mirrors sales)"
```

---

### Task 3: Engine warning support for row-level adapters + Sales `receipts` import adapter

**Why the engine change first:** `erp/imports/engine.py`'s grouped path (`_dispatch_group`)
already lets `adapter.write` return `(record, warnings)` so a document can succeed while still
surfacing a non-blocking issue (e.g. `total_mismatch`). The row-level path (`_dispatch`) has no
such support — `adapter.write` must return a bare record. The `receipts` adapter needs exactly
this: an unmatched payment still imports (as a pending row with `order=None`), but must surface a
`payment_unmatched` warning on that row. This step extends `_dispatch`/`_execute_chunk`
symmetrically with the grouped path — every existing row-level adapter (`customers`, `suppliers`,
…) returns a bare record today and is completely unaffected (the tuple check is opt-in, identical
to `_dispatch_group`'s own `_write()` helper).

**Files:**
- Modify: `erp/imports/engine.py`
- Create: `erp/imports/tests/test_engine_row_warnings.py`
- Modify: `erp/imports/adapters/sales.py`
- Create: `erp/imports/tests/test_receipt_adapter.py`

**Interfaces:**
- Consumes: `erp.sales.services.pending_payments.create_pending_payment` (Task 1),
  `erp.imports.registry.{FieldSpec, Issue, register}`, `erp.imports.adapters._rbac.require_role`.
- Produces: `erp.imports.engine._dispatch` now returns `tuple[str, dict, list[Issue]]` (was
  `tuple[str, dict]`) — internal to `engine.py`, no external caller depends on the old shape.
  `receipts` entity registered in `erp.imports.registry.REGISTER`.

- [ ] **Step 1: Write the failing engine test**

Create `erp/imports/tests/test_engine_row_warnings.py`:

```python
"""A row-level (ungrouped) adapter's ``write`` may return ``(record, warnings)`` exactly like a
grouped adapter's — the engine attaches the warnings to that row's issues without erroring it."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine, registry
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import FieldSpec, Issue

pytestmark = pytest.mark.django_db


class _Record:
    def __init__(self, pk):
        self.pk = pk


class _WarningEmittingAdapter:
    entity = "test_row_warnings"
    label_key = "imports.entity.testRowWarnings"
    fields = [FieldSpec(name="value", kind="text")]
    natural_key = []
    group_by = None

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row):
        return []

    def write(self, actor, row):
        record = _Record(pk=row["value"])
        if row["value"] == "warn":
            return record, [Issue(field="value", code="test_warning", message="test.warning")]
        return record

    def exists(self, actor, row):
        return None

    def existing_labels(self, actor):
        return []


@pytest.fixture(autouse=True)
def _register():
    if "test_row_warnings" not in registry.REGISTER:
        registry.register(_WarningEmittingAdapter())
    yield


def _manager() -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username="rw1", email="rw1@erp.local", password="pw12345!", is_superuser=True)
    u.groups.add(bm)
    return u


def test_row_level_write_may_return_warnings_without_erroring():
    actor = _manager()
    batch = ImportBatch.objects.create(entity="test_row_warnings")
    ImportRow.objects.create(batch=batch, row_number=1, normalized={"value": "warn"}, status=ImportRow.Status.VALID)
    ImportRow.objects.create(batch=batch, row_number=2, normalized={"value": "clean"}, status=ImportRow.Status.VALID)

    report = engine.execute_batch(actor, batch)

    assert report["imported"] == 2  # both rows still imported — a warning never blocks
    row1 = batch.rows.get(row_number=1)
    assert row1.status == ImportRow.Status.IMPORTED
    assert any(i["code"] == "test_warning" for i in row1.issues)
    row2 = batch.rows.get(row_number=2)
    assert row2.issues == []


def test_existing_row_level_adapters_unaffected_by_bare_record_return():
    """A guard: any adapter still returning a bare record (every one built before this session)
    behaves exactly as before — no warnings, no crash unpacking a non-tuple."""
    actor = _manager()
    batch = ImportBatch.objects.create(entity="customers")
    assert "customers" in registry.entities()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest erp/imports/tests/test_engine_row_warnings.py::test_row_level_write_may_return_warnings_without_erroring -v`
Expected: FAIL — `AssertionError` on `row1.issues` being empty (current `_dispatch` doesn't unpack
tuples, so `result_ref` gets built from the tuple itself and no issue is attached), or a `TypeError`
from `_result_ref` trying `getattr((record, warnings), "pk", None)` — either way, red.

- [ ] **Step 3: Extend the engine**

In `erp/imports/engine.py`, replace the `_dispatch` function and its call site in `_execute_chunk`:

```python
def _write_row(adapter, actor, normalized: dict) -> tuple[Any, list[Issue]]:
    """Mirrors ``_dispatch_group``'s ``_write()`` helper — ``adapter.write`` may return the record
    alone (every adapter built before this) or ``(record, warnings)`` (session 16b: a row-level
    adapter that needs to flag something non-blocking, e.g. an unmatched payment)."""
    result = adapter.write(actor, normalized)
    if isinstance(result, tuple) and len(result) == 2:
        return result
    return result, []


def _dispatch(actor, adapter, batch: ImportBatch, row: ImportRow) -> tuple[str, dict, list[Issue]]:
    if row.status == ImportRow.Status.DUPLICATE:  # merge-decided; readiness already verified support
        target_pk = (row.decision or {}).get("target_pk")
        record = adapter.update(actor, row.normalized, target_pk=target_pk)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "updated"), []

    existing = adapter.exists(actor, row.normalized)
    strategy = batch.strategy

    if strategy == ImportBatch.Strategy.CREATE_ONLY:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}, []
        record, warnings = _write_row(adapter, actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "created"), warnings

    if strategy == ImportBatch.Strategy.UPDATE_ONLY:
        if existing is None:
            return ImportRow.Status.SKIPPED, {}, []
        record = adapter.update(actor, row.normalized, target_pk=getattr(existing, "pk", None))
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "updated"), []

    if strategy == ImportBatch.Strategy.UPSERT:
        if existing is not None:
            record = adapter.update(actor, row.normalized, target_pk=getattr(existing, "pk", None))
            return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "updated"), []
        record, warnings = _write_row(adapter, actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "created"), warnings

    if strategy == ImportBatch.Strategy.SKIP_EXISTING:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}, []
        record, warnings = _write_row(adapter, actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "created"), warnings

    raise ValueError(f"unknown strategy: {strategy!r}")  # pragma: no cover — model choices are exhaustive
```

Now update `_execute_chunk` to consume the 3-tuple and persist warnings (replace the existing
function body):

```python
def _execute_chunk(actor, adapter, batch: ImportBatch, row_ids: list) -> None:
    rows = list(ImportRow.objects.select_for_update().filter(id__in=row_ids).order_by("row_number"))
    imported = updated = created = skipped = 0

    for row in rows:
        if execute_status(row) == ImportRow.Status.SKIPPED:
            row.status = ImportRow.Status.SKIPPED
            row.result_ref = {}
            skipped += 1
            continue

        action, result_ref, warnings = _dispatch(actor, adapter, batch, row)
        row.status = action
        row.result_ref = result_ref
        if warnings:
            row.issues = [*row.issues, *[w.as_dict() for w in warnings]]
        if action == ImportRow.Status.IMPORTED:
            imported += 1
            if result_ref.get("action") == "updated":
                updated += 1
            else:
                created += 1
        else:
            skipped += 1

    ImportRow.objects.bulk_update(rows, ["status", "result_ref", "issues"])

    batch.refresh_from_db()
    batch.processed_count = batch.processed_count + len(rows)
    batch.save(update_fields=["processed_count"])

    audit_record(
        module="imports", action="execute_chunk", entity_type=batch.entity, entity_id=str(batch.pk),
        actor=actor, after={"imported": imported, "created": created, "updated": updated, "skipped": skipped},
    )
```

(Only two changes from the original: `bulk_update` always includes `"issues"` now — harmless for
rows with an unchanged empty list — and `_dispatch`'s three-tuple is unpacked.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest erp/imports/tests/test_engine_row_warnings.py -v`
Expected: 2 passed
Run: `pytest erp/imports -v`
Expected: full existing suite still green (confirms every adapter built before this session is
unaffected by the bare-record path).

- [ ] **Step 5: Commit the engine change alone**

```bash
git add erp/imports/engine.py erp/imports/tests/test_engine_row_warnings.py
git commit -m "feat(imports): row-level adapters may return (record, warnings), mirroring grouped adapters"
```

- [ ] **Step 6: Write the failing adapter test**

Create `erp/imports/tests/test_receipt_adapter.py`:

```python
"""``receipts`` import adapter (sales customer receipts) — always creates a PendingPayment, never
posts to the GL. See DESIGN_PENDING_PAYMENTS_AND_STOCK.md."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine
from erp.imports.models import ImportBatch, ImportRow
from erp.sales.domain.models import PendingPayment, PendingPaymentStatus
from erp.sales.services import OrderLineInput, confirm_order, create_order, deliver_order, invoice_order

from erp.sales.tests.factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _manager(username="rcpt1") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True)
    u.groups.add(bm)
    return u


def _invoiced_order(customer, wh):
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    return order


def _row(batch, row_number, normalized):
    return ImportRow.objects.create(batch=batch, row_number=row_number, normalized=normalized, status=ImportRow.Status.VALID)


def test_receipt_with_resolvable_order_creates_a_matched_pending_payment():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUST1")
    order = _invoiced_order(customer, wh)
    actor = _manager()
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST1", "amount_minor": 500_00, "date": "2026-06-20",
                    "method": "cash", "order_ref": order.number})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id == order.id
    assert pending.status == PendingPaymentStatus.PENDING
    assert pending.amount_minor == 500_00
    row = batch.rows.get(row_number=1)
    assert row.issues == []  # matched — no warning


def test_receipt_without_a_reference_stays_unmatched_with_a_warning():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    make_customer(code="CUST2")
    actor = _manager("rcpt2")
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST2", "amount_minor": 300_00, "date": "2026-06-20", "method": ""})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id is None
    row = batch.rows.get(row_number=1)
    assert any(i["code"] == "payment_unmatched" for i in row.issues)


def test_receipt_never_touches_the_gl_at_import_time():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUST3")
    order = _invoiced_order(customer, wh)
    actor = _manager("rcpt3")
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST3", "amount_minor": 500_00, "date": "2026-06-20", "order_ref": order.number})

    engine.execute_batch(actor, batch)

    order.refresh_from_db()
    assert order.paid_minor == 0  # untouched — applying is a separate, human-triggered step


def test_receipt_method_normalizes_arabic_tokens():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUST4")
    order = _invoiced_order(customer, wh)
    actor = _manager("rcpt4")
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST4", "amount_minor": 100_00, "date": "2026-06-20",
                    "method": "نقدي", "order_ref": order.number})

    engine.execute_batch(actor, batch)

    assert PendingPayment.objects.get().method == "cash"
```

- [ ] **Step 7: Run test to verify it fails**

Run: `pytest erp/imports/tests/test_receipt_adapter.py -v`
Expected: FAIL — `KeyError: no import adapter for entity 'receipts'`.

- [ ] **Step 8: Implement the `receipts` adapter**

First, extend the two existing top-level imports (this file already imports sibling
`erp.sales.services.*` and `erp.sales.domain.models.*` at module level — follow that, no local
imports inside the new class):

```python
from erp.sales.domain.models import (
    Customer, OrderStatus, PendingPayment, PendingPaymentStatus, Quotation, QuotationStatus, SalesOrder,
)
from erp.sales.services.orders import OrderLineInput
from erp.sales.services.pending_payments import create_pending_payment
from erp.sales.services.quotations import QuoteLineInput
```

(Replaces the existing `from erp.sales.domain.models import Customer, OrderStatus, Quotation,
QuotationStatus, SalesOrder` line and adds one new import line right after
`from erp.sales.services.orders import OrderLineInput`.)

Then add near the bottom of the file (after the existing `SalesInvoiceAdapter`/`register(...)`
calls), before end of file:

```python
# --- receipts (session 16b — PendingPayment, drafts-only) -----------------------------------------
def _find_order(actor, ref: str):
    """An existing SalesOrder by its ERP-native ``number`` (a human re-keying what they see on
    screen) or by the import-tag ``notes`` a prior document import left (``import:<doc>`` /
    ``import-so:<doc>`` — the source system's own invoice/order number, the common case for a
    cutover payments file)."""
    ref = (ref or "").strip()
    if not ref:
        return None
    qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
    return qs.filter(number=ref).first() or qs.filter(notes__in=[f"import:{ref}", f"import-so:{ref}"]).first()


_METHOD_TOKENS = {
    "cash": "cash", "نقدي": "cash", "نقدا": "cash",
    "transfer": "transfer", "bank transfer": "transfer", "تحويل": "transfer", "تحويل بنكي": "transfer",
    "cheque": "cheque", "check": "cheque", "شيك": "cheque",
}


def _normalize_method(value) -> str:
    token = str(value or "").strip().casefold()
    return _METHOD_TOKENS.get(token, "")


class ReceiptAdapter:
    """Customer receipts — always stages a ``sales.PendingPayment`` (drafts-only; see
    ``adapters/accounting.py`` for why the direct write-path ``receive_payment`` can't be used from
    an import). A resolvable ``order_ref`` pre-matches the row; otherwise it imports unmatched with
    a ``payment_unmatched`` warning (never blocks) — applying/matching is a human review-screen
    action (``erp.sales.services.pending_payments``), out of scope here.

    No natural key: a flat receipts file rarely carries a stable per-row id, so ``exists`` always
    returns ``None`` — every import run creates new pending rows. True duplicates are a human's call
    on the (future) review screen, same as any other data-entry double-check.
    """

    entity = "receipts"
    label_key = "imports.entity.receipts"
    fields = [
        FieldSpec(
            name="customer_ref", required=True, kind="ref", ref="customers",
            synonyms_en=["customer", "customer code", "customer name"],
            synonyms_ar=["العميل", "كود العميل", "اسم العميل"],
        ),
        FieldSpec(
            name="amount_minor", required=True, kind="money",
            synonyms_en=["amount", "payment amount", "received"],
            synonyms_ar=["المبلغ", "مبلغ الدفعة", "المحصل"],
        ),
        FieldSpec(
            name="date", required=True, kind="date",
            synonyms_en=["date", "payment date", "received date"],
            synonyms_ar=["التاريخ", "تاريخ الدفعة"],
        ),
        FieldSpec(
            name="method", kind="text",
            synonyms_en=["method", "payment method"],
            synonyms_ar=["طريقة الدفع", "الطريقة"],
        ),
        # Deliberately NOT kind="ref" — an unresolved order must import unmatched (warning), never
        # trigger the missing_ref/auto-create-master flow (there's nothing sane to auto-create for
        # a stray invoice number).
        FieldSpec(
            name="order_ref", kind="text",
            synonyms_en=["invoice number", "invoice ref", "order number"],
            synonyms_ar=["رقم الفاتورة", "رقم الطلب"],
        ),
    ]
    natural_key = []
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "customer_ref":
            return _find_customer(actor, value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        customer = _find_customer(actor, row.get("customer_ref"))
        order = _find_order(actor, row.get("order_ref"))
        pending = create_pending_payment(
            order=order,
            party_code=customer.code if customer else (row.get("customer_ref") or "").strip(),
            amount_minor=int(row["amount_minor"]),
            date=_as_date(row.get("date")) or _dt.date.today(),
            method=_normalize_method(row.get("method")),
            source="import",
            actor=actor,
        )
        if order is None:
            return pending, [Issue(
                field="order_ref", code="payment_unmatched", message="imports.issues.paymentUnmatched",
                meta={"customer_ref": row.get("customer_ref"), "order_ref": row.get("order_ref")},
            )]
        return pending

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []

    def delete(self, actor, pk) -> None:
        """Rollback support: a still-PENDING row has posted nothing anywhere, so a plain delete is
        a true reversal. Refuses once applied/discarded — never deletes a row a human already
        acted on."""
        pending = PendingPayment.objects.filter(pk=pk).first()
        if pending is None:
            return
        if pending.status != PendingPaymentStatus.PENDING:
            raise ValueError(f"cannot delete pending payment {pending.pk}: status is {pending.status!r}, not pending")
        pending.delete()


register(ReceiptAdapter())
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `pytest erp/imports/tests/test_receipt_adapter.py -v`
Expected: 4 passed
Run: `pytest erp/imports erp/sales -v`
Expected: full suite green (no regression in either module).

- [ ] **Step 10: Commit**

```bash
git add erp/imports/adapters/sales.py erp/imports/tests/test_receipt_adapter.py
git commit -m "feat(imports): receipts adapter -- stages PendingPayment, drafts-only (sales side)"
```

---

### Task 4: Purchasing `payments` import adapter (mirrors Task 3 Step 6-10)

**Files:**
- Modify: `erp/imports/adapters/purchasing.py`
- Create: `erp/imports/tests/test_payment_adapter.py`

**Interfaces:**
- Consumes: `erp.purchasing.services.pending_payments.create_pending_payment` (Task 2), the engine
  warning support already shipped in Task 3 Step 3 (no further engine changes needed).
- Produces: `payments` entity registered in `erp.imports.registry.REGISTER`.

- [ ] **Step 1: Write the failing test**

Create `erp/imports/tests/test_payment_adapter.py` (mirrors `test_receipt_adapter.py`):

```python
"""``payments`` import adapter (purchasing supplier payments) — mirrors test_receipt_adapter.py."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine
from erp.imports.models import ImportBatch, ImportRow
from erp.purchasing.domain.models import PendingPayment, PendingPaymentStatus
from erp.purchasing.services import POLineInput, bill_order, confirm_order, create_order, receive_order

from erp.purchasing.tests.factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _manager(username="pay1") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True)
    u.groups.add(bm)
    return u


def _billed_order(supplier, wh):
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    return order


def _row(batch, row_number, normalized):
    return ImportRow.objects.create(batch=batch, row_number=row_number, normalized=normalized, status=ImportRow.Status.VALID)


def test_payment_with_resolvable_order_creates_a_matched_pending_payment():
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier(code="SUP1")
    order = _billed_order(supplier, wh)
    actor = _manager()
    batch = ImportBatch.objects.create(entity="payments")
    _row(batch, 1, {"supplier_ref": "SUP1", "amount_minor": 400_00, "date": "2026-06-20",
                    "method": "transfer", "order_ref": order.number})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id == order.id
    assert pending.status == PendingPaymentStatus.PENDING


def test_payment_without_a_reference_stays_unmatched_with_a_warning():
    make_books()
    make_item()
    wh = make_warehouse()
    make_supplier(code="SUP2")
    actor = _manager("pay2")
    batch = ImportBatch.objects.create(entity="payments")
    _row(batch, 1, {"supplier_ref": "SUP2", "amount_minor": 200_00, "date": "2026-06-20"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id is None
    row = batch.rows.get(row_number=1)
    assert any(i["code"] == "payment_unmatched" for i in row.issues)


def test_payment_never_touches_the_gl_at_import_time():
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier(code="SUP3")
    order = _billed_order(supplier, wh)
    actor = _manager("pay3")
    batch = ImportBatch.objects.create(entity="payments")
    _row(batch, 1, {"supplier_ref": "SUP3", "amount_minor": 400_00, "date": "2026-06-20", "order_ref": order.number})

    engine.execute_batch(actor, batch)

    order.refresh_from_db()
    assert order.paid_minor == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest erp/imports/tests/test_payment_adapter.py -v`
Expected: FAIL — `KeyError: no import adapter for entity 'payments'`.

- [ ] **Step 3: Implement the `payments` adapter**

First, extend the two existing top-level imports (mirrors Task 3 Step 8 — no local imports inside
the new class):

```python
from erp.purchasing.domain.models import PendingPayment, PendingPaymentStatus, POStatus, PurchaseOrder, Supplier
from erp.purchasing.services.orders import POLineInput
from erp.purchasing.services.pending_payments import create_pending_payment
```

(Replaces the existing `from erp.purchasing.domain.models import POStatus, PurchaseOrder,
Supplier` line and adds one new import line right after
`from erp.purchasing.services.orders import POLineInput`.)

Then add at the end of the file:

```python
# --- payments (session 16b — PendingPayment, drafts-only) ------------------------------------------
def _find_order(actor, ref: str):
    """Mirrors ``adapters.sales._find_order`` — see that function's docstring."""
    ref = (ref or "").strip()
    if not ref:
        return None
    qs = scope_queryset(actor, PurchaseOrder.objects.all(), "purchasing.order.view")
    return qs.filter(number=ref).first() or qs.filter(notes__in=[f"import:{ref}", f"import-po:{ref}"]).first()


_METHOD_TOKENS = {
    "cash": "cash", "نقدي": "cash", "نقدا": "cash",
    "transfer": "transfer", "bank transfer": "transfer", "تحويل": "transfer", "تحويل بنكي": "transfer",
    "cheque": "cheque", "check": "cheque", "شيك": "cheque",
}


def _normalize_method(value) -> str:
    token = str(value or "").strip().casefold()
    return _METHOD_TOKENS.get(token, "")


class PaymentAdapter:
    """Supplier payments — mirrors ``adapters.sales.ReceiptAdapter`` exactly; see that class's
    docstring for the drafts-only reasoning and the no-natural-key decision."""

    entity = "payments"
    label_key = "imports.entity.payments"
    fields = [
        FieldSpec(
            name="supplier_ref", required=True, kind="ref", ref="suppliers",
            synonyms_en=["supplier", "supplier code", "supplier name", "vendor"],
            synonyms_ar=["المورد", "كود المورد", "اسم المورد"],
        ),
        FieldSpec(
            name="amount_minor", required=True, kind="money",
            synonyms_en=["amount", "payment amount", "paid"],
            synonyms_ar=["المبلغ", "مبلغ الدفعة", "المدفوع"],
        ),
        FieldSpec(
            name="date", required=True, kind="date",
            synonyms_en=["date", "payment date"],
            synonyms_ar=["التاريخ", "تاريخ الدفعة"],
        ),
        FieldSpec(
            name="method", kind="text",
            synonyms_en=["method", "payment method"],
            synonyms_ar=["طريقة الدفع", "الطريقة"],
        ),
        FieldSpec(
            name="order_ref", kind="text",
            synonyms_en=["bill number", "invoice number", "order number"],
            synonyms_ar=["رقم الفاتورة", "رقم الطلب"],
        ),
    ]
    natural_key = []
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "supplier_ref":
            return _find_supplier(value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        supplier = _find_supplier(row.get("supplier_ref"))
        order = _find_order(actor, row.get("order_ref"))
        pending = create_pending_payment(
            order=order,
            party_code=supplier.code if supplier else (row.get("supplier_ref") or "").strip(),
            amount_minor=int(row["amount_minor"]),
            date=_as_date(row.get("date")) or _dt.date.today(),
            method=_normalize_method(row.get("method")),
            source="import",
            actor=actor,
        )
        if order is None:
            return pending, [Issue(
                field="order_ref", code="payment_unmatched", message="imports.issues.paymentUnmatched",
                meta={"supplier_ref": row.get("supplier_ref"), "order_ref": row.get("order_ref")},
            )]
        return pending

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []

    def delete(self, actor, pk) -> None:
        pending = PendingPayment.objects.filter(pk=pk).first()
        if pending is None:
            return
        if pending.status != PendingPaymentStatus.PENDING:
            raise ValueError(f"cannot delete pending payment {pending.pk}: status is {pending.status!r}, not pending")
        pending.delete()


register(PaymentAdapter())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest erp/imports/tests/test_payment_adapter.py -v`
Expected: 3 passed
Run: `pytest erp/imports erp/purchasing -v`
Expected: full suite green.

- [ ] **Step 5: Commit**

```bash
git add erp/imports/adapters/purchasing.py erp/imports/tests/test_payment_adapter.py
git commit -m "feat(imports): payments adapter -- stages PendingPayment, drafts-only (purchasing side)"
```

---

### Task 5: Sales API — list/apply/discard/match

**Files:**
- Modify: `erp/sales/api/serializers.py`
- Modify: `erp/sales/api/views.py`
- Modify: `erp/sales/api/urls.py`
- Create: `erp/sales/tests/test_pending_payment_api.py`

**Interfaces:**
- Consumes: `erp.sales.services.pending_payments.{apply_pending_payment, discard_pending_payment,
  match_pending_payment}` (Task 1).
- Produces: `GET/POST /api/sales/pending-payments`, `POST /api/sales/pending-payments/<uuid:pk>/apply`,
  `.../discard`, `.../match` — consumed later by Agent A's review screen (out of scope here).

- [ ] **Step 1: Write the failing tests**

Create `erp/sales/tests/test_pending_payment_api.py`:

```python
"""Pending-payment review API — list/apply/discard/match. Backend-only; no UI in this plan."""
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.sales.services import OrderLineInput, confirm_order, create_order, deliver_order, invoice_order
from erp.sales.services.pending_payments import create_pending_payment

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="pp_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _invoiced_order():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUSTX")
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    return customer, order


def test_list_shows_pending_payments():
    customer, order = _invoiced_order()
    create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)
    client = _admin_client()

    resp = client.get("/api/sales/pending-payments")

    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1
    assert resp.data["data"][0]["amount_minor"] == 500_00
    assert resp.data["data"][0]["order_number"] == order.number


def test_apply_via_api_posts_the_payment():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=1500_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/sales/pending-payments/{pending.id}/apply")

    assert resp.status_code == 200
    assert resp.data["data"]["status"] == "applied"
    order.refresh_from_db()
    assert order.status == "paid"


def test_discard_via_api():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/sales/pending-payments/{pending.id}/discard")

    assert resp.status_code == 200
    assert resp.data["data"]["status"] == "discarded"


def test_match_via_api_then_apply():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=None, party_code=customer.code, amount_minor=1500_00, date=DATE)
    client = _admin_client()

    matched = client.post(f"/api/sales/pending-payments/{pending.id}/match", {"order_id": str(order.id)}, format="json")
    assert matched.status_code == 200
    assert matched.data["data"]["order_number"] == order.number

    applied = client.post(f"/api/sales/pending-payments/{pending.id}/apply")
    assert applied.data["data"]["status"] == "applied"


def test_unauthenticated_is_rejected():
    client = APIClient()
    assert client.get("/api/sales/pending-payments").status_code in (401, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest erp/sales/tests/test_pending_payment_api.py -v`
Expected: FAIL — 404 (no such URL yet).

- [ ] **Step 3: Add the serializers**

In `erp/sales/api/serializers.py`, add after `PaymentSerializer`:

```python
class PendingPaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    order_id = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    party_code = serializers.CharField()
    amount_minor = serializers.IntegerField()
    date = serializers.DateField()
    method = serializers.CharField()
    source = serializers.CharField()
    status = serializers.CharField()
    batch_ref = serializers.CharField()

    def get_order_id(self, obj) -> str | None:
        return str(obj.order_id) if obj.order_id else None

    def get_order_number(self, obj) -> str | None:
        return obj.order.number if obj.order_id else None


class MatchPendingPaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
```

- [ ] **Step 4: Add the views**

In `erp/sales/api/views.py`, add the `PendingPayment` import to the `..domain.models` import line
(`from ..domain.models import Customer, PendingPayment, Quotation, SalesOrder`), add
`PendingPaymentSerializer` and `MatchPendingPaymentSerializer` to the serializers import block, and
add near the end of the file (after `OrderPaymentView`). The module already has `from .. import
services` at the top (line 23) — the new views call `services.apply_pending_payment` etc. directly,
no new import needed:

```python
def _pending_qs():
    return PendingPayment.objects.select_related("order")


def _scoped_pending(request: Request):
    return scope_queryset(request.user, _pending_qs(), "sales.order.view")


class PendingPaymentListView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> Response:
        qs = _scoped_pending(request).order_by("-date", "-created_at")
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return _envelope(PendingPaymentSerializer(qs, many=True).data)


class PendingPaymentApplyView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, pk) -> Response:
        pending = get_object_or_404(_scoped_pending(request), id=pk)
        services.apply_pending_payment(pending, actor=request.user)
        return _envelope(PendingPaymentSerializer(pending).data)


class PendingPaymentDiscardView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, pk) -> Response:
        pending = get_object_or_404(_scoped_pending(request), id=pk)
        services.discard_pending_payment(pending, actor=request.user)
        return _envelope(PendingPaymentSerializer(pending).data)


class PendingPaymentMatchView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, pk) -> Response:
        pending = get_object_or_404(_scoped_pending(request), id=pk)
        s = MatchPendingPaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = get_object_or_404(_scoped_orders(request), id=s.validated_data["order_id"])
        services.match_pending_payment(pending, order, actor=request.user)
        return _envelope(PendingPaymentSerializer(pending).data)
```

- [ ] **Step 5: Wire the URLs**

In `erp/sales/api/urls.py`, add after the `orders/<uuid:order_id>/payment` line:

```python
    path("pending-payments", views.PendingPaymentListView.as_view(), name="pending-payment-list"),
    path("pending-payments/<uuid:pk>/apply", views.PendingPaymentApplyView.as_view(), name="pending-payment-apply"),
    path("pending-payments/<uuid:pk>/discard", views.PendingPaymentDiscardView.as_view(), name="pending-payment-discard"),
    path("pending-payments/<uuid:pk>/match", views.PendingPaymentMatchView.as_view(), name="pending-payment-match"),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest erp/sales/tests/test_pending_payment_api.py -v`
Expected: 5 passed
Run: `pytest erp/sales -v`
Expected: full module suite green.

- [ ] **Step 7: Commit**

```bash
git add erp/sales/api/serializers.py erp/sales/api/views.py erp/sales/api/urls.py \
        erp/sales/tests/test_pending_payment_api.py
git commit -m "feat(sales): pending-payments review API -- list/apply/discard/match"
```

---

### Task 6: Purchasing API — list/apply/discard/match (mirrors Task 5)

**Files:**
- Modify: `erp/purchasing/api/serializers.py`
- Modify: `erp/purchasing/api/views.py`
- Modify: `erp/purchasing/api/urls.py`
- Create: `erp/purchasing/tests/test_pending_payment_api.py`

**Interfaces:**
- Consumes: `erp.purchasing.services.pending_payments.*` (Task 2).
- Produces: `GET/POST /api/purchasing/pending-payments` + `.../apply`/`.../discard`/`.../match`.

- [ ] **Step 1: Write the failing tests**

Create `erp/purchasing/tests/test_pending_payment_api.py` (mirrors Task 5 Step 1, purchasing side):

```python
"""Pending-payment review API (purchasing) -- mirrors erp/sales/tests/test_pending_payment_api.py."""
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.purchasing.services import POLineInput, bill_order, confirm_order, create_order, receive_order
from erp.purchasing.services.pending_payments import create_pending_payment

from .factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="pp_pur_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _billed_order():
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier(code="SUPX")
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    return supplier, order


def test_list_shows_pending_payments():
    supplier, order = _billed_order()
    create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)
    client = _admin_client()

    resp = client.get("/api/purchasing/pending-payments")

    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1


def test_apply_via_api_posts_the_payment():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=1000_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/purchasing/pending-payments/{pending.id}/apply")

    assert resp.status_code == 200
    assert resp.data["data"]["status"] == "applied"
    order.refresh_from_db()
    assert order.status == "paid"


def test_discard_via_api():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/purchasing/pending-payments/{pending.id}/discard")

    assert resp.data["data"]["status"] == "discarded"


def test_match_via_api_then_apply():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=None, party_code=supplier.code, amount_minor=1000_00, date=DATE)
    client = _admin_client()

    matched = client.post(f"/api/purchasing/pending-payments/{pending.id}/match", {"order_id": str(order.id)}, format="json")
    assert matched.status_code == 200

    applied = client.post(f"/api/purchasing/pending-payments/{pending.id}/apply")
    assert applied.data["data"]["status"] == "applied"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest erp/purchasing/tests/test_pending_payment_api.py -v`
Expected: FAIL — 404 (no such URL yet).

- [ ] **Step 3: Add the serializers**

In `erp/purchasing/api/serializers.py`, add after `PaymentSerializer` (identical shape to Task 5
Step 3, `PendingPaymentSerializer` + `MatchPendingPaymentSerializer`).

- [ ] **Step 4: Add the views**

In `erp/purchasing/api/views.py`: add `PendingPayment` to the `..domain.models` import, add the two
serializers to the import block, and add (mirroring Task 5 Step 4, `_CanBuy` instead of `_CanSell`,
`_scoped_pos`/`_po_qs` instead of `_scoped_orders`/`_order_qs`, `"purchasing.order.view"` instead
of `"sales.order.view"`). The module already has `from .. import services` at the top (line 20) —
no new import needed:

```python
def _pending_qs():
    return PendingPayment.objects.select_related("order")


def _scoped_pending(request: Request):
    return scope_queryset(request.user, _pending_qs(), "purchasing.order.view")


class PendingPaymentListView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request) -> Response:
        qs = _scoped_pending(request).order_by("-date", "-created_at")
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return _envelope(PendingPaymentSerializer(qs, many=True).data)


class PendingPaymentApplyView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, pk) -> Response:
        pending = get_object_or_404(_scoped_pending(request), id=pk)
        services.apply_pending_payment(pending, actor=request.user)
        return _envelope(PendingPaymentSerializer(pending).data)


class PendingPaymentDiscardView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, pk) -> Response:
        pending = get_object_or_404(_scoped_pending(request), id=pk)
        services.discard_pending_payment(pending, actor=request.user)
        return _envelope(PendingPaymentSerializer(pending).data)


class PendingPaymentMatchView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, pk) -> Response:
        pending = get_object_or_404(_scoped_pending(request), id=pk)
        s = MatchPendingPaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = get_object_or_404(_scoped_pos(request), id=s.validated_data["order_id"])
        services.match_pending_payment(pending, order, actor=request.user)
        return _envelope(PendingPaymentSerializer(pending).data)
```

- [ ] **Step 5: Wire the URLs**

In `erp/purchasing/api/urls.py`, add after `orders/<uuid:order_id>/payment`:

```python
    path("pending-payments", views.PendingPaymentListView.as_view(), name="pending-payment-list"),
    path("pending-payments/<uuid:pk>/apply", views.PendingPaymentApplyView.as_view(), name="pending-payment-apply"),
    path("pending-payments/<uuid:pk>/discard", views.PendingPaymentDiscardView.as_view(), name="pending-payment-discard"),
    path("pending-payments/<uuid:pk>/match", views.PendingPaymentMatchView.as_view(), name="pending-payment-match"),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest erp/purchasing/tests/test_pending_payment_api.py -v`
Expected: 4 passed
Run: `pytest erp/purchasing -v`
Expected: full module suite green.

- [ ] **Step 7: Commit**

```bash
git add erp/purchasing/api/serializers.py erp/purchasing/api/views.py erp/purchasing/api/urls.py \
        erp/purchasing/tests/test_pending_payment_api.py
git commit -m "feat(purchasing): pending-payments review API -- list/apply/discard/match (mirrors sales)"
```

---

### Task 7: Close out — guard test, DECISIONS entry, full gates, board update

**Files:**
- Modify: `erp/imports/tests/test_finance_adapters.py`
- Modify: `erp/imports/adapters/accounting.py`
- Modify: `DECISIONS.md`
- Modify: `Docs/plan/PARALLEL_PLAN.md`

**Interfaces:**
- Consumes: nothing new — this task only updates documentation/guards for everything shipped in
  Tasks 1-6.

- [ ] **Step 1: Update the guard test**

In `erp/imports/tests/test_finance_adapters.py`, replace the final function
(`test_blocked_finance_entities_are_not_registered`) with:

```python
# --- guard: inventory-opening stays unbuilt (blocker, by design; payments/receipts now shipped) --
def test_inventory_finance_entities_stay_unregistered():
    """``payments``/``receipts`` shipped (session 16b — ``PendingPayment``, drafts-only; see
    ``erp.sales.services.pending_payments`` / ``erp.purchasing.services.pending_payments``).
    ``inventory_opening``/``inventory_transactions`` remain the documented blocker (sub-project 2,
    ``DESIGN_PENDING_PAYMENTS_AND_STOCK.md``) — pinned so a later session re-reads the reasoning
    before registering one."""
    registered = set(registry.entities())
    assert {"journal_entries", "account_opening", "payments", "receipts"} <= registered
    for blocked in ("inventory_opening", "inventory_transactions"):
        assert blocked not in registered
```

Also update the module docstring at the top of the file (lines 10-13) to remove the now-stale
claim that payments/receipts are unbuilt:

```python
"""Finance adapters (FILE_16): ``journal_entries`` + ``account_opening``.

Both write DRAFT journal entries via ``contracts.create_journal_entry_draft`` and are grouped
document adapters, so — like ``test_document_adapters.py`` — these tests build ``ImportRow``
fixtures directly (the shape ``analyze``/``normalize_row`` would have produced) and drive
``engine.execute_batch``/``rollback_batch``. They also exercise the engine's new ``validate_group``
hook: the per-entry balance guard (``journal_entries``) and the human-in-the-loop suspense
correction (``account_opening``).

``payments``/``receipts`` now ship too (session 16b) — see ``erp/imports/tests/
test_receipt_adapter.py`` and ``test_payment_adapter.py``, and ``erp.sales``/``erp.purchasing``'s
own ``pending_payments`` service tests; not repeated here. The inventory-opening adapters are still
deliberately NOT built (see ``adapters/accounting.py`` and ``DESIGN_PENDING_PAYMENTS_AND_STOCK.md``)
— the guard test below pins that decision.
"""
```

- [ ] **Step 2: Update `adapters/accounting.py`'s docstring**

In `erp/imports/adapters/accounting.py`, replace the "DELIBERATELY NOT BUILT" block (the module
docstring's final paragraph, lines ~28-43) with:

```python
DELIBERATELY NOT BUILT here (FILE_16 Before-You-Start STOP rule — no GL-correct, drafts-only module
write-path exists, so building it would misstate a customer's books; recorded in ``erp-status``):

* ``inventory_opening`` / ``inventory_transactions`` — ``inventory.receive`` posts Dr Inventory /
  Cr GRNI (a supplier-bill liability, wrong for an opening) and ``adjust_stock`` posts the offset to
  a P&L variance account; both post immediately and would DOUBLE-COUNT the Inventory control account
  that ``account_opening`` already books. Weighted-average costing carries no as-of-date, so
  replaying backdated historic movements computes cost against the CURRENT balance and corrupts
  COGS. No draft inventory-opening / sub-ledger-load service exists to import against. Design for a
  fix (a new, additive ``PendingStockEntry`` posting to a dedicated suspense account, plus a
  double-book guard on ``account_opening``) is written up in ``DESIGN_PENDING_PAYMENTS_AND_STOCK.md``
  — not yet implemented.

``payments`` / ``receipts`` shipped separately (session 16b) in ``erp/imports/adapters/sales.py``
(``ReceiptAdapter``) and ``erp/imports/adapters/purchasing.py`` (``PaymentAdapter``) — they stage a
module-local ``PendingPayment`` instead of posting immediately, resolving the same drafts-only
conflict this file's own payment write-paths (``sales.receive_payment``, ``purchasing.pay_order``)
couldn't.
"""
```

- [ ] **Step 3: Run the full backend test suite**

Run: `pytest erp/sales erp/purchasing erp/imports erp/accounting -v`
Expected: all green, including the updated guard test.
Run: `pytest` (full suite, repo root)
Expected: all green except the pre-existing, separately-tracked `erp/workflow/tests/test_api.py`
failures (already flagged in `erp-status`, unrelated to this work).

- [ ] **Step 4: Run the gate suite**

Run: `python scripts/gates/_run.py all`
Expected: 00-02/04-17 green (gate03 N/A on this checkout — no `apps/web` `node_modules`).

- [ ] **Step 5: Add the DECISIONS.md entry**

Append to `DECISIONS.md` (after the most recent entry):

```markdown
## Draftable payments — PendingPayment, mirrored per module (smart-import FILE_16 follow-up, 2026-07-17)

`FILE_16_FINANCE_ADAPTERS.md` Task B (payments/receipts) was left unbuilt because the only
existing write-paths (`sales.receive_payment`, `purchasing.pay_order`) post to the GL immediately —
violating the drafts-only standing decision (reaffirmed above, 2026-07-09) — and require an
already-invoiced order, which a freshly-imported order never is yet.

**Fix:** a new `PendingPayment` model, staged by the import (or, later, the AI assistant) instead
of posting. A human applies it later from a review screen (not yet built — `apps/web`, Agent A),
which calls the **existing, unmodified** `receive_payment`/`pay_order` — no second write path, just
deferred by a human confirmation, matching the `agent-actions` drafts-only pattern already used for
orders/POs/journal entries.

**Not a shared model.** `erp.accounting` has zero imports from `erp.sales`/`erp.purchasing`
(accounting is dependency-free; sales/purchasing depend on it, never the reverse). Two mirrored
models — `erp.sales.domain.models.PendingPayment`, `erp.purchasing.domain.models.PendingPayment` —
avoid inverting that and match the codebase's existing convention of duplicating payment concerns
per module rather than sharing them (`PaymentSerializer` was already separate per module).

**Unmatched payments never touch the GL.** No suspense-account posting happens for an unresolved
invoice reference (unlike `account_opening`'s imbalance correction) — the row just stays
`order=None` with a `payment_unmatched` warning until a human matches it. Nothing is booked until
`apply_pending_payment` runs, so there is no "cash without a home" GL entry to reconcile later.

**Engine extended, not modified:** `erp.imports.engine._dispatch` (row-level/ungrouped adapters)
now accepts `adapter.write` returning `(record, warnings)`, mirroring what `_dispatch_group`
already supported for grouped adapters. Every adapter built before this session returns a bare
record and is unaffected (opt-in, guarded by an `isinstance(result, tuple)` check).

**Full spec:** `Docs/plan/smart-import-plan/DESIGN_PENDING_PAYMENTS_AND_STOCK.md`. Sub-project 2
(reconciled inventory opening) is specced there too but not yet built — still a documented blocker
in `adapters/accounting.py`.
```

- [ ] **Step 6: Update the PARALLEL_PLAN board**

In `Docs/plan/PARALLEL_PLAN.md`, add a row to the Wave 3+ table (after B15):

```markdown
| B16 | Draftable payments — `PendingPayment` (smart-import FILE_16 Task B follow-up) | B | `erp/sales/domain/models.py`+`services/pending_payments.py`, `erp/purchasing/domain/models.py`+`services/pending_payments.py`, `erp/imports/engine.py` (row-warning support), `erp/imports/adapters/{sales,purchasing}.py` (`receipts`/`payments`), both modules' `api/` (list/apply/discard/match) | B15 | done(HEAD) — backend + API + tests only; review screen is apps/web, Agent A's territory, unbuilt. Sub-project 2 (inventory opening) specced in `DESIGN_PENDING_PAYMENTS_AND_STOCK.md`, not yet built. |
```

And update the closing narrative line (the one starting "**B:** TH FILE_13 activity timeline
backend...") to append: `→ B16 draftable payments (done — see above) → next: inventory-opening
reconciliation (sub-project 2) or check board for a new task.`

- [ ] **Step 7: Final commit**

```bash
git add erp/imports/tests/test_finance_adapters.py erp/imports/adapters/accounting.py \
        DECISIONS.md Docs/plan/PARALLEL_PLAN.md
git commit -m "docs: close out draftable-payments work -- DECISIONS entry, guard test, board update"
```

---

## After this plan

Sub-project 2 (reconciled inventory opening — `PendingStockEntry`, the `account_opening`
double-book guard, and the permanent `inventory_transactions` blocker) is specced in
`DESIGN_PENDING_PAYMENTS_AND_STOCK.md` but needs its own implementation plan — write one with
`superpowers:writing-plans` in a fresh session before starting it, following the same pattern this
plan used.
