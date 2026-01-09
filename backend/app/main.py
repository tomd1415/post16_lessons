import asyncio
import csv
import io
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import (
    CSRF_HEADER_NAME,
    LINK_OVERRIDES_PATH,
    RUNNER_CONCURRENCY,
    SESSION_COOKIE_NAME,
    SESSION_TTL_MINUTES,
)
from .db import SessionLocal, engine, get_db
from .models import ActivityMark, ActivityRevision, ActivityState, Base, Session as AuthSession, User
from .python_runner import RunnerError, RunnerUnavailable, run_python, runner_diagnostics
from .rate_limit import LoginLimiter, compute_lock_seconds
from .security import hash_password, verify_password

app = FastAPI(
    title="Thinking like a Coder API",
    version="0.1.0",
)

login_limiter = LoginLimiter()
runner_semaphore = asyncio.Semaphore(RUNNER_CONCURRENCY)
MANIFEST_PATH = os.getenv("LESSON_MANIFEST_PATH", "/srv/lessons/manifest.json")
_manifest_cache = None
_manifest_mtime = None
_link_overrides_cache = None
_link_overrides_mtime = None


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


def activity_state_public(state: ActivityState) -> dict:
    return {
        "lesson_id": state.lesson_id,
        "activity_id": state.activity_id,
        "state": state.state,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        "last_client_at": state.last_client_at.isoformat() if state.last_client_at else None,
    }


def activity_revision_public(rev: ActivityRevision) -> dict:
    return {
        "id": str(rev.id),
        "lesson_id": rev.lesson_id,
        "activity_id": rev.activity_id,
        "state": rev.state,
        "created_at": rev.created_at.isoformat() if rev.created_at else None,
        "client_saved_at": rev.client_saved_at.isoformat() if rev.client_saved_at else None,
    }


def activity_mark_public(mark: ActivityMark) -> dict:
    return {
        "lesson_id": mark.lesson_id,
        "activity_id": mark.activity_id,
        "status": mark.status,
        "updated_at": mark.updated_at.isoformat() if mark.updated_at else None,
    }


def valid_lesson_id(lesson_id: str) -> bool:
    return bool(re.match(r"^lesson-\d+$", lesson_id))


def valid_activity_id(activity_id: str) -> bool:
    return bool(re.match(r"^a\d+$", activity_id))


def parse_client_time(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def load_manifest():
    global _manifest_cache, _manifest_mtime
    try:
        mtime = os.path.getmtime(MANIFEST_PATH)
    except OSError:
        return None
    if _manifest_cache is not None and _manifest_mtime == mtime:
        return _manifest_cache
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as handle:
            _manifest_cache = json.load(handle)
            _manifest_mtime = mtime
            return _manifest_cache
    except Exception:
        return None


def load_link_overrides():
    global _link_overrides_cache, _link_overrides_mtime
    path = Path(LINK_OVERRIDES_PATH)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        _link_overrides_cache = {}
        _link_overrides_mtime = None
        return {}
    except OSError:
        return {}
    if _link_overrides_cache is not None and _link_overrides_mtime == mtime:
        return _link_overrides_cache
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            data = {}
        _link_overrides_cache = data
        _link_overrides_mtime = mtime
        return data
    except Exception:
        return {}


def save_link_overrides(overrides: dict) -> None:
    path = Path(LINK_OVERRIDES_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(overrides, indent=2))
    tmp_path.replace(path)
    global _link_overrides_cache, _link_overrides_mtime
    _link_overrides_cache = overrides
    _link_overrides_mtime = path.stat().st_mtime


def lesson_index(manifest):
    lessons = (manifest or {}).get("lessons") or []
    return {lesson.get("id"): lesson for lesson in lessons if lesson.get("id")}


def lesson_activity_map(lesson):
    return {activity.get("id"): activity for activity in (lesson or {}).get("activities") or []}


def objective_texts_for_activity(lesson, activity):
    objective_lookup = {obj.get("id"): obj.get("text") for obj in (lesson or {}).get("objectives") or []}
    ids = (activity or {}).get("objectiveIds") or []
    return [objective_lookup.get(obj_id, obj_id) for obj_id in ids]


def link_item_public(item: dict, override: dict | None) -> dict:
    override = override or {}
    replacement_url = (override.get("replacement_url") or item.get("replacementUrl") or "").strip()
    local_path = (override.get("local_path") or item.get("localPath") or "").strip()
    disabled = bool(override.get("disabled") or item.get("disabled"))
    effective_url = ""
    if not disabled:
        effective_url = local_path or replacement_url or item.get("url") or ""
    return {
        "id": item.get("id"),
        "lesson_id": item.get("lessonId"),
        "title": item.get("title"),
        "url": item.get("url"),
        "section": item.get("section"),
        "status": item.get("status"),
        "last_checked": item.get("lastChecked"),
        "replacement_url": replacement_url,
        "local_path": local_path,
        "disabled": disabled,
        "effective_url": effective_url,
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


def require_teacher(request: Request) -> User:
    user = request.state.user
    if not user or user.role not in {"teacher", "admin"}:
        raise HTTPException(status_code=403, detail="Teacher or admin required.")
    return user


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
    if path.startswith("/teacher") or "/teacher/" in path:
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
            if session and session.expires_at:
                expires_at = session.expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at <= utcnow():
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


@app.get("/api/activity/state")
def list_activity_state(request: Request, db: Session = Depends(get_db)):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    rows = (
        db.query(ActivityState)
        .filter(ActivityState.user_id == user.id)
        .order_by(ActivityState.updated_at.desc())
        .all()
    )
    return {"items": [activity_state_public(row) for row in rows]}


@app.get("/api/activity/state/{lesson_id}/{activity_id}")
def get_activity_state(
    request: Request,
    lesson_id: str,
    activity_id: str,
    db: Session = Depends(get_db),
):
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not valid_lesson_id(lesson_id) or not valid_activity_id(activity_id):
        raise HTTPException(status_code=400, detail="Invalid lesson or activity id.")
    row = (
        db.query(ActivityState)
        .filter(
            ActivityState.user_id == user.id,
            ActivityState.lesson_id == lesson_id,
            ActivityState.activity_id == activity_id,
        )
        .first()
    )
    if not row:
        return {"state": None}
    return activity_state_public(row)


@app.post("/api/activity/state/{lesson_id}/{activity_id}")
def save_activity_state(
    request: Request,
    lesson_id: str,
    activity_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    csrf_guard(request)
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not valid_lesson_id(lesson_id) or not valid_activity_id(activity_id):
        raise HTTPException(status_code=400, detail="Invalid lesson or activity id.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    state = payload.get("state")
    if state is None:
        raise HTTPException(status_code=400, detail="Missing state.")

    client_saved_at = parse_client_time(payload.get("client_saved_at"))
    now = utcnow()

    row = (
        db.query(ActivityState)
        .filter(
            ActivityState.user_id == user.id,
            ActivityState.lesson_id == lesson_id,
            ActivityState.activity_id == activity_id,
        )
        .first()
    )
    if row:
        row.state = state
        row.last_client_at = client_saved_at
        row.updated_at = now
    else:
        row = ActivityState(
            user_id=user.id,
            lesson_id=lesson_id,
            activity_id=activity_id,
            state=state,
            last_client_at=client_saved_at,
        )
        db.add(row)
        db.flush()

    revision = ActivityRevision(
        activity_state_id=row.id,
        user_id=user.id,
        lesson_id=lesson_id,
        activity_id=activity_id,
        state=state,
        client_saved_at=client_saved_at,
        created_at=now,
    )
    db.add(revision)
    db.commit()
    return {
        "ok": True,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "revision_id": str(revision.id),
    }


@app.post("/api/python/run")
async def python_run(request: Request, payload: dict):
    csrf_guard(request)
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    lesson_id = payload.get("lesson_id", "")
    activity_id = payload.get("activity_id", "")
    code = payload.get("code", "")
    files = payload.get("files") or []
    if not valid_lesson_id(lesson_id) or not valid_activity_id(activity_id):
        raise HTTPException(status_code=400, detail="Invalid lesson or activity id.")
    if not isinstance(code, str) or not code.strip():
        raise HTTPException(status_code=400, detail="Code is required.")

    async with runner_semaphore:
        try:
            result = await asyncio.to_thread(run_python, code, files)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RunnerUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except RunnerError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"ok": True, **result}


@app.get("/api/python/diagnostics")
def python_diagnostics(request: Request):
    require_teacher(request)
    return runner_diagnostics()


@app.get("/api/teacher/users")
def list_pupils(
    request: Request,
    cohort_year: str = "",
    db: Session = Depends(get_db),
):
    require_teacher(request)
    query = db.query(User).filter(User.role == "pupil", User.active.is_(True))
    if cohort_year:
        query = query.filter(User.cohort_year == cohort_year)
    pupils = query.order_by(User.username.asc()).all()
    return {"items": [user_public(pupil) for pupil in pupils]}


@app.get("/api/teacher/revisions")
def teacher_revisions(
    request: Request,
    username: str,
    lesson_id: str = "",
    activity_id: str = "",
    limit: int = 50,
    db: Session = Depends(get_db),
):
    require_teacher(request)
    username = normalize_username(username)
    if not username:
        raise HTTPException(status_code=400, detail="Username is required.")
    if lesson_id and not valid_lesson_id(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson id.")
    if activity_id and not valid_activity_id(activity_id):
        raise HTTPException(status_code=400, detail="Invalid activity id.")

    pupil = db.query(User).filter(User.username == username).first()
    if not pupil:
        raise HTTPException(status_code=404, detail="Pupil not found.")

    limit = max(1, min(int(limit or 50), 200))
    query = db.query(ActivityRevision).filter(ActivityRevision.user_id == pupil.id)
    if lesson_id:
        query = query.filter(ActivityRevision.lesson_id == lesson_id)
    if activity_id:
        query = query.filter(ActivityRevision.activity_id == activity_id)
    revisions = query.order_by(ActivityRevision.created_at.desc()).limit(limit).all()
    return {"items": [activity_revision_public(rev) for rev in revisions]}


@app.get("/api/teacher/overview")
def teacher_overview(
    request: Request,
    cohort_year: str = "",
    db: Session = Depends(get_db),
):
    require_teacher(request)
    manifest = load_manifest() or {}
    lessons = (manifest.get("lessons") or []) if isinstance(manifest, dict) else []
    lessons_sorted = sorted(lessons, key=lambda l: l.get("number") or 0)
    totals = {lesson.get("id"): len(lesson.get("activities") or []) for lesson in lessons_sorted}

    query = db.query(User).filter(User.role == "pupil", User.active.is_(True))
    if cohort_year:
        query = query.filter(User.cohort_year == cohort_year)
    pupils = query.order_by(User.username.asc()).all()
    pupil_map = {pupil.id: pupil for pupil in pupils}
    completion = {
        pupil.username: {
            lesson.get("id"): {"completed": 0, "total": totals.get(lesson.get("id"), 0)}
            for lesson in lessons_sorted
        }
        for pupil in pupils
    }

    if pupils:
        marks = (
            db.query(ActivityMark)
            .filter(ActivityMark.user_id.in_(pupil_map.keys()), ActivityMark.status == "complete")
            .all()
        )
        for mark in marks:
            pupil = pupil_map.get(mark.user_id)
            if not pupil:
                continue
            lesson_id = mark.lesson_id
            if lesson_id not in totals:
                continue
            completion[pupil.username][lesson_id]["completed"] += 1

    return {
        "lessons": [
            {
                "id": lesson.get("id"),
                "number": lesson.get("number"),
                "title": lesson.get("title"),
                "total_activities": totals.get(lesson.get("id"), 0),
            }
            for lesson in lessons_sorted
        ],
        "pupils": [user_public(pupil) for pupil in pupils],
        "completion": completion,
    }


@app.get("/api/teacher/pupil/{username}/lesson/{lesson_id}")
def pupil_lesson_detail(
    request: Request,
    username: str,
    lesson_id: str,
    db: Session = Depends(get_db),
):
    require_teacher(request)
    username = normalize_username(username)
    if not username or not valid_lesson_id(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid username or lesson.")
    pupil = db.query(User).filter(User.username == username).first()
    if not pupil:
        raise HTTPException(status_code=404, detail="Pupil not found.")

    states = (
        db.query(ActivityState)
        .filter(ActivityState.user_id == pupil.id, ActivityState.lesson_id == lesson_id)
        .order_by(ActivityState.activity_id.asc())
        .all()
    )
    marks = (
        db.query(ActivityMark)
        .filter(ActivityMark.user_id == pupil.id, ActivityMark.lesson_id == lesson_id)
        .order_by(ActivityMark.activity_id.asc())
        .all()
    )

    return {
        "pupil": user_public(pupil),
        "teacher_notes": pupil.teacher_notes or "",
        "states": [activity_state_public(state) for state in states],
        "marks": [activity_mark_public(mark) for mark in marks],
    }


@app.post("/api/teacher/mark")
def set_activity_mark(request: Request, payload: dict, db: Session = Depends(get_db)):
    csrf_guard(request)
    require_teacher(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    username = normalize_username(payload.get("username", ""))
    lesson_id = payload.get("lesson_id", "")
    activity_id = payload.get("activity_id", "")
    status = (payload.get("status") or "").strip().lower()
    if status not in {"complete", "incomplete"}:
        raise HTTPException(status_code=400, detail="Invalid status.")
    if not username or not valid_lesson_id(lesson_id) or not valid_activity_id(activity_id):
        raise HTTPException(status_code=400, detail="Invalid lesson or activity id.")
    pupil = db.query(User).filter(User.username == username).first()
    if not pupil:
        raise HTTPException(status_code=404, detail="Pupil not found.")

    now = utcnow()
    mark = (
        db.query(ActivityMark)
        .filter(
            ActivityMark.user_id == pupil.id,
            ActivityMark.lesson_id == lesson_id,
            ActivityMark.activity_id == activity_id,
        )
        .first()
    )
    if mark:
        mark.status = status
        mark.updated_at = now
    else:
        mark = ActivityMark(
            user_id=pupil.id,
            lesson_id=lesson_id,
            activity_id=activity_id,
            status=status,
        )
        db.add(mark)
    db.commit()
    return {"ok": True, "mark": activity_mark_public(mark)}


@app.post("/api/teacher/pupil/{username}/notes")
def update_pupil_notes(
    request: Request,
    username: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    csrf_guard(request)
    require_teacher(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    pupil = db.query(User).filter(User.username == normalize_username(username)).first()
    if not pupil:
        raise HTTPException(status_code=404, detail="Pupil not found.")
    notes = (payload.get("teacher_notes", "") or "").strip() or None
    pupil.teacher_notes = notes
    db.commit()
    return {"ok": True, "teacher_notes": pupil.teacher_notes or ""}


@app.get("/api/teacher/export/lesson/{lesson_id}")
def export_lesson_csv(
    request: Request,
    lesson_id: str,
    cohort_year: str = "",
    db: Session = Depends(get_db),
):
    require_teacher(request)
    if not valid_lesson_id(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson id.")
    manifest = load_manifest()
    if not manifest:
        raise HTTPException(status_code=500, detail="Lesson manifest unavailable.")
    lessons = lesson_index(manifest)
    lesson = lessons.get(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found.")

    query = db.query(User).filter(User.role == "pupil", User.active.is_(True))
    if cohort_year:
        query = query.filter(User.cohort_year == cohort_year)
    pupils = query.order_by(User.username.asc()).all()
    pupil_ids = [pupil.id for pupil in pupils]

    marks = {}
    if pupil_ids:
        for mark in (
            db.query(ActivityMark)
            .filter(
                ActivityMark.user_id.in_(pupil_ids),
                ActivityMark.lesson_id == lesson_id,
            )
            .all()
        ):
            marks[(mark.user_id, mark.activity_id)] = mark

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "username",
            "name",
            "cohort_year",
            "lesson_id",
            "lesson_title",
            "activity_id",
            "activity_title",
            "objectives",
            "status",
            "marked_at",
        ]
    )

    activity_map = lesson_activity_map(lesson)
    for pupil in pupils:
        for activity_id, activity in activity_map.items():
            mark = marks.get((pupil.id, activity_id))
            status = mark.status if mark else "incomplete"
            marked_at = mark.updated_at.isoformat() if mark and mark.updated_at else ""
            objectives = objective_texts_for_activity(lesson, activity)
            writer.writerow(
                [
                    pupil.username,
                    pupil.name,
                    pupil.cohort_year or "",
                    lesson_id,
                    lesson.get("title") or "",
                    activity_id,
                    activity.get("title") or "",
                    " | ".join(objectives),
                    status,
                    marked_at,
                ]
            )

    filename = f"lesson-{lesson_id}-export.csv"
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/teacher/export/pupil/{username}")
def export_pupil_csv(
    request: Request,
    username: str,
    db: Session = Depends(get_db),
):
    require_teacher(request)
    username = normalize_username(username)
    if not username:
        raise HTTPException(status_code=400, detail="Invalid username.")
    manifest = load_manifest()
    if not manifest:
        raise HTTPException(status_code=500, detail="Lesson manifest unavailable.")
    lessons = (manifest.get("lessons") or []) if isinstance(manifest, dict) else []
    pupil = db.query(User).filter(User.username == username).first()
    if not pupil:
        raise HTTPException(status_code=404, detail="Pupil not found.")

    marks = {}
    for mark in db.query(ActivityMark).filter(ActivityMark.user_id == pupil.id).all():
        marks[(mark.lesson_id, mark.activity_id)] = mark

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "lesson_id",
            "lesson_title",
            "activity_id",
            "activity_title",
            "objectives",
            "status",
            "marked_at",
        ]
    )

    for lesson in sorted(lessons, key=lambda l: l.get("number") or 0):
        activity_map = lesson_activity_map(lesson)
        for activity_id, activity in activity_map.items():
            mark = marks.get((lesson.get("id"), activity_id))
            status = mark.status if mark else "incomplete"
            marked_at = mark.updated_at.isoformat() if mark and mark.updated_at else ""
            objectives = objective_texts_for_activity(lesson, activity)
            writer.writerow(
                [
                    lesson.get("id") or "",
                    lesson.get("title") or "",
                    activity_id,
                    activity.get("title") or "",
                    " | ".join(objectives),
                    status,
                    marked_at,
                ]
            )

    filename = f"pupil-{pupil.username}-export.csv"
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/teacher/links")
def teacher_links(request: Request):
    require_teacher(request)
    manifest = load_manifest() or {}
    items = (manifest.get("linksRegistry") or {}).get("items") or []
    overrides = load_link_overrides()
    merged = []
    for item in items:
        if not isinstance(item, dict):
            continue
        link_id = item.get("id")
        override = overrides.get(link_id, {}) if link_id else {}
        merged.append(link_item_public(item, override))
    return {"items": merged}


@app.post("/api/teacher/links/{link_id}")
def update_link_override(
    request: Request,
    link_id: str,
    payload: dict,
):
    csrf_guard(request)
    require_teacher(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    manifest = load_manifest() or {}
    items = (manifest.get("linksRegistry") or {}).get("items") or []
    known_ids = {item.get("id") for item in items if isinstance(item, dict)}
    if link_id not in known_ids:
        raise HTTPException(status_code=404, detail="Link not found.")

    overrides = load_link_overrides()
    replacement_url = (payload.get("replacement_url") or "").strip() or None
    local_path = (payload.get("local_path") or "").strip() or None
    disabled = bool(payload.get("disabled"))
    notes = (payload.get("notes") or "").strip() or None

    if not any([replacement_url, local_path, disabled, notes]):
        overrides.pop(link_id, None)
        save_link_overrides(overrides)
    else:
        overrides[link_id] = {
            "replacement_url": replacement_url,
            "local_path": local_path,
            "disabled": disabled,
            "notes": notes,
            "updated_at": utcnow().isoformat(),
        }
        save_link_overrides(overrides)

    override = overrides.get(link_id)
    item = next((item for item in items if item.get("id") == link_id), None)
    return {"ok": True, "item": link_item_public(item or {}, override)}


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
