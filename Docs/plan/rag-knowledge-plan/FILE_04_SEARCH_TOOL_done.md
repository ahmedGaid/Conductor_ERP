# SESSION 4 — `search_documents` Tool + Loop Routing
# Files: erp/assistant/tools.py, erp/assistant/services/agent.py, erp/assistant/tests/test_tools.py, erp/assistant/tests/test_agent.py

---

## Before You Start

1. Open `erp/assistant/tools.py` → read a private tool runner (e.g. `_find_customers`) and its
   `_cite_*` helper to copy the exact result/citation shapes; re-read the `TOOLS` dict tail
   (the `query_data` entry is last) and `catalog_text()`.
2. Open `erp/assistant/services/agent.py` → re-read `_LOOP_SYSTEM` (lines ~37–62) and
   `_run_tool` — note that tool args flow through `_ARG_FIELDS` (from `ask.py`), which already
   includes `query` and `limit`; a tool using only those needs NO schema change.
3. Open `erp/assistant/tests/test_agent.py` → see how the planner (`complete_json`) and answer
   stream (`complete_stream`) are monkeypatched.

Do not write anything yet.

---

## Task A — Tool runner + citation in `tools.py`

Next to the other private runners (keep module grouping — put it before the `TOOLS` dict,
after the audit runner), add:

```python
# Knowledge base (RAG) — company documents uploaded by an administrator.
def _search_documents(actor, query: str = "", limit=6):
    from .services import knowledge  # local import — mirrors how services import each other

    hits = knowledge.search(str(query or ""), limit=_int(limit, 6))
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
```

(`_int` — tools.py almost certainly has an int-coercion helper for `limit`; reuse the one you
find. If limits are coerced inline instead, do it that way.)

In the `TOOLS` dict, directly ABOVE the `query_data` entry (so Analytics stays last), add:

```python
    # Knowledge base — company documents (SOPs, policies, catalogs, contracts, manuals)
    Tool("search_documents",
         "Search the company's uploaded documents (policies, SOPs, catalogs, contracts, "
         "manuals) and return the most relevant passages. Use for any question answered by "
         "documentation rather than live ERP data.",
         {"query": "what to look for, in the user's own words",
          "limit": "how many passages (default 6)"},
         _search_documents, lambda r: r.get("citations", []), "Knowledge"),
```

## Task B — Loop-prompt routing in `agent.py`

In `_LOOP_SYSTEM`, find the line:

```
"The query_data tool is the flexible fallback for a count/total no specific tool covers. ...
```

Directly BEFORE it, insert this line (keeps catalog → routing → grammar order):

```python
    "Choosing a source: live business data (balances, stock, orders, invoices, totals) MUST come "
    "from the data tools; anything defined by company documents (policies, SOPs, procedures, "
    "catalog details, contract terms) MUST come from search_documents; when a question needs "
    "both, gather both before answering. Conversation history is context, never a source of "
    "business facts. If search_documents finds nothing, say no document covers it — never "
    "invent documentation.\n"
```

## Task C — Tests

Extend `tests/test_tools.py`:
- test_search_documents_returns_passages_and_citations — seed a ready doc + chunks →
  run tool → `found` True, citation `{"type": "document", ...}`
- test_search_documents_empty_is_honest — no docs → `found` False + the honest note
- test_catalog_text_lists_knowledge_group — `catalog_text()` contains "Knowledge:" and
  "search_documents"

Extend `tests/test_agent.py`:
- test_loop_runs_search_documents_and_cites — fake planner: round 1 → `{"action": "tool",
  "tool": "search_documents", "query": "refund policy", ...}`, round 2 → `{"action":
  "answer"}`; fake stream → assert a step event for the tool, and the citations event carries
  the document citation
- test_loop_system_contains_source_routing — `_LOOP_SYSTEM` mentions "search_documents" and
  "never" + "invent" (guards the prompt like test_context does)

---

## Smoke Test

- [ ] `pytest erp/assistant` green
- [ ] Dev server + a seeded policy doc: ask the assistant "ما هي سياسة الاسترجاع؟" → step chip
      shows the search, answer quotes the policy, citation chip appears
- [ ] Ask about a doc that doesn't exist ("what is the travel policy?") → honest "no document
      covers this" answer, no fabrication
- [ ] Ask a live-data question ("كم عميل لدينا؟") → still uses data tools, NOT search_documents
- [ ] Mixed question ("do we have enough stock of X to satisfy the catalog's minimum order?")
      → both a data tool and search_documents appear as steps

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_04_SEARCH_TOOL_done.md
→ Type /compact in Claude Code
→ Open FILE_05_SOURCE_ROUTING_PROMPT.md and continue
```
