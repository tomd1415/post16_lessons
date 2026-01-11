#!/bin/bash
# Run all performance tests in sequence
# Saves results to performance/results/ directory

set -e  # Exit on error

echo "=========================================="
echo "TLAC Performance Test Suite"
echo "=========================================="
echo ""

# Check if services are running
echo "Checking if services are running..."
if ! curl -k -s https://localhost:8443/api/health > /dev/null 2>&1; then
    echo "Error: Application is not running!"
    echo "Please start it with: docker compose up -d"
    exit 1
fi
echo "✓ Application is running"
echo ""

# Create results directory
RESULTS_DIR="performance/results"
mkdir -p "$RESULTS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$RESULTS_DIR/test_results_$TIMESTAMP.txt"

echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Header
echo "TLAC Performance Test Results" > "$RESULTS_FILE"
echo "Generated: $(date)" >> "$RESULTS_FILE"
echo "=========================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Test 1: Benchmark
echo "Running API Benchmark Tests..."
echo "" >> "$RESULTS_FILE"
echo "=== API BENCHMARK ===" >> "$RESULTS_FILE"
python performance/benchmark.py 2>&1 | tee -a "$RESULTS_FILE"
echo ""
sleep 2

# Test 2: Rate Limiter Validation
echo "Running Rate Limiter Validation..."
echo "" >> "$RESULTS_FILE"
echo "=== RATE LIMITER VALIDATION ===" >> "$RESULTS_FILE"
python performance/test_rate_limiter.py 2>&1 | tee -a "$RESULTS_FILE"
echo ""
sleep 2

# Test 3: Stress Tests
echo "Running Stress Tests..."
echo "" >> "$RESULTS_FILE"
echo "=== STRESS TESTS ===" >> "$RESULTS_FILE"
python performance/stress_test.py 2>&1 | tee -a "$RESULTS_FILE"
echo ""

# Summary
echo "=========================================="
echo "All performance tests complete!"
echo "=========================================="
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""
echo "Next steps:"
echo "  1. Review the results file"
echo "  2. Check admin metrics: https://localhost:8443/admin-metrics.html"
echo "  3. Review Prometheus: http://localhost:9090"
echo ""
echo "To run Locust load tests:"
echo "  locust -f performance/locustfile.py --host=https://localhost:8443"
echo "  Then open http://localhost:8089"
echo ""
