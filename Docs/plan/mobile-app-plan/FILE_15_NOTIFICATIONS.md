# SESSION 15 — Push Notifications & Deep Links
# Files: erp/notifications/** (additive), apps/mobile/lib/core/notifications/** (new),
#        apps/mobile/lib/presentation/pages/inbox/notifications_page.dart (new)

**Objective:** the ERP taps you on the shoulder — approvals waiting, mentions, assignments,
workflow updates, AI results — as native push that deep-links straight into the exact record,
respecting permissions and language. Plus the in-app notification inbox mirroring web's
(`erp/notifications` is the source; the linear-polish plan has an inbox session — READ what
shipped). Push is a delivery channel for the EXISTING notification system, not a second system.

---

## Before You Start

1. Open `erp/notifications/` (models, services, API) → what creates notifications today, their
   types, how web lists/marks-read. The mobile inbox and push both hang off THIS.
2. Session 03's `push_token` field + registration endpoint — the delivery address book.
3. Read current `firebase_messaging` docs: FCM token lifecycle (`onTokenRefresh`), Android
   channels, iOS APNs setup (key upload in the Firebase console + entitlements), foreground vs
   background vs terminated handlers. Backend sends via **FCM HTTP v1 API** (service-account
   JSON on the Django side — stored as a secret, never committed). DECISIONS recap (entry
   written in session 01): Firebase for messaging transport ONLY; payloads MINIMAL — type +
   record ref + localized title, never amounts or customer names in the push body beyond what
   the notification type template says. Re-read that payload-privacy rule before writing Task A.
4. Session 06's `parseLink` — pushes carry `conductor://` targets.

"Do not write anything yet."

---

## Task A — Backend fan-out (`erp/notifications/`, additive)

1. `services/push.py`: `send_push(notification)` — look up the user's live (non-revoked) devices
   with push tokens → build per-language payload (user's language preference; ar default) →
   POST to FCM HTTP v1 (batched; handle `UNREGISTERED`/`INVALID_ARGUMENT` responses by clearing
   the dead token). Called from wherever notifications are created today (find the single choke
   point — there should be one service; if creation is scattered, add the hook at the
   model/service layer, not per-caller). New backend dependency for FCM auth (`google-auth` or
   plain JWT signing) = a one-line DECISIONS entry — check what the repo already has first.
2. Per-type opt-outs: a small `NotificationPreference` model (user × type × channel) IF web
   doesn't already have one — READ first. Mobile settings screen gets the toggles; web can adopt
   later.
3. Badge count: unread count in each push payload (`apns` badge field; Android badge via
   channel/launcher support) so the app icon stays honest.
4. Tests: fan-out to 2 devices, language split, revoked device skipped, dead-token cleanup,
   payload contains ref + keys but no forbidden fields.

## Task B — Client (`lib/core/notifications/`)

1. Registration: after login/biometric-enrol (session 07 hook point), ask with a designed
   pre-prompt (value first: "عشان توصلك الموافقات أول بأول") → OS permission
   (`FirebaseMessaging.requestPermission`) → FCM token (+ `onTokenRefresh` re-registration) →
   session 03 endpoint. Declines respected forever; re-ask only from settings.
2. Android channels: one per notification family (approvals / mentions / workflow / AI) with
   Arabic names — this is what makes OS-level per-type control feel native.
3. Handlers: foreground push (`FirebaseMessaging.onMessage`) → quiet in-app AppToast (never a
   modal); tap from background/terminated (`onMessageOpenedApp` / `getInitialMessage`) →
   `parseLink` → navigate (through the session 07 lock, stash-then-unlock). Badge sync on open;
   mark-read propagates to server (same endpoint web uses).
4. Inbox screen (`inbox/notifications_page.dart`): the web inbox mirrored — grouped list, unread
   emphasis, mark-all-read, each row deep-links. The inbox tab badge = approvals + unread count
   (session 10's badge merges here; semantics stated explicitly, `flutter-lessons` issue 9).

---

## Smoke Test

- [ ] Web action (submit PO for approval) → phone buzzes within seconds → notification in Arabic
      → tap from KILLED app → biometric unlock → lands on THAT approval detail
- [ ] Approve there → web reflects it; badge count drops on the app icon
- [ ] Foreground push → quiet toast, no interruption of typing
- [ ] Language preference en → push arrives in English; switch back → Arabic
- [ ] Revoke device from web → push to it stops (FCM response logged, token cleared); re-login →
      resumes
- [ ] Type toggle off (approvals) in mobile settings → that push stops, others continue; inbox
      still shows the notification (channel ≠ existence)
- [ ] Inbox parity with web: same items, same read states after mark-read on either side
- [ ] `pytest erp/notifications` green; analyze + test + parity green; PARITY.md notification
      rows flipped

## Risks

- iOS push setup (APNs key in Firebase console + entitlements + a real device — simulators don't
  receive APNs) is pure ceremony but blocks everything → do the credentials setup FIRST in the
  session, let it bake while building Task A.
- Notification storms (bulk workflow events) → batch/collapse at the fan-out layer (FCM
  `collapse_key`/tag per record) — one record, one visible notification.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_16_OFFLINE_WRITES.md
```
