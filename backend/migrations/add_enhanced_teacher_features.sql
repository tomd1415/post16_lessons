-- Migration: Add enhanced teacher features
-- Run this against your database to add:
-- 1. New ActivityFeedback table
-- 2. New columns on ActivityMark table

-- Create activity_feedback table if not exists
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
);

CREATE INDEX IF NOT EXISTS ix_activity_feedback_user_id ON activity_feedback(user_id);

-- Add new columns to activity_marks table (ignore errors if they already exist)
DO $$
BEGIN
    -- Add answer_marks column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'activity_marks' AND column_name = 'answer_marks') THEN
        ALTER TABLE activity_marks ADD COLUMN answer_marks JSONB;
    END IF;

    -- Add score column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'activity_marks' AND column_name = 'score') THEN
        ALTER TABLE activity_marks ADD COLUMN score INTEGER;
    END IF;

    -- Add max_score column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'activity_marks' AND column_name = 'max_score') THEN
        ALTER TABLE activity_marks ADD COLUMN max_score INTEGER;
    END IF;

    -- Add attempt_count column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'activity_marks' AND column_name = 'attempt_count') THEN
        ALTER TABLE activity_marks ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0;
    END IF;

    -- Add first_save_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'activity_marks' AND column_name = 'first_save_at') THEN
        ALTER TABLE activity_marks ADD COLUMN first_save_at TIMESTAMPTZ;
    END IF;

    -- Add last_save_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'activity_marks' AND column_name = 'last_save_at') THEN
        ALTER TABLE activity_marks ADD COLUMN last_save_at TIMESTAMPTZ;
    END IF;
END $$;

-- Verify the changes
SELECT 'Migration complete. Tables and columns added successfully.' AS status;
