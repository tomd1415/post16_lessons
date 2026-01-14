from datetime import datetime, timedelta, timezone

from backend.app.models import ActivityFeedback, ActivityMark, ActivityRevision, ActivityState, AuditLog, Session as AuthSession, User
from backend.tests.utils import login, seed_user


def test_admin_metrics_requires_admin(client, db_session):
    """Ensure /api/admin/metrics requires admin role."""
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")
    seed_user(db_session, "admin.one", role="admin", cohort_year=None, password="Secret123!")

    # Unauthenticated request should fail
    res = client.get("/api/admin/metrics")
    assert res.status_code == 403

    # Pupil should be denied
    login(client, "pupil.one", "Secret123!")
    res = client.get("/api/admin/metrics")
    assert res.status_code == 403

    # Teacher should be denied
    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/admin/metrics")
    assert res.status_code == 403

    # Admin should succeed
    login(client, "admin.one", "Secret123!")
    res = client.get("/api/admin/metrics")
    assert res.status_code == 200


def test_admin_metrics_returns_valid_structure(client, db_session):
    """Ensure /api/admin/metrics returns expected response structure."""
    seed_user(db_session, "admin.one", role="admin", cohort_year=None, password="Secret123!")
    login(client, "admin.one", "Secret123!")

    res = client.get("/api/admin/metrics")
    assert res.status_code == 200
    data = res.json()

    # Check top-level keys
    assert "summary" in data
    assert "http" in data
    assert "authentication" in data
    assert "python_runner" in data
    assert "activity" in data
    assert "system" in data

    # Check summary section
    summary = data["summary"]
    assert "total_users" in summary
    assert "active_users" in summary
    assert "total_pupils" in summary
    assert "total_teachers" in summary
    assert "total_admins" in summary
    assert "active_sessions" in summary
    assert "recent_logins_7d" in summary

    # Check system section has db_connections
    system = data["system"]
    assert "db_connections" in system
    assert "total_errors" in system


def test_admin_metrics_db_connections_is_valid(client, db_session):
    """Ensure db_connections is a non-negative integer (the fix for always showing 0)."""
    seed_user(db_session, "admin.one", role="admin", cohort_year=None, password="Secret123!")
    login(client, "admin.one", "Secret123!")

    res = client.get("/api/admin/metrics")
    assert res.status_code == 200
    data = res.json()

    db_connections = data["system"]["db_connections"]
    assert isinstance(db_connections, int)
    assert db_connections >= 0


def test_metrics_requires_admin(client, db_session):
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")
    seed_user(db_session, "admin.one", role="admin", cohort_year=None, password="Secret123!")

    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/metrics")
    assert res.status_code == 403

    login(client, "admin.one", "Secret123!")
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "users_active" in data
    assert "activity_states" in data


def test_audit_log_create_user(client, db_session):
    seed_user(db_session, "admin.one", role="admin", cohort_year=None, password="Secret123!")

    csrf = login(client, "admin.one", "Secret123!")
    res = client.post(
        "/api/admin/users",
        json={
            "username": "teacher.two",
            "name": "Teacher Two",
            "role": "teacher",
            "cohort_year": "",
            "password": "Secret123!",
            "teacher_notes": "",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    audit = client.get("/api/admin/audit?action=create_user")
    assert audit.status_code == 200
    items = audit.json().get("items", [])
    assert any(item.get("action") == "create_user" for item in items)


def test_retention_purge_deletes_old_pupil(app, db_session):
    from backend.app import retention

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=365 * 3)

    teacher = seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")
    user = seed_user(db_session, "pupil.old", role="pupil", cohort_year="2022", password="Secret123!")
    user.created_at = old_time
    user.last_login_at = old_time
    db_session.add(user)
    db_session.commit()

    state = ActivityState(
        user_id=user.id,
        lesson_id="lesson-1",
        activity_id="a01",
        state={"answer": "old"},
        created_at=old_time,
        updated_at=old_time,
    )
    db_session.add(state)
    db_session.flush()

    revision = ActivityRevision(
        activity_state_id=state.id,
        user_id=user.id,
        lesson_id="lesson-1",
        activity_id="a01",
        state={"answer": "old"},
        created_at=old_time,
    )
    mark = ActivityMark(
        user_id=user.id,
        lesson_id="lesson-1",
        activity_id="a01",
        status="complete",
        created_at=old_time,
        updated_at=old_time,
    )
    feedback = ActivityFeedback(
        user_id=user.id,
        lesson_id="lesson-1",
        activity_id="a01",
        feedback_text="Good work!",
        teacher_id=teacher.id,
        created_at=old_time,
        updated_at=old_time,
    )
    session = AuthSession(
        id="sess-old",
        user_id=user.id,
        csrf_token="csrf-old",
        created_at=old_time,
        expires_at=old_time + timedelta(hours=1),
    )
    audit = AuditLog(
        actor_user_id=None,
        target_user_id=user.id,
        action="mark_activity",
        created_at=old_time,
    )
    db_session.add_all([revision, mark, feedback, session, audit])
    db_session.commit()

    cutoff = retention.retention_cutoff(years=2, now=now)
    targets = retention.collect_retention_targets(db_session, cutoff)
    target_ids = [item["user"].id for item in targets]
    assert user.id in target_ids

    counts = retention.purge_users(db_session, target_ids)
    assert counts["users"] == 1
    assert db_session.query(User).count() == 1  # Teacher remains
    assert db_session.query(ActivityState).count() == 0
    assert db_session.query(ActivityRevision).count() == 0
    assert db_session.query(ActivityMark).count() == 0
    assert db_session.query(ActivityFeedback).count() == 0
    assert db_session.query(AuthSession).count() == 0
    assert db_session.query(AuditLog).count() == 0
