# SESSION 01 — Guard infrastructure (org toggle + typed retype-confirm)
# Files: erp/identity/models.py, erp/identity/migrations/, erp/identity/serializers.py,
#        erp/assistant/services/actions.py, erp/assistant/api/views.py,
#        apps/web/src/pages/settings/OrganizationPage.tsx, apps/web/src/api/identity.ts,
#        apps/web/src/api/assistant.ts, apps/web/src/assistant/ActionCard.tsx,
#        erp/assistant/tests/test_actions.py, erp/identity/tests/

**Model:** Opus. Safety-critical shared foundation — every later file in this plan (FILE_02–07)
depends on this guard being correct. No new posting action is registered here; this session proves
the mechanism with a monkeypatched toy action, same spirit as `test_actions.py`'s existing
`_toy_action` helper (which only tests `_validate_action` in isolation — this session goes further,
exercising the guard through the real HTTP confirm endpoint).

---

## Before You Start

1. Read `FILE_00_INDEX.md` in full — the guard mechanism section is this session's spec.
2. Read `erp/identity/models.py` `OrgPreferences` (single-row, pk=1, System-Admin-only-editable) and
   its `einvoice_enabled` field — the exact template for the new field.
3. Read `erp/identity/services.py` `get_org_preferences()`/`update_org_preferences()` and
   `erp/identity/serializers.py` `OrgPreferencesSerializer` — reuse, do not duplicate.
4. Read `apps/web/src/pages/settings/OrganizationPage.tsx` — the `settings.org.einvoice` `SettingRow`
   (a checkbox bound to `org.einvoice_enabled`, saved via `patchOrgPreferences`) is the exact row
   template to copy.
5. Read `erp/assistant/services/actions.py` `_can`/`_refused`/`build`/`execute`/`ACTIONS` and
   `erp/assistant/api/views.py` `ActionExecuteView.post` (confirms a proposal, calls
   `actions.execute`) end to end.
6. Read `apps/web/src/assistant/ActionCard.tsx` and `apps/web/src/api/assistant.ts`
   (`ActionProposal`, `executeAction`), and `apps/web/src/components/PaymentDialog.tsx` +
   `apps/web/src/lib/money.ts` (`parseToMinor`) — the retype-match precedent to reuse, not reinvent.

"Do not write anything yet."

---

## Task A — `OrgPreferences.assistant_posting_enabled`

- `erp/identity/models.py`: add `assistant_posting_enabled = models.BooleanField(default=False)`
  to `OrgPreferences`, directly below `einvoice_enabled`, with a one-line comment mirroring that
  field's style (what turning it on unlocks: posting actions from the assistant).
- Generate the migration (`manage.py makemigrations identity`).
- `erp/identity/serializers.py`: add `"assistant_posting_enabled"` to `OrgPreferencesSerializer`'s
  `fields`.
- No view/permission change needed — `OrgPreferencesView.patch` is already `SYSTEM_ADMIN`-only for
  every field on this serializer.

## Task B — `OrganizationPage.tsx` checkbox

- `apps/web/src/api/identity.ts`: add `assistant_posting_enabled: boolean;` to the `OrgPreferences`
  interface.
- `apps/web/src/pages/settings/OrganizationPage.tsx`: add a new `SettingRow` directly below the
  `settings.org.einvoice` row, same shape (checkbox bound to
  `org.assistant_posting_enabled`, `onChange={(e) => save({ assistant_posting_enabled: e.target.checked })}`).
- `ar.json`/`en.json`: add `settings.org.assistantPosting` (title) +
  `settings.org.assistantPostingDesc` (one line: "Let the assistant post, receive, and pay — not
  just draft. Off by default.").

## Task C — the shared guard in `actions.py`

Add, near `_can`/`_refused`:

```python
def _posting_enabled() -> bool:
    from erp.identity.services import get_org_preferences
    return get_org_preferences().assistant_posting_enabled


def _refused_posting_disabled() -> dict:
    return {"error": "Posting actions aren't turned on for this workspace. Ask your System Admin "
                     "to enable them in Settings → Organization."}


def _can_post(actor, *roles: str) -> bool:
    """Gate for any risk="post" action: the org toggle AND the same role check a draft action
    would use. Neither check replaces the other."""
    return _posting_enabled() and _can(actor, *roles)
```

**Two different call shapes, deliberately** — a build-time refusal should name the SPECIFIC reason
(toggle off vs. wrong role), but an execute-time refusal only needs to raise, never explain twice
(the proposal already explained it). So:

- Every `_build_*` for a `risk="post"` action checks the two conditions **separately, in this
  order**: `if not _posting_enabled(): return _refused_posting_disabled()`, then
  `if not _can(actor, *roles): return _refused()` — giving an accurate message either way.
- Every `_execute_*` for the same action calls the combined `_can_post(actor, *roles)` once and
  raises `PermissionError` if it's `False` — matching exactly how a plain `_can` failure raises
  `PermissionError` in every existing draft action's execute today; no message to pick here.

## Task D — the `challenge` convention + confirm-time verification

Add a small helper next to `idempotency_key`:

```python
def challenge(minor: int, currency: str = "EGP") -> dict:
    """The retype-confirm the UI shows for a risk="post" proposal: a human-readable label (reusing
    Money.format — no new formatting logic) plus the exact minor-unit target to match against."""
    from erp.accounting.domain.money import Money
    return {"label": Money(minor, currency).format(), "minor": minor}
```

Every risk="post" action's `build_proposal` includes `"challenge": challenge(<amount_minor>)` in
its returned dict when it succeeds (not on `{error}`/`{blocker}` returns). `build()` in `actions.py`
already forwards the whole proposal dict unchanged, so no change needed there.

`erp/assistant/api/views.py` `ActionExecuteView.post`: right before `actions.execute(...)` runs,
if `proposal.get("challenge")` is present, require `request.data.get("typed_minor")` to be an int
equal to `proposal["challenge"]["minor"]`; on mismatch or missing, return the existing calm
`ValidationError`-style 400 the view already uses elsewhere in this method — **do not** flip
`proposal["status"]` (the card must stay `"pending"` and reusable, exactly like a plain permission
refusal today never consumes the card).

## Task E — `ActionCard.tsx` + `api/assistant.ts`

- `ActionProposal` interface: add `challenge?: { label: string; minor: number };`.
- `executeAction(messageId, decision, typedMinor?: number)`: when `typedMinor` is defined, include
  `typed_minor: typedMinor` in the POST body.
- `ActionCard.tsx`: when `proposal.challenge` is present, render a text input above the footer
  buttons (label: `t("assistant.action.retypeLabel", { value: proposal.challenge.label })`); parse
  its value with `parseToMinor` on every keystroke; the Confirm button's `disabled` expression gains
  `|| (proposal.challenge && parsed !== proposal.challenge.minor)`; `resolve("confirm")` passes the
  parsed value through to `executeAction`. New i18n keys: `assistant.action.retypeLabel`,
  `assistant.action.retypeMismatch` (shown inline if the server 400s — reuse the existing
  `error` state slot the card already has for a failed confirm).

## Task F — tests

`erp/assistant/tests/test_actions.py`:
- `_can_post` unit tests: toggle off + right role → `False`; toggle on + wrong role → `False`;
  toggle on + right role → `True` (monkeypatch `identity.services.get_org_preferences` or set the
  `OrgPreferences` row directly via `get_or_create`).
- `challenge(4523000)` → `{"label": "45,230.00 EGP", "minor": 4523000}`.
- End-to-end guard test through the real view: `monkeypatch.setitem(actions.ACTIONS, "toy_post",
  Action(name="toy_post", ..., risk="post", kind="post", build_proposal=<returns a challenge>,
  execute=<records a call>))`, then drive `POST /api/assistant/actions/execute` (via DRF test
  client, a `Message` fixture with this proposal already in `meta`) through: toggle off → 400/error,
  card stays pending; toggle on, wrong `typed_minor` → 400, card stays pending, execute() never
  called; toggle on, right `typed_minor` → 200, execute() called once, card `confirmed`.

`erp/identity/tests/`: `OrgPreferencesView` PATCH round-trip for the new field, non-admin PATCH
still 403 (existing test file already covers the pattern — extend it, don't duplicate the class).

---

## Smoke Test

- [ ] `Settings → Organization` (as System Admin) shows the new checkbox, off by default; toggling
      it persists (reload the page, still checked); a non-admin user doesn't see a PATCH-capable
      control (existing admin-only gate, unchanged)
- [ ] Toy risk="post" action (monkeypatched in the test only — nothing user-visible yet): toggle
      off → confirm attempt refused calmly, card still pending; toggle on, wrong retyped value →
      400, card still pending; toggle on, right value → executes, card flips to confirmed
- [ ] `pytest erp/assistant erp/identity` green
- [ ] i18n parity (new keys in both `ar.json`/`en.json`) + `npx tsc --noEmit` + `python
      scripts/gates/gate03.py` green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_02_POST_JOURNAL_ENTRY.md and continue.
```
