# SESSION 11 — Ambient AI Digests
# Files: erp/assistant/services/digest.py (new), a schedule entry (locate the pattern), erp/assistant/tests/test_digest.py, i18n only if a UI string appears

---

## Before You Start

1. Open `erp/assistant/tools.py` → the digest is COMPOSED from existing tool runners
   (`_low_stock`, `_overdue_receivables`, `_expiring_batches`, `_open_purchase_orders`) —
   read their result shapes. No new data access.
2. Find how scheduled/periodic work runs in this codebase: grep `cron`, `celery`, `beat`,
   `management/commands` under `erp/` → the digest must use the EXISTING mechanism (likely a
   management command run by the host's scheduler — confirm). If none exists, a management
   command IS the deliverable; scheduling = a documented crontab line, nothing new built.
3. Open `erp/notifications/services/dispatch.py` (read in a prior session: `dispatch(channel,
   recipient, subject, body, ...)`) — the digest sends through it, landing in the session-08
   inbox (inapp channel) and/or email.
4. Check RBAC: who receives which digest — a digest runs PER USER as that user (tools respect
   actor), so each recipient only sees their modules.

Do not write anything yet.

---

## Task A — `services/digest.py`

```python
def build_digest(actor) -> dict | None:
    """Compose the morning digest for one user from existing tool runners, run AS the user.

    Sections (each skipped when empty): overdue receivables (top 3 + count), low stock
    (top 3 + count), batches expiring ≤7 days, POs stuck >N days. Returns None when EVERY
    section is empty — silence is the default, a digest must earn its send (Telegram calm:
    no "all good!" spam)."""


def send_digests() -> int:
    """Build + dispatch for every active user with assistant access. Returns count sent.
    Body is plain text in the user's language (read their preference), numbers via the same
    formatting discipline as answers. Dispatch failures already land as failed rows —
    never raise."""
```

Write real bodies. Tone: blame-free, factual lines, one deep-link path per section (the web
routes for the relevant filtered lists — reuse the reference→route convention).

## Task B — The trigger

Management command `send_ai_digests` (or the existing scheduler pattern from step 2).
Document the schedule line (e.g. 07:00 Africa/Cairo, weekdays) in the deployment docs where
other ops runbook lines live — find them first.

## Task C — Tests

- test_digest_skips_empty_sections / test_digest_none_when_all_quiet
- test_digest_respects_module_access — user without inventory access → no stock section
- test_send_digests_dispatches_per_user (dispatch seam faked)
- test_digest_language_follows_user_pref

---

## Smoke Test

- [ ] Seeded data: run the command → inbox rows appear per user, sections correct
- [ ] User without a module's access → that section absent from THEIR digest
- [ ] All-quiet dataset → nothing sent
- [ ] Arabic-preference user gets Arabic digest
- [ ] `pytest erp/assistant` green

---

## After This Session

```
Smoke test passed?
→ Commit, rename FILE_11_AMBIENT_DIGESTS_done.md
→ /compact → FILE_12_CMDK_AI_BRIDGE.md
```
