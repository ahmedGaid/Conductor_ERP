#!/usr/bin/env bash
# Conductor ERP — redeploy the free public sales-demo (called by
# .github/workflows/deploy-demo.yml over SSH on every push to `main`; see
# Docs/plan/demo-deploy-plan.md). NOT for a real customer install.
#
# Hard-resets to origin/main (not a ff-only pull) so the demo box can never
# drift from a stray local edit — this is a deploy target, not a workspace.
# Migrations/collectstatic run automatically on `web` boot
# (RUN_MIGRATIONS=true, see deploy/docker/entrypoint.sh) — nothing extra here.
#
# Usage: deploy/demo-redeploy.sh   (run ON the demo VM, from anywhere)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")

cd "$REPO_ROOT"

echo "[demo-redeploy] fetching origin/main…"
git fetch origin main
git reset --hard origin/main

echo "[demo-redeploy] rebuilding image (cached layers reused when unchanged)…"
"${COMPOSE[@]}" build

echo "[demo-redeploy] restarting stack…"
"${COMPOSE[@]}" up -d

echo "[demo-redeploy] done: $(git rev-parse --short HEAD)"
