import argparse
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_

from .config import RETENTION_YEARS
from .db import SessionLocal
from .models import ActivityMark, ActivityRevision, ActivityState, AuditLog, Session as AuthSession, User


def ensure_utc(value):
    if not value:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_iso(value):
    if not value:
        return None
    try:
        if len(value) == 10:
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def retention_cutoff(years=RETENTION_YEARS, now=None, cutoff_override=None):
    if cutoff_override:
        return cutoff_override
    now = ensure_utc(now) or datetime.now(timezone.utc)
    return now - timedelta(days=365 * years)


def latest_activity_for_user(db, user):
    timestamps = []
    for value in (user.last_login_at, user.created_at):
        value = ensure_utc(value)
        if value:
            timestamps.append(value)

    state_time = db.query(func.max(ActivityState.updated_at)).filter(ActivityState.user_id == user.id).scalar()
    revision_time = db.query(func.max(ActivityRevision.created_at)).filter(ActivityRevision.user_id == user.id).scalar()
    for value in (state_time, revision_time):
        value = ensure_utc(value)
        if value:
            timestamps.append(value)

    return max(timestamps) if timestamps else None


def collect_retention_targets(db, cutoff, include_staff=False):
    roles = ["pupil"] if not include_staff else ["pupil", "teacher", "admin"]
    users = db.query(User).filter(User.role.in_(roles)).all()
    targets = []
    for user in users:
        last_activity = latest_activity_for_user(db, user)
        if last_activity and last_activity < cutoff:
            targets.append({"user": user, "last_activity": last_activity})
    targets.sort(key=lambda item: (item["last_activity"], item["user"].username))
    return targets


def retention_counts(db, user_ids):
    if not user_ids:
        return {
            "users": 0,
            "sessions": 0,
            "activity_states": 0,
            "activity_revisions": 0,
            "activity_marks": 0,
            "audit_logs": 0,
        }
    return {
        "users": db.query(User).filter(User.id.in_(user_ids)).count(),
        "sessions": db.query(AuthSession).filter(AuthSession.user_id.in_(user_ids)).count(),
        "activity_states": db.query(ActivityState).filter(ActivityState.user_id.in_(user_ids)).count(),
        "activity_revisions": db.query(ActivityRevision).filter(ActivityRevision.user_id.in_(user_ids)).count(),
        "activity_marks": db.query(ActivityMark).filter(ActivityMark.user_id.in_(user_ids)).count(),
        "audit_logs": db.query(AuditLog)
        .filter(or_(AuditLog.actor_user_id.in_(user_ids), AuditLog.target_user_id.in_(user_ids)))
        .count(),
    }


def purge_users(db, user_ids):
    if not user_ids:
        return retention_counts(db, user_ids)
    counts = {
        "activity_revisions": db.query(ActivityRevision)
        .filter(ActivityRevision.user_id.in_(user_ids))
        .delete(synchronize_session=False),
        "activity_states": db.query(ActivityState)
        .filter(ActivityState.user_id.in_(user_ids))
        .delete(synchronize_session=False),
        "activity_marks": db.query(ActivityMark)
        .filter(ActivityMark.user_id.in_(user_ids))
        .delete(synchronize_session=False),
        "sessions": db.query(AuthSession)
        .filter(AuthSession.user_id.in_(user_ids))
        .delete(synchronize_session=False),
        "audit_logs": db.query(AuditLog)
        .filter(or_(AuditLog.actor_user_id.in_(user_ids), AuditLog.target_user_id.in_(user_ids)))
        .delete(synchronize_session=False),
        "users": db.query(User)
        .filter(User.id.in_(user_ids))
        .delete(synchronize_session=False),
    }
    db.commit()
    return counts


def serialize_targets(targets, limit):
    if limit is None:
        limit = len(targets)
    output = []
    for item in targets[:limit]:
        user = item["user"]
        output.append(
            {
                "username": user.username,
                "name": user.name,
                "role": user.role,
                "cohort_year": user.cohort_year,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_activity_at": item["last_activity"].isoformat() if item["last_activity"] else None,
            }
        )
    return output


def run_retention(dry_run=True, include_staff=False, years=RETENTION_YEARS, cutoff_override=None, sample=20):
    db = SessionLocal()
    try:
        cutoff = retention_cutoff(years=years, cutoff_override=cutoff_override)
        targets = collect_retention_targets(db, cutoff, include_staff=include_staff)
        user_ids = [item["user"].id for item in targets]
        counts = retention_counts(db, user_ids)
        report = {
            "mode": "dry-run" if dry_run else "apply",
            "cutoff": cutoff.isoformat(),
            "include_staff": include_staff,
            "target_count": len(targets),
            "counts": counts,
            "sample": serialize_targets(targets, sample),
        }
        if not dry_run:
            report["deleted"] = purge_users(db, user_ids)
        return report
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Retention purge job for TLAC.")
    parser.add_argument("--apply", action="store_true", help="Delete records instead of dry-run.")
    parser.add_argument("--include-staff", action="store_true", help="Include teacher/admin accounts.")
    parser.add_argument("--years", type=int, default=RETENTION_YEARS, help="Retention window in years.")
    parser.add_argument("--cutoff-date", type=str, default="", help="Override cutoff date (YYYY-MM-DD or ISO).")
    parser.add_argument("--sample", type=int, default=20, help="Max sample users to print.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    cutoff_override = parse_iso(args.cutoff_date)
    report = run_retention(
        dry_run=not args.apply,
        include_staff=args.include_staff,
        years=args.years,
        cutoff_override=cutoff_override,
        sample=args.sample,
    )

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print(f"Retention cutoff: {report['cutoff']}")
    print(f"Mode: {report['mode']}")
    print(f"Targets: {report['target_count']}")
    print("Counts:")
    for key, value in report["counts"].items():
        print(f"  {key}: {value}")
    if report["sample"]:
        print("Sample targets:")
        for item in report["sample"]:
            print(
                f"  {item['username']} ({item['role']}) last activity {item['last_activity_at']}"
            )
    if "deleted" in report:
        print("Deleted:")
        for key, value in report["deleted"].items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
