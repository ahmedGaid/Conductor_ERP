# Session 09 — Real ETA e-invoicing integration (replace the stub)

**Goal:** turn the e-invoice module from a lifecycle stub into a real Egyptian Tax Authority
integration — because ETA compliance is the wedge in the whole GTM story, and today
`submit_invoice`/`poll_invoice` don't talk to ETA at all. **Run any time after Session 00; must be
done before the Session 08 demo is recorded.** Branch `feat/eta-integration`.

> ETA's API surface and signing requirements change; verify current docs at build time
> (invoicing.eta.gov.eg SDK portal) — do not trust memory. Start against the **preprod/sandbox**
> environment; production credentials are the customer's, entered in Settings.

## What ETA actually requires (verify each at build time)
- **Onboarding:** taxpayer registers on the ETA portal, gets Client ID + Client Secret per POS/ERP.
- **Auth:** OAuth2 client-credentials token against the ETA identity server.
- **Document format:** ETA JSON document schema (not UBL XML) — issuer/receiver tax ids, activity
  code, line items with ETA item codes (GS1/EGS), tax subtypes (T1 VAT etc.), totals.
- **Signing:** documents signed with the taxpayer's e-seal certificate (USB token/HSM). Signing
  happens client-side by design (the certificate must never leave the customer's machine) — plan a
  small local signing agent or manual-signature upload path for v1; document the constraint.
- **Lifecycle:** submit → accepted/rejected (validation) → the `uuid`/`longId` ETA assigns; recent
  mandates also cover **receipts** (B2C) — invoices (B2B) first, receipts later (backlog).

## Tasks
1. **Config:** `ETASettings` (org-level, Settings UI): environment (preprod/prod), client id/secret
   (encrypted at rest — add a small `EncryptedCharField` helper or encrypt via SECRET_KEY-derived
   key), taxpayer RIN, activity code. Designed "not configured" state — module still lists local
   compliance records with a setup CTA.
2. **Client:** `erp/einvoice/eta/client.py` — token acquisition (cached until expiry), submit
   documents, get submission status. stdlib urllib per house style; timeouts; typed errors mapped to
   blame-free messages. All calls audited with correlation id.
3. **Document builder:** `erp/einvoice/eta/document.py` — map `ETAInvoice` + source invoice lines →
   ETA JSON schema. Item-code mapping table (item sku → EGS/GS1 code) with a designed "missing code"
   resolution flow. Unit-test against ETA's published sample documents.
4. **Signing:** implement the chosen v1 path (local agent or signature upload); keep the signing
   interface separate from the client so an HSM integration can slot in later.
5. **Wire the stub:** `submit_invoice`/`poll_invoice` now call the client when configured; keep the
   current simulated path as `ETA_MODE=mock` for dev/gates (gates must stay offline).
6. **Status sync:** Celery task polls submitted documents → valid/rejected with ETA's reasons
   surfaced (translated, blame-free). Rejected → designed fix-and-resubmit flow.
7. **Tests:** mocked ETA server covering happy path, auth failure, validation rejection, timeout.
   Gate-safe (no network).

## Done bar
- Against ETA preprod: a real posted invoice submits, gets a UUID, and reaches `valid` — screenshot
  the portal as proof.
- Gates GREEN offline (`ETA_MODE=mock`); parity + `tsc -b` + `gate03` GREEN on Settings UI.
- DECISIONS.md "ETA 2026-07": signing approach chosen + why; receipts (B2C) explicitly deferred to
  backlog.
