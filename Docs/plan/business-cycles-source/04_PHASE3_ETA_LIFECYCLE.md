# Phase 3 — ETA E-Invoice Lifecycle (Egypt) as Native Document States
# LOW RISK — additive columns + state machine extension on ar_invoice. No external API calls in this phase; the transport adapter is stubbed behind an interface.

## The design decision this phase encodes (rule C4)

The Egyptian Tax Authority (ETA) e-invoice is NOT an export feature. It is part of the invoice's
life. A posted invoice that the ETA has not accepted is not "done". Therefore:

- ETA status lives ON the document, transitions through the guarded write path, and appears in
  the timeline like any state change.
- Submission payload is generated ONCE at submission time and stored immutably (what was sent is
  evidence, not a rendering).
- An ETA-REJECTED posted invoice is never edited. It is credited (reversal document) and
  re-issued (rule C8). The UI offers exactly this action and nothing else.

## What you will do in this phase

1. Add ETA columns + state machine to `ar_invoice`.
2. Create `eta_submission` immutable log table.
3. Create transition procedures and a transport adapter interface (stub implementation).
4. Mutability + UI: ETA status chip, timeline events, credit-and-reissue command.

## Step 1 — Schema

Migration `db/migrations/NNN_eta_lifecycle.sql`:

```sql
ALTER TABLE ar_invoice
  ADD COLUMN eta_status text NOT NULL DEFAULT 'not_applicable'
    CHECK (eta_status IN ('not_applicable','eta_pending','eta_submitted','eta_accepted','eta_rejected')),
  ADD COLUMN eta_uuid text,             -- ETA-assigned UUID on acceptance
  ADD COLUMN eta_long_id text,
  ADD COLUMN eta_submitted_at timestamptz,
  ADD COLUMN eta_resolved_at  timestamptz;

CREATE TABLE eta_submission (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      uuid NOT NULL REFERENCES tenant(id),
  invoice_id     uuid NOT NULL REFERENCES ar_invoice(id),
  attempt_no     int  NOT NULL,
  payload        jsonb NOT NULL,        -- exact document sent, frozen
  payload_hash   text NOT NULL,
  response       jsonb,
  outcome        text CHECK (outcome IN ('submitted','accepted','rejected','error')),
  submitted_by   uuid NOT NULL,
  submitted_at   timestamptz NOT NULL DEFAULT now(),
  resolved_at    timestamptz,
  UNIQUE (invoice_id, attempt_no)
);

SELECT attach_event_log_trigger('eta_submission');

-- eta_submission is append-only: block UPDATE except resolution columns, block DELETE always.
CREATE OR REPLACE FUNCTION trg_eta_submission_immutable() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'C8: eta_submission rows are never deleted';
  END IF;
  IF NEW.payload IS DISTINCT FROM OLD.payload
     OR NEW.payload_hash IS DISTINCT FROM OLD.payload_hash
     OR NEW.attempt_no IS DISTINCT FROM OLD.attempt_no THEN
    RAISE EXCEPTION 'C4: submitted payload is immutable';
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER eta_submission_immutable
  BEFORE UPDATE OR DELETE ON eta_submission
  FOR EACH ROW EXECUTE FUNCTION trg_eta_submission_immutable();
```

## Step 2 — State machine procedures

Allowed transitions (enforce here, nowhere else):

```
posted + not_applicable   → eta_pending      (mark as ETA-relevant; automatic at posting when tenant has ETA enabled)
eta_pending               → eta_submitted    (sp_eta_submit)
eta_submitted             → eta_accepted     (sp_eta_resolve)
eta_submitted             → eta_rejected     (sp_eta_resolve)
eta_rejected              → [terminal]       (credit + reissue creates a NEW invoice at eta_pending)
```

```sql
CREATE OR REPLACE FUNCTION sp_eta_submit(
  p_tenant_id uuid, p_invoice_id uuid, p_actor uuid, p_payload jsonb
) RETURNS uuid AS $$
DECLARE v_inv ar_invoice%ROWTYPE; v_attempt int; v_sub_id uuid;
BEGIN
  SELECT * INTO v_inv FROM ar_invoice
   WHERE id = p_invoice_id AND tenant_id = p_tenant_id FOR UPDATE;
  IF v_inv.state <> 'posted' THEN
    RAISE EXCEPTION 'C4: only posted invoices are submitted to ETA';
  END IF;
  IF v_inv.eta_status <> 'eta_pending' THEN
    RAISE EXCEPTION 'C4: invalid ETA transition from %', v_inv.eta_status;
  END IF;

  SELECT COALESCE(max(attempt_no),0) + 1 INTO v_attempt
    FROM eta_submission WHERE invoice_id = p_invoice_id;

  INSERT INTO eta_submission (tenant_id, invoice_id, attempt_no, payload, payload_hash,
                              outcome, submitted_by)
  VALUES (p_tenant_id, p_invoice_id, v_attempt, p_payload,
          encode(sha256(convert_to(p_payload::text,'UTF8')),'hex'), 'submitted', p_actor)
  RETURNING id INTO v_sub_id;

  UPDATE ar_invoice SET eta_status = 'eta_submitted', eta_submitted_at = now()
   WHERE id = p_invoice_id;
  RETURN v_sub_id;
END; $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION sp_eta_resolve(
  p_tenant_id uuid, p_submission_id uuid, p_actor uuid,
  p_outcome text, p_response jsonb, p_eta_uuid text DEFAULT NULL, p_eta_long_id text DEFAULT NULL
) RETURNS void AS $$
DECLARE v_sub eta_submission%ROWTYPE;
BEGIN
  IF p_outcome NOT IN ('accepted','rejected') THEN
    RAISE EXCEPTION 'outcome must be accepted or rejected';
  END IF;
  SELECT * INTO v_sub FROM eta_submission
   WHERE id = p_submission_id AND tenant_id = p_tenant_id AND outcome = 'submitted' FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'no open submission %', p_submission_id; END IF;

  UPDATE eta_submission SET outcome = p_outcome, response = p_response, resolved_at = now()
   WHERE id = p_submission_id;

  UPDATE ar_invoice SET
    eta_status      = CASE WHEN p_outcome = 'accepted' THEN 'eta_accepted' ELSE 'eta_rejected' END,
    eta_uuid        = CASE WHEN p_outcome = 'accepted' THEN p_eta_uuid ELSE eta_uuid END,
    eta_long_id     = CASE WHEN p_outcome = 'accepted' THEN p_eta_long_id ELSE eta_long_id END,
    eta_resolved_at = now()
  WHERE id = v_sub.invoice_id;
END; $$ LANGUAGE plpgsql;
```

## Step 3 — Transport adapter (NestJS) — interface now, real API later

Create `src/eta/eta-transport.interface.ts` and a stub `MockEtaTransport` that returns a
deterministic accepted/rejected response based on a test flag. The real ETA SDK integration
(authentication, document signing with the tenant's certificate, UBL-like JSON structure per ETA
spec) is a FUTURE instruction set — leave a single TODO-free seam: the interface with methods
`submitDocument(payload): Promise<SubmissionResult>` and `getDocumentStatus(uuid)`. Payload
BUILDING (mapping `ar_invoice` → ETA document JSON) goes in `src/eta/eta-payload.builder.ts` and
must be pure (no I/O) so it is testable against ETA sample documents.

Feature flag: `tenant_settings.eta_enabled boolean DEFAULT false`. When false, posting leaves
`eta_status = 'not_applicable'` and no ETA UI is rendered. Default OFF (graceful degradation rule).

## Step 4 — Mutability + UI

- Mutability: ETA columns are NEVER user-editable in any state — they change only through the two procedures. Encode as absent from `field_mutability` editable sets in all states.
- UI: status chip on the invoice header (`pending / submitted / accepted / rejected` with the ETA UUID once accepted); each transition appears in the existing timeline; on `eta_rejected` the ONLY offered action is "Credit & re-issue" which (a) creates a credit note via a chain procedure mirroring Phase 1 patterns, (b) creates a fresh draft invoice copied from the rejected one. Do not implement partial-credit in this phase.
- Arabic-first: the ETA panel labels ship in Arabic and English from day one, using the existing i18n mechanism. If none exists, flag it in your response — do not invent one silently.

## Verification for Phase 3

`db/tests/test_eta_lifecycle.sql` asserting:
1. Submitting a draft invoice raises C4.
2. Skipping states (pending → accepted) raises C4.
3. Payload mutation on a submission row raises.
4. Deleting a submission row raises.
5. Rejected invoice accepts no field edits through the write path.
6. With `eta_enabled = false`, posting leaves status `not_applicable`.

```bash
make verify && make verify-cycles
```

## What you just built

ETA compliance as document truth: every invoice knows where it stands with the tax authority, with
immutable evidence of every submission.

## Next file: 05_PHASE4_P2P.md
