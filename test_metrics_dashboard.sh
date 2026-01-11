#!/bin/bash
# Quick test script for the admin metrics dashboard

echo "Testing admin metrics endpoint..."

# Login as admin
LOGIN_RESPONSE=$(curl -s -c /tmp/test_cookies.txt -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ChangeMe123"}')

if echo "$LOGIN_RESPONSE" | grep -q '"ok":true'; then
  echo "✓ Login successful"
else
  echo "✗ Login failed"
  exit 1
fi

# Test metrics endpoint
METRICS_RESPONSE=$(curl -s -b /tmp/test_cookies.txt http://localhost:8080/api/admin/metrics)

if echo "$METRICS_RESPONSE" | grep -q '"summary"'; then
  echo "✓ Admin metrics endpoint working"
  echo ""
  echo "Sample data:"
  echo "$METRICS_RESPONSE" | python3 -m json.tool | head -30
else
  echo "✗ Admin metrics endpoint failed"
  echo "Response: $METRICS_RESPONSE"
  exit 1
fi

# Clean up
rm -f /tmp/test_cookies.txt

echo ""
echo "✓ All tests passed!"
echo ""
echo "You can now access the metrics dashboard at:"
echo "  https://localhost:8443/admin-metrics.html"
