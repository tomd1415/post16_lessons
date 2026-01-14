# Production Deployment Guide

Comprehensive guide for deploying TLAC (Thinking Like a Coder) to production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Security Hardening](#security-hardening)
4. [Database Setup](#database-setup)
5. [Docker Deployment](#docker-deployment)
6. [Reverse Proxy Configuration](#reverse-proxy-configuration)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Monitoring Setup](#monitoring-setup)
9. [Backup Configuration](#backup-configuration)
10. [Scaling Considerations](#scaling-considerations)
11. [Maintenance Procedures](#maintenance-procedures)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB SSD | 50+ GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Required Software

```bash
# Docker Engine 24.0+
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose 2.20+
sudo apt install docker-compose-plugin

# Verify installations
docker --version
docker compose version
```

---

## Environment Configuration

### 1. Create Production Environment File

```bash
# Copy example and customize
cp .env.example .env.production
chmod 600 .env.production
```

Use the file with Docker Compose:
```bash
docker compose --env-file .env.production -f compose.yml -f compose.prod.yml up -d
```

### 2. Required Environment Variables

```bash
# .env.production

# ============================================
# DATABASE
# ============================================
POSTGRES_USER=tlac_prod
POSTGRES_PASSWORD=<GENERATE_STRONG_PASSWORD>
POSTGRES_DB=tlac_production
# Only needed when running the API outside compose:
DATABASE_URL=postgresql+psycopg://tlac_prod:<PASSWORD>@db:5432/tlac_production

# ============================================
# SESSION
# ============================================
SESSION_TTL_MINUTES=480
SESSION_COOKIE_NAME=tlac_session

# ============================================
# PYTHON RUNNER
# ============================================
RUNNER_ENABLED=1
RUNNER_IMAGE=post16_lessons-api
RUNNER_DOCKER_HOST=unix:///var/run/docker.sock
RUNNER_DOCKER_API_VERSION=1.50
RUNNER_TIMEOUT_SEC=3
RUNNER_MEMORY_MB=128
RUNNER_CPUS=0.5
RUNNER_PIDS_LIMIT=64
RUNNER_TMPFS_MB=32
RUNNER_MAX_OUTPUT=20000
RUNNER_MAX_CODE_SIZE=20000
RUNNER_MAX_FILES=8
RUNNER_MAX_FILE_BYTES=50000
RUNNER_MAX_ARCHIVE_BYTES=250000
RUNNER_CONCURRENCY=2
RUNNER_AUTO_PULL=0

# ============================================
# DATA RETENTION
# ============================================
RETENTION_YEARS=2

# ============================================
# ATTENTION THRESHOLDS
# ============================================
ATTENTION_LIMIT=200
ATTENTION_REVISION_THRESHOLD=5
ATTENTION_STUCK_DAYS=7

# ============================================
# PATHS
# ============================================
STATIC_ROOT=/srv
LESSON_MANIFEST_PATH=/srv/lessons/manifest.json
LINK_OVERRIDES_PATH=/data/link-overrides.json
```

### 3. Generate Secure Passwords

```bash
# Generate database password
openssl rand -base64 32

# Generate backup encryption key (if using encrypted backups)
openssl rand -base64 32
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Verify
sudo ufw status
```

### 2. Disable Root SSH

```bash
# /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes

sudo systemctl restart sshd
```

### 3. Docker Security

```bash
# compose.prod.yml security additions

services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL

  db:
    security_opt:
      - no-new-privileges:true
```

### 4. Content Security Policy

The application includes CSP headers via Caddy. Verify in production:

```bash
curl -I https://your-domain.com | grep -i content-security
```

### 5. Database Security

```sql
-- Connect to PostgreSQL and run:

-- Revoke public access
REVOKE ALL ON DATABASE tlac_production FROM PUBLIC;

-- Create read-only user for reporting (optional)
CREATE USER tlac_readonly WITH PASSWORD '<PASSWORD>';
GRANT CONNECT ON DATABASE tlac_production TO tlac_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tlac_readonly;
```

---

## Database Setup

### 1. Initial Setup

```bash
# Start database first
docker compose -f compose.yml -f compose.prod.yml up -d db

# Wait for database to be ready
docker compose -f compose.yml -f compose.prod.yml logs -f db
# Look for "database system is ready to accept connections"
```

### 2. Create Database Schema

```bash
# Schema is auto-created on first API start
docker compose -f compose.yml -f compose.prod.yml up -d api

# Verify tables exist
docker compose -f compose.yml -f compose.prod.yml exec db psql -U tlac_prod -d tlac_production -c "\dt"
```

### 3. Bootstrap Admin User

```bash
# Via curl (one-time only)
curl -X POST https://your-domain.com/api/admin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "name": "System Administrator",
    "password": "<SECURE_PASSWORD>"
  }'
```

### 4. Database Backup Configuration

```yaml
# compose.prod.yml
services:
  backup:
    image: postgres:16
    environment:
      - PGHOST=db
      - PGUSER=tlac_prod
      - PGPASSWORD=${POSTGRES_PASSWORD}
      - PGDATABASE=tlac_production
    volumes:
      - ./backups:/backups
    command: >
      sh -c "while true; do
        pg_dump -Fc > /backups/db_$(date +%Y%m%d_%H%M%S).dump
        find /backups -name '*.dump' -mtime +7 -delete
        sleep 86400
      done"
```

---

## Docker Deployment

Commands below assume `compose.yml` + `compose.prod.yml`. If you keep production settings in `.env.production`, add `--env-file .env.production` to each command.

### 1. Production Docker Compose

Use `compose.yml` as the base and add a `compose.prod.yml` override for production-specific changes (ports, TLS, secrets).

Example `compose.prod.yml`:

```yaml
services:
  proxy:
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/Caddyfile.prod:/etc/caddy/Caddyfile:ro
  api:
    environment:
      - RUNNER_AUTO_PULL=0
      - RETENTION_YEARS=2
  db:
    # Optionally use Docker secrets for POSTGRES_PASSWORD
```

Copy `docker/Caddyfile` to `docker/Caddyfile.prod` and update the site address/TLS (see below).

### 2. Build and Deploy

```bash
# Build images
docker compose -f compose.yml -f compose.prod.yml build

# Start services
docker compose -f compose.yml -f compose.prod.yml up -d

# Check status
docker compose -f compose.yml -f compose.prod.yml ps

# View logs
docker compose -f compose.yml -f compose.prod.yml logs -f
```

### 3. Zero-Downtime Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart with zero downtime
docker compose -f compose.yml -f compose.prod.yml build api
docker compose -f compose.yml -f compose.prod.yml up -d --no-deps api
```

---

## Reverse Proxy Configuration

### Caddy Production Configuration

Static assets are served by the API container, so Caddy just reverse-proxies.

```caddyfile
# docker/Caddyfile.prod

{
    admin off
    email admin@your-school.edu
}

your-domain.com {
    header {
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        X-Frame-Options "DENY"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
    }

    reverse_proxy api:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}

www.your-domain.com {
    redir https://your-domain.com{uri} permanent
}
```

---

## SSL/TLS Configuration

### Automatic (Let's Encrypt via Caddy)

Caddy automatically provisions and renews Let's Encrypt certificates. Ensure:

1. Domain DNS points to server IP
2. Ports 80 and 443 are open
3. Email is configured in Caddyfile

### Manual Certificate

If using existing certificates:

```caddyfile
your-domain.com {
    tls /etc/ssl/certs/your-cert.pem /etc/ssl/private/your-key.pem
    # ... rest of config
}
```

### IP Address Only (No Domain Name)

For internal networks where you only have an IP address (e.g., school LANs), use `mkcert` to create trusted certificates.

#### 1. Install mkcert

**Debian/Ubuntu:**
```bash
sudo apt install libnss3-tools
curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert
```

**Gentoo:**
```bash
emerge -av app-crypt/mkcert
```

#### 2. Create Local CA and Certificates

```bash
# Install the local CA (creates rootCA.pem in ~/.local/share/mkcert/)
mkcert -install

# Generate certificate for your server IP (replace with your actual IP)
mkcert -cert-file tlac-cert.pem -key-file tlac-key.pem 192.168.1.100 localhost 127.0.0.1

# Verify the certificate was created
ls -la tlac-*.pem
```

#### 3. Deploy Certificates to Docker

```bash
# Create certs directory
mkdir -p docker/certs

# Copy certificates
cp tlac-cert.pem tlac-key.pem docker/certs/

# Set appropriate permissions
chmod 644 docker/certs/tlac-cert.pem
chmod 600 docker/certs/tlac-key.pem
```

#### 4. Configure Caddyfile for IP Address

Create `docker/Caddyfile.ip`:

```caddyfile
{
    admin off
}

http://:8080 {
    redir https://{host}:8443{uri}
}

https://:8443 {
    tls /etc/caddy/certs/tlac-cert.pem /etc/caddy/certs/tlac-key.pem

    # Security headers
    header {
        Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
    }

    reverse_proxy api:8000 {
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

#### 5. Update Docker Compose

Add the certificate volume mount to your `compose.yml`:

```yaml
services:
  proxy:
    image: caddy:2-alpine
    ports:
      - "8080:8080"
      - "8443:8443"
    volumes:
      - ./docker/Caddyfile.ip:/etc/caddy/Caddyfile:ro
      - ./docker/certs:/etc/caddy/certs:ro  # Add this line
    # ... rest of config
```

#### 6. Distribute CA Certificate to Client Machines

To avoid browser warnings, install the CA certificate on each client machine.

**Find your CA certificate:**
```bash
# The CA is stored here (on the machine where you ran mkcert -install)
ls ~/.local/share/mkcert/
# Look for: rootCA.pem
```

**Install on Windows clients:**
1. Copy `rootCA.pem` to the Windows machine
2. Double-click the file → Install Certificate
3. Select "Local Machine" → Next
4. Select "Place all certificates in the following store" → Browse
5. Select "Trusted Root Certification Authorities" → OK → Next → Finish

**Install on macOS clients:**
1. Copy `rootCA.pem` to the Mac
2. Double-click to open in Keychain Access
3. Add to "System" keychain
4. Find the certificate, double-click, expand "Trust"
5. Set "When using this certificate" to "Always Trust"

**Install on Linux clients:**
```bash
# Debian/Ubuntu
sudo cp rootCA.pem /usr/local/share/ca-certificates/mkcert-ca.crt
sudo update-ca-certificates

# For Firefox (uses its own certificate store)
# Go to Settings → Privacy & Security → Certificates → View Certificates
# Import rootCA.pem under "Authorities" tab
```

**Install on Chromebooks (if managed):**
- Upload the CA certificate via Google Admin Console under Device Management → Networks → Certificates

#### 7. Verify Setup

After restarting Docker and installing the CA on a client:

```bash
# From a client machine with CA installed
curl https://192.168.1.100:8443/api/health
# Should return {"status": "ok", ...} without certificate warnings
```

---

## Monitoring Setup

### 1. Enable Prometheus Scraping

Prometheus scrapes `/metrics`. Configure it like this:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tlac'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scheme: 'http'
```

### 2. Recommended Alerts

```yaml
# alerting_rules.yml
groups:
  - name: tlac
    rules:
      - alert: HighErrorRate
        expr: sum(rate(tlac_http_requests_total{status=~"5.."}[5m])) / sum(rate(tlac_http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(tlac_http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API response time"

      - alert: DatabaseConnectionsHigh
        expr: tlac_db_connections_active > 15
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool usage high"

      - alert: PythonRunnerErrors
        expr: rate(tlac_python_runs_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Python runner experiencing errors"
```

### 3. Health Check Endpoint

Configure load balancer/uptime monitor to check:

```
GET https://your-domain.com/api/health
Expected: {"status": "ok", "db_ok": true, ...}
```

---

## Backup Configuration

### 1. Automated Database Backups

See [Backup and Recovery Guide](backup-and-recovery.md) for detailed instructions.

```bash
# Quick setup
mkdir -p /srv/backups
chmod 700 /srv/backups

# Add to crontab
crontab -e
# 0 3 * * * /path/to/backup-script.sh
```

### 2. Backup Verification

```bash
# Test restore to verify backups work
pg_restore --list /srv/backups/latest.dump
```

### 3. Off-site Backup

```bash
# Sync to remote storage
aws s3 sync /srv/backups s3://your-bucket/tlac-backups/
# or
rclone sync /srv/backups remote:tlac-backups/
```

---

## Scaling Considerations

### Horizontal Scaling

For high-traffic deployments:

```yaml
# compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
```

With load balancing in Caddy:

```caddyfile
reverse_proxy api:8000 {
    lb_policy round_robin
    health_uri /api/health
}
```

### Database Scaling

For larger deployments:

1. **Read Replicas**: Configure PostgreSQL streaming replication
2. **Connection Pooling**: Use PgBouncer for connection pooling
3. **External Database**: Consider managed PostgreSQL (AWS RDS, Cloud SQL)

### Resource Limits

Adjust based on load testing:

```yaml
# High-traffic configuration
api:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 1G

db:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

---

## Maintenance Procedures

### Scheduled Maintenance

```bash
# 1. Enable maintenance mode (optional)
# Add maintenance page to Caddy config

# 2. Create backup
./scripts/backup.sh

# 3. Pull updates
git pull origin main

# 4. Rebuild and restart
docker compose -f compose.yml -f compose.prod.yml build
docker compose -f compose.yml -f compose.prod.yml up -d

# 5. Verify health
curl https://your-domain.com/api/health

# 6. Monitor logs
docker compose -f compose.yml -f compose.prod.yml logs -f --tail=100
```

### Database Maintenance

```bash
# Connect to database
docker compose -f compose.yml -f compose.prod.yml exec db psql -U tlac_prod -d tlac_production

# Vacuum and analyze
VACUUM ANALYZE;

# Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Log Rotation

```bash
# /etc/logrotate.d/tlac
/var/log/tlac/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs
docker compose -f compose.yml -f compose.prod.yml logs api

# Check resource limits
docker stats

# Verify environment
docker compose -f compose.yml -f compose.prod.yml config
```

#### 2. Database Connection Errors

```bash
# Test database connectivity
docker compose -f compose.yml -f compose.prod.yml exec api python -c "
from app.db import engine
from sqlalchemy import text
with engine.connect() as conn:
    print(conn.execute(text('SELECT 1')).scalar())
"

# Check connection pool
docker compose -f compose.yml -f compose.prod.yml exec db psql -U tlac_prod -d tlac_production -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 3. High Memory Usage

```bash
# Check container memory
docker stats --no-stream

# Restart with memory limits
docker compose -f compose.yml -f compose.prod.yml restart api
```

#### 4. SSL Certificate Issues

```bash
# Check Caddy logs
docker compose -f compose.yml -f compose.prod.yml logs proxy

# Force certificate renewal
docker compose -f compose.yml -f compose.prod.yml exec proxy caddy reload --config /etc/caddy/Caddyfile
```

#### 5. Python Runner Failures

```bash
# Check runner diagnostics
curl -k https://your-domain.com/api/python/diagnostics

# Verify Docker socket permissions
ls -la /var/run/docker.sock

# Check runner container
docker ps -a | grep python-runner
```

### Health Check Commands

```bash
# Full system check
echo "=== System Health ==="
curl -s https://your-domain.com/api/health | jq .

echo "=== Container Status ==="
docker compose -f compose.yml -f compose.prod.yml ps

echo "=== Resource Usage ==="
docker stats --no-stream

echo "=== Database Connections ==="
docker compose -f compose.yml -f compose.prod.yml exec db psql -U tlac_prod -d tlac_production -c "SELECT count(*) as connections FROM pg_stat_activity;"

echo "=== Recent Errors ==="
docker compose -f compose.yml -f compose.prod.yml logs --tail=50 api | grep -i error
```

---

## Checklist

### Pre-Deployment

- [ ] Server meets minimum requirements
- [ ] Docker and Docker Compose installed
- [ ] Firewall configured
- [ ] SSH hardened
- [ ] Domain DNS configured
- [ ] SSL certificates ready (or Let's Encrypt configured)
- [ ] Environment variables set
- [ ] Strong passwords generated

### Post-Deployment

- [ ] Health endpoint responding
- [ ] Admin user created
- [ ] SSL certificate valid
- [ ] Backups configured and tested
- [ ] Monitoring alerts configured
- [ ] Log rotation configured
- [ ] Test user login works
- [ ] Python runner functional
- [ ] Performance baseline established

### Regular Maintenance

- [ ] Weekly: Review logs for errors
- [ ] Weekly: Check backup integrity
- [ ] Monthly: Apply security updates
- [ ] Monthly: Review metrics and performance
- [ ] Quarterly: Test disaster recovery
- [ ] Annually: Review security configuration

---

**Last Updated**: 2026-01-14
**Version**: 1.0.0
