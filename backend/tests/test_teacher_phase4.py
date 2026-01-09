from backend.tests.utils import login, seed_user


def test_marking_and_overview(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    csrf = login(client, "teacher.one", "Secret123!")
    res = client.post(
        "/api/teacher/mark",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "status": "complete",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    res = client.get("/api/teacher/overview")
    assert res.status_code == 200
    data = res.json()
    completion = data["completion"]["pupil.one"]["lesson-1"]
    assert completion["completed"] == 1
    assert completion["total"] >= 1

    res = client.post(
        "/api/teacher/mark",
        json={
            "username": "pupil.one",
            "lesson_id": "lesson-1",
            "activity_id": "a01",
            "status": "incomplete",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    res = client.get("/api/teacher/pupil/pupil.one/lesson/lesson-1")
    assert res.status_code == 200
    marks = res.json()["marks"]
    assert marks[0]["status"] == "incomplete"


def test_pupil_lesson_detail_and_notes(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    csrf = login(client, "teacher.one", "Secret123!")
    res = client.post(
        "/api/teacher/pupil/pupil.one/notes",
        json={"teacher_notes": "Needs support with decomposition."},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    res = client.get("/api/teacher/pupil/pupil.one/lesson/lesson-1")
    assert res.status_code == 200
    data = res.json()
    assert data["teacher_notes"] == "Needs support with decomposition."


def test_csv_exports(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/teacher/export/lesson/lesson-1")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "username" in res.text
    assert "pupil.one" in res.text

    res = client.get("/api/teacher/export/pupil/pupil.one")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "lesson_id" in res.text


def test_cohort_filters(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    seed_user(db_session, "pupil.two", role="pupil", cohort_year="2025", password="Secret123!")
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    login(client, "teacher.one", "Secret123!")
    res = client.get("/api/teacher/users?cohort_year=2024")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "pupil.one"

    res = client.get("/api/teacher/overview?cohort_year=2025")
    assert res.status_code == 200
    data = res.json()
    pupils = [p["username"] for p in data["pupils"]]
    assert pupils == ["pupil.two"]
