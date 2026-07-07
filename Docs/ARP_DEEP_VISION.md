# ARP Deep Vision — The Agentic Operating System

> Companion to [`ARP_STRATEGY.md`](ARP_STRATEGY.md) (category + scope + rules) and
> [`plan/arp-roadmap.md`](plan/arp-roadmap.md) (execution order). This file answers one question:
> **what must the AI layer become so that no one can build this before us — or copy it after us?**
> It widens the *depth* of the agentic layer, never the module count (STRATEGY §5 stands in full).
> Drafted 2026-07-07 at founder request. Roadmap/DECISIONS changes it implies are listed in §10 and
> take effect only when logged there.

---

## 1. The thesis — features don't make moats, flywheels do

Everything in the original vision ("AI operates the ERP") is a *feature list*. Features get copied
in quarters. What cannot be copied is a **compounding system**: an architecture where every new
module is agent-operable by construction, every user correction makes the product smarter for that
company, every agent run adds to a provable safety record, and every implemented customer produces
a reusable industry blueprint. Incumbents (SAP/Odoo/local players) are UI-first codebases; to match
this they must rewrite their write-paths, their permission model, and their audit trail — years,
not quarters. That retrofit cost is the "before". The flywheels below are the "after".

**The five compounding moats:**

| # | Moat | Compounds with | Copyable? |
|---|---|---|---|
| 1 | **Architecture flywheel** — contracts → tools auto-derived; new module = instantly operable | every module we ship | Only by rewriting an ERP from scratch (which is what we did) |
| 2 | **Company Brain** — per-tenant memory of vocabulary, corrections, policies | every day of usage | No — it's *their* data accumulating in *our* structure |
| 3 | **Trust ledger** — years of audited, verified, replayable agent runs | every agent action | No — time cannot be bought |
| 4 | **Blueprint & playbook network** — industry setup packs + shareable SOPs | every implementation | Slowly — needs our customer base |
| 5 | **Egyptian depth** — dialect, ETA, local tax, Arabic-first agentic UX | every localization decision | Foreign players won't; local players can't (no AI substrate) |

Every capability in this document must feed at least one flywheel. If it only adds a feature, it
doesn't ship (the ARP test, extended).

## 2. The seven-layer Agentic OS

Today's stack: module `services` → `Tool` registry (reads, actor-scoped) → `Action` registry
(propose→confirm writes) → agent loop → workspace panel. Solid, but it is a *kernel*, not an OS.
The OS adds five layers. Everything in phases A–F rides on these; building them early is cheap,
retrofitting them later is the same trap the incumbents are in.

```
L6  Agent Runtime        — background agents, scheduler, budgets, agent inbox
L5  Autonomy Ladder      — earned per-(user,action) trust levels; RBAC extended in time
L4  Company Brain        — per-tenant memory: aliases, corrections, policies, patterns
L3  Planner & Playbooks  — graph-derived plans; confirmed runs saved as reusable SOPs
L2  Simulation           — dry-run any plan in a rolled-back transaction; diff card first
L1  Verifier             — deterministic invariant checks after EVERY agent write
L0  Action Graph         — typed tools/actions with declared effects, preconditions, compensation
     └── module services + contracts + RBAC + audit (exists; the bedrock)
```

### L0 — Action Graph (tool substrate v2)

Upgrade `Tool`/`Action` from flat registries to a **graph with declared semantics**. Each action
declares, as data:

- `requires`: entities that must exist (customer, item, warehouse, open period…)
- `effects`: records it creates/updates + GL/stock impact class
- `invariants`: which verifier packs must pass after execution (L1)
- `compensation`: the action that undoes it (credit note reverses invoice; nothing "deletes")
- `risk`: `read | draft | post | destructive` — drives confirm/autonomy rules
- `idempotency_key`: how re-runs are detected (agent retries must be safe)

Why this is the keystone: **"set up my company" stops being prompt engineering and becomes graph
traversal.** The planner computes the dependency order deterministically (sales order needs
customer + item + warehouse + price → those need units + categories…); the LLM only fills
parameters and talks to the human. Deterministic skeleton, probabilistic filling — the inverse of
every chatbot-ERP demo on the market, and the reason ours won't hallucinate a workflow.

Also the **registry decorator**: one decorator on a module contract function auto-registers it in
the graph. From then on, *every module we ever ship is agent-operable on day one* — moat #1.

### L1 — Verifier (correct by construction, generalized)

After every agent write, run the invariant pack the action declared: trial balance balances, stock
never negative (unless policy allows), document sequences unbroken, doc totals equal line sums, VAT
consistent with rates, period open. Any failure → automatic compensation + honest report card.

The model **narrates; it never computes** (STRATEGY §3.4). The verifier is where that rule becomes
mechanical. This generalizes Phase B's "closed by construction" into **every write, every day**.
No competitor bolting GPT onto an ERP has this — their failure mode is silent wrong numbers, ours
is a caught-and-rolled-back report. That difference is the trust ledger (moat #3).

### L2 — Simulation (the diff card)

`simulate(plan)`: execute the whole multi-step plan inside one `transaction.atomic` that always
rolls back; collect the diff (records that would be created/updated, GL impact, stock impact,
documents that would post). Render as one **diff card**: "This will create 3 customers, 1 price
list, 14 orders; receivables +42,300 EGP. Approve?"

- Import preview (Phase A) becomes a *free consequence* of this layer instead of bespoke code.
- Month-close preview (Phase B) likewise.
- Claim it buys: **"See tomorrow's books before you post them."** No ERP on earth demos this.

### L3 — Planner & Playbooks

- **Planner**: walks the Action Graph to produce ordered, simulated, permission-checked plans from
  a natural-language goal. Multi-step by construction (vision §3).
- **Playbooks**: any confirmed agent run can be saved, parametrized (customer, period, warehouse),
  and re-run — manually, scheduled, or event-triggered. Permissions are checked at *run* time, not
  save time.
- **SOP compiler**: paste/dictate a company procedure in Arabic → draft playbook. The company's
  tribal knowledge becomes executable and stays when the employee leaves — an SMB pain no one
  addresses.
- Later (Phase F): industry playbook packs and accountant-shared playbooks — moat #4's network.

### L4 — Company Brain (the data flywheel)

A per-tenant structured memory store (not embeddings-first; typed tables, RAG plan already covers
documents):

- **Alias table**: "شركة النور" = customer #142; "كرتونة" = 12 pcs for item X. Learned from
  corrections, confirmed once, used forever.
- **Correction log**: every time a human edits an AI draft before confirming, store the delta.
  Feeds few-shot context per company. *The assistant measurably improves per company per month.*
- **Policy memory**: "wholesale customers get 14-day terms", "we never sell below cost from
  warehouse B" — stated once in chat, confirmed, then enforced in proposals.
- **Pattern memory**: seasonality, usual order sizes, expected margins — feeds anomaly agents.

Strictly per-tenant. No cross-tenant learning without explicit anonymized opt-in (a Phase F
decision). This is moat #2: after a year, Conductor knows the company like a senior employee —
and switching away means hiring a new one.

### L5 — Autonomy Ladder (RBAC extended into time)

Per **(user, action)** trust level — the mechanism that turns "human-in-the-loop" from a static
rule into a graduated, earned contract:

| Level | Behaviour |
|---|---|
| 0 | Suggest only — agent may not even propose |
| 1 | Propose → confirm each (today's default; floor for `post`/`destructive` risk) |
| 2 | Batch confirm — one approval for a whole plan |
| 3 | Auto-execute with undo window + digest entry (drafts and `create`-risk only) |
| 4 | Autonomous within charter — audit only (background agents on read/draft work) |

Promotion is **earned**: N consecutive approvals without edits → offer the upgrade; any correction
→ automatic demotion; admins cap maximum level per role; `post` and `destructive` never exceed
level 1 without a founder-level policy switch. Every level change is itself an audited event.
No ERP has a concept like this — it is the product-shaped answer to "how does autonomy grow
without ever betraying trust", and it demos beautifully.

### L6 — Agent Runtime (the background workforce)

- **Scheduler**: management-command + cron vs. worker — needs its DECISIONS entry (already flagged
  in roadmap Phase C).
- **Agent registry with charters**: every background agent declares scope (allowed tools), budget
  (LLM tokens/day, max writes/run, max records touched), cadence, escalation target, and the KPI it
  is accountable for. A charter is a config record, reviewable and auditable — not code spelunking.
- **Agent inbox**: findings arrive as evidence-linked cards; one-tap "fix it" runs a simulated plan
  (L2) → approve; "dismiss with reason" feeds the Company Brain (L4).

**The roster** (each an instance of ONE runtime — we build the runtime once, agents are charters):

| Agent | Charter (scope → KPI) | Phase |
|---|---|---|
| **Bookkeeper** | unposted docs, missing entries, unbalanced drafts → nothing pending > 48h | B |
| **Auditor** | duplicates, price drift, odd discounts, broken sequences, fraud patterns → anomalies surfaced < 24h | C |
| **Stock Controller** | reorder points, dead stock, expiring batches → zero stockouts on A-items | C |
| **Collector** | receivables aging, dunning drafts (Arabic, human tone) → DSO down | C |
| **Cash Forecaster** | 13-week cash view from open orders/bills → brief's cash line | C |
| **Compliance** | VAT/ETA deadlines, missing tax data → zero late filings | C/E(ETA) |
| **Implementation Coach** | setup completeness, unused modules, go-live score → time-to-live | A2 |
| **Data Janitor** | dedupe proposals, normalization, missing fields → data quality score | A |

## 3. The Implementation Consultant (the gap, now a phase — "A2")

The vision's §4/§8, previously unphased. The single biggest commercial lever after migration,
because together they kill the implementation industry:

1. **Interview**: conversational, Arabic-first, adaptive (industry? warehouses? manufacturing? —
   it already knows not to offer manufacturing; scope discipline reaches the wizard too).
2. **Blueprint**: industry packs for the Egyptian market — trading/distribution, pharma, food,
   building materials, services — each = chart of accounts + VAT config + units + document
   sequences + approval chains + roles. Packs are *data*, versioned in-repo, growing per
   implementation (moat #4… and moat #5, because they encode Egyptian reality).
3. **Simulated setup** (L2): the whole configuration as one diff card → one approval → configured
   company.
4. **Go-live readiness score**: derived from the Action Graph (which `requires` are unmet, which
   flows never ran) — an honest number, not a checklist theater. The Implementation Coach agent
   owns it until go-live, then hands off to the Phase C roster.

Exit test: a founder with zero ERP knowledge answers ~15 questions in Arabic and receives a
company that passes the readiness score — zero consultant hours. Combined with Phase A:
**"From spreadsheets to a running company in one afternoon"** becomes literally true, and we can
film it.

## 4. What each existing phase gains from the OS layers

| Phase | As planned | Widened by |
|---|---|---|
| **A — Smart Import** | 17-session engine | L2 gives preview/diff free; Data Janitor charter runs post-import; corrections seed the Company Brain on day one (flywheel starts at onboarding) |
| **A2 — Consultant** | *(new)* | §3 above |
| **B — Month-close** | orchestrated close | Becomes the flagship **playbook** (L3) + verifier showcase (L1); Bookkeeper agent keeps books close-ready all month so the close is minutes, not an hour |
| **C — Proactive** | brief + anomalies | Becomes the **runtime + roster** (L6) — brief is just the daily digest of agent findings; each finding one-tap fixable via L2 |
| **D — Bank vision** | photo → recon | Unmatched lines become detours (exists) + Collector agent learns payment patterns (L4) |
| **E — WhatsApp** | photo/voice/brief | Egyptian-dialect alias learning (L4); voice-first counter mode: «سجّل فاتورة لأحمد، ٣ كراتين زيت» → simulated draft → confirm — the demo that wins the market |
| **F — Platform** | portal + cloud | + Playbook/blueprint sharing across an accountant's clients; anonymized benchmark opt-in ("your margin vs. sector") — network effects on moats #2/#4 |

## 5. The eval harness (the invisible moat)

`erp/assistant/evals/`: a golden suite of real (anonymized) business tasks — Arabic and English —
scored on tool choice, plan shape, verifier outcomes, and answer faithfulness. Runs like a gate on
every provider/prompt/tool change (same discipline as gate03). Two effects: we can swap LLM
providers fearlessly (no vendor lock — a *cost* moat), and agent quality regressions are caught
before customers see them (feeds moat #3). No ERP competitor will have agent CI; most don't have
CI.

## 6. Safety, restated as product (vision §13 → mechanics)

Every agent action carries: **reasoning** (streamed, stored), **affected records** (diff card),
**preview** (L2), **rollback** (L0 compensation), **audit** (existing `audit.record`, plus agent
run id → full replay), **approval** (L5 level), **verifier verdict** (L1). The "flight recorder":
any agent run is replayable step-by-step from the audit trail — for the customer's auditor, for
regulators, for us. Trust (values order #1) made inspectable. This paragraph is the enterprise
sales deck in miniature.

## 7. The six guarantees (founder bars, 2026-07-07 — every phase is measured against these)

These are not aspirations; each has a mechanism and a gate. A phase that can't demonstrate all six
on its own flows is not done.

### G1 — The grandmother bar (non-technical, self-serve)

An owner with zero ERP and zero technical knowledge completes every AI flow **alone, in Arabic,
with no manual and no consultant**. Mechanisms:

- **One question at a time.** The wizard, detours, and imports never show a form wall; the agent
  asks, the user answers, the diff card shows the result in plain words.
- **No jargon anywhere a user reads.** The canonical lexicon (Identity System §6) is the plain
  layer; technical mapping (posting, ledgers, journals) happens under the hood. "هنسجل الفاتورة دي؟"
  not "post to the receivables sub-ledger".
- **Blame-free errors with a fix attached** (existing brand rule) — every blocker arrives as
  issue + one-tap fastest permitted fix + guaranteed resume (STRATEGY §3.5/3.6).
- **Undo everywhere** (linear-polish primitive already shipped) + L2 preview before anything real.
- **The gate:** every phase's acceptance file includes a scripted **unaided-user test** — a
  non-technical tester completes the flow start-to-finish with no help. Fails → not done. Same
  standing as gate03.

### G2 — The zero-hallucination contract

- **Numbers, names, dates, and statuses come ONLY from tool results** — server-formatted,
  citation-linked, every one clickable to the real record. Model text containing an unverifiable
  number is a build bug, not a model quirk.
- **Forced grounding:** the deterministic guard that already forces a real `search_documents` call
  before document-shaped answers (`agent.py::run`, DECISIONS FILE_11 addendum) generalizes to all
  data-shaped intents — an answer with zero tool calls to a lookup/report question is rejected
  before the user sees it. (Closes the filed "live-data grounding gap" as a standing bar.)
- **Refuse-over-guess:** when the data isn't reachable, the assistant says so and offers the
  fastest path — it never fills the silence. "لا أرى هذه البيانات" beats a confident invention,
  always (Trust is value #1).
- **Schema-constrained outputs** (JSON mode already in use) + L1 verifier as the last net: what
  slips past the prompt is caught by mechanical invariants and rolled back with an honest card.

### G3 — Small-model equality (routing: the cheap model does the job exactly like the flagship)

The principle that makes this possible: **intelligence lives in the substrate, not the model.**
The Action Graph plans deterministically; tools are typed; outputs are schema-constrained; the
verifier checks the math. What remains for the LLM — intent classification, slot filling,
narration — is exactly the work small models do well.

- **Router:** intents are classed by difficulty; each class routes to the cheapest model admitted
  for it. Automatic escalation on low confidence, schema-validation failure, or verifier failure —
  the user never sees the retry, only the (correct) answer.
- **The admission rule:** a model enters the routing table **only after passing the golden eval
  suite (§5) in BOTH languages at the same bar as the flagship model** for that intent class.
  If a cheap model can't match the bar, it simply doesn't route — so no user ever experiences a
  "cheap model day".
- Providers are already pluggable (multi-provider client, PR #31: Anthropic/Gemini/Groq) — the
  router is a thin layer on what exists.
- **The business consequence:** cheap-by-default routing keeps per-tenant AI cost at SMB pricing —
  the moat competitors with flagship-only stacks cannot price against.

### G4 — Arabic exactly like English (parity as a gate, not a promise)

- Arabic is the **primary test language**, not a translation target. Every golden eval task exists
  in Egyptian-phrased Arabic AND English with the **same pass bar** — build-blocking, exactly like
  the i18n parity gate. A model or prompt change that scores lower in Arabic does not ship.
- **Normalization layer before the model:** Arabic-Indic digits (٣ = 3), hamza/ta-marbuta/tashkeel
  variants, mixed Arabic-English in one sentence ("اعمل sales order لشركة النور"), dialect terms —
  resolved deterministically and via Company Brain aliases (L4), so the model receives clean intent
  regardless of how it was typed.
- Voice input (Phase E) targets Egyptian dialect specifically, and its transcripts run through the
  same normalization + eval bar.

### G5 — Three roads to everything (reachable)

Every function is reachable three ways: **the screen** (navigation), **⌘K palette** (power users),
**the chat** (ask in plain words — the equalizer for G1 users). Nothing is chat-only, nothing is
screen-only; the palette↔AI bridge (linear-polish FILE_12) already joins two of the three. The
Action Graph makes this cheap: one registration feeds all three surfaces.

### G6 — Flexible without settings sprawl

Flexibility comes from **saying it, not configuring it**: policies stated once in chat and
confirmed into the Company Brain (L4), playbooks saved from real runs (L3), autonomy earned per
action (L5). "قول القاعدة مرة واحدة، أكّدها، وخلاص" replaces settings pages — STRATEGY §5.2
(no settings sprawl) survives contact with "make it flexible".

## 8. What we still refuse (the moat is also what we don't build)

Unchanged and re-affirmed — depth over breadth is *how* the moat compounds:

- No HR / manufacturing / projects until the money loop is unbeatable (STRATEGY §5.1). The wizard
  and blueprints simply never offer them.
- No general-purpose "AI can do anything" marketing — claims follow demos (claims gate).
- No embeddings-everywhere: typed tools + typed memory first; RAG only where documents live.
- No cross-tenant learning by default — the Company Brain is the customer's, full stop.
- No autonomy shortcuts: `post`/`destructive` never auto-execute, whatever the trust level says.

## 9. Why "no one before, no one after" — the honest argument

**Before**: the substrate (actor-scoped services, append-only audit, typed contracts, tool-use
architecture) was built into the foundation for two years. Anyone starting now starts two years
back — and anyone bolting AI onto an existing ERP inherits write-paths that were never designed to
be driven by an agent (no compensation, no invariants, superuser integrations everywhere).

**After**: copying the feature list doesn't copy the flywheels. A competitor shipping "AI ERP" in
2027 has zero corrections in any Company Brain, zero entries in any trust ledger, zero Egyptian
blueprints, and a UI-era codebase to retrofit. Meanwhile every Conductor tenant-day widens all
five gaps. That — not any single feature — is the answer to the founder's question.

## 10. Roadmap & DECISIONS changes — **APPROVED 2026-07-07, applied**

Applied same day: roadmap phases W+/A2/B2 + C re-charter + F additions in
[`plan/arp-roadmap.md`](plan/arp-roadmap.md); queue position 6 in
[`plan/EXECUTION_ORDER.md`](plan/EXECUTION_ORDER.md); DECISIONS entry "ARP Deep Vision
2026-07-07"; strategy change log §8. Original proposal text kept below for the record.

Roadmap inserts (letters keep their meaning; inserts use suffixes):

1. **Phase W+ (post ai-workspace 15, ~4–5 sessions): "OS foundations"** — Action Graph v2 (L0),
   verifier packs (L1), simulation/diff card (L2). Before Phase A, because A and B both ride on
   them and A's preview otherwise gets built bespoke and thrown away.
2. **Phase A2 (~4–5 sessions): Implementation Consultant** — after A; shares its claim.
3. **Phase B2 (~4–5 sessions): Company Brain + Autonomy Ladder** (L4+L5) — after B; needs real
   usage data to learn from, and B's flagship earns the trust the ladder spends.
4. **Phase C rewritten as "Agent Runtime + roster"** (L6) — brief becomes the digest of charters.
5. **Phase F gains** playbook/blueprint sharing + anonymized benchmark opt-in.

DECISIONS entries needed when approved: scheduler choice (cron vs worker); simulation layer;
autonomy-ladder model + its RBAC interaction; Company Brain data model + privacy stance; eval
harness as a standing gate; Phase A2 addition; agent charters as config records; **model router +
admission rule (G3)**; **Arabic-parity eval bar as build-blocking gate (G4)**; **grounding guard
generalized to all data intents (G2 — closes the filed live-data gap)**; **unaided-user test in
every phase acceptance (G1)**.

Current queue (unified-ui → ai-workspace 11–15 → smart-import) is **not** disturbed; W+ slots in
after workspace 15 and before smart-import begins.

## 11. Change log

- **2026-07-07 — Created** at founder request: widen the AI-operating-system vision into a
  defensibility plan. No roadmap/DECISIONS change is in force until logged there (§10).
- **2026-07-07 (later) — §7 "six guarantees" added** at founder request: grandmother bar
  (self-serve, no technical guidance), zero-hallucination contract, small-model equality via
  routing + admission rule, Arabic=English parity as a build-blocking gate, three roads to every
  function, flexibility without settings sprawl. Four new DECISIONS items added to §10.
- **2026-07-07 (later still) — §10 APPROVED by founder and applied**: roadmap + EXECUTION_ORDER +
  DECISIONS + strategy change log all updated. This document is now in force, not a proposal.
