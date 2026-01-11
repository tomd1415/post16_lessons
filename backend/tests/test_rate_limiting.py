"""
Tests for rate limiting functionality
"""
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.rate_limit import ApiRateLimiter, LoginLimiter, utcnow
from backend.tests.utils import login, seed_user


def test_login_rate_limit_blocks_after_max_attempts(client, db_session):
    """Test that login is blocked after max failed attempts"""
    seed_user(db_session, "test.user", role="pupil", cohort_year="2024", password="Correct123!")

    # Make max failed attempts
    for _ in range(5):
        res = client.post(
            "/api/auth/login",
            json={"username": "test.user", "password": "WrongPassword"},
            headers={"Content-Type": "application/json"},
        )
        assert res.status_code in [401, 429]

    # Next attempt should be rate limited
    res = client.post(
        "/api/auth/login",
        json={"username": "test.user", "password": "Correct123!"},
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 429
    data = res.json()
    assert "locked" in data["detail"].lower() or "too many" in data["detail"].lower()


def test_login_rate_limit_allows_after_successful_login(client, db_session):
    """Test that rate limit is reset after successful login"""
    seed_user(db_session, "test.user", role="pupil", cohort_year="2024", password="Correct123!")

    # Make a few failed attempts
    for _ in range(2):
        client.post(
            "/api/auth/login",
            json={"username": "test.user", "password": "WrongPassword"},
            headers={"Content-Type": "application/json"},
        )

    # Successful login should reset the counter
    res = client.post(
        "/api/auth/login",
        json={"username": "test.user", "password": "Correct123!"},
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 200

    # Should be able to log in again
    res = client.post(
        "/api/auth/login",
        json={"username": "test.user", "password": "Correct123!"},
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 200


def test_login_limiter_lockout_duration(db_session):
    """Test that lockout duration increases with failed attempts"""
    limiter = LoginLimiter()
    key = "test.user"

    # 3 failures - 30 second lock
    for _ in range(3):
        lock_seconds = limiter.record_failure(db_session, key)
    assert lock_seconds == 30

    # 5 total failures - 120 second lock
    for _ in range(2):
        lock_seconds = limiter.record_failure(db_session, key)
    assert lock_seconds == 120


def test_login_limiter_reset_clears_attempts(db_session):
    """Test that reset clears login attempts"""
    from backend.app.models import LoginAttempt

    limiter = LoginLimiter()
    key = "test.user"

    # Record some failures
    limiter.record_failure(db_session, key)
    limiter.record_failure(db_session, key)

    # Verify they exist
    attempt = db_session.query(LoginAttempt).filter(LoginAttempt.identifier == key).first()
    assert attempt is not None
    assert attempt.failed_count == 2

    # Reset should delete the record
    limiter.reset(db_session, key)

    # Verify record is gone
    attempt = db_session.query(LoginAttempt).filter(LoginAttempt.identifier == key).first()
    assert attempt is None


def test_login_limiter_database_persistence(db_session):
    """Test that login attempts are persisted in database"""
    from backend.app.models import LoginAttempt

    limiter = LoginLimiter()
    key = "test.user"

    # Record failed attempts (commits automatically)
    limiter.record_failure(db_session, key)
    limiter.record_failure(db_session, key)

    # Check database
    attempt = db_session.query(LoginAttempt).filter(LoginAttempt.identifier == key).first()
    assert attempt is not None
    assert attempt.failed_count == 2


def test_api_rate_limiter_sliding_window(db_session):
    """Test that API rate limiter uses sliding window"""
    from backend.app.models import ApiRateLimit

    limiter = ApiRateLimiter()
    identifier = "user:123"
    endpoint = "test_endpoint"

    # Make requests within window (commits automatically)
    for _ in range(3):
        is_allowed, current, limit = limiter.check_and_increment(db_session, identifier, endpoint, limit=5)

    # Should still be allowed
    is_allowed, current, limit = limiter.check_and_increment(db_session, identifier, endpoint, limit=5)
    assert is_allowed
    assert current <= limit

    # Exhaust the limit (one more to reach 5, then exceed)
    is_allowed, current, limit = limiter.check_and_increment(db_session, identifier, endpoint, limit=5)

    # Should be blocked on 6th request
    is_allowed, current, limit = limiter.check_and_increment(db_session, identifier, endpoint, limit=5)
    assert not is_allowed
    assert current > limit


def test_api_rate_limiter_window_reset(db_session):
    """Test that rate limit window resets after time period"""
    from backend.app.models import ApiRateLimit

    limiter = ApiRateLimiter()
    identifier = "user:123"
    endpoint = "test_endpoint"

    # Exhaust limit
    for _ in range(55):
        limiter.check_and_increment(db_session, identifier, endpoint, limit=50)

    # Manually set window_start to past
    record = (
        db_session.query(ApiRateLimit)
        .filter(
            ApiRateLimit.identifier == identifier,
            ApiRateLimit.endpoint == endpoint,
        )
        .first()
    )
    record.window_start = utcnow() - timedelta(minutes=2)
    db_session.commit()

    # Should be allowed again (new window)
    is_allowed, current, limit = limiter.check_and_increment(db_session, identifier, endpoint, limit=50)
    assert is_allowed
    assert current == 1  # Fresh window
