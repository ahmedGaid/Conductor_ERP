# SESSION 10 — Declarative Confirmation Registry (Action Safety)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py

---

## Before You Start

**Prerequisite: ai-workspace FILE_10_SAFE_ACTIONS is shipped** (propose → confirm → execute
with audit). This session formalizes its safety gate so every FUTURE action kind inherits it
declaratively — it changes structure, not behaviour.

1. Open `erp/assistant/services/actions.py` → read the whole file: how actions are declared,
   what `build` does (validate + price, no write), how the execute path re-reads the proposal
   from message meta and runs the module contract.
2. Open `erp/assistant/tests/test_actions.py` → the seams tests fake.
3. Open the execute endpoint in `erp/assistant/api/views.py` (search "execute") → confirm the
   permission check + status transitions (pending → executed/dismissed).

Do not write anything yet.

---

## Task A — Action metadata

However actions are declared in the file you read (dataclass / dict registry — follow it),
give every action two declarative fields:

```python
    kind: str                    # "create" | "update" | "delete" | "approve" | "post" |
                                 # "reverse" | "cancel" | "close_period" | "bulk" | "adjust"
    requires_confirm: bool = True   # NO action may default to False
```

and a module-level constant:

```python
# The harness spec's irreversible list: these kinds can NEVER ship with requires_confirm=False,
# and their confirm card must restate consequences (not just the payload).
DESTRUCTIVE_KINDS = {"delete", "cancel", "approve", "post", "reverse", "close_period",
                     "bulk", "adjust"}
```

Current actions (drafts/creates) get `kind="create"`.

## Task B — Enforcement, not convention

1. In the registry's construction (or an import-time assert loop right below it):

```python
for _a in <registry>.values():
    assert _a.requires_confirm or _a.kind not in DESTRUCTIVE_KINDS, (
        f"action {_a.name}: destructive kind '{_a.kind}' must require confirmation")
```

2. In the execute path, before running the contract, re-validate in order and stop at the
   first failure (harness spec: validate → confirm → execute):
   - proposal status is "pending" (not already executed/dismissed) — likely exists; keep
   - the actor STILL has the action's permission (permissions may have changed since propose)
   - the action's `build`-time validation still holds (re-run the cheap checks: entities still
     exist, period/status unchanged) — follow whatever validation `build` already factors out;
     extract a shared helper if build's validation is inline, so both call one function.
   Each failure returns the existing blame-free error shape, never a half-executed write.

3. Confirm-card payload (`build`'s return) gains `"kind"`, so the client card can phrase
   destructive kinds more explicitly later — additive key, no client change required now.

## Task C — Tests

Extend `tests/test_actions.py`:
- test_every_action_declares_kind_and_confirm — iterate registry: all have a kind from the
  known set, all `requires_confirm` True (today)
- test_destructive_kind_without_confirm_is_impossible — constructing/registering an action
  with kind "delete", requires_confirm False → the assert trips
- test_execute_reruns_permission_check — build as allowed user, strip role, execute → refused,
  nothing written
- test_execute_revalidates_before_write — delete the referenced entity between build and
  execute → calm validation error, nothing written
- test_proposal_kind_rides_in_payload — built proposal dict contains "kind"

---

## Smoke Test

- [ ] `pytest erp/assistant` green
- [ ] Dev server: propose + confirm a draft (the session-10 flow) → works exactly as before
- [ ] Confirm the same proposal twice → second attempt refused calmly (status guard)
- [ ] Revoke the role between propose and confirm → execute refused, no write
- [ ] Import-time assert verified: temporarily add a fake delete-kind action with
      requires_confirm=False → app fails to start; remove it

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_10_CONFIRM_REGISTRY_done.md
→ Type /compact in Claude Code
→ Open FILE_11_ACCEPTANCE.md and continue
```
