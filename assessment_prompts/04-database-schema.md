# Database Schema

PostgreSQL database schema for the KS3 Assessment System.

## Entity Relationship Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Teacher   │────<│  Assessment  │>────│    Unit     │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────┴─────┐ ┌─────┴─────┐
              │ Question  │ │  Attempt  │
              └───────────┘ └───────────┘
                                 │
                           ┌─────┴─────┐
                           │  Answer   │
                           └───────────┘
                                 │
                           ┌─────┴─────┐
                           │   Pupil   │>────┌───────────┐
                           └───────────┘     │  Class    │
                                             └───────────┘
```

## Tables

### Users

```sql
-- Teachers can create assessments and view analytics
CREATE TABLE teachers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

-- Pupils take assessments
CREATE TABLE pupils (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    year_group INTEGER NOT NULL CHECK (year_group BETWEEN 7 AND 9),
    class_id UUID REFERENCES classes(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Classes group pupils
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL,  -- e.g., "7A", "8CS1"
    year_group INTEGER NOT NULL CHECK (year_group BETWEEN 7 AND 9),
    teacher_id UUID REFERENCES teachers(id),
    academic_year VARCHAR(10) NOT NULL,  -- e.g., "2024-25"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Teacher-class many-to-many (teachers can have multiple classes)
CREATE TABLE teacher_classes (
    teacher_id UUID REFERENCES teachers(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    PRIMARY KEY (teacher_id, class_id)
);
```

### Sessions

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('teacher', 'pupil')),
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);
```

### Units and Topics

```sql
-- Units represent a half-term of learning
CREATE TABLE units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    year_group INTEGER NOT NULL CHECK (year_group BETWEEN 7 AND 9),
    half_term INTEGER NOT NULL CHECK (half_term BETWEEN 1 AND 6),
    academic_year VARCHAR(10) NOT NULL,
    created_by UUID REFERENCES teachers(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Topics within a unit
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID REFERENCES units(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Learning objectives for each topic
CREATE TABLE learning_objectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    code VARCHAR(20),  -- e.g., "LO1", "LO2"
    description TEXT NOT NULL,
    order_index INTEGER NOT NULL
);

-- Uploaded lesson documents
CREATE TABLE unit_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID REFERENCES units(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL CHECK (file_type IN ('docx', 'pptx', 'pdf')),
    extracted_text TEXT,  -- Parsed content
    uploaded_by UUID REFERENCES teachers(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Assessments

```sql
CREATE TYPE assessment_status AS ENUM ('draft', 'review', 'published', 'archived');

CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    unit_id UUID REFERENCES units(id),
    year_group INTEGER NOT NULL CHECK (year_group BETWEEN 7 AND 9),

    -- AI generation metadata
    generation_prompt TEXT,  -- Teacher's special instructions
    ai_model VARCHAR(50),
    generated_at TIMESTAMP WITH TIME ZONE,

    -- Status
    status assessment_status DEFAULT 'draft',
    published_at TIMESTAMP WITH TIME ZONE,

    -- Settings
    time_limit_minutes INTEGER,
    allow_hints BOOLEAN DEFAULT TRUE,
    show_immediate_feedback BOOLEAN DEFAULT FALSE,
    randomize_questions BOOLEAN DEFAULT FALSE,
    randomize_options BOOLEAN DEFAULT TRUE,
    max_attempts INTEGER DEFAULT 1,  -- How many times pupil can attempt the whole assessment
    allow_question_retry BOOLEAN DEFAULT TRUE,  -- Can retry individual questions within an attempt
    max_question_retries INTEGER DEFAULT 3,  -- Max retries per question (0 = unlimited)

    -- Metadata
    total_points INTEGER,
    estimated_duration_minutes INTEGER,
    created_by UUID REFERENCES teachers(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Which classes can access an assessment
CREATE TABLE assessment_classes (
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    class_id UUID REFERENCES classes(id) ON DELETE CASCADE,
    available_from TIMESTAMP WITH TIME ZONE,
    available_until TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (assessment_id, class_id)
);

CREATE INDEX idx_assessments_status ON assessments(status);
CREATE INDEX idx_assessments_unit ON assessments(unit_id);
```

### Questions

```sql
CREATE TYPE question_type AS ENUM (
    'multiple_choice', 'multiple_select', 'text_input', 'extended_text',
    'matching', 'ordering', 'parsons', 'code_completion', 'python_code',
    'code_debug', 'trace_table', 'drag_label', 'binary_convert', 'logic_gates'
);

CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL,

    -- Question content
    type question_type NOT NULL,
    question_text TEXT NOT NULL,
    question_html TEXT,  -- Optional rich text version
    image_url VARCHAR(500),

    -- Type-specific data stored as JSONB
    type_data JSONB NOT NULL,

    -- Scoring
    difficulty INTEGER NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
    points INTEGER NOT NULL DEFAULT 1,
    time_estimate_seconds INTEGER,

    -- Support
    hint TEXT,
    scaffold JSONB,  -- Easier version of question

    -- Feedback templates
    feedback_correct TEXT NOT NULL,
    feedback_incorrect TEXT NOT NULL,
    feedback_partial TEXT,

    -- Metadata
    topic_id UUID REFERENCES topics(id),
    learning_objective_id UUID REFERENCES learning_objectives(id),
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_questions_assessment ON questions(assessment_id);
CREATE INDEX idx_questions_type ON questions(type);
CREATE INDEX idx_questions_difficulty ON questions(difficulty);
CREATE INDEX idx_questions_tags ON questions USING GIN(tags);
```

### Question Type Data Examples

The `type_data` JSONB field stores type-specific data:

```sql
-- Multiple Choice
{
    "options": [
        {"id": "a", "text": "Option A", "is_correct": true},
        {"id": "b", "text": "Option B", "is_correct": false}
    ],
    "shuffle_options": true
}

-- Python Code
{
    "starter_code": "def add(a, b):\n    pass",
    "test_cases": [
        {"input": "add(1, 2)", "expected": "3", "visible": true},
        {"input": "add(-1, 1)", "expected": "0", "visible": false}
    ],
    "banned_keywords": ["eval"],
    "required_keywords": ["return"],
    "time_limit_seconds": 5
}

-- Matching
{
    "left_items": [{"id": "l1", "text": "CPU"}],
    "right_items": [{"id": "r1", "text": "Processor"}],
    "correct_pairs": [{"left": "l1", "right": "r1"}]
}

-- Parsons
{
    "blocks": [
        {"id": "b1", "code": "for i in range(5):", "indent": 0},
        {"id": "b2", "code": "print(i)", "indent": 1}
    ],
    "solution": [{"block_id": "b1", "indent": 0}, {"block_id": "b2", "indent": 1}],
    "enable_indentation": true
}
```

### Attempts and Answers

```sql
CREATE TYPE attempt_status AS ENUM ('in_progress', 'completed', 'abandoned');

CREATE TABLE attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    pupil_id UUID REFERENCES pupils(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL DEFAULT 1,  -- Allows multiple attempts if teacher permits

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    time_taken_seconds INTEGER,

    -- Results
    status attempt_status DEFAULT 'in_progress',
    total_score DECIMAL(5,2),
    max_score INTEGER,
    percentage DECIMAL(5,2),

    -- Metadata
    ip_address INET,
    user_agent TEXT,

    -- Allow multiple attempts per pupil (attempt_number distinguishes them)
    UNIQUE(assessment_id, pupil_id, attempt_number)
);

CREATE TABLE answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES attempts(id) ON DELETE CASCADE,
    question_id UUID REFERENCES questions(id) ON DELETE CASCADE,

    -- Answer data (varies by question type)
    answer_data JSONB NOT NULL,

    -- Scoring
    score DECIMAL(5,2),
    max_score INTEGER,
    is_correct BOOLEAN,

    -- Timing and behavior
    time_taken_seconds INTEGER,
    attempts_count INTEGER DEFAULT 1,
    hint_used BOOLEAN DEFAULT FALSE,
    scaffold_used BOOLEAN DEFAULT FALSE,

    -- Feedback shown
    feedback_shown TEXT,

    -- Timestamps
    first_answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(attempt_id, question_id)
);

CREATE INDEX idx_attempts_pupil ON attempts(pupil_id);
CREATE INDEX idx_attempts_assessment ON attempts(assessment_id);
CREATE INDEX idx_answers_attempt ON answers(attempt_id);
CREATE INDEX idx_answers_question ON answers(question_id);
```

### Answer Data Examples

```sql
-- Multiple Choice
{"selected_option": "a"}

-- Multiple Select
{"selected_options": ["a", "c", "d"]}

-- Text Input
{"text": "RAM"}

-- Python Code
{
    "code": "def add(a, b):\n    return a + b",
    "test_results": [
        {"input": "add(1,2)", "expected": "3", "actual": "3", "passed": true}
    ]
}

-- Matching
{"pairs": [{"left": "l1", "right": "r1"}, {"left": "l2", "right": "r2"}]}

-- Ordering
{"order": ["item3", "item1", "item2", "item4"]}

-- Parsons
{"blocks": [{"block_id": "b1", "indent": 0}, {"block_id": "b2", "indent": 1}]}
```

### Answer History (for tracking every submission)

```sql
-- Track every answer submission for detailed analytics
-- This allows seeing what pupils tried before getting the right answer
CREATE TABLE answer_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_id UUID REFERENCES answers(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,  -- 1, 2, 3... for this question
    answer_data JSONB NOT NULL,
    score DECIMAL(5,2),
    is_correct BOOLEAN,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_answer_history_answer ON answer_history(answer_id);
CREATE INDEX idx_answer_history_submitted ON answer_history(submitted_at);
```

This allows tracking:
- What a pupil answered on each try
- How many attempts before getting correct
- Time between attempts
- Patterns in wrong answers

### Analytics and Audit

```sql
-- Track AI usage for cost management
CREATE TABLE ai_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID REFERENCES teachers(id),
    model VARCHAR(50) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    operation VARCHAR(50) NOT NULL,  -- 'generate_assessment', 'regenerate_question', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log for important actions
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    user_type VARCHAR(10),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

-- Aggregated statistics (updated periodically)
CREATE TABLE assessment_statistics (
    assessment_id UUID PRIMARY KEY REFERENCES assessments(id) ON DELETE CASCADE,
    attempts_count INTEGER DEFAULT 0,
    completions_count INTEGER DEFAULT 0,
    average_score DECIMAL(5,2),
    median_score DECIMAL(5,2),
    std_deviation DECIMAL(5,2),
    average_time_seconds INTEGER,
    question_stats JSONB,  -- Per-question statistics
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE question_statistics (
    question_id UUID PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
    attempts_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    partial_count INTEGER DEFAULT 0,
    incorrect_count INTEGER DEFAULT 0,
    hint_usage_count INTEGER DEFAULT 0,
    scaffold_usage_count INTEGER DEFAULT 0,
    average_time_seconds INTEGER,
    -- For multiple choice: track which options were selected
    option_distribution JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Migrations

Use Alembic for database migrations:

```python
# alembic/versions/001_initial_schema.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create enum types
    op.execute("CREATE TYPE assessment_status AS ENUM ('draft', 'review', 'published', 'archived')")
    op.execute("CREATE TYPE question_type AS ENUM (...)")
    op.execute("CREATE TYPE attempt_status AS ENUM ('in_progress', 'completed', 'abandoned')")

    # Create tables in order (respecting foreign keys)
    op.create_table('teachers', ...)
    op.create_table('classes', ...)
    # ... etc

def downgrade():
    # Drop in reverse order
    op.drop_table('answers')
    op.drop_table('attempts')
    # ... etc
    op.execute("DROP TYPE assessment_status")
    # ... etc
```

## SQLAlchemy Models

```python
# backend/app/models/assessment.py

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from ..db import Base

class AssessmentStatus(enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("units.id"))
    year_group = Column(Integer, nullable=False)

    generation_prompt = Column(Text)
    ai_model = Column(String(50))
    generated_at = Column(TIMESTAMP(timezone=True))

    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.DRAFT)
    published_at = Column(TIMESTAMP(timezone=True))

    time_limit_minutes = Column(Integer)
    allow_hints = Column(Boolean, default=True)
    show_immediate_feedback = Column(Boolean, default=False)
    randomize_questions = Column(Boolean, default=False)
    randomize_options = Column(Boolean, default=True)

    total_points = Column(Integer)
    estimated_duration_minutes = Column(Integer)

    created_by = Column(UUID(as_uuid=True), ForeignKey("teachers.id"))
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    unit = relationship("Unit", back_populates="assessments")
    questions = relationship("Question", back_populates="assessment", order_by="Question.order_index")
    attempts = relationship("Attempt", back_populates="assessment")
    creator = relationship("Teacher", back_populates="assessments")
```

## Indexes for Performance

```sql
-- For teacher dashboard queries
CREATE INDEX idx_attempts_assessment_completed ON attempts(assessment_id, completed_at)
    WHERE status = 'completed';

-- For pupil progress queries
CREATE INDEX idx_attempts_pupil_completed ON attempts(pupil_id, completed_at DESC);

-- For question analysis
CREATE INDEX idx_answers_question_correct ON answers(question_id, is_correct);

-- For finding assessments by class
CREATE INDEX idx_assessment_classes_class ON assessment_classes(class_id);

-- Full-text search on questions (optional)
CREATE INDEX idx_questions_search ON questions
    USING GIN(to_tsvector('english', question_text));
```

## Data Retention

```sql
-- Archive old attempts after academic year
CREATE TABLE archived_attempts (
    -- Same structure as attempts
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to archive old data
CREATE OR REPLACE FUNCTION archive_old_attempts()
RETURNS void AS $$
BEGIN
    INSERT INTO archived_attempts
    SELECT *, NOW() as archived_at
    FROM attempts
    WHERE completed_at < NOW() - INTERVAL '2 years';

    DELETE FROM attempts
    WHERE completed_at < NOW() - INTERVAL '2 years';
END;
$$ LANGUAGE plpgsql;
```
