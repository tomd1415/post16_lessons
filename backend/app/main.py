import asyncio
import csv
import io
import json
import os
import re
import secrets
import statistics
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import (
    ATTENTION_LIMIT,
    ATTENTION_REVISION_THRESHOLD,
    ATTENTION_STUCK_DAYS,
    CSRF_HEADER_NAME,
    LINK_OVERRIDES_PATH,
    RUNNER_CONCURRENCY,
    SESSION_COOKIE_NAME,
    SESSION_TTL_MINUTES,
)
from .db import SessionLocal, engine, get_db
from .models import AuditLog, ActivityMark, ActivityRevision, ActivityState, Base, Session as AuthSession, User
from .python_runner import RunnerError, RunnerUnavailable, run_python, runner_diagnostics
from .rate_limit import LoginLimiter, compute_lock_seconds
from .security import hash_password, verify_password

@asynccontextmanager
async def lifespan(_: FastAPI):
    last_err = None
    for _ in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception as exc:  # pragma: no cover - startup resilience
            last_err = exc
            await asyncio.sleep(1)
    if last_err:
        raise last_err
    yield


app = FastAPI(
    title="Thinking like a Coder API",
    version="0.1.0",
    lifespan=lifespan,
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


def audit_log_public(entry: AuditLog, actor: User | None, target: User | None) -> dict:
    return {
        "id": str(entry.id),
        "action": entry.action,
        "actor_username": actor.username if actor else None,
        "target_username": target.username if target else None,
        "lesson_id": entry.lesson_id,
        "activity_id": entry.activity_id,
        "metadata": entry.metadata_json or {},
        "ip_address": entry.ip_address,
        "user_agent": entry.user_agent,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
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


def safe_mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def safe_median(values):
    if not values:
        return None
    return statistics.median(values)


def format_minutes(value):
    if value is None:
        return None
    return round(float(value), 1)


def ensure_utc(value):
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def log_audit(
    db: Session,
    action: str,
    actor: User | None = None,
    target_user: User | None = None,
    lesson_id: str | None = None,
    activity_id: str | None = None,
    metadata: dict | None = None,
    request: Request | None = None,
):
    entry = AuditLog(
        actor_user_id=actor.id if actor else None,
        target_user_id=target_user.id if target_user else None,
        action=action,
        lesson_id=lesson_id,
        activity_id=activity_id,
        metadata_json=metadata or {},
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(entry)


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


def require_admin(request: Request) -> User:
    user = request.state.user
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required.")
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
    return path.startswith("/admin")


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
@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text("select 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db_ok": db_ok,
        "time": utcnow().isoformat(),
    }


@app.get("/api/metrics")
def metrics(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    user_counts = {
        "pupil": db.query(User).filter(User.role == "pupil", User.active.is_(True)).count(),
        "teacher": db.query(User).filter(User.role == "teacher", User.active.is_(True)).count(),
        "admin": db.query(User).filter(User.role == "admin", User.active.is_(True)).count(),
    }
    return {
        "users_active": user_counts,
        "sessions": db.query(AuthSession).count(),
        "activity_states": db.query(ActivityState).count(),
        "activity_revisions": db.query(ActivityRevision).count(),
        "activity_marks": db.query(ActivityMark).count(),
        "audit_logs": db.query(AuditLog).count(),
        "time": utcnow().isoformat(),
    }


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


@app.get("/api/teacher/stats")
def teacher_stats(
    request: Request,
    cohort_year: str = "",
    lesson_id: str = "",
    db: Session = Depends(get_db),
):
    require_teacher(request)
    if lesson_id and not valid_lesson_id(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson id.")

    manifest = load_manifest() or {}
    lessons = (manifest.get("lessons") or []) if isinstance(manifest, dict) else []
    lessons = sorted(lessons, key=lambda l: l.get("number") or 0)
    if lesson_id:
        lessons = [lesson for lesson in lessons if lesson.get("id") == lesson_id]

    lesson_ids = [lesson.get("id") for lesson in lessons if lesson.get("id")]
    lesson_titles = {lesson.get("id"): lesson.get("title") for lesson in lessons if lesson.get("id")}

    activity_meta = {}
    activity_objectives = {}
    objective_text = {}
    objective_activity_ids = {}
    totals = {}
    for lesson in lessons:
        lid = lesson.get("id")
        if not lid:
            continue
        activities = lesson.get("activities") or []
        activity_meta[lid] = {activity.get("id"): activity for activity in activities if activity.get("id")}
        activity_objectives[lid] = {}
        for activity in activities:
            activity_id = activity.get("id")
            if not activity_id:
                continue
            obj_ids = activity.get("objectiveIds") or []
            activity_objectives[lid][activity_id] = obj_ids
            for obj_id in obj_ids:
                objective_activity_ids.setdefault(lid, {}).setdefault(obj_id, set()).add(activity_id)
        objectives = lesson.get("objectives") or []
        objective_text[lid] = {obj.get("id"): obj.get("text") for obj in objectives if obj.get("id")}
        totals[lid] = len(activity_meta[lid])

    query = db.query(User).filter(User.role == "pupil", User.active.is_(True))
    if cohort_year:
        query = query.filter(User.cohort_year == cohort_year)
    pupils = query.order_by(User.username.asc()).all()
    pupil_ids = [pupil.id for pupil in pupils]

    lesson_stats = {
        lid: {
            "lesson_id": lid,
            "lesson_title": lesson_titles.get(lid, ""),
            "total_pupils": len(pupils),
            "completed_pupils": 0,
            "completion_rate": 0.0,
        }
        for lid in lesson_ids
    }
    activity_stats = {}
    objective_stats = {}
    for lid in lesson_ids:
        activity_stats[lid] = {}
        for activity_id, activity in (activity_meta.get(lid) or {}).items():
            activity_stats[lid][activity_id] = {
                "activity_id": activity_id,
                "activity_title": activity.get("title") or "",
                "completed": 0,
                "total": len(pupils),
                "completion_rate": 0.0,
            }
        objective_stats[lid] = {}
        for obj_id, text in (objective_text.get(lid) or {}).items():
            total_targets = len(pupils) * len(objective_activity_ids.get(lid, {}).get(obj_id, set()))
            objective_stats[lid][obj_id] = {
                "objective_id": obj_id,
                "objective_text": text or "",
                "completed": 0,
                "total": total_targets,
                "completion_rate": 0.0,
            }

    pupil_completion_counts = {}
    marks = []
    if pupil_ids and lesson_ids:
        marks_query = db.query(ActivityMark).filter(ActivityMark.user_id.in_(pupil_ids))
        marks_query = marks_query.filter(ActivityMark.lesson_id.in_(lesson_ids))
        marks = marks_query.all()
    for mark in marks:
        if mark.status != "complete":
            continue
        lid = mark.lesson_id
        activity_id = mark.activity_id
        if lid not in activity_meta or activity_id not in activity_meta[lid]:
            continue
        pupil_completion_counts[(mark.user_id, lid)] = pupil_completion_counts.get((mark.user_id, lid), 0) + 1
        activity_stats[lid][activity_id]["completed"] += 1
        for obj_id in activity_objectives.get(lid, {}).get(activity_id, []):
            if obj_id in objective_stats[lid]:
                objective_stats[lid][obj_id]["completed"] += 1

    for lid in lesson_ids:
        total = totals.get(lid, 0)
        for pupil in pupils:
            completed = pupil_completion_counts.get((pupil.id, lid), 0)
            if total > 0 and completed >= total:
                lesson_stats[lid]["completed_pupils"] += 1
        if len(pupils):
            lesson_stats[lid]["completion_rate"] = lesson_stats[lid]["completed_pupils"] / len(pupils)

        for stats in activity_stats[lid].values():
            if stats["total"]:
                stats["completion_rate"] = stats["completed"] / stats["total"]

        for stats in objective_stats[lid].values():
            if stats["total"]:
                stats["completion_rate"] = stats["completed"] / stats["total"]

    activity_timing = {lid: {aid: [] for aid in (activity_meta.get(lid) or {})} for lid in lesson_ids}
    pupil_lesson_durations = {}
    if pupil_ids and lesson_ids:
        revisions_query = db.query(ActivityRevision).filter(ActivityRevision.user_id.in_(pupil_ids))
        revisions_query = revisions_query.filter(ActivityRevision.lesson_id.in_(lesson_ids))
        revisions = revisions_query.all()
    else:
        revisions = []

    revision_times = {}
    for rev in revisions:
        lid = rev.lesson_id
        aid = rev.activity_id
        if lid not in activity_meta or aid not in activity_meta[lid]:
            continue
        timestamp = ensure_utc(rev.client_saved_at or rev.created_at)
        if not timestamp:
            continue
        key = (rev.user_id, lid, aid)
        revision_times.setdefault(key, []).append(timestamp)

    for (user_id, lid, aid), times in revision_times.items():
        if len(times) < 2:
            continue
        times_sorted = sorted(times)
        duration_sec = (times_sorted[-1] - times_sorted[0]).total_seconds()
        if duration_sec < 0:
            continue
        minutes = duration_sec / 60.0
        activity_timing[lid][aid].append(minutes)
        pupil_lesson_durations[(user_id, lid)] = pupil_lesson_durations.get((user_id, lid), 0.0) + minutes

    lesson_timing = {}
    activity_timing_stats = {}
    for lid in lesson_ids:
        pupil_minutes = [minutes for (user_id, lesson_key), minutes in pupil_lesson_durations.items() if lesson_key == lid]
        lesson_timing[lid] = {
            "avg_minutes": format_minutes(safe_mean(pupil_minutes)),
            "median_minutes": format_minutes(safe_median(pupil_minutes)),
            "samples": len(pupil_minutes),
        }
        activity_timing_stats[lid] = {}
        for aid, durations in activity_timing[lid].items():
            activity_timing_stats[lid][aid] = {
                "avg_minutes": format_minutes(safe_mean(durations)),
                "median_minutes": format_minutes(safe_median(durations)),
                "samples": len(durations),
            }

    return {
        "lesson_ids": lesson_ids,
        "lesson_stats": lesson_stats,
        "activity_stats": activity_stats,
        "objective_stats": objective_stats,
        "timing": {
            "lessons": lesson_timing,
            "activities": activity_timing_stats,
        },
    }


@app.get("/api/teacher/attention")
def teacher_attention(
    request: Request,
    cohort_year: str = "",
    lesson_id: str = "",
    limit: int = ATTENTION_LIMIT,
    db: Session = Depends(get_db),
):
    require_teacher(request)
    if lesson_id and not valid_lesson_id(lesson_id):
        raise HTTPException(status_code=400, detail="Invalid lesson id.")
    limit = max(1, min(int(limit or ATTENTION_LIMIT), 500))

    manifest = load_manifest() or {}
    lessons = (manifest.get("lessons") or []) if isinstance(manifest, dict) else []
    lesson_titles = {lesson.get("id"): lesson.get("title") for lesson in lessons if lesson.get("id")}
    activity_titles = {}
    for lesson in lessons:
        lid = lesson.get("id")
        for activity in lesson.get("activities") or []:
            activity_id = activity.get("id")
            if lid and activity_id:
                activity_titles[(lid, activity_id)] = activity.get("title") or ""

    query = db.query(User).filter(User.role == "pupil", User.active.is_(True))
    if cohort_year:
        query = query.filter(User.cohort_year == cohort_year)
    pupils = query.order_by(User.username.asc()).all()
    pupil_map = {pupil.id: pupil for pupil in pupils}
    pupil_ids = [pupil.id for pupil in pupils]

    marks = []
    if pupil_ids:
        marks_query = db.query(ActivityMark).filter(ActivityMark.user_id.in_(pupil_ids))
        if lesson_id:
            marks_query = marks_query.filter(ActivityMark.lesson_id == lesson_id)
        marks = marks_query.all()
    mark_status = {(mark.user_id, mark.lesson_id, mark.activity_id): mark.status for mark in marks}

    revisions = []
    if pupil_ids:
        revisions_query = db.query(ActivityRevision).filter(ActivityRevision.user_id.in_(pupil_ids))
        if lesson_id:
            revisions_query = revisions_query.filter(ActivityRevision.lesson_id == lesson_id)
        revisions = revisions_query.all()

    rev_summary = {}
    for rev in revisions:
        lid = rev.lesson_id
        aid = rev.activity_id
        key = (rev.user_id, lid, aid)
        timestamp = ensure_utc(rev.client_saved_at or rev.created_at)
        if not timestamp:
            continue
        entry = rev_summary.get(key)
        if not entry:
            rev_summary[key] = {"count": 1, "last": timestamp}
        else:
            entry["count"] += 1
            if timestamp > entry["last"]:
                entry["last"] = timestamp

    cutoff = utcnow() - timedelta(days=ATTENTION_STUCK_DAYS)
    items = []
    for (user_id, lid, aid), info in rev_summary.items():
        pupil = pupil_map.get(user_id)
        if not pupil:
            continue
        status = mark_status.get((user_id, lid, aid), "incomplete")
        reasons = []
        if status != "complete":
            reasons.append("not_completed")
        if info["count"] >= ATTENTION_REVISION_THRESHOLD:
            reasons.append("many_revisions")
        if status != "complete" and info["last"] < cutoff:
            reasons.append("stuck")
        if not reasons:
            continue
        items.append(
            {
                "username": pupil.username,
                "name": pupil.name,
                "cohort_year": pupil.cohort_year or "",
                "lesson_id": lid,
                "lesson_title": lesson_titles.get(lid, ""),
                "activity_id": aid,
                "activity_title": activity_titles.get((lid, aid), ""),
                "status": status,
                "reasons": reasons,
                "revision_count": info["count"],
                "last_activity_at": info["last"].isoformat(),
            }
        )

    def item_score(item):
        score = 0
        if "stuck" in item["reasons"]:
            score += 4
        if "many_revisions" in item["reasons"]:
            score += 2
        if "not_completed" in item["reasons"]:
            score += 1
        return score

    items.sort(key=lambda item: (-item_score(item), item["last_activity_at"]))
    items = items[:limit]

    return {
        "thresholds": {
            "stuck_days": ATTENTION_STUCK_DAYS,
            "revision_threshold": ATTENTION_REVISION_THRESHOLD,
        },
        "items": items,
    }


def audit_entries(
    db: Session,
    actor_username: str,
    target_username: str,
    action: str,
    since: str,
    limit: int,
):
    limit = max(1, min(int(limit or 200), 500))
    query = db.query(AuditLog)

    if actor_username:
        actor_username = normalize_username(actor_username)
        actor = db.query(User).filter(User.username == actor_username).first()
        if not actor:
            return {"items": []}
        query = query.filter(AuditLog.actor_user_id == actor.id)

    if target_username:
        target_username = normalize_username(target_username)
        target = db.query(User).filter(User.username == target_username).first()
        if not target:
            return {"items": []}
        query = query.filter(AuditLog.target_user_id == target.id)

    if action:
        query = query.filter(AuditLog.action == action)

    since_dt = parse_client_time(since)
    if since_dt:
        query = query.filter(AuditLog.created_at >= ensure_utc(since_dt))

    entries = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    user_ids = {entry.actor_user_id for entry in entries if entry.actor_user_id}
    user_ids.update({entry.target_user_id for entry in entries if entry.target_user_id})
    user_map = {user.id: user for user in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return {
        "items": [
            audit_log_public(entry, user_map.get(entry.actor_user_id), user_map.get(entry.target_user_id))
            for entry in entries
        ]
    }


@app.get("/api/teacher/audit")
def teacher_audit(
    request: Request,
    actor_username: str = "",
    target_username: str = "",
    action: str = "",
    since: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
):
    require_admin(request)
    return audit_entries(db, actor_username, target_username, action, since, limit)


@app.get("/api/admin/audit")
def admin_audit(
    request: Request,
    actor_username: str = "",
    target_username: str = "",
    action: str = "",
    since: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
):
    require_admin(request)
    return audit_entries(db, actor_username, target_username, action, since, limit)

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
    actor = require_teacher(request)
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
    log_audit(
        db,
        action="mark_activity",
        actor=actor,
        target_user=pupil,
        lesson_id=lesson_id,
        activity_id=activity_id,
        metadata={"status": status},
        request=request,
    )
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
    actor = require_teacher(request)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")
    pupil = db.query(User).filter(User.username == normalize_username(username)).first()
    if not pupil:
        raise HTTPException(status_code=404, detail="Pupil not found.")
    notes = (payload.get("teacher_notes", "") or "").strip() or None
    pupil.teacher_notes = notes
    log_audit(
        db,
        action="update_teacher_notes",
        actor=actor,
        target_user=pupil,
        metadata={"has_notes": bool(notes)},
        request=request,
    )
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
    db: Session = Depends(get_db),
):
    csrf_guard(request)
    actor = require_teacher(request)
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
    log_audit(
        db,
        action="update_link_override",
        actor=actor,
        metadata={
            "link_id": link_id,
            "replacement_url": replacement_url,
            "local_path": local_path,
            "disabled": disabled,
        },
        request=request,
    )
    db.commit()

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
    log_audit(
        db,
        action="bootstrap_admin",
        target_user=user,
        metadata={"username": username},
    )
    db.commit()
    return {"ok": True, "user": user_public(user)}


@app.post("/api/admin/users")
def create_user(request: Request, payload: dict, db: Session = Depends(get_db)):
    csrf_guard(request)
    actor = require_admin(request)
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
    log_audit(
        db,
        action="create_user",
        actor=actor,
        target_user=new_user,
        metadata={"role": role, "cohort_year": cohort_year},
        request=request,
    )
    db.commit()
    return {"ok": True, "user": user_public(new_user)}


@app.post("/api/admin/users/import")
def import_users(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    csrf_guard(request)
    actor = require_admin(request)

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

    log_audit(
        db,
        action="import_users",
        actor=actor,
        metadata={"created": created, "rows": len(rows)},
        request=request,
    )
    db.commit()
    return {"created": created, "errors": []}


@app.get("/api/admin/users")
def list_users(
    request: Request,
    role: str = "",
    cohort_year: str = "",
    active: str = "",
    search: str = "",
    db: Session = Depends(get_db),
):
    """List all users with optional filtering."""
    require_admin(request)

    query = db.query(User)

    if role:
        query = query.filter(User.role == role.lower())
    if cohort_year:
        query = query.filter(User.cohort_year == cohort_year)
    if active:
        is_active = active.lower() in ("true", "1", "yes")
        query = query.filter(User.active.is_(is_active))
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (User.username.ilike(search_term)) | (User.name.ilike(search_term))
        )

    users = query.order_by(User.username.asc()).all()

    return {
        "items": [
            {
                **user_public(user),
                "active": user.active,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ]
    }


@app.get("/api/admin/users/{username}")
def get_user(
    request: Request,
    username: str,
    db: Session = Depends(get_db),
):
    """Get a specific user by username."""
    require_admin(request)
    username = normalize_username(username)

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    return {
        "user": {
            **user_public(user),
            "active": user.active,
            "teacher_notes": user.teacher_notes or "",
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "failed_login_count": user.failed_login_count or 0,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
        }
    }


@app.put("/api/admin/users/{username}")
def update_user(
    request: Request,
    username: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Update a user's details."""
    csrf_guard(request)
    actor = require_admin(request)

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload.")

    username = normalize_username(username)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Prevent admin from deactivating themselves
    if user.id == actor.id and payload.get("active") is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account.")

    # Prevent demoting the last admin
    if user.role == "admin" and payload.get("role") and payload.get("role") != "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.active.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin.")

    changes = {}

    # Update name
    if "name" in payload:
        new_name = (payload["name"] or "").strip()
        if new_name and new_name != user.name:
            changes["name"] = {"old": user.name, "new": new_name}
            user.name = new_name

    # Update role
    if "role" in payload:
        new_role = (payload["role"] or "").strip().lower()
        if new_role and new_role in {"pupil", "teacher", "admin"} and new_role != user.role:
            changes["role"] = {"old": user.role, "new": new_role}
            user.role = new_role

    # Update cohort_year
    if "cohort_year" in payload:
        new_cohort = (payload["cohort_year"] or "").strip() or None
        if new_cohort != user.cohort_year:
            changes["cohort_year"] = {"old": user.cohort_year, "new": new_cohort}
            user.cohort_year = new_cohort

    # Update active status
    if "active" in payload:
        new_active = bool(payload["active"])
        if new_active != user.active:
            changes["active"] = {"old": user.active, "new": new_active}
            user.active = new_active

    # Update teacher_notes
    if "teacher_notes" in payload:
        new_notes = (payload["teacher_notes"] or "").strip() or None
        if new_notes != user.teacher_notes:
            changes["teacher_notes"] = {"old": bool(user.teacher_notes), "new": bool(new_notes)}
            user.teacher_notes = new_notes

    # Update password
    if "password" in payload and payload["password"]:
        new_password = payload["password"]
        if len(new_password) < 4:
            raise HTTPException(status_code=400, detail="Password too short.")
        user.password_hash = hash_password(new_password)
        changes["password"] = True

    # Reset failed login count / unlock account
    if payload.get("unlock_account"):
        if user.failed_login_count or user.locked_until:
            changes["unlock"] = True
            user.failed_login_count = 0
            user.locked_until = None

    if changes:
        log_audit(
            db,
            action="update_user",
            actor=actor,
            target_user=user,
            metadata={"changes": list(changes.keys())},
            request=request,
        )
        db.commit()

    return {
        "ok": True,
        "user": {
            **user_public(user),
            "active": user.active,
            "teacher_notes": user.teacher_notes or "",
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
        "changes": list(changes.keys()),
    }


@app.delete("/api/admin/users/{username}")
def delete_user(
    request: Request,
    username: str,
    db: Session = Depends(get_db),
):
    """Deactivate a user (soft delete)."""
    csrf_guard(request)
    actor = require_admin(request)

    username = normalize_username(username)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Prevent admin from deleting themselves
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")

    # Prevent deleting the last admin
    if user.role == "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.active.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin.")

    user.active = False
    log_audit(
        db,
        action="delete_user",
        actor=actor,
        target_user=user,
        request=request,
    )
    db.commit()

    return {"ok": True, "message": f"User {username} has been deactivated."}


app.mount("/", StaticFiles(directory="/srv", html=True), name="static")
