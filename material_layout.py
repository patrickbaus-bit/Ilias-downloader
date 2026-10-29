"""Sort new ILIAS downloads into a small, predictable set of subfolders per course.

Every course folder gets the same layout:

    Vorlesung/                 lecture slides, scripts, handouts
    Übung/Aufgaben/            exercise sheets, assignments
    Übung/Loesungen/           solutions to exercises
    Tutorium/Aufgaben/         tutorial sheets
    Tutorium/Loesungen/        tutorial solutions
    Prüfung/Aufgaben/          old exams
    Prüfung/Loesungen/         exam solutions
    Prüfung/Aufgaben_mit_Loesungen/
    Organisatorisches/         syllabus, schedules, info sheets
    Sonstiges/                 everything that matches no rule

The folder labels from ILIAS (e.g. a folder called "Tutorium") count as context,
but the file name decides first. Duplicate detection does not depend on these
folders, so you can move files around afterwards without re-downloading them.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def normalized(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def solution(text: str) -> bool:
    return bool(re.search(r"lösung|loesung|solution|answer.?key|musterlös|(?:^|[_\W])sol(?:[_\W]|$)", normalized(text)))


def _any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def download_category(text: str, course: str) -> Path:
    """Return the course-relative folder for a file.

    `text` holds the ILIAS folder labels the file was found under, one per line,
    with the file name as the last line. `course` is the course folder name.
    """
    context = normalized(text)
    name = normalized(text.rsplit("\n", 1)[-1])

    if _any(name, ("taschenrechner", "deckblatt", "faq", "klausurregeln")):
        return Path("Prüfung")
    if re.search(r"klausur|exam|prüfung|pruefung|altklausur|probeklausur", name):
        if _any(name, ("with solution", "mit lösung", "mit loesung")):
            return Path("Prüfung/Aufgaben_mit_Loesungen")
        return Path("Prüfung") / ("Loesungen" if solution(name) else "Aufgaben")
    if _any(name, ("organis", "syllabus", "schedule", "zeitplan", "infoblatt", "einteilung", "termine", "modulbeschreibung")):
        return Path("Organisatorisches")

    exercise_words = ("übung", "uebung", "exercise", "assignment", "aufgabe", "blatt", "problem set", "quiz")
    is_tutorial = "tutor" in name or ("tutor" in context and not _any(name, exercise_words))
    if is_tutorial or _any(name, exercise_words) or solution(name):
        kind = "Tutorium" if is_tutorial else "Übung"
        return Path(kind) / ("Loesungen" if solution(name) else "Aufgaben")

    if _any(context, ("vorlesung", "lecture", "slides", "skript", "folien", "handout", "foliensatz")) or re.search(r"\bvl\s*\d", context):
        return Path("Vorlesung")
    if "literatur" in context or "reading" in context:
        return Path("Vorlesung/Literatur")
    return Path("Sonstiges")
