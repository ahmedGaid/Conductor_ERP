# FILE_05 — LICENSE + support/warranty terms  🟡 Medium

## The finding
No `LICENSE` file at repo root; `pyproject.toml` has no license field. For a customer-hosted
handover this is a legal-clarity gap — the customer receives code with no stated terms of use,
warranty, or support scope.

## This is a founder decision (licensing) + a small doc task
The session surfaces the choice and writes the file the founder picks; it does not decide the
license unilaterally.

## Tasks
- [ ] Ask the founder the license intent:
      - **Proprietary / all-rights-reserved** (single customer, customer-hosted) — most likely for
        a delivered SMB product; OR
      - a permissive/other license if the founder intends otherwise.
- [ ] Write `LICENSE` at repo root with the chosen terms.
- [ ] Add a short `Docs/SUPPORT_TERMS.md` (or a section in the handover guide): what support the
      customer gets, response expectations, update channel, and warranty scope. Keep it one page,
      plain language, bilingual if the customer will read it.
- [ ] Reference the license from `README.md` (the audit noted README omits it) and add a `license`
      field to `pyproject.toml`.

## Watch
- Do not invent legal warranty commitments — state only what the founder confirms. If the founder is
  unsure of exact terms, ship an all-rights-reserved LICENSE + a "support terms to be agreed in the
  service contract" placeholder, and flag it.

## Done when
`LICENSE` exists at root with founder-confirmed terms; README references it; `pyproject.toml` has a
license field; a one-page support/warranty note is in the handover package.

## How to test
- `LICENSE` present at repo root; README links it.
- `Docs/SUPPORT_TERMS.md` (or handover-guide section) present and one page.
