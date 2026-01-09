from backend.tests.utils import login, seed_user


def test_activity_state_save_and_load(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    csrf = login(client, "pupil.one", "Secret123!")

    payload = {"state": {"answer": 42}, "client_saved_at": "2025-01-01T00:00:00Z"}
    res = client.post("/api/activity/state/lesson-1/a01", json=payload, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200

    res = client.get("/api/activity/state/lesson-1/a01")
    assert res.status_code == 200
    data = res.json()
    assert data["lesson_id"] == "lesson-1"
    assert data["activity_id"] == "a01"
    assert data["state"] == {"answer": 42}

    res = client.get("/api/activity/state")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1


def test_teacher_can_view_revisions(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    csrf = login(client, "pupil.one", "Secret123!")
    client.post(
        "/api/activity/state/lesson-1/a01",
        json={"state": {"draft": True}, "client_saved_at": "2025-01-01T00:00:00Z"},
        headers={"X-CSRF-Token": csrf},
    )

    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/teacher/revisions?username=pupil.one&lesson_id=lesson-1&activity_id=a01")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["lesson_id"] == "lesson-1"
