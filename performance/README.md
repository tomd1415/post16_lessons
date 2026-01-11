# Performance Testing

Performance testing suite for TLAC (Thinking Like a Coder) application.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r performance/requirements.txt
```

### 2. Start the Application

```bash
docker compose up -d
```

### 3. Run Tests

**Run all tests**:
```bash
bash performance/run_all_tests.sh
```

**Or run individual tests**:
```bash
# API benchmarking
python performance/benchmark.py

# Stress testing
python performance/stress_test.py

# Rate limiter validation
python performance/test_rate_limiter.py

# Load testing with Locust
locust -f performance/locustfile.py --host=https://localhost:8443
# Then open http://localhost:8089
```

## Test Files

| File | Purpose | Duration |
|------|---------|----------|
| `benchmark.py` | Measure API response times | ~2 minutes |
| `stress_test.py` | Test under heavy concurrent load | ~2 minutes |
| `test_rate_limiter.py` | Validate rate limiting | ~1 minute |
| `locustfile.py` | Load testing with Locust | Variable |
| `run_all_tests.sh` | Run all tests in sequence | ~5 minutes |

## What Gets Tested

- ✅ API endpoint response times
- ✅ Authentication performance
- ✅ Activity state operations
- ✅ Python code execution throughput
- ✅ Database connection pooling
- ✅ Rate limiting effectiveness
- ✅ Concurrent user handling
- ✅ System behavior under stress

## Performance Targets

### Response Times
- Health check: < 50ms average
- API reads: < 100ms average
- API writes: < 150ms average
- Python execution: < 500ms average

### Throughput
- Support 50+ concurrent users
- Handle 100+ requests/second
- Execute 60+ Python programs/minute

### Success Rates
- HTTP success rate: > 99%
- Login success rate: > 80%
- Python execution success: > 95%

## Monitoring During Tests

While tests are running, monitor:

1. **Admin Dashboard**: https://localhost:8443/admin-metrics.html
   - Real-time metrics
   - Success rates
   - Active sessions

2. **Prometheus**: http://localhost:9090
   - Detailed metrics
   - Query custom metrics
   - View targets

3. **Docker Stats**: `docker stats`
   - CPU usage
   - Memory usage
   - Container health

4. **Application Logs**: `docker compose logs -f api`
   - Error messages
   - Performance warnings
   - Rate limit triggers

## Results

Test results are saved to `performance/results/` with timestamps.

Example: `performance/results/test_results_20260111_210000.txt`

## Documentation

See [docs/performance-testing.md](../docs/performance-testing.md) for comprehensive guide including:
- Detailed test descriptions
- Performance tuning
- Troubleshooting
- CI/CD integration
- Best practices

## Common Commands

```bash
# Quick benchmark
python performance/benchmark.py

# Stress test
python performance/stress_test.py

# Validate rate limiting
python performance/test_rate_limiter.py

# Load test (headless, 50 users, 2 minutes)
locust -f performance/locustfile.py \
  --host=https://localhost:8443 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --headless

# Load test (web UI)
locust -f performance/locustfile.py --host=https://localhost:8443
# Open http://localhost:8089

# Monitor during tests
docker stats
docker compose logs -f api
```

## Troubleshooting

**Tests fail with connection errors**:
- Ensure application is running: `docker compose ps`
- Check services are healthy: `curl -k https://localhost:8443/api/health`

**Slow response times**:
- Check Docker resource limits
- Monitor database connection pool usage
- Review application logs for bottlenecks

**Rate limiting triggers too often**:
- Adjust rate limits in `backend/app/config.py`
- Check rate limiter configuration

## Support

For help with performance testing:
1. See [performance-testing.md](../docs/performance-testing.md)
2. Check application logs: `docker compose logs api`
3. Review metrics dashboard
4. Check Prometheus targets: http://localhost:9090/targets
