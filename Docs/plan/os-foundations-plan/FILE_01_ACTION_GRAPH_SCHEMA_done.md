# FILE_01 — L0: Action Graph v2 schema (declared semantics on every action)

> ONE SESSION. Read `FILE_00_INDEX.md` first. Prereq: none (first file of the phase).
> Everything here is backend-only; no UI, no i18n keys.

## Why

Today an `Action` (erp/assistant/services/actions.py L1254) declares name/description/args/
build_proposal/execute/kind/requires_confirm. The agent knows *how to call* an action but nothing
about *what it does to the system*. L0 makes semantics data: what must exist first, what it
creates, which invariants must hold afterward, what undoes it, how risky it is, how retries are
detected. FILE_02/03 (verifier) and FILE_04/05 (simulation) consume these fields; the L3 planner
(later phase) traverses them.

## The schema (target state)

```python
@dataclass(frozen=True)
class Action:
    name: str
    description: str
    args: dict
    build_proposal: Callable
    execute: Callable
    kind: str = "create"
    requires_confirm: bool = True
    # --- L0 declared semantics (all have safe defaults so the 13 non-archetype actions keep working) ---
    requires: tuple[str, ...] = ()          # entity kinds that must exist, e.g. ("customer", "item", "warehouse")
    effects: tuple[Effect, ...] = ()        # what it creates/updates, see Effect below
    invariants: tuple[str, ...] = ()        # verifier pack names (FILE_02) to run after execute
    compensation: str | None = None         # action name that undoes this one; None = draft-delete is enough
    risk: str = "draft"                     # "read" | "draft" | "post" | "destructive"
    idempotency: tuple[str, ...] = ()       # payload keys whose values form the natural retry key
```

```python
@dataclass(frozen=True)
class Effect:
    entity: str          # "sales_order", "journal_entry", "customer", ...
    verb: str            # "create" | "update"
    gl: str = "none"     # GL impact class: "none" | "draft" | "posts"
    stock: str = "none"  # stock impact class: "none" | "draft" | "moves"
```

Rules enforced at import time (extend the existing `DESTRUCTIVE_KINDS` assert block at L1426):
- `risk` must be one of the four values; `post`/`destructive` risk ⇒ `requires_confirm=True` (always).
- every name in `invariants` must exist in the verifier pack registry once FILE_02 lands — until
  then the assert only checks non-empty strings.
- `compensation`, when set, must name a registered action.
- an action whose any `Effect.gl == "posts"` or `Effect.stock == "moves"` must declare `risk="post"`
  or higher, and at least one invariant.

## Tasks

### [ ] T1.1 — Schema fields + import-time validation

- **Goal:** `Action` carries the six L0 fields with safe defaults; invalid declarations fail at
  import, not at runtime.
- **Files:** `erp/assistant/services/actions.py` (extend dataclass + validation block);
  `erp/assistant/tests/test_actions.py` (extend).
- **Steps:**
  1. Add the `Effect` dataclass and the six fields to `Action` exactly as above.
  2. Extend the module-level assert loop (L1426) into a `_validate_action(a)` function
     implementing the four rules; call it for every `ACTIONS` entry. Skip the pack-existence
     check with a `# tightened in FILE_02` comment.
  3. All 17 actions keep working untouched (defaults). Do NOT edit their declarations yet.
- **Accept:** `pytest erp/assistant/tests/test_actions.py` green; a test constructing an action
  with `risk="destructive", requires_confirm=False` (via the validator) raises AssertionError; a
  test with `Effect(gl="posts")` and `risk="draft"` raises.
- **Output:** schema v2 live, zero behaviour change.

### [ ] T1.2 — Retrofit the 4 archetype actions

- **Goal:** one fully-declared example of each archetype the later layers exercise.
- **Files:** `erp/assistant/services/actions.py`.
- **Steps:** declare full metadata on exactly these four:
  1. `create_sales_order_draft` — requires `("customer","item","warehouse")`; effects
     `Effect("sales_order","create", stock="draft")`; invariants `("doc_totals","period_open")`;
     compensation `None` (a draft is deleted, not compensated); risk `"draft"`;
     idempotency `("customer","items")`.
  2. `create_journal_entry_draft` — requires `("account",)`; effects
     `Effect("journal_entry","create", gl="draft")`; invariants `("journal_balanced","period_open")`;
     risk `"draft"`; idempotency `("lines","date")`.
  3. `create_stock_transfer_draft` — requires `("item","warehouse")`; effects
     `Effect("stock_transfer","create", stock="draft")`; invariants `("stock_non_negative",)`;
     risk `"draft"`; idempotency `("item","quantity","from_warehouse","to_warehouse")`.
  4. `create_customer` — requires `()`; effects `Effect("customer","create")`; invariants `()`;
     risk `"draft"`; idempotency `("query",)`.
- **Accept:** `pytest erp/assistant` green; in a shell,
  `ACTIONS["create_sales_order_draft"].effects[0].entity == "sales_order"`.
- **Output:** the slice FILE_02–05 will test against. The other 13 stay default — the mechanical
  fan-out is a logged follow-up (Haiku-fit), NOT part of this phase.

### [ ] T1.3 — Graph read API + registration decorator

- **Goal:** one place to ask "what does action X need/do" and one decorator so future actions
  register with semantics in a single statement.
- **Files:** NEW `erp/assistant/services/action_graph.py`; NEW test
  `erp/assistant/tests/test_action_graph.py`.
- **Steps:**
  1. `action_graph.py` exposes: `get(name) -> Action`, `all_actions()`,
     `unmet_requires(actor, name) -> list[str]` (checks each `requires` kind has ≥1 record the
     actor can see — reuse the existing lookup helpers in `actions.py`; a kind with no lookup
     helper returns "unknown", never raises), and `@register_action(**semantics)` — a decorator
     that wraps a `(build_proposal, execute)` pair into an `Action`, validates, and inserts into
     `ACTIONS`.
  2. Do NOT migrate existing actions to the decorator (churn, no benefit) — it exists for new
     actions from Phase A onward.
  3. Docstring documents the follow-up path: a future `@contract_action` decorator on module
     contracts auto-registering here = deep-vision moat #1; deliberately deferred (FILE_00
     "Registry home" decision).
- **Accept:** `pytest erp/assistant/tests/test_action_graph.py` green, covering: `unmet_requires`
  on an empty DB names the missing kinds; the decorator registers a toy action and the validator
  rejects a bad one.
- **Output:** the graph is queryable; new actions have a one-statement registration path.

### [ ] T1.4 — Surface risk in the planner prompt

- **Goal:** the loop prompt tells the model each action's risk class so proposals phrase
  themselves honestly ("this only prepares a draft").
- **Files:** `erp/assistant/services/actions.py::catalog_text` (L1437);
  `erp/assistant/tests/test_actions.py`.
- **Steps:** append `[risk: {a.risk}]` to each catalog line. Nothing else in the prompt changes.
- **Accept:** existing prompt/loop tests green; a test asserts `"[risk: draft]"` appears in
  `catalog_text()`.
- **Output:** planner prompt is risk-aware; groundwork for L5 autonomy rules later.

## After this session

`pytest erp/assistant` green → commit (`feat(assistant): os-foundations L0 — action graph v2 schema`)
→ check the boxes above → rename this file `FILE_01_ACTION_GRAPH_SCHEMA_done.md` → update
`erp-status` → fresh session for FILE_02.
