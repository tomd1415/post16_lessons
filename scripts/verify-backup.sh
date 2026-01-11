#!/usr/bin/env bash
#
# Backup Verification Script
# Verifies integrity of backup files
#
# Usage:
#   ./scripts/verify-backup.sh <backup_dir>
#
# Example:
#   ./scripts/verify-backup.sh backups/backup_20260111_140000
#

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup_dir>"
  echo ""
  echo "Example:"
  echo "  $0 backups/backup_20260111_140000"
  exit 1
fi

BACKUP_DIR="$1"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Backup Verification ===${NC}"
echo "Verifying: $BACKUP_DIR"
echo ""

# Check backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
  echo -e "${RED}✗ Backup directory does not exist${NC}"
  exit 1
fi

ERRORS=0

# Check database backup exists
if [ -f "$BACKUP_DIR/db.sql.gz" ]; then
  echo -e "${GREEN}✓${NC} Database backup file exists"

  # Test database dump integrity
  if gunzip -t "$BACKUP_DIR/db.sql.gz" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Database backup is valid (gzip integrity)"

    # Check file size
    DB_SIZE=$(stat -f%z "$BACKUP_DIR/db.sql.gz" 2>/dev/null || stat -c%s "$BACKUP_DIR/db.sql.gz" 2>/dev/null || echo "0")
    if [ "$DB_SIZE" -gt 1024 ]; then
      echo -e "${GREEN}✓${NC} Database backup has reasonable size ($(numfmt --to=iec $DB_SIZE 2>/dev/null || echo "${DB_SIZE} bytes"))"
    else
      echo -e "${RED}✗${NC} Database backup is suspiciously small ($(numfmt --to=iec $DB_SIZE 2>/dev/null || echo "${DB_SIZE} bytes"))"
      ((ERRORS++))
    fi
  else
    echo -e "${RED}✗${NC} Database backup is corrupted"
    ((ERRORS++))
  fi
else
  echo -e "${RED}✗${NC} Database backup file missing"
  ((ERRORS++))
fi

echo ""

# Check data backup exists
if [ -f "$BACKUP_DIR/data.tar.gz" ]; then
  echo -e "${GREEN}✓${NC} Data backup file exists"

  # Test data archive integrity
  if tar -tzf "$BACKUP_DIR/data.tar.gz" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Data backup is valid (tar integrity)"

    # Check file size
    DATA_SIZE=$(stat -f%z "$BACKUP_DIR/data.tar.gz" 2>/dev/null || stat -c%s "$BACKUP_DIR/data.tar.gz" 2>/dev/null || echo "0")
    if [ "$DATA_SIZE" -gt 512 ]; then
      echo -e "${GREEN}✓${NC} Data backup has reasonable size ($(numfmt --to=iec $DATA_SIZE 2>/dev/null || echo "${DATA_SIZE} bytes"))"
    else
      echo -e "${YELLOW}⚠${NC} Data backup is very small ($(numfmt --to=iec $DATA_SIZE 2>/dev/null || echo "${DATA_SIZE} bytes"))"
    fi
  else
    echo -e "${RED}✗${NC} Data backup is corrupted"
    ((ERRORS++))
  fi
else
  echo -e "${YELLOW}⚠${NC} Data backup file missing (may be intentional if no data files)"
fi

echo ""

# Check metadata exists
if [ -f "$BACKUP_DIR/backup.meta" ]; then
  echo -e "${GREEN}✓${NC} Backup metadata file exists"

  # Validate JSON
  if command -v jq &> /dev/null; then
    if jq empty "$BACKUP_DIR/backup.meta" 2>/dev/null; then
      echo -e "${GREEN}✓${NC} Metadata is valid JSON"

      # Display metadata
      echo ""
      echo "Backup metadata:"
      jq . "$BACKUP_DIR/backup.meta" | sed 's/^/  /'
    else
      echo -e "${RED}✗${NC} Metadata is invalid JSON"
      ((ERRORS++))
    fi
  else
    echo -e "${YELLOW}⚠${NC} Cannot validate JSON (jq not installed)"
  fi
else
  echo -e "${YELLOW}⚠${NC} Backup metadata file missing"
fi

echo ""
echo "================================"

if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}✓ Backup verification passed${NC}"
  echo "This backup appears to be intact and can be used for restoration."
  exit 0
else
  echo -e "${RED}✗ Backup verification failed with $ERRORS error(s)${NC}"
  echo "This backup may be corrupted or incomplete. Do not rely on it for restoration."
  exit 1
fi
