"""Tests for enhanced teacher features: answer marking, feedback, and activity detail."""

from backend.app.models import ActivityFeedback, ActivityMark, ActivityState, User
from backend.tests.utils import login, seed_user


def test_get_pupil_activity_detail_requires_teacher(client, db_session):
    """Ensure pupil activity detail endpoint requires teacher role."""
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    # Unauthenticated
    res = client.get("/api/teacher/pupil/pupil.one/activity/lesson-1/a01")
    assert res.status_code == 403

    # Pupil
    login(client, "pupil.one", "Secret123!")
    res = client.get("/api/teacher/pupil/pupil.one/activity/lesson-1/a01")
    assert res.status_code == 403

    # Teacher
    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/teacher/pupil/pupil.one/activity/lesson-1/a01")
    assert res.status_code == 200
    data = res.json()
    assert "pupil" in data
    assert "state" in data
    assert "mark" in data
    assert "feedback" in data


def test_get_pupil_activity_detail_returns_data(client, db_session):
    """Ensure pupil activity detail returns complete data."""
    pupil = seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    # Create activity state
    state = ActivityState(
        user_id=pupil.id,
        lesson_id="lesson-1",
        activity_id="a01",
        state={"answer": "test answer"},
    )
    db_session.add(state)
    db_session.commit()

    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/teacher/pupil/pupil.one/activity/lesson-1/a01")
    assert res.status_code == 200
    data = res.json()

    assert data["pupil"]["username"] == "pupil.one"
    assert data["state"]["state"]["answer"] == "test answer"


def test_answer_mark_requires_teacher(client, db_session):
    """Ensure answer marking requires teacher role."""
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    # Pupil cannot mark
    csrf = login(client, "pupil.one", "Secret123!")
    res = client.post(
        "/api/teacher/answer-mark",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "question_id": "q1",
            "correct": True,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 403


def test_answer_mark_creates_and_updates_mark(client, db_session):
    """Ensure answer marking creates and updates ActivityMark records."""
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    csrf = login(client, "teacher.one", "Secret123!")

    # Mark first answer as correct
    res = client.post(
        "/api/teacher/answer-mark",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "question_id": "q1",
            "correct": True,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["mark"]["answer_marks"]["q1"]["correct"] is True
    assert data["mark"]["score"] == 1
    assert data["mark"]["max_score"] == 1

    # Mark second answer as incorrect
    res = client.post(
        "/api/teacher/answer-mark",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "question_id": "q2",
            "correct": False,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mark"]["answer_marks"]["q2"]["correct"] is False
    assert data["mark"]["score"] == 1
    assert data["mark"]["max_score"] == 2


def test_teacher_feedback_create_and_retrieve(client, db_session):
    """Ensure teachers can create feedback and pupils can retrieve it."""
    pupil = seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    # Teacher creates feedback
    csrf = login(client, "teacher.one", "Secret123!")
    res = client.post(
        "/api/teacher/feedback",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "feedback_text": "Great work on this activity!",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "feedback" in data

    # Pupil retrieves feedback
    login(client, "pupil.one", "Secret123!")
    res = client.get("/api/pupil/feedback/lesson-1")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["feedback_text"] == "Great work on this activity!"
    assert data["items"][0]["activity_id"] == "a01"


def test_teacher_feedback_update(client, db_session):
    """Ensure teachers can update existing feedback."""
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    csrf = login(client, "teacher.one", "Secret123!")

    # Create feedback
    res = client.post(
        "/api/teacher/feedback",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "feedback_text": "Initial feedback",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    # Update feedback
    res = client.post(
        "/api/teacher/feedback",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "feedback_text": "Updated feedback",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    # Verify only one feedback exists with updated text
    login(client, "pupil.one", "Secret123!")
    res = client.get("/api/pupil/feedback/lesson-1")
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["feedback_text"] == "Updated feedback"


def test_teacher_feedback_delete(client, db_session):
    """Ensure teachers can delete feedback."""
    pupil = seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    teacher = seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    # Create feedback directly
    feedback = ActivityFeedback(
        user_id=pupil.id,
        lesson_id="lesson-1",
        activity_id="a01",
        feedback_text="Test feedback",
        teacher_id=teacher.id,
    )
    db_session.add(feedback)
    db_session.commit()
    feedback_id = str(feedback.id)

    csrf = login(client, "teacher.one", "Secret123!")
    res = client.delete(
        f"/api/teacher/feedback/{feedback_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    # Verify feedback is deleted
    assert db_session.query(ActivityFeedback).count() == 0


def test_pupil_feedback_requires_auth(client, db_session):
    """Ensure pupil feedback endpoint requires authentication."""
    res = client.get("/api/pupil/feedback/lesson-1")
    assert res.status_code == 401


def test_hybrid_automark_on_save(client, db_session):
    """Ensure saving activity state creates an in_progress mark."""
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")

    csrf = login(client, "pupil.one", "Secret123!")

    # Save activity state
    res = client.post(
        "/api/activity/state/lesson-1/a01",
        json={"state": {"answer": "test"}},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    # Verify mark was created
    mark = db_session.query(ActivityMark).filter(
        ActivityMark.lesson_id == "lesson-1",
        ActivityMark.activity_id == "a01",
    ).first()
    assert mark is not None
    assert mark.status == "in_progress"
    assert mark.attempt_count == 1
    assert mark.first_save_at is not None


def test_teacher_overview_counts_in_progress(client, db_session):
    """Ensure teacher overview includes in_progress marks in completion count."""
    pupil = seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    # Create an in_progress mark
    mark = ActivityMark(
        user_id=pupil.id,
        lesson_id="lesson-1",
        activity_id="a01",
        status="in_progress",
    )
    db_session.add(mark)
    db_session.commit()

    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/teacher/overview")
    assert res.status_code == 200
    data = res.json()

    # Find completion for pupil.one on lesson-1
    completion = data.get("completion", {}).get("pupil.one", {}).get("lesson-1", {})
    assert completion.get("completed", 0) >= 1
