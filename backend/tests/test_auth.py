from backend.tests.utils import login, seed_user


def test_login_logout_flow(client, db_session):
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")

    csrf = login(client, "teacher.one", "Secret123!")
    res = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200

    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_teacher_endpoints_require_role(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    login(client, "pupil.one", "Secret123!")

    res = client.get("/api/teacher/overview")
    assert res.status_code == 403


def test_teacher_pages_blocked_for_pupils(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    login(client, "pupil.one", "Secret123!")

    res = client.get("/teacher.html", follow_redirects=False)
    assert res.status_code == 403


def test_admin_pages_blocked_for_teachers(client, db_session):
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")
    login(client, "teacher.one", "Secret123!")

    res = client.get("/admin.html", follow_redirects=False)
    assert res.status_code == 403
