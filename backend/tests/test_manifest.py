import json
from pathlib import Path


def test_lesson2_activity_scaffold_entries():
    manifest_path = Path(__file__).resolve().parents[2] / "web" / "lessons" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    lessons = {lesson["id"]: lesson for lesson in data.get("lessons", [])}
    lesson2 = lessons.get("lesson-2")
    assert lesson2 is not None
    activities = lesson2.get("activities", [])
    ids = [activity["id"] for activity in activities]
    assert ids == ["a01", "a02", "a03", "a04"]
    teacher_resources = lesson2.get("teacherResources", [])
    teacher_resource_paths = [item.get("path") for item in teacher_resources]
    assert "/lessons/lesson-2/teacher/lesson-plan.html" in teacher_resource_paths
    assert "/lessons/lesson-2/teacher/print-cards.html" in teacher_resource_paths
    assert "/lessons/lesson-2/teacher/answer-key.html" in teacher_resource_paths
    for activity in activities:
        assert activity.get("path")
        activity_path = Path(__file__).resolve().parents[2] / "web" / activity["path"].lstrip("/")
        html = activity_path.read_text()
        assert html.count("data-quiz=") >= 3
        assert "Teacher guidance (answer prompts)" in html
        assert "activity-scaffold.js" in html


def test_lessons_3_to_15_have_activity_scaffolds():
    manifest_path = Path(__file__).resolve().parents[2] / "web" / "lessons" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    lessons = {lesson["id"]: lesson for lesson in data.get("lessons", [])}

    for lesson_num in range(3, 16):
        lesson = lessons.get(f"lesson-{lesson_num}")
        assert lesson is not None
        activities = lesson.get("activities", [])
        assert activities
        teacher_resources = lesson.get("teacherResources", [])
        assert teacher_resources

        for resource in teacher_resources:
            path = resource.get("path")
            assert path
            resource_path = Path(__file__).resolve().parents[2] / "web" / path.lstrip("/")
            assert resource_path.exists()

        for activity in activities:
            path = activity.get("path")
            assert path
            activity_path = Path(__file__).resolve().parents[2] / "web" / path.lstrip("/")
            html = activity_path.read_text()
            assert html.count("data-quiz=") >= 3
            assert "Teacher guidance (answer prompts)" in html
            if "python-runner.js" in html:
                assert "data-hint-code-template" in html
                assert "codeEditor" in html
            else:
                assert "activity-scaffold.js" in html


def test_python_runner_activity_present():
    manifest_path = Path(__file__).resolve().parents[2] / "web" / "lessons" / "manifest.json"
    data = json.loads(manifest_path.read_text())
    lessons = {lesson["id"]: lesson for lesson in data.get("lessons", [])}
    lesson4 = lessons.get("lesson-4")
    assert lesson4 is not None
    runner = next((a for a in lesson4.get("activities", []) if a.get("id") == "a02"), None)
    assert runner is not None
    path = runner.get("path")
    assert path
    activity_path = Path(__file__).resolve().parents[2] / "web" / path.lstrip("/")
    html = activity_path.read_text()
    assert "python-runner.js" in html
    assert html.count("data-quiz=") >= 3
    assert "codeEditor" in html
    assert "data-hint-code-template" in html
