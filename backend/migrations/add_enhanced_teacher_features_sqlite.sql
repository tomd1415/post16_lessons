-- Migration: Add enhanced teacher features (SQLite version)
-- Run this against your SQLite database

-- Create activity_feedback table if not exists
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
);

CREATE INDEX IF NOT EXISTS ix_activity_feedback_user_id ON activity_feedback(user_id);

-- SQLite doesn't support ADD COLUMN IF NOT EXISTS, so these may error if columns exist
-- Run each separately and ignore "duplicate column name" errors

-- ALTER TABLE activity_marks ADD COLUMN answer_marks TEXT;
-- ALTER TABLE activity_marks ADD COLUMN score INTEGER;
-- ALTER TABLE activity_marks ADD COLUMN max_score INTEGER;
-- ALTER TABLE activity_marks ADD COLUMN attempt_count INTEGER DEFAULT 0;
-- ALTER TABLE activity_marks ADD COLUMN first_save_at TEXT;
-- ALTER TABLE activity_marks ADD COLUMN last_save_at TEXT;
