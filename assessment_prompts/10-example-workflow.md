# Example Workflow

End-to-end example of creating and delivering an assessment.

## Scenario

Mr Smith teaches Year 7 Computing. He has just finished teaching a unit on Binary and Data Representation and wants to create an end-of-unit assessment.

## Step 1: Teacher Uploads Lesson Materials

### Documents Mr Smith Has

1. **Binary_Lesson_Plan.docx** - Contains:
   - Learning objectives
   - Key vocabulary
   - Activity descriptions
   - Success criteria

2. **Binary_Slides.pptx** - Contains:
   - 20 slides covering binary concepts
   - Examples of conversions
   - Practice problems

### API Call

```http
POST /api/units
Content-Type: application/json

{
  "title": "Binary and Data Representation",
  "year_group": 7,
  "half_term": 2,
  "academic_year": "2024-25"
}
```

Response:
```json
{"id": "unit-123", "title": "Binary and Data Representation"}
```

```http
POST /api/units/unit-123/documents
Content-Type: multipart/form-data

files: [Binary_Lesson_Plan.docx, Binary_Slides.pptx]
```

### Extracted Content (Preview)

```json
{
  "learning_objectives": [
    "Understand why computers use binary",
    "Convert binary numbers to decimal (up to 8 bits)",
    "Convert decimal numbers to binary (up to 255)",
    "Add two binary numbers (up to 8 bits)",
    "Explain the terms bit, nibble, and byte"
  ],
  "vocabulary": [
    {"term": "Binary", "definition": "A number system using only 0 and 1"},
    {"term": "Bit", "definition": "A single binary digit"},
    {"term": "Nibble", "definition": "4 bits"},
    {"term": "Byte", "definition": "8 bits"},
    {"term": "Decimal", "definition": "Base 10 number system (0-9)"}
  ],
  "content_preview": "Lesson 1: Introduction to Binary\n\nWhy do computers use binary?..."
}
```

## Step 2: Teacher Configures Assessment Generation

### Generation Request

```http
POST /api/assessments/generate
Content-Type: application/json

{
  "unit_id": "unit-123",
  "title": "Year 7 Binary Assessment - HT2",
  "num_questions": 15,
  "time_limit_minutes": 30,
  "difficulty_range": [1, 5],
  "teacher_instructions": "Include a good mix of binary to decimal and decimal to binary conversions. Make sure there are at least 2 questions about why computers use binary (important exam topic). Include one or two simple Python coding questions about converting numbers. Avoid questions about hexadecimal - we haven't covered that yet.",
  "required_question_types": ["multiple_choice", "binary_convert", "python_code", "matching"],
  "excluded_question_types": ["extended_text", "logic_gates"]
}
```

### AI Processing

The AI receives this prompt (simplified):

```
Generate 15 assessment questions for Year 7 Binary unit.

Learning Objectives:
- Understand why computers use binary
- Convert binary to decimal (up to 8 bits)
- Convert decimal to binary (up to 255)
- Add two binary numbers
- Explain bit, nibble, byte

Key Vocabulary: Binary, Bit, Nibble, Byte, Decimal

Teacher Instructions: Include mix of conversions. 2+ questions about why binary.
Include simple Python. No hexadecimal.

Required types: multiple_choice, binary_convert, python_code, matching
Excluded types: extended_text, logic_gates

Generate varied, inclusive assessment with difficulty progression 1→5.
```

### Generation Response

```json
{
  "assessment_id": "assess-456",
  "status": "draft",
  "title": "Year 7 Binary Assessment - HT2",
  "questions_generated": 15,
  "question_types": {
    "multiple_choice": 4,
    "binary_convert": 5,
    "python_code": 2,
    "matching": 2,
    "text_input": 2
  },
  "difficulty_distribution": {
    "1": 3,
    "2": 4,
    "3": 5,
    "4": 2,
    "5": 1
  },
  "total_points": 22,
  "estimated_duration_minutes": 28,
  "warnings": []
}
```

## Step 3: Generated Questions (Sample)

### Question 1 (Multiple Choice, Difficulty 1)

```json
{
  "number": 1,
  "type": "multiple_choice",
  "difficulty": 1,
  "points": 1,
  "question_text": "What number system do computers use to store and process all data?",
  "type_data": {
    "options": [
      {"id": "a", "text": "Decimal", "is_correct": false},
      {"id": "b", "text": "Binary", "is_correct": true},
      {"id": "c", "text": "Roman numerals", "is_correct": false},
      {"id": "d", "text": "Fractions", "is_correct": false}
    ],
    "shuffle_options": true
  },
  "hint": "Think about what electronic circuits can do - they can be ON or OFF.",
  "feedback_correct": "That's right! Computers use binary (1s and 0s) because electronic circuits have two states: ON and OFF.",
  "feedback_incorrect": "Not quite. Computers use binary - a system with just two digits (0 and 1) - because electronic circuits can only be ON or OFF."
}
```

### Question 5 (Binary Convert, Difficulty 2)

```json
{
  "number": 5,
  "type": "binary_convert",
  "difficulty": 2,
  "points": 1,
  "question_text": "Convert this binary number to decimal:",
  "type_data": {
    "conversion_type": "binary_to_decimal",
    "given_value": "1011",
    "correct_answer": "11",
    "show_working": true,
    "working_template": {
      "binary_positions": ["8", "4", "2", "1"],
      "binary_digits": ["1", "0", "1", "1"]
    }
  },
  "hint": "Write out the place values: 8, 4, 2, 1. Then add up the values where there's a 1.",
  "feedback_correct": "Excellent! 1011 = 8 + 0 + 2 + 1 = 11",
  "feedback_incorrect": "Not quite. Let's work it out: 1011 has place values 8-4-2-1. So it's 8 + 0 + 2 + 1 = 11"
}
```

### Question 8 (Matching, Difficulty 2)

```json
{
  "number": 8,
  "type": "matching",
  "difficulty": 2,
  "points": 2,
  "question_text": "Match each term to its correct definition:",
  "type_data": {
    "left_items": [
      {"id": "l1", "text": "Bit"},
      {"id": "l2", "text": "Nibble"},
      {"id": "l3", "text": "Byte"},
      {"id": "l4", "text": "Binary"}
    ],
    "right_items": [
      {"id": "r1", "text": "A single binary digit (0 or 1)"},
      {"id": "r2", "text": "A group of 4 bits"},
      {"id": "r3", "text": "A group of 8 bits"},
      {"id": "r4", "text": "A number system using only 0 and 1"}
    ],
    "correct_pairs": [
      {"left": "l1", "right": "r1"},
      {"left": "l2", "right": "r2"},
      {"left": "l3", "right": "r3"},
      {"left": "l4", "right": "r4"}
    ],
    "shuffle_right": true
  },
  "hint": "Remember: Bit is the smallest, then Nibble (4), then Byte (8).",
  "feedback_correct": "Perfect! Bit (1) < Nibble (4) < Byte (8), and Binary is the number system.",
  "feedback_partial": "You got {correct}/{total} correct. Remember the sizes: Bit=1, Nibble=4, Byte=8.",
  "feedback_incorrect": "Let's review: Bit = 1 digit, Nibble = 4 bits, Byte = 8 bits, Binary = the 0s and 1s system."
}
```

### Question 12 (Python Code, Difficulty 4)

```json
{
  "number": 12,
  "type": "python_code",
  "difficulty": 4,
  "points": 3,
  "question_text": "Write a function called `to_decimal` that takes a binary string (like \"1011\") and returns the decimal number it represents.",
  "type_data": {
    "starter_code": "def to_decimal(binary_string):\n    # Your code here\n    pass",
    "test_cases": [
      {"input": "to_decimal('1011')", "expected": "11", "visible": true},
      {"input": "to_decimal('1111')", "expected": "15", "visible": true},
      {"input": "to_decimal('10000')", "expected": "16", "visible": false},
      {"input": "to_decimal('0')", "expected": "0", "visible": false}
    ],
    "banned_keywords": [],
    "required_keywords": ["def", "return"],
    "time_limit_seconds": 5,
    "hidden_test_weight": 0.4
  },
  "hint": "You could use Python's built-in int() function with a second argument, or loop through each digit.",
  "scaffold": {
    "hint_code": "def to_decimal(binary_string):\n    # Method 1: Use int() with base 2\n    return int(binary_string, ___)\n\n    # OR Method 2: Manual calculation\n    # result = 0\n    # for digit in binary_string:\n    #     result = result * 2 + int(digit)\n    # return result"
  },
  "feedback_correct": "Brilliant! Your function converts binary to decimal perfectly.",
  "feedback_partial": "{passed}/{total} tests passed. Check edge cases like '0' and longer binary numbers.",
  "feedback_incorrect": "Not working yet. Try using int(binary_string, 2) - the 2 tells Python it's binary!"
}
```

## Step 4: Teacher Reviews and Edits

Mr Smith reviews the generated assessment in the dashboard.

### Edit Made

He decides Question 12 (Python) is too hard for most of Year 7. He clicks "Edit" and simplifies it:

```http
PATCH /api/assessments/assess-456/questions/q12
Content-Type: application/json

{
  "difficulty": 3,
  "question_text": "Complete this function that converts a 4-bit binary string to decimal. The function should use Python's built-in int() function.",
  "type_data": {
    "starter_code": "def to_decimal(binary_string):\n    # Use int() with a second argument to specify base 2\n    return int(binary_string, ___)",
    "test_cases": [
      {"input": "to_decimal('1011')", "expected": "11", "visible": true},
      {"input": "to_decimal('1111')", "expected": "15", "visible": true},
      {"input": "to_decimal('0001')", "expected": "1", "visible": false}
    ]
  }
}
```

### Regenerate Request

He also asks the AI to regenerate Question 15 with different instructions:

```http
POST /api/assessments/assess-456/questions/q15/regenerate
Content-Type: application/json

{
  "instructions": "Make this an easier multiple choice question about why binary is useful for computers. Difficulty should be 2.",
  "keep_type": false
}
```

## Step 5: Teacher Publishes Assessment

After reviewing all 15 questions, Mr Smith is satisfied.

```http
POST /api/assessments/assess-456/publish
Content-Type: application/json

{
  "class_ids": ["class-7a", "class-7b"],
  "available_from": "2024-02-05T09:00:00Z",
  "available_until": "2024-02-12T23:59:59Z"
}
```

## Step 6: Pupil Takes Assessment

### Chloe logs in and starts the assessment

```http
POST /api/pupil/assessments/assess-456/start
```

### She answers Question 1 correctly

```http
POST /api/pupil/attempts/attempt-789/answers
Content-Type: application/json

{
  "question_id": "q1",
  "answer_data": {
    "selected_option": "b"
  }
}
```

Response (immediate feedback enabled):
```json
{
  "saved": true,
  "feedback": {
    "is_correct": true,
    "score": 1,
    "max_score": 1,
    "message": "That's right! Computers use binary (1s and 0s) because electronic circuits have two states: ON and OFF."
  }
}
```

### She struggles with Question 5 and requests a hint

```http
POST /api/pupil/attempts/attempt-789/questions/q5/hint
```

Response:
```json
{
  "hint": "Write out the place values: 8, 4, 2, 1. Then add up the values where there's a 1.",
  "hint_used": true
}
```

### She answers Question 5 with the hint's help

```http
POST /api/pupil/attempts/attempt-789/answers
Content-Type: application/json

{
  "question_id": "q5",
  "answer_data": {
    "answer": "11"
  }
}
```

Response:
```json
{
  "saved": true,
  "feedback": {
    "is_correct": true,
    "score": 1,
    "max_score": 1,
    "message": "Excellent! 1011 = 8 + 0 + 2 + 1 = 11. Great job using the hint to help you!"
  }
}
```

### She completes the assessment

```http
POST /api/pupil/attempts/attempt-789/complete
```

Response:
```json
{
  "completed": true,
  "summary": {
    "total_score": 16,
    "max_score": 22,
    "percentage": 73,
    "questions_answered": 15,
    "time_taken_minutes": 26,
    "message": "Well done! You've demonstrated good knowledge. Keep practising the areas you found tricky.",
    "strengths": [
      "Understanding why computers use binary",
      "Converting binary to decimal"
    ],
    "areas_for_development": [
      "Converting decimal to binary",
      "Python coding"
    ]
  }
}
```

## Step 7: Teacher Reviews Results

After a week, most pupils have completed the assessment.

```http
GET /api/analytics/assessments/assess-456/results
```

### Class Summary

```json
{
  "summary": {
    "total_pupils": 58,
    "completed": 54,
    "in_progress": 2,
    "not_started": 2,
    "average_score": 68.5,
    "median_score": 71,
    "highest_score": 95,
    "lowest_score": 32
  }
}
```

### Question Analysis

```json
{
  "question_analysis": [
    {
      "number": 1,
      "type": "multiple_choice",
      "correct_rate": 0.94,
      "hint_usage_rate": 0.04,
      "average_time_seconds": 25
    },
    {
      "number": 12,
      "type": "python_code",
      "correct_rate": 0.41,
      "hint_usage_rate": 0.56,
      "scaffold_usage_rate": 0.35,
      "average_time_seconds": 180,
      "flag": "low_success_rate"
    }
  ]
}
```

### Insights for Mr Smith

- Questions 1-4: High success (>80%) - good confidence builders
- Question 12 (Python): Only 41% success - may need to reteach this skill
- 8 pupils scored below 50% - consider intervention
- Average hint usage was 23% - appropriate level of challenge

## Step 8: Data Stored for Trend Analysis

All data is stored for longitudinal analysis:

- Individual pupil scores across all assessments
- Class performance by topic over time
- Question effectiveness metrics
- Hint and scaffold usage patterns

This allows Mr Smith to:
- Track which pupils are improving or declining
- Identify topics that consistently cause difficulty
- Refine future assessments based on question performance
- Demonstrate pupil progress to parents and leadership

---

## Summary

This workflow demonstrates:

1. **Document upload and processing** - extracting learning objectives and vocabulary
2. **AI-powered generation** - creating varied questions with teacher guidance
3. **Teacher review and editing** - maintaining control over content
4. **Pupil experience** - accessible interface with support options
5. **Analytics** - comprehensive data for teaching improvement

The system handles the heavy lifting of question creation while keeping teachers in control of the final assessment.
