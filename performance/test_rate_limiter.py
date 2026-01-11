#!/usr/bin/env python3
"""
Rate Limiter Validation Test
Verifies that rate limiting is working correctly

Usage:
    python performance/test_rate_limiter.py
"""

import requests
import time
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:8443"


def test_login_rate_limit():
    """
    Test login rate limiting
    Should trigger after 5 failed attempts
    """
    print("\n" + "="*70)
    print("Testing Login Rate Limiter")
    print("="*70)
    print("Attempting multiple failed logins with same IP/username...\n")

    session = requests.Session()
    session.verify = False

    # Try logging in with wrong password multiple times
    results = []
    for i in range(10):
        start = time.time()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "test.ratelimit", "password": "wrongpassword"}
        )
        elapsed = (time.time() - start) * 1000

        status = response.status_code
        try:
            detail = response.json().get("detail", "")
        except:
            detail = ""

        results.append({
            "attempt": i + 1,
            "status": status,
            "detail": detail,
            "time": elapsed
        })

        print(f"Attempt {i+1}: Status {status} - {detail} ({elapsed:.0f}ms)")

        # Small delay between requests
        time.sleep(0.1)

    # Analyze results
    print("\n" + "-"*70)
    print("Analysis:")

    rate_limited = sum(1 for r in results if r["status"] == 429)
    failed = sum(1 for r in results if r["status"] == 401)

    print(f"  Failed login attempts (401): {failed}")
    print(f"  Rate limited attempts (429): {rate_limited}")

    if rate_limited > 0:
        first_rate_limit = next(i for i, r in enumerate(results) if r["status"] == 429)
        print(f"  First rate limit triggered at attempt: {first_rate_limit + 1}")
        print("\n✓ Rate limiting is working correctly!")
    else:
        print("\n⚠️  Warning: No rate limiting detected after 10 attempts")

    print("="*70 + "\n")


def test_api_rate_limit():
    """
    Test general API rate limiting
    """
    print("\n" + "="*70)
    print("Testing API Rate Limiter")
    print("="*70)
    print("Making rapid requests to test rate limiting...\n")

    session = requests.Session()
    session.verify = False

    # Login first
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "duguid.t", "password": "clover8556"}
    )

    if login_resp.status_code != 200:
        print("✗ Failed to authenticate, skipping API rate limit test")
        return

    csrf_token = login_resp.json().get("csrf_token", "")

    # Make many rapid requests to activity save endpoint
    results = []
    start_time = time.time()

    for i in range(100):
        response = session.post(
            f"{BASE_URL}/api/activity/state",
            json={
                "lesson_id": "lesson-1",
                "activity_id": "01-test",
                "state": {"progress": i}
            },
            headers={"X-CSRF-Token": csrf_token}
        )

        results.append({
            "request": i + 1,
            "status": response.status_code,
            "time": time.time() - start_time
        })

        if i < 5:  # Print first few requests
            print(f"Request {i+1}: Status {response.status_code}")

    duration = time.time() - start_time

    # Analysis
    print(f"\n... (made {len(results)} total requests in {duration:.2f}s)\n")
    print("-"*70)
    print("Analysis:")

    success_count = sum(1 for r in results if r["status"] == 200)
    rate_limited = sum(1 for r in results if r["status"] == 429)
    throughput = len(results) / duration

    print(f"  Successful requests: {success_count}")
    print(f"  Rate limited requests: {rate_limited}")
    print(f"  Throughput: {throughput:.2f} requests/second")

    if rate_limited > 0:
        print(f"\n✓ Rate limiting activated after heavy load")
    else:
        print(f"\n✓ All requests succeeded (no rate limiting triggered at this load)")

    print("="*70 + "\n")


def test_python_runner_rate_limit():
    """
    Test Python runner rate limiting
    """
    print("\n" + "="*70)
    print("Testing Python Runner Rate Limiter")
    print("="*70)
    print("Making rapid Python execution requests...\n")

    session = requests.Session()
    session.verify = False

    # Login first
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "duguid.t", "password": "clover8556"}
    )

    if login_resp.status_code != 200:
        print("✗ Failed to authenticate, skipping Python runner rate limit test")
        return

    csrf_token = login_resp.json().get("csrf_token", "")

    # Make rapid Python execution requests
    results = []
    start_time = time.time()

    for i in range(20):
        response = session.post(
            f"{BASE_URL}/api/python/run",
            json={
                "code": f"print({i})",
                "stdin": ""
            },
            headers={"X-CSRF-Token": csrf_token}
        )

        status = response.status_code
        results.append({"request": i + 1, "status": status})

        if i < 5:
            print(f"Request {i+1}: Status {status}")

        time.sleep(0.1)  # Small delay since Python execution takes time

    duration = time.time() - start_time

    print(f"\n... (made {len(results)} total requests in {duration:.2f}s)\n")
    print("-"*70)
    print("Analysis:")

    success_count = sum(1 for r in results if r["status"] == 200)
    rate_limited = sum(1 for r in results if r["status"] == 429)

    print(f"  Successful executions: {success_count}")
    print(f"  Rate limited: {rate_limited}")

    if rate_limited > 0:
        first_limit = next(i for i, r in enumerate(results) if r["status"] == 429)
        print(f"  First rate limit at request: {first_limit + 1}")
        print(f"\n✓ Python runner rate limiting is working")
    else:
        print(f"\n✓ All executions succeeded (rate limit not triggered)")

    print("="*70 + "\n")


def main():
    """Run all rate limiter tests"""
    print("\n" + "="*70)
    print("RATE LIMITER VALIDATION TESTS")
    print("="*70)
    print("These tests validate that rate limiting is working correctly")
    print("to protect the system from abuse and overload.\n")

    test_login_rate_limit()
    time.sleep(2)

    test_api_rate_limit()
    time.sleep(2)

    test_python_runner_rate_limit()

    print("\n" + "="*70)
    print("RATE LIMITER TESTS COMPLETE")
    print("="*70)
    print("\nRecommendations:")
    print("  - Monitor rate limit metrics in admin dashboard")
    print("  - Adjust limits in backend/app/config.py if needed")
    print("  - Check database for rate limit records")
    print("\n")


if __name__ == "__main__":
    main()
