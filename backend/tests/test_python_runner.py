import base64

import pytest
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


def test_runner_exec_command_uses_inline_code():
    from backend.app import python_runner

    code = "print('hello')"
    cmd, env = python_runner._build_exec_command(code)
    assert len(cmd) >= 7
    assert cmd[4] == "python"
    assert cmd[5] == "-c"
    assert all(token != "/tmp/main.py" for token in cmd)
    assert "/tmp/main.py" in cmd[6]
    assert "os.chdir('/tmp')" in cmd[6]
    assert "os.walk" in cmd[6]
    assert "shutil.copy2" in cmd[6]
    decoded = base64.b64decode(env["TLAC_CODE_B64"]).decode("utf-8")
    assert decoded == code


def test_sanitize_files_rejects_absolute_path():
    from backend.app import python_runner

    with pytest.raises(ValueError):
        python_runner._sanitize_files([{"path": "/etc/passwd", "content": "x"}])


def test_sanitize_files_rejects_parent_path():
    from backend.app import python_runner

    with pytest.raises(ValueError):
        python_runner._sanitize_files([{"path": "../notes.txt", "content": "x"}])


def test_sanitize_files_allows_simple_path():
    from backend.app import python_runner

    files = python_runner._sanitize_files([{"path": "notes.txt", "content": "hi"}])
    assert files[0]["path"] == "notes.txt"
