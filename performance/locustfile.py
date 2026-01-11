"""
Performance tests for TLAC (Thinking Like a Coder) application
Uses Locust for load testing and performance validation

Run with:
    locust -f performance/locustfile.py --host=https://localhost:8443
"""

import random
import json
from locust import HttpUser, task, between, events
from faker import Faker

fake = Faker()


class TLACUser(HttpUser):
    """
    Simulates a typical TLAC user performing various actions
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Called when a simulated user starts"""
        # Disable SSL verification for local testing
        self.client.verify = False

        # Login as a pupil
        self.username = f"perf.user{random.randint(1, 1000)}"
        self.login()

    def login(self):
        """Authenticate as a user"""
        response = self.client.post("/api/auth/login", json={
            "username": "duguid.t",  # Use existing test user
            "password": "clover8556"
        }, name="/api/auth/login")

        if response.status_code == 200:
            self.csrf_token = response.json().get("csrf_token", "")
        else:
            # If login fails, try with default admin
            response = self.client.post("/api/auth/login", json={
                "username": "admin",
                "password": "ChangeMe123"
            }, name="/api/auth/login (fallback)")
            if response.status_code == 200:
                self.csrf_token = response.json().get("csrf_token", "")

    @task(5)
    def check_auth(self):
        """Check authentication status (common operation)"""
        self.client.get("/api/auth/me", name="/api/auth/me")

    @task(3)
    def get_activity_state(self):
        """Fetch activity state"""
        lesson_id = f"lesson-{random.randint(1, 12)}"
        activity_id = f"{random.randint(1, 10):02d}-activity"

        self.client.get(
            f"/api/activity/state?lesson_id={lesson_id}&activity_id={activity_id}",
            name="/api/activity/state"
        )

    @task(2)
    def save_activity_state(self):
        """Save activity progress"""
        lesson_id = f"lesson-{random.randint(1, 12)}"
        activity_id = f"{random.randint(1, 10):02d}-activity"

        payload = {
            "lesson_id": lesson_id,
            "activity_id": activity_id,
            "state": {
                "completed": random.choice([True, False]),
                "progress": random.randint(0, 100),
                "code": "print('Hello, World!')",
                "last_modified": "2026-01-11T21:00:00Z"
            }
        }

        self.client.post(
            "/api/activity/state",
            json=payload,
            headers={"X-CSRF-Token": getattr(self, 'csrf_token', '')},
            name="/api/activity/state (save)"
        )

    @task(1)
    def run_python_code(self):
        """Execute Python code"""
        test_codes = [
            "print('Hello, World!')",
            "x = 5 + 3\nprint(x)",
            "for i in range(5):\n    print(i)",
            "def greet(name):\n    return f'Hello, {name}'\nprint(greet('Alice'))",
        ]

        payload = {
            "code": random.choice(test_codes),
            "stdin": ""
        }

        self.client.post(
            "/api/python/run",
            json=payload,
            headers={"X-CSRF-Token": getattr(self, 'csrf_token', '')},
            name="/api/python/run"
        )

    @task(1)
    def get_lesson_manifest(self):
        """Fetch lesson manifest"""
        self.client.get("/lessons/manifest.json", name="/lessons/manifest.json")


class TeacherUser(HttpUser):
    """
    Simulates a teacher performing marking and admin tasks
    """
    wait_time = between(2, 5)

    def on_start(self):
        """Called when a simulated teacher starts"""
        self.client.verify = False
        self.login()

    def login(self):
        """Login as teacher"""
        response = self.client.post("/api/auth/login", json={
            "username": "t.duguid",
            "password": "clover8556"
        }, name="/api/auth/login (teacher)")

        if response.status_code == 200:
            self.csrf_token = response.json().get("csrf_token", "")

    @task(3)
    def check_auth(self):
        """Check authentication"""
        self.client.get("/api/auth/me", name="/api/auth/me (teacher)")

    @task(2)
    def view_pupil_progress(self):
        """View a pupil's progress"""
        self.client.get(
            "/api/teacher/pupils/duguid.t",
            name="/api/teacher/pupils/{username}"
        )

    @task(1)
    def mark_activity(self):
        """Mark an activity as complete"""
        payload = {
            "username": "duguid.t",
            "lesson_id": f"lesson-{random.randint(1, 12)}",
            "activity_id": f"{random.randint(1, 10):02d}-activity",
            "marked": True
        }

        self.client.post(
            "/api/teacher/mark",
            json=payload,
            headers={"X-CSRF-Token": getattr(self, 'csrf_token', '')},
            name="/api/teacher/mark"
        )


class AdminUser(HttpUser):
    """
    Simulates an admin checking metrics and system health
    """
    wait_time = between(5, 10)

    def on_start(self):
        """Called when a simulated admin starts"""
        self.client.verify = False
        self.login()

    def login(self):
        """Login as admin"""
        response = self.client.post("/api/auth/login", json={
            "username": "admin",
            "password": "ChangeMe123"
        }, name="/api/auth/login (admin)")

        if response.status_code == 200:
            self.csrf_token = response.json().get("csrf_token", "")

    @task(5)
    def view_metrics_dashboard(self):
        """View admin metrics"""
        self.client.get("/api/admin/metrics", name="/api/admin/metrics")

    @task(2)
    def check_system_health(self):
        """Check API health"""
        self.client.get("/api/health", name="/api/health")

    @task(1)
    def view_audit_log(self):
        """View audit log"""
        self.client.get(
            "/api/admin/audit?limit=50",
            name="/api/admin/audit"
        )


# Custom events for reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print("\n" + "="*60)
    print("TLAC Performance Test Starting")
    print("="*60)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.user_count if hasattr(environment.runner, 'user_count') else 'N/A'}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("\n" + "="*60)
    print("TLAC Performance Test Complete")
    print("="*60)

    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median Response Time: {stats.total.median_response_time:.2f}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")

    if stats.total.num_failures > 0:
        print(f"\n⚠️  Failure Rate: {(stats.total.num_failures / stats.total.num_requests * 100):.2f}%")

    print("="*60 + "\n")
