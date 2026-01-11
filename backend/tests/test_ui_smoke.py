from backend.tests.utils import login, seed_user


def test_static_css_public(client):
    res = client.get("/core/app.css")
    assert res.status_code == 200
    assert "--maxw" in res.text


def test_login_page_renders(client):
    res = client.get("/login.html")
    assert res.status_code == 200
    assert "<h1>Sign in</h1>" in res.text
    assert 'id="loginForm"' in res.text


def test_student_hub_requires_login(client):
    res = client.get("/index.html", follow_redirects=False)
    assert res.status_code in {302, 307}
    assert res.headers["location"].startswith("/login.html?next=/index.html")


def test_student_hub_renders_for_pupil(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    login(client, "pupil.one", "Secret123!")
    res = client.get("/index.html")
    assert res.status_code == 200
    assert "<h1>Student hub</h1>" in res.text
    assert 'id="catalog"' in res.text


def test_teacher_hub_renders_for_teacher(client, db_session):
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")
    login(client, "teacher.one", "Secret123!")
    res = client.get("/teacher.html")
    assert res.status_code == 200
    assert "<h1>Teacher hub</h1>" in res.text
    assert 'data-requires-role="teacher"' in res.text


def test_admin_hub_renders_for_admin(client, db_session):
    seed_user(db_session, "admin.one", role="admin", cohort_year=None, password="Secret123!")
    login(client, "admin.one", "Secret123!")
    res = client.get("/admin.html")
    assert res.status_code == 200
    assert "<h1>Admin tools</h1>" in res.text
    assert 'data-requires-role="admin"' in res.text
