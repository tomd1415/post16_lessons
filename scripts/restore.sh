#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ $# -lt 1 ]; then
  echo "Usage: scripts/restore.sh <backup_dir> [--force]"
  exit 1
fi

BACKUP_DIR="$1"
FORCE="${2:-}"

if [ "$FORCE" != "--force" ]; then
  echo "Refusing to restore without --force (this will overwrite existing data)."
  exit 1
fi

if [ ! -f "$BACKUP_DIR/db.sql.gz" ]; then
  echo "Missing $BACKUP_DIR/db.sql.gz"
  exit 1
fi

DB_USER="${TLAC_DB_USER:-${POSTGRES_USER:-tlac}}"
DB_NAME="${TLAC_DB_NAME:-${POSTGRES_DB:-tlac}}"

echo "Restoring database..."
docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c "$BACKUP_DIR/db.sql.gz" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME"

if [ -f "$BACKUP_DIR/data.tar.gz" ]; then
  echo "Restoring data files..."
  tar -xzf "$BACKUP_DIR/data.tar.gz" -C "$ROOT_DIR"
fi

echo "Restore complete."
