# Session 00 — Security hardening (do this first)

**Goal:** close the real gaps found in the 2026-07-02 targeted review so no later feature (and no
SaaS tenant boundary) inherits a hole. Recall `erp-frontend` only if you touch UI; this is mostly
backend. Work on a branch `feat/sec-hardening`.

## Context / where the problems are
- `erp/identity/access.py` — `scope_for(user, code)` returns `OWN | BRANCH | ALL` but **nothing
  applies it to querysets**. List views return everything.
- `erp/einvoice/api/views.py:54` — `ETAInvoice.objects.all()[:200]` proves the leak: any Accountant
  sees every branch's invoices.
- `erp/workflow/adapters/rest.py` + `adapters/webhook.py` — `urllib.urlopen(url)` with no egress
  guard (SSRF).
- `config/settings/base.py` — JWT 30m/7d, throttle `anon 60/min` (login sits under this).
- `apps/web/src/api/client.ts` — verify where the JWT is stored (localStorage vs memory).

## Tasks (in order)

### 1. Enforce data scope on reads (the big one)
1. Add `erp/identity/scoping.py` with `scope_queryset(qs, user, code, *, branch_field="branch",
   owner_field="created_by")`:
   - superadmin / scope `ALL` → `qs` unchanged.
   - scope `BRANCH` → `qs.filter(branch__in=user's branches)` (derive the user's branch set; a user
     has one home branch today — design for many).
   - scope `OWN` → `qs.filter(**{owner_field: user})`.
2. Sweep **every list/detail API view** that returns business records (sales, purchasing, inventory,
   crm, accounting, einvoice, pricing). Wrap the base queryset in `scope_queryset(...)`. Detail
   views must 404 (not 403) when the object is outside scope — reuse `get_object_or_404` on the
   scoped queryset.
3. Start with `einvoice` as the reference implementation, then fan out one module per commit.
4. **Test:** add `test_scope_*` per module — a BRANCH-scoped user in branch A cannot see branch B's
   rows via list or detail. Add to the gate suite (extend `gate12` security tests).

### 2. Block SSRF in workflow egress
1. Add `erp/workflow/adapters/egress.py::assert_public_url(url)`:
   - parse; require scheme in `{http, https}`.
   - resolve host; reject if it resolves to loopback / link-local / private / reserved
     (`ipaddress.ip_address(...).is_private/.is_loopback/.is_link_local/.is_reserved`) — reject
     `169.254.169.254` explicitly.
   - optional env allowlist `WORKFLOW_EGRESS_ALLOWLIST` (host suffixes); when set, host must match.
2. Call it at the top of `RestAdapter.call` (webhook flows through REST, so one guard covers both).
   Return `AdapterResult(ok=False, error="egress blocked: <reason>")` — do not raise.
3. **Test:** `test_egress_blocks_metadata_ip`, `test_egress_blocks_rfc1918`, `test_allowlist_pass`.

### 3. Tighten auth surface
1. Add a dedicated login throttle: subclass `ScopedRateThrottle` (scope `login`, e.g. `5/min` per IP)
   on the token-obtain view only; keep `anon 60/min` global. Env-tunable `DRF_THROTTLE_LOGIN`.
2. Confirm refresh-token rotation + blacklist is on (it is in `SIMPLE_JWT`) — add a test that a
   rotated-out refresh token is rejected.
3. **JWT storage:** open `apps/web/src/api/client.ts`. If the access token is in `localStorage`,
   move the **refresh** token to an HttpOnly, Secure, SameSite=Strict cookie and keep only the
   short-lived access token in memory (module variable, not storage). If already in memory, just
   document it. This kills XSS token theft.
4. Add password validators `NumericPasswordValidator` + `UserAttributeSimilarityValidator` to
   `AUTH_PASSWORD_VALIDATORS`.

### 4. File-handling review (import + backup)
1. Locate the CSV import endpoint (Customers/Suppliers/Items generic import) and the Docker
   backup/restore path. Verify: max upload size enforced, content-type checked, row cap, and that
   restore does not shell-interpolate untrusted paths. Add limits where missing.
2. **Test:** oversized upload rejected; malformed CSV yields a designed error, not a 500.

### 5. Security headers / prod checklist
1. Run `python manage.py check --deploy --settings=config.settings.prod`; resolve every warning that
   isn't already env-gated. Add a `Content-Security-Policy` (self + no inline where feasible;
   customer-hosted, no CDN, so CSP can be strict).

## Done bar
- New `test_scope_*`, `test_egress_*`, `test_login_throttle` all pass; `gate:all` GREEN.
- `manage.py check --deploy` clean under prod settings.
- Write a one-paragraph note to `DECISIONS.md` "Security 2026-07": scope model is now enforced, not
  advisory; egress is default-deny.
