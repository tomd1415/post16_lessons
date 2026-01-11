#!/usr/bin/env bash
#
# Setup Automated Backup Cron Job
# Configures cron to run backups automatically
#
# Usage:
#   ./scripts/setup-backup-cron.sh [schedule]
#
# Schedule formats:
#   daily       - Run at 2 AM daily (default)
#   hourly      - Run hourly
#   weekly      - Run at 2 AM every Sunday
#   custom      - Prompt for custom cron expression
#
# Examples:
#   ./scripts/setup-backup-cron.sh daily
#   ./scripts/setup-backup-cron.sh weekly
#   ./scripts/setup-backup-cron.sh custom
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_SCRIPT="$ROOT_DIR/scripts/backup.sh"
SCHEDULE="${1:-daily}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Automated Backup Setup ===${NC}"
echo ""

# Check if backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
  echo -e "${RED}ERROR: Backup script not found at $BACKUP_SCRIPT${NC}"
  exit 1
fi

# Make sure backup script is executable
chmod +x "$BACKUP_SCRIPT"

# Determine cron expression
case "$SCHEDULE" in
  daily)
    CRON_EXPR="0 2 * * *"
    DESCRIPTION="Daily at 2:00 AM"
    ;;
  hourly)
    CRON_EXPR="0 * * * *"
    DESCRIPTION="Hourly"
    ;;
  weekly)
    CRON_EXPR="0 2 * * 0"
    DESCRIPTION="Weekly on Sunday at 2:00 AM"
    ;;
  custom)
    echo "Enter custom cron expression (e.g., '0 3 * * *' for 3 AM daily):"
    read -r CRON_EXPR
    DESCRIPTION="Custom schedule: $CRON_EXPR"
    ;;
  *)
    echo -e "${RED}ERROR: Invalid schedule. Use: daily, hourly, weekly, or custom${NC}"
    exit 1
    ;;
esac

# Create cron job entry
CRON_JOB="$CRON_EXPR cd $ROOT_DIR && $BACKUP_SCRIPT >> $ROOT_DIR/backups/backup.log 2>&1"
CRON_COMMENT="# TLAC Automated Backup - $DESCRIPTION"

echo "Schedule: $DESCRIPTION"
echo "Cron expression: $CRON_EXPR"
echo "Backup script: $BACKUP_SCRIPT"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "TLAC Automated Backup"; then
  echo -e "${YELLOW}WARNING: TLAC backup cron job already exists${NC}"
  echo ""
  echo "Current cron jobs:"
  crontab -l | grep -A1 "TLAC Automated Backup" || true
  echo ""
  read -p "Do you want to replace the existing cron job? (y/N): " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi

  # Remove existing TLAC backup cron jobs
  (crontab -l 2>/dev/null | grep -v "TLAC Automated Backup" | grep -v "$BACKUP_SCRIPT") | crontab -
  echo "Removed existing cron job"
fi

# Add new cron job
(crontab -l 2>/dev/null; echo ""; echo "$CRON_COMMENT"; echo "$CRON_JOB") | crontab -

echo -e "${GREEN}✓ Cron job installed successfully${NC}"
echo ""
echo "Cron job details:"
echo "  Schedule: $DESCRIPTION"
echo "  Command: $CRON_JOB"
echo ""
echo "To view all cron jobs:"
echo "  crontab -l"
echo ""
echo "To remove this cron job:"
echo "  crontab -e"
echo "  (then delete the lines with 'TLAC Automated Backup')"
echo ""
echo "Backup logs will be written to:"
echo "  $ROOT_DIR/backups/backup.log"
echo ""
echo -e "${GREEN}Setup complete!${NC}"

exit 0
