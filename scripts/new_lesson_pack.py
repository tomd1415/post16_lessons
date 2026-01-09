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
<body>
  <div class="topbar no-print">
    <div class="container">
      <div class="brand">
        <b>{title}</b>
        <span>Activity placeholder (content coming soon)</span>
      </div>
      <div class="row">
        <button class="btn" id="teacherToggle" type="button">Teacher mode: OFF</button>
      </div>
    </div>
  </div>

  <div class="container">
    <h1>{title}</h1>
    <div class="note warn">
      This activity shell is ready for content. Replace this with the real activity in Lesson 1 style.
    </div>

    <div class="card">
      <h2>What to add</h2>
      <ul class="list">
        <li>Student instructions</li>
        <li>Inputs and interactions</li>
        <li>Autosave hooks for activity state</li>
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
    lesson = next((item for item in manifest.get("lessons", []) if item.get("id") == args.lesson_id), None)
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
                path.write_text(ACTIVITY_TEMPLATE.format(title=activity_title.strip(" -")))

    print(f"Lesson pack ready: {lesson_dir}")


if __name__ == "__main__":
    main()
