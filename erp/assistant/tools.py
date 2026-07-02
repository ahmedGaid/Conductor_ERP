"""The assistant's tool catalog — a fixed set of typed READ tools.

Architecture (DECISIONS "AI 2026-07"): tool-use, never free-text-to-SQL. Each tool is one existing
scoped contract call, executed **as the current user** (``actor``), so RBAC + data-scope + audit
hold automatically — the AI is just another actor with the caller's permissions. Money is formatted
here, server-side, and citations are built here from the real records, so the model narrates the
numbers/links it is given and can never invent them.

Every tool is read-only. Writes stay human-in-the-loop through the normal module endpoints (part 1's
invoice→draft flow is the template); no tool in this catalog mutates data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from erp.inventory import contracts as inventory
from erp.sales import contracts as sales


def _egp(minor: int | None) -> str:
    """Integer minor units → a human EGP string with Western digits (money formats at the edge)."""
    return f"{(minor or 0) / 100:,.2f} EGP"


# --- tool implementations (thin wrappers over the scoped contract helpers) ----------------------

def _sales_summary(actor, *, period: str = "this_month", **_) -> dict:
    r = sales.sales_summary(actor, period=period)
    return {**r, "total": _egp(r["total_minor"])}


def _top_customers(actor, *, limit: int = 5, **_) -> dict:
    rows = sales.top_customers(actor, limit=int(limit or 5))
    return {"customers": [{**c, "total": _egp(c["total_minor"])} for c in rows]}


def _overdue_receivables(actor, *, limit: int = 10, **_) -> dict:
    r = sales.overdue_receivables(actor, limit=int(limit or 10))
    return {
        "total_outstanding": _egp(r["total_outstanding_minor"]),
        "total_outstanding_minor": r["total_outstanding_minor"],
        "customers": [{**c, "outstanding": _egp(c["outstanding_minor"])} for c in r["customers"]],
    }


def _find_orders(actor, *, query: str = "", **_) -> dict:
    rows = sales.find_orders(actor, query=query or "")
    return {"orders": [{**o, "total": _egp(o["total_minor"])} for o in rows]}


def _low_stock(actor, *, limit: int = 20, **_) -> dict:
    return {"items": inventory.low_stock(limit=int(limit or 20))}


# --- citation builders (real records → click-through links, never model-invented) ---------------

def _cite_customers(result: dict) -> list[dict]:
    return [{"type": "customer", "value": c["code"], "label": c["name"]}
            for c in result.get("customers", [])]


def _cite_orders(result: dict) -> list[dict]:
    return [{"type": "order", "value": o["id"], "label": o["number"]}
            for o in result.get("orders", [])]


def _cite_items(result: dict) -> list[dict]:
    return [{"type": "item", "value": i["sku"], "label": i["name"]}
            for i in result.get("items", [])]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: dict            # arg name -> plain-language description (for the router prompt)
    run: Callable
    cite: Callable[[dict], list[dict]]


TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool(
        "sales_summary",
        "Total net sales value and order count for a period.",
        {"period": "one of: this_month | last_month | this_year"},
        _sales_summary, lambda _r: [],
    ),
    Tool(
        "top_customers",
        "The customers with the highest net sales, best first.",
        {"limit": "how many customers (default 5)"},
        _top_customers, _cite_customers,
    ),
    Tool(
        "overdue_receivables",
        "Customers who still owe money (invoiced more than they have paid), largest first.",
        {"limit": "how many customers (default 10)"},
        _overdue_receivables, _cite_customers,
    ),
    Tool(
        "find_orders",
        "Look up sales orders by order number or customer name.",
        {"query": "text to search order number / customer name"},
        _find_orders, _cite_orders,
    ),
    Tool(
        "low_stock",
        "Items at or below their reorder point (need restocking).",
        {"limit": "how many items (default 20)"},
        _low_stock, _cite_items,
    ),
]}


def catalog_text() -> str:
    """A compact, stable description of the tools for the router prompt."""
    lines = []
    for t in TOOLS.values():
        args = ", ".join(f"{k} ({v})" for k, v in t.args.items()) or "no arguments"
        lines.append(f"- {t.name}: {t.description} Arguments: {args}")
    return "\n".join(lines)
