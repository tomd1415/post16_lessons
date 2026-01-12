# KS3 Computing Assessment System - Prompt Overview

This folder contains prompts and specifications for building an AI-powered assessment generation system for KS3 Computing (Years 7-9).

## System Concept

Teachers upload lesson plans (.docx) and resources (.pptx) for a unit, provide any additional context, and the AI generates a complete, differentiated assessment covering the unit's learning objectives.

## How These Documents Work Together

```
CHANGELOG.md                <- IMPORTANT: Read this first! Tracks all modifications
00-overview.md              <- You are here. Start here for context.
01-system-architecture.md   <- Technical stack, project structure, deployment
02-question-types.md        <- All question type specifications with examples
03-ai-generation.md         <- How the AI generates assessments from lesson plans
04-database-schema.md       <- Database tables and relationships
05-api-endpoints.md         <- REST API design
06-teacher-dashboard.md     <- Teacher interface requirements
07-pupil-interface.md       <- Pupil assessment-taking interface
08-document-processing.md   <- Parsing .docx and .pptx files
09-marking-feedback.md      <- Auto-marking and feedback generation
10-example-workflow.md      <- End-to-end example of creating an assessment
```

## For the AI Building This System

**IMPORTANT:** Always read `CHANGELOG.md` first! It tracks all customisations, design decisions, and modifications made to these documents.

If you're an AI assistant helping to build this system, use these documents as follows:

| When the user asks about... | Read this document |
|---|---|
| What has changed, design decisions, customisations | `CHANGELOG.md` |
| Project setup, tech stack, folder structure | `01-system-architecture.md` |
| What question types to support | `02-question-types.md` |
| How to generate questions from lesson plans | `03-ai-generation.md` |
| Database design or data models | `04-database-schema.md` |
| API routes or backend endpoints | `05-api-endpoints.md` |
| Teacher features, analytics, dashboards | `06-teacher-dashboard.md` |
| Pupil experience, assessment interface | `07-pupil-interface.md` |
| Processing Word/PowerPoint files | `08-document-processing.md` |
| Marking logic, feedback, scoring | `09-marking-feedback.md` |
| A complete example | `10-example-workflow.md` |

## Quick Start for Developers

### Tech Stack
- **Backend**: Python 3.11+ with FastAPI
- **Database**: PostgreSQL 15+
- **Frontend**: Vanilla JavaScript (no frameworks)
- **AI**: OpenAI API (GPT-5.2 / GPT-5.1 via `responses` endpoint)
- **Document Processing**: python-docx, python-pptx
- **Containerisation**: Docker with Docker Compose
- **Reverse Proxy**: Caddy

### Key Design Principles

1. **AI-Generated Content**: The AI creates assessment questions from teacher-provided lesson materials
2. **Teacher Control**: Teachers can review, edit, and approve AI-generated content before publishing
3. **Inclusive Design**: Questions scaffold from accessible to challenging; no pupil should feel they "failed"
4. **Comprehensive Tracking**: Record every interaction for teacher analytics and trend analysis
5. **Privacy First**: GDPR compliant, minimal data collection, secure by default

### CRITICAL: Pupil Accessibility Needs

**All pupils at this school have communication difficulties**, primarily:
- **Autism Spectrum Condition (ASC)**
- **ADHD**
- **Related communication and processing differences**

This fundamentally shapes how assessments must be designed:

| Need | Design Response |
|------|-----------------|
| Clear, literal language | Avoid idioms, sarcasm, metaphors, ambiguous phrasing |
| Reduced cognitive load | One question per screen, minimal visual clutter, no distractions |
| Predictable structure | Consistent layout across all questions, clear expectations upfront |
| Processing time | Generous time limits (or untimed), no visible countdown pressure |
| Sensory considerations | Calm colours, no flashing/animations, quiet interface |
| Explicit instructions | Tell them exactly what to do - never assume understanding |
| Concrete examples | Use specific, real-world examples they can visualise |
| Positive reinforcement | Celebrate effort and progress, not just correctness |
| Anxiety reduction | Save progress constantly, allow breaks, no sudden surprises |
| Executive function support | Clear start/stop points, visual progress indicators |
| Transition support | Warn before assessment ends, clear "what happens next" |

**This applies to ALL documents in this folder** - every component must consider these needs.

### Core User Journeys

**Teacher Journey:**
1. Upload lesson plan documents for a unit
2. Add any special instructions (e.g., "Focus on binary conversion", "Include more debugging questions")
3. AI generates draft assessment
4. Teacher reviews, edits if needed, approves
5. Publish assessment to specific classes
6. View results and analytics after pupils complete

**Pupil Journey:**
1. Log in and see available assessments
2. Start assessment - questions presented one at a time or in sections
3. Answer questions with immediate or delayed feedback (teacher choice)
4. Use hints/scaffolds if struggling (usage tracked but not penalised)
5. Complete assessment and see encouraging summary
6. View own progress over time

## Project Context

This system is being built for a UK secondary school to assess computing topics covered each half term. The school uses:
- Windows PCs for pupils
- Windows PCs for teachers
- Internal network (no public domain, IP-based access)
- Microsoft Teams (potential future SSO integration)

Year groups and typical ages:
- Year 7: 11-12 years old
- Year 8: 12-13 years old
- Year 9: 13-14 years old

Class sizes: Up to 15 pupils, wide range of abilities within each class.

## Document Formats

Teachers provide materials in:
- **.docx**: Lesson plans, learning objectives, key vocabulary, homework tasks
- **.pptx**: Lesson slides with content, diagrams, examples, activities

The AI must parse these documents to understand:
- What topics are covered
- What the learning objectives are
- Key terminology and definitions
- Example problems and solutions
- The progression of difficulty

## Getting Started

1. Read `01-system-architecture.md` for project setup
2. Read `02-question-types.md` to understand what you're building
3. Read `03-ai-generation.md` to understand the AI integration
4. Start with database schema (`04-database-schema.md`) and API (`05-api-endpoints.md`)
5. Build frontend interfaces (`06-teacher-dashboard.md`, `07-pupil-interface.md`)
6. Integrate document processing (`08-document-processing.md`)
7. Implement marking (`09-marking-feedback.md`)
8. Test with example workflow (`10-example-workflow.md`)

## Questions?

If anything is unclear, check the relevant document first. If still unclear, ask the user for clarification - they have access to example lesson plans and can provide additional context.

## Maintaining These Documents

When making changes to any document in this folder:
1. **Read `CHANGELOG.md` first** - understand existing customisations
2. **Make your changes** to the relevant document(s)
3. **Update `CHANGELOG.md`** - document what you changed and why
4. **Check for conflicts** - ensure changes don't break accessibility requirements
