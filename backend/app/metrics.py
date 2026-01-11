"""
Prometheus metrics for monitoring application performance and health
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Application info
app_info = Info("tlac_app", "TLAC application information")
app_info.info({
    "version": "1.1.0",
    "name": "Thinking Like a Coder",
    "environment": "production"
})

# HTTP request metrics
http_requests_total = Counter(
    "tlac_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "tlac_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    "tlac_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"]
)

# Authentication metrics
auth_login_attempts_total = Counter(
    "tlac_auth_login_attempts_total",
    "Total login attempts",
    ["status"]  # success, failed, rate_limited
)

auth_sessions_active = Gauge(
    "tlac_auth_sessions_active",
    "Number of active user sessions"
)

# Activity metrics
activity_saves_total = Counter(
    "tlac_activity_saves_total",
    "Total activity state saves",
    ["lesson_id"]
)

activity_save_duration_seconds = Histogram(
    "tlac_activity_save_duration_seconds",
    "Activity save operation latency",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Python runner metrics
python_runs_total = Counter(
    "tlac_python_runs_total",
    "Total Python code executions",
    ["status"]  # success, error, timeout
)

python_run_duration_seconds = Histogram(
    "tlac_python_run_duration_seconds",
    "Python execution duration",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0)
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    "tlac_rate_limit_exceeded_total",
    "Total requests blocked by rate limiting",
    ["endpoint", "limit_type"]  # limit_type: login, api
)

rate_limit_usage = Histogram(
    "tlac_rate_limit_usage",
    "Rate limit usage percentage",
    ["endpoint"],
    buckets=(0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0)
)

# Database metrics
db_connections_active = Gauge(
    "tlac_db_connections_active",
    "Number of active database connections"
)

db_query_duration_seconds = Histogram(
    "tlac_db_query_duration_seconds",
    "Database query duration",
    ["operation"],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

db_errors_total = Counter(
    "tlac_db_errors_total",
    "Total database errors",
    ["error_type"]
)

# Audit log metrics
audit_entries_total = Counter(
    "tlac_audit_entries_total",
    "Total audit log entries",
    ["action"]
)

# Teacher/admin metrics
teacher_marks_total = Counter(
    "tlac_teacher_marks_total",
    "Total activity marks assigned by teachers"
)

admin_user_operations_total = Counter(
    "tlac_admin_user_operations_total",
    "Total admin user management operations",
    ["operation"]  # create, update, delete
)

# Error metrics
errors_total = Counter(
    "tlac_errors_total",
    "Total application errors",
    ["error_type", "endpoint"]
)

# Backup metrics
backup_duration_seconds = Histogram(
    "tlac_backup_duration_seconds",
    "Backup operation duration",
    buckets=(10, 30, 60, 120, 300, 600, 1200)
)

backup_size_bytes = Gauge(
    "tlac_backup_size_bytes",
    "Size of last backup in bytes",
    ["backup_type"]  # database, data
)

backup_last_success_timestamp = Gauge(
    "tlac_backup_last_success_timestamp",
    "Timestamp of last successful backup"
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint to avoid self-monitoring loops
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        # Normalize endpoint to avoid high cardinality
        endpoint = self._normalize_endpoint(request.url.path)

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Measure request duration
        start_time = time.time()

        try:
            response = await call_next(request)
            status = response.status_code

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            return response

        except Exception as e:
            # Record error
            errors_total.labels(
                error_type=type(e).__name__,
                endpoint=endpoint
            ).inc()
            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()

    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint paths to reduce cardinality
        Replace IDs and variable parts with placeholders
        """
        # Skip static files
        if path.startswith("/static/") or path.startswith("/core/") or path.startswith("/lessons/"):
            return "/static"

        # API endpoints
        if path.startswith("/api/"):
            parts = path.split("/")

            # /api/activity/state/lesson-1/a01 -> /api/activity/state/{lesson}/{activity}
            if len(parts) >= 6 and parts[2] == "activity" and parts[3] == "state":
                return "/api/activity/state/{lesson}/{activity}"

            # /api/teacher/pupils/{username} -> /api/teacher/pupils/{username}
            if len(parts) >= 5 and parts[2] == "teacher" and parts[3] == "pupils":
                return "/api/teacher/pupils/{username}"

            # /api/python/run -> /api/python/run
            if parts[2:4] == ["python", "run"]:
                return "/api/python/run"

            # Generic normalization for other endpoints
            # Keep first 3-4 parts, replace rest with {id}
            if len(parts) > 4:
                return "/".join(parts[:4]) + "/{id}"

        return path


def record_login_attempt(success: bool, rate_limited: bool = False):
    """Record a login attempt"""
    if rate_limited:
        auth_login_attempts_total.labels(status="rate_limited").inc()
    elif success:
        auth_login_attempts_total.labels(status="success").inc()
    else:
        auth_login_attempts_total.labels(status="failed").inc()


def record_activity_save(lesson_id: str, duration: float):
    """Record an activity save operation"""
    activity_saves_total.labels(lesson_id=lesson_id).inc()
    activity_save_duration_seconds.observe(duration)


def record_python_run(status: str, duration: float):
    """Record a Python code execution"""
    python_runs_total.labels(status=status).inc()
    python_run_duration_seconds.observe(duration)


def record_rate_limit_exceeded(endpoint: str, limit_type: str):
    """Record a rate limit violation"""
    rate_limit_exceeded_total.labels(
        endpoint=endpoint,
        limit_type=limit_type
    ).inc()


def record_rate_limit_usage(endpoint: str, current: int, limit: int):
    """Record rate limit usage"""
    if limit > 0:
        usage = current / limit
        rate_limit_usage.labels(endpoint=endpoint).observe(usage)


def record_audit_entry(action: str):
    """Record an audit log entry"""
    audit_entries_total.labels(action=action).inc()


def record_teacher_mark():
    """Record a teacher marking operation"""
    teacher_marks_total.inc()


def record_admin_operation(operation: str):
    """Record an admin user operation"""
    admin_user_operations_total.labels(operation=operation).inc()


def record_db_query(operation: str, duration: float):
    """Record a database query"""
    db_query_duration_seconds.labels(operation=operation).observe(duration)


def record_db_error(error_type: str):
    """Record a database error"""
    db_errors_total.labels(error_type=error_type).inc()


def update_active_sessions(count: int):
    """Update active sessions count"""
    auth_sessions_active.set(count)


def update_db_connections(count: int):
    """Update active database connections count"""
    db_connections_active.set(count)


def record_backup(duration: float, db_size: int, data_size: int):
    """Record backup metrics"""
    backup_duration_seconds.observe(duration)
    backup_size_bytes.labels(backup_type="database").set(db_size)
    backup_size_bytes.labels(backup_type="data").set(data_size)
    backup_last_success_timestamp.set(time.time())
