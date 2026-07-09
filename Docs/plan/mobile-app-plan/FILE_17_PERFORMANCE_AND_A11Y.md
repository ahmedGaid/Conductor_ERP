# SESSION 17 — Performance & Accessibility
# Files: surgical edits across apps/mobile (measured, not guessed), apps/mobile/PERF.md (new)

**Objective:** make "instant, calm, premium" measurable and true on the devices Egyptian SMBs
actually carry — including a ~150 USD Android. Then make the app usable by everyone: VoiceOver/
TalkBack in Arabic, dynamic type, contrast, reduced motion. Nothing here is a rewrite; it is a
measurement pass with surgical fixes and budgets written down so regressions are visible.

**Budgets (record in `PERF.md`, verified this session and re-verified in 21):**
cold start → interactive dashboard ≤ 2.5 s on the low-end Android reference device (≤ 1.5 s on a
current iPhone); list scroll 60 fps sustained on 1000-row cached lists; navigation transition
start < 100 ms after tap; APK/IPA size noted with a stated ceiling; zero dropped-frame warnings
in dev overlay on the six busiest screens.

---

## Before You Start

1. Acquire/emulate the low-end Android reference (define the exact model in PERF.md).
2. Read current Expo/RN profiling guidance (release-mode profiling only — dev mode lies).
3. List the six busiest screens from usage logic: dashboard, invoice list, invoice create,
   approvals inbox, assistant conversation, item list.

"Do not write anything yet."

---

## Task A — Measure, then fix startup

1. Measure release-build cold start on both reference devices; break down: JS bundle load →
   first render → auth/hydration → dashboard data. Record baseline in PERF.md.
2. Standard fixes AS MEASUREMENT DICTATES (not speculatively): Hermes confirmed on; deferred
   requires/lazy route loading for heavy screens (assistant markdown, scanner, report table);
   SecureStore/SQLite reads parallelized in the boot path; splash → skeleton dashboard
   immediately (cached render is the whole point of session 04 — verify it actually renders
   pre-network).

## Task B — Lists & memory

1. FlashList audit on the six screens: stable `keyExtractor`, `getItemType` for mixed rows,
   memoized row components, no anonymous closures in renderItem, image thumbnails sized (never
   full-res decode into a 56 dp row). Fix violations.
2. Memory: attachment viewer and scanner release on unmount (profile a 10-minute
   scan-and-browse session; heap must plateau); SQLite cache eviction (session 04) verified
   against its caps.
3. Re-render hygiene: React DevTools highlight pass on the six screens; context providers split
   if theme/auth/i18n churn re-renders the world (fix = split providers/selector hooks — a
   session-02/05 refactor if needed, small and contained).

## Task C — Accessibility

1. Screen readers: TalkBack + VoiceOver pass over the golden path (sign-in → dashboard → approve
   → invoice create → assistant). Every Pressable gets `accessibilityRole` + Arabic
   `accessibilityLabel` (labels are i18n keys — parity checker covers them); money values read
   as amounts, not digit soup (format the label string); StatusChips announce the WORD (colour
   was never the only carrier — brand rule pays off here); ScanSheet announces state changes.
2. Dynamic type: OS font scale 130% and 200% — layouts reflow (no clipped Arabic ascenders, no
   fixed-height rows that truncate), critical screens remain operable at 200%.
3. Contrast: audit token pairs used on mobile against WCAG AA (the tokens came from web so this
   should pass — VERIFY, especially dark-mode secondary text; any failure is a tokens.css
   conversation, not a mobile fork).
4. Reduced motion: full sweep — every animation consults `useReducedMotion` (grep for animation
   entry points; the session-05 rule audited app-wide).
5. Keyboard (iPad): tab order sane on FormScreens; cmd-K search; esc closes Sheets.

---

## Smoke Test

- [ ] PERF.md exists: device definitions, baseline vs. after numbers, all budgets met (or a
      written, justified exception per miss)
- [ ] Low-end Android release build: cold start ≤ 2.5 s to interactive cached dashboard;
      1000-row invoice list scrolls without visible jank
- [ ] TalkBack, Arabic: complete an approval end-to-end eyes-closed (screen curtain on)
- [ ] VoiceOver: same flow on iOS
- [ ] 200% font scale: sign-in, dashboard, invoice create, approvals all operable
- [ ] Reduced motion: zero animated transitions anywhere (spot-check 6 screens)
- [ ] tsc + parity green; no behaviour regressions on the phase-2/3 smoke highlights (quick
      re-run of session 09 + 10 golden paths)

## Risks

- Fixing perf by feel instead of measurement → the baseline-first structure of Task A/B is the
  guardrail; every fix cites its measurement in the commit message.
- Arabic screen-reader quality varies by OS → test on real devices, note OS-level gaps honestly
  in PERF.md (what we fixed vs. what the platform can't do).

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_18_SECURITY_HARDENING.md
```
