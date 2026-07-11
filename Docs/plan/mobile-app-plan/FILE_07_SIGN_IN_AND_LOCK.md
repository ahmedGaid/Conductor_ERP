# SESSION 7 — Sign-in & Biometric Lock
# Files: apps/mobile/lib/presentation/pages/auth/** (new), apps/mobile/lib/core/auth/** (new),
#        apps/mobile/lib/presentation/pages/more/devices_page.dart, locales (mobile.auth.* keys)

**Objective:** the front door — a calm, on-brand sign-in screen, secure credential handling, and
an app lock: Face ID / Touch ID / Android biometrics (device-PIN fallback) required on cold start
and after backgrounding. Plus the "manage devices" screen (remote logout from session 03) so
users see and control every signed-in phone.

**Security model recap:** tokens in `flutter_secure_storage` (session 04); biometrics gate ACCESS
to the app, they never replace server auth. Server can kill any device at any time (revocation →
`authExpired` → this session's sign-out path).

---

## Before You Start

1. Open web's login page → mirror copy tone, field order, error wording (same i18n keys where
   they exist).
2. Open the session-04 auth repository + the `authExpired` stream.
3. Read `local_auth` docs: `canCheckBiometrics`, `getAvailableBiometrics`, `authenticate` options
   (`biometricOnly: false` — allow device-credential fallback; a user with gloves still needs in).
4. Open session 03's device endpoints for the devices screen contract.
5. Recall `flutter-lessons` issues 6 (local `_submitting` bool for the button spinner, side
   effects in listener) and 7 (auth bloc first; router listens to it).

"Do not write anything yet."

---

## Task A — Sign-in screen

1. Layout: wordmark (monochrome, from assets — export per Identity System, never the coloured
   logo), company-server field IF the product supports self-hosted servers (check how web/dev
   handles base URLs — for now a build-config base URL via `--dart-define` + hidden dev override
   via 7 taps on the wordmark), username/email + password, one primary button.
2. States: designed loading (button spinner from a local `_submitting` bool, fields disabled),
   blame-free errors from `ApiFailure` keys ("كلمة المرور غير صحيحة — جرّب مرة أخرى" tone; exact
   copy through the conductor-brand lexicon) shown via `BlocListener`, offline state
   ("لا يوجد اتصال" pill + retry).
3. On success: store tokens, register device name (`device_info_plus`? NO — not on the approved
   list; use `Platform` basics + a user-editable name field defaulting to platform model if
   available without a new dep; if a dep is truly needed, stop and ask per ground rule 6),
   navigate to tabs, THEN offer biometric enrolment in an AppSheet: "افتح كوندكتور ببصمتك" —
   enable/later. Never force it.

## Task B — App lock (`lib/core/auth/lock_cubit.dart`, `pages/auth/lock_page.dart`)

1. State machine: `unlocked` → (background > 60 s OR cold start, when biometrics enrolled) →
   `locked` → `local_auth.authenticate` → `unlocked`. Backgrounding detected via
   `WidgetsBindingObserver.didChangeAppLifecycleState`. Grace period constant in one place;
   later a setting.
2. `LockPage`: full-screen, wordmark + one "unlock" button (auto-triggers prompt on mount;
   button is the retry). Fallback path after repeated failure: sign out (with confirm AppDialog —
   destructive, so haptic + explicit wording).
3. **Privacy shield:** when app enters task switcher, cover content (lifecycle observer swaps in
   a plain token-background overlay; on Android additionally `FLAG_SECURE` — session 18 finalizes
   policy; scaffold the overlay now).
4. Deep-link stash from session 06: locked arrival → unlock → land on the target.

## Task C — Auth wiring

1. Router redirect guard (session 06's `go_router` + auth bloc): no tokens → sign-in; tokens +
   lock enrolled → lock page first. No flash of protected content (native splash holds until the
   first route decision is made).
2. `authExpired` (refresh dead / device revoked): clear state → sign-in screen with a calm
   notice: "تم تسجيل الخروج من هذا الجهاز" — informative, not alarming.
3. Sign-out (More → sign out): call logout endpoint, wipe secure storage + drift cache, reset
   blocs, land on sign-in.

## Task D — Devices screen (`pages/more/devices_page.dart`)

ListRows: device name, platform icon (own set), "آخر ظهور" relative time, current-device chip.
Swipe/row action → revoke (confirm AppDialog) → optimistic in-place removal (`flutter-lessons`
issue 5) + undo-less (revocation is serious; no undo — wording says so). This same data appears
on web later; endpoint already serves both.

---

## Smoke Test

- [ ] Full journey on device, Arabic first: sign in → biometric offer → enable → background 2 min
      → reopen → Face ID/fingerprint prompt → unlocked to the same screen
- [ ] Wrong password → blame-free translated error; airplane mode → offline state, no crash
- [ ] Task switcher: app preview is the shield, not ledger data
- [ ] Second device (or reinstall) → both appear in devices screen → revoke the other → it lands
      on sign-in with the calm notice within one request cycle
- [ ] Deep link while locked → unlock → correct record stub
- [ ] No-biometric-hardware emulator → app never dead-ends (lock skipped or PIN fallback)
- [ ] analyze + test + parity green; PARITY.md auth rows flipped

## Risks

- Biometric API differences (Android class 2 vs 3 sensors) → rely on `local_auth`'s available-
  biometrics query; when only weak biometrics exist, still allow but note for session 18.
- Lock-state races with deep links/notifications → the stash-then-unlock order is the invariant;
  test it.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_08_DASHBOARD_AND_REPORTS.md
Phase 1 complete — natural merge checkpoint.
```
