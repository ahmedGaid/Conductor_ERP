# Product

## Register

product

## Users

Staff at Egyptian small/medium businesses running day-to-day operations: accountants and
bookkeepers, branch managers, sales and purchasing clerks, warehouse staff, and support/CRM users.
They are **Arabic-first** and work in long, focused sessions — data entry, posting, reconciliation,
reporting — mostly at a desk, but increasingly also on phones/tablets in the field. They are
domain-competent but **not technical**; the software must teach itself and never get in the way.

## Product Purpose

**Conductor** is a customer-hosted, single-tenant ERP (Accounting, Inventory, Sales, Purchasing, CRM,
e-invoicing, workflows). It replaces spreadsheets and aging legacy ERPs with one calm, modern,
Arabic/RTL-first system that keeps the books correct by construction (double-entry, stock = GL,
balanced trial balance) while staying approachable. Success = a new user completes real work
(post an entry, invoice an order, reconcile a bank statement) **without external documentation or
training**, and trusts the numbers.

## Brand Personality

Calm, fast, invisible. Three words: **quiet, precise, trustworthy.** The tool should feel like Linear
/ Uber / Telegram — near-black, minimal chrome, generous space, instant response — not like finance
software shouting at you. Voice is plain and reassuring; it explains, never lectures. Colour is used
sparingly and always *means* something (status, links, key figures), never decoration.

## Anti-references

- **Old-style legacy ERP** (SAP/Oracle-era): cramped grey forms, tiny fields, every control on one
  dense screen, modal-on-modal. The thing we are explicitly replacing.
- **Over-coloured dashboards**: flashy multi-accent palettes, gradient/“hero-metric” cards, colour as
  decoration. (An indigo brand-recolour was tried and rejected — the near-black chrome stays.)
- Consumer-app playfulness (bouncy motion, emoji, illustration-heavy) — too casual for finance.
- Cream/beige “editorial SaaS” — the warm off-white + big-serif generic AI default.

## Design Principles

1. **The tool disappears into the task.** Speed and clarity over decoration; never make the user wait
   for choreography or hunt for the next action.
2. **Bilingual by birth, not translation.** Arabic/RTL is the default reality; every screen reads
   naturally right-to-left first, English is the mirror. Logical CSS only.
3. **Show what's needed now; tuck the rest away.** Progressive disclosure keeps dense ERP data
   approachable without dumbing it down — primary action and key figures first, detail on demand.
4. **Colour carries meaning.** Near-black chrome is fixed; colour appears only for status, links, and
   key figures. No decorative accents, no full-saturation on inactive states.
5. **Earned familiarity.** Standard affordances done cleanly — same button, same form control, same
   status vocabulary everywhere. Trust comes from consistency, not novelty.

## Accessibility & Inclusion

- **WCAG AA**: body text ≥ 4.5:1, large/bold ≥ 3:1; status is never colour-only (always a label too).
- **Full RTL/LTR parity**: logical properties only; AR and EN strings kept at key-parity (gate-enforced).
- **Keyboard-first**: one visible focus ring discipline app-wide; all actions reachable without a mouse.
- **Reduced motion**: every transition has a `prefers-reduced-motion` fallback (already enforced).
- **Mixed devices**: responsive behaviour is structural (collapsing nav, responsive tables), not fluid
  type — readable and operable on phone, tablet, and desktop.
