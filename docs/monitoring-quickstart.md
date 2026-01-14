# Monitoring Quick Start

Get monitoring up and running in 5 minutes.

## 1. Install Dependencies

If you run the API outside Docker, install backend requirements (Prometheus client is already included):

```bash
cd backend
../.venv/bin/pip install -r requirements.txt
```

## 2. Start Monitoring Stack

```bash
# From project root
docker compose -f compose.yml -f compose.monitoring.yml up -d
```

This starts:
- **Prometheus** on port 9090
- **Grafana** on port 3000
- Existing TLAC services (API, DB, Caddy)

## 3. Access Dashboards

### Grafana (Recommended)
1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Navigate to **Dashboards** → **TLAC Overview**

### Prometheus (Advanced)
1. Open http://localhost:9090
2. Try a query: `rate(tlac_http_requests_total[5m])`

## 4. View Metrics

Admin metrics (requires an admin session):
- UI: `https://localhost:8443/admin-metrics.html`
- JSON: `https://localhost:8443/api/admin/metrics`

Prometheus metrics:
```bash
curl -k https://localhost:8443/metrics
```

## 5. Test It Works

Generate some traffic:
```bash
# Make a few requests
for i in {1..10}; do
  curl -k -s https://localhost:8443/ > /dev/null
  echo "Request $i complete"
done

# Wait 15 seconds and check Grafana.
```

## What's Next?

- **Set up alerts**: See [monitoring-guide.md](monitoring-guide.md#alerting)
- **Create custom dashboards**: See [monitoring-guide.md](monitoring-guide.md#creating-custom-dashboards)
- **Configure retention**: Edit `docker/prometheus.yml`
- **Secure Grafana**: Change default password!

## Troubleshooting

**Grafana shows "No Data":**
Verify Prometheus can reach `/metrics`:
```bash
docker compose exec prometheus wget -O- http://api:8000/metrics

# Check Prometheus targets
open http://localhost:9090/targets
```

**Metrics endpoint returns 403 or 404:**
- `/api/metrics` and `/api/admin/metrics` require an admin session.
- If `/metrics` returns 404, rebuild/restart the API container.

## Default Metrics Available

- **HTTP**: Request rate, latency, status codes
- **Auth**: Login attempts, active sessions
- **Activity**: Saves, latencies by lesson
- **Python**: Executions, success/error rates
- **Rate Limiting**: Violations, usage
- **Database**: Connections, query latency
- **Backups**: Duration, size, last success time

See full list in [monitoring-guide.md](monitoring-guide.md#available-metrics).

## Configuration

### Change Grafana Password

```bash
# In .env file
GRAFANA_ADMIN_PASSWORD=your-secure-password

# Restart
docker compose -f compose.monitoring.yml restart grafana
```

### Adjust Prometheus Scrape Interval

Edit `docker/prometheus.yml`:
```yaml
global:
  scrape_interval: 10s  # Scrape every 10 seconds
```

Then restart:
```bash
docker compose -f compose.monitoring.yml restart prometheus
```

## Stop Monitoring

```bash
# Stop all services
docker compose -f compose.yml -f compose.monitoring.yml down

# Or just monitoring services
docker compose -f compose.monitoring.yml down
```

## Complete Documentation

For full documentation, see [monitoring-guide.md](monitoring-guide.md).
