# Question Types Specification

This document defines all supported question types, their data structures, rendering requirements, and marking logic.

## Question Type Summary

| Type | Code | Difficulty Range | Auto-Markable | Partial Credit |
|------|------|------------------|---------------|----------------|
| Multiple Choice | `multiple_choice` | All | Yes | No |
| Multiple Select | `multiple_select` | All | Yes | Yes |
| Text Input | `text_input` | All | Yes* | Yes |
| Extended Text | `extended_text` | Medium-High | No** | N/A |
| Matching | `matching` | Low-Medium | Yes | Yes |
| Ordering | `ordering` | Low-Medium | Yes | Yes |
| Parsons Problem | `parsons` | Medium-High | Yes | Yes |
| Code Completion | `code_completion` | Medium | Yes | Yes |
| Python Coding | `python_code` | Medium-High | Yes | Yes |
| Code Debugging | `code_debug` | Medium-High | Yes | Yes |
| Trace Table | `trace_table` | Medium-High | Yes | Yes |
| Drag-Drop Label | `drag_label` | Low-Medium | Yes | Yes |
| Binary Conversion | `binary_convert` | Medium | Yes | No |
| Logic Gates | `logic_gates` | Medium-High | Yes | Yes |

\* Text input uses keyword matching
\** Extended text can be AI-marked or teacher-marked

---

## Question Base Schema

All questions share these common fields:

```json
{
  "id": "uuid",
  "type": "question_type_code",
  "topic_id": "uuid",
  "difficulty": 1-5,
  "points": 1-10,
  "time_estimate_seconds": 30-600,

  "question_text": "The main question prompt",
  "question_html": "<p>Optional HTML formatting</p>",
  "image_url": "/api/images/optional-image.png",

  "hint": "Optional hint text shown on request",
  "scaffold": { /* Optional easier version */ },

  "feedback": {
    "correct": "Shown when fully correct",
    "partial": "Shown when partially correct (use {score}/{total})",
    "incorrect": "Shown when incorrect - educational, not punitive"
  },

  "tags": ["binary", "year7", "half-term-2"],
  "created_at": "2024-01-15T10:30:00Z",
  "created_by": "teacher_uuid"
}
```

---

## 1. Multiple Choice (`multiple_choice`)

Single correct answer from 4 options.

### Data Structure

```json
{
  "type": "multiple_choice",
  "question_text": "What does CPU stand for?",
  "options": [
    {
      "id": "a",
      "text": "Central Processing Unit",
      "is_correct": true
    },
    {
      "id": "b",
      "text": "Computer Personal Unit",
      "is_correct": false,
      "distractor_feedback": "This isn't quite right - 'Personal' isn't part of CPU."
    },
    {
      "id": "c",
      "text": "Central Program Utility",
      "is_correct": false
    },
    {
      "id": "d",
      "text": "Core Processing Unit",
      "is_correct": false,
      "distractor_feedback": "Close! It's 'Central' not 'Core'."
    }
  ],
  "shuffle_options": true,
  "feedback": {
    "correct": "That's right! The CPU is the Central Processing Unit - the 'brain' of the computer.",
    "incorrect": "Not quite. CPU stands for Central Processing Unit."
  }
}
```

### Marking Logic
- 1 point if correct option selected
- 0 points otherwise
- No partial credit

### Frontend Notes
- Display as radio buttons
- Shuffle options if `shuffle_options` is true (but track original order)
- Show distractor-specific feedback if available

---

## 2. Multiple Select (`multiple_select`)

Multiple correct answers possible.

### Data Structure

```json
{
  "type": "multiple_select",
  "question_text": "Which of these are examples of secondary storage? Select all that apply.",
  "options": [
    {"id": "a", "text": "Hard Disk Drive (HDD)", "is_correct": true},
    {"id": "b", "text": "RAM", "is_correct": false},
    {"id": "c", "text": "USB Flash Drive", "is_correct": true},
    {"id": "d", "text": "CPU Cache", "is_correct": false},
    {"id": "e", "text": "Solid State Drive (SSD)", "is_correct": true}
  ],
  "min_selections": 1,
  "max_selections": 5,
  "feedback": {
    "correct": "Perfect! HDDs, SSDs, and USB drives are all secondary storage.",
    "partial": "You got {correct}/{total} correct. Remember: secondary storage keeps data when power is off.",
    "incorrect": "Not quite. Secondary storage is permanent storage like HDDs, SSDs, and USB drives."
  }
}
```

### Marking Logic
- Calculate: (correct selections - incorrect selections) / total correct options
- Minimum score is 0 (no negative marks)
- Example: 3 correct options, student selects 2 correct + 1 incorrect = (2-1)/3 = 0.33

### Frontend Notes
- Display as checkboxes
- Show selection count if limits apply

---

## 3. Text Input (`text_input`)

Short text answer with keyword matching.

### Data Structure

```json
{
  "type": "text_input",
  "question_text": "What is the name of the component that stores data temporarily while the computer is running?",
  "max_length": 100,
  "case_sensitive": false,
  "accepted_answers": [
    {"text": "RAM", "points": 1.0},
    {"text": "Random Access Memory", "points": 1.0},
    {"text": "memory", "points": 0.5},
    {"text": "main memory", "points": 0.75}
  ],
  "required_keywords": [],
  "forbidden_keywords": [],
  "feedback": {
    "correct": "Exactly right! RAM (Random Access Memory) is temporary storage.",
    "partial": "You're on the right track! The full answer is RAM or Random Access Memory.",
    "incorrect": "The answer is RAM (Random Access Memory) - it stores data temporarily while the computer is on."
  }
}
```

### Marking Logic
1. Normalize answer (trim, optionally lowercase)
2. Check exact matches first (full points)
3. Check partial matches (partial points)
4. Check for required keywords
5. Check for forbidden keywords (reduce score)

### Frontend Notes
- Single line text input
- Show character count if max_length specified
- Disable autocomplete/spellcheck for technical terms

---

## 4. Extended Text (`extended_text`)

Longer written response, typically teacher-marked.

### Data Structure

```json
{
  "type": "extended_text",
  "question_text": "Explain why a computer needs both RAM and secondary storage. Include at least two differences between them.",
  "min_words": 30,
  "max_words": 200,
  "marking_guide": {
    "points_available": 4,
    "mark_scheme": [
      {"criterion": "Mentions RAM is temporary/volatile", "points": 1},
      {"criterion": "Mentions secondary storage is permanent", "points": 1},
      {"criterion": "Mentions RAM is faster", "points": 1},
      {"criterion": "Explains why both are needed together", "points": 1}
    ]
  },
  "ai_marking_enabled": true,
  "ai_marking_prompt": "Mark this response about RAM vs secondary storage. Award points for: volatility difference, speed difference, capacity difference, explaining why both are needed.",
  "feedback": {
    "submitted": "Your answer has been submitted for marking. Check back later for feedback."
  }
}
```

### Marking Logic
- If AI marking enabled: use OpenAI to assess against mark scheme
- Otherwise: queue for teacher marking
- AI provides suggested marks + feedback, teacher can override

### Frontend Notes
- Textarea with word count
- Show minimum word requirement
- Save draft automatically

---

## 5. Matching (`matching`)

Connect items from two columns.

### Data Structure

```json
{
  "type": "matching",
  "question_text": "Match each file extension to its file type:",
  "left_items": [
    {"id": "l1", "text": ".docx"},
    {"id": "l2", "text": ".mp3"},
    {"id": "l3", "text": ".png"},
    {"id": "l4", "text": ".html"}
  ],
  "right_items": [
    {"id": "r1", "text": "Word Document"},
    {"id": "r2", "text": "Audio File"},
    {"id": "r3", "text": "Image File"},
    {"id": "r4", "text": "Web Page"}
  ],
  "correct_pairs": [
    {"left": "l1", "right": "r1"},
    {"left": "l2", "right": "r2"},
    {"left": "l3", "right": "r3"},
    {"left": "l4", "right": "r4"}
  ],
  "shuffle_right": true,
  "feedback": {
    "correct": "Perfect matching!",
    "partial": "You got {correct}/{total} pairs correct.",
    "incorrect": "Let's review: .docx is Word, .mp3 is audio, .png is image, .html is web page."
  }
}
```

### Marking Logic
- Points = correct pairs / total pairs
- Each pair is worth equal fraction of total points

### Frontend Notes
- Drag and drop or click-to-connect
- Visual lines showing connections
- Allow easy correction

---

## 6. Ordering (`ordering`)

Arrange items in correct sequence.

### Data Structure

```json
{
  "type": "ordering",
  "question_text": "Put these steps of the fetch-decode-execute cycle in the correct order:",
  "items": [
    {"id": "1", "text": "The instruction is decoded by the control unit", "correct_position": 2},
    {"id": "2", "text": "The instruction is fetched from RAM", "correct_position": 1},
    {"id": "3", "text": "The instruction is executed by the ALU", "correct_position": 3},
    {"id": "4", "text": "The program counter is incremented", "correct_position": 4}
  ],
  "allow_ties": false,
  "feedback": {
    "correct": "Perfect! Fetch, Decode, Execute, then increment the counter.",
    "partial": "{correct}/{total} items in the right position.",
    "incorrect": "The correct order is: Fetch → Decode → Execute → Increment counter."
  }
}
```

### Marking Logic
- Count items in exactly correct position
- Points = correct positions / total items
- Alternative: use Kendall tau distance for more nuanced scoring

### Frontend Notes
- Drag and drop to reorder
- Number indicators showing current position
- "Reset" button to start over

---

## 7. Parsons Problem (`parsons`)

Arrange code blocks to form working program. May include distractors (wrong blocks).

### Data Structure

```json
{
  "type": "parsons",
  "question_text": "Arrange these code blocks to create a program that prints numbers 1 to 5:",
  "blocks": [
    {"id": "b1", "code": "for i in range(1, 6):", "indent": 0, "is_distractor": false},
    {"id": "b2", "code": "print(i)", "indent": 1, "is_distractor": false},
    {"id": "b3", "code": "for i in range(5):", "indent": 0, "is_distractor": true},
    {"id": "b4", "code": "print(i + 1)", "indent": 1, "is_distractor": true}
  ],
  "solution": [
    {"block_id": "b1", "indent": 0},
    {"block_id": "b2", "indent": 1}
  ],
  "alternative_solutions": [
    [
      {"block_id": "b3", "indent": 0},
      {"block_id": "b4", "indent": 1}
    ]
  ],
  "enable_indentation": true,
  "max_distractors_penalty": 0.5,
  "feedback": {
    "correct": "Well done! The for loop with range(1, 6) counts from 1 to 5.",
    "partial": "You're close! Check the range values and indentation.",
    "incorrect": "Not quite. We need a for loop counting from 1 to 5, with print inside the loop."
  }
}
```

### Marking Logic
1. Check if solution matches any valid solution (including alternatives)
2. Check indentation is correct
3. Penalize if distractors included
4. Partial credit for correct blocks in wrong order

### Frontend Notes
- Two-column layout: available blocks | solution area
- Drag and drop between areas
- Indentation handles (if enabled)
- Syntax highlighting for code

---

## 8. Code Completion (`code_completion`)

Fill in blanks in existing code.

### Data Structure

```json
{
  "type": "code_completion",
  "question_text": "Complete this function that calculates the area of a rectangle:",
  "code_template": "def area(width, height):\n    result = width {{BLANK_1}} height\n    {{BLANK_2}} result",
  "blanks": [
    {
      "id": "BLANK_1",
      "correct_answers": ["*", "* "],
      "hint": "What operation calculates area from width and height?"
    },
    {
      "id": "BLANK_2",
      "correct_answers": ["return", "return "],
      "hint": "How do you send a value back from a function?"
    }
  ],
  "feedback": {
    "correct": "Perfect! Multiply width by height and return the result.",
    "partial": "You got {correct}/{total} blanks correct.",
    "incorrect": "Area = width * height. Use 'return' to send the result back."
  }
}
```

### Marking Logic
- Each blank marked independently
- Points = correct blanks / total blanks
- Trim whitespace when comparing

### Frontend Notes
- Display code with input fields in place of blanks
- Monospace font
- Tab to move between blanks

---

## 9. Python Coding (`python_code`)

Write Python code, tested against test cases.

### Data Structure

```json
{
  "type": "python_code",
  "question_text": "Write a function called `is_even` that takes a number and returns True if it's even, False if it's odd.",
  "starter_code": "def is_even(n):\n    # Write your code here\n    pass",
  "test_cases": [
    {"input": "is_even(4)", "expected": "True", "visible": true},
    {"input": "is_even(7)", "expected": "False", "visible": true},
    {"input": "is_even(0)", "expected": "True", "visible": false},
    {"input": "is_even(-2)", "expected": "True", "visible": false}
  ],
  "hidden_test_weight": 0.5,
  "time_limit_seconds": 5,
  "banned_keywords": ["import"],
  "required_keywords": ["def", "return"],
  "feedback": {
    "correct": "Excellent! Your function handles all test cases.",
    "partial": "{passed}/{total} tests passed. Check edge cases like 0 and negative numbers.",
    "incorrect": "Not working yet. Remember: a number is even if it divides by 2 with no remainder (use %)."
  },
  "scaffold": {
    "hint_code": "def is_even(n):\n    # Use the modulo operator %\n    # n % 2 gives the remainder when dividing by 2\n    remainder = n % 2\n    # Return True if remainder is 0\n    pass"
  }
}
```

### Marking Logic
1. Run code in sandboxed Python runner
2. Execute each test case
3. Compare output to expected
4. Score = (visible_tests_passed + hidden_weight * hidden_tests_passed) / total_weighted
5. Check for banned/required keywords

### Frontend Notes
- Code editor with syntax highlighting
- "Run Code" button for testing before submit
- Show visible test results
- Console output display

---

## 10. Code Debugging (`code_debug`)

Find and fix errors in provided code.

### Data Structure

```json
{
  "type": "code_debug",
  "question_text": "This code should print numbers 1 to 5, but it has a bug. Find and fix it.",
  "buggy_code": "for i in range(1, 5):\n    print(i)",
  "bug_description": "The range end value is wrong",
  "correct_code": "for i in range(1, 6):\n    print(i)",
  "alternative_fixes": [
    "for i in range(5):\n    print(i + 1)"
  ],
  "test_cases": [
    {"expected_output": "1\n2\n3\n4\n5\n"}
  ],
  "feedback": {
    "correct": "Great debugging! range(1, 6) gives us 1, 2, 3, 4, 5.",
    "partial": "Your fix works, but there might be a simpler solution.",
    "incorrect": "The bug is in the range. range(1, 5) only goes up to 4. Try range(1, 6)."
  }
}
```

### Marking Logic
1. Run student's fixed code
2. Compare output to expected
3. Full marks if output matches
4. Bonus: compare to known correct solutions

### Frontend Notes
- Pre-filled code editor
- Highlight changes made by student
- Show diff between original and edited

---

## 11. Trace Table (`trace_table`)

Fill in variable values as code executes.

### Data Structure

```json
{
  "type": "trace_table",
  "question_text": "Complete the trace table for this code:",
  "code": "x = 1\nfor i in range(3):\n    x = x * 2\nprint(x)",
  "variables": ["i", "x"],
  "trace_rows": [
    {"step": 1, "description": "After x = 1", "values": {"x": "1"}},
    {"step": 2, "description": "i = 0, after x = x * 2", "values": {"i": "0", "x": "2"}},
    {"step": 3, "description": "i = 1, after x = x * 2", "values": {"i": "1", "x": "4"}},
    {"step": 4, "description": "i = 2, after x = x * 2", "values": {"i": "2", "x": "8"}}
  ],
  "cells_to_fill": [
    {"step": 2, "variable": "x"},
    {"step": 3, "variable": "x"},
    {"step": 4, "variable": "i"},
    {"step": 4, "variable": "x"}
  ],
  "feedback": {
    "correct": "Perfect! You traced through the loop correctly.",
    "partial": "{correct}/{total} values correct. Step through the loop carefully.",
    "incorrect": "Let's trace together: x starts at 1, then doubles each time: 2, 4, 8."
  }
}
```

### Marking Logic
- Each cell marked independently
- Points = correct cells / total cells to fill

### Frontend Notes
- Table layout with code on left
- Pre-filled cells shown, empty inputs for student
- Step-by-step highlighting option

---

## 12. Drag-Drop Label (`drag_label`)

Label parts of a diagram.

### Data Structure

```json
{
  "type": "drag_label",
  "question_text": "Drag the labels to the correct parts of the computer:",
  "image_url": "/api/images/computer-diagram.png",
  "drop_zones": [
    {"id": "z1", "x": 150, "y": 80, "width": 80, "height": 30, "correct_label": "l1"},
    {"id": "z2", "x": 300, "y": 200, "width": 80, "height": 30, "correct_label": "l2"},
    {"id": "z3", "x": 100, "y": 300, "width": 80, "height": 30, "correct_label": "l3"}
  ],
  "labels": [
    {"id": "l1", "text": "CPU"},
    {"id": "l2", "text": "RAM"},
    {"id": "l3", "text": "Hard Drive"},
    {"id": "l4", "text": "Power Supply", "is_distractor": true}
  ],
  "feedback": {
    "correct": "All labels placed correctly!",
    "partial": "{correct}/{total} labels correct.",
    "incorrect": "Review the diagram - the CPU is the processor, RAM is memory sticks, Hard Drive stores files."
  }
}
```

### Marking Logic
- Points = correct placements / total zones
- Distractors don't affect score unless placed

### Frontend Notes
- Image with overlay drop zones
- Draggable labels
- Visual feedback on drop (correct/incorrect if immediate feedback enabled)

---

## 13. Binary Conversion (`binary_convert`)

Convert between binary, decimal, and hexadecimal.

### Data Structure

```json
{
  "type": "binary_convert",
  "question_text": "Convert this binary number to decimal:",
  "conversion_type": "binary_to_decimal",
  "given_value": "10110",
  "correct_answer": "22",
  "show_working": true,
  "working_template": {
    "binary_positions": ["16", "8", "4", "2", "1"],
    "binary_digits": ["1", "0", "1", "1", "0"],
    "calculation": "16 + 0 + 4 + 2 + 0 = 22"
  },
  "feedback": {
    "correct": "Correct! 10110 in binary = 22 in decimal.",
    "incorrect": "Not quite. Remember: 10110 = (1×16) + (0×8) + (1×4) + (1×2) + (0×1) = 22"
  }
}
```

### Conversion Types
- `binary_to_decimal`
- `decimal_to_binary`
- `binary_to_hex`
- `hex_to_binary`
- `hex_to_decimal`
- `decimal_to_hex`

### Marking Logic
- Exact match required (case insensitive for hex)
- No partial credit

### Frontend Notes
- Include working area for showing method
- Binary: show place values
- Hex: show conversion table

---

## 14. Logic Gates (`logic_gates`)

Complete truth tables or identify gate outputs.

### Data Structure

```json
{
  "type": "logic_gates",
  "question_text": "Complete the truth table for an AND gate:",
  "gate_type": "truth_table",
  "gate": "AND",
  "inputs": ["A", "B"],
  "truth_table": [
    {"A": 0, "B": 0, "output": 0, "fill_in": false},
    {"A": 0, "B": 1, "output": 0, "fill_in": true},
    {"A": 1, "B": 0, "output": 0, "fill_in": true},
    {"A": 1, "B": 1, "output": 1, "fill_in": true}
  ],
  "feedback": {
    "correct": "Perfect! AND only outputs 1 when ALL inputs are 1.",
    "partial": "{correct}/{total} rows correct. AND = both inputs must be 1.",
    "incorrect": "Remember: AND gate outputs 1 only when A=1 AND B=1."
  }
}
```

### Marking Logic
- Each cell marked independently
- Points = correct cells / cells to fill

### Frontend Notes
- Table with inputs shown, outputs to fill
- Option to show gate diagram
- 0/1 or True/False toggle

---

## Adding New Question Types

When adding a new question type:

1. Add entry to this document with full specification
2. Create database migration for the type
3. Add schema validation in Pydantic
4. Implement renderer in `web/js/components/question-types/`
5. Implement marker in `backend/app/services/marker.py`
6. Update AI generation prompt in `03-ai-generation.md`
7. Add tests for marking logic
8. Document in teacher help section
