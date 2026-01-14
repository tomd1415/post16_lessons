# Monitoring and Metrics Guide

Comprehensive guide for monitoring the TLAC (Thinking Like a Coder) application using Prometheus and Grafana.

## Overview

The TLAC application collects Prometheus metrics in-process and exposes admin JSON metrics at `/api/metrics` and `/api/admin/metrics`, plus a Prometheus `/metrics` endpoint for scraping. This guide covers:

- Metrics available
- Setting up Prometheus and Grafana
- Creating custom dashboards
- Alerting configuration
- Troubleshooting

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start application with monitoring
docker compose -f compose.yml -f compose.monitoring.yml up -d

# Or start monitoring services separately
docker compose -f compose.monitoring.yml up -d prometheus grafana
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3000
  - Default credentials: `admin` / `admin`
  - Pre-configured dashboard: "TLAC Overview"
- **Prometheus**: http://localhost:9090
  - Query metrics directly
  - View targets and configuration

### 3. View Metrics

Admin metrics (requires an admin session):
- UI: `https://localhost:8443/admin-metrics.html`
- JSON: `https://localhost:8443/api/admin/metrics`

Prometheus metrics endpoint:
- `https://localhost:8443/metrics` (TLS uses Caddy's internal CA)

## Prometheus Endpoint

`/metrics` is enabled by default. If you want to restrict it, add auth in the handler or limit access to the monitoring network.

## Available Metrics

These Prometheus counters are available at `/metrics`.

### HTTP Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_http_requests_total` | Counter | Total HTTP requests | `method`, `endpoint`, `status` |
| `tlac_http_request_duration_seconds` | Histogram | Request latency | `method`, `endpoint` |
| `tlac_http_requests_in_progress` | Gauge | Active requests | `method`, `endpoint` |

**Example Queries:**
```promql
# Request rate (requests per second)
rate(tlac_http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(tlac_http_request_duration_seconds_bucket[5m]))

# Error rate (4xx + 5xx)
rate(tlac_http_requests_total{status=~"[45].."}[5m])
```

### Authentication Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_auth_login_attempts_total` | Counter | Login attempts | `status` (success/failed/rate_limited) |
| `tlac_auth_sessions_active` | Gauge | Active user sessions | - |

**Example Queries:**
```promql
# Login success rate
rate(tlac_auth_login_attempts_total{status="success"}[5m])
/ rate(tlac_auth_login_attempts_total[5m])

# Failed login rate
rate(tlac_auth_login_attempts_total{status="failed"}[5m])
```

### Activity Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_activity_saves_total` | Counter | Activity state saves | `lesson_id` |
| `tlac_activity_save_duration_seconds` | Histogram | Save operation latency | - |

**Example Queries:**
```promql
# Most popular lessons
topk(5, rate(tlac_activity_saves_total[1h]))

# Average save duration
rate(tlac_activity_save_duration_seconds_sum[5m])
/ rate(tlac_activity_save_duration_seconds_count[5m])
```

### Python Runner Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_python_runs_total` | Counter | Python executions | `status` (success/error/timeout) |
| `tlac_python_run_duration_seconds` | Histogram | Execution duration | - |

**Example Queries:**
```promql
# Python run success rate
rate(tlac_python_runs_total{status="success"}[5m])
/ rate(tlac_python_runs_total[5m])

# Average execution time
histogram_quantile(0.5, rate(tlac_python_run_duration_seconds_bucket[5m]))
```

### Rate Limiting Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_rate_limit_exceeded_total` | Counter | Rate limit violations | `endpoint`, `limit_type` |
| `tlac_rate_limit_usage` | Histogram | Rate limit usage % | `endpoint` |

Note: API rate limiting is not enforced by default, so these may remain at 0 unless you wire `ApiRateLimiter`.

**Example Queries:**
```promql
# Rate limit violations per endpoint
sum by(endpoint) (rate(tlac_rate_limit_exceeded_total[5m]))

# Average rate limit usage
histogram_quantile(0.95, rate(tlac_rate_limit_usage_bucket[5m]))
```

### Database Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_db_connections_active` | Gauge | Active connections | - |
| `tlac_db_query_duration_seconds` | Histogram | Query latency | `operation` |
| `tlac_db_errors_total` | Counter | Database errors | `error_type` |

**Example Queries:**
```promql
# Database connection usage
tlac_db_connections_active

# Slow queries (> 1 second)
sum(rate(tlac_db_query_duration_seconds_bucket{le="1.0"}[5m]))
```

### Backup Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_backup_duration_seconds` | Histogram | Backup duration | - |
| `tlac_backup_size_bytes` | Gauge | Backup size | `backup_type` |
| `tlac_backup_last_success_timestamp` | Gauge | Last successful backup | - |

**Example Queries:**
```promql
# Time since last backup (seconds)
time() - tlac_backup_last_success_timestamp

# Backup size trend
tlac_backup_size_bytes{backup_type="database"}
```

### Error Metrics

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `tlac_errors_total` | Counter | Application errors | `error_type`, `endpoint` |

**Example Queries:**
```promql
# Error rate by type
sum by(error_type) (rate(tlac_errors_total[5m]))

# Errors per endpoint
topk(5, rate(tlac_errors_total[1h]))
```

## Grafana Dashboards

### Pre-configured Dashboard: TLAC Overview

The default dashboard includes:

1. **Overview Stats**
   - Requests per minute
   - Active sessions
   - Error rate

2. **Request Metrics**
   - Request rate by status code
   - Request latency percentiles (p50, p95, p99)
   - Requests in progress

3. **Authentication**
   - Login attempts (success/failed/rate limited)
   - Active sessions over time

4. **Rate Limiting**
   - Rate limit violations by endpoint
   - Rate limit usage

5. **Performance**
   - Activity save latency
   - Python execution times
   - Database query latency

### Creating Custom Dashboards

1. **Access Grafana**: http://localhost:3000
2. **Create Dashboard**: Click "+" → "Dashboard"
3. **Add Panel**: Click "Add visualization"
4. **Select Data Source**: Choose "Prometheus"
5. **Write Query**: Use PromQL (see example queries above)
6. **Configure Visualization**: Choose chart type, colors, etc.
7. **Save Dashboard**: Click "Save" icon

### Example Custom Panels

**Panel 1: Error Rate**
```promql
sum(rate(tlac_errors_total[5m])) by (error_type)
```
- Visualization: Time series
- Legend: `{{error_type}}`

**Panel 2: Top Endpoints by Traffic**
```promql
topk(10, sum by(endpoint) (rate(tlac_http_requests_total[5m])))
```
- Visualization: Bar chart
- Legend: `{{endpoint}}`

**Panel 3: Database Connection Pool Usage**
```promql
tlac_db_connections_active
```
- Visualization: Gauge
- Thresholds: Green (< 15), Yellow (15-20), Red (> 20)

## Alerting

### Prometheus Alerting Rules

Create alert rules in `docker/prometheus/alerts/tlac.yml`:

```yaml
groups:
  - name: tlac_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(tlac_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      # Low login success rate
      - alert: LowLoginSuccessRate
        expr: |
          rate(tlac_auth_login_attempts_total{status="success"}[5m])
          / rate(tlac_auth_login_attempts_total[5m]) < 0.5
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Login success rate below 50%"

      # High request latency
      - alert: HighRequestLatency
        expr: histogram_quantile(0.95, rate(tlac_http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "95th percentile latency above 2 seconds"

      # Backup age
      - alert: BackupTooOld
        expr: time() - tlac_backup_last_success_timestamp > 86400
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "No successful backup in 24 hours"

      # Database connection pool exhaustion
      - alert: HighDBConnections
        expr: tlac_db_connections_active > 18
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool nearly exhausted"
```

### Grafana Alerting

1. **Create Alert**: In any panel, click "Alert" tab
2. **Define Condition**: Set threshold (e.g., error rate > 0.1)
3. **Configure Notifications**: Email, Slack, PagerDuty, etc.
4. **Test Alert**: Click "Test" to verify

**Example: High Error Rate Alert**
- Query: `rate(tlac_errors_total[5m])`
- Condition: WHEN `last()` OF `query(A, 5m, now)` IS ABOVE `0.1`
- For: 5m
- Notification: Email to ops@example.com

## Configuration

### Environment Variables

Configure Grafana via `.env` (used by `compose.monitoring.yml`):

```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=changeme123
```

Prometheus retention and scrape intervals are configured in `docker/prometheus.yml` or via the Prometheus command flags in `compose.monitoring.yml`.

### Prometheus Configuration

Edit `docker/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s      # Default scrape interval
  evaluation_interval: 15s  # How often to evaluate rules

scrape_configs:
  - job_name: 'tlac-api'
    metrics_path: /metrics
    scrape_interval: 10s    # Override for this job
    static_configs:
      - targets: ['api:8000']
```

### Grafana Provisioning

Auto-provision dashboards by placing JSON files in:
```
docker/grafana/dashboards/
```

Auto-provision datasources in:
```
docker/grafana/provisioning/datasources/
```

## Monitoring Best Practices

### 1. Set Up Alerts for Critical Metrics

- **Error rate** > 1%
- **Login success rate** < 80%
- **Request latency p95** > 2s
- **Database connections** > 90% pool size
- **Backup age** > 24 hours

### 2. Monitor Key Business Metrics

- Daily active users
- Activity completions
- Python code executions
- Teacher marking activity

### 3. Track Performance Trends

- Weekly request volume
- Average response times
- Database query performance
- Backup sizes and duration

### 4. Regular Review

- **Daily**: Check error rates and alerts
- **Weekly**: Review performance trends
- **Monthly**: Capacity planning (disk, connections, etc.)

## Troubleshooting

### Metrics Not Appearing

**Check admin metrics are accessible:**
- UI: `https://localhost:8443/admin-metrics.html`
- JSON: `https://localhost:8443/api/admin/metrics` (admin session required)

**Prometheus scrape test:**
```bash
docker compose exec prometheus wget -O- http://api:8000/metrics
```

**Check Prometheus targets:**
1. Open http://localhost:9090/targets
2. Verify `tlac-api` target is "UP"
3. Check last scrape time

**Check Prometheus logs:**
```bash
docker compose logs prometheus
```

### Grafana Not Showing Data

**Verify datasource:**
1. Grafana → Configuration → Data Sources
2. Click "Prometheus"
3. Click "Test" button
4. Should show "Data source is working"

**Check query syntax:**
- Use Prometheus UI (http://localhost:9090) to test queries
- Verify metric names match exactly

**Check time range:**
- Ensure dashboard time range includes data
- Check "Last 5 minutes" instead of default

### High Memory Usage

**Prometheus retention:**
```yaml
# In compose.monitoring.yml
command:
  - '--storage.tsdb.retention.time=15d'  # Reduce from 30d
```

**Grafana:**
- Reduce query resolution
- Limit dashboard auto-refresh rate
- Archive old dashboards

### Missing Metrics

**Restart application:**
```bash
docker compose restart api
```

**Check application logs:**
```bash
docker compose logs api | grep -i metric
```

**Verify imports:**
```bash
# Inside container
docker compose exec api python -c "from app import metrics; print('OK')"
```

## Security Considerations

### 1. Secure Grafana

```bash
# Change default password immediately
GF_SECURITY_ADMIN_PASSWORD=strong-random-password

# Disable anonymous access
GF_AUTH_ANONYMOUS_ENABLED=false

# Enable HTTPS
GF_SERVER_PROTOCOL=https
GF_SERVER_CERT_FILE=/etc/grafana/ssl/cert.pem
GF_SERVER_CERT_KEY=/etc/grafana/ssl/key.pem
```

### 2. Restrict Metrics Endpoint

Add authentication to `/metrics` endpoint if exposing publicly:

```python
@app.get("/metrics")
def prometheus_metrics(request: Request, db: Session = Depends(get_db)):
    # Require admin or API key
    require_admin(request)  # Or check API key header
    # ... rest of function
```

### 3. Network Isolation

Use Docker networks to isolate monitoring:

```yaml
# In compose.monitoring.yml
services:
  prometheus:
    networks:
      - monitoring
      - tlac-network  # Only for scraping

networks:
  monitoring:
    internal: true  # No external access
```

### 4. Secure Prometheus

- Disable admin API in production
- Use authentication for Prometheus UI
- Restrict access to port 9090

## Advanced Topics

### Custom Metrics

Add custom metrics in `backend/app/metrics.py`, then call them from your endpoints:

```python
# backend/app/metrics.py
from prometheus_client import Counter

custom_operations_total = Counter(
    "tlac_custom_operations_total",
    "Custom operations",
    ["operation"]
)

def record_custom_operation(operation: str):
    custom_operations_total.labels(operation=operation).inc()
```

```python
# backend/app/main.py (or another module)
from app import metrics

# In your endpoint
metrics.record_custom_operation("process_data")
```

### Federation

Scrape multiple TLAC instances:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tlac-prod-1'
    metrics_path: /metrics
    scheme: https
    static_configs:
      - targets: ['prod1.example.com:443']

  - job_name: 'tlac-prod-2'
    metrics_path: /metrics
    scheme: https
    static_configs:
      - targets: ['prod2.example.com:443']
```

### Long-term Storage

Use Thanos for long-term metric storage:

```bash
# Add to compose.monitoring.yml
thanos:
  image: thanosio/thanos:v0.33.0
  command: store
  # ... configuration
```

## Support

For issues with monitoring:

1. Check [Troubleshooting](#troubleshooting) section
2. Review Prometheus logs: `docker compose logs prometheus`
3. Review Grafana logs: `docker compose logs grafana`
4. Check admin metrics: `https://localhost:8443/admin-metrics.html` (admin session required)
5. Consult Prometheus documentation: https://prometheus.io/docs/
6. Consult Grafana documentation: https://grafana.com/docs/

---

**Last Updated:** 2026-01-14
**Version:** 1.0.0
