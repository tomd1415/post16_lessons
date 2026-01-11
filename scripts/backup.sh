#!/usr/bin/env bash
#
# Database and Data Backup Script
# Backs up PostgreSQL database and data files with retention policies
#
# Usage:
#   ./scripts/backup.sh [backup_dir] [--retention-days N] [--retention-count N]
#
# Options:
#   backup_dir              Custom backup directory (default: backups/backup_TIMESTAMP)
#   --retention-days N      Delete backups older than N days (default: 30)
#   --retention-count N     Keep only last N backups (default: 14)
#
# Environment Variables:
#   BACKUP_RETENTION_DAYS   Days to keep backups (default: 30)
#   BACKUP_RETENTION_COUNT  Number of backups to keep (default: 14)
#   TLAC_DB_USER           Database user (default: tlac)
#   TLAC_DB_NAME           Database name (default: tlac)
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Default configuration
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-14}"
timestamp="$(date -u +%Y%m%d_%H%M%S)"
dest=""
LOG_FILE="backups/backup.log"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --retention-count)
      RETENTION_COUNT="$2"
      shift 2
      ;;
    *)
      dest="$1"
      shift
      ;;
  esac
done

# Set default destination if not provided
if [ -z "$dest" ]; then
  dest="backups/backup_${timestamp}"
fi

DB_USER="${TLAC_DB_USER:-${POSTGRES_USER:-tlac}}"
DB_NAME="${TLAC_DB_NAME:-${POSTGRES_DB:-tlac}}"

# Ensure backups directory exists
mkdir -p "$(dirname "$dest")"
mkdir -p "$dest"

# Ensure log file exists
touch "$LOG_FILE"

# Logging function
log() {
  local message="[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $@"
  echo "$message" | tee -a "$LOG_FILE"
}

log "INFO: Starting backup to $dest"
log "INFO: Database: $DB_NAME (user: $DB_USER)"

# Check if Docker Compose is running
if ! docker compose ps db | grep -q "Up"; then
  log "ERROR: Database container is not running"
  exit 1
fi

# Backup database
log "INFO: Backing up database..."
if docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" 2>&1 | gzip > "$dest/db.sql.gz"; then
  DB_SIZE=$(du -h "$dest/db.sql.gz" | cut -f1)
  log "INFO: Database backup complete (size: $DB_SIZE)"
else
  log "ERROR: Database backup failed"
  rm -rf "$dest"
  exit 1
fi

# Backup data files
log "INFO: Backing up data files..."
if [ -d "reports" ]; then
  tar -czf "$dest/data.tar.gz" data reports 2>&1 | tee -a "$LOG_FILE" || true
else
  tar -czf "$dest/data.tar.gz" data 2>&1 | tee -a "$LOG_FILE" || true
fi

if [ -f "$dest/data.tar.gz" ]; then
  DATA_SIZE=$(du -h "$dest/data.tar.gz" | cut -f1)
  log "INFO: Data backup complete (size: $DATA_SIZE)"
else
  log "WARN: Data backup may have failed or no data to backup"
fi

# Create backup metadata
cat > "$dest/backup.meta" <<EOF
{
  "timestamp": "$timestamp",
  "database": "$DB_NAME",
  "db_size": "$DB_SIZE",
  "data_size": "${DATA_SIZE:-0}",
  "created_at": "$(date -Iseconds)"
}
EOF

TOTAL_SIZE=$(du -sh "$dest" | cut -f1)
log "INFO: Backup complete (total size: $TOTAL_SIZE)"

# Apply retention policy - delete backups older than RETENTION_DAYS
log "INFO: Applying retention policy (${RETENTION_DAYS} days, keep last ${RETENTION_COUNT})"

DELETED_BY_AGE=0
if [ -d "backups" ]; then
  while IFS= read -r old_backup; do
    if [ -n "$old_backup" ] && [ -d "$old_backup" ]; then
      log "INFO: Deleting old backup (by age): $(basename "$old_backup")"
      rm -rf "$old_backup"
      ((DELETED_BY_AGE++)) || true
    fi
  done < <(find backups -maxdepth 1 -name "backup_*" -type d -mtime "+${RETENTION_DAYS}" 2>/dev/null || true)
fi

# Keep only last N backups
BACKUP_COUNT=$(find backups -maxdepth 1 -name "backup_*" -type d 2>/dev/null | wc -l || echo "0")
if [ "${BACKUP_COUNT}" -gt "${RETENTION_COUNT}" ]; then
  EXCESS=$((BACKUP_COUNT - RETENTION_COUNT))
  log "INFO: Found ${BACKUP_COUNT} backups, removing ${EXCESS} oldest"

  DELETED_BY_COUNT=0
  while IFS= read -r old_backup; do
    if [ -n "$old_backup" ] && [ -d "$old_backup" ]; then
      log "INFO: Deleting old backup (by count): $(basename "$old_backup")"
      rm -rf "$old_backup"
      ((DELETED_BY_COUNT++)) || true
    fi
  done < <(find backups -maxdepth 1 -name "backup_*" -type d -printf '%T@ %p\n' 2>/dev/null | sort -n | head -n "${EXCESS}" | cut -d' ' -f2- || true)
fi

TOTAL_DELETED=$((DELETED_BY_AGE + ${DELETED_BY_COUNT:-0}))
if [ "${TOTAL_DELETED}" -gt 0 ]; then
  log "INFO: Deleted ${TOTAL_DELETED} old backup(s)"
fi

# Show current backup status
CURRENT_COUNT=$(find backups -maxdepth 1 -name "backup_*" -type d 2>/dev/null | wc -l || echo "0")
TOTAL_BACKUPS_SIZE=$(du -sh backups 2>/dev/null | cut -f1 || echo "0")

log "INFO: Backup retention summary:"
log "INFO:   Current backups: ${CURRENT_COUNT}"
log "INFO:   Total size: ${TOTAL_BACKUPS_SIZE}"
log "INFO:   Latest: $(basename "$dest")"
log "INFO: Backup process completed successfully"

exit 0
