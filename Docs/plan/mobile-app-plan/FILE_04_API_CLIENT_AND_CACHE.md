# SESSION 4 — API Client & Read Cache
# Files: apps/mobile/lib/core/network/** (new), apps/mobile/lib/data/datasources/remote/** (new),
#        apps/mobile/lib/data/datasources/local/cache_db.dart (new, drift),
#        apps/mobile/lib/core/di/injection.dart (new)

**Objective:** the data spine of the app — a `dio` client with automatic auth attach + silent
refresh + retry, and a `drift` (SQLite) read cache implementing **stale-while-revalidate**: every
screen renders instantly from cache, then quietly updates from the network. This is what makes
the app feel instant on Egyptian mobile networks, and stay useful offline.

**Why hand-rolled cache, not a data library:** the pattern we need is small: one repository
mixin, one cache table, one revalidation rule. Own it — no extra state/cache dependency beyond
the approved list.

---

## Before You Start

1. Open `apps/web/src/api/` → read 2–3 endpoint modules → note base-URL handling, error envelope
   shape, pagination shape. Mobile mirrors these exactly (Dart models in `lib/data/models/`).
2. Re-read session 03's endpoints (login/refresh) — the client implements their contract.
3. Recall `flutter-lessons`: issue 1 (HTTP-probe connectivity), issue 2 (no TTL for
   remote-vs-local choice), issue 3 (`_ready` init future), issue 7 (DI order).
4. Read current `drift` docs (table/DAO API and codegen via `build_runner`).

"Do not write anything yet."

---

## Task A — Token store + dio client (`lib/core/network/`)

1. Token pair lives in `flutter_secure_storage` (Keychain/Keystore) — never prefs. In-memory
   copy for hot use; loaded at app start before the router decides the first route.
2. `NetworkInfo` (`lib/core/network/network_info.dart`): HTTP HEAD probe via `dart:io
   HttpClient` — google.com + 1.1.1.1 in parallel, 5 s timeout, ANY success = online
   (`flutter-lessons` issue 1; `internet_connection_checker` is banned).
3. `ApiClient` wrapping `dio`:
   - interceptor attaches `Authorization: Bearer <access>`
   - on 401: single-flight refresh (concurrent 401s await ONE refresh `Completer`), then replay
     the request once; refresh failure → clear tokens → emit an `authExpired` event on an auth
     stream (session 07 routes this to the sign-in screen with a calm, designed message — never
     a raw error)
   - network failure: throw a typed `OfflineFailure` (the cache layer catches it)
   - timeouts: 15 s default; no automatic retry of non-idempotent requests
4. Error envelope: parse the backend's standard error shape (matched in Before-You-Start read)
   into a typed `ApiFailure { key, message, fields? }` in `lib/core/errors/` so screens can show
   translated, blame-free messages via i18n keys — mobile never displays raw server strings.

## Task B — drift read cache (`lib/data/datasources/local/cache_db.dart`)

1. One drift database `conductor.db`; drift's schema versioning handles migrations. v1 table:

```dart
class CacheEntries extends Table {
  TextColumn get key => text()();            // canonical URL incl. sorted query params
  TextColumn get payload => text()();        // JSON
  IntColumn get fetchedAt => integer()();    // epoch ms
  TextColumn get etag => text().nullable()();
  @override Set<Column> get primaryKey => {key};
}
```

2. `CachedRepository` mixin (or base class) used by every read repository —
   `cachedFetch<T>(key, remote, fromJson)`:
   - emit 1: cached payload if present (with an `isStale` flag when older than a staleness hint)
   - always kick a background revalidate (send `If-None-Match` when etag held; treat 304 as
     fresh-confirm) unless `NetworkInfo` says offline
   - revalidate success → write cache, emit updated data (ONE additional emit — no Loading state
     between, `flutter-lessons` issues 4–5); failure while cache exists → keep showing cache,
     expose `isOffline` so screens can show the quiet offline indicator (session 05 builds it —
     a small monochrome pill, not a red banner)
   - scope keys per user id (login switch must not leak another user's cache — clear on user
     change)
   - remote-vs-local choice is connectivity-based only, NO TTL (`flutter-lessons` issue 2);
     staleness hint affects the `isStale` flag, never triggers refetch loops
3. Cache eviction: on app start, delete rows older than 14 days; cap total rows (~2000, LRU by
   `fetchedAt`). Attachments are NOT cached here (session 13 has its own file store).
4. Any local datasource with async init uses `late final Future<void> _ready = _init();` and
   awaits it in every public method (`flutter-lessons` issue 3).

## Task C — DI + first real endpoints

1. `lib/core/di/injection.dart`: `get_it` wiring in the binding order from `flutter-lessons`
   issue 7 — secure storage/prefs → `NetworkInfo` + `ApiClient` → datasources → repositories →
   use cases → BLoCs (factories; auth/settings blocs lazy singletons).
2. Implement auth datasource + repository (login/refresh/logout/devices against session 03) and
   `me` (current user + permissions — find the existing endpoint web uses for its
   session/permissions bootstrap; reuse it). Dart models in `lib/data/models/` with `fromJson`/
   `toJson` + round-trip unit tests; timestamps arrive as ISO strings (`flutter-lessons`
   issue 11).
3. A temporary dev screen lists devices through the full spine (bloc → use case → repo →
   cachedFetch) to prove it.

---

## Smoke Test

- [ ] Dev screen: login (against local Django on LAN — document the dev base URL setup, Android
      emulator `10.0.2.2` vs device LAN IP; base URL injected via `--dart-define`, never
      hardcoded), device list renders
- [ ] Kill the network (airplane mode) → reopen app → device list still renders from cache with
      offline indicator; restore network → list revalidates silently (verify via a changed
      device name from web)
- [ ] Force-expire the access token (set TTL 10 s server-side temporarily) → next call silently
      refreshes; TWO simultaneous calls trigger exactly ONE refresh (log-assert), both succeed
- [ ] Revoke the device from Django admin → next call routes to `authExpired` (console event ok
      for now), tokens cleared from secure storage
- [ ] Login as a second user → first user's cached rows are gone (scoping proven)
- [ ] `flutter analyze` 0 issues; `flutter test` green (model round-trips, single-flight refresh
      unit test); money/i18n untouched

## Risks

- Refresh races are THE classic mobile-auth bug → the single-flight test above is non-negotiable.
- Emulator networking confusion burns time → the dev-base-URL doc note in Task C prevents it.
- drift codegen (`build_runner`) friction → commit generated files; regeneration documented in
  the session commit message.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_05_DESIGN_SYSTEM.md
Phase 0 complete — natural merge checkpoint.
```
