# SESSION 17 — Performance & Accessibility
# Files: surgical edits across apps/mobile (measured, not guessed), apps/mobile/PERF.md (new)

**Objective:** make "instant, calm, premium" measurable and true on the devices Egyptian SMBs
actually carry — including a ~150 USD Android. Then make the app usable by everyone: VoiceOver/
TalkBack in Arabic, dynamic type, contrast, reduced motion. Nothing here is a rewrite; it is a
measurement pass with surgical fixes and budgets written down so regressions are visible.

**Budgets (record in `PERF.md`, verified this session and re-verified in 21):**
cold start → interactive cached dashboard ≤ 2.5 s on the low-end Android reference device
(≤ 1.5 s on a current iPhone); **99th-percentile frame time ≤ 16 ms** (zero visible jank) on the
six busiest screens, measured in profile mode via DevTools timeline; list scroll smooth on
1000-row cached lists; navigation transition start < 100 ms after tap; APK (split-per-abi) and
IPA sizes noted with a stated ceiling.

---

## Before You Start

1. Acquire/emulate the low-end Android reference (define the exact model in PERF.md).
2. Read current Flutter profiling guidance (**profile/release mode only — debug mode lies**):
   DevTools timeline, `PerformanceOverlay`, `SchedulerBinding.addTimingsCallback` for frame
   stats.
3. Confirm Impeller is the active renderer on both platforms for the pinned SDK; note any
   platform still on Skia.
4. List the six busiest screens from usage logic: dashboard, invoice list, invoice create,
   approvals inbox, assistant conversation, item list.

"Do not write anything yet."

---

## Task A — Measure, then fix startup

1. Measure release-build cold start on both reference devices; break down: engine/runtime init →
   first frame → auth/hydration → cached dashboard render. Record baseline in PERF.md.
2. Standard fixes AS MEASUREMENT DICTATES (not speculatively): drift/secure-storage reads
   parallelized in the boot path (one `Future.wait`); native splash hands off to the cached
   skeleton dashboard immediately (cached render is the whole point of session 04 — verify it
   actually renders pre-network); defer heavy construction (scanner, report table, assistant
   markdown) to first use; check for accidental synchronous asset/JSON work on the UI isolate —
   move heavy parsing to `compute()` only if measurement shows it matters.

## Task B — Frames, lists & memory

1. Frame audit on the six screens (DevTools timeline, profile mode): hunt oversized rebuilds
   (missing `const` constructors — the lint enforces most; `buildWhen` gaps re-checked), missing
   `RepaintBoundary` around independently-animating regions (streaming bubbles!), shader-compile
   jank (Impeller should remove it — verify on the low-end device; if any first-run stutter
   remains, note it honestly in PERF.md).
2. List audit: `ListView.builder` everywhere (no unbuilt `Column` of hundreds), `prototypeItem`/
   `itemExtent` where rows are uniform, memoized row widgets, image thumbnails sized with
   `cacheWidth`/`cacheHeight` (never full-res decode into a 56 dp row).
3. Memory: attachment viewer and scanner release on close (profile a 10-minute scan-and-browse
   session in DevTools memory view; heap must plateau — scanner controller disposal from session
   11 verified); drift cache eviction (session 04) verified against its caps.

## Task C — Accessibility

1. Screen readers: TalkBack + VoiceOver pass over the golden path (sign-in → dashboard → approve
   → invoice create → assistant). Every tappable gets a `Semantics` label in Arabic (labels are
   i18n keys — parity checker covers them); money values read as amounts, not digit soup
   (`Semantics.label` carries the formatted string); StatusChips announce the WORD (colour was
   never the only carrier — brand rule pays off here); ScanSheet announces state changes
   (`SemanticsService.announce`).
2. Dynamic type: OS font scale 130% and 200% (`MediaQuery.textScaler` honoured — no
   `textScaleFactor: 1` overrides anywhere) — layouts reflow (no clipped Arabic ascenders, no
   fixed-height rows that truncate), critical screens remain operable at 200%.
3. Contrast: audit token pairs used on mobile against WCAG AA (the tokens came from web so this
   should pass — VERIFY, especially dark-mode secondary text; any failure is a tokens.css
   conversation, not a mobile fork).
4. Reduced motion: full sweep — every animation consults the session-05 `reducedMotion(context)`
   helper (grep animation entry points; the rule audited app-wide).
5. Keyboard (iPad): tab order sane on FormScreens (`FocusTraversalGroup`); cmd-K search; esc
   closes Sheets.

---

## Smoke Test

- [ ] PERF.md exists: device definitions, baseline vs. after numbers, all budgets met (or a
      written, justified exception per miss)
- [ ] Low-end Android release build: cold start ≤ 2.5 s to interactive cached dashboard;
      1000-row invoice list scrolls without visible jank; p99 frame ≤ 16 ms on the six screens
- [ ] TalkBack, Arabic: complete an approval end-to-end eyes-closed (screen curtain on)
- [ ] VoiceOver: same flow on iOS
- [ ] 200% font scale: sign-in, dashboard, invoice create, approvals all operable
- [ ] Reduced motion: zero animated transitions anywhere (spot-check 6 screens)
- [ ] analyze + test + goldens + parity green; no behaviour regressions on the phase-2/3 smoke
      highlights (quick re-run of session 09 + 10 golden paths)

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
