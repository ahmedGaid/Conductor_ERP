# SESSION 4 — API Client & Read Cache
# Files: apps/mobile/src/api/client.ts (new), apps/mobile/src/api/endpoints/** (new),
#        apps/mobile/src/offline/db.ts (new), apps/mobile/src/offline/readCache.ts (new)

**Objective:** the data spine of the app — a typed fetch client with automatic auth attach +
silent refresh + retry, and an SQLite read cache implementing **stale-while-revalidate**: every
screen renders instantly from cache, then quietly updates from the network. This is what makes
the app feel instant on Egyptian mobile networks, and stay useful offline.

**Why hand-rolled, not a data library:** react-query/SWR are new dependencies and their offline
persistence story would still need custom SQLite glue. The pattern we need is small: one hook,
one cache table, one revalidation rule. Own it.

---

## Before You Start

1. Open `apps/web/src/api/` → read 2–3 endpoint modules → note base-URL handling, error envelope
   shape, pagination shape. Mobile mirrors these exactly.
2. Open `packages/core/api-types.ts` (session 02) → this is where response types live.
3. Re-read session 03's endpoints (login/refresh) — the client implements their contract.
4. Read current `expo-sqlite` API docs (sync vs async API has changed across SDK versions).

"Do not write anything yet."

---

## Task A — Token store + fetch client (`src/api/client.ts`)

1. Token pair lives in `expo-secure-store` (Keychain/Keystore) — never AsyncStorage. In-memory
   copy for hot use; `loadTokens()` at app start.
2. `apiFetch<T>(path, init?)`:
   - attach `Authorization: Bearer <access>`
   - on 401: single-flight refresh (concurrent 401s await ONE refresh promise), then replay the
     request once; refresh failure → clear tokens → emit `authExpired` event (session 07 routes
     this to the sign-in screen with a calm, designed message — never a raw error)
   - network failure: throw a typed `OfflineError` (the cache layer catches it)
   - timeouts: 15 s default; no automatic retry of non-idempotent requests
3. Error envelope: parse the backend's standard error shape (matched in Before-You-Start read)
   into a typed `ApiError { key, message, fields? }` so screens can show translated,
   blame-free messages via i18n keys — mobile never displays raw server strings.

## Task B — SQLite cache (`src/offline/db.ts`, `src/offline/readCache.ts`)

1. `db.ts`: open one database `conductor.db`; migration runner (versioned `PRAGMA user_version`).
   v1 schema:

```sql
CREATE TABLE cache (
  key TEXT PRIMARY KEY,          -- canonical URL incl. sorted query params
  payload TEXT NOT NULL,         -- JSON
  fetched_at INTEGER NOT NULL,   -- epoch ms
  etag TEXT
);
```

2. `readCache.ts`: `useApiQuery<T>(path, { ttl, params })` hook —
   - render 1: return cached payload if present (with `isStale` flag when older than `ttl`)
   - always kick a background revalidate (send `If-None-Match` when etag held; treat 304 as
     fresh-confirm) unless offline
   - revalidate success → write cache, update state; failure while cache exists → keep showing
     cache, expose `isOffline` so screens can show the quiet offline indicator (session 05
     builds it — a small monochrome pill, not a red banner)
   - scope keys per user id (login switch must not leak another user's cache — clear on user change)
3. Cache eviction: on app start, delete rows older than 14 days; cap total rows (~2000, LRU by
   `fetched_at`). Attachments are NOT cached here (session 13 has its own file store).

## Task C — First real endpoints (`src/api/endpoints/`)

Implement `auth.ts` (login/refresh/logout/devices against session 03) and `me.ts` (current user +
permissions — find the existing endpoint web uses for its session/permissions bootstrap; reuse
it). Types in `packages/core/api-types.ts`. A temporary dev screen lists devices from
`useApiQuery` to prove the whole spine.

---

## Smoke Test

- [ ] Dev screen: login (against local Django on LAN — document the dev base URL setup, Android
      emulator `10.0.2.2` vs device LAN IP), device list renders
- [ ] Kill the network (airplane mode) → reopen app → device list still renders from cache with
      offline indicator; restore network → list revalidates silently (verify via a changed
      device name from web)
- [ ] Force-expire the access token (set TTL 10 s server-side temporarily) → next call silently
      refreshes; TWO simultaneous calls trigger exactly ONE refresh (log-assert), both succeed
- [ ] Revoke the device from Django admin → next call routes to `authExpired` (console event ok
      for now), tokens cleared from secure store
- [ ] Login as a second user → first user's cached rows are gone (scoping proven)
- [ ] `npx tsc --noEmit` green; money/i18n untouched

## Risks

- Refresh races are THE classic mobile-auth bug → the single-flight test above is non-negotiable.
- Emulator networking confusion burns time → the dev-base-URL doc note in Task C prevents it.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_05_DESIGN_SYSTEM.md
Phase 0 complete — natural merge checkpoint.
```
