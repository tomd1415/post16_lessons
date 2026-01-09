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
