# FILE_01 — Key format + offline verifier + issuer tool

**Model: Opus** (security design). **Effort: Medium.** Branch: `feat/license-key`.

## Goal
One pure function answers "is this license genuine, and what does it allow?" with no internet,
plus a founder-only tool that creates keys. Nothing is enforced yet — this is the core only.

## Before You Start
- `FILE_00_INDEX.md` — locked decisions 1–3, 6, 7 and the edition defaults.
- `config/settings/base.py` — how `APP_VERSION` / `ASSISTANT_ENABLED` settings are defined (mirror
  the `env(...)` style for `LICENSE_MODE`).
- `erp/identity/rbac.py` `MODULES` — the module names an edition lists.
- `requirements.txt` — confirm `cryptography` is pinned (no new dependency).

## Tasks
- [ ] **New app `erp/licensing/`** (models, services, tests; add to `INSTALLED_APPS`).
- [ ] **Payload schema v1** (canonical JSON: sorted keys, UTF-8, no whitespace):
      `v`, `license_id`, `company_name`, `tax_id`, `edition`, `modules[]`, `max_branches`
      (int or null = unlimited), `issued_at`, `maintenance_until`, `ai_until` (date or null).
- [ ] **Key string** = `CND1.` + base64url(payload) + `.` + base64url(Ed25519 signature). Also
      accepted as a `.lic` text file containing the same string.
- [ ] **`services/verify.py`** — `verify(key: str) -> LicenseInfo | LicenseError`. Checks prefix,
      version, signature against the **public key constant** in `erp/licensing/keys.py`, schema,
      and unknown modules. Pure: no DB, no clock (dates are compared by the caller).
      Errors are typed (`malformed`, `bad_signature`, `unsupported_version`) — never a raw traceback.
- [ ] **`EDITIONS`** constant (Basic / Integrated / Enterprise → modules + default max_branches) —
      the issuer uses it; the verifier trusts only the signed `modules` list, not the edition name.
- [ ] **`LICENSE_MODE`** setting: `off` (default) | `enforce`.
- [ ] **Issuer tool** `tools/license/issue_license.py` (NOT a Django command, NOT shipped to
      customers): reads the private key from a path in env `CONDUCTOR_LICENSE_PRIVATE_KEY`, takes
      `--company --tax-id --edition [--max-branches] [--ai-until] [--years 1]`, prints the key and
      writes `<tax_id>.lic`. `--new-keypair` generates a keypair once and prints the public key to
      paste into `keys.py`. Refuses to run if the private key file is inside the repo.
- [ ] `.gitignore`: `*.pem`, `*.lic`, `tools/license/private*`.
- [ ] **Tests** (a throwaway test keypair generated in the test, never the real one): valid key
      round-trips; one flipped byte in payload → `bad_signature`; one flipped byte in signature →
      `bad_signature`; wrong prefix → `malformed`; `v=2` → `unsupported_version`; unknown module →
      error; Arabic company name survives round-trip.

## Smoke test
- [ ] `pytest erp/licensing` green.
- [ ] Issue a key with the tool against a temp keypair → `verify()` returns the same fields.
- [ ] `git grep -n "PRIVATE KEY"` → no hits.
- [ ] Full `pytest` green with `LICENSE_MODE=off` (nothing else changed behaviour).

## After This Session
Commit `feat(licensing): signed key format + offline verifier + issuer tool (license-key FILE_01)`,
rename this file `_done`, update `erp-status`. **The founder generates the real keypair on their
own machine** (`--new-keypair`), keeps the private key off the repo and backed up offline, and the
public key is committed in `keys.py`. Losing the private key = no more renewals can be issued.
