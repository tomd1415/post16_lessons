from datetime import datetime, timedelta, timezone

from backend.app.models import ActivityMark, ActivityRevision
from backend.tests.utils import login, seed_user


def test_teacher_stats_requires_teacher(client, db_session):
    seed_user(db_session, "pupil.stats", role="pupil", cohort_year="2024", password="Secret123!")
    login(client, "pupil.stats", "Secret123!")
    res = client.get("/api/teacher/stats")
    assert res.status_code == 403


def test_teacher_stats_counts_completion_and_timing(client, db_session):
    seed_user(db_session, "teacher.stats", role="teacher", cohort_year=None, password="Secret123!")
    pupil1 = seed_user(db_session, "pupil.stats1", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "pupil.stats2", role="pupil", cohort_year="2024", password="Secret123!")
    csrf = login(client, "teacher.stats", "Secret123!")

    mark = ActivityMark(
        user_id=pupil1.id,
        lesson_id="lesson-1",
        activity_id="a01",
        status="complete",
    )
    db_session.add(mark)

    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = t1 + timedelta(minutes=3)
    db_session.add(
        ActivityRevision(
            activity_state_id=None,
            user_id=pupil1.id,
            lesson_id="lesson-1",
            activity_id="a01",
            state={},
            created_at=t1,
            client_saved_at=t1,
        )
    )
    db_session.add(
        ActivityRevision(
            activity_state_id=None,
            user_id=pupil1.id,
            lesson_id="lesson-1",
            activity_id="a01",
            state={},
            created_at=t2,
            client_saved_at=t2,
        )
    )
    db_session.commit()

    res = client.get("/api/teacher/stats?cohort_year=2024&lesson_id=lesson-1", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    data = res.json()

    lesson_stats = data["lesson_stats"]["lesson-1"]
    assert lesson_stats["total_pupils"] == 2
    assert lesson_stats["completed_pupils"] == 0

    activity_stats = data["activity_stats"]["lesson-1"]["a01"]
    assert activity_stats["completed"] == 1
    assert activity_stats["total"] == 2
    assert activity_stats["completion_rate"] == 0.5

    timing = data["timing"]["activities"]["lesson-1"]["a01"]
    assert timing["samples"] == 1
    assert timing["avg_minutes"] == 3.0


def test_teacher_attention_flags_stuck_and_many_revisions(client, db_session):
    from backend.app import config

    seed_user(db_session, "teacher.attention", role="teacher", cohort_year=None, password="Secret123!")
    pupil = seed_user(db_session, "pupil.attention", role="pupil", cohort_year="2024", password="Secret123!")
    csrf = login(client, "teacher.attention", "Secret123!")

    old = datetime.now(timezone.utc) - timedelta(days=config.ATTENTION_STUCK_DAYS + 2)
    for idx in range(config.ATTENTION_REVISION_THRESHOLD):
        stamp = old + timedelta(minutes=idx)
        db_session.add(
            ActivityRevision(
                activity_state_id=None,
                user_id=pupil.id,
                lesson_id="lesson-1",
                activity_id="a01",
                state={},
                created_at=stamp,
                client_saved_at=stamp,
            )
        )
    db_session.commit()

    res = client.get(
        "/api/teacher/attention?cohort_year=2024&lesson_id=lesson-1",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert items
    item = items[0]
    assert item["activity_id"] == "a01"
    assert "not_completed" in item["reasons"]
    assert "many_revisions" in item["reasons"]
    assert "stuck" in item["reasons"]
