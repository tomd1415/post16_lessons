# AI Assessment Generation

This document describes how the AI generates assessment questions from teacher-provided lesson materials.

## Overview

The AI receives:
1. Parsed content from lesson plan documents (.docx)
2. Parsed content from presentation slides (.pptx)
3. Teacher's special instructions
4. Target year group and difficulty range
5. Required number of questions and mix of types

The AI outputs:
1. A structured assessment with varied question types
2. Questions covering all key learning objectives
3. Appropriate difficulty progression
4. Inclusive feedback language

## OpenAI Integration

### API Configuration

```python
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Recommended model for structured output
MODEL = "gpt-5.2"  # or "gpt-4o" when available

# Token limits
MAX_INPUT_TOKENS = 8000   # Leave room for lesson content
MAX_OUTPUT_TOKENS = 4000  # Assessment JSON can be large
```

### Using Structured Output (Responses API)

If using OpenAI's structured output / responses API:

```python
response = client.responses.create(
    model=MODEL,
    input=[
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_prompt_with_lesson_content
        }
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "assessment",
            "schema": ASSESSMENT_SCHEMA
        }
    },
    max_tokens=MAX_OUTPUT_TOKENS,
    temperature=0.7
)

assessment_data = json.loads(response.output)
```

### Using Standard Chat Completions

Alternatively, with chat completions:

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ],
    response_format={"type": "json_object"},
    max_tokens=MAX_OUTPUT_TOKENS,
    temperature=0.7
)

assessment_data = json.loads(response.choices[0].message.content)
```

## System Prompt

```text
You are an expert educational assessment designer for UK secondary school computing (KS3, ages 11-14). You create engaging, inclusive assessments that accurately test understanding while ensuring all students feel capable of success.

## Your Task
Generate assessment questions based on lesson materials provided by the teacher. You will receive:
- Extracted text from lesson plans and slides
- Learning objectives for the unit
- Teacher's special instructions
- Target year group and number of questions needed
- Taxonomy strands to cover (from NCCE Teach Computing taxonomy)

## NCCE Taxonomy Strands
Tag each question with relevant taxonomy strand(s):
- NW: Networks
- CM: Creating Media
- DI: Data and Information
- DD: Design and Development
- CS: Computing Systems
- IT: Impact of Technology
- AL: Algorithms
- PG: Programming
- ET: Effective Use of Tools
- SS: Safety and Security

## Question Type Selection Rules

Choose question types based on what's being assessed:

| Learning Type | Best Question Types |
|---------------|---------------------|
| Recall of facts/definitions | multiple_choice, text_input, matching |
| Understanding concepts | multiple_choice, multiple_select, extended_text |
| Applying knowledge | python_code, code_completion, binary_convert |
| Analysing/evaluating | code_debug, extended_text, ordering |
| Creating/problem-solving | python_code, parsons, code_completion |

## Variety Requirements
- Never use the same question type more than 3 times in a row
- Include at least 4 different question types per assessment
- Mix knowledge recall with application questions
- Start with accessible questions, progress to challenging

## Difficulty Progression
Questions should follow this pattern:
1. First 20%: Confidence builders (difficulty 1-2)
2. Middle 60%: Core assessment (difficulty 2-4)
3. Final 20%: Stretch challenges (difficulty 4-5)

## Inclusive Language Rules
NEVER use:
- "Wrong", "incorrect", "failed", "bad"
- Language that implies judgment of the student

ALWAYS use:
- "Not quite", "nearly there", "try again"
- Language that separates the attempt from the student's worth
- Feedback that teaches, not just evaluates

## Accessibility for Autism/ADHD (CRITICAL)
All pupils have communication difficulties (autism, ADHD, similar). Every question MUST:

### Language Requirements
- Use clear, literal language - no idioms, metaphors, or sarcasm
- Keep sentences short (max 15-20 words)
- One instruction per sentence
- Avoid ambiguous pronouns ("it", "this", "that") - be specific
- Use concrete, specific vocabulary over abstract terms
- Define technical terms on first use in assessment

### Question Structure
- Each question tests ONE concept only
- State exactly what format the answer should be in
- If there's a specific order to follow, number the steps
- Avoid negative phrasing ("Which is NOT...") - phrase positively instead
- Use "Select ONE answer" not "Choose the best answer"

### Cognitive Load
- Limit multiple choice options to 4 maximum
- Avoid "all of the above" or "none of the above" options
- Keep code snippets short (under 10 lines where possible)
- Provide visual structure (bullet points, numbered lists)
- Avoid questions requiring inference or "reading between the lines"

### Examples in Questions
- Use concrete, familiar contexts (school, games, everyday objects)
- Be specific: "a list of 5 numbers" not "some numbers"
- Include worked examples where appropriate

### Feedback Accessibility
- Start feedback with clear statement: "Correct!" or "Not quite."
- Explain WHY the answer is right/wrong in simple terms
- Use step-by-step explanations
- Keep feedback concise (3-4 sentences maximum)
- End with encouragement that acknowledges effort

## Feedback Requirements
Every question MUST have:
1. `correct` feedback: Celebrates and reinforces why it's right
2. `incorrect` feedback: Explains the concept, gives the right answer, encourages
3. `partial` feedback (where applicable): Acknowledges progress, guides to full answer
4. `hint`: A gentle nudge without giving the answer away

## Output Format
Return a JSON object with this structure:
{
  "assessment_title": "Unit 3: Binary and Data Representation",
  "year_group": 7,
  "estimated_duration_minutes": 30,
  "learning_objectives_covered": ["LO1", "LO2", "LO3"],
  "questions": [
    { /* Question object per 02-question-types.md specification */ }
  ],
  "metadata": {
    "total_points": 25,
    "question_type_distribution": {"multiple_choice": 4, "python_code": 2, ...},
    "difficulty_distribution": {"1": 2, "2": 5, "3": 8, "4": 3, "5": 2}
  }
}
```

## User Prompt Template

```text
## Lesson Materials

### Unit Information
- Unit Title: {unit_title}
- Year Group: {year_group}
- Half Term: {half_term}

### Learning Objectives
{learning_objectives}

### Lesson Plan Content
{lesson_plan_text}

### Slide Content
{slides_text}

### Key Vocabulary
{vocabulary_list}

## Teacher Instructions
{teacher_special_instructions}

## Assessment Requirements
- Number of questions: {num_questions}
- Time available: {time_minutes} minutes
- Difficulty range: {min_difficulty} to {max_difficulty}
- Must include question types: {required_types}
- Avoid question types: {excluded_types}

## Generate Assessment
Create a {num_questions}-question assessment covering the learning objectives above. Follow all rules in your system prompt. Return valid JSON only.
```

## Response Schema

```python
ASSESSMENT_SCHEMA = {
    "type": "object",
    "required": ["assessment_title", "year_group", "questions", "metadata"],
    "properties": {
        "assessment_title": {"type": "string"},
        "year_group": {"type": "integer", "minimum": 7, "maximum": 9},
        "estimated_duration_minutes": {"type": "integer"},
        "learning_objectives_covered": {
            "type": "array",
            "items": {"type": "string"}
        },
        "questions": {
            "type": "array",
            "items": {"$ref": "#/$defs/question"}
        },
        "metadata": {
            "type": "object",
            "properties": {
                "total_points": {"type": "integer"},
                "question_type_distribution": {"type": "object"},
                "difficulty_distribution": {"type": "object"}
            }
        }
    },
    "$defs": {
        "question": {
            "type": "object",
            "required": ["type", "question_text", "difficulty", "points", "feedback"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "multiple_choice", "multiple_select", "text_input",
                        "extended_text", "matching", "ordering", "parsons",
                        "code_completion", "python_code", "code_debug",
                        "trace_table", "drag_label", "binary_convert", "logic_gates"
                    ]
                },
                "question_text": {"type": "string"},
                "difficulty": {"type": "integer", "minimum": 1, "maximum": 5},
                "points": {"type": "integer", "minimum": 1, "maximum": 10},
                "feedback": {
                    "type": "object",
                    "required": ["correct", "incorrect"],
                    "properties": {
                        "correct": {"type": "string"},
                        "incorrect": {"type": "string"},
                        "partial": {"type": "string"}
                    }
                },
                "hint": {"type": "string"}
                # Additional properties depend on question type
                # See 02-question-types.md for full schemas
            }
        }
    }
}
```

## Backend Service

```python
# backend/app/services/ai_generator.py

from openai import OpenAI
import json
from typing import Optional
from ..config import settings

class AssessmentGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate_assessment(
        self,
        lesson_content: dict,
        year_group: int,
        num_questions: int,
        teacher_instructions: str,
        required_types: Optional[list] = None,
        excluded_types: Optional[list] = None,
        difficulty_range: tuple = (1, 5)
    ) -> dict:
        """
        Generate an assessment from lesson content.

        Args:
            lesson_content: Dict with 'lesson_plan', 'slides', 'vocabulary', 'objectives'
            year_group: 7, 8, or 9
            num_questions: Target number of questions
            teacher_instructions: Special instructions from teacher
            required_types: Question types that must be included
            excluded_types: Question types to avoid
            difficulty_range: (min, max) difficulty levels

        Returns:
            Assessment dict ready for database storage
        """
        user_prompt = self._build_user_prompt(
            lesson_content,
            year_group,
            num_questions,
            teacher_instructions,
            required_types,
            excluded_types,
            difficulty_range
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=4000,
            temperature=0.7
        )

        assessment_data = json.loads(response.choices[0].message.content)

        # Validate and clean the response
        assessment_data = self._validate_assessment(assessment_data)

        return assessment_data

    def _build_user_prompt(self, lesson_content, year_group, num_questions,
                           teacher_instructions, required_types, excluded_types,
                           difficulty_range) -> str:
        # Build prompt from template
        # ... implementation
        pass

    def _validate_assessment(self, data: dict) -> dict:
        """Validate AI output meets requirements."""
        # Check all required fields present
        # Validate question types are valid
        # Ensure feedback language is inclusive
        # Verify difficulty distribution
        # ... implementation
        pass


# System prompt stored as module constant
SYSTEM_PROMPT = """..."""  # As defined above
```

## Handling Large Documents

For documents that exceed token limits:

```python
def chunk_content(content: str, max_chars: int = 20000) -> list[str]:
    """Split content into chunks that fit within token limits."""
    # Split by section headings first
    sections = re.split(r'\n#{1,3}\s+', content)

    chunks = []
    current_chunk = ""

    for section in sections:
        if len(current_chunk) + len(section) < max_chars:
            current_chunk += "\n" + section
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = section

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


async def generate_from_large_document(self, lesson_content: dict, **kwargs):
    """Handle documents that exceed token limits."""
    full_content = lesson_content['lesson_plan'] + lesson_content['slides']

    if len(full_content) < 20000:
        # Single pass generation
        return await self.generate_assessment(lesson_content, **kwargs)

    # Multi-pass: extract key info first, then generate
    summary = await self._summarize_content(full_content)
    lesson_content['lesson_plan'] = summary

    return await self.generate_assessment(lesson_content, **kwargs)
```

## Quality Checks

After AI generation, run these checks:

```python
def quality_check_assessment(assessment: dict) -> list[str]:
    """Return list of issues found."""
    issues = []

    questions = assessment.get('questions', [])

    # Check variety
    types_used = [q['type'] for q in questions]
    if len(set(types_used)) < 4:
        issues.append("Insufficient variety: fewer than 4 question types used")

    # Check for repetition
    for i in range(len(types_used) - 3):
        if len(set(types_used[i:i+4])) == 1:
            issues.append(f"Same question type used 4+ times in a row at position {i}")

    # Check difficulty progression
    difficulties = [q['difficulty'] for q in questions]
    first_quarter = difficulties[:len(difficulties)//4]
    if any(d > 3 for d in first_quarter):
        issues.append("Difficult questions too early - should start accessible")

    # Check feedback language
    bad_words = ['wrong', 'incorrect', 'failed', 'bad', 'stupid']
    for q in questions:
        feedback = json.dumps(q.get('feedback', {})).lower()
        for word in bad_words:
            if word in feedback:
                issues.append(f"Forbidden word '{word}' found in feedback")

    # Check all questions have hints
    for i, q in enumerate(questions):
        if 'hint' not in q or not q['hint']:
            issues.append(f"Question {i+1} missing hint")

    return issues
```

## Teacher Review Workflow

After AI generates assessment:

1. **Draft Stage**: Assessment saved as draft, visible only to teacher
2. **Review Stage**: Teacher sees each question with edit options
3. **Edit Stage**: Teacher can:
   - Modify question text
   - Change options/answers
   - Adjust difficulty
   - Rewrite feedback
   - Delete questions
   - Request AI regenerate specific question
4. **Approve Stage**: Teacher marks assessment as ready
5. **Publish Stage**: Assessment made available to selected classes

```python
# API endpoint for regenerating single question
@router.post("/assessments/{assessment_id}/questions/{question_index}/regenerate")
async def regenerate_question(
    assessment_id: UUID,
    question_index: int,
    instructions: str = Body(...),
    current_user: Teacher = Depends(get_current_teacher)
):
    """Ask AI to regenerate a specific question with new instructions."""
    assessment = await get_assessment(assessment_id)

    question = assessment.questions[question_index]

    new_question = await generator.regenerate_single_question(
        question=question,
        instructions=instructions,
        context=assessment.lesson_content
    )

    assessment.questions[question_index] = new_question
    await save_assessment(assessment)

    return new_question
```

## Cost Management

Track and limit AI usage:

```python
# Track tokens used per generation
async def generate_with_tracking(self, teacher_id: UUID, **kwargs):
    response = await self._generate(**kwargs)

    # Log usage
    await log_ai_usage(
        teacher_id=teacher_id,
        model=self.model,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        timestamp=datetime.utcnow()
    )

    # Check rate limits
    usage_today = await get_teacher_usage_today(teacher_id)
    if usage_today > settings.AI_DAILY_LIMIT:
        raise RateLimitExceeded("Daily AI generation limit reached")

    return response
```

## Error Handling

```python
from openai import OpenAIError, RateLimitError, APIError

async def generate_with_retry(self, **kwargs) -> dict:
    """Generate with retry logic for transient failures."""
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            return await self.generate_assessment(**kwargs)

        except RateLimitError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise GenerationError("OpenAI rate limit exceeded. Please try again later.")

        except APIError as e:
            if e.status_code >= 500 and attempt < max_retries - 1:
                await asyncio.sleep(base_delay)
            else:
                raise GenerationError(f"OpenAI API error: {e.message}")

        except json.JSONDecodeError:
            # AI returned invalid JSON
            if attempt < max_retries - 1:
                continue  # Retry
            else:
                raise GenerationError("AI returned invalid response. Please try again.")
```

## Testing AI Generation

```python
# tests/test_generation.py

import pytest
from app.services.ai_generator import AssessmentGenerator, quality_check_assessment

@pytest.fixture
def sample_lesson_content():
    return {
        "lesson_plan": "Learning Objectives: Understand binary...",
        "slides": "Slide 1: Binary Basics...",
        "vocabulary": ["binary", "bit", "byte", "decimal"],
        "objectives": ["Convert binary to decimal", "Explain why computers use binary"]
    }

async def test_generates_correct_number_of_questions(sample_lesson_content):
    generator = AssessmentGenerator()
    assessment = await generator.generate_assessment(
        lesson_content=sample_lesson_content,
        year_group=7,
        num_questions=10,
        teacher_instructions=""
    )

    assert len(assessment['questions']) == 10

async def test_respects_difficulty_range(sample_lesson_content):
    generator = AssessmentGenerator()
    assessment = await generator.generate_assessment(
        lesson_content=sample_lesson_content,
        year_group=7,
        num_questions=10,
        teacher_instructions="",
        difficulty_range=(1, 3)
    )

    for q in assessment['questions']:
        assert 1 <= q['difficulty'] <= 3

async def test_quality_checks_pass(sample_lesson_content):
    generator = AssessmentGenerator()
    assessment = await generator.generate_assessment(
        lesson_content=sample_lesson_content,
        year_group=7,
        num_questions=15,
        teacher_instructions=""
    )

    issues = quality_check_assessment(assessment)
    assert len(issues) == 0, f"Quality issues found: {issues}"
```
