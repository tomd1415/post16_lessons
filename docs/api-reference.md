# API Reference

Complete reference documentation for the TLAC (Thinking Like a Coder) API.

## Overview

- **Base URL**: `https://localhost:8443/api`
- **Authentication**: Session-based with cookies
- **CSRF Protection**: Required for POST/PUT/DELETE requests via `X-CSRF-Token` header
- **Content-Type**: `application/json` (unless otherwise specified)

## Authentication

All endpoints except `/api/health`, `/api/metrics`, and `/api/auth/login` require authentication.

### Session Cookies

After successful login, a session cookie (`tlac_session`) is set. Include this cookie in all subsequent requests.

### CSRF Protection

For mutating requests (POST, PUT, DELETE), include the CSRF token in the `X-CSRF-Token` header. Obtain the token from `/api/auth/me`.

---

## Health & Monitoring

### GET /api/health

Health check endpoint for monitoring and load balancers.

**Authentication**: Not required

**Response**:
```json
{
  "status": "ok",
  "db_ok": true,
  "time": "2026-01-11T12:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"ok"` or `"degraded"` |
| `db_ok` | boolean | Database connectivity status |
| `time` | string | Server time in ISO format |

---

### GET /api/metrics

Prometheus metrics endpoint for scraping.

**Authentication**: Not required

**Response**: Prometheus text format

```
# HELP tlac_http_requests_total Total HTTP requests
# TYPE tlac_http_requests_total counter
tlac_http_requests_total{method="GET",endpoint="/api/health",status="200"} 42.0
...
```

---

### GET /api/admin/metrics

JSON summary of key metrics for admin dashboard.

**Authentication**: Admin only

**Response**:
```json
{
  "summary": {
    "total_users": 150,
    "active_users": 145,
    "total_pupils": 140,
    "total_teachers": 8,
    "total_admins": 2,
    "active_sessions": 25,
    "recent_logins_7d": 120
  },
  "http": {
    "total_requests": 5000,
    "successful_requests": 4850,
    "error_requests": 150,
    "success_rate": 97.0
  },
  "authentication": {
    "total_login_attempts": 200,
    "successful_logins": 180,
    "failed_logins": 18,
    "rate_limited_logins": 2,
    "success_rate": 90.0
  },
  "python_runner": {
    "total_runs": 1500,
    "successful_runs": 1400,
    "error_runs": 80,
    "timeout_runs": 20,
    "success_rate": 93.3
  },
  "activity": {
    "total_saves": 8000,
    "rate_limit_violations": 5
  },
  "system": {
    "db_connections": 5,
    "total_errors": 50
  }
}
```

---

## Authentication Endpoints

### GET /api/auth/me

Get current user information and CSRF token.

**Authentication**: Required

**Response** (authenticated):
```json
{
  "user": {
    "id": "uuid",
    "username": "smith.j",
    "name": "John Smith",
    "role": "pupil",
    "cohort_year": "2025"
  },
  "csrf_token": "abc123..."
}
```

**Response** (not authenticated):
```json
{
  "detail": "Not authenticated."
}
```

---

### POST /api/auth/login

Authenticate user and create session.

**Authentication**: Not required

**Request Body**:
```json
{
  "username": "smith.j",
  "password": "secret123"
}
```

**Response** (success):
```json
{
  "ok": true,
  "user": {
    "id": "uuid",
    "username": "smith.j",
    "name": "John Smith",
    "role": "pupil",
    "cohort_year": "2025"
  }
}
```

**Response** (failure):
| Status | Detail |
|--------|--------|
| 401 | `"Invalid username or password."` |
| 403 | `"Account disabled."` |
| 429 | `"Too many attempts. Try again shortly."` |

**Rate Limiting**: 5 failed attempts per IP/username combination triggers lockout.

---

### POST /api/auth/logout

End current session.

**Authentication**: Required
**CSRF**: Required

**Response**:
```json
{
  "ok": true
}
```

---

## Activity Endpoints

### GET /api/activity/state

List all activity states for current user.

**Authentication**: Required

**Response**:
```json
{
  "items": [
    {
      "lesson_id": "lesson-1",
      "activity_id": "a01",
      "state": {"code": "print('hello')", "progress": 50},
      "updated_at": "2026-01-11T10:00:00+00:00",
      "last_client_at": "2026-01-11T10:00:00+00:00"
    }
  ]
}
```

---

### GET /api/activity/state/{lesson_id}/{activity_id}

Get activity state for specific lesson/activity.

**Authentication**: Required

**Path Parameters**:
| Parameter | Format | Example |
|-----------|--------|---------|
| `lesson_id` | `lesson-\d+` | `lesson-1` |
| `activity_id` | `a\d+` | `a01` |

**Response** (found):
```json
{
  "lesson_id": "lesson-1",
  "activity_id": "a01",
  "state": {"code": "print('hello')", "progress": 50},
  "updated_at": "2026-01-11T10:00:00+00:00",
  "last_client_at": "2026-01-11T10:00:00+00:00"
}
```

**Response** (not found):
```json
{
  "state": null
}
```

---

### POST /api/activity/state/{lesson_id}/{activity_id}

Save activity state.

**Authentication**: Required
**CSRF**: Required

**Path Parameters**:
| Parameter | Format | Example |
|-----------|--------|---------|
| `lesson_id` | `lesson-\d+` | `lesson-1` |
| `activity_id` | `a\d+` | `a01` |

**Request Body**:
```json
{
  "state": {"code": "print('hello')", "progress": 75},
  "client_saved_at": 1704970800000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `state` | object | Yes | Activity state data |
| `client_saved_at` | number/string | No | Client timestamp (ms epoch or ISO) |

**Response**:
```json
{
  "ok": true,
  "updated_at": "2026-01-11T10:00:00+00:00",
  "revision_id": "uuid"
}
```

**Rate Limiting**: 60 saves per minute per user.

---

## Python Runner Endpoints

### POST /api/python/run

Execute Python code in sandboxed environment.

**Authentication**: Required
**CSRF**: Required

**Request Body**:
```json
{
  "lesson_id": "lesson-1",
  "activity_id": "a01",
  "code": "print('Hello, World!')",
  "files": []
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lesson_id` | string | Yes | Lesson ID |
| `activity_id` | string | Yes | Activity ID |
| `code` | string | Yes | Python code to execute |
| `files` | array | No | Additional files for execution |

**Response** (success):
```json
{
  "ok": true,
  "stdout": "Hello, World!\n",
  "stderr": "",
  "exit_code": 0,
  "timed_out": false,
  "duration_ms": 150,
  "files": []
}
```

**Response** (timeout):
```json
{
  "ok": true,
  "stdout": "",
  "stderr": "Execution timed out",
  "exit_code": -1,
  "timed_out": true,
  "duration_ms": 5000,
  "files": []
}
```

**Error Responses**:
| Status | Detail |
|--------|--------|
| 400 | `"Code is required."` |
| 429 | `"Too many code executions. Limit: X per minute."` |
| 503 | `"Python runner unavailable."` |
| 500 | Runner error details |

**Rate Limiting**: 30 executions per minute per user.

---

### GET /api/python/diagnostics

Get Python runner diagnostic information.

**Authentication**: Teacher or Admin

**Response**:
```json
{
  "docker_available": true,
  "image_exists": true,
  "container_running": false,
  "runner_type": "docker",
  "concurrency_limit": 5
}
```

---

## Teacher Endpoints

### GET /api/teacher/users

List all active pupils.

**Authentication**: Teacher or Admin

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `cohort_year` | string | Filter by cohort year |

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "username": "smith.j",
      "name": "John Smith",
      "role": "pupil",
      "cohort_year": "2025"
    }
  ]
}
```

---

### GET /api/teacher/revisions

Get activity revision history for a pupil.

**Authentication**: Teacher or Admin

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | Yes | Pupil username |
| `lesson_id` | string | No | Filter by lesson |
| `activity_id` | string | No | Filter by activity |
| `limit` | integer | No | Max results (default: 50, max: 200) |

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "lesson_id": "lesson-1",
      "activity_id": "a01",
      "state": {"code": "..."},
      "created_at": "2026-01-11T10:00:00+00:00",
      "client_saved_at": "2026-01-11T10:00:00+00:00"
    }
  ]
}
```

---

### GET /api/teacher/overview

Get class completion overview.

**Authentication**: Teacher or Admin

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `cohort_year` | string | Filter by cohort year |

**Response**:
```json
{
  "lessons": [
    {
      "id": "lesson-1",
      "number": 1,
      "title": "Introduction to Python",
      "total_activities": 5
    }
  ],
  "pupils": [
    {
      "id": "uuid",
      "username": "smith.j",
      "name": "John Smith",
      "role": "pupil",
      "cohort_year": "2025"
    }
  ],
  "completion": {
    "smith.j": {
      "lesson-1": {"completed": 3, "total": 5}
    }
  }
}
```

---

### GET /api/teacher/stats

Get detailed statistics for lessons and activities.

**Authentication**: Teacher or Admin

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `cohort_year` | string | Filter by cohort year |
| `lesson_id` | string | Filter by specific lesson |

**Response**:
```json
{
  "lesson_ids": ["lesson-1"],
  "lesson_stats": {
    "lesson-1": {
      "lesson_id": "lesson-1",
      "lesson_title": "Introduction",
      "total_pupils": 30,
      "completed_pupils": 25,
      "completion_rate": 0.83
    }
  },
  "activity_stats": {
    "lesson-1": {
      "a01": {
        "activity_id": "a01",
        "activity_title": "Hello World",
        "completed": 28,
        "total": 30,
        "completion_rate": 0.93
      }
    }
  },
  "objective_stats": {
    "lesson-1": {
      "obj1": {
        "objective_id": "obj1",
        "objective_text": "Understand variables",
        "completed": 85,
        "total": 90,
        "completion_rate": 0.94
      }
    }
  },
  "timing": {
    "lessons": {
      "lesson-1": {
        "avg_minutes": "45.5",
        "median_minutes": "42.0",
        "samples": 25
      }
    },
    "activities": {
      "lesson-1": {
        "a01": {
          "avg_minutes": "8.2",
          "median_minutes": "7.5",
          "samples": 28
        }
      }
    }
  }
}
```

---

### GET /api/teacher/attention

Get pupils needing attention (stuck, many revisions, incomplete).

**Authentication**: Teacher or Admin

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cohort_year` | string | | Filter by cohort year |
| `lesson_id` | string | | Filter by lesson |
| `limit` | integer | 50 | Max results (max: 500) |

**Response**:
```json
{
  "thresholds": {
    "stuck_days": 7,
    "revision_threshold": 10
  },
  "items": [
    {
      "username": "smith.j",
      "name": "John Smith",
      "cohort_year": "2025",
      "lesson_id": "lesson-1",
      "lesson_title": "Introduction",
      "activity_id": "a01",
      "activity_title": "Hello World",
      "status": "incomplete",
      "reasons": ["stuck", "many_revisions"],
      "revision_count": 15,
      "last_activity_at": "2026-01-04T10:00:00+00:00"
    }
  ]
}
```

---

### GET /api/teacher/pupil/{username}/lesson/{lesson_id}

Get detailed pupil progress for a lesson.

**Authentication**: Teacher or Admin

**Path Parameters**:
| Parameter | Description |
|-----------|-------------|
| `username` | Pupil username |
| `lesson_id` | Lesson ID |

**Response**:
```json
{
  "pupil": {
    "id": "uuid",
    "username": "smith.j",
    "name": "John Smith",
    "role": "pupil",
    "cohort_year": "2025"
  },
  "teacher_notes": "Working well on loops",
  "states": [
    {
      "lesson_id": "lesson-1",
      "activity_id": "a01",
      "state": {"code": "..."},
      "updated_at": "2026-01-11T10:00:00+00:00",
      "last_client_at": "2026-01-11T10:00:00+00:00"
    }
  ],
  "marks": [
    {
      "lesson_id": "lesson-1",
      "activity_id": "a01",
      "status": "complete",
      "updated_at": "2026-01-11T10:00:00+00:00"
    }
  ]
}
```

---

### POST /api/teacher/mark

Set activity completion status.

**Authentication**: Teacher or Admin
**CSRF**: Required

**Request Body**:
```json
{
  "username": "smith.j",
  "lesson_id": "lesson-1",
  "activity_id": "a01",
  "status": "complete"
}
```

| Field | Type | Values |
|-------|------|--------|
| `username` | string | Pupil username |
| `lesson_id` | string | Lesson ID |
| `activity_id` | string | Activity ID |
| `status` | string | `"complete"` or `"incomplete"` |

**Response**:
```json
{
  "ok": true,
  "mark": {
    "lesson_id": "lesson-1",
    "activity_id": "a01",
    "status": "complete",
    "updated_at": "2026-01-11T10:00:00+00:00"
  }
}
```

---

### POST /api/teacher/pupil/{username}/notes

Update teacher notes for a pupil.

**Authentication**: Teacher or Admin
**CSRF**: Required

**Path Parameters**:
| Parameter | Description |
|-----------|-------------|
| `username` | Pupil username |

**Request Body**:
```json
{
  "teacher_notes": "Working well on loops. Needs help with functions."
}
```

**Response**:
```json
{
  "ok": true,
  "teacher_notes": "Working well on loops. Needs help with functions."
}
```

---

### GET /api/teacher/export/lesson/{lesson_id}

Export lesson progress as CSV.

**Authentication**: Teacher or Admin

**Path Parameters**:
| Parameter | Description |
|-----------|-------------|
| `lesson_id` | Lesson ID |

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `cohort_year` | string | Filter by cohort year |

**Response**: CSV file download

**CSV Columns**:
- `username`, `name`, `cohort_year`, `lesson_id`, `lesson_title`
- `activity_id`, `activity_title`, `objectives`, `status`, `marked_at`

---

### GET /api/teacher/export/pupil/{username}

Export pupil's complete progress as CSV.

**Authentication**: Teacher or Admin

**Path Parameters**:
| Parameter | Description |
|-----------|-------------|
| `username` | Pupil username |

**Response**: CSV file download

**CSV Columns**:
- `lesson_id`, `lesson_title`, `activity_id`, `activity_title`
- `objectives`, `status`, `marked_at`

---

### GET /api/teacher/links

Get external links registry with overrides.

**Authentication**: Teacher or Admin

**Response**:
```json
{
  "items": [
    {
      "id": "link-1",
      "title": "Python Docs",
      "original_url": "https://docs.python.org",
      "replacement_url": null,
      "local_path": null,
      "disabled": false,
      "notes": null
    }
  ]
}
```

---

### POST /api/teacher/links/{link_id}

Update link override settings.

**Authentication**: Teacher or Admin
**CSRF**: Required

**Path Parameters**:
| Parameter | Description |
|-----------|-------------|
| `link_id` | Link ID from registry |

**Request Body**:
```json
{
  "replacement_url": "https://internal.school.edu/python-docs",
  "local_path": null,
  "disabled": false,
  "notes": "Using internal mirror"
}
```

**Response**:
```json
{
  "ok": true,
  "item": {
    "id": "link-1",
    "title": "Python Docs",
    "original_url": "https://docs.python.org",
    "replacement_url": "https://internal.school.edu/python-docs",
    "local_path": null,
    "disabled": false,
    "notes": "Using internal mirror"
  }
}
```

---

## Admin Endpoints

### GET /api/admin/audit

Get audit log entries with pagination.

**Authentication**: Admin only

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `actor_username` | string | Filter by actor |
| `target_username` | string | Filter by target |
| `action` | string | Filter by action type |
| `since` | string | Filter by date (ISO or ms timestamp) |
| `limit` | integer | Max results (default: 50, max: 200) |
| `cursor` | string | Pagination cursor |

**Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "action": "login",
      "actor_username": "smith.j",
      "target_username": null,
      "lesson_id": null,
      "activity_id": null,
      "metadata": {},
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2026-01-11T10:00:00+00:00"
    }
  ],
  "has_more": true,
  "next_cursor": "2026-01-11T10:00:00+00:00:uuid"
}
```

**Audit Actions**:
- `login`, `logout`
- `mark_activity`
- `update_teacher_notes`
- `update_link_override`
- `create_user`, `import_users`
- `bootstrap_admin`

---

### POST /api/admin/bootstrap

Create initial admin user (only works if no admin exists).

**Authentication**: Not required (one-time only)

**Request Body**:
```json
{
  "username": "admin",
  "name": "System Administrator",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "ok": true,
  "user": {
    "id": "uuid",
    "username": "admin",
    "name": "System Administrator",
    "role": "admin",
    "cohort_year": null
  }
}
```

**Errors**:
| Status | Detail |
|--------|--------|
| 403 | `"Admin already exists."` |
| 400 | `"Missing required fields."` |

---

### POST /api/admin/users

Create a new user.

**Authentication**: Admin only
**CSRF**: Required

**Request Body**:
```json
{
  "username": "smith.j",
  "name": "John Smith",
  "role": "pupil",
  "cohort_year": "2025",
  "password": "initial_password",
  "teacher_notes": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Unique username |
| `name` | string | Yes | Display name |
| `role` | string | No | `pupil`, `teacher`, or `admin` (default: pupil) |
| `cohort_year` | string | For pupils | Cohort/year group |
| `password` | string | Yes | Initial password |
| `teacher_notes` | string | No | Teacher notes |

**Username Requirements**:
- General: `^[a-z0-9._-]+$`
- Pupils: `^[a-z][a-z\-']*\.[a-z]$` (lastname.firstinitial)

**Response**:
```json
{
  "ok": true,
  "user": {
    "id": "uuid",
    "username": "smith.j",
    "name": "John Smith",
    "role": "pupil",
    "cohort_year": "2025"
  }
}
```

---

### POST /api/admin/users/import

Bulk import users from CSV file.

**Authentication**: Admin only
**CSRF**: Required
**Content-Type**: `multipart/form-data`

**Request**: File upload with CSV data

**CSV Required Headers**:
- `username`, `name`, `password`

**CSV Optional Headers**:
- `role` (default: pupil)
- `cohort_year` (required for pupils)
- `teacher_notes`

**Response** (success):
```json
{
  "created": 25,
  "errors": []
}
```

**Response** (with errors - rollback):
```json
{
  "created": 0,
  "errors": [
    {"row": 3, "error": "Invalid username format."},
    {"row": 7, "error": "Username already exists."}
  ]
}
```

---

## Error Responses

All errors return JSON with a `detail` field:

```json
{
  "detail": "Error message here"
}
```

**Common HTTP Status Codes**:
| Status | Meaning |
|--------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Not authenticated |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists |
| 429 | Too Many Requests - Rate limited |
| 500 | Server Error - Internal error |
| 503 | Service Unavailable - Service temporarily down |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login attempts | 5 failures | Per IP+username |
| Activity saves | 60 | Per minute per user |
| Python executions | 30 | Per minute per user |

When rate limited, response is HTTP 429 with:
```json
{
  "detail": "Too many requests. Limit: X per minute."
}
```

---

## Data Validation

### Lesson ID Format
Pattern: `^lesson-\d+$`
Examples: `lesson-1`, `lesson-12`

### Activity ID Format
Pattern: `^a\d+$`
Examples: `a01`, `a15`

### Username Formats
- General: `^[a-z0-9._-]+$`
- Pupil: `^[a-z][a-z\-']*\.[a-z]$` (lastname.firstinitial)

### Timestamps
- Accept: Unix milliseconds or ISO 8601 strings
- Return: ISO 8601 with timezone (`+00:00`)

---

**Last Updated**: 2026-01-11
**API Version**: 1.1.0
