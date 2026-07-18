# SESSION 14 — API Keys + Developer Docs Page
# Files: erp/identity/ (ApiKey model + auth class + service), erp/identity/tests/, apps/web settings→developers page, i18n locales

Twenty reference: Settings → "APIs & MCP" — keys, docs, playground in one place. Ours is the
minimal honest version: role-bound keys + a truthful reference page. This turns the verified
internal DRF API into an integration story (accountant tools, Phase E WhatsApp bridge).

---

## Before You Start

1. Open `erp/identity/` auth (simplejwt wiring) + DRF `DEFAULT_AUTHENTICATION_CLASSES` in
   settings → where a second auth class slots in.
2. Open the RBAC role model + `require_role` → keys BIND to a role; a key is never broader than
   the role it carries.
3. Open gate17's route inventory (FILE_03) → the docs page reuses that generator (one truth).

"Do not write anything yet."

---

## Task A — Keys

`ApiKey(name, prefix, hashed_key, role FK, created_by, expires_at?, last_used_at, is_active)`.
Secret shown ONCE at creation (`ck_<prefix>_<random>`); stored hashed. DRF auth class:
`Authorization: Api-Key <key>` → authenticates as a key-principal carrying the bound role;
audit rows record the key identity (never impersonates a human user). Throttle scope for keys.
Service fns admin-only: create/revoke/list.

## Task B — Settings → "المطوّرون / Developers"

Keys table (name, role, prefix, last used, expiry, revoke w/ confirm); create dialog with the
one-time secret display + copy (calm warning it won't show again). Designed empty state.

## Task C — Reference page

Static in-app page (same settings area): endpoint list generated from the gate17 inventory
(method, path, brief), auth instructions with a copy-pasteable curl, rate-limit note, and the
integer-minor-units money rule stated plainly. Regenerated at build/gate time — never
hand-maintained.

## Task D — Tests

Key auth happy path; revoked/expired → 401; role enforcement (key with sales role hits
accounting write → 403); audit records key principal; hashed storage (raw secret nowhere).

---

## Smoke Test

- [ ] `curl -H "Authorization: Api-Key …" /api/sales/orders/` → 200; after revoke → 401
- [ ] Key bound to read-only role rejected on POST with human error
- [ ] Secret visible exactly once in UI; DB stores hash only
- [ ] `pytest erp/identity` green; parity + tsc + gate03 green; brand checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_15_ARABIC_USER_DOCS.md in a FRESH session.
```
