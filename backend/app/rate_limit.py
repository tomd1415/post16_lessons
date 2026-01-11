from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session


def utcnow():
    return datetime.now(timezone.utc)


def ensure_timezone_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is timezone-aware (for SQLite compatibility)"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# API rate limit configuration (requests per minute)
API_RATE_LIMITS = {
    "activity_save": 60,  # 60 saves per minute
    "python_run": 20,  # 20 code executions per minute
    "mark_activity": 30,  # 30 marks per minute
    "default": 120,  # 120 requests per minute for other endpoints
}


def compute_lock_seconds(failed_count: int) -> int:
    if failed_count < 3:
        return 0
    if failed_count < 5:
        return 30
    if failed_count < 7:
        return 120
    if failed_count < 9:
        return 300
    return 600


class LoginLimiter:
    """
    Database-backed login rate limiter.
    Tracks failed login attempts and applies exponential backoff.
    """

    def check(self, db: Session, key: str) -> int:
        """
        Check if the given key is currently locked.
        Returns number of seconds remaining in lock, or 0 if not locked.
        """
        from .models import LoginAttempt

        attempt = db.query(LoginAttempt).filter(LoginAttempt.identifier == key).first()
        if not attempt:
            return 0

        locked_until = ensure_timezone_aware(attempt.locked_until)
        if locked_until and locked_until > utcnow():
            return int((locked_until - utcnow()).total_seconds())
        return 0

    def record_failure(self, db: Session, key: str) -> int:
        """
        Record a failed login attempt for the given key.
        Returns number of seconds the key is locked for.
        """
        from .models import LoginAttempt

        attempt = db.query(LoginAttempt).filter(LoginAttempt.identifier == key).first()
        if attempt:
            attempt.failed_count += 1
            attempt.updated_at = utcnow()
        else:
            attempt = LoginAttempt(
                identifier=key,
                failed_count=1,
            )
            db.add(attempt)

        lock_seconds = compute_lock_seconds(attempt.failed_count)
        if lock_seconds:
            attempt.locked_until = utcnow() + timedelta(seconds=lock_seconds)
        else:
            attempt.locked_until = None

        db.commit()
        return lock_seconds

    def reset(self, db: Session, key: str) -> None:
        """
        Reset (delete) the login attempt record for the given key.
        Called on successful login.
        """
        from .models import LoginAttempt

        attempt = db.query(LoginAttempt).filter(LoginAttempt.identifier == key).first()
        if attempt:
            db.delete(attempt)
            db.commit()


class ApiRateLimiter:
    """
    Database-backed API rate limiter using sliding window.
    Tracks API requests per user/IP and enforces configurable limits.
    """

    def __init__(self, window_minutes: int = 1):
        self.window_minutes = window_minutes

    def check_and_increment(
        self,
        db: Session,
        identifier: str,
        endpoint: str,
        limit: Optional[int] = None,
    ) -> tuple[bool, int, int]:
        """
        Check if the request is within rate limit and increment counter.
        Returns (is_allowed, current_count, limit).
        """
        from .models import ApiRateLimit

        if limit is None:
            limit = API_RATE_LIMITS.get(endpoint, API_RATE_LIMITS["default"])

        now = utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)

        # Clean up old records outside the window
        db.query(ApiRateLimit).filter(
            ApiRateLimit.identifier == identifier,
            ApiRateLimit.endpoint == endpoint,
            ApiRateLimit.window_start < window_start,
        ).delete()

        # Get or create rate limit record
        record = (
            db.query(ApiRateLimit)
            .filter(
                ApiRateLimit.identifier == identifier,
                ApiRateLimit.endpoint == endpoint,
            )
            .first()
        )

        if not record:
            # First request in this window
            record = ApiRateLimit(
                identifier=identifier,
                endpoint=endpoint,
                request_count=1,
                window_start=now,
            )
            db.add(record)
            db.commit()
            return True, 1, limit

        # Check if we're still in the same window
        window_start_aware = ensure_timezone_aware(record.window_start)
        if window_start_aware and window_start_aware < window_start:
            # Start a new window
            record.window_start = now
            record.request_count = 1
            record.updated_at = now
        else:
            # Increment counter in current window
            record.request_count += 1
            record.updated_at = now

        db.commit()

        is_allowed = record.request_count <= limit
        return is_allowed, record.request_count, limit
