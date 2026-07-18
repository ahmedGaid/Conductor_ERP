# FILE_03 — Document signing  (Large)

## Goal
Implement ETA's required signing on the submitted document (the stub only SHA-256 hashes). Prove a
signed document is accepted by the ETA sandbox. This is the correctness core of real compliance.

## Before you start (read)
- ETA's CURRENT signing spec — the required method (canonicalization + signature) and any
  hardware/software-certificate requirement. This is volatile and legally load-bearing: look it up
  against official ETA docs, cite the exact version in DECISIONS. Do NOT implement from memory.
- FILE_02 submission path; `eta_adapter.py`

## Tasks
- [ ] Confirm the signing method in force (canonical serialization + signature scheme + cert
      source) with the founder/customer; record in DECISIONS.
- [ ] Implement canonicalization exactly per spec (field order, encoding — a single mismatch fails
      validation).
- [ ] Implement signing with the customer's certificate/key material, sourced from secrets/HSM
      config — never in the repo.
- [ ] Submit signed documents to the sandbox; iterate until ETA returns `valid`.
- [ ] Any new crypto/signing dependency → DECISIONS STOP-gate before install.

## Watch
- Signing correctness is pass/fail with no partial credit — verify against sandbox `valid`, not
  against your own re-hash.
- Certificate/key material is the most sensitive secret in the system — env/secret/HSM only,
  documented handling, never logged.

## Done when
A signed invoice reaches ETA-sandbox status `valid`. Signing key material is external to the repo.
DECISIONS records the exact ETA signing spec version implemented.

## How to test
- Sandbox submit a signed invoice → polls to `valid`.
- Tamper one signed byte → ETA rejects (proves the signature is real, not cosmetic).
- Secret scan of repo → no key material.
