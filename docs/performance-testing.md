# Performance Testing Guide

Comprehensive guide for performance testing the TLAC (Thinking Like a Coder) application.

## Overview

This guide covers:
- Load testing with Locust
- API benchmarking
- Stress testing
- Rate limiter validation
- Performance monitoring

## Prerequisites

### Install Dependencies

```bash
# Install Python performance testing dependencies
pip install -r performance/requirements.txt
```

Required packages:
- `locust==2.20.0` - Load testing framework
- `requests==2.31.0` - HTTP client
- `faker==22.0.0` - Test data generation

### Ensure System is Running

```bash
# Start the application
docker compose up -d

# Verify services are healthy
docker compose ps
curl -k https://localhost:8443/api/health
```

## Test Types

### 1. API Benchmarking

**Purpose**: Measure baseline response times for individual endpoints

**Usage**:
```bash
python performance/benchmark.py
```

**What it tests**:
- Health check endpoint
- Authentication endpoints
- Activity state operations
- Python code execution
- Teacher operations

**Expected results**:
- Health check: < 50ms average
- Authentication: < 200ms average
- Activity saves: < 100ms average
- Python execution: < 500ms average (depends on code complexity)

**Example output**:
```
Testing: Health Check
  GET /api/health
  Avg: 23.45ms | Median: 21.32ms | P95: 45.67ms | P99: 52.11ms
  ✓ Excellent
```

### 2. Load Testing with Locust

**Purpose**: Simulate realistic user load and identify bottlenecks

**Basic Usage**:
```bash
# Start Locust web interface
locust -f performance/locustfile.py --host=https://localhost:8443

# Open browser to http://localhost:8089
# Set number of users and spawn rate
# Start test
```

**Command-line Usage** (headless):
```bash
# Run with 50 users, spawn rate of 5 users/second, for 2 minutes
locust -f performance/locustfile.py \
  --host=https://localhost:8443 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless
```

**User Types**:

1. **TLACUser** (Pupils) - Weight: 70%
   - Check authentication status
   - Get/save activity state
   - Run Python code
   - View lesson manifest

2. **TeacherUser** - Weight: 20%
   - View pupil progress
   - Mark activities
   - Check system health

3. **AdminUser** - Weight: 10%
   - View metrics dashboard
   - Check audit logs
   - Monitor system health

**Interpreting Results**:

Good performance indicators:
- Response time P95 < 500ms
- Failure rate < 1%
- RPS (requests/second) scales linearly with user count
- No timeout errors

Warning signs:
- Response time increasing with load
- Failure rate > 5%
- Database connection errors
- Memory/CPU saturation

### 3. Stress Testing

**Purpose**: Test system behavior under extreme load

**Usage**:
```bash
python performance/stress_test.py
```

**Test Scenarios**:

1. **Authentication Stress Test**
   - 100 concurrent login requests
   - Tests database connection pooling
   - Validates session creation performance

2. **Activity Save Stress Test**
   - 200 concurrent save operations
   - Tests database write performance
   - Validates transaction handling

3. **Python Runner Stress Test**
   - 30 concurrent code executions
   - Tests Docker container pooling
   - Validates resource isolation

4. **Concurrent User Simulation**
   - 20 users performing mixed operations
   - Runs for 30 seconds
   - Realistic usage pattern

**Acceptance Criteria**:
- Success rate > 95%
- No database deadlocks
- P95 response time < 1000ms under peak load
- No memory leaks after extended testing

### 4. Rate Limiter Validation

**Purpose**: Verify rate limiting is working correctly

**Usage**:
```bash
python performance/test_rate_limiter.py
```

**Tests**:

1. **Login Rate Limit**
   - Attempts 10 failed logins
   - Should trigger HTTP 429 after 5 attempts
   - Validates brute force protection

2. **API Rate Limit**
   - Makes 100 rapid activity save requests
   - May trigger rate limiting under heavy load
   - Validates general API protection

3. **Python Runner Rate Limit**
   - Makes 20 rapid code execution requests
   - Validates resource protection

**Expected Behavior**:
- Failed login rate limit: 5 attempts before lockout
- API rate limits: Configurable per endpoint
- Clear HTTP 429 responses with appropriate headers

## Performance Monitoring

### During Tests

**Monitor these metrics** (via admin dashboard at `https://localhost:8443/admin-metrics.html`):

1. **HTTP Requests**
   - Total requests
   - Error rate
   - Response time percentiles

2. **Authentication**
   - Login success rate
   - Active sessions
   - Rate limited attempts

3. **Python Runner**
   - Execution count
   - Success rate
   - Timeouts

4. **System Health**
   - Database connections
   - Error counts
   - Memory/CPU usage (via Docker stats)

### System Resource Monitoring

```bash
# Monitor Docker container resources
docker stats

# Monitor database connections
docker compose exec db psql -U tlac -c "SELECT count(*) FROM pg_stat_activity;"

# View API logs during test
docker compose logs -f api

# Check for errors
docker compose logs api | grep -i error
```

## Performance Targets

### Response Time Targets

| Endpoint Type | Average | P95 | P99 |
|---------------|---------|-----|-----|
| Static files | < 50ms | < 100ms | < 200ms |
| API reads | < 100ms | < 200ms | < 300ms |
| API writes | < 150ms | < 300ms | < 500ms |
| Python execution | < 500ms | < 1000ms | < 2000ms |

### Throughput Targets

- **Concurrent users**: Support 50+ simultaneous users
- **Requests/second**: 100+ RPS sustained
- **Python executions/minute**: 60+ executions

### Resource Targets

- **CPU usage**: < 70% average under normal load
- **Memory usage**: < 80% of available RAM
- **Database connections**: < 15 of 20 pool size
- **Disk I/O**: No queue saturation

## Common Issues and Solutions

### Issue: High Response Times

**Symptoms**:
- P95 > 1000ms
- Timeouts under load

**Diagnosis**:
```bash
# Check database query performance
docker compose logs api | grep "slow query"

# Check database connection pool
# Look for "connection pool exhausted" warnings

# Check Docker resource limits
docker stats
```

**Solutions**:
- Increase database connection pool size
- Add database indexes
- Optimize slow queries
- Increase container resources

### Issue: Rate Limit False Positives

**Symptoms**:
- Legitimate requests getting HTTP 429
- Rate limit triggered too quickly

**Solutions**:
- Adjust rate limits in `backend/app/config.py`
- Implement per-user vs per-IP limits
- Add rate limit bypass for trusted IPs

### Issue: Python Runner Timeouts

**Symptoms**:
- Frequent execution timeouts
- Long queue times

**Solutions**:
- Increase `RUNNER_TIMEOUT_SEC` in `.env`
- Increase `RUNNER_CONCURRENCY` for more parallel executions
- Optimize container startup time

### Issue: Database Connection Pool Exhaustion

**Symptoms**:
- "Too many connections" errors
- Slow database operations under load

**Solutions**:
- Increase pool size in `backend/app/db.py`
- Reduce connection timeout
- Fix connection leaks (check for unclosed connections)

## Best Practices

### Before Testing

1. **Start with fresh state**:
   ```bash
   docker compose down
   docker compose up -d
   # Wait for services to be fully ready
   sleep 10
   ```

2. **Clear metrics**:
   - Restart services to reset Prometheus counters
   - Or account for baseline metrics in analysis

3. **Document baseline**:
   - Run benchmark test before changes
   - Save results for comparison

### During Testing

1. **Monitor system resources**:
   - Keep `docker stats` running
   - Watch for memory/CPU saturation
   - Monitor disk I/O

2. **Watch for errors**:
   - Monitor application logs
   - Check error rates in metrics
   - Look for database errors

3. **Test incrementally**:
   - Start with low load
   - Gradually increase users
   - Identify breaking point

### After Testing

1. **Analyze results**:
   - Compare against targets
   - Identify bottlenecks
   - Document findings

2. **Review metrics**:
   - Check Prometheus for detailed metrics
   - Export Grafana dashboards
   - Save screenshots of key graphs

3. **Clean up**:
   ```bash
   # Stop load test
   # Review and save results
   # Restart services if needed
   docker compose restart
   ```

## Continuous Performance Testing

### CI/CD Integration

Add performance tests to your CI pipeline:

```yaml
# Example GitHub Actions workflow
name: Performance Tests
on: [pull_request]
jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker compose up -d
      - name: Run benchmark
        run: python performance/benchmark.py
      - name: Check performance targets
        run: python performance/check_targets.py
```

### Regular Testing Schedule

- **Daily**: Run benchmark tests
- **Weekly**: Run stress tests
- **Monthly**: Full load testing with Locust
- **Per release**: Comprehensive performance regression testing

## Reporting

### Generate Performance Report

Create a summary report after testing:

```bash
# Run all tests and save output
python performance/benchmark.py > results/benchmark_$(date +%Y%m%d).txt
python performance/stress_test.py > results/stress_$(date +%Y%m%d).txt

# Export metrics from Prometheus
curl http://localhost:9090/api/v1/query?query=tlac_http_request_duration_seconds > results/metrics_$(date +%Y%m%d).json
```

### Performance Metrics to Track

1. **Baseline Metrics**
   - Response times (P50, P95, P99)
   - Throughput (RPS)
   - Error rates

2. **Load Test Metrics**
   - Max concurrent users supported
   - Breaking point (when errors > 5%)
   - Resource utilization at peak

3. **Regression Metrics**
   - Response time changes vs previous version
   - Throughput changes
   - Resource usage changes

## Support

For performance issues:

1. Check this guide for common issues
2. Review application logs: `docker compose logs api`
3. Check Prometheus metrics: `http://localhost:9090`
4. Review admin dashboard: `https://localhost:8443/admin-metrics.html`

---

**Last Updated:** 2026-01-11
**Version:** 1.0.0
