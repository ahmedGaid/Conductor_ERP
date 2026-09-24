# License Key — Master Index

> **Source: founder request, 2026-09-24.** Sell Conductor as a **one-time purchase** (perpetual
> license, unlimited users) + an **optional annual maintenance fee** (updates + support + ETA
> changes), like a desktop app — alongside, not instead of, the SaaS model in
> `Docs/pitch/Conductor_Pitch_Deck.md` slide 8. Conductor is customer-hosted and single-tenant,
> so the license must be **verified offline** and must be **hard to copy to a second company**.

## Why this plan exists

Today any copy of the code runs as a full, unlimited install. There is no way to sell "this
package, for this company, with updates until this date." Without a license key, a perpetual
sale is a copy away from a free second customer, and the maintenance fee has nothing to bite on.

## What the license controls (and what it never touches)

| Controls | How |
|---|---|
| **Which company** may use it | Bound to the company's tax registration number (VAT/ETA ID) + name |
| **Package (edition)** | Which modules are on (e.g. CRM, workflows) |
| **Size** | Max branches (users are always **unlimited**) |
| **Maintenance** | `maintenance_until` date — releases newer than it can't be installed |
| **AI assistant** | Separate add-on with its own end date (it costs money per use) |

**Never touched — the trust floor:** a customer's own data is never locked. Every state, even an
invalid or expired license, keeps the books **readable and exportable**. Perpetual means
perpetual: the version they paid for keeps working forever; only *new releases* need maintenance.

## The files (strict order; one file = one session)

| File | Task | Effort | Model |
|---|---|---|---|
| FILE_01 | Key format + offline verifier + issuer tool (the crypto core) | Medium | **Opus** (security design) |
| FILE_02 | Install/status commands, provisioning hook, trial state, license API | Small–Med | Sonnet |
| FILE_03 | Enforcement: modules, branches, AI add-on, company binding, read-only | Medium | Sonnet (Opus review of the read-only guard) |
| FILE_04 | Maintenance gate in `manage.py upgrade` + renewal flow | Small | Sonnet |
| FILE_05 | Settings → License page + calm status banners (ar/en) | Small–Med | Sonnet |
| FILE_06 | Acceptance, runbook, sales/issuing procedure, DECISIONS | Small | Sonnet |

Merge checkpoints: after FILE_03 (backend complete, `LICENSE_MODE=off` keeps everything else
unaffected), after FILE_06.

## Locked decisions (re-confirm only if code contradicts)

1. **Signed key, offline.** Ed25519 signature over a canonical JSON payload. The **public** key
   ships in the code; the **private** key lives only on the founder's machine, never in the repo,
   never on a customer server. No phone-home: the verifier works with no internet.
2. **No new dependency.** `cryptography` is already pinned in `requirements.txt` (Ed25519 is in it).
3. **Off by default.** `LICENSE_MODE` = `off` (dev, tests, demo, future SaaS) | `enforce`
   (perpetual customer installs). With `off`, behaviour is byte-identical to today — the existing
   test suite must pass untouched.
4. **Company binding is the real anti-copy lever.** The code ships as Python source, so a
   determined customer *can* patch out a check — no offline scheme stops that; the LICENSE terms
   (`pre-handover-hardening/FILE_05`) are the legal backstop. What makes copying useless in practice:
   the license is bound to the company's **tax ID**, and every e-invoice to the ETA and every printed
   document carries the company tax ID. A copy at another company either shows the licensed
   company's identity or cannot submit e-invoices. Machine fingerprinting is **not** used (it breaks
   on every server move and punishes honest customers).
5. **Maintenance gates releases, never usage.** Expired maintenance = the app keeps running forever;
   `manage.py upgrade` refuses a release **dated after** `maintenance_until` until a renewal key is
   installed.
6. **Unlimited users, always.** No per-user check exists anywhere. Size is priced by branches and
   edition.
7. **AI is a separate, dated add-on.** Effective assistant on = `ASSISTANT_ENABLED` AND license
   `ai_until >= today`. AI calls cost real money per use — a perpetual license can't include them
   forever.
8. **Blame-free, calm states.** No red alarms, no countdown panic. Human Arabic, one canonical word
   per concept, added to Identity System §6 **before** shipping: **ترخيص** (license), **الصيانة
   السنوية** (annual maintenance), **الباقة** (edition/package), **فترة التجربة** (trial).

## Founder decisions — defaults chosen so the plan can proceed (change any before its file runs)

| Question | Default in this plan | Needed by |
|---|---|---|
| Trial length with no license | 30 days full use, then read-only | FILE_02 |
| Edition names + contents | Basic (accounting, inventory, sales, purchasing, e-invoice, 1 branch) · Integrated (+ CRM, workflows, 5 branches) · Enterprise (all, unlimited branches) | FILE_01 |
| Maintenance included in year 1 | Yes — `maintenance_until` = issue date + 1 year | FILE_01 |
| Grace after maintenance ends | None for upgrades (it's opt-in); a 30-day "ending soon" notice before | FILE_05 |
| Clock rolled back | Detect (last-seen date), show a calm notice, never lock data | FILE_03 |

## Out of scope

- Online activation / phone-home / license server.
- Payments for renewals (founder issues renewal keys by hand after payment; SaaS billing is
  `Docs/plan/07-billing-and-provisioning.md`).
- Obfuscating or compiling the Python source.
- Per-user seat counting (deliberately never — decision 6).
