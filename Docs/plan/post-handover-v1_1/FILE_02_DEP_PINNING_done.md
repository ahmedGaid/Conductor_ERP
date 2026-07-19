# FILE_02 — Backend dependency lockfile + Dependabot

## Finding
`requirements.txt` uses loose range pins; several packages (`argon2-cffi`, `pyotp`,
`django-cors-headers`) have NO upper bound. No backend lockfile → non-reproducible installs. No
`.github/dependabot.yml` → no automated CVE alerts. (Frontend already has `package-lock.json`.)

## Tasks
- [x] Introduce a fully-pinned backend lockfile: `pip-compile` (`requirements.in` → pinned
      `requirements.txt`/`requirements.lock`), or equivalent. DECISIONS entry for the chosen tool.
- [x] Add upper bounds to the currently-unbounded packages.
- [x] Add `.github/dependabot.yml` for `pip` (backend) + `npm` (`apps/web`), weekly.
- [x] CI installs from the lockfile so builds are reproducible.

## Done when
Backend installs are lockfile-reproducible; Dependabot opens PRs on the next vulnerable/outdated
release; no unbounded package pins remain.

## How to test
- Fresh venv from the lockfile → identical resolved versions.
- Dependabot config validates in the Actions/Insights tab.

## Closed 2026-07-19 (A)
`requirements.in` is now the loose source (edit this); `pip-compile requirements.in -o
requirements.txt` produces the fully-pinned lockfile the `backend` CI job already installs from
(`pip install -r requirements.txt` — no `ci.yml` change needed, it was already lockfile-shaped
once compiled). Upper bounds added to the three unbounded packages the finding named
(`argon2-cffi<26.0`, `pyotp<3.0`, `django-cors-headers<5.0`, capped one major above the currently
resolved version). `.github/dependabot.yml` added for `pip` + `apps/web` npm, weekly. Verified:
`pip install -r requirements.txt` from the lockfile exits 0; full gate suite re-run after install.
