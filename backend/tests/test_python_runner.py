from backend.tests.utils import login, seed_user


def test_python_run_requires_auth(client):
    res = client.post(
        "/api/python/run",
        json={"lesson_id": "lesson-4", "activity_id": "a02", "code": "print('hi')"},
    )
    assert res.status_code == 401


def test_python_run_requires_code(client, db_session):
    seed_user(db_session, "pupil.runner")
    csrf = login(client, "pupil.runner", "Pass123!")
    res = client.post(
        "/api/python/run",
        json={"lesson_id": "lesson-4", "activity_id": "a02", "code": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 400


def test_python_run_happy_path(client, db_session, monkeypatch):
    seed_user(db_session, "pupil.runner2")
    csrf = login(client, "pupil.runner2", "Pass123!")

    def fake_run(code, files):
        return {
            "stdout": "Hello",
            "stderr": "",
            "exit_code": 0,
            "timed_out": False,
            "duration_ms": 5,
            "files": [],
        }

    monkeypatch.setattr("backend.app.main.run_python", fake_run)
    res = client.post(
        "/api/python/run",
        json={"lesson_id": "lesson-4", "activity_id": "a02", "code": "print('Hello')"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["stdout"] == "Hello"


def test_python_diagnostics_requires_teacher(client, db_session):
    seed_user(db_session, "pupil.diagnostics")
    login(client, "pupil.diagnostics", "Pass123!")
    res = client.get("/api/python/diagnostics")
    assert res.status_code == 403


def test_python_diagnostics_teacher_access(client, db_session):
    seed_user(db_session, "teacher.diagnostics", role="teacher")
    login(client, "teacher.diagnostics", "Pass123!")
    res = client.get("/api/python/diagnostics")
    assert res.status_code == 200
    data = res.json()
    assert "runner_enabled" in data
