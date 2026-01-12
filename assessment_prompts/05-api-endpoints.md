# API Endpoints

REST API design for the KS3 Assessment System.

## Base URL

```
https://{server}:8443/api
```

## Authentication

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "teacher1",
  "password": "securepassword",
  "user_type": "teacher"  // or "pupil"
}
```

Response:
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "username": "teacher1",
    "name": "Mr Smith",
    "role": "teacher"
  }
}
```

Sets `session` cookie (HTTP-only, secure).

### Logout

```http
POST /api/auth/logout
```

### Get Current User

```http
GET /api/auth/me
```

## Units and Documents

### Create Unit

```http
POST /api/units
Content-Type: application/json

{
  "title": "Binary and Data Representation",
  "year_group": 7,
  "half_term": 2,
  "academic_year": "2024-25",
  "description": "Introduction to binary number system"
}
```

### Upload Documents to Unit

```http
POST /api/units/{unit_id}/documents
Content-Type: multipart/form-data

files: [lesson_plan.docx, slides.pptx]
```

Response:
```json
{
  "message": "Processed 2 documents",
  "documents": [
    {"id": "uuid", "filename": "lesson_plan.docx", "type": "docx"},
    {"id": "uuid", "filename": "slides.pptx", "type": "pptx"}
  ],
  "extracted": {
    "learning_objectives": [
      "Convert binary to decimal",
      "Convert decimal to binary"
    ],
    "vocabulary_count": 8,
    "content_preview": "First 500 characters of extracted content..."
  }
}
```

### List Units

```http
GET /api/units?year_group=7&academic_year=2024-25
```

## Assessment Generation

### Generate Assessment from Unit

```http
POST /api/assessments/generate
Content-Type: application/json

{
  "unit_id": "uuid",
  "title": "Half Term 2 Assessment",
  "num_questions": 15,
  "time_limit_minutes": 30,
  "difficulty_range": [1, 5],
  "teacher_instructions": "Focus more on binary to decimal conversion. Include at least 2 Python coding questions.",
  "required_question_types": ["multiple_choice", "python_code"],
  "excluded_question_types": ["extended_text"]
}
```

Response (may take 10-30 seconds):
```json
{
  "assessment_id": "uuid",
  "status": "draft",
  "title": "Half Term 2 Assessment",
  "questions_generated": 15,
  "question_types": {
    "multiple_choice": 5,
    "python_code": 3,
    "matching": 2,
    "text_input": 3,
    "binary_convert": 2
  },
  "total_points": 25,
  "estimated_duration_minutes": 28,
  "warnings": []
}
```

### Get Assessment (Teacher View)

```http
GET /api/assessments/{id}
```

Response includes all questions with correct answers (teacher only).

### Update Assessment

```http
PATCH /api/assessments/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "time_limit_minutes": 35,
  "allow_hints": true
}
```

### Update Question

```http
PATCH /api/assessments/{assessment_id}/questions/{question_id}
Content-Type: application/json

{
  "question_text": "Updated question text",
  "difficulty": 3,
  "feedback_incorrect": "Updated feedback"
}
```

### Regenerate Single Question

```http
POST /api/assessments/{assessment_id}/questions/{question_id}/regenerate
Content-Type: application/json

{
  "instructions": "Make this question easier and about input/output instead",
  "keep_type": true  // false to let AI choose new type
}
```

### Delete Question

```http
DELETE /api/assessments/{assessment_id}/questions/{question_id}
```

### Reorder Questions

```http
POST /api/assessments/{assessment_id}/questions/reorder
Content-Type: application/json

{
  "question_order": ["uuid1", "uuid2", "uuid3", ...]
}
```

### Publish Assessment

```http
POST /api/assessments/{id}/publish
Content-Type: application/json

{
  "class_ids": ["uuid1", "uuid2"],
  "available_from": "2024-02-01T09:00:00Z",
  "available_until": "2024-02-14T23:59:59Z"
}
```

### Archive Assessment

```http
POST /api/assessments/{id}/archive
```

## Pupil Endpoints

### List Available Assessments

```http
GET /api/pupil/assessments
```

Response:
```json
{
  "available": [
    {
      "id": "uuid",
      "title": "Half Term 2 Assessment",
      "unit": "Binary and Data",
      "question_count": 15,
      "time_limit_minutes": 30,
      "available_until": "2024-02-14T23:59:59Z",
      "status": "not_started"
    }
  ],
  "completed": [
    {
      "id": "uuid",
      "title": "Half Term 1 Assessment",
      "completed_at": "2024-01-15T14:30:00Z",
      "score": 85,
      "can_view_results": true
    }
  ]
}
```

### Start Assessment Attempt

```http
POST /api/pupil/assessments/{id}/start
```

Response:
```json
{
  "attempt_id": "uuid",
  "assessment": {
    "title": "Half Term 2 Assessment",
    "time_limit_minutes": 30,
    "question_count": 15,
    "allow_hints": true,
    "show_immediate_feedback": false
  },
  "questions": [
    {
      "id": "uuid",
      "number": 1,
      "type": "multiple_choice",
      "question_text": "What does CPU stand for?",
      "points": 1,
      "options": [
        {"id": "a", "text": "Central Processing Unit"},
        {"id": "b", "text": "Computer Personal Unit"},
        {"id": "c", "text": "Central Program Utility"},
        {"id": "d", "text": "Core Processing Unit"}
      ]
      // Note: is_correct is NOT included for pupils
    }
  ]
}
```

### Submit Answer

```http
POST /api/pupil/attempts/{attempt_id}/answers
Content-Type: application/json

{
  "question_id": "uuid",
  "answer_data": {
    "selected_option": "a"
  }
}
```

Response (if immediate feedback enabled):
```json
{
  "saved": true,
  "feedback": {
    "is_correct": true,
    "score": 1,
    "max_score": 1,
    "message": "That's right! The CPU is the Central Processing Unit."
  }
}
```

Response (if no immediate feedback):
```json
{
  "saved": true
}
```

### Request Hint

```http
POST /api/pupil/attempts/{attempt_id}/questions/{question_id}/hint
```

Response:
```json
{
  "hint": "Think about what the CPU does - it processes instructions centrally.",
  "hint_used": true
}
```

### Request Scaffold

```http
POST /api/pupil/attempts/{attempt_id}/questions/{question_id}/scaffold
```

### Run Python Code (for coding questions)

```http
POST /api/pupil/attempts/{attempt_id}/questions/{question_id}/run
Content-Type: application/json

{
  "code": "def double(n):\n    return n * 2"
}
```

Response:
```json
{
  "output": "",
  "test_results": [
    {"input": "double(5)", "expected": "10", "actual": "10", "passed": true},
    {"input": "double(0)", "expected": "0", "actual": "0", "passed": true}
  ],
  "visible_tests_passed": 2,
  "visible_tests_total": 2,
  "has_hidden_tests": true
}
```

### Complete Attempt

```http
POST /api/pupil/attempts/{attempt_id}/complete
```

Response:
```json
{
  "completed": true,
  "summary": {
    "total_score": 18,
    "max_score": 25,
    "percentage": 72,
    "questions_answered": 15,
    "time_taken_minutes": 24,
    "message": "Well done! You've shown good understanding of binary concepts."
  }
}
```

### Get Attempt Results

```http
GET /api/pupil/attempts/{attempt_id}/results
```

## Teacher Analytics

### Get Class Results

```http
GET /api/analytics/assessments/{assessment_id}/results
```

Response:
```json
{
  "assessment": {
    "id": "uuid",
    "title": "Half Term 2 Assessment",
    "max_score": 25
  },
  "summary": {
    "total_pupils": 28,
    "completed": 26,
    "in_progress": 2,
    "average_score": 68.5,
    "median_score": 71,
    "highest_score": 96,
    "lowest_score": 32
  },
  "pupils": [
    {
      "id": "uuid",
      "name": "Alice Brown",
      "status": "completed",
      "score": 85,
      "percentage": 85,
      "time_taken_minutes": 22,
      "completed_at": "2024-02-05T10:15:00Z"
    }
  ],
  "question_analysis": [
    {
      "question_id": "uuid",
      "number": 1,
      "type": "multiple_choice",
      "correct_rate": 0.85,
      "hint_usage_rate": 0.12,
      "average_time_seconds": 45
    }
  ]
}
```

### Get Pupil Detail

```http
GET /api/analytics/pupils/{pupil_id}
```

### Get Question Analysis

```http
GET /api/analytics/assessments/{assessment_id}/questions/{question_id}
```

Response:
```json
{
  "question": {
    "id": "uuid",
    "type": "multiple_choice",
    "question_text": "What does CPU stand for?",
    "correct_answer": "a"
  },
  "statistics": {
    "attempts": 26,
    "correct": 22,
    "incorrect": 4,
    "correct_rate": 0.846,
    "average_time_seconds": 38,
    "hint_usage": 3
  },
  "option_distribution": {
    "a": 22,
    "b": 1,
    "c": 2,
    "d": 1
  }
}
```

### Get Trend Data

```http
GET /api/analytics/pupils/{pupil_id}/trends
GET /api/analytics/classes/{class_id}/trends
```

### Export Results

```http
GET /api/analytics/assessments/{assessment_id}/export?format=csv
```

## Admin Endpoints

### Manage Users

```http
GET /api/admin/teachers
POST /api/admin/teachers
GET /api/admin/pupils
POST /api/admin/pupils/bulk  // CSV upload
DELETE /api/admin/users/{id}
```

### Manage Classes

```http
GET /api/admin/classes
POST /api/admin/classes
POST /api/admin/classes/{id}/pupils  // Add pupils to class
```

### System Stats

```http
GET /api/admin/stats
```

Response:
```json
{
  "users": {
    "teachers": 12,
    "pupils": 450,
    "active_today": 180
  },
  "assessments": {
    "total": 45,
    "published": 38,
    "attempts_this_week": 523
  },
  "ai_usage": {
    "generations_today": 8,
    "tokens_this_month": 125000
  }
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": true,
  "code": "VALIDATION_ERROR",
  "message": "Human-readable error message",
  "details": {
    "field": "specific field error"
  }
}
```

Common error codes:
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `NOT_FOUND` (404)
- `VALIDATION_ERROR` (422)
- `RATE_LIMITED` (429)
- `SERVER_ERROR` (500)

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Login | 5 per minute |
| AI Generation | 10 per hour (per teacher) |
| Code Execution | 30 per minute (per pupil) |
| General API | 100 per minute |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1707123456
```

## Websocket (Optional)

For real-time updates during assessment:

```javascript
const ws = new WebSocket('wss://{server}:8443/api/ws/attempt/{attempt_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // { type: 'time_warning', minutes_remaining: 5 }
  // { type: 'answer_saved', question_id: 'uuid' }
};
```
