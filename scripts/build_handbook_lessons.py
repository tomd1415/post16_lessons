#!/usr/bin/env python3
"""Populate lesson activities + teacher resources for lessons 3-15 using TeacherHandbook.pdf."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader

MANIFEST_PATH = Path("web/lessons/manifest.json")
HANDBOOK_PATH = Path("plans/TeacherHandbook.pdf")
LESSON_DIR = Path("web/lessons")

TEACHER_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} - Teacher hub</title>
  <link rel="stylesheet" href="../../core/app.css" />
</head>
<body data-lesson-id="{lesson_id}" data-lesson-role="teacher">
  <div class="topbar no-print">
    <div class="container">
      <div class="brand">
        <b data-lesson-title>{title}</b>
        <span data-lesson-summary>Lesson overview loading...</span>
      </div>
      <div class="row">
        <button class="btn" id="teacherToggle" type="button">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class="container">
    <h1 data-lesson-title>{title}</h1>
    <div class="note">
      <b>Timings:</b> <span data-lesson-timings>Loading...</span>
    </div>

    <div class="grid cols2" style="margin-top:12px">
      <div class="card">
        <h2>Objectives</h2>
        <ul class="list" data-lesson-objectives></ul>
      </div>
      <div class="card">
        <h2>Teacher resources</h2>
        <ul class="list" data-lesson-teacher-resources></ul>
      </div>
    </div>

    <div class="grid cols2" style="margin-top:12px">
      <div class="card">
        <h2>Activities</h2>
        <ul class="list" data-lesson-activities></ul>
      </div>
      <div class="card">
        <h2>External links</h2>
        <ul class="list" data-lesson-links></ul>
      </div>
    </div>

    <div class="footer">
      <div id="toast" class="toast" role="status" aria-live="polite"></div>
    </div>
  </div>

  <script src="../../core/app.js"></script>
  <script src="../../core/lesson-pack.js"></script>
</body>
</html>
"""

STUDENT_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} - Student hub</title>
  <link rel="stylesheet" href="../../core/app.css" />
</head>
<body data-lesson-id="{lesson_id}" data-lesson-role="student">
  <div class="topbar no-print">
    <div class="container">
      <div class="brand">
        <b data-lesson-title>{title}</b>
        <span data-lesson-summary>Lesson overview loading...</span>
      </div>
      <div class="row">
        <button class="btn" id="teacherToggle" type="button">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class="container">
    <h1 data-lesson-title>{title}</h1>
    <div class="note">
      <b>Timings:</b> <span data-lesson-timings>Loading...</span>
    </div>

    <div class="grid cols2" style="margin-top:12px">
      <div class="card">
        <h2>Lesson overview</h2>
        <p data-lesson-summary>Loading...</p>
      </div>
      <div class="card">
        <h2>Objectives</h2>
        <ul class="list" data-lesson-objectives></ul>
      </div>
    </div>

    <div class="card" style="margin-top:12px">
      <h2>Activities</h2>
      <ul class="list" data-lesson-activities></ul>
    </div>

    <div class="footer">
      <div id="toast" class="toast" role="status" aria-live="polite"></div>
    </div>
  </div>

  <script src="../../core/app.js"></script>
  <script src="../../core/lesson-pack.js"></script>
</body>
</html>
"""
LESSON_CHECKS: Dict[int, List[dict]] = {
    3: [
        {
            "q": "Which flowchart symbol represents a decision?",
            "options": ["Rectangle", "Diamond", "Oval"],
            "correct": "b",
        },
        {
            "q": "A sequence in an algorithm means...",
            "options": [
                "instructions followed in order",
                "random choices with no order",
                "skipping steps to save time",
            ],
            "correct": "a",
        },
        {
            "q": "Pseudocode is best described as...",
            "options": [
                "code that runs directly on a computer",
                "structured plain-language steps",
                "a type of flowchart symbol",
            ],
            "correct": "b",
        },
    ],
    4: [
        {
            "q": "What file extension is used for Python programs?",
            "options": [".txt", ".py", ".doc"],
            "correct": "b",
        },
        {
            "q": "Which action runs a program?",
            "options": ["Run/Execute", "Save", "Close"],
            "correct": "a",
        },
        {
            "q": "Saving a program means...",
            "options": [
                "storing the code so it can be opened again",
                "printing the code to paper",
                "deleting the code after running",
            ],
            "correct": "a",
        },
    ],
    5: [
        {
            "q": "Which operation happens first without parentheses?",
            "options": ["Addition", "Multiplication", "Subtraction"],
            "correct": "b",
        },
        {
            "q": "Parentheses in an expression mean...",
            "options": [
                "evaluate inside first",
                "ignore everything inside",
                "subtract inside first",
            ],
            "correct": "a",
        },
        {
            "q": "Which symbol means division in Python?",
            "options": ["%", "/", "//"],
            "correct": "b",
        },
    ],
    6: [
        {
            "q": "Which is a Boolean value?",
            "options": ["True", "42", "hello"],
            "correct": "a",
        },
        {
            "q": "A variable is used to...",
            "options": [
                "store data that can change",
                "print data only",
                "delete data",
            ],
            "correct": "a",
        },
        {
            "q": "Which line assigns a value to a variable?",
            "options": ["score == 10", "score = 10", "10 = score"],
            "correct": "b",
        },
    ],
    7: [
        {
            "q": "AND is true only when...",
            "options": [
                "both conditions are true",
                "either condition is true",
                "both conditions are false",
            ],
            "correct": "a",
        },
        {
            "q": "OR is true when...",
            "options": [
                "at least one condition is true",
                "both conditions are false",
                "only the first condition is true",
            ],
            "correct": "a",
        },
        {
            "q": "NOT does what to a Boolean value?",
            "options": ["Flips it", "Doubles it", "Leaves it unchanged"],
            "correct": "a",
        },
    ],
    8: [
        {
            "q": "Which is an ordered collection in Python?",
            "options": ["List", "Boolean", "Integer"],
            "correct": "a",
        },
        {
            "q": "A tuple is...",
            "options": ["immutable", "random", "a loop"],
            "correct": "a",
        },
        {
            "q": "List indexing in Python starts at...",
            "options": ["0", "1", "-1 only"],
            "correct": "a",
        },
    ],
    9: [
        {
            "q": "Comments are...",
            "options": [
                "ignored by the interpreter",
                "required to run code",
                "used to store numbers",
            ],
            "correct": "a",
        },
        {
            "q": "Good indentation helps by...",
            "options": [
                "showing code structure clearly",
                "making code run faster",
                "removing errors automatically",
            ],
            "correct": "a",
        },
        {
            "q": "Descriptive names make code...",
            "options": ["easier to understand", "slower", "shorter"],
            "correct": "a",
        },
    ],
    10: [
        {
            "q": "A conditional statement lets a program...",
            "options": ["choose between paths", "repeat forever", "store data"],
            "correct": "a",
        },
        {
            "q": "A logic test evaluates to...",
            "options": ["True or False", "a list", "a file"],
            "correct": "a",
        },
        {
            "q": "Which operator checks equality?",
            "options": ["=", "==", ":="],
            "correct": "b",
        },
    ],
    11: [
        {
            "q": "A parameter is...",
            "options": ["an input to a function", "a loop", "an error"],
            "correct": "a",
        },
        {
            "q": "A function typically...",
            "options": ["returns a value", "prints only", "never uses parameters"],
            "correct": "a",
        },
        {
            "q": "A procedure is usually a named block that...",
            "options": ["performs a task", "stores a list", "opens files only"],
            "correct": "a",
        },
    ],
    12: [
        {
            "q": "A loop is used to...",
            "options": ["repeat instructions", "stop a program", "rename files"],
            "correct": "a",
        },
        {
            "q": "A while loop repeats while...",
            "options": ["a condition is true", "a file is open", "time runs out"],
            "correct": "a",
        },
        {
            "q": "An infinite loop happens when...",
            "options": [
                "the exit condition never becomes false",
                "the program is saved",
                "there are no variables",
            ],
            "correct": "a",
        },
    ],
    13: [
        {
            "q": "A library provides...",
            "options": ["reusable code", "random errors", "hardware only"],
            "correct": "a",
        },
        {
            "q": "An event handler responds to...",
            "options": [
                "user actions like clicks",
                "variable names",
                "file extensions",
            ],
            "correct": "a",
        },
        {
            "q": "Which statement brings in a library?",
            "options": ["import", "print", "return"],
            "correct": "a",
        },
    ],
    14: [
        {
            "q": "Recursion means...",
            "options": [
                "a function calls itself",
                "a loop stops immediately",
                "a variable never changes",
            ],
            "correct": "a",
        },
        {
            "q": "A base case is used to...",
            "options": ["stop recursion", "start a loop", "print a file"],
            "correct": "a",
        },
        {
            "q": "Each recursive call should...",
            "options": [
                "move closer to the base case",
                "restart from the beginning",
                "ignore the previous call",
            ],
            "correct": "a",
        },
    ],
    15: [
        {
            "q": "A syntax error is...",
            "options": [
                "invalid code structure",
                "a slow program",
                "an improvement idea",
            ],
            "correct": "a",
        },
        {
            "q": "A logic error means...",
            "options": [
                "the program runs but gives the wrong result",
                "the file is missing",
                "the code will not start",
            ],
            "correct": "a",
        },
        {
            "q": "Testing helps by...",
            "options": [
                "checking against requirements",
                "removing all comments",
                "making code run instantly",
            ],
            "correct": "a",
        },
    ],
}


def normalize(text: str) -> str:
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\u2018", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u00a0", " ")
    text = text.encode("ascii", "ignore").decode("ascii")
    return text


def clean_lines(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        section_match = re.match(r"^\d+\.\d+\s+(.+)$", line)
        if section_match:
            line = section_match.group(1).strip()
        if "Teacher Handbook" in line:
            continue
        if "PageFooterText" in line:
            continue
        if line.startswith("Page "):
            continue
        if line.startswith("ICDL Thinking"):
            continue
        lines.append(line)
    return "\n".join(lines)


def extract_section(text: str, start_marker: str, end_marker: str | None) -> str:
    if start_marker not in text:
        return ""
    start = text.index(start_marker) + len(start_marker)
    if end_marker and end_marker in text[start:]:
        end = text.index(end_marker, start)
        return text[start:end].strip()
    return text[start:].strip()


def parse_resource_blocks(section_text: str) -> List[dict]:
    resources = []
    if not section_text:
        return resources
    blocks = re.split(r"Resource:\s*", section_text)
    for block in blocks[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        desc = "\n".join(lines[1:])
        url = None
        m_url = re.search(r"URL:\s*(\S+)", block)
        if m_url:
            url = m_url.group(1).strip()
        m_obj = re.search(r"Learning Objective:\s*(.*?)\n", block)
        m_use = re.search(r"Suggested Use:\s*(.*?)\n", block)
        learning_objective = m_obj.group(1).strip() if m_obj else ""
        suggested_use = m_use.group(1).strip() if m_use else ""

        desc = re.sub(r"^Learning Objective:.*$", "", desc, flags=re.MULTILINE)
        desc = re.sub(r"^Suggested Use:.*$", "", desc, flags=re.MULTILINE)
        desc = re.sub(r"^URL:.*$", "", desc, flags=re.MULTILINE)
        desc = clean_lines(desc)
        resources.append(
            {
                "title": title,
                "url": url,
                "learning_objective": learning_objective,
                "suggested_use": suggested_use,
                "description": desc.strip(),
            }
        )
    return resources


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def render_quick_checks(lesson_num: int) -> str:
    checks = LESSON_CHECKS.get(lesson_num, [])
    html_parts = []
    for idx, check in enumerate(checks, start=1):
        qid = f"q{idx}"
        html_parts.append(f"        <p><b>Prompt {idx}:</b> {check['q']}</p>")
        html_parts.append(f"        <div data-quiz=\"{qid}\" data-correct=\"{check['correct']}\">")
        for opt_idx, option in enumerate(check["options"]):
            letter = chr(ord("a") + opt_idx)
            html_parts.append(
                "          "
                + f"<label class=\"choice\"><input type=\"radio\" name=\"{qid}\" value=\"{letter}\"> {option}</label>"
            )
        html_parts.append("        </div>")
        html_parts.append("        <div class=\"row\" style=\"margin-top:8px\">")
        html_parts.append(
            f"          <button class=\"btn good\" data-quiz-check=\"{qid}\" type=\"button\">Check</button>"
        )
        html_parts.append("        </div>")
        html_parts.append(
            f"        <div class=\"note\" data-quiz-feedback=\"{qid}\" style=\"margin-top:10px; display:none\"></div>"
        )
        if idx != len(checks):
            html_parts.append("\n        <div style=\"height:10px\"></div>")
    return "\n".join(html_parts)


def render_instructions(description: str) -> str:
    if not description:
        return ""
    lines = [line.strip() for line in description.splitlines() if line.strip()]
    roman_items = []
    bullet_items = []
    paragraphs = []
    for line in lines:
        if re.match(r"^(?:[ivx]+)\.", line, re.IGNORECASE):
            roman_items.append(re.sub(r"^(?:[ivx]+)\.\s*", "", line))
        elif line.startswith("-") or line.startswith("*") or line.startswith("\u2022"):
            bullet_items.append(line.lstrip("-* \u2022"))
        else:
            paragraphs.append(line)

    html_parts = []
    for para in paragraphs:
        html_parts.append(f"<p>{para}</p>")
    if roman_items:
        html_parts.append("<ol>")
        for item in roman_items:
            html_parts.append(f"  <li>{item}</li>")
        html_parts.append("</ol>")
    if bullet_items:
        html_parts.append("<ul>")
        for item in bullet_items:
            html_parts.append(f"  <li>{item}</li>")
        html_parts.append("</ul>")
    return "\n".join(html_parts)


def render_activity_html(lesson_id: str, activity_id: str, title: str, lesson_num: int, resource: dict, objectives: List[dict]) -> str:
    quick_checks = render_quick_checks(lesson_num)
    instructions = render_instructions(resource.get("description", ""))
    learning_objective = resource.get("learning_objective", "").strip()
    suggested_use = resource.get("suggested_use", "").strip()

    teacher_items = []
    for idx, check in enumerate(LESSON_CHECKS.get(lesson_num, []), start=1):
        correct_idx = ord(check["correct"]) - ord("a")
        correct_text = check["options"][correct_idx]
        teacher_items.append(f"<li>Quick check {idx}: {correct_text}</li>")
    if learning_objective:
        teacher_items.append(f"<li>Learning objective focus: {learning_objective}</li>")
    teacher_items.append("<li>Look for clear steps and correct use of key terms.</li>")

    teacher_guidance = "\n".join(teacher_items)

    step3_intro = []
    if learning_objective:
        step3_intro.append(f"<div class=\"note\"><b>Learning objective:</b> {learning_objective}</div>")
    if suggested_use:
        step3_intro.append(f"<p><b>Suggested use:</b> {suggested_use}</p>")
    if instructions:
        step3_intro.append(instructions)
    step3_intro_html = "\n".join(step3_intro)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>{activity_id} - {title}</title>
  <link rel=\"stylesheet\" href=\"../../../core/app.css\" />
</head>
<body data-lesson-id=\"{lesson_id}\" data-activity-id=\"{activity_id}\">
  <div class=\"topbar no-print\">
    <div class=\"container\">
      <div class=\"brand\">
        <b>{activity_id} - {title}</b>
        <span>Activity scaffold (structured steps + instant feedback)</span>
      </div>
      <div class=\"row\">
        <a class=\"pill\" href=\"../index.html\"><strong>HOME</strong> <span>Teacher hub</span></a>
        <a class=\"pill\" href=\"../student.html\"><strong>STUDENT</strong> <span>Student hub</span></a>
        <button class=\"btn\" id=\"teacherToggle\" type=\"button\">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class=\"container\">
    <h1>{activity_id} - {title}</h1>
    <div class=\"note\">
      <b>How this works:</b> This activity is broken into small steps with quick checks and spaces to add your own ideas.
    </div>

    <div class=\"grid cols2\" style=\"margin-top:12px\">
      <div class=\"card\">
        <h2>Step 1: Quick checks</h2>
{quick_checks}
      </div>

      <div class=\"card\">
        <h2>Step 2: Key ideas in your own words</h2>
        <p>Explain the main idea of <b>{title}</b> in one or two sentences.</p>
        <textarea data-field=\"step2_notes\" placeholder=\"Write your notes here...\"></textarea>
      </div>
    </div>

    <div class=\"card\" style=\"margin-top:12px\">
      <h2>Step 3: Build the main task</h2>
      {step3_intro_html}
      <ul class=\"list checklist\">
        <li><label><input type=\"checkbox\" data-check=\"goal\"> I can describe the goal in one clear sentence.</label></li>
        <li><label><input type=\"checkbox\" data-check=\"inputs\"> I can list the inputs or information needed.</label></li>
        <li><label><input type=\"checkbox\" data-check=\"steps\"> I can outline the main steps in order.</label></li>
        <li><label><input type=\"checkbox\" data-check=\"test\"> I can describe how to test if it works.</label></li>
      </ul>
      <div style=\"margin-top:10px\"></div>
      <label for=\"taskNotes\"><b>Your structured notes</b></label>
      <textarea id=\"taskNotes\" data-field=\"task_notes\" placeholder=\"Requirement 1: ...\nRequirement 2: ...\"></textarea>
    </div>

    <div class=\"card\" style=\"margin-top:12px\">
      <h2>Step 4: Reflection</h2>
      <p>Encourage pupils to note what was easy, what was tricky, and what they would change.</p>
      <textarea data-field=\"reflection\" placeholder=\"What went well? What would you do differently next time?\"></textarea>
    </div>

    <div class=\"teacher-only card\" style=\"margin-top:12px; display:none\">
      <h2>Teacher guidance (answer prompts)</h2>
      <ul class=\"list\">
        {teacher_guidance}
      </ul>
    </div>

    <div class=\"footer\">
      <div id=\"toast\" class=\"toast\" role=\"status\" aria-live=\"polite\"></div>
      <div class=\"no-print\">
        <hr class=\"sep\"/>
        <small>
          Tip: add <span class=\"kbd\">?teacher=1</span> to the URL to force teacher mode on.
        </small>
      </div>
    </div>
  </div>

  <script src=\"../../../core/app.js\"></script>
  <script src=\"../../../core/activity-scaffold.js\"></script>
</body>
</html>
"""


def render_lesson_plan(lesson: dict, overview: str, exercises: List[dict], additional: List[dict]) -> str:
    objectives_html = "\n".join(
        f"<li>{obj['text']}</li>" for obj in lesson.get("objectives", [])
    )
    exercises_html = "\n".join(
        f"<li><b>{ex['title']}</b> — {ex.get('learning_objective', '')}</li>" for ex in exercises
    )
    add_html = []
    for item in additional:
        if item.get("url"):
            add_html.append(
                f"<li><b>{item['title']}</b> — <a href=\"{item['url']}\">{item['url']}</a></li>"
            )
        else:
            add_html.append(f"<li><b>{item['title']}</b></li>")
    additional_html = "\n".join(add_html)

    overview_html = "".join(f"<p>{line}</p>" for line in overview.splitlines() if line)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>Lesson plan - {lesson['title']}</title>
  <link rel=\"stylesheet\" href=\"../../../core/app.css\" />
</head>
<body>
  <div class=\"topbar no-print\">
    <div class=\"container\">
      <div class=\"brand\">
        <b>Thinking like a Coder — {lesson['title']}</b>
        <span>Teacher resource (lesson plan)</span>
      </div>
      <div class=\"row\">
        <a class=\"pill\" href=\"../index.html\"><strong>HOME</strong> <span>Teacher hub</span></a>
        <a class=\"pill\" href=\"../student.html\"><strong>STUDENT</strong> <span>Student hub</span></a>
        <button class=\"btn\" id=\"teacherToggle\" type=\"button\">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class=\"container\">
    <h1>Lesson plan</h1>

    <div class=\"card\">
      <h2>Overview</h2>
      {overview_html or '<p>Lesson overview text not provided in handbook.</p>'}
    </div>

    <div class=\"grid cols2\" style=\"margin-top:12px\">
      <div class=\"card\">
        <h2>Learning objectives</h2>
        <ul class=\"list\">
          {objectives_html}
        </ul>
      </div>
      <div class=\"card\">
        <h2>Exercises in this lesson</h2>
        <ul class=\"list\">
          {exercises_html or '<li>No exercises listed.</li>'}
        </ul>
      </div>
    </div>

    <div class=\"card\" style=\"margin-top:12px\">
      <h2>Additional resources</h2>
      <ul class=\"list\">
        {additional_html or '<li>No additional resources listed.</li>'}
      </ul>
    </div>

    <div class=\"footer\">
      <div id=\"toast\" class=\"toast\" role=\"status\" aria-live=\"polite\"></div>
    </div>
  </div>

  <script src=\"../../../core/app.js\"></script>
</body>
</html>
"""


def render_print_cards(lesson: dict, exercises: List[dict]) -> str:
    cards = []
    for ex in exercises:
        cards.append(
            """
      <div class=\"card\">
        <h2>{title}</h2>
        <ul class=\"list\">
          <li>State the goal in one clear sentence.</li>
          <li>List the key steps or inputs/outputs.</li>
          <li>Create your solution using the target technique.</li>
        </ul>
      </div>
""".format(title=ex["title"])
        )
    cards_html = "\n".join(cards)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>Printable cards - {lesson['title']}</title>
  <link rel=\"stylesheet\" href=\"../../../core/app.css\" />
</head>
<body>
  <div class=\"topbar no-print\">
    <div class=\"container\">
      <div class=\"brand\">
        <b>Thinking like a Coder — {lesson['title']}</b>
        <span>Printable prompt cards</span>
      </div>
      <div class=\"row\">
        <a class=\"pill\" href=\"../index.html\"><strong>HOME</strong> <span>Teacher hub</span></a>
        <a class=\"pill\" href=\"../student.html\"><strong>STUDENT</strong> <span>Student hub</span></a>
        <button class=\"btn\" id=\"teacherToggle\" type=\"button\">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class=\"container\">
    <h1>Printable cards</h1>
    <div class=\"note\">
      Print and cut these cards for quick prompts or station work.
    </div>

    <div class=\"grid cols2\" style=\"margin-top:12px\">
{cards_html}
    </div>

    <div class=\"footer\">
      <div id=\"toast\" class=\"toast\" role=\"status\" aria-live=\"polite\"></div>
    </div>
  </div>

  <script src=\"../../../core/app.js\"></script>
</body>
</html>
"""


def render_answer_key(lesson: dict, answers_text: str, lesson_num: int) -> str:
    answer_lines = [line for line in answers_text.splitlines() if line.strip()]
    answer_html = "".join(f"<p>{line}</p>" for line in answer_lines)

    check_items = []
    for idx, check in enumerate(LESSON_CHECKS.get(lesson_num, []), start=1):
        correct_idx = ord(check["correct"]) - ord("a")
        correct_text = check["options"][correct_idx]
        check_items.append(f"<li>Quick check {idx}: {correct_text}</li>")
    checks_html = "\n".join(check_items)

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>Answer guidance - {lesson['title']}</title>
  <link rel=\"stylesheet\" href=\"../../../core/app.css\" />
</head>
<body>
  <div class=\"topbar no-print\">
    <div class=\"container\">
      <div class=\"brand\">
        <b>Thinking like a Coder — {lesson['title']}</b>
        <span>Answer guidance</span>
      </div>
      <div class=\"row\">
        <a class=\"pill\" href=\"../index.html\"><strong>HOME</strong> <span>Teacher hub</span></a>
        <a class=\"pill\" href=\"../student.html\"><strong>STUDENT</strong> <span>Student hub</span></a>
        <button class=\"btn\" id=\"teacherToggle\" type=\"button\">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class=\"container\">
    <h1>Answer guidance</h1>

    <div class=\"card\">
      <h2>Quick check answers</h2>
      <ul class=\"list\">
        {checks_html}
      </ul>
    </div>

    <div class=\"card\" style=\"margin-top:12px\">
      <h2>Review question answers (from handbook)</h2>
      {answer_html or '<p>No review answers listed in handbook.</p>'}
    </div>

    <div class=\"footer\">
      <div id=\"toast\" class=\"toast\" role=\"status\" aria-live=\"polite\"></div>
    </div>
  </div>

  <script src=\"../../../core/app.js\"></script>
</body>
</html>
"""


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    lessons = {lesson["id"]: lesson for lesson in manifest.get("lessons", [])}

    reader = PdfReader(str(HANDBOOK_PATH))
    page_texts = [normalize(p.extract_text() or "") for p in reader.pages]

    # Identify lesson start pages based on "Learning objectives" heading.
    lesson_start = {}
    for i, text in enumerate(page_texts):
        if "Learning objectives" not in text:
            continue
        m = re.search(r"LESSON\s+(\d+)\s+-|Lesson\s+(\d+)\s+-", text)
        if m:
            nums = [g for g in m.groups() if g]
            if nums:
                lesson_start[int(nums[0])] = i

    lesson_nums = sorted(lesson_start)
    lesson_ranges = {}
    for idx, n in enumerate(lesson_nums):
        start = lesson_start[n]
        end = (lesson_start[lesson_nums[idx + 1]] - 1) if idx + 1 < len(lesson_nums) else len(page_texts) - 1
        lesson_ranges[n] = (start, end)

    for lesson_num in range(3, 16):
        lesson_id = f"lesson-{lesson_num}"
        lesson = lessons.get(lesson_id)
        if not lesson:
            continue
        start, end = lesson_ranges[lesson_num]
        lesson_text = clean_lines("\n".join(page_texts[start:end + 1]))

        overview = extract_section(lesson_text, "LESSON OVERVIEW", "ADDITIONAL RESOURCES")
        additional_text = extract_section(lesson_text, "ADDITIONAL RESOURCES", "EXERCISES")
        exercises_text = extract_section(lesson_text, "EXERCISES", "ANSWERS TO REVIEW QUESTIONS")
        answers_text = extract_section(lesson_text, "ANSWERS TO REVIEW QUESTIONS", None)

        additional_resources = parse_resource_blocks(additional_text)
        exercises = parse_resource_blocks(exercises_text)

        # Build activities in manifest.
        activities = []
        for idx, resource in enumerate(exercises, start=1):
            slug = slugify(resource["title"])
            activity_id = f"a{idx:02d}"
            filename = f"{idx:02d}-{slug}.html"
            activities.append(
                {
                    "id": activity_id,
                    "title": resource["title"],
                    "path": f"/lessons/{lesson_id}/activities/{filename}",
                    "objectiveIds": [obj["id"] for obj in lesson.get("objectives", [])],
                    "expectedEvidence": "Completed task output and written notes.",
                    "rubricHook": None,
                }
            )
        lesson["activities"] = activities
        if lesson.get("status") == "placeholder":
            lesson["status"] = "draft"

        # Ensure lesson pack files exist and are updated.
        lesson_dir = LESSON_DIR / lesson_id
        activities_dir = lesson_dir / "activities"
        activities_dir.mkdir(parents=True, exist_ok=True)

        lesson_dir.mkdir(parents=True, exist_ok=True)
        (lesson_dir / "index.html").write_text(
            TEACHER_TEMPLATE.format(title=lesson.get("title", lesson_id), lesson_id=lesson_id)
        )
        (lesson_dir / "student.html").write_text(
            STUDENT_TEMPLATE.format(title=lesson.get("title", lesson_id), lesson_id=lesson_id)
        )

        for idx, resource in enumerate(exercises, start=1):
            slug = slugify(resource["title"])
            activity_id = f"a{idx:02d}"
            filename = f"{idx:02d}-{slug}.html"
            path = activities_dir / filename
            html = render_activity_html(lesson_id, activity_id, resource["title"], lesson_num, resource, lesson.get("objectives", []))
            path.write_text(html)

        # Teacher resources
        teacher_dir = lesson_dir / "teacher"
        teacher_dir.mkdir(parents=True, exist_ok=True)
        (teacher_dir / "lesson-plan.html").write_text(
            render_lesson_plan(lesson, overview, exercises, additional_resources)
        )
        (teacher_dir / "print-cards.html").write_text(
            render_print_cards(lesson, exercises)
        )
        (teacher_dir / "answer-key.html").write_text(
            render_answer_key(lesson, answers_text, lesson_num)
        )

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print("Updated lessons 3-15 from handbook.")


if __name__ == "__main__":
    main()
