"""Idempotency on external writes: no duplicate side effect on a same-attempt retry."""
from __future__ import annotations

import pytest
from django.db import connection

from erp.workflow.engine import engine
from erp.workflow.engine.idempotency import key_for
from erp.workflow.models import (
    IdempotencyRecord,
    InstanceStatus,
    NodeType,
    WorkflowInstance,
)

from .factories import make_workflow

pytestmark = pytest.mark.django_db


PO_INSERT = (
    "INSERT INTO erp_external.purchase_orders "
    "(id, request_ref, amount, supplier, idempotency_key) "
    "VALUES (%s, %s, %s, %s, %s) "
    "ON CONFLICT (idempotency_key) DO NOTHING"
)


def _write_wf():
    return make_workflow(
        "po",
        nodes=[
            ("start", NodeType.START, {}),
            (
                "create_po",
                NodeType.API_CALL,
                {
                    "adapter": "sql",
                    "write": True,
                    "statement": PO_INSERT,
                    "params": [
                        "{{ctx.requestRef}}",
                        "{{ctx.requestRef}}",
                        "{{ctx.amount}}",
                        "{{ctx.supplier}}",
                        "{{idem}}",
                    ],
                },
            ),
            ("end", NodeType.END, {}),
        ],
        edges=[("start", "create_po", None, 0), ("create_po", "end", None, 0)],
    )


def _po_count(ref):
    with connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM erp_external.purchase_orders WHERE request_ref = %s", [ref])
        return cur.fetchone()[0]


def test_external_write_creates_one_row_and_ledger_record():
    wf = _write_wf()
    payload = {"requestRef": "PR-1", "amount": 100, "supplier": "ACME"}
    inst = engine.start_instance(wf, payload)
    assert inst.status == InstanceStatus.COMPLETED
    assert _po_count("PR-1") == 1
    assert IdempotencyRecord.objects.count() == 1


def test_same_attempt_cached_skips_side_effect():
    wf = _write_wf()
    node = wf.nodes.get(key="create_po")
    inst = WorkflowInstance.objects.create(
        workflow=wf, status=InstanceStatus.PENDING, current_node=node,
        context={"requestRef": "PR-2", "amount": 100, "supplier": "ACME"},
    )
    # Pre-seed the ledger for attempt 1 -> the engine must return the cached response and NOT
    # execute the SQL side effect.
    key = key_for(inst.id, node.id, 1)
    IdempotencyRecord.objects.create(
        key=key, instance_id=inst.id, node_id=node.id, response={"cached": True}
    )
    engine.run(inst.id, max_steps=1)
    assert _po_count("PR-2") == 0  # side effect skipped
    inst.refresh_from_db()
    assert inst.context["create_po"] == {"cached": True}
