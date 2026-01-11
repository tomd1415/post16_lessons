#!/usr/bin/env python3
"""
API Endpoint Benchmark Script
Measures response times for key API endpoints

Usage:
    python performance/benchmark.py
"""

import requests
import time
import statistics
import urllib3
from typing import List, Dict, Tuple

# Disable SSL warnings for local testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:8443"
ITERATIONS = 100


def benchmark_endpoint(
    method: str,
    endpoint: str,
    headers: Dict = None,
    json_data: Dict = None,
    description: str = ""
) -> Tuple[float, float, float, float]:
    """
    Benchmark a single endpoint
    Returns: (avg, median, p95, p99) in milliseconds
    """
    times = []

    for _ in range(ITERATIONS):
        start = time.time()
        try:
            if method == "GET":
                response = requests.get(
                    f"{BASE_URL}{endpoint}",
                    headers=headers,
                    verify=False,
                    timeout=10
                )
            elif method == "POST":
                response = requests.post(
                    f"{BASE_URL}{endpoint}",
                    headers=headers,
                    json=json_data,
                    verify=False,
                    timeout=10
                )

            elapsed = (time.time() - start) * 1000  # Convert to ms
            if response.status_code < 400:
                times.append(elapsed)
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

    if not times:
        return 0, 0, 0, 0

    avg = statistics.mean(times)
    median = statistics.median(times)
    p95 = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
    p99 = statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)

    return avg, median, p95, p99


def main():
    """Run benchmarks"""
    print("\n" + "="*70)
    print("TLAC API Performance Benchmark")
    print("="*70)
    print(f"Iterations per endpoint: {ITERATIONS}")
    print(f"Target: {BASE_URL}")
    print("="*70 + "\n")

    # Login to get session cookies and CSRF token
    print("Authenticating...")
    session = requests.Session()
    session.verify = False

    login_response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "duguid.t", "password": "clover8556"}
    )

    csrf_token = ""
    if login_response.status_code == 200:
        csrf_token = login_response.json().get("csrf_token", "")
        print("✓ Authentication successful\n")
    else:
        print("⚠️  Authentication failed, some tests may fail\n")

    headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}

    # Define benchmarks
    benchmarks = [
        # Public endpoints
        ("GET", "/api/health", None, None, "Health Check"),
        ("GET", "/lessons/manifest.json", None, None, "Lesson Manifest"),

        # Authentication
        ("GET", "/api/auth/me", None, None, "Check Auth Status"),

        # Activity endpoints
        (
            "GET",
            "/api/activity/state?lesson_id=lesson-4&activity_id=01-intro",
            None,
            None,
            "Get Activity State"
        ),
        (
            "POST",
            "/api/activity/state",
            headers,
            {
                "lesson_id": "lesson-4",
                "activity_id": "01-intro",
                "state": {"completed": False, "progress": 50}
            },
            "Save Activity State"
        ),

        # Python runner
        (
            "POST",
            "/api/python/run",
            headers,
            {"code": "print('Hello, World!')", "stdin": ""},
            "Python Code Execution"
        ),

        # Teacher endpoints
        ("GET", "/api/teacher/pupils/duguid.t", None, None, "View Pupil Progress"),
    ]

    results = []

    print("Running benchmarks...\n")
    for method, endpoint, request_headers, json_data, description in benchmarks:
        print(f"Testing: {description}")
        print(f"  {method} {endpoint}")

        # Use session for requests to maintain cookies
        if method == "GET":
            times = []
            for _ in range(ITERATIONS):
                start = time.time()
                try:
                    response = session.get(f"{BASE_URL}{endpoint}", timeout=10)
                    elapsed = (time.time() - start) * 1000
                    if response.status_code < 400:
                        times.append(elapsed)
                except:
                    pass
        else:
            times = []
            for _ in range(ITERATIONS):
                start = time.time()
                try:
                    response = session.post(
                        f"{BASE_URL}{endpoint}",
                        headers=request_headers,
                        json=json_data,
                        timeout=10
                    )
                    elapsed = (time.time() - start) * 1000
                    if response.status_code < 400:
                        times.append(elapsed)
                except:
                    pass

        if times:
            avg = statistics.mean(times)
            median = statistics.median(times)
            p95 = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
            p99 = statistics.quantiles(times, n=100)[98] if len(times) >= 100 else max(times)

            print(f"  Avg: {avg:.2f}ms | Median: {median:.2f}ms | P95: {p95:.2f}ms | P99: {p99:.2f}ms")

            # Color code results
            if avg < 100:
                status = "✓ Excellent"
            elif avg < 300:
                status = "✓ Good"
            elif avg < 500:
                status = "⚠️  Fair"
            else:
                status = "✗ Slow"

            print(f"  {status}\n")

            results.append({
                "description": description,
                "method": method,
                "endpoint": endpoint,
                "avg": avg,
                "median": median,
                "p95": p95,
                "p99": p99
            })
        else:
            print(f"  ✗ Failed - no successful requests\n")

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"{'Endpoint':<30} {'Avg (ms)':<12} {'Median (ms)':<12} {'P95 (ms)':<12}")
    print("-"*70)

    for result in results:
        print(
            f"{result['description']:<30} "
            f"{result['avg']:<12.2f} "
            f"{result['median']:<12.2f} "
            f"{result['p95']:<12.2f}"
        )

    print("="*70)

    # Performance targets
    print("\nPerformance Targets:")
    print("  ✓ Excellent: < 100ms average")
    print("  ✓ Good:      < 300ms average")
    print("  ⚠️  Fair:      < 500ms average")
    print("  ✗ Slow:      >= 500ms average")

    # Check if any endpoints are slow
    slow_endpoints = [r for r in results if r['avg'] >= 500]
    if slow_endpoints:
        print(f"\n⚠️  Warning: {len(slow_endpoints)} endpoint(s) are slow:")
        for endpoint in slow_endpoints:
            print(f"  - {endpoint['description']}: {endpoint['avg']:.2f}ms")
    else:
        print("\n✓ All endpoints performing within acceptable limits")

    print("\n")


if __name__ == "__main__":
    main()
