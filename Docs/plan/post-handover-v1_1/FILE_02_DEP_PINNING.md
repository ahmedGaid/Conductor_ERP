# FILE_02 — Backend dependency lockfile + Dependabot

## Finding
`requirements.txt` uses loose range pins; several packages (`argon2-cffi`, `pyotp`,
`django-cors-headers`) have NO upper bound. No backend lockfile → non-reproducible installs. No
`.github/dependabot.yml` → no automated CVE alerts. (Frontend already has `package-lock.json`.)

## Tasks
- [ ] Introduce a fully-pinned backend lockfile: `pip-compile` (`requirements.in` → pinned
      `requirements.txt`/`requirements.lock`), or equivalent. DECISIONS entry for the chosen tool.
- [ ] Add upper bounds to the currently-unbounded packages.
- [ ] Add `.github/dependabot.yml` for `pip` (backend) + `npm` (`apps/web`), weekly.
- [ ] CI installs from the lockfile so builds are reproducible.

## Done when
Backend installs are lockfile-reproducible; Dependabot opens PRs on the next vulnerable/outdated
release; no unbounded package pins remain.

## How to test
- Fresh venv from the lockfile → identical resolved versions.
- Dependabot config validates in the Actions/Insights tab.
