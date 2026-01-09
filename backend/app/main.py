import csv
import io
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import CSRF_HEADER_NAME, SESSION_COOKIE_NAME, SESSION_TTL_MINUTES
from .db import SessionLocal, engine, get_db
from .models import Base, Session as AuthSession, User
from .rate_limit import LoginLimiter, compute_lock_seconds
from .security import hash_password, verify_password

app = FastAPI(
    title="Thinking like a Coder API",
    version="0.1.0",
)

login_limiter = LoginLimiter()


def utcnow():
    return datetime.now(timezone.utc)


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def valid_username(username: str) -> bool:
    return bool(re.match(r"^[a-z0-9._-]+$", username))


def valid_pupil_username(username: str) -> bool:
    return bool(re.match(r"^[a-z][a-z\-']*\.[a-z]$", username))


def user_public(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "cohort_year": user.cohort_year,
    }


def create_session(db: Session, user: User, request: Request) -> AuthSession:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = utcnow()
    expires = now + timedelta(minutes=SESSION_TTL_MINUTES)
    session = AuthSession(
        id=token,
        user_id=user.id,
        csrf_token=csrf,
        created_at=now,
        expires_at=expires,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    db.commit()
    return session


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_TTL_MINUTES * 60,
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        "",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=0,
        path="/",
    )


def csrf_guard(request: Request) -> None:
    session = request.state.session
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    token = request.headers.get(CSRF_HEADER_NAME)
    if not token or token != session.csrf_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token.")


def forbidden_page() -> HTMLResponse:
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Access denied</title>
  <link rel="stylesheet" href="/core/app.css" />
</head>
<body>
  <div class="container" style="margin-top:32px">
    <div class="card">
      <h1>Access denied</h1>
      <p>You do not have permission to view this page.</p>
      <div class="row" style="margin-top:12px">
        <a class="btn" href="/index.html">Go to student hub</a>
      </div>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html, status_code=403)


def is_public_path(path: str) -> bool:
    if path in {"/login.html", "/favicon.ico"}:
        return True
    if path.startswith("/core/"):
        return True
    if path == "/lessons/manifest.json":
        return True
    return False


def is_teacher_path(path: str) -> bool:
    if path == "/teacher.html" or "/teacher/" in path:
        return True
    if re.match(r"^/lessons/lesson-\d+/?$", path):
        return True
    if re.match(r"^/lessons/lesson-\d+/index\.html$", path):
        return True
    return False


def is_admin_path(path: str) -> bool:
    return path == "/admin.html"


def is_student_path(path: str) -> bool:
    if path in {"/", "/index.html"}:
        return True
    if path.startswith("/lessons/"):
        return True
    return False


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    db = SessionLocal()
    try:
        user = None
        session = None
        token = request.cookies.get(SESSION_COOKIE_NAME)
        if token:
            session = db.get(AuthSession, token)
            if session and session.expires_at <= utcnow():
                db.delete(session)
                db.commit()
                session = None
            if session:
                user = db.get(User, session.user_id)
                if user and not user.active:
                    user = None

        request.state.user = user
        request.state.session = session

        if path.startswith("/api/"):
            return await call_next(request)

        if is_public_path(path):
            return await call_next(request)

        if not user:
            return RedirectResponse(f"/login.html?next={quote(path)}")

        if is_admin_path(path) and user.role != "admin":
            return forbidden_page()

        if is_teacher_path(path) and user.role not in {"teacher", "admin"}:
            return forbidden_page()

        if is_student_path(path):
            return await call_next(request)

        return await call_next(request)
    finally:
        db.close()


@app.on_event("startup")
def startup():
    last_err = None
    for _ in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:  # pragma: no cover - startup resilience
            last_err = exc
            time.sleep(1)
    if last_err:
        raise last_err


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/me")
def auth_me(request: Request):
    user = request.state.user
    session = request.state.session
    if not user or not session:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {
        "user": user_public(user),
        "csrf_token": session.csrf_token,
    }


@app.post("/api/auth/login")
def login(request: Request, payload: dict, db: Session = Depends(get_db)):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    username = normalize_username(payload.get("username", ""))
    password = payload.get("password", "")
    ip_key = f"{request.client.host if request.client else 'unknown'}:{username}"

    if login_limiter.check(ip_key) > 0:
        raise HTTPException(status_code=429, detail="Too many attempts. Try again shortly.")

    user = db.query(User).filter(User.username == username).first()
    if user and user.locked_until and user.locked_until > utcnow():
        raise HTTPException(status_code=429, detail="Too many attempts. Try again shortly.")

    if not user or not verify_password(user.password_hash, password):
        if user:
            user.failed_login_count += 1
            lock_seconds = compute_lock_seconds(user.failed_login_count)
            if lock_seconds:
                user.locked_until = utcnow() + timedelta(seconds=lock_seconds)
            db.commit()
        else:
            login_limiter.record_failure(ip_key)
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if not user.active:
        raise HTTPException(status_code=403, detail="Account disabled.")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    db.commit()

    session = create_session(db, user, request)
    response = JSONResponse({"ok": True, "user": user_public(user)})
    set_session_cookie(response, session.id)
    login_limiter.reset(ip_key)
    return response


@app.post("/api/auth/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    csrf_guard(request)
    session = request.state.session
    if session:
        db_session = db.get(AuthSession, session.id)
        if db_session:
            db.delete(db_session)
            db.commit()
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@app.post("/api/admin/bootstrap")
def bootstrap_admin(payload: dict, db: Session = Depends(get_db)):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    admin_exists = db.query(User).filter(User.role == "admin").first()
    if admin_exists:
        raise HTTPException(status_code=403, detail="Admin already exists.")

    username = normalize_username(payload.get("username", ""))
    name = (payload.get("name", "") or "").strip()
    password = payload.get("password", "")

    if not username or not name or not password:
        raise HTTPException(status_code=400, detail="Missing required fields.")
    if not valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format.")

    user = User(
        username=username,
        name=name,
        role="admin",
        password_hash=hash_password(password),
        cohort_year=None,
        teacher_notes=None,
    )
    db.add(user)
    db.commit()
    return {"ok": True, "user": user_public(user)}


@app.post("/api/admin/users")
def create_user(request: Request, payload: dict, db: Session = Depends(get_db)):
    csrf_guard(request)
    user = request.state.user
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")

    username = normalize_username(payload.get("username", ""))
    name = (payload.get("name", "") or "").strip()
    role = (payload.get("role", "pupil") or "pupil").strip().lower()
    cohort_year = (payload.get("cohort_year", "") or "").strip() or None
    teacher_notes = (payload.get("teacher_notes", "") or "").strip() or None
    password = payload.get("password", "")

    if role not in {"pupil", "teacher", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if not username or not name or not password:
        raise HTTPException(status_code=400, detail="Missing required fields.")
    if not valid_username(username):
        raise HTTPException(status_code=400, detail="Invalid username format.")
    if role == "pupil" and not valid_pupil_username(username):
        raise HTTPException(status_code=400, detail="Pupil username must be lastname.firstinitial.")
    if role == "pupil" and not cohort_year:
        raise HTTPException(status_code=400, detail="Cohort/year is required for pupils.")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists.")

    new_user = User(
        username=username,
        name=name,
        role=role,
        cohort_year=cohort_year,
        teacher_notes=teacher_notes,
        password_hash=hash_password(password),
    )
    db.add(new_user)
    db.commit()
    return {"ok": True, "user": user_public(new_user)}


@app.post("/api/admin/users/import")
def import_users(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    csrf_guard(request)
    user = request.state.user
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required.")

    raw = file.file.read()
    text = raw.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV header missing.")

    rows = []
    for row in reader:
        cleaned = {}
        for k, v in row.items():
            key = (k or "").strip().lower()
            cleaned[key] = (v or "").strip()
        rows.append(cleaned)

    existing = {u.username for u in db.query(User.username).all()}
    created = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        username = normalize_username(row.get("username", ""))
        name = row.get("name", "")
        role = (row.get("role", "pupil") or "pupil").lower()
        cohort_year = row.get("cohort_year") or None
        password = row.get("password", "")
        teacher_notes = row.get("teacher_notes") or None

        if not username or not name or not password:
            errors.append({"row": idx, "error": "Missing username, name, or password."})
            continue
        if role not in {"pupil", "teacher", "admin"}:
            errors.append({"row": idx, "error": "Invalid role."})
            continue
        if not valid_username(username):
            errors.append({"row": idx, "error": "Invalid username format."})
            continue
        if role == "pupil" and not valid_pupil_username(username):
            errors.append({"row": idx, "error": "Pupil username must be lastname.firstinitial."})
            continue
        if role == "pupil" and not cohort_year:
            errors.append({"row": idx, "error": "Cohort/year is required for pupils."})
            continue
        if username in existing:
            errors.append({"row": idx, "error": "Username already exists."})
            continue

        new_user = User(
            username=username,
            name=name,
            role=role,
            cohort_year=cohort_year,
            teacher_notes=teacher_notes,
            password_hash=hash_password(password),
        )
        db.add(new_user)
        existing.add(username)
        created += 1

    if errors:
        db.rollback()
        return {"created": 0, "errors": errors}

    db.commit()
    return {"created": created, "errors": []}


app.mount("/", StaticFiles(directory="/srv", html=True), name="static")
