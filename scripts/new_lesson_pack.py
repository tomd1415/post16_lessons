#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


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


ACTIVITY_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="../../../core/app.css" />
</head>
<body data-lesson-id="{lesson_id}" data-activity-id="{activity_id}">
  <div class="topbar no-print">
    <div class="container">
      <div class="brand">
        <b>{title}</b>
        <span>Activity scaffold (structured steps + instant feedback)</span>
      </div>
      <div class="row">
        <a class="pill" href="../index.html"><strong>HOME</strong> <span>Teacher hub</span></a>
        <a class="pill" href="../student.html"><strong>STUDENT</strong> <span>Student hub</span></a>
        <button class="btn" id="teacherToggle" type="button">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class="container">
    <h1>{title}</h1>
    <div class="note">
      <b>How this works:</b> This activity is broken into small steps with quick checks and spaces to add your own ideas.
    </div>

    <div class="grid cols2" style="margin-top:12px">
      <div class="card">
        <h2>Step 1: Quick checks</h2>
        <p><b>Prompt 1:</b> Replace this with a simple question that builds confidence.</p>
        <div data-quiz="q1" data-correct="b">
          <label class="choice"><input type="radio" name="q1" value="a"> Option A (replace)</label>
          <label class="choice"><input type="radio" name="q1" value="b"> Option B (correct)</label>
          <label class="choice"><input type="radio" name="q1" value="c"> Option C (replace)</label>
        </div>
        <div class="row" style="margin-top:8px">
          <button class="btn good" data-quiz-check="q1" type="button">Check</button>
        </div>
        <div class="note" data-quiz-feedback="q1" style="margin-top:10px; display:none"></div>

        <div style="height:10px"></div>
        <p><b>Prompt 2:</b> Add a second quick check for instant feedback.</p>
        <div data-quiz="q2" data-correct="a">
          <label class="choice"><input type="radio" name="q2" value="a"> Option A (correct)</label>
          <label class="choice"><input type="radio" name="q2" value="b"> Option B (replace)</label>
          <label class="choice"><input type="radio" name="q2" value="c"> Option C (replace)</label>
        </div>
        <div class="row" style="margin-top:8px">
          <button class="btn good" data-quiz-check="q2" type="button">Check</button>
        </div>
        <div class="note" data-quiz-feedback="q2" style="margin-top:10px; display:none"></div>

        <div style="height:10px"></div>
        <p><b>Prompt 3:</b> Add a third quick check to reinforce understanding.</p>
        <div data-quiz="q3" data-correct="c">
          <label class="choice"><input type="radio" name="q3" value="a"> Option A (replace)</label>
          <label class="choice"><input type="radio" name="q3" value="b"> Option B (replace)</label>
          <label class="choice"><input type="radio" name="q3" value="c"> Option C (correct)</label>
        </div>
        <div class="row" style="margin-top:8px">
          <button class="btn good" data-quiz-check="q3" type="button">Check</button>
        </div>
        <div class="note" data-quiz-feedback="q3" style="margin-top:10px; display:none"></div>
      </div>

      <div class="card">
        <h2>Step 2: Key ideas in your own words</h2>
        <p>Prompt pupils to explain a term or idea in one or two sentences.</p>
        <textarea data-field="step2_notes" placeholder="Write your notes here..."></textarea>
      </div>
    </div>

    <div class="card" style="margin-top:12px">
      <h2>Step 3: Build the main task</h2>
      <p>Break the big task into smaller checkpoints before pupils attempt the full task.</p>
      <ul class="list checklist">
        <li><label><input type="checkbox" data-check="goal"> I can describe the goal in one clear sentence.</label></li>
        <li><label><input type="checkbox" data-check="inputs"> I can list the inputs or information needed.</label></li>
        <li><label><input type="checkbox" data-check="steps"> I can outline the main steps in order.</label></li>
        <li><label><input type="checkbox" data-check="test"> I can describe how to test if it works.</label></li>
      </ul>
      <div style="margin-top:10px"></div>
      <label for="taskNotes"><b>Your structured notes</b></label>
      <textarea id="taskNotes" data-field="task_notes" placeholder="Requirement 1: ...&#10;Requirement 2: ..."></textarea>
    </div>

    <div class="card" style="margin-top:12px">
      <h2>Step 4: Reflection</h2>
      <p>Encourage pupils to note what was easy, what was tricky, and what they would change.</p>
      <textarea data-field="reflection" placeholder="What went well? What would you do differently next time?"></textarea>
    </div>

    <div class="teacher-only card" style="margin-top:12px; display:none">
      <h2>Teacher guidance (answer prompts)</h2>
      <ul class="list">
        <li>Quick check answers: replace with the correct options.</li>
        <li>Key ideas to listen for in pupil notes.</li>
        <li>Common misconceptions and follow-up prompts.</li>
      </ul>
    </div>

    <div class="footer">
      <div id="toast" class="toast" role="status" aria-live="polite"></div>
      <div class="no-print">
        <hr class="sep"/>
        <small>
          Tip: add <span class="kbd">?teacher=1</span> to the URL to force teacher mode on.
        </small>
      </div>
    </div>
  </div>

  <script src="../../../core/app.js"></script>
  <script src="../../../core/activity-scaffold.js"></script>
</body>
</html>
"""

TEACHER_RESOURCE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{resource_title} - {lesson_title}</title>
  <link rel="stylesheet" href="../../../core/app.css" />
</head>
<body>
  <div class="topbar no-print">
    <div class="container">
      <div class="brand">
        <b>Thinking like a Coder — {lesson_title}</b>
        <span>Teacher resource (draft)</span>
      </div>
      <div class="row">
        <a class="pill" href="../index.html"><strong>HOME</strong> <span>Teacher hub</span></a>
        <a class="pill" href="../student.html"><strong>STUDENT</strong> <span>Student hub</span></a>
        <button class="btn" id="teacherToggle" type="button">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class="container">
    <h1>{resource_title}</h1>
    <div class="note warn">
      This resource is a structured placeholder. Replace the content using Lesson 1 style and layout.
    </div>

    <div class="card">
      <h2>What to add</h2>
      <ul class="list">
        {resource_items}
      </ul>
    </div>

    <div class="footer">
      <div id="toast" class="toast" role="status" aria-live="polite"></div>
    </div>
  </div>

  <script src="../../../core/app.js"></script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Scaffold a lesson pack from the manifest.")
    parser.add_argument("--lesson-id", required=True, help="Lesson id, e.g. lesson-2")
    parser.add_argument("--manifest", default="web/lessons/manifest.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    lessons = manifest.get("lessons", [])
    lesson = next((item for item in lessons if item.get("id") == args.lesson_id), None)
    if not lesson:
        raise SystemExit(f"Lesson not found in manifest: {args.lesson_id}")

    title = lesson.get("title") or args.lesson_id
    lesson_dir = Path("web/lessons") / args.lesson_id
    lesson_dir.mkdir(parents=True, exist_ok=True)

    teacher_path = lesson_dir / "index.html"
    student_path = lesson_dir / "student.html"
    if args.force or not teacher_path.exists():
        teacher_path.write_text(TEACHER_TEMPLATE.format(title=title, lesson_id=args.lesson_id))
    if args.force or not student_path.exists():
        student_path.write_text(STUDENT_TEMPLATE.format(title=title, lesson_id=args.lesson_id))

    activities = lesson.get("activities") or []
    if activities:
        activities_dir = lesson_dir / "activities"
        activities_dir.mkdir(parents=True, exist_ok=True)
        for activity in activities:
            filename = activity.get("path", "").split("/")[-1]
            if not filename:
                continue
            path = activities_dir / filename
            if args.force or not path.exists():
                activity_title = f"{activity.get('id', '')} - {activity.get('title', 'Activity')}"
                path.write_text(
                    ACTIVITY_TEMPLATE.format(
                        title=activity_title.strip(" -"),
                        lesson_id=args.lesson_id,
                        activity_id=activity.get("id", ""),
                    )
                )

    teacher_resources = list(lesson.get("teacherResources") or [])
    default_resources = [
        {"title": "Lesson plan", "path": f"/lessons/{args.lesson_id}/teacher/lesson-plan.html"},
        {"title": "Printable cards", "path": f"/lessons/{args.lesson_id}/teacher/print-cards.html"},
        {"title": "Answer guidance", "path": f"/lessons/{args.lesson_id}/teacher/answer-key.html"},
    ]
    existing_paths = {item.get("path") for item in teacher_resources if item.get("path")}
    for resource in default_resources:
        if resource["path"] not in existing_paths:
            teacher_resources.append(resource)
            existing_paths.add(resource["path"])
    if teacher_resources != lesson.get("teacherResources"):
        lesson["teacherResources"] = teacher_resources
        Path(args.manifest).write_text(json.dumps(manifest, indent=2))

    teacher_dir = lesson_dir / "teacher"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    resource_templates = [
        (
            "lesson-plan.html",
            "Lesson plan",
            [
                "<li>Lesson overview, objectives, timings, and key vocabulary.</li>",
                "<li>Suggested teaching sequence and pacing.</li>",
                "<li>Assessment checkpoints and differentiation notes.</li>",
            ],
        ),
        (
            "print-cards.html",
            "Printable cards",
            [
                "<li>Printable prompt/term cards for classroom use.</li>",
                "<li>Any supporting diagrams or templates.</li>",
                "<li>Notes on printing and cutting.</li>",
            ],
        ),
        (
            "answer-key.html",
            "Answer guidance",
            [
                "<li>Expected answers for auto-marked checks.</li>",
                "<li>Guidance for open-ended responses.</li>",
                "<li>Common misconceptions and prompts.</li>",
            ],
        ),
    ]
    for filename, title, items in resource_templates:
        path = teacher_dir / filename
        if args.force or not path.exists():
            path.write_text(
                TEACHER_RESOURCE_TEMPLATE.format(
                    resource_title=title,
                    lesson_title=lesson.get("title") or args.lesson_id,
                    resource_items="".join(items),
                )
            )

    print(f"Lesson pack ready: {lesson_dir}")


if __name__ == "__main__":
    main()
