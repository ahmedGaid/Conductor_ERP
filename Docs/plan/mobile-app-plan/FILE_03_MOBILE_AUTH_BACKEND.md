# SESSION 3 — Mobile Auth Backend
# Files: erp/identity/** (additive), erp/identity/tests/**, config URLs (read to find the right include)

**Objective:** give the Django backend everything a native client needs to authenticate:
short-lived access tokens + rotating refresh tokens, a device registry (name, platform, last
seen), remote logout ("sign out that phone" from any device), and a push-token registration
endpoint (used in session 15). All additive — web session auth is untouched.

**Why tokens, not cookies:** native apps hold credentials in the OS keystore, not a cookie jar;
refresh rotation + server-side revocation gives remote logout and MDM-style control. This is the
enterprise-security foundation the whole mobile app stands on.

---

## Before You Start

1. Open `erp/identity/models.py` → read the user model and any existing token/session models.
2. Open `erp/identity/api/` (or wherever its views live — find via `codegraph_explore "identity
   auth endpoints"`) → note the auth mechanism web uses today and DRF authentication classes
   configured in settings.
3. Open `erp/audit/services.py` → confirm the `record(...)` signature for audit events.
4. Check whether a JWT/token library is already a dependency. If NOT: **stop and write the
   DECISIONS entry first** — options are `djangorestframework-simplejwt` (standard, maintained)
   vs. a hand-rolled opaque-token model. Default recommendation: **opaque random tokens stored
   hashed in the DB** — no new dependency, revocation is a DELETE, and we don't need stateless
   validation at this scale. Decide, record, then build.

"Do not write anything yet."

---

## Task A — Models (assuming the opaque-token decision; adapt if DECISIONS chose JWT)

In `erp/identity/models.py`, add:

```python
class MobileDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mobile_devices")
    name = models.CharField(max_length=120)            # "iPhone 15 من أحمد" — device self-reports
    platform = models.CharField(max_length=10)          # "ios" | "android"
    app_version = models.CharField(max_length=20)
    push_token = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

class MobileToken(models.Model):
    device = models.ForeignKey(MobileDevice, on_delete=models.CASCADE, related_name="tokens")
    kind = models.CharField(max_length=8)                # "access" | "refresh"
    token_hash = models.CharField(max_length=64, unique=True)  # sha256 of the raw token
    expires_at = models.DateTimeField()
    rotated_from = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
```

Raw tokens: 32 random bytes, urlsafe-b64; only the hash is stored. Access TTL 15 min, refresh
TTL 30 days with rotation (each refresh issues a new pair and expires the old refresh token;
reuse of a consumed refresh token revokes the whole device — token-theft tripwire).

## Task B — Endpoints (new module, e.g. `erp/identity/api/mobile.py`, wired additively into urls)

| Endpoint | Method | Behaviour |
|---|---|---|
| `/api/mobile/auth/login` | POST | credentials + device info → device row + token pair. Audit `record(actor, "mobile.login", device)`. Same throttling/lockout policy as web login (read what web does; match it). |
| `/api/mobile/auth/refresh` | POST | refresh token → new pair, rotation + reuse tripwire as above. |
| `/api/mobile/auth/logout` | POST | revoke calling device (sets `revoked_at`, deletes live tokens). |
| `/api/mobile/devices` | GET | current user's devices (name, platform, last seen) — powers "manage devices" on BOTH web and mobile settings. |
| `/api/mobile/devices/<id>/revoke` | POST | remote logout of any of the user's own devices. Audit it. |
| `/api/mobile/devices/push-token` | POST | store/replace the Expo push token for the calling device (session 15 consumes). |

Add a DRF authentication class `MobileTokenAuthentication` (`Authorization: Bearer <token>`):
hash lookup → live, unexpired, device not revoked → `request.user`. Append it to DRF's default
authentication classes so **every existing API endpoint accepts mobile tokens with zero changes**
— this single line is what guarantees "one API". RBAC/permissions then apply identically because
`request.user` is the same user.

## Task C — Tests (`erp/identity/tests/test_mobile_auth.py`)

Cover: login happy path (ar name round-trips), wrong password (blame-free error message key),
access token works on a real existing endpoint (pick one from `erp/sales` API), expired access
rejected, refresh rotation works, refresh REUSE revokes device, revoked device rejected
everywhere, device list scoped to owner, push-token upsert, audit rows written.

---

## Smoke Test

- [ ] `pytest erp/identity` green, including all Task C cases
- [ ] Manual: `curl` login → token → call an existing sales list endpoint with `Bearer` → same
      JSON web gets; permissions of a restricted test user correctly limit the response
- [ ] Refresh reuse → device revoked → old access token now 401 (tripwire proven end-to-end)
- [ ] Web login flow untouched: log into the web app normally, browse two pages
- [ ] `python manage.py migrate` clean forward; migration touches ONLY identity app

## Risks

- Appending an auth class can shadow throttling assumptions → run the full backend test suite,
  not just identity.
- Clock skew on devices → server timestamps only; the client never validates expiry locally
  except as a pre-emptive refresh hint.

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file with _done
→ /compact → open FILE_04_API_CLIENT_AND_CACHE.md
```
