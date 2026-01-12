# Assessment System - Change Log

This document tracks all modifications, additions, and customisations made to the assessment system prompt documents. Use this to understand what has changed from base specifications and why.

## How to Use This Document

When reading the prompt documents, check here first to understand:
- What customisations have been applied
- Why specific design decisions were made
- Which documents have been modified

When making changes:
1. Add a new entry under the relevant section
2. Reference the specific file(s) and section(s) modified
3. Explain the rationale
4. Note any knock-on effects to other documents

---

## School Context

| Setting | Value |
|---------|-------|
| School type | UK secondary school, specialist provision |
| Year groups | Year 7-9 (KS3, ages 11-14) |
| Class sizes | Up to 15 pupils |
| Pupil needs | All pupils have communication difficulties (ASC, ADHD, similar) |
| Hardware | Windows PCs (pupils and teachers) |
| Network | Internal network, IP-based access (no public domain) |
| Collaboration | Microsoft Teams |
| Curriculum | NCCE Teach Computing |

---

## Change History

### 2024-XX-XX: Initial Setup

**Documents created:**
- `00-overview.md` - System overview and navigation guide
- `01-system-architecture.md` - Technical stack and deployment
- `02-question-types.md` - 14 question type specifications
- `03-ai-generation.md` - OpenAI integration and prompts
- `04-database-schema.md` - PostgreSQL schema design
- `05-api-endpoints.md` - REST API specification
- `06-teacher-dashboard.md` - Teacher interface wireframes
- `07-pupil-interface.md` - Pupil assessment experience
- `08-document-processing.md` - NCCE document parsing
- `09-marking-feedback.md` - Auto-marking and feedback logic
- `10-example-workflow.md` - End-to-end example

---

### 2024-XX-XX: Platform Configuration

**Files modified:** `00-overview.md`, `01-system-architecture.md`

**Changes:**
- Changed from Chromebooks to Windows PCs
- Changed from Google Workspace to Microsoft Teams
- Updated class size reference to "up to 15 pupils"

**Rationale:** Reflects actual school infrastructure.

---

### 2024-XX-XX: AI Model Update

**Files modified:** `03-ai-generation.md`

**Changes:**
- Updated model from `gpt-4o` to `gpt-5.2`
- Using OpenAI `responses` endpoint for structured output

**Rationale:** Newer model available with better structured output support.

---

### 2024-XX-XX: Multiple Attempts Support

**Files modified:** `04-database-schema.md`

**Changes:**
- Added `attempt_number` field to `attempts` table
- Added `max_attempts`, `allow_question_retry`, `max_question_retries` to `assessments` table
- Created `answer_history` table to track every submission

**Rationale:** Teachers need to see all attempts, not just final answers. Supports retry-based learning approach.

**Schema additions:**
```sql
-- In assessments table
max_attempts INTEGER DEFAULT 1,
allow_question_retry BOOLEAN DEFAULT TRUE,
max_question_retries INTEGER DEFAULT 3,

-- New table
CREATE TABLE answer_history (
    id UUID PRIMARY KEY,
    answer_id UUID REFERENCES answers(id),
    attempt_number INTEGER NOT NULL,
    answer_data JSONB NOT NULL,
    score DECIMAL(5,2),
    is_correct BOOLEAN,
    submitted_at TIMESTAMP WITH TIME ZONE
);
```

---

### 2024-XX-XX: NCCE Curriculum Integration

**Files modified:** `03-ai-generation.md`, `08-document-processing.md`

**Changes:**
- Added 10 taxonomy strands (NW, CM, DI, DD, CS, IT, AL, PG, ET, SS)
- Added curriculum map Excel parser
- Added unit zip file processor
- Documented NCCE folder structure

**Rationale:** School uses NCCE Teach Computing curriculum. Questions should be tagged with taxonomy strands for curriculum alignment.

---

### 2024-XX-XX: Accessibility for Autism/ADHD (CRITICAL)

**Files modified:** `00-overview.md`, `03-ai-generation.md`, `07-pupil-interface.md`

**Changes:**

#### 00-overview.md
Added "CRITICAL: Pupil Accessibility Needs" section establishing that ALL pupils have communication difficulties (autism, ADHD, similar). This is a fundamental design constraint.

#### 03-ai-generation.md
Added comprehensive "Accessibility for Autism/ADHD" section to AI system prompt:
- Language requirements (literal, short sentences, no idioms)
- Question structure (one concept, explicit formats, avoid negatives)
- Cognitive load limits (max 4 options, short code)
- Concrete examples requirement
- Accessible feedback patterns

#### 07-pupil-interface.md
Added detailed "Autism/ADHD Accessibility" section:
- Visual design (calm colours, no animations, consistent layout)
- Interface behaviour (no countdown timers, constant progress saving)
- Anxiety reduction features
- Sensory considerations with CSS example
- Communication clarity checklist

**Rationale:** All pupils at this school have communication difficulties. This is not an edge case - it's the primary user base. Every design decision must account for:
- Literal language interpretation
- Reduced cognitive load
- Predictability and consistency
- Anxiety reduction
- Sensory sensitivities
- Executive function support

**Impact:** This affects ALL other documents. When implementing any feature, verify it meets these accessibility requirements.

---

## Design Decisions Log

Record significant design choices and their rationale here.

### DD-001: No Red for Incorrect Answers

**Decision:** Use amber/orange instead of red for incorrect feedback.

**Rationale:** Red can trigger anxiety responses. Amber is still visually distinct but less alarming.

**Applies to:** `07-pupil-interface.md`, all frontend components

---

### DD-002: No Visible Countdown Timers

**Decision:** Do not show countdown timers by default. If time must be shown, use approximate language ("About 20 minutes remaining").

**Rationale:** Countdown timers cause significant anxiety for pupils with ADHD and autism. Time pressure impairs performance.

**Applies to:** `07-pupil-interface.md`, assessment taking interface

---

### DD-003: One Question Per Screen

**Decision:** Display only one question at a time, never multiple questions on screen.

**Rationale:** Reduces cognitive load, prevents overwhelm, maintains focus.

**Applies to:** `07-pupil-interface.md`, question rendering

---

### DD-004: Constant Progress Saving

**Decision:** Save after EVERY interaction, not just question submission.

**Rationale:** Reduces anxiety about losing work. Pupils need reassurance that progress is safe.

**Applies to:** `04-database-schema.md`, `05-api-endpoints.md`, frontend state management

---

### DD-005: Positive-Only Question Phrasing

**Decision:** Never use negative phrasing like "Which is NOT..." - always phrase positively.

**Rationale:** Negative phrasing causes confusion for pupils who interpret language literally.

**Applies to:** `03-ai-generation.md`, AI question generation

---

### DD-006: Maximum 4 Options for Multiple Choice

**Decision:** Limit multiple choice options to 4 maximum.

**Rationale:** More options increase cognitive load. 4 is sufficient for assessment validity.

**Applies to:** `02-question-types.md`, `03-ai-generation.md`

---

## Pending Decisions

Track decisions that need to be made or confirmed.

| ID | Topic | Options | Status |
|----|-------|---------|--------|
| PD-001 | Break functionality | How to implement "take a break" - pause timer? Save and exit? | Needs discussion |
| PD-002 | Audio support | Should questions have read-aloud option? | Needs discussion |
| PD-003 | Visual themes | Should pupils be able to choose colour themes? | Needs discussion |

---

## Validation Checklist

Before deploying any feature, verify:

### Accessibility
- [ ] Uses literal, clear language
- [ ] No idioms, metaphors, or sarcasm
- [ ] One instruction per sentence
- [ ] Icons have text labels
- [ ] No red for errors (use amber)
- [ ] No countdown timers visible
- [ ] Progress is constantly saved
- [ ] Calm colour palette used
- [ ] No animations (or respects prefers-reduced-motion)
- [ ] Consistent layout with existing screens

### Technical
- [ ] Works on Windows PCs
- [ ] Works on internal network (IP-based)
- [ ] Database schema supports feature
- [ ] API endpoints documented
- [ ] Error handling is graceful

---

## Document Dependencies

```
00-overview.md
    ├── Sets context for ALL other documents
    └── CRITICAL accessibility requirements apply everywhere

03-ai-generation.md
    ├── Depends on: 02-question-types.md (question schemas)
    ├── Depends on: 08-document-processing.md (input format)
    └── Feeds into: 04-database-schema.md (output storage)

07-pupil-interface.md
    ├── Depends on: 02-question-types.md (what to render)
    ├── Depends on: 05-api-endpoints.md (data fetching)
    └── Must follow: 00-overview.md accessibility requirements

09-marking-feedback.md
    ├── Depends on: 02-question-types.md (marking logic per type)
    └── Feeds into: 04-database-schema.md (score storage)
```

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| 1.0 | Initial | Base assessment system specification |
| 1.1 | - | Platform config (Windows/Teams) |
| 1.2 | - | AI model update (GPT-5.2) |
| 1.3 | - | Multiple attempts support |
| 1.4 | - | NCCE curriculum integration |
| 1.5 | - | Autism/ADHD accessibility (CRITICAL) |

---

## Notes for AI Assistants

When working with these documents:

1. **Always check this changelog first** - understand what customisations exist
2. **Accessibility is non-negotiable** - every feature must work for pupils with autism/ADHD
3. **Consistency matters** - follow established patterns and design decisions
4. **Update this log** - when you make changes, document them here
5. **Cross-reference** - changes often affect multiple documents

If asked to implement something that conflicts with the accessibility requirements, raise this with the user before proceeding.
