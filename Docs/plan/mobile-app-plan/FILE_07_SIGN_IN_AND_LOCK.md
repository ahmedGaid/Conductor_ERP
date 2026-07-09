# SESSION 7 — Sign-in & Biometric Lock
# Files: apps/mobile/app/(auth)/sign-in.tsx, apps/mobile/src/auth/** (new),
#        apps/mobile/app/(tabs)/more/devices.tsx, locales (mobile.auth.* keys)

**Objective:** the front door — a calm, on-brand sign-in screen, secure credential handling, and
an app lock: Face ID / Touch ID / Android biometrics (device-PIN fallback) required on cold start
and after backgrounding. Plus the "manage devices" screen (remote logout from session 03) so
users see and control every signed-in phone.

**Security model recap:** tokens in SecureStore (session 04); biometrics gate ACCESS to the app,
they never replace server auth. Server can kill any device at any time (revocation → `authExpired`
→ this session's sign-out path).

---

## Before You Start

1. Open web's login page → mirror copy tone, field order, error wording (same i18n keys where
   they exist).
2. Open `src/api/endpoints/auth.ts` + the `authExpired` event from session 04.
3. Read `expo-local-authentication` docs: `hasHardwareAsync`, `supportedAuthenticationTypesAsync`,
   `authenticateAsync` options (disable device-credential fallback? NO — allow it; a user with
   gloves still needs in).
4. Open session 03's device endpoints for the devices screen contract.

"Do not write anything yet."

---

## Task A — Sign-in screen

1. Layout: wordmark (monochrome, from assets — export per Identity System, never the coloured
   logo), company-server field IF the product supports self-hosted servers (check how web/dev
   handles base URLs — for now a build-config base URL + hidden dev override via 7 taps on the
   wordmark), username/email + password, one primary button.
2. States: designed loading (button spinner, fields disabled), blame-free errors from `ApiError`
   keys ("كلمة المرور غير صحيحة — جرّب مرة أخرى" tone; exact copy through the conductor-brand
   lexicon), offline state ("لا يوجد اتصال" pill + retry).
3. On success: store tokens, register device name (`Device.deviceName` via expo-constants/device
   — check API), navigate to tabs, THEN offer biometric enrolment in a Sheet: "افتح كوندكتور
   ببصمتك" — enable/later. Never force it.

## Task B — App lock (`src/auth/lock.ts`, `src/auth/LockScreen.tsx`)

1. State machine: `unlocked` → (background > 60 s OR cold start, when biometrics enrolled) →
   `locked` → biometric prompt → `unlocked`. Grace period constant in one place; later a setting.
2. `LockScreen`: full-screen, wordmark + one "unlock" button (auto-triggers prompt on mount;
   button is the retry). Fallback path after repeated failure: sign out (with confirm Dialog —
   destructive, so haptic + explicit wording).
3. **Privacy shield:** when app enters task switcher, cover content (RN `AppState` +  a plain
   token-background overlay; on Android additionally `FLAG_SECURE` — session 18 finalizes policy;
   scaffold the overlay now).
4. Deep-link stash from session 06: locked arrival → unlock → land on the target.

## Task C — Auth wiring

1. `(auth)` group guard in `app/_layout.tsx`: no tokens → sign-in; tokens + lock enrolled → lock
   screen first. No flash of protected content (splash holds until decision made).
2. `authExpired` (refresh dead / device revoked): clear state → sign-in screen with a calm
   notice: "تم تسجيل الخروج من هذا الجهاز" — informative, not alarming.
3. Sign-out (More → sign out): call logout endpoint, wipe SecureStore + SQLite cache + i18n-safe
   restart to sign-in.

## Task D — Devices screen (`more/devices.tsx`)

ListRows: device name, platform icon (own set), "آخر ظهور" relative time, current-device chip.
Swipe/row action → revoke (confirm Dialog) → optimistic removal + undo-less (revocation is
serious; no undo — wording says so). This same data appears on web later; endpoint already
serves both.

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
- [ ] tsc + parity green; PARITY.md auth rows flipped

## Risks

- Biometric API differences (Android class 2 vs 3 sensors) → rely on expo-local-authentication's
  security-level query; when only weak biometrics exist, still allow but note for session 18.
- Lock-state races with deep links/notifications → the stash-then-unlock order is the invariant;
  test it.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_08_DASHBOARD_AND_REPORTS.md
Phase 1 complete — natural merge checkpoint.
```
