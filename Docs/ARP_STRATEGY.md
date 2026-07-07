# ARP — Category Strategy & Team Charter

> Status: **active strategy reference — read at the start of every session that builds, plans,
> markets, or scopes Conductor.** This document owns the category definition, the build/remove
> scope discipline, and the team rules. Narrative/voice stays in the Brand Brief; in-app rules stay
> in the Directive; assets/lexicon stay in the Identity System; execution order lives in
> [`Docs/plan/arp-roadmap.md`](plan/arp-roadmap.md). Adopted 2026-07-02.

---

## 1. The category

**ARP — Agentic Resource Planning.** The successor category to ERP.

> **ERP was software you operate. ARP is software that operates with you.**

ERP records what happened and waits for a trained operator. ARP understands the business, executes
work through the same permissions and audit trail as any employee, plans before acting, asks before
writing, and returns the user to exactly where they left off. Conductor is **the first ARP** —
الأول من نوعه.

**Signature lines** (the standing category copy — don't improvise variants):
- EN: *ERP was software you operate. ARP is software that operates with you.*
- AR: **كوندكتور — أول نظام يدير معك، لا يُدار فقط.**
- Arabic category phrase (Identity System §6 governs): **الإدارة الذكية للموارد** — the acronym
  stays Latin **ARP** in both languages (like ERP before it). Never «تخطيط الموارد الوكيلي».

**Category ≠ brand.** ARP is deliberately brand-neutral so it can become an industry term (as
Gartner's "ERP" did) with Conductor holding the "first" position. We define it publicly by
demonstrating it, not by asserting it.

## 2. The claims gate (Brief §12 applies with full force)

**No public use of "ARP" — site, deck, ads, app store, YC application — until at least one
flagship agentic flow runs live for a real customer:** the PO detour-and-resume flow
(ai-workspace sessions 12–13) or the autonomous month-close (roadmap Phase B). Until then, ARP is
internal vocabulary. A category claim without a demo is exactly the hype the brand forbids.

When it goes public: update Brief §1/§13 wording from "adopted (internal)" to the public category
line, and log it in Brief §17.

## 3. What ARP requires of the product — the bar

Every feature must pass **the ARP test**: *does this let the system operate — understand, plan,
execute, verify, resume — or does it only display?* Display-only features need a reason to exist.

Non-negotiable mechanics (already DECISIONS-backed — restated here as the category's constitution):
1. **The AI is an actor, never a superuser.** Every tool/action runs as the current user; RBAC,
   data scope, and audit hold by construction. (DECISIONS "AI 2026-07".)
2. **Tool-use, never free-text-to-SQL.** The model chooses typed tools; it never composes queries.
3. **Writes are human-in-the-loop.** Propose → confirm → execute through the normal contract →
   `audit.record`. Drafts only; posting stays on module screens.
4. **The model narrates, it never computes.** Money formatted server-side; citations built from
   real records; every number verifiable by click.
5. **Blockers are actionable.** Never "X doesn't exist" — always issue + fastest permitted fix +
   guaranteed return to the paused step (ai-workspace sessions 12–13).
6. **Interruptions resume.** Any detour restores full context. "What were we doing?" is a bug.

## 4. Build — what earns a place (ranked; execution order in the roadmap)

| # | Capability | Why it makes Conductor unbeatable |
|---|---|---|
| 1 | **Autonomous month-close** | "Correct by construction" matures into **closed by construction**. The flagship ARP claim; no MENA incumbent has it. |
| 2 | **Migration agent** (Excel-chaos onboarding) | Kills ERP's #1 killer — implementation. "From spreadsheets to a running system in one afternoon." |
| 3 | **Proactive daily brief** | Push, not pull: cash, receivables, approvals, one anomaly — every morning. The AI that works while you sleep. |
| 4 | **Anomaly watch** | Duplicate invoices, price drift, odd discounts, broken sequences — trust (value #1) made visible to the owner. |
| 5 | **Bank statement reconciliation by photo/PDF** | Egyptian bank APIs barely exist; vision + auto-match into the existing recon module. |
| 6 | **WhatsApp interface** | Where Egyptian SMBs actually live: invoice photo → draft; Arabic voice note → answer; daily brief delivery. (New dependency — deliberate decision, not drift.) |
| 7 | **Accountant portal** (multi-company) | External accountants become the distribution channel. |
| 8 | **Cloud multi-tenant default** | Venture-scale distribution; self-hosted becomes the premium/enterprise option. |

Prerequisite for 1–7: the AI workspace (`Docs/plan/ai-workspace-plan/`, sessions 01–15) — the
agentic loop, safe actions, and detour/resume machinery everything above rides on.

## 5. Remove / refuse — what scope discipline means

1. **No HR, manufacturing, or projects modules** until the money loop (sales → inventory →
   accounting → VAT) is unbeatable and a paying customer base demands them. Half-modules are how
   "another ERP" happens (Brief §15).
2. **No settings sprawl.** Every new setting needs a reason a default couldn't serve. One way to
   do each thing. Configurability is Odoo's disease, not our feature.
3. **No dashboard theater.** No chart or KPI ships without a named decision it informs.
4. **"Customer-hosted" demoted from lead value prop to deployment option** (Brief §8.5 to be
   revised when cloud lands — roadmap Phase F). Recorded in DECISIONS.
5. **No feature-grid competition — ever.** We win on experience, onboarding speed, and the ARP
   test (Brief §13: *not more ERP — a new category*).

## 6. Team rules — الالتزام (binding for everyone: founders, engineers, designers, marketers, AI sessions)

1. **Read before you act.** UI/copy/identity → brand triad docs. Scope/priorities → this file +
   the roadmap. Architecture → DECISIONS.md. Never from memory.
2. **The ARP test gates every feature.** Operate, not just display — or justify why.
3. **The six mechanics in §3 are inviolable.** No shortcut ships that weakens actor-scoping,
   tool-use, human-in-the-loop writes, verifiable numbers, actionable blockers, or resume.
4. **The brand hard rules are code, not taste:** tokens-only colour, logical CSS, ar/en parity,
   monochrome chrome, one type voice, one icon hand, canonical Arabic lexicon (§6 of the Identity
   System — add the word there **before** it ships), designed states, settled motion.
5. **Scope discipline:** nothing from §5's refuse list enters a sprint, a plan file, or a demo
   without a written DECISIONS entry reversing it.
6. **Claims discipline:** nothing is marketed before it runs live (§2). "ARP" in public follows
   the claims gate. No "revolutionary", no "AI-powered everything".
7. **New dependency = written decision first.** Backend or frontend, no exceptions (WhatsApp API
   included).
8. **Gates before "done":** i18n parity, `tsc`, gate03, module pytest — plus the brand-feel
   checklist for anything a user sees. Green gate without the checklist is not done.
9. **Every AI capability ships with its permission story.** Who can trigger it, what it can touch,
   what the audit trail shows — written in the PR description.
10. **One task = one session; plans live in `Docs/plan/`;** big work splits at the marked
    checkpoints. Decisions get recorded the day they're made.
11. **The tie-breaker order is the Brief's values order:** Trust > Simplicity > Local fit >
    Consistency > Quality > Speed. When two rules conflict, the higher value wins.
12. **"Would Linear ship this?"** — the final question on every screen, message, and doc. If the
    honest answer is no, it isn't done.

## 7. Where things are recorded (so this file stays true)

- Category wording / public claims → Brand Brief (§1, §13, §17 log)
- Agentic-OS depth, moats, six guarantees → `Docs/ARP_DEEP_VISION.md` (adopted 2026-07-07)
- Arabic terms → Identity System §6 (before shipping)
- Architecture & reversals of §5 → DECISIONS.md
- Execution order & phase status → `Docs/plan/arp-roadmap.md`
- This file changes only by explicit founder decision — log the date below.

## 8. Change log

- **2026-07-02 — Created.** ARP category adopted (internal; public use gated on a live flagship
  demo). Build/remove scope fixed (§4/§5), team rules charter established (§6), cloud-default
  decision recorded. Companion roadmap created at `Docs/plan/arp-roadmap.md`.
- **2026-07-07 — Deep vision adopted (founder decision).** `Docs/ARP_DEEP_VISION.md` approved in
  full: agentic-OS layers L0–L6, five compounding moats, and six binding guarantees (grandmother
  bar, zero-hallucination contract, small-model-equality router, Arabic=English parity gate,
  three-roads reachability, flexibility-without-settings). Roadmap gains phases W+ / A2 / B2;
  Phase C re-chartered as Agent Runtime + roster. §3 mechanics and §5 refuse-list unchanged —
  depth widened, zero new modules. DECISIONS "ARP Deep Vision 2026-07-07" carries the detail.
