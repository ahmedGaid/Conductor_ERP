# Conductor ERP — Business Plan & Go-To-Market Strategy

**Version 1.0 · July 2026 · Confidential**
Prepared for: investors, strategic partners, and prospective enterprise customers.

---

## How to read this document

Three rules govern everything below.

1. **Every number is an assumption until proven.** Egypt has poor commercial data. Where a figure is
   estimated, the estimate is labelled, the derivation is shown, and the source of error is named.
   Nothing here is presented as fact when it is an inference.
2. **Conservative / Realistic / Optimistic.** Any projection that materially affects the investment
   case is shown in three scenarios. The **Realistic** case is the plan of record. Board targets,
   hiring triggers, and runway are set against **Conservative**.
3. **Weak assumptions are challenged in-line.** Where the founding thesis is fragile — and there are
   four places where it is — the document says so under a heading marked
   **⚠️ Assumption under stress**. An investor should read those four sections first.

**Currency.** All figures in Egyptian Pounds (EGP) with USD equivalents at **1 USD = 50 EGP**,
the planning rate. The EGP has lost ~70% of its USD value since 2022; USD-denominated projections
for an EGP-revenue business are structurally misleading. This is treated as a first-order risk, not
a footnote (§15.3, §16.8).

**Fiscal year.** Year 1 begins at commercial launch (planned Q1 2027), not at company founding.

---

# 1. Executive Summary

## 1.1 What Conductor is

Conductor is a cloud ERP for Egyptian small and medium businesses — companies with 10 to 250
employees running real operational complexity: multiple warehouses, credit sales, production orders,
payroll, and a tax authority that now demands machine-readable invoices for every transaction.

Sixteen modules ship in the core product: General Ledger, Accounts Payable, Accounts Receivable,
Inventory, Purchasing, Sales, CRM, Manufacturing, Asset Management, Projects, HR & Payroll, Banking,
Fixed Assets, Business Intelligence, Workflow, and Document Management. This is not a phased promise;
it is the current build state.

Conductor is **Arabic-first**. Not Arabic-localised — Arabic-first. The interface is designed
right-to-left, the terminology is a single canonical Arabic lexicon (one word per concept, never
two), and the English build is the translation, not the other way around. Every competitor in this
market inverts that relationship, and every Egyptian finance team can feel it within ten minutes of
use.

## 1.2 The problem

An Egyptian company with 40 employees and EGP 80M in annual revenue has three bad options today.

**Option A — the international suite.** NetSuite, SAP Business One, or Dynamics 365. Functionally
complete. Costs USD 40,000–150,000 in year one once implementation is counted, in a currency the
customer does not earn. Takes six to fourteen months to go live. The Arabic interface is a
right-aligned afterthought. The local partner controls the relationship and charges for every field
change. Fewer than 3,000 Egyptian companies can rationally buy this.

**Option B — the open-source suite.** Odoo or ERPNext. Cheap to license, expensive to own. The
software is a construction kit, not a product: a competent Odoo deployment in Egypt requires a
partner, EGP 150,000–600,000 of implementation, and a permanent dependency on whoever configured it.
Upgrades break customisations. The Arabic is community-contributed and inconsistent — the same
concept appears under three different words on three different screens. Accounting controls are
configurable to the point of being optional, which is precisely the wrong default in a market where
the auditor is the customer's real user.

**Option C — the local accounting package.** Daftra, Qoyod, Al-Amin, dozens of desktop systems from
the 1990s still running on a machine under someone's desk. Cheap, familiar, priced in EGP. They do
invoicing and a general ledger. They do not do manufacturing, or projects, or multi-warehouse
inventory costing, or workflow approvals. The company outgrows the software in year three and then
faces options A and B again.

The gap is specific and it is large: **there is no product between EGP 20,000/year and EGP 2,000,000/year
that a 40-person Egyptian company can buy, deploy in six weeks, and still be running in year seven.**

## 1.3 Why the market needs it now

Four forces converged between 2020 and 2026, and none of them were true five years ago.

**1. The state made structured accounting compulsory.** The Egyptian Tax Authority's e-invoicing
mandate now covers effectively all VAT-registered entities, and the e-receipt system is extending the
same logic to retail. Every B2B invoice must be submitted, signed, and accepted by ETA in a defined
schema. A company running its books in Excel or a 1998 desktop package is no longer merely
inefficient — it is non-compliant. This is the single most important fact in this document. **The
government has done the market education that would otherwise have cost us five years and USD 10M.**

**2. Cloud objections collapsed.** The 2019 Egyptian SMB owner said "my data will not leave my
office." The 2026 owner runs payroll through a bank portal, files taxes through a government web
form, and pays suppliers through InstaPay. The objection is now about *uptime and Arabic support*,
not about the cloud itself. That is a solvable objection.

**3. Currency devaluation broke the dollar-priced incumbents.** A NetSuite contract that cost EGP
1.5M in 2021 costs EGP 5.5M in 2026 for identical scope. Renewal conversations across the mid-market
are now open in a way they have not been for a decade. Every devaluation is a lead-generation event
for an EGP-priced product.

**4. AI made "software that explains itself" possible.** The reason ERP implementations take nine
months is not the software — it is the translation between what a business does and what the system
expects. Conductor's AI layer attacks that translation cost directly (§1.5). But it does so under a
hard constraint: **AI drafts, humans post.** Nothing that touches the ledger is autonomous.

## 1.4 Why us, why this shape

Conductor's product philosophy is unusual for ERP and is the primary source of durable advantage:

| Principle | What it means in practice | Why competitors cannot copy it quickly |
|---|---|---|
| **Simple like Linear** | One canonical way to do each task. No 40-field forms with 34 hidden fields. | Requires saying no to configurability; incumbents' revenue depends on configurability. |
| **Beautiful like Notion** | Design tokens, one type voice, one icon set, designed empty/error states. | Requires a design system enforced by build gates, not by taste. |
| **Fast like Telegram** | Sub-200ms interactions, optimistic updates, keyboard-first. | Requires architectural decisions made at the start, not retrofitted. |
| **Reliable like Oracle** | Double-entry integrity, immutable audit trail, period locks that actually lock. | Cultural, not technical — most modern ERP startups are lax here. |
| **Trustworthy before intelligent** | AI proposes; a human posts. Every AI action is logged, attributed, reversible. | Directly conflicts with the "autonomous agent" positioning most AI-ERP startups have taken. |

The fifth row is the differentiator that matters commercially. The buyer of an ERP in Egypt is
usually the **financial manager or the owner's accountant**, not the CTO. That person's career risk
is a wrong number in a filed return. Every "AI does your accounting" pitch increases their perceived
risk. Conductor's pitch — *AI removes the typing, you keep the control* — decreases it.

## 1.5 The AI thesis, stated honestly

Conductor is being built as **ARP — Agentic Resource Planning** — an ERP where an assistant can
read the whole business state and draft work across modules. The commercial value is not
"intelligence." It is **implementation cost collapse**:

- **Data migration** — the single largest line item in every ERP project — becomes an AI-assisted
  mapping exercise instead of six weeks of consultant time.
- **Chart-of-accounts and workflow setup** becomes a guided conversation instead of a configuration
  workshop.
- **Ongoing support tickets** ("how do I issue a credit note against a partially paid invoice")
  are answered in-product with reference to the customer's own data.

If Conductor can take a 40-person manufacturer live in **6 weeks at EGP 120,000** where Odoo takes
**20 weeks at EGP 400,000**, that is the whole business. AI is the means; implementation economics
are the end. We will not market AI as a feature. We will market **"live in six weeks"** and let the
mechanism be our problem.

**⚠️ Assumption under stress #1:** the six-week claim is unproven at scale. It is validated against
internal builds and pilot design, not against 50 live customers. If real-world implementation
converges to 12 weeks, gross margin drops from 76% to ~68% and the Year-3 ARR target falls roughly
20%. §9.6 models this.

## 1.6 Long-term vision

By 2031, Conductor is the system of record for 4,000–6,000 businesses across Egypt, Saudi Arabia,
the UAE, Jordan, Morocco, and Kenya — the layer where the invoice, the inventory movement, the
payroll run, and the bank reconciliation all live in one auditable ledger, in Arabic, priced in local
currency.

Around that ledger sit: a payments and banking layer, government integrations in each market, a
partner ecosystem of accounting firms and implementers, an app marketplace, industry editions
(manufacturing, distribution, construction, clinics), and public APIs that make Conductor the
default backend for anything an Egyptian developer builds for business customers.

The strategic prize is not ERP licence revenue. It is **being the system that knows what every SMB in
the region actually did** — which, with permission and correct governance, becomes the basis for
credit, insurance, procurement, and benchmarking products with far better economics than software.

## 1.7 The ask

**USD 1.5M seed** (EGP 75M) for 24 months of runway to reach:

- 380–450 paying customers
- EGP 34M (~USD 680k) ARR exiting Year 2
- Net revenue retention above 105%
- Repeatable 8-week implementation with a partner-delivered majority
- Series A readiness at USD 1.5M ARR run-rate

Use of funds: 46% engineering, 24% go-to-market, 14% implementation & customer success, 9% infra &
security, 7% G&A. Detail in §16.

## 1.8 What would make this fail

Stated up front, because an investor will find them anyway:

1. **Egyptian SMBs may simply not pay for software.** Willingness to pay is the deepest risk in this
   market, deeper than competition. Mitigation and evidence: §3.6, §15.1.
2. **Odoo's partner ecosystem is entrenched.** 30+ Egyptian partners with sales teams already sell
   Odoo. We are competing against a distribution channel, not a product. §5.6.
3. **Implementation is a services business wearing a SaaS costume.** If we cannot push 60%+ of
   implementations to partners by Year 3, we become a consultancy with poor multiples. §11.4.
4. **Currency.** EGP revenue, USD-denominated cloud costs and salaries-for-senior-talent. §16.8.

---

# 2. Market Opportunity

## 2.1 Method, and why most ERP market sizes are worthless

The standard approach — take a published "MENA ERP market USD 2.1bn, growing 14% CAGR" figure and
claim 1% — is useless for two reasons. First, those figures are dominated by enterprise licences and
services for companies we will never sell to. Second, they say nothing about how many businesses can
actually *pay*, which is the only number that matters.

We build bottom-up instead: **count the businesses, filter to those that can pay, multiply by what
they can pay.** Every filter is stated and challengeable.

## 2.2 The business population funnel — Egypt

Egypt's last full economic census (CAPMAS, 2017/18) counted approximately **3.7 million
establishments**. Population growth and formalisation drives put the 2026 figure at roughly
**4.0–4.3 million**. Almost all of them are irrelevant to us.

| # | Layer | Estimate (2026) | Derivation & confidence |
|---|---|---|---|
| 1 | All establishments (incl. informal) | 4,100,000 | CAPMAS census extrapolated. **High confidence** on order of magnitude. |
| 2 | Formally registered (holds a tax file) | ~1,150,000 | ~28% formalisation. Egypt's informal economy is estimated at 40–60% of GDP; formalisation drives (2020 MSME Law 152) have added ~500k files. **Medium.** |
| 3 | VAT-registered / under ETA e-invoice mandate | ~520,000 | ETA has publicly cited "hundreds of thousands" of registered issuers. **Medium-low** — this is the number we most want and least reliably know. |
| 4 | ≥ 5 employees | ~186,000 | ~36% of VAT-registered. Egyptian firm-size distribution is extremely bottom-heavy: ~87% of all establishments have 1–4 workers. **Medium.** |
| 5 | Annual revenue ≥ EGP 20M (~USD 400k) — the ERP affordability floor | ~97,000 | Below this, a company cannot justify EGP 40k+/yr on software plus implementation. **Medium-low.** |
| 6 | Operationally complex enough to need ERP (not just invoicing) | ~62,000 | Excludes single-location service firms adequately served by an accounting package. **Low-medium — this is our judgement, not data.** |
| 7 | Currently pay for *some* business software | ~26,000 | Includes desktop legacy. Implies ~42% of layer 6 already pay something — consistent with anecdotal channel checks. **Low.** |
| 8 | Would accept a cloud, subscription product today | ~19,000 | ~73% of layer 7. Post-2023 attitudes; would have been ~25% in 2019. **Low.** |

**Read layers 5–8 as directional, not precise.** The honest statement is: *the Egyptian ERP-buyable
universe is tens of thousands of companies, not hundreds of thousands and not thousands.* A business
plan that requires the number to be 300,000 is a bad plan; this one requires it to be above ~35,000,
which we are confident of.

## 2.3 TAM / SAM / SOM

**TAM — Total Addressable Market.** All Egyptian businesses that could rationally buy an ERP of
Conductor's class, at the annual revenue Conductor could earn from each (subscription + attributable
services, amortised).

| Segment (by employees) | Companies | Avg annual value to Conductor (EGP) | TAM (EGP) | TAM (USD) |
|---|---:|---:|---:|---:|
| Micro (1–9), complex enough | 21,000 | 14,000 | 294M | 5.9M |
| Small (10–49) | 27,500 | 62,000 | 1,705M | 34.1M |
| Medium (50–249) | 11,500 | 185,000 | 2,128M | 42.6M |
| Large / lower-enterprise (250–999) | 2,100 | 520,000 | 1,092M | 21.8M |
| **Total Egypt TAM** | **62,100** | **~85,600 blended** | **5,219M** | **104.4M** |

**Egypt TAM ≈ EGP 5.2 billion (USD 104M) in annual revenue potential.**

This is smaller than the numbers most ERP decks show, and that is deliberate. A USD 104M Egyptian TAM
supports a company reaching perhaps USD 15–25M ARR domestically — a strong outcome, but not a
venture-scale one alone. **The venture case requires MENA expansion, and this document does not
pretend otherwise.**

**Regional TAM extension** (Years 4–6, illustrative — these markets are not modelled bottom-up with
the same rigour and should be treated as an order-of-magnitude sketch):

| Market | Relevant SMBs (est.) | Avg annual value (USD) | TAM (USD) | Entry difficulty |
|---|---:|---:|---:|---|
| Egypt | 62,000 | 1,712 | 104M | Home |
| Saudi Arabia | 46,000 | 4,400 | 202M | High price ceiling; ZATCA Fatoora mandate mirrors ETA. **Best second market.** |
| UAE | 28,000 | 5,100 | 143M | Crowded; strong Zoho/Odoo presence; English-first. |
| Jordan + Lebanon | 14,000 | 1,900 | 27M | Low value, good testbed. |
| Morocco + Tunisia | 34,000 | 1,500 | 51M | French-first — a different product. |
| Kenya + Nigeria | 55,000 | 1,300 | 72M | English-first, mobile-money-centric. Different product. |
| **MENA core (EG+SA+AE+JO)** | **150,000** | — | **~476M** | |

**Strategic conclusion: Saudi Arabia is the only expansion market that matters before Year 4.** It has
2.6× Egypt's per-customer value, an e-invoicing mandate structurally identical to ETA's (so the
compliance engine ports), and an Arabic-first requirement we already satisfy. Morocco and West Africa
are French/English-first and would require a second product; they are explicitly deprioritised.

**SAM — Serviceable Addressable Market.** Egypt only, Years 1–3. Companies of 10–249 employees, in
the six priority industries (§4), VAT-registered, with revenue above EGP 20M.

| Filter | Companies | Note |
|---|---:|---|
| Egypt small + medium (10–249) | 39,000 | From TAM table |
| × in six priority industries (~68%) | 26,500 | §4 ranking |
| × reachable via our channels in 3 years (~72%) | 19,100 | Excludes deep-upper-Egypt, closed government supply chains |
| **SAM** | **19,100 companies** | |
| × blended annual value EGP 98,000 | | Higher than TAM blend — priority industries are richer |
| **SAM value** | **EGP 1,872M (USD 37.4M)** | |

**SOM — Serviceable Obtainable Market, 3 years.** What we can realistically capture.

| Scenario | 3-yr customers | % of SAM | Blended ARPA (EGP) | Exit-Y3 ARR (EGP) | Exit-Y3 ARR (USD) |
|---|---:|---:|---:|---:|---:|
| Conservative | 340 | 1.8% | 82,000 | 27.9M | 558k |
| **Realistic** | **620** | **3.2%** | **91,000** | **56.4M** | **1.13M** |
| Optimistic | 1,050 | 5.5% | 104,000 | 109.2M | 2.18M |

**Sanity check against comparables.** Daftra reports tens of thousands of users, but at an ARPA of
roughly EGP 6,000–15,000 — a different (much lower) segment. Odoo's Egyptian partner ecosystem
collectively lands an estimated 250–450 new mid-market deployments a year across 30+ partners; a
single well-funded product taking 200 deals in Year 3 is aggressive but not fantastical. The
Realistic case implies **Conductor wins roughly 1 in 5 new mid-market cloud ERP decisions in Egypt by
Year 3.** That is the claim an investor should interrogate.

## 2.4 Market growth

| Driver | Direction | Magnitude (our estimate) |
|---|---|---|
| ETA e-invoice/e-receipt enforcement widening | ↑↑ | Adds ~8–12% to layer 3 annually as enforcement bites |
| Formalisation drives (MSME Law 152 incentives) | ↑ | ~5%/yr growth in layer 2 |
| EGP devaluation vs. USD-priced incumbents | ↑↑ | Episodic; each 20% devaluation opens a renewal window |
| SMB failure rate / economic contraction | ↓ | Real; Egyptian SMB mortality is high. Netted into churn, §9.3 |
| Cloud acceptance | ↑ | Layer 8 conversion improving ~6pp/yr |
| **Net addressable-market growth** | **↑** | **~11–14% p.a. in company count; higher in EGP terms due to inflation-linked pricing** |

Inflation deserves a note: Egyptian inflation running 15–25% means EGP-denominated ARR grows
mechanically with annual price escalators. We build **CPI-linked renewal uplifts (capped at 12%)**
into every contract from day one. This is standard in Egypt and customers expect it — but it means
**reported EGP ARR growth overstates real growth**, and we report both.

---

# 3. Ideal Customer Profile

## 3.1 Segment definitions

| Segment | Employees | Annual revenue (EGP) | Annual revenue (USD) | Finance staff |
|---|---|---|---|---|
| Micro | 1–9 | < 20M | < 400k | 0–1 (often external accountant) |
| Small | 10–49 | 20M – 150M | 400k – 3M | 1–3 |
| Medium | 50–249 | 150M – 900M | 3M – 18M | 3–10 |
| Enterprise (lower) | 250–999 | > 900M | > 18M | 10–30 |

## 3.2 Micro (1–9 employees)

**Profile.** A trading company, a clinic, a small workshop. One owner who is also the salesperson.
Books kept by an external accountant who visits monthly with a USB stick.

**Pain points.**
- ETA e-invoice compliance is now mandatory and they are handling it through a free portal, manually,
  one invoice at a time.
- No idea what actual stock is. No idea which customer owes what beyond a notebook.
- Cash-flow blindness — the single most common cause of failure.

**Buying behaviour.** Owner decides alone, in one meeting, on price. Sales cycle: 3–14 days. Will not
attend a demo longer than 20 minutes. Extremely price-sensitive: EGP 500/month is a real decision,
EGP 2,000/month is a rejection. Churns hard — often because the business itself fails.

**Expected implementation.** Zero-touch. Self-serve signup, guided setup, no consultant. Any human
touch destroys the unit economics at this price.

**Verdict: not our beachhead.** We serve Micro only through a **Starter** tier that is self-serve,
support-light, and deliberately capability-limited — as a **funnel into Small**, and as a channel for
accounting firms (§11.4) who onboard many micro clients at once. We do not build for Micro and we do
not measure success by Micro logos. Expected ARPA EGP 9,000–16,000/yr.

**⚠️ Assumption under stress #2:** self-serve SMB SaaS has a poor track record in Egypt. Card
penetration, trust in online subscriptions, and support expectations all work against it. We plan
Starter as an experiment with a defined kill criterion: if Starter CAC payback exceeds 14 months by
month 18, we shut it and go pure mid-market.

## 3.3 Small (10–49 employees) — **primary beachhead**

**Profile.** A distributor with two warehouses and 200 credit customers. A 30-person contract
manufacturer. A construction subcontractor running 6 concurrent projects. Revenue EGP 20–150M. There
is a financial manager, one or two accountants, and a storekeeper who keeps a parallel Excel file
nobody trusts.

**Pain points, in the order they say them:**
1. "I don't know my real profit per product/project until three months later."
2. "Stock on the system never matches stock in the warehouse."
3. "Collections. I don't know who owes me what, and nobody chases it."
4. "ETA rejects my invoices and I don't know why." *(compliance is the door-opener)*
5. "My accountant is the only person who understands the system, and he is leaving."
6. "The reports are in English and the board is Egyptian."

**Buying behaviour.** Two-to-three person committee: owner/GM (budget), financial manager (real
evaluator, real veto), and often an IT person or external consultant (technical veto). Sales cycle
**5–11 weeks**. Requires: a demo with *their* data, a written implementation plan, at least two
referenceable customers in their industry, and a price in EGP. Highly reference-driven — Egyptian
mid-market buys on trust networks, not on G2 reviews.

**Expected implementation.** 4–8 weeks. 3–6 modules live at go-live (GL, AR, AP, Inventory, Sales,
Purchasing), others phased. EGP 60,000–180,000 implementation fee. 8–25 named users.

**Expected ARPA:** EGP 55,000–120,000/yr subscription. **This segment is 55–60% of the Year-3 revenue
plan and where product, marketing, and hiring are pointed.**

## 3.4 Medium (50–249 employees) — **the value segment**

**Profile.** A 140-person food manufacturer with three production lines and a fleet. A regional
distributor with 8 branches. A construction firm with 20 active projects. Revenue EGP 150–900M.
Already has *something* — usually an aging local system, an Odoo deployment they resent, or SAP B1
they underuse.

**Pain points.**
1. Consolidation across branches/entities takes 3+ weeks each month-end.
2. Costing is wrong or absent — they cannot answer "what does this SKU actually cost to make."
3. Approvals happen on WhatsApp; there is no auditable trail when the auditor asks.
4. Their existing system's vendor is unresponsive or has raised prices in USD.
5. Data is in four systems and reconciliation is a full-time job.

**Buying behaviour.** Formal. RFP or structured comparison, 3–6 vendors, scoring matrix. Committee of
5–9: CFO (economic buyer), CEO (sponsor), IT manager (technical), heads of ops/production/sales
(users), sometimes the external auditor (informal veto). Sales cycle **4–9 months**. Requires: a paid
or unpaid PoC on real data, security documentation, a data-migration plan, SLA terms, and an escape
clause. Will negotiate hard and will ask for source-code escrow or on-premise as a bargaining chip.

**Expected implementation.** 10–20 weeks, 8–14 modules, phased in two or three waves. EGP
250,000–900,000 implementation. 25–90 named users. Almost always requires 2–4 custom reports and 1–2
integrations (bank file formats, a legacy POS, a WMS).

**Expected ARPA:** EGP 160,000–420,000/yr. **This is ~35% of Year-3 revenue from ~18% of logos** — and
it is where net revenue retention above 110% comes from, because these accounts expand modules and
users every year.

## 3.5 Enterprise (250+ employees)

**Profile.** Groups, listed companies, large family conglomerates, sizeable government-adjacent
entities.

**Pain points.** Multi-entity consolidation, statutory reporting, IFRS compliance, cost centres,
inter-company eliminations, complex approvals, integration with existing HR/banking/treasury.

**Buying behaviour.** 9–24 month cycles. Procurement, legal, security review, sometimes a public
tender. Requires: ISO 27001 or equivalent, penetration test reports, financial statements proving
vendor viability, local data residency, dedicated account team, custom SLA with penalties, and often
a Big-4 or large local integrator as prime contractor.

**Expected implementation.** 6–18 months, EGP 1.5M–8M, 100–600 users.

**Verdict: not before Year 3, and only reactively.** Enterprise deals in Years 1–2 are a **trap**.
They consume the whole engineering roadmap, distort the product toward one customer, and pay slowly.
The rule: **no enterprise deal in Years 1–2 unless it (a) comes inbound, (b) requires no more than 15
person-days of custom work, and (c) pays 50% up front.** Anything else is politely declined or routed
to a partner. We will break this rule at most once, for a lighthouse logo, and the board should hold
us to it.

## 3.6 The willingness-to-pay question

**⚠️ Assumption under stress #3.** The core commercial risk is not competition. It is that Egyptian
SMBs have a deeply ingrained low willingness-to-pay for software, an expectation of one-time
purchases rather than subscriptions, and a widespread tolerance for piracy in adjacent categories.

**Why we believe it is changing anyway:**

| Evidence | Strength |
|---|---|
| ETA compliance is a legal requirement, not a productivity nice-to-have. Legal requirements get budgeted. | **Strong** |
| Cloud-hosted products cannot be pirated. The historic alternative to paying (a cracked copy) is unavailable. | **Strong** |
| SMBs already pay recurring EGP for telecoms, delivery platform commissions, POS terminal fees, and accountant retainers. Recurring payment is not culturally alien; recurring payment *for software* is new. | Medium |
| Devaluation has made local-currency pricing a positive differentiator rather than a discount signal. | Medium |
| Odoo partners routinely close EGP 300k–700k projects in Egypt today. Money at this level exists. | **Strong** |

**Mitigation built into the plan:**
- Price anchoring on **replacement cost, not feature count** — "one additional accountant costs EGP
  180,000/year; Conductor costs EGP 84,000."
- Annual prepay with a meaningful discount (§7.5) — matches Egyptian cash-behaviour and fixes cash
  flow.
- Implementation fee charged **up front**, non-refundable, which both funds delivery and filters
  unserious buyers.
- **Compliance as the wedge, operations as the expansion.** Sell the ETA problem (urgent, budgeted,
  undeniable); expand into inventory/manufacturing/BI once trust exists.

---

# 4. Target Industries

## 4.1 Ranking method

Each industry scored 1–5 on four axes, then ranked by a weighted composite:
**Priority = (ERP Fit × 0.35) + (Pain Intensity × 0.30) + (Expected ARR × 0.20) − (Sales Difficulty × 0.15)**

*ERP Fit* = how much of the pain our current 16 modules already solve, without vertical development.
*Sales Difficulty* = length of cycle, number of stakeholders, procurement friction, price resistance.

## 4.2 The ranking

| # | Industry | ERP fit | Pain | Sales difficulty | Expected ARPA (EGP) | Composite | Tier |
|---:|---|:---:|:---:|:---:|---:|:---:|---|
| 1 | **Distribution & Wholesale** | 5 | 5 | 2 | 105,000 | **4.6** | **Beachhead** |
| 2 | **Light Manufacturing** | 5 | 5 | 3 | 185,000 | **4.5** | **Beachhead** |
| 3 | **Retail chains (multi-branch)** | 4 | 5 | 3 | 120,000 | **4.0** | **Beachhead** |
| 4 | **Construction & Contracting** | 4 | 5 | 4 | 195,000 | **3.8** | Wave 2 |
| 5 | **Food & Beverage (production)** | 5 | 4 | 3 | 165,000 | **3.8** | Wave 2 |
| 6 | **Professional Services** | 4 | 3 | 2 | 62,000 | **3.5** | Wave 2 |
| 7 | **Logistics & Transport** | 3 | 4 | 3 | 130,000 | **3.2** | Wave 3 |
| 8 | **Automotive (parts/service)** | 4 | 4 | 3 | 115,000 | **3.6** | Wave 2 |
| 9 | **Healthcare (clinics/labs)** | 2 | 4 | 3 | 95,000 | **2.8** | Wave 3 |
| 10 | **Hospitality (hotels/F&B)** | 2 | 4 | 3 | 88,000 | **2.7** | Wave 3 |
| 11 | **Education (private schools)** | 2 | 3 | 4 | 78,000 | **2.2** | Wave 4 |
| 12 | **Agriculture** | 3 | 4 | 4 | 92,000 | **2.7** | Wave 4 |
| 13 | **Government / public sector** | 3 | 3 | 5 | 600,000 | **2.3** | Wave 4 |

## 4.3 Tier 1 — beachhead industries (Years 1–2)

### Distribution & Wholesale — **rank 1**

**Why first.** Egypt's economy is a trading economy. Distribution is the single largest population of
mid-size formal companies, and the pain is exactly what a general ERP solves — no vertical
development required.

- **Pain:** multi-warehouse stock accuracy, credit-limit control, collections ageing, supplier price
  lists that change monthly, batch/expiry tracking, van-sales reconciliation, and rebates that nobody
  can calculate.
- **ERP fit: 5/5.** Inventory + Purchasing + Sales + AR + AP + BI covers ~90% of need on day one.
- **Sales difficulty: 2/5.** Owner-led, fast decisions, clear ROI ("your stock variance is 6%; every
  point is EGP 900k").
- **ARPA:** EGP 105,000. **Priority: highest volume, fastest cycles, best reference density** — one
  happy distributor introduces three more, because they all know each other.

### Light Manufacturing — **rank 2**

**Why second.** Highest ARPA in Tier 1, deepest lock-in, and the module (Manufacturing) that most
competitors at our price point do badly or not at all.

- **Pain:** true product cost is unknown; WIP is invisible; production planning is on a whiteboard;
  scrap and yield are guesses; the BOM in the system does not match the BOM on the floor.
- **ERP fit: 5/5** for discrete and simple process manufacturing. Weaker for complex process (chemicals,
  pharma) — we explicitly do not chase those in Years 1–2.
- **Sales difficulty: 3/5.** Longer cycle (8–14 weeks), production manager must be won separately from
  finance.
- **ARPA:** EGP 185,000. **Priority: the value anchor of the portfolio.**

### Multi-branch Retail — **rank 3**

- **Pain:** branch-level stock and cash reconciliation, transfers, shrinkage, POS-to-GL gaps, and now
  ETA **e-receipt** compliance, which is a live, urgent, budgeted problem.
- **ERP fit: 4/5.** We are the back office; a POS integration is required (we integrate, we do not
  build a POS in Years 1–3).
- **Priority: high — e-receipt is a compliance wedge as sharp as e-invoice.**

## 4.4 Tier 2 — wave 2 (Year 2, after references exist)

**Construction & Contracting.** Highest ARPA outside enterprise (EGP 195,000) and the Projects module
maps well to cost-per-project, retentions, progress billing, and subcontractor management. Marked
down only on sales difficulty (4/5) — long cycles, chaotic data, notoriously slow payers. Enter with
a proven Projects module and strict payment terms.

**Food & Beverage production.** Manufacturing plus batch/expiry plus quality plus distribution. High
fit, high ARPA. Requires lot traceability to be genuinely solid before we sell it.

**Professional services** (agencies, engineering consultancies, law/audit firms). Low ARPA but very
short cycles, high referenceability, and — critically — **accounting firms in this category become
channel partners**, which is worth more than their subscription.

**Automotive parts & service.** Distribution mechanics plus service jobs. Good fit, decent ARPA, dense
referral network.

## 4.5 Tier 3–4 — deprioritised, and why

**Healthcare, Hospitality, Education** all share one property: the buyer's primary system is a
*vertical* system (HIS/PMS/SIS), and ERP is the secondary purchase. We would be competing on someone
else's terms and would need vertical modules we do not have. Revisit in Year 3+ via **industry
editions** (§17.7) or partner-built marketplace apps.

**Agriculture** has real pain and real money but extreme seasonality, low digital maturity, and
geographic dispersion that destroys sales efficiency.

**Government** has the highest deal values in the table and the worst everything else: tender
processes, 9–24 month cycles, payment delays measured in quarters, and requirements (local hosting,
security certification, Arabic documentation to standard) that cost more than the first deal is
worth. **Explicitly out of scope until Year 4**, at which point it becomes a partner-led motion
(§11.9), never direct.

## 4.6 Focus discipline

The most common failure mode for an ERP startup is selling to everyone and building for everyone.
**Years 1–2: three industries, no exceptions.** A prospect outside Distribution, Manufacturing, or
Retail is sold to only if (a) it is inbound, (b) it needs zero vertical work, and (c) the deal is
above EGP 80k ARR. Everything else is a "not yet," recorded in the CRM for Wave 2.

---

# 5. Competitive Landscape

## 5.1 The map

| Vendor | Class | Egypt price reality (year 1, 25 users, all-in) | Real position |
|---|---|---|---|
| **Oracle NetSuite** | Global cloud suite | USD 55k–160k (EGP 2.7M–8M) | Mid-market/enterprise. Wins on breadth + brand. Loses on price, Arabic, speed. |
| **SAP Business One** | Global mid-market | USD 45k–120k (EGP 2.2M–6M) | Manufacturing credibility. Partner-delivered, on-prem heritage, dated UX. |
| **Microsoft Dynamics 365 BC** | Global mid-market | USD 40k–110k | Strong where Microsoft stack is already in place. Partner-dependent. |
| **Odoo** | Open-core suite | EGP 250k–800k with partner | **The real competitor.** Broad, cheap licence, expensive to own. |
| **ERPNext / Frappe** | Open source | EGP 120k–450k with partner | Free licence, thin Egyptian partner base, weak Arabic, engineering-led buyers only. |
| **Zoho One / Books** | SMB cloud suite | USD 3k–12k | Strong SMB brand, cheap, great UX. Weak manufacturing/inventory depth, weak ETA. |
| **QuickBooks** | SMB accounting | USD 1k–3k | Accounting only. Not an ERP. Weak Arabic. Losing ground in Egypt. |
| **Sage** | Accounting/mid-market | EGP 80k–400k | Legacy installed base, fading. |
| **Daftra** | Regional SMB cloud | EGP 6k–40k | Arabic-native, cheap, well-known. Ceiling is low — invoicing/light accounting. |
| **Qoyod / Wafeq / Fatoora vendors** | Compliance-first SaaS | EGP 5k–35k | Solve the ETA/ZATCA problem only. Land-grab on compliance. |
| **Local Egyptian ERPs** (Al-Motakamel, Onyx, Sait, dozens of bespoke shops) | Desktop/legacy | EGP 60k–500k one-time + AMC | Deep local accounting knowledge, real installed base, terrible UX, on-prem, no roadmap. |

## 5.2 Capability comparison

Scored 1–5, from the perspective of an Egyptian company with 40 employees. This is our assessment,
and a hostile reviewer should challenge the rows where we score ourselves 5.

| Dimension | NetSuite | SAP B1 | D365 BC | Odoo | ERPNext | Zoho | QuickBooks | Sage | Daftra | Local ERPs | **Conductor** |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Usability (Arabic UI)** | 2 | 2 | 2 | 2 | 2 | 3 | 2 | 2 | 4 | 2 | **5** |
| **Usability (overall)** | 3 | 2 | 3 | 3 | 2 | 4 | 4 | 3 | 4 | 2 | **5** |
| **Speed / responsiveness** | 3 | 2 | 3 | 3 | 3 | 4 | 4 | 3 | 4 | 3 | **5** |
| **Implementation time** | 1 | 1 | 2 | 2 | 2 | 4 | 5 | 3 | 5 | 3 | **4** |
| **Total cost year 1 (EGP)** | 1 | 1 | 1 | 3 | 4 | 4 | 5 | 3 | 5 | 4 | **4** |
| **Accounting rigour / audit trail** | 5 | 5 | 5 | 3 | 3 | 3 | 3 | 4 | 2 | 4 | **5** |
| **ETA e-invoice / e-receipt** | 3 | 3 | 3 | 3 | 2 | 3 | 1 | 2 | 5 | 4 | **5** |
| **Inventory depth** | 5 | 5 | 4 | 4 | 4 | 3 | 2 | 3 | 2 | 3 | **4** |
| **Manufacturing** | 4 | 5 | 4 | 4 | 4 | 1 | 1 | 2 | 1 | 2 | **4** |
| **Reporting / BI** | 5 | 4 | 4 | 3 | 3 | 4 | 3 | 3 | 2 | 2 | **4** |
| **Workflow & approvals** | 4 | 3 | 4 | 3 | 3 | 4 | 1 | 2 | 2 | 2 | **4** |
| **Customisation without a consultant** | 2 | 1 | 2 | 2 | 2 | 4 | 3 | 2 | 3 | 1 | **4** |
| **Integrations / open API** | 5 | 3 | 4 | 4 | 4 | 5 | 4 | 3 | 3 | 1 | **3** |
| **AI assistance** | 3 | 2 | 4 | 2 | 1 | 3 | 3 | 2 | 1 | 1 | **5** |
| **Local support quality** | 2 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 4 | **5** | **5** |
| **Vendor viability / brand trust** | 5 | 5 | 5 | 4 | 3 | 4 | 5 | 4 | 3 | 3 | **2** |
| **Ecosystem / partner network** | 5 | 5 | 5 | 5 | 3 | 4 | 4 | 4 | 2 | 2 | **1** |
| **Weighted total (SMB-weighted)** | 3.2 | 2.9 | 3.2 | 3.1 | 2.8 | 3.5 | 3.0 | 2.8 | 3.3 | 2.7 | **4.2** |

**The two rows we lose, we lose badly: brand trust (2) and ecosystem (1).** They are the two things a
new entrant cannot buy. §5.6 and §10 are largely about closing them.

## 5.3 Pricing comparison — a 25-user distributor, first year, all-in

| Vendor | Licence/subscription | Implementation | Year 1 total (EGP) | Year 1 total (USD) | Year 2+ (EGP) |
|---|---:|---:|---:|---:|---:|
| Oracle NetSuite | 1,850,000 | 2,400,000 | **4,250,000** | 85,000 | 2,100,000 |
| SAP Business One | 1,300,000 | 1,900,000 | **3,200,000** | 64,000 | 620,000 (AMC) |
| Dynamics 365 BC | 1,150,000 | 1,600,000 | **2,750,000** | 55,000 | 1,250,000 |
| Odoo (Enterprise + partner) | 265,000 | 420,000 | **685,000** | 13,700 | 310,000 |
| ERPNext (partner-hosted) | 90,000 | 320,000 | **410,000** | 8,200 | 150,000 |
| Zoho One | 210,000 | 90,000 | **300,000** | 6,000 | 225,000 |
| Daftra | 28,000 | 15,000 | **43,000** | 860 | 30,000 |
| Local ERP (perpetual) | 280,000 one-time | 120,000 | **400,000** | 8,000 | 56,000 (AMC) |
| **Conductor (Growth, 25 users)** | **255,000** | **135,000** | **390,000** | **7,800** | **272,000** |

Conductor is priced **43% below Odoo's all-in year one** and **at parity with a legacy on-prem local
ERP**, while being cloud, supported, and continuously updated. Against NetSuite we are **91% cheaper**.

**The honest caveat:** we are *not* cheaper than Zoho or Daftra, and we should never try to be. Those
products serve a customer we do not want. If a prospect is choosing between Conductor and Daftra on
price, we have qualified badly.

## 5.4 Where Conductor genuinely wins

1. **Arabic-first is not a feature, it is an architecture.** Competitors bolt RTL onto an LTR product.
   Conductor's layout, terminology, number formatting, and document templates were built RTL-first and
   the English build is derived. The difference is visible in ten minutes and cannot be closed by a
   translation project.
2. **Time-to-value.** 4–8 weeks vs. 16–40 weeks. This is the claim we live or die on.
3. **Total cost in EGP, with no FX exposure for the customer.** In a market that has devalued 70% in
   four years, this is worth more than any feature.
4. **Audit-grade AI.** Everyone will have an AI copilot within 24 months. Almost nobody will have one
   whose every action is attributed, logged, reversible, and gated behind human posting. Finance
   buyers will pay for the restraint.
5. **Product quality as a wedge.** ERP is the last major software category where the incumbent
   experience is universally bad. A product that is genuinely fast and genuinely well-designed is a
   differentiator in ERP in a way it no longer is in CRM or project management.
6. **One vendor, one number to call.** Odoo/ERPNext buyers deal with a partner whose incentives are
   billable hours. Conductor is the vendor, the implementer (initially), and the support line.

## 5.5 Where Conductor genuinely loses — and what we do about it

| Weakness | Reality | Response |
|---|---|---|
| **No brand, no track record** | A CFO betting their books on a startup is taking career risk. This is the #1 lost-deal reason we should expect. | Referenceable customers first (§10 Phase 0 is entirely about this); published uptime; source-code escrow offered above EGP 200k ARR; audited financials from Year 2; big-name design partners. |
| **No partner ecosystem** | Odoo has 30+ Egyptian partners with salespeople. We have none. | §11.4 — partner programme is a Year-1 priority, not a Year-3 nicety. Target 8 active partners by end of Year 2. |
| **Functional depth vs. NetSuite/SAP** | They have 20 years of edge cases. We do not. | Stay in the segment where those edge cases don't apply. Say no to deals that need them. Publish a public "what Conductor does not do" page — it converts better than pretending. |
| **Integration breadth** | We score 3/5. Ecosystem integrations are thin. | Public API + marketplace (Year 2–3). Prioritise the five integrations that actually block deals: ETA, bank statement formats, POS, e-commerce, payroll/social-insurance filings. |
| **Manufacturing depth for process industries** | Real gap. | Don't sell there. Discrete + simple process only until Year 3. |
| **We are also the implementer** | Services revenue looks like SaaS revenue and inflates apparent scale. | Report subscription ARR and services revenue separately, always. Push services to partners (§11.4). |

## 5.6 The Odoo problem, stated plainly

**⚠️ Assumption under stress #4.** Odoo is not beatable on features and is not beatable on licence
price. It is beatable on **total cost of ownership, upgrade safety, Arabic quality, and the fact that
Odoo customers frequently dislike their partner.**

The winning motion against Odoo is not a feature comparison. It is:

> "Ask your Odoo partner what your last upgrade cost, and what the next one will cost. Ask what
> happens to your customisations. Then ask how many of your Arabic screens use the same word for
> *invoice*."

Our competitive intelligence priority in Year 1 is to build a documented library of **Odoo
migration cases** — customers who moved off Odoo to Conductor, with before/after cost and timeline.
Three such cases are worth more than any marketing spend. **Target: 5 documented Odoo migrations by
end of Year 2.**

If, after 18 months, we are consistently losing head-to-head against Odoo on deals we should win, the
strategy is wrong and the correct response is to narrow — become the best *Distribution* ERP in Egypt
rather than the best general one.

---

# 6. Positioning

## 6.1 The positioning statement

> **For Egyptian companies of 10–250 people who have outgrown their accounting package but cannot
> justify an international ERP, Conductor is the cloud ERP that goes live in six weeks and is
> genuinely built in Arabic — unlike Odoo, which needs a partner and a year, and unlike NetSuite,
> which needs a budget in dollars.**

Everything below is that sentence, aimed at a specific alternative.

## 6.2 Why Conductor instead of…

### …ERPNext

**Their buyer:** an engineering-minded owner or IT manager who values open source and low licence cost
and is willing to own the consequences.

**The pitch:** *"ERPNext is free the way a plot of land is free. You still have to build the house, and
you have to maintain it forever."*

- **Ownership cost.** ERPNext requires a technical owner permanently. When that person leaves, the
  system becomes unmaintainable. Conductor requires no technical owner.
- **Arabic.** ERPNext's Arabic is community-translated and inconsistent — a real problem when a
  finance team must agree on terminology to close a period.
- **ETA compliance.** Available via third-party apps of variable quality and unclear maintenance.
  Conductor's ETA integration is core product, maintained by us, covered by SLA.
- **Support.** Forum-based vs. contractual.

**Where we lose to ERPNext:** genuinely cost-constrained buyers with in-house engineering. Concede
those deals quickly.

### …Odoo

**Their buyer:** a mid-market company that has been sold by a partner on breadth ("everything in one
place, 40 apps").

**The pitch:** *"Odoo sells you apps. We sell you a working business in six weeks. Count the total, not
the licence."*

- **TCO.** EGP 685k vs. EGP 390k in year one (§5.3), and the gap widens with every customisation.
- **Upgrade risk.** Odoo customisations are the standard reason companies stay three versions behind.
  Conductor customers are always on current; upgrades are ours to manage, not theirs to pay for.
- **Configurability as a liability.** Odoo's flexibility means every deployment is unique and every
  new hire must be retrained on *your* Odoo. Conductor is opinionated by design.
- **Arabic and RTL quality.** Direct, demonstrable, side-by-side in a demo.
- **Partner incentive alignment.** Their partner earns more when the project takes longer. We earn
  more when it takes less — and our contract says so (§7.7, fixed-price implementation).

### …Oracle NetSuite

**Their buyer:** a CFO who wants a name nobody gets fired for choosing, usually at a company with
foreign shareholders or an eye on an exit.

**The pitch:** *"NetSuite is the right answer for a company with USD revenue. If you earn in pounds,
you are paying an FX premium for features you will never switch on."*

- **Price.** 9:1 in year one.
- **FX.** A NetSuite renewal after a devaluation is a budget crisis. Conductor's is a CPI-linked bump.
- **Utilisation.** Most Egyptian NetSuite deployments use a fraction of the platform. Sell against
  paid-for-but-unused.
- **Speed of change.** A field change through a NetSuite partner takes weeks and a change order.

**Where we lose to NetSuite:** multi-country consolidation, IFRS-heavy reporting, PE/VC-backed
companies whose investors mandate a tier-1 system. Concede these. Revisit at Year 4.

### …QuickBooks / Zoho Books / Daftra

**Their buyer:** a smaller company that needs invoicing and a ledger and nothing else.

**The pitch:** *"They are excellent until the day your stock, your production, and your projects stop
fitting in an accounting package. That day has a date, and you're near it."*

- The trigger events are specific and diagnosable: a second warehouse, a first production order, the
  first time a customer's credit limit is breached without anyone noticing, the first month-end that
  takes three weeks.
- **Positioning: we are the graduation.** This is a *sequencing* play, and it means we should be
  friendly to these products, publish migration guides, and build importers. A Daftra customer is a
  future Conductor customer, not an enemy.

### …a local Egyptian ERP

**Their buyer:** a company that values a local accountant-founder who understands Egyptian tax and
answers the phone.

**The pitch:** *"They know Egyptian accounting. So do we — and we also have a product that will still
be maintained in 2032."*

- **Cloud vs. a server in the office.** Ask what happens when the office floods, or the machine is
  stolen, or the one developer who wrote it retires.
- **Roadmap.** Ask when the last meaningful update shipped.
- **Mobile and remote access.** Usually absent or bolted on.
- **Where they beat us:** relationships, deep bespoke tax knowledge, and willingness to build anything
  for a fee. Respect this. Several of these firms should become **partners**, not casualties (§11.5).

## 6.3 The four words

Everything above compresses to four claims, in priority order. Every piece of marketing, every demo,
every deck uses these and nothing else:

1. **Fast** — live in six weeks, and the software itself is fast.
2. **Arabic** — built in Arabic, not translated into it.
3. **Trustworthy** — every transaction traceable; AI never posts on its own.
4. **In pounds** — priced in EGP, no FX shock at renewal.

## 6.4 The anti-positioning

Things we explicitly do **not** claim, because claiming them loses trust with the exact buyer we want:

- Not "AI-powered ERP." (Raises risk perception in finance buyers; also becoming table stakes.)
- Not "replaces your accountant." (Insults the person who recommends us.)
- Not "the cheapest." (Attracts customers who churn.)
- Not "everything for everyone." (Publish the gaps; it converts better.)
- Not "no-code, configure anything." (That's Odoo's pitch and it's a trap.)

---

# 7. Pricing Strategy

## 7.1 Principles

1. **Price in EGP, always.** No USD list price, no FX clause. This is a differentiator, not a
   concession.
2. **Per-user, with a platform floor.** Per-user alone punishes us on 8-person companies; platform-fee
   alone punishes the customer on 60-person ones. Both.
3. **Modules gate tiers, not add-ons.** A per-module price list is how Odoo makes buyers feel nickeled.
   Three module bundles, clearly drawn.
4. **Implementation is priced separately, fixed-price, and paid up front.** Never bundled into
   subscription — bundling hides the cost of delivery and destroys the ability to see true gross
   margin.
5. **Annual prepay is the default.** Monthly is available at a 20% premium, deliberately unattractive.
   Egyptian SMB cash behaviour favours an annual payment tied to a budget cycle, and we need the cash.
6. **Discounting is capped and structured.** Ad-hoc discounting in a young company destroys pricing
   power permanently. §7.6.

## 7.2 Subscription tiers

Prices are per named user per month, billed annually, plus a platform fee. VAT excluded.

| | **Starter** | **Growth** | **Business** | **Enterprise** |
|---|---|---|---|---|
| **Target** | Micro / first system | Small (10–49) | Medium (50–249) | 250+ / multi-entity |
| **Platform fee (EGP/yr)** | 0 | 24,000 | 60,000 | 180,000+ |
| **Per user (EGP/mo)** | 390 | 640 | 1,050 | Negotiated (≥900) |
| **Per user (USD/mo)** | 7.80 | 12.80 | 21.00 | ≥18.00 |
| **Minimum users** | 2 | 5 | 15 | 40 |
| **Included users** | — | — | — | — |
| **Typical deal size** | 3 users | 18 users | 45 users | 140 users |
| **Typical annual (EGP)** | 14,040 | 162,240 | 627,000 | 1,692,000 |
| **Storage** | 10 GB | 100 GB | 500 GB | 2 TB + (EGP 90/GB/yr) |
| **Documents/mo (ETA)** | 500 | 5,000 | 25,000 | Unlimited (fair use) |
| **API calls/mo** | — | 100k | 1M | 10M |
| **AI credits/mo** | 200 | 3,000 | 15,000 | 60,000 |
| **Environments** | Prod only | Prod | Prod + sandbox | Prod + sandbox + staging |

### Module access by tier

| Module | Starter | Growth | Business | Enterprise |
|---|:--:|:--:|:--:|:--:|
| General Ledger | ✅ | ✅ | ✅ | ✅ |
| Accounts Receivable | ✅ | ✅ | ✅ | ✅ |
| Accounts Payable | ✅ | ✅ | ✅ | ✅ |
| Sales | ✅ | ✅ | ✅ | ✅ |
| Purchasing | — | ✅ | ✅ | ✅ |
| Inventory (single warehouse) | ✅ | ✅ | ✅ | ✅ |
| Inventory (multi-warehouse, costing) | — | ✅ | ✅ | ✅ |
| Banking & reconciliation | — | ✅ | ✅ | ✅ |
| CRM | — | ✅ | ✅ | ✅ |
| Document Management | Basic | ✅ | ✅ | ✅ |
| Business Intelligence | 5 std reports | 30 std reports | ✅ Custom builder | ✅ + warehouse export |
| Workflow & approvals | — | Basic (2 levels) | ✅ Full | ✅ Full + SLA escalation |
| Fixed Assets | — | ✅ | ✅ | ✅ |
| Asset Management (maintenance) | — | — | ✅ | ✅ |
| Manufacturing | — | — | ✅ | ✅ |
| Projects | — | — | ✅ | ✅ |
| HR & Payroll | — | Add-on | ✅ | ✅ |
| Multi-entity / consolidation | — | — | — | ✅ |
| Multi-currency | — | ✅ | ✅ | ✅ |
| ETA e-invoice & e-receipt | ✅ | ✅ | ✅ | ✅ |
| Public API | — | Read-only | ✅ | ✅ |
| SSO / SAML | — | — | ✅ | ✅ |
| Audit trail export | — | ✅ | ✅ | ✅ + immutable archive |

**Note on ETA in Starter:** compliance is available at every tier, including the cheapest. Gating
compliance behind a paid upgrade would be both commercially short-sighted and ethically poor. It is
our wedge; give it away.

### Support by tier

| | Starter | Growth | Business | Enterprise |
|---|---|---|---|---|
| Channel | Email + knowledge base | Email + chat | Email + chat + phone | Dedicated CSM + phone |
| Hours | Business (Sun–Thu 9–5) | Business | Extended (Sun–Thu 8–8, Sat 10–4) | 24/7 for P1 |
| First-response SLA (P1) | 24h | 8h | 4h | 1h |
| First-response SLA (P3) | 72h | 24h | 12h | 8h |
| Uptime SLA | 99.5% (best effort) | 99.5% | 99.9% w/ credits | 99.95% w/ credits |
| Named CSM | — | — | Shared | Dedicated |
| Quarterly business review | — | — | ✅ | ✅ |
| Onboarding | Self-serve + 1 webinar | Guided (see §7.3) | Full implementation | Full programme |

## 7.3 Implementation pricing

Fixed price, scoped in writing, paid **60% on signature / 40% on go-live**. Never time-and-materials
for standard scope — T&M shifts risk to the customer and lengthens projects.

| Package | Scope | Duration | Price (EGP) | Price (USD) | Gross margin target |
|---|---|---|---:|---:|---:|
| **Self-serve** | Guided in-product setup, 1 group webinar | 1 week | 0 | 0 | n/a |
| **Launch** | Up to 5 users, 4 modules, 1 data import, 2 training sessions | 2–3 weeks | 35,000 | 700 | 55% |
| **Standard** | Up to 25 users, 7 modules, 3 data imports, 5 training sessions, 2 custom reports | 5–8 weeks | 135,000 | 2,700 | 50% |
| **Advanced** | Up to 60 users, 11 modules, full migration, 10 training sessions, 5 custom reports, 1 integration | 10–14 weeks | 385,000 | 7,700 | 45% |
| **Enterprise** | Multi-entity, unlimited modules, phased rollout, integrations, change management | 16–36 weeks | From 950,000 | From 19,000 | 40% |

**Rule:** implementation gross margin is measured and reported per project. Any project below 30%
margin triggers a scope post-mortem. Consistent sub-target margin means the packages are mispriced,
not that the team is slow.

## 7.4 Other services

| Service | Price | Notes |
|---|---|---|
| **Additional training (on-site, per day)** | EGP 9,000 | Cairo/Giza/Alex. +EGP 4,000 travel elsewhere. |
| **Additional training (remote, per 2h session)** | EGP 2,200 | |
| **Conductor Academy — certification (per person)** | EGP 4,500 | Free for partner staff. Revenue is secondary; the goal is a labour pool that knows Conductor (§14.7). |
| **Data migration (beyond package)** | EGP 18,000 per additional source system | |
| **Custom report** | EGP 6,500 each | Beyond package allowance. |
| **Custom development** | EGP 2,200/hour, 40h minimum | Deliberately expensive. See below. |
| **Custom integration (standard connector)** | EGP 45,000–120,000 | Bank formats, POS, e-commerce. |
| **Premium support upgrade** | +18% of subscription | Buys the next tier's SLA without the tier. |
| **Dedicated environment / private tenancy** | +EGP 240,000/yr | Enterprise only. |
| **Source-code escrow** | EGP 30,000/yr | Offered above EGP 200k ARR. A trust instrument, priced at cost. |
| **AI credit top-up** | EGP 350 per 1,000 credits | See §8.9. |
| **Extra storage** | EGP 90/GB/yr | |

**On custom development being expensive:** EGP 2,200/hour is above local market rate. This is
intentional. Custom development is the mechanism by which an ERP company slowly becomes a consultancy
with 30% margins and no product. Pricing it high does three things: it funds the true cost including
long-term maintenance, it pushes customers toward the standard product, and it pushes the work toward
partners. **Target: custom development never exceeds 8% of revenue.**

## 7.5 Discounts and terms

| Term | Discount | Rationale |
|---|---|---|
| Monthly billing | **+20% premium** | Discourage; protects cash. |
| Annual prepay | Baseline (0%) | The default. |
| 2-year prepay | −12% | |
| 3-year prepay | −20% | Reserved for Business/Enterprise. |
| Design partner (first 15 customers) | −40% for 24 months | In exchange for a written case study, reference calls, and product feedback commitment. **Contractual, not informal.** |
| Non-profit / educational | −30% | Small volume, good will. |
| Partner-sourced deal | −20% off list (partner margin) | §11.4 |
| Multi-entity (2nd+ legal entity) | −25% on platform fee | |

**Renewal escalation.** Every contract carries a CPI-linked uplift at renewal, **capped at 12%**. In a
15–25% inflation environment this is a below-inflation increase and reads as a concession, while
protecting real revenue. It must be in the first contract; introducing it later is a fight.

## 7.6 Discount governance

- Sales reps may discount to **−10%** without approval.
- **−10% to −20%** requires the head of sales.
- Beyond **−20%** requires the CEO and a written reason recorded in the CRM.
- **Discounts are never given on implementation fees.** If a customer needs a concession, give
  subscription months, never delivery cost — delivery cost is real cash out.

## 7.7 Marketplace revenue

From Year 2, third-party apps, connectors, industry templates, and report packs.

| Model | Conductor take | Notes |
|---|---|---|
| Paid apps by third-party developers | **20%** | Below the 30% platform standard, deliberately — we need supply, not margin, in the first three years. |
| Conductor-built premium apps | 100% | |
| Certified partner services listings | EGP 15,000/yr listing + 8% referral | |
| Integration connectors (partner-built) | 20% | |

Marketplace is **not a revenue line worth modelling before Year 3.** It is modelled at <2% of revenue
in Year 3 (§9). Its value is ecosystem lock-in (§14.9), not cash.

## 7.8 Pricing risks

- **We may be too expensive for Small and too cheap for Medium.** The Growth tier at EGP 162k/yr for
  18 users is a real number for an Egyptian company with EGP 60M revenue (0.27% of revenue — defensible,
  but it will be argued). Plan: hold price for 12 months, measure win rate by deal size, then adjust
  the platform fee (not the per-user rate — per-user changes are visible and damage trust).
- **Per-user pricing invites user-count gaming.** Companies will share logins. Mitigation: named users
  enforced technically, with a warehouse/shop-floor "operational user" at EGP 190/mo for scan-and-post
  roles who don't need financial access. This is also a genuine product need, not just an
  anti-gaming measure.
- **Price increases are hard in Egypt.** Land the CPI clause in v1 contracts. Everything else is a
  negotiation we will lose.

---

# 8. Revenue Model

## 8.1 Streams and their role

| # | Stream | Y1 % | Y2 % | Y3 % | Gross margin | Strategic role |
|---:|---|---:|---:|---:|---:|---|
| 1 | **Subscriptions** | 52% | 63% | 71% | 87% | The business. Everything else exists to grow this. |
| 2 | **Implementation** | 34% | 24% | 16% | 48% | Necessary; deliberately shrinking as a share. |
| 3 | **Training & certification** | 3% | 3% | 3% | 62% | Builds the labour pool (a moat). |
| 4 | **Consulting / advisory** | 4% | 3% | 2% | 55% | Accepted, never pursued. |
| 5 | **Custom development** | 5% | 4% | 3% | 45% | Capped at 8%. Priced to discourage. |
| 6 | **Premium support** | 1% | 2% | 2% | 78% | High margin; sells itself at Business tier. |
| 7 | **Custom integrations** | 1% | 1% | 1% | 50% | Converts to product over time. |
| 8 | **AI credits (overage)** | 0% | 0.4% | 1.0% | 55% | Real cost pass-through, small markup. |
| 9 | **Marketplace** | 0% | 0.2% | 0.8% | 90% | Ecosystem, not cash, until Year 4. |
| 10 | **Partner commissions (inbound)** | 0% | 0.2% | 0.5% | 95% | Referral fees from banks/payments partners. |
| 11 | **Data migration (beyond package)** | 0% | 0.2% | 0.4% | 45% | |
| 12 | **API usage (overage)** | 0% | 0% | 0.3% | 88% | Only matters once the ecosystem exists. |

**The shape that matters:** subscription share rising from 52% → 71% while services fall from 44% →
22%. An ERP company whose services share is *not* falling is a consultancy, and gets consultancy
multiples (1–2× revenue) instead of SaaS multiples (5–10× ARR). **This ratio is the single most
important operating metric in the plan after ARR itself**, and it is a board-level KPI.

## 8.2 Subscriptions

Recurring, annual-prepay-default, per-user + platform fee. Recognised monthly. Deferred revenue is a
balance-sheet feature we manage deliberately — annual prepay means cash collected substantially
exceeds recognised revenue in a growth year, which is what funds the growth.

**Expansion mechanics** (the source of net revenue retention >100%):
- **Seat growth** — customers grow; we estimate +11% seats/year on retained accounts.
- **Tier upgrade** — Growth → Business when Manufacturing or Projects is needed. ~14% of Growth
  accounts upgrade annually.
- **Module add-ons** — HR & Payroll as a Growth-tier add-on (EGP 180/user/mo).
- **Entity additions** — a second company under the same group.
- **Storage/AI/API overage** — small but pure margin.

Target **Net Revenue Retention: 96% Y1 → 104% Y2 → 111% Y3.**

## 8.3 Implementation

Fixed-price, sold with every Growth+ deal. Two structural intentions:

1. **It must be profitable, not a loss-leader.** A free implementation is a EGP 135,000 acquisition
   cost disguised as a discount. Target 45–55% gross margin.
2. **It must migrate to partners.** In-house delivery caps growth at hiring speed. Target mix:
   Y1 90% in-house / Y2 65% / Y3 40%. Partner-delivered projects contribute a **12% referral fee** to
   us instead of full project revenue — lower revenue, far higher margin, unlimited scale.

## 8.4 Training & certification

Two audiences: **customers** (usage, adoption, renewal) and **the labour market** (accountants,
implementers, students). The second matters more strategically — an Egyptian accountant who lists
"Conductor certified" on their CV is a distribution asset. Conductor Academy is run near break-even
on purpose; free for partner staff, EGP 4,500 for individuals, target 400 certified individuals by
end of Year 3.

## 8.5 Consulting / advisory

Process design, chart-of-accounts restructuring, costing-model design. **Accepted when asked for,
never marketed.** It is high-touch, unscalable, and competes with our own partners for the same work.
Every consulting hour we sell is an hour a partner didn't earn, which weakens the channel.

## 8.6 Custom development

EGP 2,200/h, 40h minimum, capped at 8% of revenue by policy. Any request that appears three times
across customers is escalated to product for evaluation as a standard feature — this is the mechanism
by which customer money funds roadmap.

## 8.7 Premium support & SLA upgrades

+18% of subscription for the next tier's SLA. Near-pure margin above the fixed support team cost.
Attach rate target: 20% of Business-tier accounts by Year 3.

## 8.8 Marketplace & partner commissions

**Outbound (we pay):** 20% first-year margin to partners who source deals; 12% referral fee to
partners who deliver implementations we sourced.
**Inbound (we receive):** referral commissions from banking, payments, lending, and insurance partners
when a Conductor customer takes their product. Small in Year 3 (~0.5% of revenue), potentially
material by Year 5 — an SMB that has just been approved for working capital based on Conductor data
is a valuable referral, and a 1% origination fee on EGP 5M of facilitated lending is EGP 50,000 from a
single customer.

## 8.9 AI credits

AI has **real marginal cost** — unlike every other feature we ship. Pretending otherwise is how
AI-heavy SaaS companies destroy their gross margin.

- Every tier includes a monthly credit allowance calibrated to normal use (§7.2). ~90% of customers
  should never think about credits.
- Overage: EGP 350 per 1,000 credits, at roughly a 55% gross margin on our inference cost.
- **Cost controls, non-negotiable:** hard per-tenant monthly caps; small-model routing for routine
  tasks with large-model escalation only when needed; aggressive prompt caching; batch processing for
  non-interactive work (OCR, migration mapping); and a monthly per-customer AI cost report reviewed
  by finance.
- **KPI: AI cost must stay below 4.5% of subscription revenue.** Breaching this triggers a re-pricing
  review, not a silent margin loss.

## 8.10 Revenue quality

| Metric | Y1 target | Y2 | Y3 |
|---|---:|---:|---:|
| Recurring revenue % of total | 53% | 65% | 74% |
| Gross margin (blended) | 63% | 71% | 76% |
| Gross margin (subscription only) | 84% | 86% | 87% |
| Net revenue retention | 96% | 104% | 111% |
| Gross logo retention | 84% | 88% | 91% |
| % revenue from top 5 customers | 31% | 19% | 12% |
| Annual-prepay share of new bookings | 70% | 78% | 82% |

**Customer concentration at 31% in Year 1 is a genuine risk** and is the normal shape of a young B2B
company. The mitigation is volume, not cleverness; it resolves itself by Year 2 if the plan is met and
becomes a serious problem if it is not.

---

# 9. Three-Year Revenue Forecast

## 9.1 Core assumptions

Every assumption below is a lever an investor should test.

| Assumption | Conservative | **Realistic** | Optimistic | Basis |
|---|---:|---:|---:|---|
| New customers, Year 1 | 42 | **78** | 128 | Y1 is founder-led sales + 2 reps from Q2 |
| New customers, Year 2 | 118 | **215** | 348 | 5 reps, partner channel opens |
| New customers, Year 3 | 235 | **412** | 690 | 9 reps, 8 partners producing |
| Blended new-logo ARPA Y1 (EGP) | 58,000 | **68,000** | 79,000 | Mix-weighted from §7.2 |
| ARPA growth p.a. | +6% | **+9%** | +13% | CPI uplift + mix shift to Business tier |
| Gross logo churn Y1 / Y2 / Y3 | 22/19/16% | **16/12/9%** | 12/9/7% | High Y1 is normal + Egyptian SMB mortality |
| Net revenue retention Y3 | 96% | **111%** | 122% | Seat + tier + module expansion |
| Blended CAC (EGP) | 78,000 | **58,000** | 44,000 | Fully loaded S&M ÷ new logos |
| Implementation attach rate | 72% | **80%** | 86% | Starter tier is 0-attach |
| Subscription gross margin | 80% | **86%** | 89% | |
| Blended gross margin Y3 | 69% | **76%** | 80% | Services mix dependent |
| Partner-sourced share of new logos Y3 | 18% | **32%** | 45% | The biggest swing factor in Y3 |

## 9.2 Year 1 — quarterly

Year 1 begins at commercial launch. Q1 is design-partner conversion; real selling starts in Q2.

**Customers and bookings**

| | Q1 | Q2 | Q3 | Q4 | **Y1 total** |
|---|---:|---:|---:|---:|---:|
| New customers | 9 | 15 | 24 | 30 | **78** |
| Churned customers | 0 | 1 | 3 | 5 | **9** |
| Ending customers | 9 | 23 | 44 | 69 | **69** |
| Avg new-logo ARPA (EGP) | 52,000 | 63,000 | 71,000 | 76,000 | 68,000 |
| Ending ARR (EGP) | 468,000 | 1,412,000 | 2,973,000 | 4,968,000 | **4,968,000** |
| Ending ARR (USD) | 9,360 | 28,240 | 59,460 | 99,360 | **99,360** |

**Recognised revenue (EGP)**

| | Q1 | Q2 | Q3 | Q4 | **Y1** |
|---|---:|---:|---:|---:|---:|
| Subscription (recognised) | 78,000 | 274,000 | 588,000 | 1,020,000 | **1,960,000** |
| Implementation | 405,000 | 620,000 | 890,000 | 1,105,000 | **3,020,000** |
| Training | 22,000 | 48,000 | 78,000 | 96,000 | **244,000** |
| Consulting | 30,000 | 62,000 | 105,000 | 128,000 | **325,000** |
| Custom development | 0 | 75,000 | 140,000 | 210,000 | **425,000** |
| Premium support / other | 4,000 | 12,000 | 28,000 | 46,000 | **90,000** |
| **Total revenue** | **539,000** | **1,091,000** | **1,829,000** | **2,605,000** | **6,064,000** |
| **Total revenue (USD)** | 10,780 | 21,820 | 36,580 | 52,100 | **121,280** |

**Costs (EGP)**

| | Q1 | Q2 | Q3 | Q4 | **Y1** |
|---|---:|---:|---:|---:|---:|
| Cloud infrastructure | 105,000 | 138,000 | 182,000 | 240,000 | **665,000** |
| AI inference | 24,000 | 42,000 | 68,000 | 98,000 | **232,000** |
| Delivery/implementation staff (COGS) | 380,000 | 520,000 | 690,000 | 820,000 | **2,410,000** |
| Support staff (COGS) | 90,000 | 135,000 | 210,000 | 285,000 | **720,000** |
| **Total COGS** | **599,000** | **835,000** | **1,150,000** | **1,443,000** | **4,027,000** |
| **Gross profit** | −60,000 | 256,000 | 679,000 | 1,162,000 | **2,037,000** |
| **Gross margin** | −11% | 23% | 37% | 45% | **34%** |
| Engineering payroll | 1,380,000 | 1,520,000 | 1,780,000 | 1,940,000 | **6,620,000** |
| Sales payroll + commission | 240,000 | 520,000 | 690,000 | 860,000 | **2,310,000** |
| Marketing spend | 180,000 | 320,000 | 420,000 | 480,000 | **1,400,000** |
| G&A (finance, legal, office, admin) | 340,000 | 365,000 | 395,000 | 420,000 | **1,520,000** |
| **Total opex** | **2,140,000** | **2,725,000** | **3,285,000** | **3,700,000** | **11,850,000** |
| **EBITDA** | **−2,200,000** | **−2,469,000** | **−2,606,000** | **−2,538,000** | **−9,813,000** |
| **EBITDA (USD)** | −44,000 | −49,380 | −52,120 | −50,760 | **−196,260** |

**Year 1 blended gross margin of 34% is the honest number and it is bad.** It is bad because Year 1 is
34% services revenue at 48% margin, plus a delivery team sized ahead of demand, plus infrastructure
that doesn't yet amortise. Anyone showing 70%+ gross margin in year one of an ERP business is either
not doing implementations or is hiding their delivery cost in opex. This improves structurally, not
by effort — see Y2/Y3.

## 9.3 Year 2 and Year 3 — annual

| (EGP) | **Year 1** | **Year 2** | **Year 3** |
|---|---:|---:|---:|
| **Customers** | | | |
| New customers | 78 | 215 | 412 |
| Churned | 9 | 26 | 61 |
| **Ending customers** | **69** | **258** | **609** |
| Gross logo churn | 16% | 12% | 9% |
| Net revenue retention | 96% | 104% | 111% |
| Blended ARPA (ending) | 72,000 | 82,000 | 93,000 |
| **Ending ARR** | **4,968,000** | **21,156,000** | **56,637,000** |
| **Ending ARR (USD)** | **99,360** | **423,120** | **1,132,740** |
| **Revenue** | | | |
| Subscription | 1,960,000 | 11,850,000 | 35,900,000 |
| Implementation | 3,020,000 | 4,510,000 | 8,090,000 |
| Training & certification | 244,000 | 565,000 | 1,520,000 |
| Consulting | 325,000 | 560,000 | 1,010,000 |
| Custom development | 425,000 | 750,000 | 1,520,000 |
| Premium support | 90,000 | 375,000 | 1,010,000 |
| AI credits / API / storage overage | 0 | 95,000 | 660,000 |
| Marketplace + partner commissions | 0 | 75,000 | 660,000 |
| **Total revenue** | **6,064,000** | **18,780,000** | **50,370,000** |
| **Total revenue (USD)** | **121,280** | **375,600** | **1,007,400** |
| **COGS** | | | |
| Cloud infrastructure | 665,000 | 1,510,000 | 3,120,000 |
| AI inference | 232,000 | 640,000 | 1,590,000 |
| Delivery staff | 2,410,000 | 3,180,000 | 4,750,000 |
| Support staff | 720,000 | 1,760,000 | 3,020,000 |
| **Total COGS** | **4,027,000** | **7,090,000** | **12,480,000** |
| **Gross profit** | **2,037,000** | **11,690,000** | **37,890,000** |
| **Gross margin** | **34%** | **62%** | **75%** |
| **Operating expenses** | | | |
| Engineering | 6,620,000 | 11,400,000 | 17,900,000 |
| Sales | 2,310,000 | 6,850,000 | 14,200,000 |
| Marketing | 1,400,000 | 3,900,000 | 7,600,000 |
| G&A | 1,520,000 | 3,150,000 | 5,800,000 |
| **Total opex** | **11,850,000** | **25,300,000** | **45,500,000** |
| **EBITDA** | **−9,813,000** | **−13,610,000** | **−7,610,000** |
| **EBITDA (USD)** | **−196,260** | **−272,200** | **−152,200** |
| **EBITDA margin** | −162% | −72% | −15% |
| **Headcount (end of year)** | 21 | 42 | 71 |

## 9.4 Unit economics

| Metric | Year 1 | Year 2 | Year 3 | Note |
|---|---:|---:|---:|---|
| Blended CAC (EGP) | 47,600 | 49,800 | 52,900 | (S&M spend) ÷ new logos |
| Blended CAC (USD) | 952 | 996 | 1,058 | |
| First-year ARPA (EGP) | 68,000 | 76,000 | 84,000 | |
| **CAC payback (months, on gross profit)** | **14.7** | **10.2** | **8.4** | Subscription GM basis |
| Avg customer lifetime (yrs) | 6.3 | 8.3 | 11.1 | = 1 / gross churn |
| **LTV (EGP, gross-profit basis)** | 368,000 | 542,000 | 812,000 | ARPA × GM × lifetime, NRR-adjusted |
| **LTV : CAC** | **7.7 : 1** | **10.9 : 1** | **15.4 : 1** | |

**These LTV:CAC ratios are suspiciously good and should be discounted.** Two reasons: (a) lifetime
derived from a churn rate we have not yet observed over a full cycle — an 11-year implied lifetime for
an Egyptian SMB is not credible, and we cap the modelled lifetime at 5 years for internal planning,
which brings Year-3 LTV:CAC to **7.0:1**; (b) CAC excludes founder time in Year 1, which is real
cost. **The defensible claim is LTV:CAC above 4:1 with CAC payback under 12 months by Year 2** — still
excellent, and far more likely to survive contact with reality.

## 9.5 Three scenarios — Year 3 exit

| | Conservative | **Realistic** | Optimistic |
|---|---:|---:|---:|
| Ending customers | 341 | **609** | 1,043 |
| Ending ARR (EGP) | 27,900,000 | **56,637,000** | 109,200,000 |
| Ending ARR (USD) | 558,000 | **1,132,740** | 2,184,000 |
| Y3 revenue (EGP) | 26,400,000 | **50,370,000** | 92,800,000 |
| Y3 gross margin | 69% | **75%** | 80% |
| Y3 EBITDA (EGP) | −18,200,000 | **−7,610,000** | +4,900,000 |
| Cumulative cash burn (EGP) | −44,600,000 | **−31,030,000** | −19,400,000 |
| Cumulative burn (USD) | −892,000 | **−620,600** | −388,000 |
| Months to EBITDA break-even | 52 | **41** | 32 |
| Capital required (USD, incl. buffer) | 2.2M | **1.5M** | 1.0M |

**The Conservative case still produces a real company** — USD 558k ARR, 341 customers, a working
partner channel — but requires a bridge round or a deliberate slowdown into profitability at ~USD
700k ARR. That optionality is why the plan is designed around a Conservative-case runway.

## 9.6 Sensitivity — what actually moves the outcome

Year-3 ARR impact of a single variable moving, all else held:

| Variable | Change | Y3 ARR impact |
|---|---|---:|
| Implementation time 6 wk → 12 wk | +6 weeks | **−19%** (delivery capacity caps sales) |
| Partner-sourced logos 32% → 12% | −20pp | **−17%** |
| Gross churn 9% → 16% | +7pp | **−14%** |
| Blended ARPA −15% | −15% | **−15%** |
| Sales rep productivity −25% | −25% | **−21%** |
| EGP devaluation 30% | −30% | **−3% in EGP, −27% in USD** |
| ETA mandate enforcement stalls | — | **−11%** (loses the primary wedge) |

**Two conclusions.** First, **delivery capacity and the partner channel matter more than sales
headcount** — a fact that should shape hiring order (§10). Second, **currency is the largest single
threat to USD-denominated returns and we cannot mitigate it operationally**, only by eventually
earning in SAR/AED (§17).

---

# 10. Go-To-Market Strategy

## 10.1 Overview

| | **Phase 0** | **Phase 1** | **Phase 2** | **Phase 3** |
|---|---|---|---|---|
| Name | Design partners | Launch | Scale | Expansion |
| Timing | Months −6 to 0 | Months 1–12 (Y1) | Months 13–30 (Y2–Y3H1) | Months 31–48 (Y3H2–Y4) |
| Motion | Founder-led, hand-delivered | Founder + first reps | Inside sales + partners | Partner-led + second country |
| Customers added | 15 | 78 | 400 | 800+ |
| Exit ARR (EGP) | ~800k | 4.97M | 40M | 110M+ |
| Headcount | 12 | 21 | 55 | 95 |
| Core question answered | *Does it work?* | *Will they pay?* | *Does it repeat?* | *Does it travel?* |

## 10.2 Phase 0 — Design partners (pre-launch, 6 months)

**Goal:** 15 real companies running real books on Conductor, with the right to publish what happened.
Not pilots. Not trials. **Production, month-end closed, ETA invoices filed.**

**Actions**
- Recruit 15 design partners: 6 distribution, 5 manufacturing, 4 retail. Sourced from founder network,
  accounting-firm introductions, and industry associations (Federation of Egyptian Industries chambers,
  Chamber of Commerce sector divisions).
- Terms: **−40% for 24 months** in exchange for a signed commitment to a case study, three reference
  calls, and a monthly feedback session. Written, not informal.
- Implement each personally. The founders do the first ten implementations. This is not a scaling
  strategy; it is the only way to learn where the product actually breaks.
- Instrument everything: time-to-go-live, hours per module, every support question, every place a
  consultant had to intervene.
- Build the **implementation playbook** from these 15 projects. This document is the asset Phase 1
  depends on.
- Close month-end successfully at 10+ partners. **This is the gate to Phase 1.** An ERP that has not
  closed a month is not an ERP.

**KPIs**

| KPI | Target |
|---|---|
| Design partners live in production | 15 |
| Successful month-end closes | ≥10 |
| Median time-to-go-live | ≤ 8 weeks (target 6) |
| Implementation hours per project | ≤ 210 |
| P1 defects at go-live | 0 |
| Written case studies | ≥ 6 |
| Willing to give a reference call | ≥ 12 |
| ETA invoices successfully filed | > 25,000 |

**Hiring (to 12):** 5 engineers, 1 designer, 2 implementation consultants, 1 support, 1 finance/ops,
2 founders.
**Marketing:** none paid. Content foundation only — 20 deep articles on ETA compliance, Egyptian
accounting practice, and inventory costing. SEO takes 6–9 months to work; start it before you need it.
**Exit criteria:** 10 closed month-ends, ≤8-week median go-live, 6 case studies, NPS ≥ 40.

## 10.3 Phase 1 — Launch (Year 1)

**Goal:** prove that companies who don't know the founders will pay full price.

**Actions**
- **Public launch** anchored on case studies, not features. The launch asset is
  *"How Nile Distribution closed their month in 3 days instead of 19"* — not a product tour.
- Hire **2 account executives** (Q2) with mid-market Egyptian software experience — ideally from
  Odoo partners, ERP resellers, or Daftra. They bring pipeline and pattern recognition.
- Founder remains lead salesperson for all deals above EGP 150k ARR through Q4. Founder-led sales in
  year one is not a failure to delegate; it is how the pitch gets debugged.
- **Compliance-led demand generation.** Every ETA deadline, every new e-receipt phase, is a content
  and webinar moment. Own the "what does the new ETA rule mean for you" search results in Arabic.
- **Accounting firm programme launches** (§11.5). Target 25 firms signed, 6 producing referrals.
- Build the **Conductor Academy** v1 — free courses, paid certification.
- Ship the **public API v1** and 3 core integrations (2 bank statement formats, 1 POS).
- Publish **status.conductor.eg** with real uptime from day one. Radical transparency about downtime
  is a trust-building asset for a vendor with no brand.

**KPIs**

| KPI | Q1 | Q2 | Q3 | Q4 |
|---|---:|---:|---:|---:|
| New customers | 9 | 15 | 24 | 30 |
| Ending ARR (EGP) | 468k | 1.41M | 2.97M | 4.97M |
| Qualified pipeline (EGP ARR) | 2.1M | 4.8M | 8.5M | 13.0M |
| Win rate (qualified → closed) | 22% | 26% | 29% | 32% |
| Median sales cycle (days) | 74 | 68 | 61 | 55 |
| Median time-to-go-live (weeks) | 8 | 7 | 6 | 6 |
| CAC (EGP) | 61k | 52k | 46k | 42k |
| Gross logo churn (annualised) | — | 18% | 17% | 16% |
| NPS | 42 | 45 | 47 | 50 |
| Accounting firms signed | 4 | 11 | 19 | 25 |
| Organic sessions/month | 3,500 | 9,000 | 21,000 | 38,000 |

**Hiring to 21:** +2 AEs, +1 SDR, +3 engineers, +2 implementation consultants, +1 support, +1 content
marketer, +1 partner manager.
**Marketing spend:** EGP 1.4M — 35% content/SEO, 25% paid search (Arabic ETA and ERP keywords), 15%
events, 15% webinars, 10% video.
**Exit criteria:** 69 customers, EGP 4.97M ARR, CAC payback < 15 months, 3 partner-sourced deals
closed, ≥8 published case studies.

## 10.4 Phase 2 — Scale (Year 2 – H1 Year 3)

**Goal:** make it repeatable without the founders, and shift delivery to partners.

**Actions**
- **Build the inside-sales machine.** SDR team (4), AE team (6), defined territories by industry, not
  geography. Documented qualification (MEDDICC-lite adapted for Egyptian committee dynamics).
- **Partner channel becomes primary growth engine.** Recruit and certify 8 implementation partners.
  Partner economics: 20% margin on sourced deals, 12% referral on delivered ones, free certification,
  co-marketing budget, and a genuine commitment not to compete with them on services.
- **Launch the marketplace** — third-party apps, industry templates, report packs.
- **Wave 2 industries** — construction, F&B, automotive, professional services. Each needs 2 reference
  customers and an industry-specific landing page and template pack before the sales team is allowed
  to prospect there.
- **Product: depth over breadth.** No new modules. Deepen manufacturing costing, BI, workflow, mobile.
- **Ship mobile apps** (approvals, sales rep, warehouse scanning) — the single most-requested item from
  design partners.
- **ISO 27001 certification** begins. It is a 9–12 month process and it gates Enterprise deals in
  Year 3.
- **Saudi market research and regulatory work** begins in H2 Year 2. ZATCA Fatoora compliance is the
  entry ticket and takes ~6 months to build and certify.

**KPIs**

| KPI | Year 2 | Y3 H1 |
|---|---:|---:|
| New customers | 215 | 175 |
| Ending ARR (EGP) | 21.2M | 35.0M |
| Partner-sourced share of new logos | 18% | 27% |
| Partner-delivered share of implementations | 35% | 52% |
| Gross margin | 62% | 71% |
| Net revenue retention | 104% | 108% |
| Median time-to-go-live (weeks) | 5 | 5 |
| CAC payback (months) | 10.2 | 9.1 |
| Certified partner consultants | 24 | 48 |
| Marketplace apps live | 6 | 15 |
| Organic sessions/month | 95,000 | 165,000 |

**Hiring to 55:** sales +11, implementation +6, support +5, engineering +9, marketing +3, partner
team +2, finance/legal +2.
**Marketing spend:** EGP 3.9M Y2 — 30% content/SEO, 22% paid, 18% events/webinars, 15% partner
co-marketing, 15% video/community.
**Exit criteria (end Y2):** 258 customers, EGP 21.2M ARR, 8 certified partners, ≥30% of new logos
partner-influenced, gross margin > 60%, NRR > 100%.

## 10.5 Phase 3 — Expansion (H2 Year 3 – Year 4)

**Goal:** prove the model travels, and reach the Series A story.

**Actions**
- **Saudi Arabia entry.** Riyadh office, 1 country manager, 2 AEs, 2 implementation consultants, and
  **2 local implementation partners signed before the office opens.** ZATCA-certified product.
  Pricing at SAR levels — roughly 2.6× Egypt ARPA. Target 60 Saudi customers by end of Year 4.
- **Enterprise motion opens** — but only with ISO 27001 complete, 3 lighthouse mid-market references,
  and a dedicated enterprise AE. Multi-entity consolidation must be production-proven first.
- **Banking and payments layer** — embedded payment collection, bank feeds via API, and a
  working-capital referral partnership with 1–2 Egyptian banks or fintechs.
- **Industry editions** — Distribution Edition, Manufacturing Edition, Construction Edition:
  pre-configured chart of accounts, workflows, reports, and KPIs. This cuts implementation further
  and is the mechanism for entering Wave 3 industries at low marginal cost.
- **Developer ecosystem** — public API v2, webhooks, sandbox, documentation, a small developer fund.
- **UAE and Jordan** research; no commitment before Saudi shows repeatability.

**KPIs**

| KPI | Year 3 H2 | Year 4 target |
|---|---:|---:|
| New customers | 237 | 800 |
| Ending ARR (EGP) | 56.6M | 128M |
| Ending ARR (USD) | 1.13M | 2.56M |
| Saudi customers | 8 | 60 |
| Non-Egypt revenue share | 3% | 17% |
| Partner-sourced logos | 32% | 44% |
| Gross margin | 75% | 79% |
| EBITDA margin | −15% | +4% |
| NRR | 111% | 116% |

**Hiring to 95:** Saudi team (8), enterprise sales (4), engineering (+14), platform/API (+4),
security/compliance (+2), remainder in CS and support.
**Exit criteria:** USD 1.5M+ ARR run-rate, 2 countries, >40% partner-sourced, NRR >110%, approaching
EBITDA break-even — the Series A profile.

## 10.6 The single biggest GTM risk

**Delivery capacity, not demand generation, is the binding constraint** (§9.6). A company that sells
40 implementations it can only deliver 25 of will destroy its reputation in a market that runs on
reputation. **The rule for Years 1–2: never sell more than 80% of delivery capacity in a given
quarter.** If pipeline exceeds capacity, extend the go-live date and say so honestly, or route to a
partner. Never compress the project.

---

# 11. Sales Strategy

## 11.1 The motion mix over time

| Channel | Y1 % of new ARR | Y2 % | Y3 % |
|---|---:|---:|---:|
| Founder-led direct | 55% | 18% | 6% |
| Inside sales (SDR → AE) | 31% | 42% | 38% |
| Accounting-firm referral | 9% | 16% | 14% |
| Implementation partners | 4% | 18% | 32% |
| Self-serve (Starter) | 1% | 3% | 4% |
| Enterprise / tenders | 0% | 3% | 6% |

## 11.2 Direct sales (field, mid-market and above)

For deals above **EGP 150k ARR** — Medium segment and complex Small.

**Process, 6 stages, with exit criteria that are actually enforced:**

| Stage | Exit criterion | Typical duration |
|---|---|---|
| 1. Qualified | Budget confirmed, ERP timeline within 6 months, 3 pains named, decision process mapped | 1 week |
| 2. Discovery | Written pain document reviewed and confirmed by the financial manager | 1–2 weeks |
| 3. Tailored demo | Demo built on the prospect's own data (a real customer list, a real BOM). **No generic demos above EGP 150k.** | 1–2 weeks |
| 4. Proposal + implementation plan | Fixed price, fixed scope, named go-live date, named consultants | 1 week |
| 5. Validation | Reference call with a same-industry customer; security/technical review | 1–3 weeks |
| 6. Close | Signature, 60% implementation fee collected | 1–2 weeks |

**Rules.**
- **Never demo before discovery.** The single most common failure in ERP sales is demoing features to
  someone whose problem you haven't heard.
- **Always sell the implementation plan, not the software.** The buyer's real fear is a failed project,
  not a missing feature.
- **Always identify the auditor.** The company's external auditor or accounting firm has an informal
  veto and is almost never in the room. Get to them early; they are also a channel (§11.5).
- **Qualify out loudly.** A deal we cannot deliver well is worth less than no deal.

**AE targets:** EGP 2.4M new ARR/year at full ramp (ramp = 4 months). Quota-to-OTE ratio ~5:1.
OTE EGP 480k (base 288k / variable 192k).

## 11.3 Inside sales

For deals **EGP 40k–150k ARR** — the Small-segment volume engine.

- **SDRs** work outbound lists built from ETA registration data, industry association directories,
  chamber-of-commerce listings, and import/export records. Target: 22 qualified meetings/month per SDR.
- Fully remote sales cycle: video discovery, video demo, e-signature. Cuts cycle time ~35% versus
  field sales, which matters in a country where crossing Cairo costs three hours.
- **AE targets:** EGP 1.5M new ARR/year, 55-day average cycle, 12 concurrent opportunities.
- **The playbook is a written asset**, not tribal knowledge: 14 objection-handling scripts, 6 industry
  discovery guides, a ROI calculator in Arabic, and a competitive battlecard per competitor, all
  reviewed quarterly.

## 11.4 Implementation partner channel — **the most important channel**

Egypt has a real, existing population of ERP implementers: Odoo partners, SAP B1 partners, Microsoft
partners, and independent consultancies. Many are dissatisfied — thin margins, difficult vendor
relationships, products their customers complain about.

**The offer:**

| Element | Terms |
|---|---|
| Deal margin (partner-sourced) | 20% of year-1 subscription, 12% recurring |
| Implementation revenue | **100% to the partner** |
| Referral fee (we source, they deliver) | 12% of implementation value to us; rest to them |
| Certification | Free for partner staff, 5 days, Conductor-run |
| Leads | Qualified leads routed to certified partners by industry and region |
| Marketing | Co-funded campaigns, listing in the partner directory |
| **Non-compete commitment** | **We will not bid against a certified partner on services in their registered accounts.** |

**The last row is the whole programme.** Odoo's partners compete with Odoo's own direct sales. SAP's
partners compete with SAP. A credible, contractual commitment not to take services revenue away from
partners is our single strongest recruiting argument, and it costs us services revenue we didn't want
anyway (§8.5).

**Targets:** 3 partners signed by end Y1 · 8 certified and producing by end Y2 · 18 by end Y3 ·
32% of new logos partner-sourced by Y3.

**Partner tiers:** Registered (referral only) → Certified (2+ certified consultants, 3 deployments) →
Gold (8+ consultants, 12 deployments, dedicated support channel, 25% margin).

**Risk:** partners deliver badly and the brand suffers. Mitigation: certification with real
assessment, mandatory Conductor QA sign-off on the first three projects per partner, customer CSAT
tracked per partner, and de-certification for partners below 70% CSAT.

## 11.5 Accounting firms — the trust channel

The external accountant is the most influential unpaid advisor in the Egyptian SMB. They see 20–80
clients. They are consulted before every system decision. And they carry the pain of bad client data
directly.

**The offer:**
- **Free Conductor for the firm's own books**, permanently, up to 10 users.
- **A multi-client console** — one login, all client books, cross-client reporting. This is a genuine
  product build (Year 2) and is what makes the channel work.
- **20% of year-1 subscription** for referred clients, 10% recurring.
- **Free certification and a listing** in the partner directory.
- Co-branded content: ETA guides, month-end checklists, tax-calendar tools.

**Targets:** 25 firms by end Y1, 90 by end Y2, 220 by end Y3. 14% of new ARR by Year 3.

**Why this works better than in other markets:** Egyptian SMBs delegate more of their financial life to
their accountant than their US or European equivalents. Winning the accountant is close to winning the
client.

## 11.6 Referral programme (customers)

- Existing customer refers a company that becomes a paying customer → **2 months free** for the
  referrer, **10% off year one** for the referred.
- Capped at 6 months of free service per referrer per year.
- Target: 12% of new logos by Year 3.
- **Not a growth strategy** — a satisfaction indicator. If referrals are low, the product isn't good
  enough, and no incentive fixes that.

## 11.7 Affiliate programme

Bloggers, YouTube channels, accounting educators, business consultants. **15% of year-1 subscription,
90-day cookie, self-serve dashboard.** Small (3% of new logos), cheap to run, and useful for building
Arabic-language content mass we could not produce ourselves. Launched Year 2.

## 11.8 Resellers

Distinct from implementation partners: resellers sell but do not implement — typically IT hardware and
networking companies with existing SMB relationships. **12% of year-1 subscription, no recurring**, and
the implementation is delivered by us or a certified partner. Low priority; opportunistic only.

## 11.9 Government tenders

**Not before Year 4, and never direct.** When we enter, it is exclusively as a subcontractor to an
established Egyptian systems integrator who owns the tender relationship, the bid-bond capacity, and
the payment-delay tolerance. Prerequisites: ISO 27001, local data residency, Arabic documentation to
government standard, 3 years of audited financials, and a balance sheet that can survive 9-month
receivables. Government deal values (EGP 600k+ ARR) are attractive; government cash-flow behaviour
kills young companies.

## 11.10 Enterprise sales

Opens H2 Year 3. Dedicated AE, solution architect, and security/compliance support. 9–18 month cycles,
formal RFPs, POCs, procurement, legal. Requirements gate: ISO 27001, penetration test report, DPA
template, source-code escrow, audited financials, a 99.95% SLA with credits, and 3 referenceable
mid-market customers of comparable complexity.

**Discipline:** maximum 6 active enterprise opportunities at once, and no enterprise commitment that
requires more than 20% of a quarter's engineering capacity. Enterprise deals that bend the roadmap
are how mid-market ERP companies die.

## 11.11 Sales enablement assets (built in Phase 0–1, maintained forever)

1. ROI calculator (Arabic + English) — inventory variance, DSO reduction, close-time reduction, headcount avoidance.
2. Competitive battlecards — 8, one per competitor, updated quarterly with real lost-deal data.
3. Industry discovery guides — 6, one per priority industry.
4. Reference customer library — by industry, size, and modules, with pre-agreed reference availability.
5. Standard implementation plan template — the artefact that actually closes deals.
6. Security & compliance pack — architecture, backup policy, DPA, ETA certification, uptime history.
7. "What Conductor does not do" — a public, honest gap list. It builds more trust than it costs deals.

---

# 12. Marketing Strategy

## 12.1 Strategic frame

Conductor has no brand, in a category where brand is the primary risk-reducer. Marketing's job for
three years is exactly one thing: **manufacture credibility faster than the sales team burns it.**

That produces three priorities, in order:
1. **Proof** — case studies, references, published uptime, real numbers.
2. **Authority** — own Arabic-language ERP and Egyptian-accounting search results and video.
3. **Reach** — paid, events, community.

Most startups run these in reverse and wonder why the leads don't convert.

**Budget:** EGP 1.4M (Y1) → 3.9M (Y2) → 7.6M (Y3). ~23% of revenue Y1, 21% Y2, 15% Y3.

| Channel | Y1 | Y2 | Y3 | Primary KPI |
|---|---:|---:|---:|---|
| Content & SEO | 35% | 30% | 26% | Organic sessions → MQL |
| Paid search | 25% | 18% | 15% | CPL, MQL→SQL rate |
| Events & webinars | 15% | 18% | 19% | Meetings booked |
| Video / YouTube | 10% | 12% | 13% | Watch time, assisted conversions |
| Partner co-marketing | 5% | 15% | 18% | Partner-sourced pipeline |
| Paid social (LinkedIn/Facebook) | 8% | 5% | 6% | Cost per SQL |
| Community & open source | 2% | 2% | 3% | Developer signups, GitHub stars |

## 12.2 SEO — the compounding asset

Arabic-language business software search in Egypt is **under-served to a degree that is hard to
believe.** Most competitors publish machine-translated Arabic or none. This is the highest-ROI channel
available and it is available now.

**Three content clusters:**

| Cluster | Example queries (translated) | Intent | Volume | Competition |
|---|---|---|---|---|
| **Compliance** | "how to register for ETA e-invoice", "e-invoice rejection codes", "e-receipt requirements" | High urgency, low commercial intent, **enormous trust value** | High | Low |
| **Accounting practice** | "inventory costing methods", "how to calculate depreciation", "month-end close checklist" | Educational; builds the accountant relationship | Medium | Low |
| **Category & comparison** | "best ERP in Egypt", "Odoo alternatives", "ERP price Egypt", "cloud accounting Egypt" | High commercial intent | Low-medium | Medium |

**Programme:** 8 deep articles/month in Arabic, 3 in English, from month −6. Every article reviewed by
a practising Egyptian accountant before publication — accuracy is the moat here; a single wrong tax
statement destroys the authority the whole channel depends on.

**Free tools as link magnets and lead capture:** ETA invoice validator, depreciation calculator,
Egyptian payroll and social-insurance calculator, VAT calculator, inventory-valuation comparator.
These get linked, shared, and used — and each one is a soft demonstration that we understand Egyptian
accounting.

**Targets:** 38k organic sessions/month by end Y1 · 95k by end Y2 · 165k by end Y3.
**Realistic expectation:** near-zero traffic for months 1–5, meaningful from month 7, dominant from
month 14. Anyone promising faster is guessing.

## 12.3 Content marketing

| Asset | Cadence | Purpose |
|---|---|---|
| Case studies | 2/quarter | The highest-converting asset we own. Always with numbers. |
| Industry guides | 1/quarter | "ERP for Egyptian Distributors" — gated, generates MQLs |
| ETA compliance handbook | Annual, updated | The definitive Arabic reference. Free, ungated, link magnet. |
| Benchmark report | Annual from Y2 | "The State of Egyptian SMB Finance" — anonymised, aggregated Conductor data. Press-worthy, and a moat that grows with the customer base. |
| Newsletter | Weekly | Accounting/tax/business news for Egyptian finance managers. Owned audience. |
| Blog | 8–11/month | SEO engine |

**The benchmark report deserves emphasis.** By Year 3 we will hold anonymised operational data on 600
Egyptian companies — real DSO, real inventory turns, real margins by sector. Nobody else has this.
Published annually with proper anonymisation and consent, it is simultaneously the best PR asset, the
best SEO asset, and a genuine public good.

## 12.4 YouTube & video

Arabic B2B software video in Egypt is essentially empty. Four series:

1. **Conductor in 3 minutes** — one feature, one problem, one solution. 2/week.
2. **Accounting explained** — depreciation, WIP, provisions, closing entries, taught by an accountant,
   in Egyptian Arabic. This builds the accountant audience, which is the referral channel.
3. **ETA compliance** — every regulation update, explained within 72 hours. Timeliness is the value.
4. **Customer stories** — filmed on site, in the warehouse, on the factory floor. Credibility.

**Targets:** 3,000 subscribers end Y1, 22,000 end Y2, 65,000 end Y3.

## 12.5 LinkedIn

Where Egyptian financial managers, CFOs, and ERP consultants actually are.

- **Founder-led posting, 4×/week.** Building in public, real numbers, honest failure posts. Founder
  brand converts better than company brand for a company with no brand.
- Company page: case studies, product updates, hiring.
- Paid: targeted at Finance Manager / Financial Controller / CFO / Operations Manager titles at
  Egyptian companies of 50–500 employees. Expect EGP 900–1,600 per qualified lead.
- **Recruiting is a marketing channel too** — visible engineering culture posts reduce hiring cost.

## 12.6 Facebook

Still the dominant platform for Egyptian SMB owners, especially outside Cairo. Different audience from
LinkedIn: the owner, not the finance manager.

- Groups: Egyptian accountants, importers, manufacturers, distributors. **Participate genuinely for
  months before mentioning the product.** Egyptian business groups are ruthless about self-promotion.
- Paid: video-first creative, Arabic, interest and behaviour targeting.
- Lead-gen forms with immediate WhatsApp follow-up. **WhatsApp response time is the primary conversion
  variable in this market** — target under 4 minutes during business hours.

## 12.7 Google Ads

- **Arabic keywords first**, English second. Lower CPCs, higher intent, negligible competition.
- Bid on competitor terms: "Odoo Egypt", "NetSuite price", "ERPNext Arabic" — cheap, high-intent.
- Compliance keywords ("ETA e-invoice system") are high-volume and low-intent; route to content, not
  to demo requests, and capture email.
- **Target CPL EGP 400–900; target CAC from paid EGP 34,000–58,000.**
- Discipline: paid search is capped at 25% of budget and reduced as organic compounds. Paid channels
  that scale linearly are not a strategy.

## 12.8 Events

| Event type | Frequency | Cost/event (EGP) | Purpose |
|---|---|---:|---|
| Industry association sessions (FEI chambers, chambers of commerce) | Monthly | 25,000 | Highest-quality lead source in Egypt. Underrated. |
| Cairo ICT / Egypt tech expos | Annual | 180,000 | Presence and credibility. Modest lead yield. |
| Conductor customer day | Annual from Y2 | 250,000 | Community, references, upsell |
| Accounting-firm breakfasts | Quarterly | 35,000 | Channel recruitment |
| Governorate roadshows (Alex, Mansoura, Mahalla, 10th of Ramadan) | Quarterly from Y2 | 60,000 | Industrial-zone concentration; underserved by every competitor |

**10th of Ramadan, 6th of October, Sadat City, and Borg El Arab industrial zones deserve specific
attention** — dense concentrations of exactly our manufacturing ICP, and no competitor runs local
events there.

## 12.9 Webinars

Bi-weekly, Arabic, 45 minutes: 25 minutes of genuinely useful content, 10 minutes of product, 10
minutes Q&A.

Highest-performing topics, in order: ETA compliance updates → month-end close in under 5 days →
inventory costing → cash-flow forecasting → payroll & social insurance.

**Targets:** 180 registrants/webinar Y1 → 450 Y2. Attendance ~40%. Registrant→SQL ~6%.
Webinars are the best MQL source in B2B ERP and the cheapest per SQL. Do not skip them.

## 12.10 Community

- **Conductor Community forum** (Arabic-first) — users, partners, accountants. Public, searchable,
  which feeds SEO.
- **Accountant community** — a private group for certified accountants; monthly technical sessions.
- **Product feedback board** — public roadmap, public voting. Radical transparency; also the cheapest
  possible prioritisation research.
- **Egyptian ERP consultants group** — deliberately vendor-neutral, run by us. Recruiting ground for
  the partner channel.

## 12.11 Open source

**We are not open-sourcing the ERP.** Open-core is Odoo's and ERPNext's strategy and competing there
means competing on their terms with none of their ecosystem.

We do open-source **infrastructure** — and this is a real, if modest, strategic play:

| Component | Rationale |
|---|---|
| **ETA e-invoice client libraries** (Python, PHP, Node, .NET) | Every Egyptian developer integrating with ETA needs this. Becomes the default; every install is a brand impression on a technical buyer. |
| **Arabic/RTL React component primitives** | Genuine contribution; establishes design credibility. |
| **Egyptian accounting reference data** — chart of accounts templates, tax tables, social insurance brackets | Useful, linkable, authoritative. |
| **Conductor SDK & API clients** | Ecosystem necessity. |

**Purpose: developer mindshare and hiring, not distribution.** Budget 2–3% of marketing. Measured in
GitHub stars, package downloads, and inbound engineering applications — not in leads.

## 12.12 Email

- **Nurture** — 12-email sequence by industry, educational-first, product mention from email 5.
- **Onboarding** — 8 emails over 30 days, milestone-triggered, not time-triggered.
- **Product updates** — monthly. Every release, named, with a video.
- **Newsletter** — weekly Egyptian finance/tax news to an owned list. Target 18,000 subscribers by end
  Y3.
- Discipline: Arabic-first, mobile-first, and honest subject lines. Egyptian B2B open rates run
  28–38%; below 22% means the list quality has degraded.

## 12.13 What we will not do

- **No influencer marketing.** Wrong category, wrong buyer, destroys the trust positioning.
- **No aggressive outbound cold email.** Damages domain reputation and the brand; SDR calling and
  LinkedIn work better in Egypt.
- **No feature-comparison advertising against competitors by name.** Battlecards are internal.
  Publicly attacking incumbents makes a small company look smaller.
- **No "AI-powered" as a headline.** §6.4.

---

# 13. Customer Success Strategy

## 13.1 Why this section is not boilerplate

In an ERP business, customer success is not a support function — it is the **product's second half.**
The software is a capability; the outcome only exists if the customer's staff actually change how they
work. Every ERP failure story in history is a change-management failure, not a software failure.

Two numbers make this concrete. Our Year-3 plan requires **NRR of 111%** and **gross churn of 9%.**
Neither is achievable by good software alone. The difference between 16% churn and 9% churn is
approximately **EGP 8.5M of Year-3 ARR** — larger than the entire Year-1 revenue.

## 13.2 Onboarding

Onboarding begins the day the contract is signed and ends 90 days after go-live. Not at go-live —
90 days after, because the first month-end close is the real acceptance test.

| Stage | Days | Owner | Milestone |
|---|---|---|---|
| Kickoff | 0–3 | Implementation lead | Scope confirmed, project plan signed, stakeholders named, success criteria written |
| Data & configuration | 4–18 | Consultant + AI migration tooling | Chart of accounts, opening balances, master data imported and reconciled |
| Configuration review | 19–24 | Customer + consultant | Customer signs off on COA, approval workflows, document templates |
| Training | 25–32 | Trainer | Role-based training, not module-based. Each user trained on *their day*, not on the software. |
| Parallel run | 33–40 | Both | Two weeks in parallel with the old system. **Non-negotiable.** Skipping the parallel run is the #1 cause of failed go-lives. |
| Go-live | 41 | Both | Cutover, hypercare begins |
| Hypercare | 41–55 | Consultant | Daily check-in, on-site or remote presence, <2h response on everything |
| First month-end close | ~60–70 | CSM + consultant | **The real acceptance test.** Attended by us. |
| Transition to success | 90 | CSM | Handover from implementation to CSM, health baseline set |

**Instrumented milestones** (measured automatically, drive health score):
first invoice issued · first ETA submission accepted · first payment recorded · first bank
reconciliation · first inventory count posted · first period closed · 80% of licensed users logged in
within 14 days.

## 13.3 Implementation methodology

**Named "Six Weeks" and published.** The methodology is a marketing asset as much as an operating one.

Principles:
1. **Fixed scope, fixed price, fixed date.** Change requests are handled formally, priced, and never
   absorbed silently. Absorbed scope creep is how implementation margin dies.
2. **Phase 1 is always GL + AR + AP + Sales + Purchasing + Inventory.** Manufacturing, Projects,
   HR/Payroll are always Phase 2. Attempting everything at once is the classic mistake.
3. **The customer does the data cleaning, we do the mapping.** Stated in the contract with a named
   customer-side data owner. Projects fail on data, and data is 70% a customer-side problem.
4. **AI-assisted migration** — schema mapping, COA suggestion, master-data deduplication, opening
   balance reconciliation. This is where the six weeks comes from.
5. **A "definition of done" checklist signed by the customer.** Ambiguous completion is how
   implementations run for eleven months.

**Post-project review on every implementation**: actual vs. planned hours, variance causes, defects
found, and one product change proposed. This feedback loop is what pushes the median from 8 weeks to
5.

## 13.4 Training

| Programme | Audience | Format | Duration | Included in |
|---|---|---|---|---|
| Role-based onboarding | All customer users | Live, role-specific | 2–6h per role | Implementation |
| In-product guidance | All users | Contextual walkthroughs, checklists | Ongoing | All tiers |
| Conductor Academy — Foundations | Any user | Self-paced Arabic video | 6h | Free, public |
| Conductor Academy — Certified User | Power users | Self-paced + exam | 14h | EGP 4,500 |
| Conductor Academy — Certified Consultant | Partners, consultants | Live + exam | 5 days | Free for partners |
| Admin training | System admins | Live | 4h | Growth+ |
| New-hire refresh | Customer's new staff | Self-paced + quarterly live session | — | Business+ |

**The new-hire problem is underrated.** Egyptian SMB staff turnover in finance and warehouse roles is
high. A customer whose trained users all leave within 18 months will churn unless the *system* teaches
the next person. This is why in-product guidance and free public Academy content matter more than
paid training revenue.

## 13.5 Support

**Structure:** Tier 1 (generalist, ~70% resolution) → Tier 2 (module specialists, ~25%) → Tier 3
(engineering, ~5%). Arabic-first, with English available.

| Priority | Definition | Growth SLA | Business SLA | Enterprise SLA |
|---|---|---|---|---|
| P1 | System down or cannot invoice/post | 8h response / 8h target fix | 4h / 4h | 1h / 4h, 24/7 |
| P2 | Major function broken, workaround exists | 24h / 3d | 8h / 2d | 4h / 1d |
| P3 | Minor issue | 24h / 10d | 12h / 5d | 8h / 3d |
| P4 | Question / how-to | 72h | 24h | 8h |

**Channels:** in-product chat (primary), email, phone (Business+), and **WhatsApp Business** — which
will be the most-used channel in Egypt regardless of what we prefer, and should therefore be built
properly with ticket integration rather than run informally from someone's phone.

**Deflection strategy:** in-product AI assistant answering with reference to the customer's own data
and configuration. **Target 42% ticket deflection by Year 3** — the single largest lever on support
cost as customer count grows 9× in three years. Support headcount cannot scale linearly with
customers; it must scale sub-linearly or the gross margin plan fails.

## 13.6 Knowledge base

- Arabic-first, English secondary. Every article in both.
- Structured by **task** ("issue a credit note against a paid invoice"), not by module. Users search
  for what they're trying to do.
- Every support ticket resolved with a non-existent article triggers article creation. Non-optional.
- Public and indexable — it is also an SEO asset.
- Target: 400 articles by end Y1, 1,200 by end Y3; 55% self-service resolution rate by Y3.

## 13.7 Customer health score

Computed weekly, 0–100, driving proactive intervention.

| Signal | Weight | What good looks like |
|---|---:|---|
| **Active user ratio** (weekly active ÷ licensed) | 22% | > 70% |
| **Transaction volume trend** (30d vs. prior 30d) | 18% | Flat or rising |
| **Core workflow completion** (period closes on time, bank recs current) | 16% | Monthly close within 7 days |
| **Module adoption breadth** | 12% | ≥ 70% of licensed modules used |
| **Support ticket volume & sentiment** | 10% | Declining after month 3 |
| **Executive engagement** (QBR attendance, sponsor responsive) | 8% | Present |
| **Payment behaviour** | 6% | On time |
| **NPS / CSAT** | 5% | ≥ 8 |
| **Champion turnover** | 3% | No change, or successor trained |

| Score | Band | Action |
|---|---|---|
| 80–100 | Healthy | Expansion play; ask for a reference or case study |
| 60–79 | Watch | CSM outreach within 7 days; adoption plan |
| 40–59 | At risk | Escalate to head of CS; recovery plan with named owner and 30-day review |
| < 40 | Critical | Executive sponsor engagement; on-site visit; retention offer if the cause is legitimate |

**Two signals are early and predictive far beyond their weight: falling active-user ratio, and
champion turnover.** A finance manager leaving a customer is the single most reliable predictor of
churn in ERP. It should trigger a CSM call the same week, every time.

## 13.8 Renewals

- Renewal motion starts at **day 270** of a 365-day term, not day 350.
- CSM-owned below EGP 200k ARR; joint CSM + AE above.
- Every renewal conversation is framed with a **value report**: transactions processed, close-time
  improvement, DSO change, stockout reduction, hours saved. Renewals are won by evidence, not
  relationship.
- CPI uplift (capped 12%) applied automatically, communicated 90 days ahead, never as a surprise.
- Multi-year conversion offered at renewal — the highest-yield moment to move a customer to a 2- or
  3-year term.

**Targets:** gross logo retention 84% (Y1) → 88% (Y2) → 91% (Y3). Gross revenue retention runs ~3pp
above logo retention (smaller customers churn more).

## 13.9 Expansion / upsell

Triggered by signal, not by calendar:

| Trigger | Play | Typical uplift |
|---|---|---|
| Licensed users 90%+ utilised | Seat expansion | +12–20% ARR |
| First production order attempted on Growth tier | Business upgrade (Manufacturing) | +55% ARR |
| Second warehouse or branch created | Business upgrade | +45% ARR |
| Manual payroll spreadsheet detected in Documents | HR & Payroll add-on | +18% ARR |
| Second legal entity registered | Multi-entity / Enterprise | +70% ARR |
| Repeated P1 tickets outside SLA | Premium support | +18% ARR |
| API rate limits hit | Tier upgrade | +30% ARR |
| BI report requests exceed allowance | Business upgrade | +40% ARR |

**Rule: no expansion conversation with a customer whose health score is below 70.** Selling more to an
unhappy customer accelerates churn and destroys the reference.

## 13.10 NPS and voice of customer

- **In-product NPS** at day 90, then every 180 days. Target 50 (Y1) → 60 (Y3).
- **Every detractor (0–6) gets a call from a human within 48 hours.** Not an email.
- Post-implementation CSAT, post-ticket CSAT, and an annual customer advisory board (12 customers,
  meets twice yearly, sees the roadmap first).
- **Public roadmap with voting.** Customers who can see where the product is going churn less, and the
  votes are free prioritisation research.

## 13.11 Team and cost

| Role | Y1 | Y2 | Y3 | Ratio target |
|---|---:|---:|---:|---|
| Implementation consultants | 4 | 7 | 9 | 1 per 6 concurrent projects |
| Customer success managers | 1 | 4 | 9 | 1 per 65 accounts (Growth), 1 per 22 (Business+) |
| Support (T1/T2) | 2 | 6 | 11 | 1 per 55 accounts, improving with deflection |
| Trainers / Academy | 0 | 1 | 2 | |
| **Total CS org** | **7** | **18** | **31** | |
| **CS cost as % of revenue** | 52% | 26% | 16% | Falls as deflection and partner delivery rise |

---

# 14. Competitive Moat

## 14.1 The honest starting position

**Conductor has no moat today.** It has a product advantage — better UX, better Arabic, faster
implementation — and product advantages are copyable. Odoo could ship a genuinely good Arabic UI in
18 months if they decided to. Any assessment that starts elsewhere is marketing, not strategy.

The real question is: **what does Conductor accumulate between now and then that cannot be copied?**
Below are twelve candidates, honestly graded. Only four are strong.

| # | Moat | Strength by Y3 | Strength by Y5 | Copyable? |
|---:|---|---|---|---|
| 1 | Switching costs (data + process) | **Strong** | **Very strong** | No — accrues per customer |
| 2 | Historical accounting data | **Strong** | **Very strong** | No |
| 3 | Audit trail continuity | Medium | **Strong** | No |
| 4 | Workflow & process investment | Medium | **Strong** | No |
| 5 | Employee adoption / trained labour pool | Medium | **Strong** | Slowly |
| 6 | Partner ecosystem | Weak | **Strong** | Yes, with money and time |
| 7 | Integrations & API surface | Weak | Medium | Yes |
| 8 | Brand trust | Weak | **Strong** | Slowly, and only with results |
| 9 | AI trained on Egyptian business patterns | Weak | Medium | Partly |
| 10 | Regulatory/compliance depth (ETA, ZATCA) | Medium | Medium | Yes — but it's a maintenance tax competitors keep paying |
| 11 | Marketplace network effects | Very weak | Medium | Yes |
| 12 | Aggregate benchmark data | Weak | **Strong** | No — requires scale we'd already have |

## 14.2 Switching costs — the primary moat

An ERP holds the customer's entire operational and financial history. Switching means: re-entering or
migrating years of transactions, rebuilding a chart of accounts, reconfiguring workflows, retraining
every user, re-integrating every connected system, and — critically — **running two systems in
parallel through a fiscal year while the auditor watches.**

**Estimated cost for a 40-person Conductor customer to switch after 3 years:**

| Component | Cost (EGP) |
|---|---:|
| Data migration out and in | 120,000 |
| New system implementation | 250,000 |
| Retraining 25 users | 60,000 |
| Rebuilding 3 integrations | 90,000 |
| Productivity loss during transition (est. 8 weeks) | 180,000 |
| Parallel run and audit reconciliation | 70,000 |
| **Total switching cost** | **~770,000** |
| Annual Conductor subscription | 162,000 |
| **Switching cost ÷ annual cost** | **4.8×** |

A competitor must be nearly five times better, not marginally cheaper, to justify a move. **This moat
is created entirely by delivering value in year one** — a customer who never fully adopted has no
switching cost at all, and will leave over EGP 20,000. Adoption depth *is* the moat.

## 14.3 Historical accounting data

Egyptian law requires retention of accounting records for **five years**. A customer three years in
has three years of ledger, invoices, ETA submissions, inventory movements, and payroll runs. That data
is where their comparatives, their trend reports, their audit responses, and their tax defences live.

**Strategic implication:** we must be aggressively good at **data export** — full, clean, documented,
free, on demand. This appears to weaken lock-in. It does the opposite: making export easy removes the
buyer's biggest fear at purchase time, and the reality is that exportable data is not the same as
transferable *system*. Customers who trust they can leave, don't.

## 14.4 Audit trail and compliance continuity

Every posting in Conductor is immutable, attributed, timestamped, and reversible only by a documented
counter-entry. Periods lock. AI actions are logged separately and never post autonomously.

For a company under ETA scrutiny — which is now every company — the continuity of that trail across
years is a compliance asset. Breaking it mid-year to switch systems is something a financial manager
will actively resist. **This moat is a direct product of the "trustworthy before intelligent"
principle**, which is why that principle is a strategy and not just a value.

## 14.5 Workflow and process investment

Approval chains, document templates, cost-centre structures, custom reports, credit rules, pricing
matrices. By year two a customer has encoded a meaningful part of *how their company actually works*
into Conductor. That configuration is not portable.

To strengthen it deliberately: make workflow configuration powerful, easy, and self-service. **Every
hour a customer spends configuring Conductor is an hour of moat.** This is the one place where we
relax the "opinionated, not configurable" stance — configuration of *process*, yes; configuration of
*core accounting behaviour*, never.

## 14.6 Employee adoption and the trained labour pool

The strongest form of this moat is external: **when Egyptian accountants list "Conductor" on their
CVs.** At that point hiring a Conductor-fluent accountant becomes easier than hiring an Odoo-fluent
one, and the switching cost includes retraining the labour market, not just the staff.

**This is why Conductor Academy is free and why certification is subsidised.** The revenue is
irrelevant; 400 certified individuals by Year 3 and 3,000 by Year 5 is the objective. It is a
long-cycle moat and it must be started in Year 1 to exist in Year 5.

## 14.7 Partner ecosystem

Currently our weakest position (§5.2 scores it 1/5) and the one that most determines Year 3–5
outcomes.

A partner who has trained 8 consultants, built 12 deployments, and derives a third of their revenue
from Conductor is structurally committed. Partners also become a distribution moat: a competitor
entering Egypt must recruit partners who are already busy and already earning.

**Path: 3 partners (Y1) → 8 (Y2) → 18 (Y3) → 45 (Y5).** The non-compete-on-services commitment
(§11.4) is the recruiting wedge.

## 14.8 Integrations

Weak today. Becomes real when a customer has connected their bank, their POS, their e-commerce store,
their shipping provider, and two internal tools. Each connection adds switching cost and each is a
place a competitor must also integrate.

**Priority order, by deal impact:** ETA (done) → bank statement formats and payment initiation →
POS systems → e-commerce (Shopify, WooCommerce, Salla, Zid) → shipping/logistics → payroll and social
insurance filing → e-signature.

## 14.9 Marketplace network effects

Real but slow, and honestly weak before Year 4. The mechanism: more customers → more developer
interest → more apps → more reasons to choose Conductor → more customers. Every marketplace has a cold
start, and ours will be cold until roughly 500 customers.

**Realistic assessment: not a moat in this plan's horizon.** It is an option we are funding cheaply
(20% take rate, developer fund) and should not be counted on for Series A.

## 14.10 AI and accumulated business knowledge

The claim "our AI gets better with data" is made by everyone and is usually false. Here is the honest
version:

**What is real:** patterns specific to Egyptian business practice — how a Cairo distributor actually
structures a chart of accounts, which ETA rejection codes correspond to which data errors, how
Egyptian manufacturers typically model a BOM, what a plausible opening-balance mapping looks like from
Al-Motakamel. These accumulate from real migrations and real support tickets and genuinely improve
migration accuracy and in-product assistance.

**What is not real:** any claim that our model becomes categorically smarter than a frontier model.
We use frontier models; so will competitors. **The advantage is in the accumulated Egyptian mappings
and the product surface around them, not in the model.** Stating this honestly is more credible with
sophisticated investors than the alternative.

**Governance constraint:** customer data is used to improve shared models only with explicit, granular,
revocable consent, and never in a form where one customer's data could surface to another. This is
both correct and commercially necessary — a single leak in a market this reference-driven would be
terminal.

## 14.11 Brand trust

Weak now, potentially our strongest asset by Year 5. In a market where an ERP decision is a career
risk, "the safe choice" is a defensible position, and only one company at a time gets to hold it in a
given segment.

**Built by:** published uptime, published customer numbers, honest gap disclosure, case studies with
real numbers, a customer advisory board, audited financials, ISO 27001, and — most of all — **not
having a public failure.** One badly failed high-profile implementation in Egypt's tightly connected
business community would cost more than any marketing budget could repair. This is the argument for
§10.6's capacity discipline.

## 14.12 Aggregate benchmark data

By Year 5, with 4,000+ customers, Conductor holds the most accurate real-time picture of Egyptian SMB
commerce that exists — better than official statistics, because it is transactional rather than
surveyed.

Uses, in increasing order of value and sensitivity: customer-facing benchmarks ("your DSO vs. your
sector") → published industry reports → credit-risk signals for lending partners → procurement and
supply-chain intelligence.

**This is the genuine long-term prize** (§17.9) and it demands the strictest governance: anonymisation,
aggregation thresholds, opt-in consent, and an absolute prohibition on any use that could expose an
individual customer's position to a competitor or supplier. Get this wrong once and the moat becomes a
liability.

## 14.13 Summary — when the moat actually exists

| Period | Defensibility | Reality |
|---|---|---|
| Years 0–2 | **Very low** | Product quality and speed only. Fully copyable. This is the dangerous window. |
| Years 2–4 | **Moderate** | Switching costs accumulating, partner channel forming, brand emerging |
| Years 4–6 | **Strong** | Data, partners, trained labour pool, brand, integrations compound together |

**The strategic conclusion: the first 24 months are a race, not a defence.** The correct behaviour in a
window with no moat is to move faster than incumbents can respond, and to convert speed into the
accumulating assets — customers, partners, certified people, and references — as quickly as possible.

---

# 15. Risks

Risks are ordered by **expected impact × probability**, not by category. Each carries a specific
mitigation, an owner, and a trigger that says when we act.

## 15.1 Market risk — willingness to pay (**highest**)

**Risk.** Egyptian SMBs do not pay for software at the levels modelled. Deals stall at price, ARPA
lands 30% below plan, and the CAC:LTV math inverts.
**Probability: Medium-High · Impact: Severe.**

**Mitigation.**
- Compliance-led selling — legal requirements get budgeted where productivity tools do not.
- ROI framed against headcount avoidance, the comparison Egyptian owners find most persuasive.
- Starter tier as a low-friction entry with a defined upgrade path.
- Design-partner pricing validates real willingness to pay before we scale sales hiring.

**Trigger:** if average closed-won ARPA is below EGP 55,000 for two consecutive quarters, we stop
sales hiring, re-price, and re-test before spending further.

## 15.2 Execution risk — implementation capacity (**highest**)

**Risk.** Implementations take 12 weeks instead of 6. Delivery becomes the growth ceiling. Margin
falls, references suffer, sales stalls behind delivery. §9.6 shows this as the single largest ARR
sensitivity (−19%).
**Probability: Medium-High · Impact: Severe.**

**Mitigation.**
- Never sell beyond 80% of delivery capacity (§10.6).
- Industry editions (pre-configured templates) as the structural fix — they attack setup time, which
  is most of the variance.
- AI migration tooling as the second structural fix.
- Partner delivery as the capacity release valve, targeted from Year 1 rather than Year 3.
- Per-project margin and hour-variance reporting from project one.

**Trigger:** median time-to-go-live above 9 weeks for a quarter → pause new bookings above capacity,
divert engineering to tooling.

## 15.3 Currency risk (**high**)

**Risk.** EGP devalues further. Revenue is EGP; cloud costs, some tooling, senior-talent compensation
benchmarks, and investor returns are USD. A 30% devaluation cuts USD ARR 30% with no operational
failure whatsoever.
**Probability: High (it has happened repeatedly) · Impact: High on returns, Medium on operations.**

**Mitigation.**
- CPI-linked renewal escalators from contract v1 (§7.5).
- Local infrastructure options evaluated to reduce USD-denominated cloud exposure.
- **Saudi entry is partly a currency hedge** — SAR is pegged to USD, so SAR revenue is effectively USD
  revenue. This is a genuine strategic argument for prioritising Saudi over Morocco.
- Report and plan in EGP; present investor returns in both currencies with explicit FX assumptions.

**Honest statement:** this cannot be fully mitigated. An investor in an Egyptian revenue business is
taking Egyptian currency risk and should price it.

## 15.4 Competitive risk — Odoo or a well-funded regional entrant (**high**)

**Risk.** Odoo invests seriously in Arabic and Egyptian localisation, or a funded Gulf player (or a
Daftra/Qoyod moving upmarket with capital) attacks the same segment.
**Probability: Medium · Impact: High.**

**Mitigation.**
- Speed. The 24-month window before defensibility exists must be used, not admired (§14.13).
- Lock in partners and accounting firms early — distribution is harder to displace than product.
- Depth in the three beachhead industries beats breadth; a focused competitor beats a general one.
- If a large player enters directly and credibly, **narrow rather than broaden** — become the
  definitive Egyptian distribution ERP rather than a general ERP losing on all fronts.

## 15.5 Regulatory risk (**medium-high**)

**Risk.** ETA changes schemas, deadlines, or certification requirements at short notice. Or new data
residency / cloud regulations require infrastructure changes.
**Probability: High (this happens regularly) · Impact: Medium.**

**Mitigation.**
- A permanently staffed compliance engineering function — not a project, a standing capacity.
- Direct relationships with ETA and with the tax-practitioner community; early sight of changes.
- Architecture that isolates compliance logic behind a versioned adapter so a schema change is a
  contained change, not a cross-cutting one.
- **Reframe as opportunity:** every regulatory change is a competitive event where the fastest
  responder wins deals. We should aim to be first to certify, publicly, every time.

## 15.6 Security risk (**medium probability, catastrophic impact**)

**Risk.** A breach exposing customer financial data. In a reference-driven market, this is a
company-ending event, not a bad quarter.
**Probability: Low-Medium · Impact: Catastrophic.**

**Mitigation.**
- Encryption at rest and in transit; strict tenant isolation; least-privilege access with audit
  logging on all internal access to customer data.
- Annual third-party penetration testing from Year 1 (not Year 3), published summary.
- ISO 27001 from Year 2, certified in Year 3.
- Cyber-liability insurance from Year 2.
- Documented, rehearsed incident-response plan including customer notification within 72 hours.
- Backups: continuous, geographically separated, **restore-tested monthly** — an untested backup is
  not a backup.
- No production data in development environments, ever. AI features operate on tenant-scoped data
  with no cross-tenant leakage path.

## 15.7 Hiring risk (**medium-high**)

**Risk.** Egypt's senior engineering talent is aggressively recruited by Gulf and remote-Western
employers paying in hard currency. We cannot match USD salaries with EGP revenue.
**Probability: High · Impact: Medium-High.**

**Mitigation.**
- Compete on the work, not only the salary: an ERP with a genuine design and engineering standard is a
  rare thing to work on in Egypt.
- Meaningful equity, properly explained — most Egyptian engineers have never had a real ESOP.
- Above-market EGP compensation with semi-annual inflation adjustment; falling behind inflation is
  how attrition starts.
- Hire junior aggressively and train; a structured internal academy.
- **Accept some attrition and design against it:** documentation standards, no single-owner systems,
  pairing on critical paths.
- Implementation consultants are harder to hire than engineers and are the actual constraint (§15.2).
  Recruit from Odoo/SAP partners and from accounting firms; train accountants into consultants rather
  than competing for scarce ERP consultants.

## 15.8 Technical risk (**medium**)

**Risk.** Scaling problems, data-integrity defects, or accumulated technical debt from moving fast.
For an ERP, a **data-integrity defect is the most severe class** — a wrong number in a filed return
is a customer-trust event.
**Probability: Medium · Impact: High.**

**Mitigation.**
- Double-entry invariants enforced at the database level, not only in application code.
- Automated reconciliation checks running continuously against every tenant's ledger.
- Comprehensive test coverage on all accounting logic; property-based tests on posting rules.
- Staged rollouts with per-tenant feature flags; no big-bang releases.
- A published, honest incident history. Hiding incidents is worse than having them.

## 15.9 Cash-flow risk (**medium**)

**Risk.** Egyptian B2B payment behaviour is slow. Customers pay late. Implementation revenue is
recognised over a project but costs are incurred immediately. Working capital tightens.
**Probability: Medium-High · Impact: Medium.**

**Mitigation.**
- **60% of implementation fee collected on signature.** Non-negotiable, no exceptions, including for
  attractive logos.
- Annual prepay as the default (§7.1), monthly at a 20% premium.
- Automated dunning; service suspension at 45 days overdue, applied consistently.
- Minimum 9 months of cash runway maintained at all times; below 9 months triggers a plan revision, not
  a hope.
- No enterprise or government deals with payment terms beyond 60 days before Year 4.

## 15.10 Cloud cost risk (**medium-low**)

**Risk.** Infrastructure and AI inference costs scale faster than revenue, compressing gross margin.
**Probability: Medium · Impact: Medium.**

**Mitigation.**
- Per-tenant cost accounting from day one. We must know what each customer costs us.
- AI cost governed by a hard KPI (§8.9): below 4.5% of subscription revenue, with model routing,
  caching, batching, and per-tenant caps.
- Reserved capacity commitments once usage is predictable (Year 2).
- Infrastructure cost per customer reviewed monthly; a rising trend is investigated, not absorbed.
- Target infrastructure at ≤6% of revenue by Year 3.

## 15.11 Key-person and concentration risk (**medium**)

**Risk.** Founder dependency in sales and product; customer concentration at 31% of revenue in top 5
(Year 1).
**Probability: Medium · Impact: Medium.**

**Mitigation.** Documented playbooks over tribal knowledge; deliberate founder hand-off of sales by
end Year 2 (55% → 18% → 6% of new ARR, §11.1); volume growth resolves concentration by Year 2; key-person
insurance from Year 2.

## 15.12 Risk summary

| Risk | Probability | Impact | Priority | Owner |
|---|---|---|---|---|
| Willingness to pay | Med-High | Severe | **1** | CEO |
| Implementation capacity | Med-High | Severe | **2** | Head of Delivery |
| Currency devaluation | High | High (returns) | **3** | CFO |
| Competitive response | Medium | High | **4** | CEO |
| Regulatory change | High | Medium | **5** | Head of Compliance Eng. |
| Security breach | Low-Med | Catastrophic | **6** | CTO |
| Hiring & retention | High | Med-High | **7** | CEO / Head of People |
| Technical / data integrity | Medium | High | **8** | CTO |
| Cash flow | Med-High | Medium | **9** | CFO |
| Cloud & AI cost | Medium | Medium | **10** | CTO |
| Key person / concentration | Medium | Medium | **11** | Board |

---

# 16. Financial Assumptions

## 16.1 Compensation (EGP, monthly gross, 2026 Cairo market)

| Role | Junior | Mid | Senior | Lead/Head |
|---|---:|---:|---:|---:|
| Backend engineer | 28,000 | 55,000 | 95,000 | 140,000 |
| Frontend engineer | 26,000 | 50,000 | 88,000 | 130,000 |
| Product designer | 25,000 | 48,000 | 85,000 | 120,000 |
| QA engineer | 20,000 | 36,000 | 60,000 | 85,000 |
| DevOps / SRE | 32,000 | 62,000 | 105,000 | 145,000 |
| Implementation consultant | 22,000 | 40,000 | 68,000 | 95,000 |
| Support engineer | 15,000 | 26,000 | 42,000 | 62,000 |
| Customer success manager | 20,000 | 35,000 | 58,000 | 85,000 |
| Account executive (base) | — | 24,000 | 36,000 | 60,000 |
| SDR (base) | 12,000 | 18,000 | — | — |
| Marketing | 16,000 | 32,000 | 58,000 | 90,000 |
| Finance / ops | 18,000 | 34,000 | 60,000 | 95,000 |

**Loading:** +19% employer social insurance and statutory costs, +8% benefits (medical, transport),
+7% recruitment amortised. **Fully loaded cost ≈ 1.34× gross salary.**
**Annual increase:** +18% (inflation-tracking; below this, attrition rises sharply).

## 16.2 Headcount plan

| Function | Y0 (pre-launch) | Y1 | Y2 | Y3 |
|---|---:|---:|---:|---:|
| Engineering | 5 | 8 | 15 | 24 |
| Product & design | 1 | 2 | 4 | 6 |
| Implementation | 2 | 4 | 7 | 9 |
| Support | 1 | 2 | 6 | 11 |
| Customer success | 0 | 1 | 4 | 9 |
| Sales (AE + SDR) | 0 | 3 | 11 | 20 |
| Partner management | 0 | 1 | 2 | 4 |
| Marketing | 0 | 2 | 5 | 8 |
| Finance, legal, ops, HR | 1 | 2 | 4 | 7 |
| Founders | 2 | 2 | 2 | 2 |
| **Total** | **12** | **21** | **42** | **71** |
| **Revenue per employee (EGP)** | — | 289,000 | 447,000 | 709,000 |

Revenue per employee approaching EGP 709k (USD 14.2k) by Year 3 is low by global SaaS standards and
appropriate for an emerging market with a services component — the correct comparison is local, not
to Stripe.

## 16.3 Cloud infrastructure

| | Y1 | Y2 | Y3 |
|---|---:|---:|---:|
| Customers (avg) | 39 | 164 | 434 |
| Compute + database (EGP) | 385,000 | 890,000 | 1,880,000 |
| Storage & backup | 92,000 | 245,000 | 540,000 |
| CDN & bandwidth | 58,000 | 130,000 | 285,000 |
| Monitoring, logging, security tooling | 130,000 | 245,000 | 415,000 |
| **Total infrastructure (EGP)** | **665,000** | **1,510,000** | **3,120,000** |
| Per customer per year (EGP) | 17,050 | 9,210 | 7,190 |
| **% of revenue** | **11.0%** | **8.0%** | **6.2%** |

Falling per-customer cost reflects fixed-cost amortisation and reserved capacity from Year 2. A rise
in this line is an early warning of an architectural problem.

## 16.4 AI inference

| | Y1 | Y2 | Y3 |
|---|---:|---:|---:|
| Total AI cost (EGP) | 232,000 | 640,000 | 1,590,000 |
| Per customer per year (EGP) | 5,950 | 3,900 | 3,660 |
| **% of subscription revenue** | 11.8% | 5.4% | **4.4%** |
| AI credit revenue (EGP) | 0 | 95,000 | 480,000 |
| **Net AI cost** | 232,000 | 545,000 | 1,110,000 |

Year 1 at 11.8% of subscription revenue is above the 4.5% KPI and is accepted only because the
subscription base is tiny and AI usage during migration is front-loaded. **It must fall below 6% by
end Year 2 or the AI feature set is re-scoped.**

## 16.5 Marketing and sales efficiency

| | Y1 | Y2 | Y3 |
|---|---:|---:|---:|
| Marketing spend (EGP) | 1,400,000 | 3,900,000 | 7,600,000 |
| Sales cost (payroll + commission) | 2,310,000 | 6,850,000 | 14,200,000 |
| **Total S&M** | **3,710,000** | **10,750,000** | **21,800,000** |
| **S&M as % of revenue** | 61% | 57% | 43% |
| New logos | 78 | 215 | 412 |
| **Blended CAC (EGP)** | **47,600** | **50,000** | **52,900** |
| New ARR added (EGP) | 5,304,000 | 16,340,000 | 34,608,000 |
| **Magic number** (new ARR ÷ prior-period S&M) | — | 4.4 | 3.2 |

A magic number above 1.0 indicates efficient growth; above 3.0 typically means **under-investment in
sales** and an opportunity to spend more. This is a positive signal and a deliberate use-of-funds
argument: if Year 2 confirms these numbers, the correct response is to accelerate hiring, which is why
the raise includes a buffer.

## 16.6 Other operating costs (EGP)

| Item | Y1 | Y2 | Y3 | Basis |
|---|---:|---:|---:|---|
| Office (Cairo, incl. utilities, internet) | 480,000 | 900,000 | 1,560,000 | ~EGP 2,000/m²/yr; 25 m²/person |
| Software & tooling | 285,000 | 620,000 | 1,180,000 | ~EGP 16k/employee/yr |
| Legal & compliance | 220,000 | 380,000 | 640,000 | Contracts, IP, DPA, entity |
| Accounting & audit | 145,000 | 290,000 | 520,000 | Audited from Y2 |
| Insurance (incl. cyber from Y2) | 0 | 180,000 | 340,000 | |
| ISO 27001 certification | 0 | 420,000 | 260,000 | Initial + surveillance |
| Penetration testing | 90,000 | 140,000 | 200,000 | Annual |
| Travel | 130,000 | 320,000 | 720,000 | Rising with governorate + Saudi |
| Recruitment | 90,000 | 260,000 | 480,000 | |
| Misc / contingency | 80,000 | 240,000 | 460,000 | ~1% of revenue |
| **Total G&A** | **1,520,000** | **3,750,000** | **6,360,000** | |

## 16.7 Tax

- **Corporate income tax: 22.5%** on taxable profit. Irrelevant during Years 1–3 (losses), but losses
  carry forward up to 5 years — worth ~EGP 7M of shielded future tax at plan.
- **VAT: 14%** on software services. Charged to customers, remitted; cash-flow-neutral but requires
  discipline on timing.
- **Payroll taxes and social insurance** included in the 1.34× loading (§16.1).
- **Withholding tax** applies on certain service payments and on cross-border software payments —
  a real friction on foreign cloud/tooling invoices, budgeted at ~EGP 90k/yr.
- **Investment incentives:** software export and ITIDA/technology-zone incentives may reduce effective
  rates. **Not modelled** — treat any benefit as upside, not as plan.

## 16.8 Gross margin bridge

| | Y1 | Y2 | Y3 | Driver |
|---|---:|---:|---:|---|
| Subscription GM | 84% | 86% | 87% | Infra amortisation, AI cost control |
| Implementation GM | 41% | 47% | 52% | Playbook maturity, industry editions |
| Training GM | 55% | 62% | 65% | Self-paced content scales |
| Other services GM | 44% | 49% | 53% | |
| **Blended GM** | **34%** | **62%** | **75%** | **Mix shift — 71% subscription by Y3** |

The Year 1 → Year 3 gross-margin improvement from 34% to 75% is driven by **revenue mix, not by cost
reduction.** If the subscription share does not shift as planned, gross margin does not improve, and
the whole model changes character (§8.1).

## 16.9 Break-even and runway

| Scenario | Break-even (months from launch) | ARR at break-even (EGP) | Cumulative burn (EGP) | Cumulative burn (USD) |
|---|---:|---:|---:|---:|
| Conservative | 52 | 51M | 44.6M | 892,000 |
| **Realistic** | **41** | **74M** | **31.0M** | **620,000** |
| Optimistic | 32 | 88M | 19.4M | 388,000 |

**Funding requirement:**

| | Amount (USD) | Amount (EGP) | Purpose |
|---|---:|---:|---|
| Realistic-case burn to break-even | 620,000 | 31.0M | Plan of record |
| Conservative-case buffer | +272,000 | +13.6M | Downside protection |
| Growth acceleration reserve | +400,000 | +20.0M | If magic number >3, spend into it |
| FX buffer (25% devaluation) | +208,000 | — | Currency protection |
| **Total raise** | **1,500,000** | **75.0M** | **24-month runway to Conservative break-even path** |

**Use of funds:**

| Category | % | USD | Rationale |
|---|---:|---:|---|
| Engineering & product | 46% | 690,000 | The product is the asset |
| Sales & marketing | 24% | 360,000 | Deliberately below typical SaaS; distribution is partner-led |
| Implementation & customer success | 14% | 210,000 | The delivery constraint (§15.2) |
| Infrastructure, security, compliance | 9% | 135,000 | ISO 27001, pen testing, cloud |
| G&A, legal, buffer | 7% | 105,000 | |

## 16.10 Long-run target model (Year 6–7, at scale)

| Line | Target | Comparable |
|---|---:|---|
| Gross margin | 80–83% | Below global SaaS (85%+) due to services and emerging-market support intensity |
| S&M | 30–34% | |
| R&D | 20–23% | ERP breadth requires sustained investment |
| G&A | 10–12% | |
| **EBITDA margin** | **14–20%** | Realistic for a regional vertical-ish SaaS at USD 15–25M ARR |
| Rule of 40 (growth + margin) | 55–70 | |
| NRR | 115–120% | |

## 16.11 Assumptions we are least confident in

Stated so an investor can test the right things:

1. **Churn at 9% by Year 3.** We have no cohort data. Egyptian SMB business mortality alone may set a
   floor near 8–10% regardless of product quality.
2. **Partner channel reaching 32% of new logos by Year 3.** This depends on recruiting organisations
   that currently make money elsewhere. Unproven.
3. **Six-week implementation at scale.** Validated on design partners, not on 400 customers.
4. **ARPA growth of +9% p.a.** Requires successfully applying CPI escalators without churn spikes.
5. **AI cost below 4.5% of subscription revenue.** Depends on model pricing trends we do not control —
   though the trend has been strongly favourable.
6. **The size of layers 5–8 of the market funnel** (§2.2). Our least reliable data.

---

# 17. Five-Year Vision

## 17.1 The destination

**By 2031, Conductor is the operating system for business in the Arab world's mid-market** — the
system where the invoice, the stock movement, the payroll run, the bank reconciliation, the approval,
and the audit trail all live in one place, in Arabic, priced in local currency, and trusted by the
finance managers who stake their careers on it.

| | 2027 (Y1) | 2028 (Y2) | 2029 (Y3) | 2030 (Y4) | 2031 (Y5) |
|---|---:|---:|---:|---:|---:|
| Customers | 69 | 258 | 609 | 1,380 | 2,850 |
| Countries | 1 | 1 | 2 | 3 | 5 |
| ARR (EGP) | 5.0M | 21.2M | 56.6M | 128M | 285M |
| ARR (USD) | 100k | 423k | 1.13M | 2.56M | 5.7M |
| Non-Egypt revenue | 0% | 0% | 3% | 17% | 34% |
| Partners | 3 | 8 | 18 | 32 | 45 |
| Certified professionals | 40 | 180 | 400 | 1,400 | 3,000 |
| Marketplace apps | 0 | 6 | 22 | 60 | 140 |
| Headcount | 21 | 42 | 71 | 128 | 215 |
| Gross margin | 34% | 62% | 75% | 79% | 81% |
| EBITDA margin | −162% | −72% | −15% | +4% | +13% |

**A note on the USD line.** USD 5.7M ARR at Year 5 is a good regional SaaS business and a modest
venture outcome. In EGP the growth is 57× over five years. The gap between those two readings is
entirely currency, and it is the honest reason MENA expansion — specifically into a
dollar-pegged market — is a strategic necessity rather than an ambition.

## 17.2 AI — from assistant to operator, without ever crossing the ledger

The evolution is deliberate and staged, and the boundary never moves.

| Stage | Years | Capability | The boundary |
|---|---|---|---|
| **Assist** | 1–2 | Answers questions about your data. Drafts invoices, POs, journal entries from documents or instructions. OCR on supplier invoices and receipts. Migration mapping. | Human reviews and posts. Always. |
| **Anticipate** | 2–3 | Flags anomalies (a supplier price 22% above the last three POs; a customer whose payment pattern just changed). Forecasts cash. Suggests reorder points. Drafts month-end accruals. | Human accepts or rejects each item. |
| **Act (drafts only)** | 3–4 | Executes multi-step work across modules — but as *drafts*: creates the PO, the goods receipt, the matching, and presents the whole chain for approval. | Nothing posts to the ledger without a named human approval, logged. |
| **Operate (bounded)** | 4–5 | Fully autonomous for defined, low-risk, reversible operations under customer-set policy: routine reorders under a threshold, standard reconciliation matches, recurring journals. | Every autonomous action is attributed to a policy the customer wrote, logged, reversible, and reported. Customer can disable entirely. |

**The line that never moves: a financial posting always has a human accountable for it.** Not because
the AI cannot do it, but because the audit trail must name a person. This is a permanent product
principle, not a transitional safety measure — and by Year 5, when competitors are shipping
autonomous accounting agents, it will be a *feature*, because it is the only version a real auditor
will accept.

**By 2031 the assistant is the primary interface for most users.** Finance staff still use forms;
everyone else — the sales rep, the warehouse supervisor, the project manager, the owner — mostly asks.

## 17.3 Banking

| Phase | Capability |
|---|---|
| Year 2 | Bank statement import (all major Egyptian bank formats), AI-assisted reconciliation |
| Year 3 | Direct bank feeds via API where available; payment file generation |
| Year 4 | Payment initiation from within Conductor — pay a supplier batch without leaving the system |
| Year 5 | Embedded lending: working capital offers based on verified Conductor transaction history, originated by bank/fintech partners |

**The Year-5 item is the strategically important one.** An SMB's biggest constraint in Egypt is not
software, it is working capital. A company whose real receivables, real inventory, and real payment
history are verifiable in Conductor is a far better credit risk than one presenting hand-prepared
statements. We do not become a lender; we become the **verification layer** that makes lending
cheaper — and take an origination referral fee.

## 17.4 Payments

Year 3: accept customer payments through Conductor-generated invoice links (cards, wallets, InstaPay,
Fawry) with automatic reconciliation to the AR ledger. Year 4: recurring collections and direct debit.
Year 5: supplier payment execution.

**Economics:** a modest share of payment volume. At Year 5, if 25% of customers process an average of
EGP 6M/year through Conductor at a 25bp net take, that is roughly **EGP 10.7M of high-margin
revenue** — comparable to a meaningful slice of subscription ARR and materially higher margin.

**Discipline:** payments must never compromise the accounting. Reconciliation correctness beats
payment volume every time.

## 17.5 Government integration

| Integration | Timing | Market |
|---|---|---|
| ETA e-invoice | Live | Egypt |
| ETA e-receipt | Y1 | Egypt |
| Social insurance filing | Y2 | Egypt |
| Payroll tax filing | Y2 | Egypt |
| VAT return preparation & filing | Y3 | Egypt |
| Customs / import documentation | Y4 | Egypt |
| **ZATCA Fatoora** | Y3 | Saudi Arabia |
| UAE e-invoicing | Y4 | UAE |
| Jordan JoFotara | Y4 | Jordan |

**The strategic insight: government integration is the highest-leverage moat available in this
region.** Every market's tax authority is building mandatory e-invoicing on a similar model. Being
certified first in each market, and maintaining that certification through constant schema churn, is
expensive, unglamorous work that competitors consistently under-invest in — and it is the thing that
makes us un-replaceable rather than merely preferred.

## 17.6 Marketplace

| Year | State |
|---|---|
| 2 | Launch. 6 apps, mostly Conductor-built. Industry templates and report packs. |
| 3 | 22 apps. First meaningful third-party developers. Connector library. |
| 4 | 60 apps. Vertical solutions built by partners (clinic, school, restaurant editions). |
| 5 | 140 apps. Genuine ecosystem; marketplace is 4–6% of revenue and a real reason to choose Conductor. |

20% take rate held deliberately low (§7.7). Ecosystem supply matters more than marketplace margin
until the ecosystem exists.

## 17.7 Industry editions

Pre-configured verticals: chart of accounts, workflows, document templates, KPIs, reports, and role
definitions. **Implementation time drops from 6 weeks to 2–3 weeks in a covered vertical**, which
simultaneously fixes the delivery constraint (§15.2), raises implementation margin, and opens
industries we would otherwise skip.

Order: Distribution (Y3) → Manufacturing (Y3) → Retail (Y3) → Construction (Y4) → F&B (Y4) →
Professional Services (Y4) → Clinics, Schools, Restaurants (Y5, partner-built where possible).

## 17.8 Developer ecosystem and public APIs

- **Y2:** REST API v1, webhooks, sandbox, Arabic + English documentation.
- **Y3:** API v2 with GraphQL, official SDKs (Python, PHP, Node, .NET), OAuth apps.
- **Y4:** app framework — third parties build UI *inside* Conductor, not just against it.
- **Y5:** 800+ registered developers, a developer conference, a developer fund.

**Why it matters:** Egypt has a large and growing developer population. If Conductor becomes the
default backend for business applications built for Egyptian companies, the ecosystem produces
distribution we do not pay for — and each integration deepens switching costs (§14.8).

## 17.9 Analytics and the data asset

Progression: standard reports (Y1) → self-service BI builder (Y2) → **anonymised sector benchmarks
inside the product** (Y3: "your DSO is 62 days; the median for Cairo food distributors is 41") →
published annual State of Egyptian SMB Finance report (Y3) → predictive analytics (Y4) →
verified-data services to lending and insurance partners with explicit customer consent (Y5).

**Governance is the whole game here.** Aggregation minimums, opt-in consent, revocable at any time,
no output that could identify a single company, and a published data-use policy in plain Arabic. The
value of this asset is entirely contingent on customers trusting us with it, and that trust is
destroyed by exactly one mistake.

## 17.10 Mobile

Y2: approvals and dashboards (the executive app). Y3: field sales, warehouse scanning, expense capture
with OCR. Y4: full role-based mobile for every operational role. Y5: mobile-first as the default for
non-finance users — which, in a market where many warehouse and field staff have a phone and not a
desk, is where a large share of daily usage will actually live.

## 17.11 Workflow automation

Y2: basic multi-level approvals. Y3: a visual workflow builder — conditions, escalations, SLAs.
Y4: cross-module automation and scheduled processes. Y5: AI-suggested automations ("this three-step
approval has been approved unchanged 340 times; should it auto-approve under EGP 5,000?").

Each automation a customer builds is moat (§14.5), and the compounding of that is why the workflow
builder is worth building well rather than adequately.

## 17.12 Geographic expansion

| Market | Entry | Rationale |
|---|---|---|
| **Egypt** | Y0 | Home. Largest SMB population in the Arab world. |
| **Saudi Arabia** | Y3 | 2.6× ARPA, ZATCA mirrors ETA, Arabic-first mandatory, **SAR pegged to USD (currency hedge)**. The single most important expansion decision. |
| **UAE** | Y4 | High value, competitive, gateway to regional groups. Partner-led entry. |
| **Jordan** | Y4 | Small but low-cost, similar regulation, useful proving ground. |
| **Kuwait, Qatar, Bahrain, Oman** | Y5 | Partner-led only. Low fixed cost. |
| **Morocco, Tunisia** | Not before Y6 | French-first — effectively a different product. |
| **Kenya, Nigeria** | Not before Y6 | English-first, different regulation, different payments. |

**Expansion model: partner-first, always.** Two certified local partners signed before any office
opens in a new market. This is what makes the Year-5 five-country plan achievable with 215 people
instead of 500.

## 17.13 What has to be true

The vision is contingent on five things, each of which is a falsifiable bet:

1. **Egyptian SMBs will pay for cloud software at EGP 60–200k/year.** Tested in Year 1. If false, the
   business is a EGP 20k/year product for a much larger market — a different company.
2. **Implementation can be systematised to 6 weeks and then to 3.** Tested in Years 1–3 via playbook
   and industry editions. If false, growth is capped by consultant hiring.
3. **A partner channel can be built in Egypt.** Tested in Year 2. If false, growth is capped by our
   own sales hiring and the model becomes far more capital-intensive.
4. **The Egypt playbook transfers to Saudi Arabia.** Tested in Year 3. If false, this is a
   single-country company — a fine business, not a venture return.
5. **Trust compounds.** That being demonstrably careful with customers' financial data, honest about
   what the product cannot do, and disciplined about what AI is allowed to touch, produces a brand
   advantage that outlasts any feature gap. **This is the founding bet, and it is the one we are
   least willing to trade away.**

---

## Appendix A — Metrics dashboard

**Reviewed weekly by the leadership team; monthly by the board.**

| Category | Metric | Y1 target | Y2 | Y3 |
|---|---|---:|---:|---:|
| **Growth** | Ending ARR (EGP) | 4.97M | 21.2M | 56.6M |
| | New customers | 78 | 215 | 412 |
| | Net new ARR (EGP) | 4.97M | 16.2M | 35.5M |
| **Retention** | Gross logo retention | 84% | 88% | 91% |
| | Net revenue retention | 96% | 104% | 111% |
| **Efficiency** | Blended CAC (EGP) | 47,600 | 50,000 | 52,900 |
| | CAC payback (months) | 14.7 | 10.2 | 8.4 |
| | Magic number | — | 4.4 | 3.2 |
| | LTV:CAC (5-yr capped lifetime) | 4.1 | 5.6 | 7.0 |
| **Margin** | Blended gross margin | 34% | 62% | 75% |
| | Subscription share of revenue | 52% | 63% | 71% |
| | Infrastructure % of revenue | 11.0% | 8.0% | 6.2% |
| | AI cost % of subscription revenue | 11.8% | 5.4% | 4.4% |
| **Delivery** | Median time-to-go-live (weeks) | 6 | 5 | 5 |
| | Implementation gross margin | 41% | 47% | 52% |
| | Partner-delivered share | 10% | 35% | 60% |
| **Product** | Weekly active / licensed users | 62% | 70% | 74% |
| | Support ticket deflection | 15% | 30% | 42% |
| | NPS | 50 | 55 | 60 |
| **Channel** | Partner-sourced share of new logos | 4% | 18% | 32% |
| | Certified partner consultants | 6 | 24 | 62 |
| | Accounting firms signed | 25 | 90 | 220 |
| **People** | Headcount | 21 | 42 | 71 |
| | Revenue per employee (EGP) | 289k | 447k | 709k |
| | Voluntary attrition | <15% | <15% | <12% |

## Appendix B — The six numbers that decide everything

If an investor reads nothing else, these are the variables that determine whether this plan works:

| # | Number | Plan | Why it decides the outcome |
|---:|---|---:|---|
| 1 | **Median time-to-go-live** | 6 weeks | Sets delivery capacity, which caps growth (−19% Y3 ARR at 12 weeks) |
| 2 | **Blended ARPA** | EGP 91,000 (Y3) | Tests the core willingness-to-pay thesis |
| 3 | **Gross logo churn** | 9% (Y3) | Tests whether the product actually gets adopted |
| 4 | **Partner-sourced logos** | 32% (Y3) | Determines whether growth is capital-efficient or capital-intensive |
| 5 | **Subscription share of revenue** | 71% (Y3) | Determines whether this is a SaaS business or a consultancy |
| 6 | **Non-Egypt revenue** | 17% (Y4) | Determines whether this is a venture outcome or a good local business |

## Appendix C — Milestones to Series A

| Milestone | Target date | Status gate |
|---|---|---|
| 15 design partners live, 10 closed month-ends | Month 0 | Gate to launch |
| First 25 full-price customers | Month 8 | Willingness-to-pay validated |
| First 3 partner-sourced deals closed | Month 12 | Channel thesis validated |
| EGP 5M ARR | Month 12 | |
| 8 certified partners producing | Month 24 | Channel operating |
| NRR > 100% | Month 24 | Expansion motion works |
| EGP 21M ARR | Month 24 | |
| ISO 27001 certified | Month 30 | Enterprise unlocked |
| ZATCA certified, first Saudi customer | Month 33 | Expansion thesis tested |
| Gross margin > 70% | Month 33 | SaaS economics proven |
| **USD 1.5M ARR run-rate, 2 countries, NRR > 110%** | **Month 36** | **Series A** |

---

*Prepared July 2026. All figures are estimates derived from the assumptions stated in each section.
Market-size estimates for Egypt derive from CAPMAS establishment data extrapolated to 2026 and are
subject to material uncertainty in layers 5–8 of the funnel (§2.2). Financial projections are
forward-looking statements and not guarantees. Currency planning rate: 1 USD = 50 EGP.*


