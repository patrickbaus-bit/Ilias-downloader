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
    Lernmaterial/              vocabulary, grammar, cheat sheets, formula collections
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
    with_solutions = _any(name, ("with solution", "mit lösung", "mit loesung"))
    # Old exams: "Klausur …", "Exam …", or a semester tag like "HWS 24 Section I …".
    old_exam = re.search(r"^(?:hws|fss|ws|ss)\s?\d{2}\b.*\b(?:section|teil|part)\b", name)
    if old_exam or re.search(r"klausur|exam|prüfung|pruefung|altklausur|probeklausur", name):
        if with_solutions:
            return Path("Prüfung/Aufgaben_mit_Loesungen")
        return Path("Prüfung") / ("Loesungen" if solution(name) else "Aufgaben")
    if _any(name, ("organis", "syllabus", "schedule", "zeitplan", "infoblatt", "einteilung", "termine",
                   "modulbeschreibung", "memo", "attendance", "anwesenheit", "certificate", "zertifikat",
                   "marking key", "bewertungsschema", "grading")) or re.search(r"(?:^|\s)info\b", name):
        return Path("Organisatorisches")
    if _any(name, ("vocab", "glossar", "glossary", "grammar", "grammatik", "cheat sheet", "cheatsheet",
                   "formelsammlung", "formula sheet", "formelblatt", "irregular verbs", "alphabet",
                   "spickzettel", "merkblatt")):
        return Path("Lernmaterial")

    exercise_words = ("übung", "uebung", "exercise", "assignment", "aufgabe", "blatt", "problem set", "quiz")
    is_tutorial = "tutor" in name or ("tutor" in context and not _any(name, exercise_words))
    if is_tutorial or _any(name, exercise_words) or solution(name):
        kind = "Tutorium" if is_tutorial else "Übung"
        return Path(kind) / ("Loesungen" if solution(name) else "Aufgaben")

    lecture_words = ("vorlesung", "lecture", "slide", "skript", "script", "folie", "handout",
                     "introduction", "einführung", "einfuehrung", "chapter", "kapitel")
    # Lecture parts like "OPM301_II_Optimization" or "FIN 401 – III Valuation".
    lecture_part = re.search(r"^[a-z]{2,4}\s?\d{3}[\s_–-]+(?:[ivx]{1,4}|\d{1,2})[\s_.–-]", name)
    if _any(name, lecture_words) or lecture_part or re.search(r"\bvl\s*\d", name):
        return Path("Vorlesung")
    if _any(context, ("vorlesung", "lecture", "slides", "skript", "folien", "handout", "foliensatz")) or re.search(r"\bvl\s*\d", context):
        return Path("Vorlesung")
    if "literatur" in context or "reading" in context:
        return Path("Vorlesung/Literatur")
    return Path("Sonstiges")
