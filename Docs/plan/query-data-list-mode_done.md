# query-data list mode — "ask me anything you may see" (single session)

**Founder decision 2026-07-07:** the assistant must answer ANY data question the user is permitted
to see (list/show/count/total), chatbot-grade — WITHOUT breaking the tool-use-never-SQL rule.
Trigger: live FILE_12 smoke — "GIVE ME LIST OF ITEMS" had no route; planner re-asked its clarify
question. Rejected stopgap: a thin `find_items` tool (subset of this; redundant once list mode
lands). Scheduled BEFORE ai-workspace FILE_13 (feeds the claims-gate demo more).

## Why safe (unchanged boundaries)
`erp/assistant/query_registry.py` already gates each entity on its view permission and runs
record-scoped entities through `scope_queryset` **as the actor**. List mode adds zero new security
surface: same permission gate, same scope path, only whitelisted fields ever reach the ORM.
Free-text-to-SQL stays banned (DECISIONS.md) — RBAC branch/own scope lives in Python, not the DB.

## Tasks
1. **List mode in `run_query`** — new explicit `aggregate="list"` (or `mode` arg): return actual
   rows. Add `columns: dict[str, str]` (display name → ORM path) per `_Entity`; order by a sane
   default (newest/number desc); `limit` capped 50; citations from a `cite` column like `_grouped`
   does; money columns minor-int + formatted at the edge (`_egp`). No aggregate + no group_by from
   the model ⇒ default to list, not count (matches user intent "show me…").
2. **Registry expansion** — add viewable entities with fields + view permission codes:
   quotation, purchase_request, warehouse, stock_movement, stock_balance (or on-hand via report),
   lead, opportunity, ticket, campaign, account, einvoice. Reuse each module's view code from
   `erp/identity/rbac.py` MODULES. Scoped=True where the module list endpoint scopes.
3. **Planner prompt reroute** (`agent.py` `_LOOP_SYSTEM` + `ask.py` router text): query_data is the
   fallback for ANY lookup/list/count/total with no dedicated tool — not "count/total" only.
   Update `query_grammar_text()` to mention listing + columns.
4. **Grounding guard (closes backlog half-entry "live-data grounding gap")** — deterministic:
   lookup/report intent + zero successful tool calls ⇒ force one `query_data` list/count attempt
   (mirror of the `search_documents` guard in `agent.py::run`, see DECISIONS FILE_11 addendum).
   If entity inference is too weak, cut scope: guard only when the planner NAMED query_data args
   but answered anyway; note remaining gap honestly.
5. **Tests** — `test_query_tool.py` additions: list returns rows with only whitelisted columns;
   scope holds (branch user sees own branch rows only); denied entity refused; new entities gated;
   prompt-level loop test: "list the items" routes to query_data and answers from rows.
6. **Gates** — assistant pytest, parity (no UI strings expected), tsc if `api/assistant.ts`
   touched (likely not), gate03, gate14.

## Non-goals
No SQL, no new npm deps, no UI change (Markdown table render already exists), no write paths.
Keep `tools.py` curated tools as the preferred fast path — query_data stays the fallback.

## After
Rename this file `_done`, update erp-status (queue → ai-workspace FILE_13), DECISIONS entry.
