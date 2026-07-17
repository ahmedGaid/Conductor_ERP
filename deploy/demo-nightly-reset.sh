#!/usr/bin/env bash
# Conductor ERP — nightly demo reset (crontab, e.g. `0 3 * * *`; see
# Docs/plan/demo-deploy-plan.md). Wipes the demo db/storage/redis volumes and
# reseeds from scratch, so the public sales demo always starts the day clean
# regardless of what a prospect (or you, live) did to it the day before.
#
# DESTRUCTIVE BY DESIGN. Never point this at a real customer install.
#
# Usage: deploy/demo-nightly-reset.sh   (run ON the demo VM; add to crontab)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")

cd "$REPO_ROOT"

echo "[demo-reset] tearing down stack + volumes…"
"${COMPOSE[@]}" down -v

echo "[demo-reset] starting fresh stack…"
"${COMPOSE[@]}" up -d

echo "[demo-reset] waiting for 'web' to report healthy…"
for _ in $(seq 1 30); do
  if "${COMPOSE[@]}" exec -T web curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

echo "[demo-reset] seeding demo data…"
"${COMPOSE[@]}" exec -T web python manage.py seed_identity
"${COMPOSE[@]}" exec -T web python manage.py seed_accounting
"${COMPOSE[@]}" exec -T web python scripts/seed_demo.py

echo "[demo-reset] done."
