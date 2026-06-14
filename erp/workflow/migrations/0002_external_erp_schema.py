"""Simulated external ERP target used by the SQL/REST adapters and the idempotency proof.

Lives in the same PostgreSQL instance under schema `erp_external` (no second container/server).
The UNIQUE idempotency_key gives a DB-level dedupe proof.
"""
from django.db import migrations

CREATE = """
CREATE SCHEMA IF NOT EXISTS erp_external;
CREATE TABLE IF NOT EXISTS erp_external.purchase_orders (
    id              text PRIMARY KEY,
    request_ref     text NOT NULL,
    amount          numeric(14,2) NOT NULL,
    supplier        text NOT NULL,
    idempotency_key text UNIQUE NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);
"""

DROP = "DROP TABLE IF EXISTS erp_external.purchase_orders; DROP SCHEMA IF EXISTS erp_external;"


class Migration(migrations.Migration):
    dependencies = [("workflow", "0001_initial")]
    operations = [migrations.RunSQL(CREATE, DROP)]
