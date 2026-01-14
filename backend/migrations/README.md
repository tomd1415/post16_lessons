# Database Migration: Enhanced Teacher Features

This migration adds support for:
- **ActivityFeedback**: Teacher comments visible to pupils
- **Extended ActivityMark**: Answer-level marking, scores, and attempt tracking

## Prerequisites

- Docker containers running (`docker compose up -d`)
- Access to the server/machine running the containers

## Migration Steps

### Step 1: Check containers are running

```bash
cd /home/duguid/projects/post16_lessons
docker compose ps
```

You should see `api` and `db` services running. If not:

```bash
docker compose up -d
```

### Step 2: Connect to the database

```bash
docker compose exec db psql -U tlac -d tlac
```

### Step 3: Run the migration SQL

Paste the following SQL into the psql prompt:

```sql
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

ALTER TABLE activity_marks ADD COLUMN IF NOT EXISTS answer_marks JSONB;
ALTER TABLE activity_marks ADD COLUMN IF NOT EXISTS score INTEGER;
ALTER TABLE activity_marks ADD COLUMN IF NOT EXISTS max_score INTEGER;
ALTER TABLE activity_marks ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0;
ALTER TABLE activity_marks ADD COLUMN IF NOT EXISTS first_save_at TIMESTAMPTZ;
ALTER TABLE activity_marks ADD COLUMN IF NOT EXISTS last_save_at TIMESTAMPTZ;
```

### Step 4: Exit psql and restart the API

```bash
\q
docker compose restart api
```

### Step 5: Verify

Check logs for any errors:

```bash
docker compose logs api --tail=50
```

## What This Migration Adds

### New Table: `activity_feedback`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | The pupil receiving feedback |
| lesson_id | VARCHAR(64) | Lesson identifier |
| activity_id | VARCHAR(64) | Activity identifier (nullable for lesson-level feedback) |
| feedback_text | TEXT | The feedback content |
| teacher_id | UUID | The teacher who wrote the feedback |
| created_at | TIMESTAMPTZ | When feedback was created |
| updated_at | TIMESTAMPTZ | When feedback was last updated |

### New Columns on `activity_marks`

| Column | Type | Description |
|--------|------|-------------|
| answer_marks | JSONB | Per-answer marking data `{"q1": {"correct": true, "attempts": 2}}` |
| score | INTEGER | Number of correct answers |
| max_score | INTEGER | Total number of marked answers |
| attempt_count | INTEGER | How many times the pupil saved their work |
| first_save_at | TIMESTAMPTZ | When the pupil first saved |
| last_save_at | TIMESTAMPTZ | When the pupil last saved |

## Troubleshooting

### "relation already exists" error
This is safe to ignore - it means the table/column already exists.

### "column already exists" error
This is safe to ignore - the `IF NOT EXISTS` clause handles this.

### API still showing errors after migration
Try a full restart:
```bash
docker compose down
docker compose up -d
```
