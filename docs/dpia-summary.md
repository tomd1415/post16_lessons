# DPIA support summary (TLAC platform)

This document summarizes personal data processing for DPIA support. It is a concise, practical aid for on-prem deployments.

## Purpose
- Deliver the ICDL "Thinking like a Coder" learning platform on a school server.
- Provide pupil learning activities, teacher review workflows, and reporting.

## Data processed
Pupil data:
- Name
- Username (lastname.firstinitial)
- Cohort/year of course
- Teacher notes (private to staff)
- Activity state and revision history (learning evidence)

Staff data:
- Name
- Username
- Role (teacher/admin)

System data:
- Session identifiers, CSRF tokens
- IP address and user-agent for audit events (staff actions only)

## Storage and access
- Data stored in Postgres on the school server.
- Link override data stored in `data/link-overrides.json`.
- Access is role-based: pupils see only their own work; teachers/admins see pupil work and dashboards.
- No parent/guardian access.

## Retention
- Default retention is 2 years after last activity.
- Retention purge job supports dry-run and apply modes (see `scripts/retention_purge.sh`).
- Data is deleted rather than exported by default.

## Security and safeguarding
- TLS termination via Caddy (internal CA).
- Secure session cookies (HttpOnly, Secure, SameSite=Lax).
- Passwords hashed with Argon2id.
- CSRF protection on state-changing endpoints.
- Rate limiting on login attempts.
- No third-party tracking or analytics.

## Audit and monitoring
- Audit log records teacher/admin actions (user creation, marking, notes, link overrides).
- Health and metrics endpoints support monitoring (`/api/health`, `/api/metrics`).

## Accessibility
- UI aims to meet UK public sector accessibility expectations and WCAG 2.2 AA where practical.

## Notes
- The platform is designed for minimal data collection and on-prem operation.
- If data categories change (e.g., uploads), update this summary and retention procedures.
