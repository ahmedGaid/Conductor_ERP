#!/usr/bin/env bash
# Conductor ERP - one-command backup for the Docker Compose deployment.
#
# Dumps the PostgreSQL database out of the `db` container (custom format, restorable
# with restore.sh / pg_restore) into a timestamped folder on the HOST, so the backup
# lives OUTSIDE the Docker volume and is trivial to copy offsite. Best-effort also
# archives the document/report storage volume. Prunes runs older than the retention
# window. Mirrors the bare-metal deploy/backup/backup.ps1.
#
# Usage (a self-hoster needs no flags - `deploy/docker/backup.sh` just works):
#   deploy/docker/backup.sh [OUT_DIR] [RETAIN_DAYS]
#     OUT_DIR      where to write backups on the host (default <repo>/backups)
#     RETAIN_DAYS  keep this many days of runs (default 14)
#
# Restore a dump with deploy/docker/restore.sh. Verify a restore PERIODICALLY into a
# scratch database - an untested backup is not a backup.
set -euo pipefail

# Resolve the repo root from this script's location so it runs from anywhere.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE=(docker compose -f "$REPO_ROOT/docker-compose.yml")

OUT_DIR="${1:-$REPO_ROOT/backups}"
RETAIN_DAYS="${2:-14}"

STAMP="$(date +%Y-%m-%d_%H%M%S)"
RUN_DIR="$OUT_DIR/$STAMP"
mkdir -p "$RUN_DIR"

# 1. Database: custom-format dump (the canonical, restorable artifact). pg_dump runs
#    inside the container over the local socket, reading the container's own
#    POSTGRES_USER/POSTGRES_DB - no password handling on the host. `-T` disables the
#    pseudo-TTY so the binary dump streams to the host file uncorrupted.
echo "Dumping database from the 'db' container -> $RUN_DIR/db.dump"
"${COMPOSE[@]}" exec -T db sh -c \
  'pg_dump --format=custom --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  > "$RUN_DIR/db.dump"

# 2. Document storage (best-effort; a fresh install with no uploads simply skips it).
STORAGE_NOTE="skipped (empty or absent)"
if "${COMPOSE[@]}" exec -T web sh -c '[ -d /app/storage ] && [ -n "$(ls -A /app/storage 2>/dev/null)" ]' 2>/dev/null; then
  echo "Archiving document storage -> $RUN_DIR/storage.tar.gz"
  "${COMPOSE[@]}" exec -T web sh -c 'tar -czf - -C /app/storage .' > "$RUN_DIR/storage.tar.gz"
  STORAGE_NOTE="storage.tar.gz"
fi

# 3. Manifest with the exact restore command (so a future operator needs no notes).
DB_BYTES="$(wc -c < "$RUN_DIR/db.dump" | tr -d ' ')"
cat > "$RUN_DIR/MANIFEST.txt" <<EOF
Conductor ERP backup (Docker Compose)
Taken:    $STAMP
Database: db.dump ($DB_BYTES bytes, pg_dump custom format)
Storage:  $STORAGE_NOTE

Restore (into a SCRATCH db to test, or the live db to recover):
  deploy/docker/restore.sh "$RUN_DIR/db.dump"            # test into erp_restore_test
  deploy/docker/restore.sh "$RUN_DIR/db.dump" --force    # RECOVER the live database
EOF

# 4. Retention: drop run folders older than RETAIN_DAYS.
find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETAIN_DAYS" \
  -exec sh -c 'echo "Pruning old backup $1"; rm -rf "$1"' _ {} \; 2>/dev/null || true

echo "Backup complete: $RUN_DIR"
