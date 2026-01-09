from backend.app.models import User
from backend.app.security import hash_password


def seed_user(db, username, role="pupil", cohort_year="2024", password="Pass123!"):
    user = User(
        username=username,
        name=f"{username} User",
        role=role,
        cohort_year=cohort_year if role == "pupil" else None,
        teacher_notes=None,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    return user


def login(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    return me.json()["csrf_token"]
