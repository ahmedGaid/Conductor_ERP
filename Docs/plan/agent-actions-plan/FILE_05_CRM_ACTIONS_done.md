# SESSION 05 — CRM actions (create opportunity, advance stage, log activity)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py,
#        apps/web/src/i18n/locales/{ar,en}.json (only if a card needs a new label)

**Model:** Sonnet. Pattern-replication. Say so, `/model` down.

---

## Before You Start

1. Read `FILE_00_INDEX.md` (drafts-only / actor / audit law).
2. Read an existing action pair as the template, and the existing `create_customer` action.
3. Read the CRM contracts (`erp/crm/contracts.py` or the sales/CRM module that owns `Opportunity`
   and activities — confirm the app path first). Confirm functions/args for: create opportunity,
   advance an opportunity's stage, log an activity/note against a customer or opportunity.

"Do not write anything yet."

---

## Task A — `create_opportunity`

Args: `customer` (code or name), `name` (deal name), optional `value` (minor units), optional
`expected_close` (date). `build_proposal` resolves the customer, shows the deal summary. `execute`
creates the opportunity. `kind="create"`.

## Task B — `advance_opportunity_stage`

Args: `query` (opportunity number/name), `stage` (target stage). `build_proposal` finds the
opportunity, shows current → target stage; risk line if the jump skips stages or moves to a closed
stage. `execute` updates the stage. `kind="update"`.

## Task C — `log_activity`

Args: `query` (customer or opportunity to attach to), `note` (the activity text), optional `type`
(call/email/meeting/note). `build_proposal` shows what will be logged and against which record.
`execute` writes the activity. `kind="create"`.

## Task D — register + tests

- Add three to `ACTIONS`; extend `ACTION_ARG_FIELDS` with `name`, `value`, `expected_close`,
  `stage`, `note`, `type` as the contracts require.
- `test_actions.py`: opportunity proposal resolves customer → confirm creates it + audit + link;
  stage advance shows current→target and confirms; skip/closed-stage jump surfaces the risk line;
  `log_activity` attaches to the right record; dismiss inert; double-confirm 409; unpermitted actor
  refused both stages.

---

## Smoke Test

- [ ] "New opportunity for <customer>: '<deal>' worth 50000 closing next month" → card → confirm →
      opportunity created, audit + link
- [ ] "Move opportunity OPP-… to Won" → current→target card → confirm → stage advanced
- [ ] "Log a call with <customer>: discussed renewal" → card → confirm → activity logged on the record
- [ ] User without CRM permission → refused calmly both stages
- [ ] `pytest erp/assistant` + (if any new string) i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_06_ACCEPTANCE.md and continue.
```
