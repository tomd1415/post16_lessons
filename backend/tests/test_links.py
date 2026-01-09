from backend.tests.utils import login, seed_user


def test_links_require_teacher(client, db_session):
    seed_user(db_session, "pupil.one", role="pupil", cohort_year="2024", password="Secret123!")
    login(client, "pupil.one", "Secret123!")

    res = client.get("/api/teacher/links")
    assert res.status_code == 403


def test_teacher_can_update_link_override(client, db_session):
    seed_user(db_session, "teacher.one", role="teacher", cohort_year=None, password="Secret123!")
    csrf = login(client, "teacher.one", "Secret123!")

    res = client.get("/api/teacher/links")
    assert res.status_code == 200
    items = res.json()["items"]
    assert items
    link_id = items[0]["id"]

    res = client.post(
        f"/api/teacher/links/{link_id}",
        json={
            "replacement_url": "https://example.com/replacement",
            "local_path": "/srv/lessons/offline/example.html",
            "disabled": False,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200

    res = client.get("/api/teacher/links")
    assert res.status_code == 200
    items = {item["id"]: item for item in res.json()["items"]}
    assert items[link_id]["replacement_url"] == "https://example.com/replacement"
    assert items[link_id]["local_path"] == "/srv/lessons/offline/example.html"
