#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

timestamp="$(date -u +%Y%m%d_%H%M%S)"
dest="${1:-backups/backup_${timestamp}}"

DB_USER="${TLAC_DB_USER:-${POSTGRES_USER:-tlac}}"
DB_NAME="${TLAC_DB_NAME:-${POSTGRES_DB:-tlac}}"

mkdir -p "$dest"
echo "Writing backup to $dest"

docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$dest/db.sql.gz"

if [ -d "reports" ]; then
  tar -czf "$dest/data.tar.gz" data reports
else
  tar -czf "$dest/data.tar.gz" data
fi

echo "Backup complete."
