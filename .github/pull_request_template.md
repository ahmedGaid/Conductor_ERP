<!--
  Conductor PR. Keep it short. UI/UX PRs must pass the Conductor Quality Review below.
  Back-end / infra / docs-only PRs: strike the Quality Review, keep the Gates that apply.
  Philosophy front door: Docs/Brand/Conductor_Product_Philosophy.md
-->

## What & why
<!-- One or two lines: what this changes and the outcome for the user. -->

## Conductor Quality Review
Every user-facing change passes **The Conductor Standard** — the 8-point ship test
(Directive → "The Conductor Standard"). Tick each, or say why it is N/A. Fail one = not done.

- [ ] **1. Invisible complexity** — depth hidden behind a simple interaction (hide, never omit)
- [ ] **2. Instant performance** — feels immediate; saving is invisible; no needless spinner
- [ ] **3. Calm by default** — monochrome chrome; colour only inside the work, paired with a word/icon
- [ ] **4. Trust through transparency** — says what happens *before*, reassures *after*; reversible
- [ ] **5. Consistency everywhere** — the same action behaves the same on every screen
- [ ] **6. Human AI** — agentic bits notice/explain/protect, drafts-only + gated (Brief §12) — N/A if none
- [ ] **7. Craft in every detail** — type, spacing, motion, language, and errors feel designed
- [ ] **8. Business confidence** — the user leaves more informed and more in control
- [ ] Ran the `conductor-brand` **brand-feel checklist** (the judgment a gate cannot see)

**Why is this *more premium* than before?**
<!-- One line. Premium = confidence, simplicity, silence — never flash (Brief §2; Directive §5).
     If it does not make the product calmer, clearer, or more trustworthy, it is not an upgrade. -->

## Gates (frontend)
- [ ] `node scripts/check-i18n-parity.mjs` — ar/en parity (build-blocking)
- [ ] `npx tsc -b` — types clean
- [ ] `python scripts/gates/gate03.py` — mechanical brand gate (tokens / logical-CSS / i18n / build)

<!-- Green gates AND passed brand-feel checklist = actually done. A green gate alone only means
     "not mechanically off-brand," never "on-brand." -->
