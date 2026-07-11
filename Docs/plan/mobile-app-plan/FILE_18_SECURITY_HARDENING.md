# SESSION 18 — Security Hardening
# Files: apps/mobile/lib/core/security/** (new), erp/identity (small additive), platform config,
#        DECISIONS.md (threat-model entry), apps/mobile/SECURITY.md (new)

**Objective:** raise the app from "secure by architecture" (tokens hashed server-side, keystore
storage, revocation, RBAC server-side — already built) to enterprise-auditable: certificate
pinning, screen privacy, root/jailbreak posture, session policy, and a written threat model a
customer's IT department can read. Everything lands with a `SECURITY.md` that states what we
protect against and — honestly — what we don't.

---

## Before You Start

1. Re-read sessions 03/07 implementations (token lifecycle, lock, privacy shield scaffold).
2. Read current Flutter/dio guidance for: TLS pinning (dio's `badCertificateCallback` /
   `SecurityContext` with pinned SPKI hashes — plus Android `network_security_config.xml` and
   iOS ATS as defense-in-depth), `FLAG_SECURE` (a small platform-channel call or existing
   approved mechanism), and root/jailbreak signal options. **Any new dep (e.g. a
   device-integrity package) = DECISIONS entry first** — prefer hand-rolled basic signals
   (su binary paths, debuggable flags) over a dependency if they cover the threat model.
3. Ask the deployment question: pinning against WHICH cert? Self-hosted customers have their own
   certs → pin to the leaf is impossible globally. Resolution: pin to the server's CA/public key
   per configured server, fetched-and-pinned on first login (TOFU + change alarm), OR pin only
   the cloud offering's cert and document self-hosted as standard-TLS. This is a real product
   decision → DECISIONS, this session.

"Do not write anything yet."

---

## Task A — Transport & device posture

1. Implement the pinning decision from above (SPKI-hash check in the dio client's certificate
   callback); failure mode = designed blocking screen ("لا يمكن التحقق من الخادم" + support
   guidance), never a silent fallback to unpinned.
2. Root/jailbreak detection (best-effort signals; document that determined attackers bypass
   client checks — honesty in SECURITY.md): on detection, WARN + report flag to server on login
   (device row gets `integrity_flag`) — org policy (block vs. allow-with-flag) is a server-side
   setting an admin controls, not a hardcoded choice.
3. `FLAG_SECURE` on Android (screenshots/recording blocked) as a server-driven org policy too —
   default ON for the app switcher shield (session 07), full screenshot blocking per org choice
   (some SMBs WANT to screenshot invoices to WhatsApp — policy, not dogma).

## Task B — Session & data policy

1. Server-side (identity, additive): per-org mobile session policy knobs — refresh-token max
   lifetime, inactivity revocation (cron/management command sweeping stale `last_seen_at`),
   max devices per user. Sensible defaults; exposed where web admin settings live.
2. On-device data: catalogue what exists (drift cache DB, drafts, outbox, attachment temp files)
   → ensure sign-out/revocation wipes ALL of it (session 07 wipe audited and extended: SQLite
   WAL/-shm files, temp dirs); iOS `DataProtection` entitlement class + Android keystore-backed
   options per current platform guidance for the SQLite file (device-encryption reality:
   documented, not oversold).
3. Audit events: mobile-specific security events flow to `erp.audit` — login, biometric-enable,
   device revoke, integrity flag, pinning failure (server hears of it on next contact). No new
   audit pathway — the existing `record(...)` service.

## Task C — Paper: SECURITY.md + MDM notes

Write `apps/mobile/SECURITY.md` (English; customer-IT-facing): auth architecture, token
lifecycle diagram, storage inventory + protection classes, pinning policy + **cert-rotation
runbook** (pins ship in app releases — rotation needs a store release with overlap-window pins;
no OTA escape hatch exists by design, so pin to CA/SPKI with a spare pin included), integrity
posture, session policy knobs, wipe semantics, what is OUT of scope (compromised-OS guarantees).
MDM/BYOD note: managed-configuration (server URL pre-provisioning) via Android RestrictionsManager
/ iOS managed app config — implement the managed-config read if trivial without a new dep, else
document as roadmap with the key schema already defined.

---

## Smoke Test

- [ ] MITM attempt (proxy with custom CA, e.g. mitmproxy) → app refuses with the designed screen;
      remove proxy → works. On a self-hosted-style second server per the DECISIONS choice
- [ ] Sign out → device storage inspected (adb / simulator filesystem): no `conductor.db` (or
      WAL/-shm leftovers), no drafts, no attachment temps, nothing in secure storage
- [ ] Server-side inactivity sweep revokes a stale test device → phone lands on sign-in with the
      calm notice; audit rows exist for the whole journey
- [ ] Rooted emulator (or root-signal simulation) → warning surfaced + `integrity_flag` visible
      on the device row server-side; org policy toggle blocks login when set
- [ ] Org screenshot policy ON → screenshot attempt blocked on Android; switcher shield on iOS
- [ ] `pytest erp/identity` green incl. new policy tests; analyze + test green; SECURITY.md
      reviewed against what the code ACTUALLY does (no aspirational claims — read it line by line)

## Risks

- Pinning bricking the app on legitimate cert rotation → pin to CA/SPKI not leaf, ALWAYS ship a
  spare pin, and document the rotation runbook in SECURITY.md — with store-only releases there
  is no OTA break-glass, so the overlap window must be generous.
- Security theatre creep → every control in this session maps to a threat in the threat model;
  anything that doesn't, gets deleted.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_19_QA_AUTOMATION.md
```
