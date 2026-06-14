"""SQL / PL-SQL adapter.

Config: { statement: str, params?: list }. PARAMETERIZED ONLY — uses %s placeholders bound to
params; never builds SQL by string concatenation (gate02 greps this file to enforce it). Targets
the same PostgreSQL instance (the demo external target lives in schema erp_external).
"""
from __future__ import annotations

from django.db import connection

from .types import AdapterCall, AdapterResult


class SqlAdapter:
    kind = "sql"

    def call(self, call: AdapterCall) -> AdapterResult:
        cfg = call.config
        statement = cfg["statement"]
        params = cfg.get("params") or []
        try:
            with connection.cursor() as cursor:
                cursor.execute(statement, params)
                rows = []
                if cursor.description is not None:
                    columns = [c[0] for c in cursor.description]
                    rows = [dict(zip(columns, r)) for r in cursor.fetchall()]
                return AdapterResult(ok=True, data=rows)
        except Exception as exc:  # noqa: BLE001
            return AdapterResult(ok=False, error=f"{type(exc).__name__}: {exc}")
