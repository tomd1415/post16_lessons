# ICDL Thinking like a Coder (On-prem learning platform)

This repo delivers a containerized, on-prem web platform for the ICDL "Thinking like a Coder" course. It preserves the Lesson 1 UI/interaction patterns and grows into a full learning platform with local accounts, teacher workflows, and a manifest-driven content system.

## Project goals (from requirements)
- Preserve Lesson 1 look/feel and interaction patterns across all new pages.
- Phased delivery with a testable demo, acceptance tests, and rollback plan per phase.
- On-prem Linux deployment, fully containerized, small scale (~50 pupils, <=7 concurrent).
- Local accounts only; minimal data; 2-year retention (planned).
- Student work saved with revision history; pupils see only current state.
- Secure defaults (TLS, secure cookies, CSRF, OWASP/NCSC-aligned).
- Accessibility aligned to UK public sector expectations and WCAG 2.2 AA where practical.

## Progress snapshot (phased plan)
- [x] Phase 0: Design system inventory + core asset extraction + compose skeleton.
- [x] Phase 1: Site shell + lesson manifest + course catalogue + lesson placeholders.
- [x] Phase 2: Local accounts + roles + cohort/year + admin UI + access controls.
- [x] Phase 3: Server-backed saving + offline-first sync + revision history + role-based menus.
- [x] Phase 4: Teacher view v1 (filtering, completion, notes, CSV export).
- [x] Phase 5: Content expansion automation + link registry tooling.
- [x] Phase 6: Python runner MVP (safe, isolated execution).
- [ ] Phase 7: Teacher view v2 (stats, attention lists, timing).
- [ ] Phase 8: Ops hardening (backups, retention purge, audit log, DPIA support).

Detailed requirements and the phase plan are in `plans/prompt_1`.

## What is in the repo
- `web/` static frontend (hubs, lesson pages, manifest, core CSS/JS).
- `backend/` FastAPI service (auth, sessions, admin API) + Postgres integration.
- `compose.yml` container orchestration (Caddy reverse proxy, API, DB).
- `docker/Caddyfile` TLS + reverse proxy config (internal CA).
- `docs/design-system-inventory.md` Lesson 1 UI/behavior inventory (design system).
- `docs/lesson-manifest.md` lesson manifest schema and usage.
- `scripts/` automation tools (lesson pack scaffold, handbook bulk import, link registry checks).
- `backend/app/python_runner.py` Python execution sandbox (Docker-per-run).
- `data/` runtime data (link overrides).
- `plans/TeacherHandbook.pdf` source handbook reference.

## Architecture overview
- Reverse proxy: Caddy (`docker/Caddyfile`)
- Backend API: FastAPI (`backend/app/main.py`)
- DB: Postgres (`compose.yml` service `db`)
- Frontend: static HTML/CSS/JS in `web/` served by FastAPI `StaticFiles`

Request flow: browser -> Caddy -> FastAPI -> StaticFiles or API routes -> Postgres.

## Running locally (Docker)
Prereqs:
- Docker + Docker Compose (or Podman + podman-compose)

Start:
```
docker compose up --build
```

Open:
- `https://localhost:8443` (TLS uses Caddy internal CA; accept the browser warning)
- `http://localhost:8080` redirects to HTTPS

Stop:
```
docker compose down
```

## First admin bootstrap
You must create the first admin account once per database.

```
curl -k -X POST https://localhost:8443/api/admin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","name":"Admin User","password":"ChangeMe123!"}'
```

Then sign in at `https://localhost:8443/login.html`, open `https://localhost:8443/admin.html`, and create teacher/pupil users.

## User management
Roles:
- `pupil` (student access only)
- `teacher` (teacher hub + teacher resources)
- `admin` (teacher hub + admin UI)

Admin UI:
- `https://localhost:8443/admin.html`
- Create users manually or import CSV.

CSV import format:
```
username,name,role,cohort_year,password,teacher_notes
lastname.f,Full Name,pupil,2024,TempPass123,Optional note
```

Rules:
- Pupil usernames must match `lastname.firstinitial`.
- `cohort_year` is required for pupils.

## Hubs and key URLs
- Student hub: `https://localhost:8443/index.html`
- Teacher hub: `https://localhost:8443/teacher.html`
- Teacher view: `https://localhost:8443/teacher-view.html`
- Teacher revision history: `https://localhost:8443/teacher-history.html`
- Link registry: `https://localhost:8443/teacher-links.html`
- Admin hub: `https://localhost:8443/admin.html`
- Login: `https://localhost:8443/login.html`
- Lesson 1 teacher hub: `https://localhost:8443/lessons/lesson-1/index.html`
- Lesson 1 student hub: `https://localhost:8443/lessons/lesson-1/student.html`
- Lesson manifest: `https://localhost:8443/lessons/manifest.json`

## Lesson manifest system
Lessons are data-driven via `web/lessons/manifest.json`.
- Used by `web/core/catalog.js` to render the course catalogue.
- Lesson 1 is the fully styled exemplar. Lessons 2-15 have draft packs generated from the handbook exercises.
- Schema details: `docs/lesson-manifest.md`.

## Lesson pack scaffolding (Phase 5)
Create or refresh a lesson pack (student hub, teacher hub, activities) from the manifest:
```
.venv/bin/python scripts/new_lesson_pack.py --lesson-id lesson-2 --force
```
Activity pages generated by this script follow a structured scaffold with:
- Three quick auto-marked checks (instant feedback).
- Guided notes and checklist steps.
- A main task area broken into smaller prompts.
- Reflection space for pupil comments.
- A teacher-only answer guidance block.

The script also ensures lesson plan / printable cards / answer guidance pages exist and are linked in the manifest.

## Handbook import (bulk, Phase 5)
Generate draft activity packs for lessons 3-15 from `plans/TeacherHandbook.pdf`:
```
.venv/bin/python scripts/build_handbook_lessons.py
```
Note: this overwrites lesson 3-15 hubs, handbook-derived activity pages, and teacher resources. It preserves any extra activities already listed in the manifest.

## Python runner (Phase 6)
The MVP runner executes Python in a short-lived container with no network access and strict CPU/memory/time limits.
- Runner activity: `https://localhost:8443/lessons/lesson-4/activities/02-python-runner.html`
- The activity saves code and run outputs as revisioned activity state.
- File I/O works inside a per-run virtual folder; use **Save files** to persist outputs.
- `import turtle` writes `turtle.svg` for preview (SVG stub, no GUI).

Runner configuration (compose envs):
- `RUNNER_IMAGE` (default `python:3.12-slim`)
- `RUNNER_DOCKER_HOST` (default `unix:///var/run/docker.sock`)
- `RUNNER_DOCKER_API_VERSION` (default `1.50`, set lower if your daemon is older)
- `RUNNER_TIMEOUT_SEC`, `RUNNER_MEMORY_MB`, `RUNNER_CPUS`, `RUNNER_CONCURRENCY`
- `RUNNER_MAX_OUTPUT`, `RUNNER_MAX_CODE_SIZE`, `RUNNER_MAX_FILES`, `RUNNER_MAX_FILE_BYTES`

Note: The API container needs access to the Docker socket.
If you are using rootless Docker/Podman, set `RUNNER_DOCKER_HOST` to the correct socket and mount it into the API container.
If the runner image is not present, set `RUNNER_AUTO_PULL=1` or pre-pull it with `docker pull python:3.12-slim`.
Offline fallback: set `RUNNER_IMAGE=post16_lessons-api` and `RUNNER_AUTO_PULL=0` to use the locally built API image.

Diagnostics (teacher/admin only):
- `https://localhost:8443/api/python/diagnostics` shows runner config, socket status, and Docker client errors.

## Link registry tooling (Phase 5)
Handbook links live in the manifest `linksRegistry.items`. Teachers can set replacement URLs or local copies in:
- `https://localhost:8443/teacher-links.html`

Run a link health check (writes report to `reports/link-check.json`):
```
.venv/bin/python scripts/link_registry_check.py
```

To also write status updates back into the manifest:
```
.venv/bin/python scripts/link_registry_check.py --write-manifest
```

## Design system baseline (must preserve)
Lesson 1 defines the visual language and interaction patterns.
- Inventory: `docs/design-system-inventory.md`
- Core assets: `web/core/app.css`, `web/core/app.js`

Key rules:
- Do not redesign; reuse existing patterns and spacing.
- Teacher mode uses the same behavior and storage keys as Lesson 1.
- Print styles and `.no-print` behavior must remain unchanged.

## Security baseline (Phase 2)
- Password hashing: Argon2id (`backend/app/security.py`).
- Session cookies: HttpOnly, Secure, SameSite=Lax.
- CSRF protection on state-changing endpoints.
- Login rate limiting + lockout backoff.
- Path-based access control for teacher/admin routes.
- TLS termination via Caddy (internal CA).

## Data model (Phase 2-3)
User fields (stored in Postgres):
- `username`, `name`, `role`, `cohort_year`, `teacher_notes`
- `password_hash` (Argon2id)
- `created_at`, `updated_at`, `last_login_at`
- `failed_login_count`, `locked_until`, `active`

Session fields:
- `id` (token), `user_id`, `csrf_token`
- `created_at`, `expires_at`, `ip_address`, `user_agent`

Activity state fields:
- `user_id`, `lesson_id`, `activity_id`
- `state` (JSON snapshot), `created_at`, `updated_at`, `last_client_at`

Activity revision fields:
- `user_id`, `lesson_id`, `activity_id`
- `state` (JSON snapshot), `created_at`, `client_saved_at`

## Development workflow
Static web changes:
- Edit files in `web/` and refresh the browser.

Backend changes:
- Rebuild or restart the API container:
```
docker compose up --build api
```
or
```
docker compose restart api
```

## Testing
Automated tests cover auth, activity state, teacher view, and manifest scaffolds:
```
.venv/bin/python -m pytest backend/tests
```
Manual smoke check:
- Sign in/out.
- Teacher vs pupil access control.
- Lesson catalogue rendering.
- Activity state saves to server and resumes after refresh.
- Offline edit queues and syncs after reconnect (no data loss).

Optional syntax check:
```
python -m py_compile backend/app/*.py
```

## Troubleshooting
- TLS warning: Caddy uses an internal CA; accept the browser warning or import the CA if needed.
- Login blocked: too many failures triggers backoff; wait and retry.
- Access denied: verify role and session; check `/api/auth/me`.
- Static changes not visible: hard refresh to bypass cached assets.

## Known gaps (planned)
- Teacher view v2 (stats, attention lists, timing) (Phase 7).
- Backups, retention purge, audit logs (Phase 8).
- Lesson 2-15 activity wording polish (draft handbook imports).

## References
- Design system inventory: `docs/design-system-inventory.md`
- Lesson manifest schema: `docs/lesson-manifest.md`
- Source handbook: `plans/TeacherHandbook.pdf`
