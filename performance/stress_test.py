#!/usr/bin/env python3
"""
Stress Test for TLAC Application
Tests system behavior under heavy concurrent load

Usage:
    python performance/stress_test.py
"""

import requests
import time
import threading
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://localhost:8443"


class StressTestResults:
    """Track stress test results"""
    def __init__(self):
        self.requests = 0
        self.successes = 0
        self.failures = 0
        self.response_times = []
        self.errors = defaultdict(int)
        self.lock = threading.Lock()

    def add_result(self, success: bool, response_time: float, error: str = None):
        """Add a test result"""
        with self.lock:
            self.requests += 1
            if success:
                self.successes += 1
                self.response_times.append(response_time)
            else:
                self.failures += 1
                if error:
                    self.errors[error] += 1

    def print_summary(self, duration: float):
        """Print test summary"""
        print("\n" + "="*70)
        print("STRESS TEST RESULTS")
        print("="*70)
        print(f"Duration: {duration:.2f}s")
        print(f"Total Requests: {self.requests}")
        print(f"Successful: {self.successes}")
        print(f"Failed: {self.failures}")

        if self.requests > 0:
            success_rate = (self.successes / self.requests) * 100
            print(f"Success Rate: {success_rate:.2f}%")

        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)
            sorted_times = sorted(self.response_times)
            median_time = sorted_times[len(sorted_times) // 2]
            p95_index = int(len(sorted_times) * 0.95)
            p95_time = sorted_times[p95_index]

            print(f"\nResponse Times:")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Median: {median_time:.2f}ms")
            print(f"  P95: {p95_time:.2f}ms")
            print(f"  Min: {min(self.response_times):.2f}ms")
            print(f"  Max: {max(self.response_times):.2f}ms")

        if duration > 0:
            throughput = self.requests / duration
            print(f"\nThroughput: {throughput:.2f} requests/second")

        if self.errors:
            print("\nErrors:")
            for error, count in sorted(self.errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count}")

        print("="*70 + "\n")


def make_request(session, method, endpoint, json_data=None, headers=None):
    """Make a single request and return timing"""
    start = time.time()
    try:
        if method == "GET":
            response = session.get(f"{BASE_URL}{endpoint}", timeout=10)
        else:
            response = session.post(
                f"{BASE_URL}{endpoint}",
                json=json_data,
                headers=headers,
                timeout=10
            )

        elapsed = (time.time() - start) * 1000
        return response.status_code < 400, elapsed, None

    except requests.exceptions.Timeout:
        elapsed = (time.time() - start) * 1000
        return False, elapsed, "Timeout"
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return False, elapsed, str(type(e).__name__)


def auth_stress_test(num_requests=100, num_workers=10):
    """Test authentication endpoint under load"""
    print(f"\n--- Authentication Stress Test ---")
    print(f"Requests: {num_requests}, Workers: {num_workers}\n")

    results = StressTestResults()
    start_time = time.time()

    def worker():
        session = requests.Session()
        session.verify = False

        success, elapsed, error = make_request(
            session,
            "POST",
            "/api/auth/login",
            json_data={"username": "duguid.t", "password": "clover8556"}
        )
        results.add_result(success, elapsed, error)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker) for _ in range(num_requests)]
        for future in as_completed(futures):
            future.result()

    duration = time.time() - start_time
    results.print_summary(duration)


def python_runner_stress_test(num_requests=50, num_workers=5):
    """Test Python code execution under load"""
    print(f"\n--- Python Runner Stress Test ---")
    print(f"Requests: {num_requests}, Workers: {num_workers}\n")

    results = StressTestResults()
    start_time = time.time()

    # Login first to get session
    session = requests.Session()
    session.verify = False
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "duguid.t", "password": "clover8556"}
    )
    csrf_token = login_resp.json().get("csrf_token", "") if login_resp.status_code == 200 else ""

    test_codes = [
        "print('Hello, World!')",
        "x = 5 + 3\nprint(x)",
        "for i in range(5):\n    print(i)",
        "print(sum(range(100)))",
    ]

    def worker(code):
        worker_session = requests.Session()
        worker_session.verify = False
        worker_session.cookies = session.cookies

        success, elapsed, error = make_request(
            worker_session,
            "POST",
            "/api/python/run",
            json_data={"code": code, "stdin": ""},
            headers={"X-CSRF-Token": csrf_token}
        )
        results.add_result(success, elapsed, error)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(worker, test_codes[i % len(test_codes)])
            for i in range(num_requests)
        ]
        for future in as_completed(futures):
            future.result()

    duration = time.time() - start_time
    results.print_summary(duration)


def activity_save_stress_test(num_requests=200, num_workers=20):
    """Test activity save endpoint under load"""
    print(f"\n--- Activity Save Stress Test ---")
    print(f"Requests: {num_requests}, Workers: {num_workers}\n")

    results = StressTestResults()
    start_time = time.time()

    # Login first
    session = requests.Session()
    session.verify = False
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "duguid.t", "password": "clover8556"}
    )
    csrf_token = login_resp.json().get("csrf_token", "") if login_resp.status_code == 200 else ""

    def worker(request_num):
        worker_session = requests.Session()
        worker_session.verify = False
        worker_session.cookies = session.cookies

        payload = {
            "lesson_id": f"lesson-{(request_num % 12) + 1}",
            "activity_id": f"{(request_num % 10) + 1:02d}-activity",
            "state": {"progress": request_num % 100, "completed": request_num % 2 == 0}
        }

        success, elapsed, error = make_request(
            worker_session,
            "POST",
            "/api/activity/state",
            json_data=payload,
            headers={"X-CSRF-Token": csrf_token}
        )
        results.add_result(success, elapsed, error)

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, i) for i in range(num_requests)]
        for future in as_completed(futures):
            future.result()

    duration = time.time() - start_time
    results.print_summary(duration)


def concurrent_user_simulation(num_users=20, duration_seconds=30):
    """Simulate concurrent users performing mixed actions"""
    print(f"\n--- Concurrent User Simulation ---")
    print(f"Users: {num_users}, Duration: {duration_seconds}s\n")

    results = StressTestResults()
    stop_flag = threading.Event()

    def simulate_user(user_id):
        """Simulate a single user"""
        session = requests.Session()
        session.verify = False

        # Login
        login_resp = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "duguid.t", "password": "clover8556"}
        )

        if login_resp.status_code != 200:
            return

        csrf_token = login_resp.json().get("csrf_token", "")
        request_count = 0

        while not stop_flag.is_set() and request_count < 50:
            # Perform random actions
            import random
            action = random.choice(['auth', 'activity_get', 'activity_save', 'health'])

            if action == 'auth':
                success, elapsed, error = make_request(session, "GET", "/api/auth/me")
            elif action == 'activity_get':
                lesson = random.randint(1, 12)
                activity = random.randint(1, 10)
                success, elapsed, error = make_request(
                    session,
                    "GET",
                    f"/api/activity/state?lesson_id=lesson-{lesson}&activity_id={activity:02d}-activity"
                )
            elif action == 'activity_save':
                lesson = random.randint(1, 12)
                activity = random.randint(1, 10)
                success, elapsed, error = make_request(
                    session,
                    "POST",
                    "/api/activity/state",
                    json_data={
                        "lesson_id": f"lesson-{lesson}",
                        "activity_id": f"{activity:02d}-activity",
                        "state": {"progress": random.randint(0, 100)}
                    },
                    headers={"X-CSRF-Token": csrf_token}
                )
            else:  # health
                success, elapsed, error = make_request(session, "GET", "/api/health")

            results.add_result(success, elapsed, error)
            request_count += 1
            time.sleep(random.uniform(0.1, 0.5))

    start_time = time.time()
    threads = []

    for i in range(num_users):
        thread = threading.Thread(target=simulate_user, args=(i,))
        thread.start()
        threads.append(thread)

    # Run for specified duration
    time.sleep(duration_seconds)
    stop_flag.set()

    # Wait for all threads
    for thread in threads:
        thread.join()

    duration = time.time() - start_time
    results.print_summary(duration)


def main():
    """Run all stress tests"""
    print("\n" + "="*70)
    print("TLAC STRESS TEST SUITE")
    print("="*70)

    # Run tests
    auth_stress_test(num_requests=100, num_workers=10)
    time.sleep(2)

    activity_save_stress_test(num_requests=200, num_workers=20)
    time.sleep(2)

    python_runner_stress_test(num_requests=30, num_workers=3)
    time.sleep(2)

    concurrent_user_simulation(num_users=15, duration_seconds=20)

    print("\n" + "="*70)
    print("ALL STRESS TESTS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("  1. Check the admin metrics dashboard: https://localhost:8443/admin-metrics.html")
    print("  2. Review Prometheus metrics: http://localhost:9090")
    print("  3. Check application logs for any errors")
    print("\n")


if __name__ == "__main__":
    main()
