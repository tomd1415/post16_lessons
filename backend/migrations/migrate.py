#!/usr/bin/env python3
"""
Database migration script for enhanced teacher features.
Run from the backend directory: python -m migrations.migrate
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db import engine


def run_migration():
    """Add new tables and columns for enhanced teacher features."""

    print("Running migration: Enhanced Teacher Features")
    print("=" * 50)

    with engine.connect() as conn:
        # Check if PostgreSQL or SQLite
        dialect = engine.dialect.name
        print(f"Database dialect: {dialect}")

        if dialect == "postgresql":
            # Create activity_feedback table
            print("\n1. Creating activity_feedback table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS activity_feedback (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    lesson_id VARCHAR(64) NOT NULL,
                    activity_id VARCHAR(64),
                    feedback_text TEXT NOT NULL,
                    teacher_id UUID NOT NULL REFERENCES users(id),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT uq_activity_feedback UNIQUE (user_id, lesson_id, activity_id)
                )
            """))
            print("   Done.")

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_activity_feedback_user_id
                ON activity_feedback(user_id)
            """))
            print("   Index created.")

            # Add columns to activity_marks
            print("\n2. Adding columns to activity_marks table...")

            columns = [
                ("answer_marks", "JSONB"),
                ("score", "INTEGER"),
                ("max_score", "INTEGER"),
                ("attempt_count", "INTEGER NOT NULL DEFAULT 0"),
                ("first_save_at", "TIMESTAMPTZ"),
                ("last_save_at", "TIMESTAMPTZ"),
            ]

            for col_name, col_type in columns:
                try:
                    # Check if column exists
                    result = conn.execute(text(f"""
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'activity_marks' AND column_name = '{col_name}'
                    """))
                    if result.fetchone() is None:
                        conn.execute(text(f"""
                            ALTER TABLE activity_marks ADD COLUMN {col_name} {col_type}
                        """))
                        print(f"   Added column: {col_name}")
                    else:
                        print(f"   Column exists: {col_name}")
                except Exception as e:
                    print(f"   Warning for {col_name}: {e}")

        else:
            # SQLite version
            print("\n1. Creating activity_feedback table...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS activity_feedback (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    lesson_id TEXT NOT NULL,
                    activity_id TEXT,
                    feedback_text TEXT NOT NULL,
                    teacher_id TEXT NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE (user_id, lesson_id, activity_id)
                )
            """))
            print("   Done.")

            print("\n2. Adding columns to activity_marks table...")
            columns = [
                ("answer_marks", "TEXT"),
                ("score", "INTEGER"),
                ("max_score", "INTEGER"),
                ("attempt_count", "INTEGER DEFAULT 0"),
                ("first_save_at", "TEXT"),
                ("last_save_at", "TEXT"),
            ]

            for col_name, col_type in columns:
                try:
                    conn.execute(text(f"""
                        ALTER TABLE activity_marks ADD COLUMN {col_name} {col_type}
                    """))
                    print(f"   Added column: {col_name}")
                except Exception as e:
                    if "duplicate column" in str(e).lower():
                        print(f"   Column exists: {col_name}")
                    else:
                        print(f"   Warning for {col_name}: {e}")

        conn.commit()

    print("\n" + "=" * 50)
    print("Migration complete!")


if __name__ == "__main__":
    run_migration()
