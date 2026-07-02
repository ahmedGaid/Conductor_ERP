#!/usr/bin/env bash
# Conductor ERP - restore a Docker Compose deployment's database from a backup.
#
# Feeds a db.dump (custom format, from backup.sh) into the `db` container with
# pg_restore --clean --if-exists. By DEFAULT it restores into a SCRATCH database
# (erp_restore_test) so you can verify a backup without touching production - an
# untested backup is not a backup. Restoring the LIVE database is destructive and
# requires --force. Mirrors the bare-metal deploy/backup/restore.ps1.
#
# Usage:
#   deploy/docker/restore.sh <DUMP_PATH> [TARGET_DB] [--force]
#     DUMP_PATH   path to db.dump on the host (required)
#     TARGET_DB   database to restore INTO (default erp_restore_test)
#     --force     required to restore into the LIVE database (POSTGRES_DB)
#
# Real recovery: stop the app first so nothing writes mid-restore, then --force:
#   docker compose stop web worker beat
#   deploy/docker/restore.sh <DUMP_PATH> --force
#   docker compose start web worker beat
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")

DUMP_PATH=""
TARGET_DB="erp_restore_test"
FORCE=false
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=true ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) if [ -z "$DUMP_PATH" ]; then DUMP_PATH="$arg"; else TARGET_DB="$arg"; fi ;;
  esac
done

[ -n "$DUMP_PATH" ] || { echo "usage: restore.sh <DUMP_PATH> [TARGET_DB] [--force]" >&2; exit 2; }
[ -f "$DUMP_PATH" ] || { echo "dump not found: $DUMP_PATH" >&2; exit 1; }

# Live DB name = the container's POSTGRES_DB. Refuse to overwrite it without --force,
# as a guard against an accidental production restore.
LIVE_DB="$("${COMPOSE[@]}" exec -T db sh -c 'printf %s "$POSTGRES_DB"' | tr -d '\r')"
if [ "$TARGET_DB" = "$LIVE_DB" ] && [ "$FORCE" != true ]; then
  echo "Refusing to restore into the LIVE database '$LIVE_DB' without --force." >&2
  echo "To TEST a backup, omit the name to restore into the scratch db 'erp_restore_test'." >&2
  exit 3
fi

# Ensure the target database exists (create the scratch db on first run). The
# existence-check SQL is passed via -e so the target name needs no nested quoting.
echo "Ensuring target database '$TARGET_DB' exists..."
EXISTS_SQL="SELECT 1 FROM pg_database WHERE datname = '$TARGET_DB'"
"${COMPOSE[@]}" exec -T -e TARGET_DB="$TARGET_DB" -e EXISTS_SQL="$EXISTS_SQL" db sh -c \
  'psql -U "$POSTGRES_USER" -d postgres -tAc "$EXISTS_SQL" | grep -q 1 || createdb -U "$POSTGRES_USER" "$TARGET_DB"'

echo "Restoring $DUMP_PATH -> database '$TARGET_DB' (clean + if-exists)..."
# pg_restore can exit non-zero on benign "does not exist, skipping" notices with
# --clean on a fresh db; surface it as a warning, then verify the data below.
if ! "${COMPOSE[@]}" exec -T -e TARGET_DB="$TARGET_DB" db sh -c \
  'pg_restore --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$TARGET_DB"' \
  < "$DUMP_PATH"; then
  echo "WARNING: pg_restore exited non-zero (often just --clean drop notices on a fresh db). Verify the counts below." >&2
fi

echo "Verifying restored row counts (a few core tables)..."
COUNT_SQL="SELECT 'accounts' AS object, count(*) FROM accounting_account
  UNION ALL SELECT 'journals', count(*) FROM accounting_journal_entry
  UNION ALL SELECT 'users', count(*) FROM identity_user;"
"${COMPOSE[@]}" exec -T -e TARGET_DB="$TARGET_DB" -e COUNT_SQL="$COUNT_SQL" db sh -c \
  'psql -U "$POSTGRES_USER" -d "$TARGET_DB" -c "$COUNT_SQL"'

echo "Restore into '$TARGET_DB' finished."
if [ "$TARGET_DB" != "$LIVE_DB" ]; then
  echo "This was a TEST restore into a scratch db. For a full drill, point a throwaway"
  echo "DATABASE_URL at '$TARGET_DB' and run the app/gates against it."
fi
