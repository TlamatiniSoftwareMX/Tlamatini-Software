import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_practical_guides_are_embedded_and_substantial():
    payload = json.loads((ROOT / "assets/offline_learning/practical_guides.json").read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert len(entries) >= 3
    lessons = [lesson for course in entries for module in course["modules"] for lesson in module["lessons"]]
    assert len(lessons) >= 18
    assert all(lesson["source_type"] == "embedded" for lesson in lessons)
    assert all(len(lesson["text"].split()) >= 45 for lesson in lessons)
    assert all(course.get("source_url") for course in entries)


def test_morse_course_is_embedded_under_communication():
    payload = json.loads((ROOT / "assets/offline_learning/morse_course.json").read_text(encoding="utf-8"))
    assert len(payload["entries"]) == 1
    course = payload["entries"][0]
    lessons = [lesson for module in course["modules"] for lesson in module["lessons"]]

    assert course["id"] == "telegrafo-codigo-morse-es"
    assert course["category"] == "Comunicacion"
    assert course["format"] == "embedded_course"
    assert len(lessons) == 6
    assert all(lesson["source_type"] == "embedded" for lesson in lessons)
    assert all(len(lesson["text"].split()) >= 80 for lesson in lessons)
