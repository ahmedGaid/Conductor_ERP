# Conductor — Visual Identity System

> Status: **active identity system.** This is the third pillar of Conductor's brand, alongside the
> [Brand & Marketing Brief](Conductor_Brand_Marketing_Brief.md) (*what we say*) and the
> [Product Design & Engineering Directive](Conductor_ERP_Product_Design_Engineering_Directive.md)
> (*how the product looks and behaves*). This file is the **identity layer**: the concrete assets and
> rules — logo, type, colour values, icon language, the Arabic lexicon, motion character, and the
> off-app surfaces (invoice / email / web / OG) — that make the brand *physically consistent
> everywhere a customer touches it.*
>
> Precedence: for any **in-app pixel, token, motion, accessibility, or i18n rule**, the **Directive
> wins** — this file never overrides it; it points to the live tokens in
> [`src/styles/tokens.css`](../../apps/web/src/styles/tokens.css). For **narrative / voice / claims**,
> the **Brief wins**. This file owns only what neither of those does: the *identity assets and the
> surfaces beyond the app shell.*
>
> Scope: *the marks, the lexicon, and the touchpoints.* When this file and the live tokens disagree,
> **the tokens are the truth** — fix this doc, not the code.

---

## 1. Identity in one paragraph

Conductor's identity is **monochrome confidence with one quiet voice of colour.** A near-black (or, in
dark mode, near-white) brand carries all the chrome and the logo; colour appears only *inside* the
work — links, deltas, status — never decorating the frame. The type is calm and bilingual by
construction. The icons are one hand, single-stroke. Nothing is loud, because trust is the first
value and loud reads as cheap. The whole system says the same thing the product does: *quiet,
precise, trustworthy.*

---

## 2. Logo & wordmark

The name **carries the strategy** (a conductor brings many parts into one harmony — see Brief §3), so
the identity is **wordmark-first**, not symbol-first.

### 2.1 Wordmark
- **"Conductor"** set in **IBM Plex Sans Arabic / Inter, weight 700 (Bold)**, in the brand colour
  (`--color-brand`). No custom letterforms, no italic, no tracking tricks — the identity is the
  *restraint*, not a logotype flourish.
- Arabic lockup: **«كوندكتور»** set in IBM Plex Sans Arabic 700, same colour. The Arabic wordmark is a
  **first-class equal**, never a subordinate translation under the Latin one.
- The wordmark always renders in a **single colour** that resolves from the theme: near-black on
  light, near-white on dark. It is *never* placed on the blue accent or any status colour.

### 2.2 The mark (monogram)
- A single **"C"** or a minimal **baton/upbeat stroke** mark, single-weight stroke to match the icon
  language (§5), drawn on the same 24×24 geometry. Used only where the full wordmark won't fit:
  favicon, app icon, avatar fallback, collapsed sidebar, OG corner.
- The mark inherits `currentColor` — one colour, theme-resolved — exactly like the nav icons. It is
  never multi-colour and never gradient.

### 2.3 Clear space & minimum size
- **Clear space** around the wordmark = the cap-height of the "C" on all sides. Nothing intrudes.
- **Minimum sizes:** wordmark ≥ 96px wide on screen; mark ≥ 16px (favicon) / 1024px master for app
  stores. Below wordmark minimum, switch to the mark.

### 2.4 Logo refusals (hard no)
- ❌ No gradient, bevel, glow, or drop shadow on the logo.
- ❌ No placing the logo on a busy photo or on the accent/status colours.
- ❌ No stretching, rotating, recolouring to a brand-foreign hue, or outlining.
- ❌ No emoji, mascot, or illustrative treatment (Brief §15 — never consumer-playful).
- ✅ The only sanctioned variants are: **light wordmark / dark wordmark / mark**, each single-colour.

---

## 3. Colour identity

Colour values are **not redefined here** — they live in
[`tokens.css`](../../apps/web/src/styles/tokens.css) and the gate enforces that nothing else holds
raw hex. This section records the *identity meaning* of each, so off-app surfaces (which don't import
the tokens) reproduce them faithfully.

### 3.1 Brand & neutrals (the chrome)
| Role | Light | Dark | Identity meaning |
|---|---|---|---|
| **Brand** (`--color-brand`) | `#111827` | `#f5f5f5` | The logo, primary buttons, focus. The "voice." |
| Brand strong | `#0a0f1a` | `#ffffff` | Pressed / max-contrast. |
| Canvas (`--color-bg`) | `#f9fafb` | `#000000` | The page. Dark mode is **true black** (Uber-style), neutral grey — no blue cast. |
| Surface | `#ffffff` | `#0d0d0d` | Cards, sheets. |
| Text | `#111827` | `#f5f5f5` | Primary reading colour. |
| Border | `#e5e7eb` | `#262626` | Thin dividers do the grouping, not boxes. |

### 3.2 The one accent (in-page only)
- **Accent = blue** `#2563eb` light / `#60a5fa` dark (`--color-accent`). It appears on **links and
  accent text inside a page** — **never on the app chrome.** This is the single most-violated rule in
  ERP UIs and the one that keeps Conductor from looking like a dashboard toy.
- Users may re-pick the accent (green/purple/orange/red/black presets). The accent family is the
  **only** thing personalization touches — the near-black chrome never changes (see DECISIONS).

### 3.3 Semantic colour (meaning, never decoration)
Success `#16a34a` · Warning `#d97706` · Danger `#dc2626` · Info `#0891b2`, each with a `-strong` text
and `-subtle` fill, plus the full status-pill map (pending / running / waiting / failed / completed).
**Rule:** colour never communicates alone — always paired with a word or icon (Directive §4).

### 3.4 Colour refusals
- ❌ No multi-accent palettes, decorative gradients, or "dashboard-flashy" recolours (Brief §15; an
  indigo recolour was tried and rejected — DECISIONS).
- ❌ No colour in the chrome. The frame is monochrome; colour lives *in the work.*

---

## 4. Typography

The product ships **IBM Plex Sans Arabic** (Arabic, primary) + **Inter** (Latin), at weights
**400 / 500 / 700** — already wired in [`main.tsx`](../../apps/web/src/main.tsx) and bundled offline
(no CDN — customer-hosted rule). This is the identity typeface for **every** surface, on and off app.

### 4.1 The pairing (and why)
- **IBM Plex Sans Arabic leads.** Arabic is the default reality, so the Arabic face is chosen first
  and Inter is selected to *match its rhythm*, not the reverse. Both are humanist, neutral, and read
  calmly over long workdays — they share the "quiet, precise" personality.
- `--font-ui` = Arabic, then Latin: Arabic glyphs render in Plex Arabic, Latin/numerals in Inter,
  automatically, in either direction.
- **Numbers:** `font-variant-numeric: tabular-nums` everywhere figures appear, so money columns align.
  Latin numerals via `--font-latin` even inside Arabic text (wrap LTR tokens in `<Bdi>`).

### 4.2 The scale (from tokens — do not invent sizes)
`xs .75 / sm .875 / md 1 / lg 1.1875 / xl 1.5 / 2xl 1.875` rem · line-height-ui `1.5` · weights
regular 400 / medium 500 / semibold 600 / bold 700. Headings use weight + size, **never** colour, to
establish hierarchy.

### 4.3 Type refusals
- ❌ No third typeface, no display/script faces, no all-caps for Arabic (Arabic has no case — never
  fake it), no condensed tracking.
- ❌ No CDN-loaded fonts on any surface — always the bundled families.
- ✅ Marketing site, invoice PDFs, emails, decks, OG images: **same two families.** A surface in a
  different font is off-brand on sight.

---

## 5. Iconography

**Decision recorded (closes the Directive's open "single icon library" backlog item):** Conductor
uses its **own hand-built single-stroke icon set** — see
[`src/app/icons.tsx`](../../apps/web/src/app/icons.tsx) — **not** an imported library. This is the
correct call and is now the standard:

- **Geometry:** 24×24 view box, `currentColor` **stroke** (not fill), rounded caps & joins, one
  consistent stroke weight. Icons inherit colour from their context (muted → text on hover/active).
- **Why own them:** a curated set reads as *one calm hand* rather than a row of mismatched glyphs;
  it's bundled offline by construction; and it stays on-brand without a third-party's stylistic drift.
- **Direction-agnostic:** no left/right baked into a path — every icon works in RTL and LTR unchanged.
  Directional glyphs (next/prev, indent) flip via transform, never a hardcoded side.
- **Adding an icon:** match the existing 24×24 / stroke / rounded recipe in `icons.tsx`. If you must
  reference Lucide/Tabler for a shape, **redraw it to the recipe** — never paste a foreign-weight path.

### Icon refusals
- ❌ No filled, duotone, emoji, or multicolour icons. ❌ No mixing in a second library's glyphs.
  ❌ No icon carrying meaning by colour alone.

---

## 6. The Arabic lexicon — *the moat*

This is Conductor's single biggest differentiator and was the least-specified part of the brand. A
**genuinely native** Arabic ERP — not a translated foreign one (Brief §8.4) — requires *one* canonical
Arabic term per concept, used identically on every screen, invoice, email, and in support. Drift here
is what makes localized products feel foreign.

> **Governance:** this table is the source of truth for Arabic product terminology. New domain terms
> are added here **before** they ship. In-app, the term still lives as an i18n key with ar/en parity
> (gate03) — this table decides *what the Arabic value is.* Egyptian business usage wins over textbook
> MSA where they differ.

### 6.0 Display orthography vs. search folding
Conductor's Arabic **display text uses full, correct orthography** — hamzas, ة, and the proper yaa
form (أمر، فاتورة، مؤسسة). We do **not** simplify what the user reads.

What we *do* simplify is **search**, so a user can type loosely and still find things.
[`lib/arabicSearch.ts`](../../apps/web/src/lib/arabicSearch.ts) folds **both** the query and the
candidate text — أإآ→ا, ؤ→و, ئ/ي→ى, ة→ه, and strips tashkeel / tatweel / bare ء — so either spelling
matches the other: typing "امر البيع" finds "أمر البيع"; "فاتوره" finds "فاتورة". Folding is
**match-only, never displayed**, and is wired into the command palette, the list filters
(`lib/filters.ts`), and user search. New text-search surfaces must use `normalizeSearch()` too.

### 6.1 Core domain terms (seed — extend as modules land)
| Concept (EN) | Canonical Arabic | Not (avoid drift) |
|---|---|---|
| Invoice | فاتورة | — |
| Sales order | أمر بيع | طلب بيع (reserve "طلب" for quotation/request) |
| Quotation | عرض سعر | تسعيرة |
| Purchase order | أمر شراء | — |
| Purchase request | طلب شراء | — |
| Customer | عميل | زبون |
| Supplier / Vendor | مورد | بائع |
| Inventory / Stock (on-hand quantity) | المخزون | — |
| Goods (physical, delivered/received) | البضاعة | — (a *distinct* concept from المخزون — both are correct) |
| Warehouse | مخزن | مستودع (dominant in-app **and** common Egyptian usage — **مخزن** is canonical) |
| Item / Product | صنف | منتج (UI lists of goods use **صنف**) |
| Account (GL) | حساب | — |
| Journal entry | قيد يومية | — |
| Trial balance | ميزان المراجعة | — |
| Ledger | دفتر الأستاذ | — |
| Payment | دفعة / سداد | — |
| Receivables | المبالغ المستحقة (لنا) | الذمم المدينة (too technical for the 80% user) |
| Approval / Approve | موافقة | اعتماد (unified to **موافقة** app-wide, 2026-06-23) |
| Draft | مسودة | — |
| Post (to ledger) | ترحيل | — |
| Reconcile (settle) | تسوية | — |
| Match (link transactions) | مطابقة | — (a *distinct* sub-action of reconcile — not drift) |
| e-invoice | فاتورة إلكترونية | — |
| Notes (free-text on a record) | ملاحظات | تعليقات (reserve for threaded comments, a different concept) |
| Opportunity | فرصة | — |

### 6.2 Status & action voice (Arabic)
Human-language statuses (Directive — "Waiting for Finance approval") must read as **natural Egyptian
business Arabic**, not enum transliteration:
- "بانتظار موافقة الإدارة المالية" — *not* "PENDING_APPROVAL_FIN".
- "تم — في انتظار السداد" · "مسودة" · "مُرحَّل".
- Errors **explain, never blame** (Brief §11): "حصل خطأ — حاول مرة أخرى" — never "خطأ ٥٠٠".

### 6.3 Lexicon refusals
- ❌ No mixing two Arabic words for one concept across screens. ❌ No left-to-right English term where
  a settled Arabic one exists. ❌ No literal word-for-word translation from the English string — write
  Arabic *as Arabic* (Brief §11). ✅ One concept, one word, everywhere.

---

## 7. Motion character

The Directive owns the motion *scale* (`--dur-fast` 120 / `--dur` 180 / `--dur-slow` 260, `--ease-out`).
This section names the *character* those numbers must express — so motion is recognizably Conductor,
not just "fast":

- **Confident, not bouncy.** `--ease-out` decelerates into place and stops — no overshoot, no spring,
  no elastic. Trust reads as *settled*, not playful (Brief §15 — never consumer-playful).
- **Enters by arriving, not announcing.** Surfaces fade + rise ≤2px and resolve to `transform: none`
  (GPU-only). Nothing slides a long distance or draws attention to its own animation.
- **Instant feedback is mandatory.** Every action has an immediate pressed/disabled/inline-result
  state. Motion confirms; it never gates (Directive §2).
- **Respect `prefers-reduced-motion`** — the `data-motion="reduced"` remap collapses durations to ~0.
  Motion is polish, never a barrier.
- **One feel, app-wide.** No bespoke per-component easing or duration. If it isn't on the scale, it
  doesn't ship.

---

## 8. Off-app surfaces — *where the brand actually meets customers*

The app shell is governed by the Directive. The brand also lives on surfaces the Directive never
mentions — and for an ERP, **the invoice is the most-seen brand artifact of all** (your customer's
customer sees it). Every surface below uses the **same wordmark, two typefaces, monochrome chrome,
and single accent.**

### 8.1 Invoice / document PDF (highest priority)
- Wordmark top-start; monochrome; tabular numerals; the *one* accent only for the total or a single
  rule. Arabic-first layout (RTL), with the Latin mirror available.
- Calm: thin borders, generous whitespace, no boxed grey forms (the very thing Conductor rejects).
- Required real content: legal entity, tax/e-invoice identifiers, correct-by-construction totals.
  The document *looks* like the product feels — that consistency is the brand.

### 8.2 Email (transactional + onboarding)
- Plain, human, bilingual; wordmark header; one accent for the single CTA; system-safe fallback to
  the bundled families. Voice = Brief §11 ("You're all set," not "Operation completed successfully").

### 8.3 Marketing site / landing
- Hero leads with a performance tagline (Brief §10) over the harmony signature; near-black chrome;
  the product's real screens as the imagery (the craft *is* the marketing). No stock "AI" art, no
  buzzwords (Brief §12).

### 8.4 OG / social cards & app icons
- Monochrome wordmark or the mark on canvas; one optional accent element; same type. OG image is a
  brand surface — it must look like Conductor at a glance, generated from a single template.

### 8.5 Decks / app-store listings
- Same families, same monochrome, real product screens. Start from the Brief for words, this file for
  the look.

---

## 9. Brand-feel review checklist (the "is this Conductor?" gate)

gate03 enforces the *mechanical* rules (tokens-only colour, logical-CSS, ar/en parity, clean build).
It **cannot** catch a screen that is token-clean yet still feels like "another ERP." Run this **human**
checklist on every new screen and every off-app surface — it checks the *promise*, not the syntax:

1. **One obvious thing.** Is there a single primary job and one primary action? (Directive §1)
2. **Chrome is monochrome.** Is colour *only* inside the work — never in the frame? (§3.2)
3. **Colour earns its place.** Does every colour pair with a word/icon and mean something? (§3.3)
4. **One voice of type.** Only the two families, the token scale, hierarchy by weight not colour? (§4)
5. **One hand of icons.** Single-stroke, `currentColor`, no foreign glyphs? (§5)
6. **Arabic is native.** Canonical lexicon terms, natural Egyptian phrasing, not translated English?
   Statuses human, errors blame-free? (§6)
7. **Motion is settled.** Fast, decelerating, no bounce, instant feedback, reduced-motion honoured? (§7)
8. **Designed states.** Is the empty/error/loading state *designed* (skeletons, guidance, one CTA),
   never a bare "No data" / blank / "Loading…"? (Directive §2, §5)
9. **Promise held.** Does this make the product *easier* to learn, or harder? If harder, it breaks the
   brand promise — redesign it. (Brief §5)
10. **Would Linear ship this?** The craft bar. If the honest answer is no, it isn't done. (Brief §2)

A screen that passes gate03 but fails this list is **not done.** Quality is correct-and-polished over
fast-and-rough (Brief §6, value 5).

---

## 10. How to use this file

- **A logo, the wordmark/mark, clear space, an app/favicon** → start here (§2).
- **The meaning of a colour on an off-app surface** → here (§3); the *value* → `tokens.css`.
- **Which typeface / size / weight, anywhere** → here (§4); in-app it resolves from the tokens.
- **An icon** → here (§5) + `icons.tsx`.
- **The Arabic word for a concept** → here (§6) — the source of truth; then add the i18n key.
- **Invoice / email / web / OG / deck design** → here (§8), with words from the Brief.
- **"Is this on-brand?"** → run §9.
- **Any in-app pixel/token/motion/a11y/i18n rule** → the **Directive** wins.
- **Any narrative / voice / claim** → the **Brief** wins.

---

## 11. Change log

- **2026-06-23 — Identity system created.** Established the third brand pillar (assets + surfaces)
  alongside the Brief (words) and Directive (in-app behaviour). Grounded every value in the live
  `tokens.css` and `icons.tsx` rather than inventing: confirmed **IBM Plex Sans Arabic + Inter**
  (400/500/700, bundled offline) as the identity type, near-black/near-white monochrome chrome with a
  single in-page blue accent, and the **own hand-built single-stroke icon set** — which **closes the
  Directive's open "single icon library" backlog item** (decision: own it, don't import). Added the
  wordmark/mark spec with clear-space and refusals, the **Arabic lexicon** (the moat — one canonical
  term per concept, governed here before it ships), the motion *character* (settled, no bounce) atop
  the Directive's motion *scale*, the off-app surface specs (invoice/email/web/OG — invoice flagged as
  the highest-priority brand artifact), and a **brand-feel review checklist** that checks the promise
  where gate03 can only check syntax. No code/token change — this file describes the existing system
  and the surfaces around it.
- **2026-06-26 — Lexicon §6.1 extended (CRM inline-edit).** Added **Notes → ملاحظات** (reserve
  تعليقات for threaded comments) and **Opportunity → فرصة** as canonical terms, governed here before
  shipping the opportunity detail inline-edit fields.
