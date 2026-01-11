# Backup and Recovery Guide

Comprehensive guide for backing up and restoring the TLAC (Thinking Like a Coder) application.

## Overview

The backup system provides:
- **Automated database backups** - PostgreSQL dumps with compression
- **Data file backups** - User-generated data and reports
- **Retention policies** - Automatic cleanup of old backups
- **Easy restoration** - Simple restore from any backup point
- **Cron integration** - Scheduled automated backups

## Table of Contents

1. [Quick Start](#quick-start)
2. [Manual Backups](#manual-backups)
3. [Automated Backups](#automated-backups)
4. [Restoration](#restoration)
5. [Backup Management](#backup-management)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

## Quick Start

### Create a backup now

```bash
./scripts/backup.sh
```

### Set up daily automated backups

```bash
./scripts/setup-backup-cron.sh daily
```

### Restore from a backup

```bash
./scripts/restore.sh backups/backup_20260111_140000 --force
```

## Manual Backups

### Basic Backup

Create a backup with default settings:

```bash
./scripts/backup.sh
```

This creates a timestamped backup directory in `backups/backup_YYYYMMDD_HHMMSS/` containing:
- `db.sql.gz` - Compressed PostgreSQL dump
- `data.tar.gz` - Compressed data files
- `backup.meta` - Metadata (timestamp, sizes, etc.)

### Custom Backup Location

Specify a custom backup directory:

```bash
./scripts/backup.sh /path/to/custom/backup
```

### Configure Retention

Override default retention policies:

```bash
# Keep backups for 60 days and maintain last 30 backups
./scripts/backup.sh --retention-days 60 --retention-count 30
```

### Environment Variables

Configure via environment variables:

```bash
export BACKUP_RETENTION_DAYS=90
export BACKUP_RETENTION_COUNT=30
./scripts/backup.sh
```

## Automated Backups

### Setting Up Cron Jobs

Use the setup script to configure automated backups:

```bash
# Daily at 2 AM (default)
./scripts/setup-backup-cron.sh daily

# Every hour
./scripts/setup-backup-cron.sh hourly

# Weekly on Sunday at 2 AM
./scripts/setup-backup-cron.sh weekly

# Custom schedule
./scripts/setup-backup-cron.sh custom
# Then enter your cron expression, e.g., "0 3 * * *" for 3 AM daily
```

### Cron Expression Examples

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Every hour | `0 * * * *` | At the start of every hour |
| Daily at 2 AM | `0 2 * * *` | Once per day at 2:00 AM |
| Twice daily | `0 2,14 * * *` | At 2:00 AM and 2:00 PM |
| Weekly | `0 2 * * 0` | Sunday at 2:00 AM |
| Monthly | `0 2 1 * *` | First of month at 2:00 AM |

### Manual Cron Setup

If you prefer to set up cron manually:

```bash
crontab -e
```

Add this line:

```cron
# TLAC Automated Backup - Daily at 2:00 AM
0 2 * * * cd /path/to/post16_lessons && ./scripts/backup.sh >> /path/to/post16_lessons/backups/backup.log 2>&1
```

### Verifying Cron Jobs

Check installed cron jobs:

```bash
crontab -l
```

View backup logs:

```bash
tail -f backups/backup.log
```

## Restoration

### Prerequisites

**WARNING**: Restoration will **overwrite** all current data. Always verify you have a recent backup before restoring.

### Restore from Backup

```bash
# List available backups
ls -lth backups/

# Restore from specific backup
./scripts/restore.sh backups/backup_20260111_140000 --force
```

The `--force` flag is **required** to prevent accidental data loss.

### What Gets Restored

The restore process:
1. **Drops and recreates** the database schema
2. **Restores** all database tables and data
3. **Extracts** data files and reports (if present)

### Restoration Steps

1. **Stop the application** (recommended):
   ```bash
   docker compose down
   ```

2. **Restore from backup**:
   ```bash
   ./scripts/restore.sh backups/backup_20260111_140000 --force
   ```

3. **Restart the application**:
   ```bash
   docker compose up -d
   ```

4. **Verify restoration**:
   - Check application logs
   - Log in and verify data
   - Check recent activity

### Partial Restoration

To restore only the database (without data files):

```bash
# Manual database-only restore
gunzip -c backups/backup_20260111_140000/db.sql.gz | \
  docker compose exec -T db psql -U tlac -d tlac
```

## Backup Management

### Retention Policies

**Default Settings**:
- **Age-based**: Delete backups older than 30 days
- **Count-based**: Keep only the last 14 backups

These policies run automatically after each backup.

### Viewing Backup Status

Check current backup status:

```bash
ls -lth backups/
```

View backup metadata:

```bash
cat backups/backup_20260111_140000/backup.meta
```

Example metadata:
```json
{
  "timestamp": "20260111_140000",
  "database": "tlac",
  "db_size": "12M",
  "data_size": "2.3M",
  "created_at": "2026-01-11T14:00:00Z"
}
```

### Manual Cleanup

Remove specific backups:

```bash
rm -rf backups/backup_20260101_020000
```

Remove backups older than 60 days:

```bash
find backups -maxdepth 1 -name "backup_*" -type d -mtime +60 -exec rm -rf {} \;
```

### Disk Space Management

Check backup disk usage:

```bash
du -sh backups/
du -h backups/ | sort -h
```

Monitor available disk space:

```bash
df -h backups/
```

## Monitoring

### Backup Logs

All backup operations are logged to `backups/backup.log`:

```bash
# View recent logs
tail -n 50 backups/backup.log

# Monitor in real-time
tail -f backups/backup.log

# Search for errors
grep -i error backups/backup.log
```

### Log Format

```
[2026-01-11 14:00:00 UTC] INFO: Starting backup to backups/backup_20260111_140000
[2026-01-11 14:00:01 UTC] INFO: Database: tlac (user: tlac)
[2026-01-11 14:00:05 UTC] INFO: Database backup complete (size: 12M)
[2026-01-11 14:00:10 UTC] INFO: Data backup complete (size: 2.3M)
[2026-01-11 14:00:10 UTC] INFO: Backup complete (total size: 15M)
[2026-01-11 14:00:11 UTC] INFO: Deleted 2 old backup(s)
[2026-01-11 14:00:11 UTC] INFO: Backup process completed successfully
```

### Backup Verification

Verify a backup is complete:

```bash
BACKUP_DIR="backups/backup_20260111_140000"

# Check all files exist
[ -f "$BACKUP_DIR/db.sql.gz" ] && echo "✓ Database backup exists"
[ -f "$BACKUP_DIR/data.tar.gz" ] && echo "✓ Data backup exists"
[ -f "$BACKUP_DIR/backup.meta" ] && echo "✓ Metadata exists"

# Test database dump integrity
gunzip -t "$BACKUP_DIR/db.sql.gz" && echo "✓ Database backup is valid"

# Test data archive integrity
tar -tzf "$BACKUP_DIR/data.tar.gz" > /dev/null && echo "✓ Data backup is valid"
```

### Alerting

Set up email notifications for backup failures (requires mailutils):

```bash
# Add to crontab
0 2 * * * cd /path/to/post16_lessons && ./scripts/backup.sh || echo "Backup failed!" | mail -s "TLAC Backup Failed" admin@example.com
```

## Troubleshooting

### Common Issues

#### "Database container is not running"

**Cause**: PostgreSQL container is not running.

**Solution**:
```bash
docker compose up -d db
# Wait for database to be ready
docker compose exec db pg_isready -U tlac
```

#### "Permission denied"

**Cause**: Backup script is not executable.

**Solution**:
```bash
chmod +x scripts/backup.sh
chmod +x scripts/restore.sh
chmod +x scripts/setup-backup-cron.sh
```

#### "No space left on device"

**Cause**: Disk is full.

**Solution**:
```bash
# Check disk usage
df -h

# Remove old backups manually
find backups -maxdepth 1 -name "backup_*" -type d -mtime +30 -exec rm -rf {} \;

# Adjust retention policy
./scripts/backup.sh --retention-days 14 --retention-count 7
```

#### Backup takes too long

**Cause**: Large database or slow disk.

**Solution**:
- Run backups during off-peak hours
- Consider incremental backups (not currently implemented)
- Use faster storage for backups
- Adjust cron schedule to less frequent backups

#### Restore fails with "database does not exist"

**Cause**: Database container issue.

**Solution**:
```bash
# Restart database container
docker compose restart db

# Recreate database if needed
docker compose exec db psql -U tlac -c "CREATE DATABASE tlac;"
```

### Testing Backups

**Regular testing is critical!** Test your backups monthly:

1. Create a test restore environment
2. Restore latest backup
3. Verify all data is present
4. Test application functionality
5. Document any issues

### Recovery Testing Checklist

- [ ] Backup file exists and is not corrupted
- [ ] Database dump can be extracted
- [ ] Data archive can be extracted
- [ ] Restore completes without errors
- [ ] Application starts successfully
- [ ] Users can log in
- [ ] Recent data is present
- [ ] All features work correctly

## Best Practices

1. **Test restores regularly** - Untested backups are useless
2. **Monitor backup logs** - Check for failures promptly
3. **Store backups off-site** - Copy to remote storage periodically
4. **Document procedures** - Keep this guide updated
5. **Automate everything** - Manual processes are error-prone
6. **Verify retention** - Ensure old backups are deleted
7. **Check disk space** - Monitor backup storage capacity
8. **Encrypt sensitive backups** - Add encryption for off-site storage

## Off-Site Backups

For production deployments, copy backups to remote storage:

### Using rsync

```bash
# Daily sync to remote server
rsync -avz --delete \
  backups/ \
  user@backup-server:/backups/tlac/
```

### Using rclone (for cloud storage)

```bash
# Install rclone
# Configure with: rclone config

# Sync to cloud storage
rclone sync backups/ remote:tlac-backups/
```

### Add to cron

```bash
# Daily backup + off-site sync
0 2 * * * cd /path/to/post16_lessons && ./scripts/backup.sh && rsync -az backups/ user@remote:/backups/
```

## Security Considerations

### Backup Encryption

Encrypt backups before off-site storage:

```bash
# Encrypt backup
gpg --symmetric --cipher-algo AES256 backups/backup_20260111_140000/db.sql.gz

# Decrypt backup
gpg backups/backup_20260111_140000/db.sql.gz.gpg
```

### Access Control

Restrict backup file permissions:

```bash
# Backups readable only by owner
chmod 700 backups
chmod 600 backups/backup_*/db.sql.gz
```

### Secure Storage

- Store backups on encrypted filesystems
- Use secure transfer protocols (SFTP, SCP, HTTPS)
- Implement access logging for backup files
- Regular security audits of backup procedures

## Support

For issues or questions:
1. Check the [troubleshooting section](#troubleshooting)
2. Review backup logs in `backups/backup.log`
3. Check Docker container logs: `docker compose logs db`
4. Consult the main documentation in `docs/`
