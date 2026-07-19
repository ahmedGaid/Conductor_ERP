"""The assistant's tool catalog — a fixed set of typed READ tools.

Architecture (DECISIONS "AI 2026-07"): tool-use, never free-text-to-SQL. Each tool is one existing
scoped contract call, executed **as the current user** (``actor``), so RBAC + data-scope + audit
hold automatically — the AI is just another actor with the caller's permissions. Money is formatted
here, server-side, and citations are built here from the real records, so the model narrates the
numbers/links it is given and can never invent them.

Every tool is read-only. Writes stay human-in-the-loop through the normal module endpoints (part 1's
invoice→draft flow is the template); no tool in this catalog mutates data.

Two enforcement styles sit behind the tools, both running as ``actor``:
- **record-scoped** modules (sales/purchasing orders, customers, journals) narrow the queryset with
  ``scope_queryset`` inside the contract, so branch/own scope holds;
- **company-wide reports** (accounting statements, VAT, inventory balances, workflow, audit) have no
  per-record dimension, so the tool gates them with an explicit permission check.
In both cases a caller who lacks the module permission gets the same calm, blame-free refusal — the
model relays it honestly instead of inventing data.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from erp.accounting import contracts as accounting
from erp.audit.models import AuditEntry
from erp.crm import contracts as crm
from erp.identity import access
from erp.inventory import contracts as inventory
from erp.purchasing import contracts as purchasing
from erp.sales import contracts as sales
from erp.workflow import services as workflow

from .query_registry import run_query as _run_query


def _egp(minor: int | None) -> str:
    """Integer minor units → a human EGP string with Western digits (money formats at the edge)."""
    return f"{(minor or 0) / 100:,.2f} EGP"


# A tool the caller isn't permitted to use returns this instead of data; the model relays it kindly.
def _denied() -> dict:
    return {"error": "This information is outside what your role can access."}


# --- Sales tools (thin wrappers over the scoped contract helpers) --------------------------------

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


# --- Customers (CRM) tools -----------------------------------------------------------------------

def _customer_profile(actor, *, query: str = "", **_) -> dict:
    if not access.has_permission(actor, "sales.customer.view"):
        return _denied()
    r = sales.customer_profile(actor, query=query or "")
    if r.get("customer") is None:
        return r
    return {
        **r,
        "outstanding": _egp(r["outstanding_minor"]),
        "recent_orders": [{**o, "total": _egp(o["total_minor"])} for o in r["recent_orders"]],
    }


def _find_customers(actor, *, query: str = "", limit: int = 10, **_) -> dict:
    if not access.has_permission(actor, "sales.customer.view"):
        return _denied()
    return {"customers": sales.find_customers(actor, query=query or "", limit=int(limit or 10))}


def _find_opportunities(actor, *, query: str = "", limit: int = 8, **_) -> dict:
    rows = crm.find_opportunities(actor, query=query or "", limit=int(limit or 8))
    return {"opportunities": [{**o, "amount": _egp(o["amount_minor"])} for o in rows]}


# --- Purchasing tools ----------------------------------------------------------------------------

def _open_purchase_orders(actor, *, status: str = None, supplier: str = None, limit: int = 20, **_) -> dict:
    if not access.has_permission(actor, "purchasing.order.view"):
        return _denied()
    rows = purchasing.open_purchase_orders(
        actor, status=status or None, supplier=supplier or None, limit=int(limit or 20)
    )
    return {"orders": [
        {**o, "subtotal": _egp(o["subtotal_minor"]), "outstanding": _egp(o["outstanding_minor"])}
        for o in rows
    ]}


def _supplier_balances(actor, *, limit: int = 10, **_) -> dict:
    if not access.has_permission(actor, "purchasing.order.view"):
        return _denied()
    r = purchasing.supplier_balances(actor, limit=int(limit or 10))
    return {
        "total_outstanding": _egp(r["total_outstanding_minor"]),
        "suppliers": [{**s, "outstanding": _egp(s["outstanding_minor"])} for s in r["suppliers"]],
    }


def _purchase_summary(actor, *, period: str = "this_month", **_) -> dict:
    if not access.has_permission(actor, "purchasing.order.view"):
        return _denied()
    r = purchasing.purchase_summary(actor, period=period or "this_month")
    return {**r, "total": _egp(r["total_minor"])}


# --- Inventory tools (company-wide balances, gated like low_stock's module) ----------------------

def _low_stock(actor, *, limit: int = 20, **_) -> dict:
    return {"items": inventory.low_stock(limit=int(limit or 20))}


def _stock_on_hand(actor, *, query: str = None, warehouse: str = None, limit: int = 20, **_) -> dict:
    if not access.has_permission(actor, "inventory.item.view"):
        return _denied()
    r = inventory.stock_on_hand(query=query or None, warehouse=warehouse or None, limit=int(limit or 20))
    return {
        "item": r.get("item"),
        "total_value": _egp(r.get("total_value_minor")),
        "rows": [{**row, "value": _egp(row["value_minor"])} for row in r.get("rows", [])],
    }


def _stock_movements(actor, *, query: str = "", limit: int = 15, **_) -> dict:
    if not access.has_permission(actor, "inventory.item.view"):
        return _denied()
    return inventory.stock_movements(query=query or "", limit=int(limit or 15))


def _expiring_batches(actor, *, days: int = 30, **_) -> dict:
    if not access.has_permission(actor, "inventory.item.view"):
        return _denied()
    return inventory.expiring_batches(days=int(days or 30))


# --- Accounting tools (company-wide GL reports, gated by the accounting permission) --------------

def _trial_balance_summary(actor, *, period: str = "this_month", **_) -> dict:
    if not access.has_permission(actor, "accounting.report.view"):
        return _denied()
    r = accounting.trial_balance_summary(period=period or "this_month")
    return {
        **r,
        "total_debit": _egp(r["total_debit_minor"]),
        "total_credit": _egp(r["total_credit_minor"]),
        "accounts": [{**a, "balance": _egp(a["balance_minor"])} for a in r["accounts"]],
    }


def _income_statement_summary(actor, *, period: str = "this_month", **_) -> dict:
    if not access.has_permission(actor, "accounting.report.view"):
        return _denied()
    r = accounting.income_statement_summary(period=period or "this_month")
    return {
        **r,
        "total_revenue": _egp(r["total_revenue_minor"]),
        "total_expenses": _egp(r["total_expenses_minor"]),
        "net_income": _egp(r["net_income_minor"]),
        "revenue": [{**ln, "amount": _egp(ln["amount_minor"])} for ln in r["revenue"]],
        "expenses": [{**ln, "amount": _egp(ln["amount_minor"])} for ln in r["expenses"]],
    }


def _vat_return_status(actor, *, period: str = "this_month", **_) -> dict:
    if not access.has_permission(actor, "accounting.report.view"):
        return _denied()
    r = accounting.vat_return_status(period=period or "this_month")
    return {
        **r,
        "output_vat": _egp(r["output_vat_minor"]),
        "input_vat": _egp(r["input_vat_minor"]),
        "net_payable": _egp(r["net_payable_minor"]),
    }


def _find_journal(actor, *, query: str = "", **_) -> dict:
    if not access.has_permission(actor, "accounting.journal.view"):
        return _denied()
    return {"journals": accounting.find_journal(actor, query=query or "")}


def _account_balance(actor, *, query: str = "", **_) -> dict:
    if not access.has_permission(actor, "accounting.account.view"):
        return _denied()
    r = accounting.account_balance(query=query or "")
    if r.get("account") is None:
        return r
    return {**r, "balance": _egp(r["balance_minor"])}


# --- Workflow tool -------------------------------------------------------------------------------

def _workflow_instance_status(actor, *, query: str = "", **_) -> dict:
    if not access.has_permission(actor, "workflow.instance.view"):
        return _denied()
    return workflow.instance_status(query or "")


# --- Audit tool ----------------------------------------------------------------------------------

def _document_history(actor, *, entity_type: str = "", entity_id: str = "", limit: int = 10, **_) -> dict:
    """Who changed a document, from the append-only audit log — read-only ORM (audit has no contract
    layer). Narrowed to modules the actor can reach, so it never surfaces history the user couldn't
    otherwise see."""
    modules = set(access.accessible_modules(actor))
    qs = AuditEntry.objects.filter(module__in=modules)
    if entity_type:
        qs = qs.filter(entity_type__icontains=entity_type)
    if entity_id:
        qs = qs.filter(entity_id=str(entity_id))
    return {"entries": [
        {"actor": (e.actor.username if e.actor else None), "action": e.action,
         "module": e.module, "entity_type": e.entity_type, "entity_id": e.entity_id,
         "result": e.result, "at": e.created_at.isoformat()}
        for e in qs.order_by("-created_at")[: max(1, min(limit, 20))]
    ]}


# --- Knowledge base tool (RAG) — company documents uploaded by an administrator -------------------

def _search_documents(actor, *, query: str = "", limit: int = 6, **_) -> dict:
    from .services import knowledge  # local import — mirrors how services import each other

    hits = knowledge.search(str(query or ""), limit=int(limit or 6))
    if not hits:
        return {"found": False,
                "note": "No company document covers this. Say so honestly; do not invent "
                        "documentation content."}
    return {
        "found": True,
        "passages": [
            {"document": h["title"], "section": h["seq"], "text": h["text"]} for h in hits
        ],
        "citations": [
            {"type": "document", "value": h["title"], "document_id": h["document_id"],
             "section": h["seq"]} for h in hits
        ],
    }


# --- Analytics tool — the bounded structured-query escape hatch (session 08 Task E) --------------

def _query_data(actor, *, entity: str = None, filters=None, group_by=None, aggregate: str = None,
                metric: str = None, limit: int = 20, **_) -> dict:
    """Flexible list/count/total across a whitelisted data set when no specific tool fits.

    Delegates to ``query_registry.run_query``, which validates every part of the grammar against the
    registry and runs it AS the actor (permission gate + ``scope_queryset``). Not free-text SQL — the
    registry is the boundary. Returns the calm refusal dict on anything off-registry or unpermitted.
    """
    return _run_query(
        actor, entity=entity, filters=filters, group_by=group_by,
        aggregate=aggregate, metric=metric, limit=int(limit or 20),
    )


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


def _cite_stock(result: dict) -> list[dict]:
    return [{"type": "item", "value": r["sku"], "label": r["name"]}
            for r in result.get("rows", [])]


def _cite_suppliers(result: dict) -> list[dict]:
    return [{"type": "supplier", "value": s["code"], "label": s["name"]}
            for s in result.get("suppliers", [])]


def _cite_purchase_orders(result: dict) -> list[dict]:
    return [{"type": "purchaseOrder", "value": o["number"], "label": o["number"]}
            for o in result.get("orders", [])]


def _cite_journals(result: dict) -> list[dict]:
    return [{"type": "journal", "value": j["number"], "label": j["number"]}
            for j in result.get("journals", [])]


def _cite_profile(result: dict) -> list[dict]:
    cites: list[dict] = []
    c = result.get("customer")
    if c:
        cites.append({"type": "customer", "value": c["code"], "label": c["name"]})
    cites += [{"type": "order", "value": o["id"], "label": o["number"]}
              for o in result.get("recent_orders", [])]
    return cites


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args: dict            # arg name -> plain-language description (for the router prompt)
    run: Callable
    cite: Callable[[dict], list[dict]]
    group: str = "Sales"  # module label used to group the router-prompt catalog


TOOLS: dict[str, Tool] = {t.name: t for t in [
    # Sales
    Tool("sales_summary",
         "Total net sales value and order count for a period.",
         {"period": "one of: this_month | last_month | this_year"},
         _sales_summary, lambda _r: [], "Sales"),
    Tool("top_customers",
         "The customers with the highest net sales, best first.",
         {"limit": "how many customers (default 5)"},
         _top_customers, _cite_customers, "Sales"),
    Tool("overdue_receivables",
         "Customers who still owe money (invoiced more than they have paid), largest first.",
         {"limit": "how many customers (default 10)"},
         _overdue_receivables, _cite_customers, "Sales"),
    Tool("find_orders",
         "Look up sales orders by order number or customer name.",
         {"query": "text to search order number / customer name"},
         _find_orders, _cite_orders, "Sales"),
    # Customers (CRM)
    Tool("customer_profile",
         "One customer's snapshot: balance still owed and their recent orders.",
         {"query": "customer code or name"},
         _customer_profile, _cite_profile, "Customers"),
    Tool("find_customers",
         "Look up customers by code or name.",
         {"query": "text to search customer code / name", "limit": "how many (default 10)"},
         _find_customers, _cite_customers, "Customers"),
    Tool("find_opportunities",
         "Look up sales opportunities (pipeline deals) by number, name or customer code — "
         "stage, value and expected close date.",
         {"query": "text to search opportunity number / name / customer code",
          "limit": "how many (default 8)"},
         _find_opportunities, lambda _r: [], "Customers"),
    # Purchasing
    Tool("open_purchase_orders",
         "Purchase orders still in flight (not yet paid), optionally filtered by status or supplier.",
         {"status": "optional exact status (e.g. confirmed, received, billed)",
          "supplier": "optional supplier code or name to filter by",
          "limit": "how many orders (default 20)"},
         _open_purchase_orders, _cite_purchase_orders, "Purchasing"),
    Tool("supplier_balances",
         "Suppliers we still owe money to (billed more than paid), largest first.",
         {"limit": "how many suppliers (default 10)"},
         _supplier_balances, _cite_suppliers, "Purchasing"),
    Tool("purchase_summary",
         "Total purchase value and order count for a period.",
         {"period": "one of: this_month | last_month | this_year"},
         _purchase_summary, lambda _r: [], "Purchasing"),
    # Inventory
    Tool("low_stock",
         "Items at or below their reorder point (need restocking).",
         {"limit": "how many items (default 20)"},
         _low_stock, _cite_items, "Inventory"),
    Tool("stock_on_hand",
         "On-hand quantity and value of an item across warehouses (optionally one warehouse).",
         {"query": "item SKU or name", "warehouse": "optional warehouse code to limit to",
          "limit": "how many rows (default 20)"},
         _stock_on_hand, _cite_stock, "Inventory"),
    Tool("stock_movements",
         "Recent stock movements (receipts, issues, transfers) for one item, newest first.",
         {"query": "item SKU or name", "limit": "how many movements (default 15)"},
         _stock_movements, lambda _r: [], "Inventory"),
    Tool("expiring_batches",
         "Received batches/lots whose earliest expiry falls within a number of days.",
         {"days": "expiry horizon in days (default 30)"},
         _expiring_batches, lambda _r: [], "Inventory"),
    # Accounting
    Tool("trial_balance_summary",
         "Trial-balance totals (debits vs credits, whether balanced) and the largest account balances.",
         {"period": "one of: this_month | last_month | this_year"},
         _trial_balance_summary, lambda _r: [], "Accounting"),
    Tool("income_statement_summary",
         "Revenue, expenses and net income (profit or loss) for a period.",
         {"period": "one of: this_month | last_month | this_year"},
         _income_statement_summary, lambda _r: [], "Accounting"),
    Tool("vat_return_status",
         "VAT collected on sales vs recovered on purchases for a period, and the net payable.",
         {"period": "one of: this_month | last_month | this_year"},
         _vat_return_status, lambda _r: [], "Accounting"),
    Tool("find_journal",
         "Look up posted journal entries by number, reference or memo.",
         {"query": "text to search journal number / reference / memo"},
         _find_journal, _cite_journals, "Accounting"),
    Tool("account_balance",
         "The current balance of one ledger account, found by code or name.",
         {"query": "account code or name"},
         _account_balance, lambda _r: [], "Accounting"),
    # Workflows
    Tool("workflow_instance_status",
         "The live state of a workflow run — current step, status and recent history "
         "(answers 'why did this workflow stop?').",
         {"query": "workflow instance id or workflow name"},
         _workflow_instance_status, lambda _r: [], "Workflows"),
    # Audit
    Tool("document_history",
         "Who changed a document and when, from the audit log (answers 'who modified this?').",
         {"entity_type": "the record type, e.g. SalesOrder / PurchaseOrder / JournalEntry",
          "entity_id": "the record's id or number", "limit": "how many entries (default 10)"},
         _document_history, lambda _r: [], "Audit"),
    # Knowledge base — company documents (SOPs, policies, catalogs, contracts, manuals)
    Tool("search_documents",
         "Search the company's uploaded documents (policies, SOPs, catalogs, contracts, "
         "manuals) and return the most relevant passages. Use for any question answered by "
         "documentation rather than live ERP data.",
         {"query": "what to look for, in the user's own words",
          "limit": "how many passages (default 6)"},
         _search_documents, lambda r: r.get("citations", []), "Knowledge"),
    # Analytics — the fallback when no specific tool fits (list/count/total over a whitelisted set)
    Tool("query_data",
         "List, count, or total records of a data set when no specific tool fits — e.g. 'list our "
         "items', 'show the sales orders', 'how many items do we have', 'total sales by status'. "
         "Pick a data set, optional filters, up to two group-by fields, and one aggregate "
         "('list' returns the rows themselves). See the query_data data sets listed below.",
         {"entity": "which data set (one of the data sets listed under query_data below)",
          "filters": "optional list of {field, op, value}; op is one of "
                     "eq/gt/lt/gte/lte/contains/between; value as text (for between pass 'low,high')",
          "group_by": "optional 0–2 fields to break the total down by",
          "aggregate": "list | count | sum | avg | min | max (default: list the rows; "
                       "count when grouped)",
          "metric": "the field to total, required for sum/avg/min/max",
          "limit": "max rows (default 20, capped at 50)"},
         _query_data, lambda r: r.get("citations", []), "Analytics"),
]}


def catalog_text() -> str:
    """A compact, stable description of the tools for the router prompt, grouped by module."""
    groups: dict[str, list[str]] = {}
    for t in TOOLS.values():
        args = ", ".join(f"{k} ({v})" for k, v in t.args.items()) or "no arguments"
        groups.setdefault(t.group, []).append(f"- {t.name}: {t.description} Arguments: {args}")
    lines: list[str] = []
    for group, items in groups.items():
        lines.append(f"{group}:")
        lines.extend(items)
    return "\n".join(lines)
