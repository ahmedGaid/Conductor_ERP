# SESSION 04 — Accounting actions (journal-entry draft, create account)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py,
#        apps/web/src/i18n/locales/{ar,en}.json (only if a card needs a new label)

**Model:** Opus. Not mechanical — a journal must balance and the card must prove it before a human
confirms. Keep Opus for this one.

---

## Before You Start

1. Read `FILE_00_INDEX.md` (drafts-only law).
2. Read an existing action pair as the template.
3. Read `erp/accounting/contracts.py` — confirm functions/args for: create an **unposted** journal
   entry (draft) and create a ledger account. Note the balance validation the contract enforces and
   the errors it raises (unbalanced, unknown account code, inactive account). **Posting** a journal
   and **reversing** one are out of scope (FILE_06 deferred decision) — draft only.

"Do not write anything yet."

---

## Task A — `create_journal_entry_draft`

Args: `lines` (list of {account (code or name), debit? , credit? , memo?}), `date` (optional,
defaults today), `reference` (optional). `build_proposal`:
- resolve every account code/name → real account; unknown/inactive → `{error}` (calm, no card);
- compute total debits vs credits in minor units and show both on the card;
- **hard rule:** if debits ≠ credits, return `{error}` explaining the imbalance and by how much —
  never emit a card for an unbalanced entry (the human should not be asked to confirm bad books).
`execute` creates the entry in **unposted/draft** state. `kind="create"`.

## Task B — `create_account`

Args: `name`, `type` (asset/liability/equity/income/expense), optional `code` (auto-assign if
omitted), optional `parent`. Duplicate-check on name/code → **risk line**, not silent create.
`build_proposal` shows the account that will be created and its place in the tree. `execute` creates
the account master. `kind="create"`.

## Task C — register + tests

- Add both to `ACTIONS`; extend `ACTION_ARG_FIELDS` with `lines`, `date`, `reference`, `type`,
  `code`, `parent`, `memo` as the contracts require (note: `items` already exists — journals use
  `lines`, keep them separate to avoid shape confusion).
- `test_actions.py`: balanced journal → proposal shows equal debit/credit totals → confirm creates
  an **unposted** entry (assert status is draft/unposted, NOT posted) + audit + link; **unbalanced
  journal → `{error}`, no card** (explicit test); unknown account → `{error}`; `create_account`
  duplicate → risk line; dismiss inert; double-confirm 409; unpermitted actor refused both stages.

---

## Smoke Test

- [ ] "Draft a journal: debit Rent 5000, credit Cash 5000" → balanced card, both totals shown →
      confirm → **unposted** entry, audit + link
- [ ] Unbalanced ask (debit 5000, credit 4000) → calm explanation of the 1000 gap, NO card
- [ ] Unknown account name → calm refusal, no card
- [ ] "Create an expense account called Marketing" → card → confirm → account created
- [ ] Duplicate account name → risk line, not silent create
- [ ] User without accounting permission → refused calmly both stages
- [ ] `pytest erp/assistant` + (if any new string) i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_05_CRM_ACTIONS.md and continue.
```
