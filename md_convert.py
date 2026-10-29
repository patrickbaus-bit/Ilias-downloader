#!/usr/bin/env python3
"""Mirror course materials as Markdown files for use with AI tools.

Only new or changed originals are converted; unchanged files are recognised by
size and modification time, so iCloud placeholders are not downloaded again.
Each conversion runs in its own process with a timeout because reading a
cloud-backed file or parsing a broken document can block indefinitely.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import quote

import settings

from converters import SUPPORTED

# Raise when the output format changes so existing Markdown files are regenerated.
CONVERTER_VERSION = 3
SKIP_DIRS: set[str] = set()
MANIFEST = ".ilias-md-manifest.json"
INDEX = "INDEX.md"
GUIDE = "_KI-ANLEITUNG.md"
GUIDE_TEXT = """# Anleitung für KI-Modelle

Dieser Ordner enthält Kursmaterialien eines Studierenden als Markdown – automatisch und ohne KI
aus den Originaldateien (PDF, PowerPoint, Word, Excel, Bilder) erzeugt. Die Ordnerstruktur
entspricht der des Originalordners. `INDEX.md` listet alle Dateien.

## Kopf jeder Datei

- `quelle`: Pfad der Originaldatei relativ zum Semesterordner, `kurs`: Fach.
- `seiten` / `folien`: Umfang des Originals.
- `hinweise`: Besonderheiten der Umwandlung (z. B. Seiten per OCR erkannt, Seiten ohne Text).

## Bezugspunkte (wichtig beim Antworten)

Der Mensch liest das Original, du liest diese Fassung. Verweise deshalb immer so, dass er die
Stelle im Original findet:

- `[Seite 12 von 80]` beginnt PDF-Seite 12 – das ist die Nummer, die PDF-Programme anzeigen.
  `[Seite 12 von 80 · im Dokument: 499]` heißt: auf dem Blatt selbst steht die Seitenzahl 499.
  Nenne in dem Fall beide Zahlen.
- `[Folie 7 von 30]` beginnt Folie 7 einer PowerPoint-Datei.
- Excel/CSV: Tabellen tragen Spaltenbuchstaben (A, B, …) und eine Spalte `Zeile` mit der
  Excel-Zeilennummer; Zelle C5 = Spalte C, Zeile 5. Formeln stehen unter jeder Tabelle.
- Word-Dateien haben keine festen Seitenzahlen; verweise auf Überschriften oder zitiere den Wortlaut.

## Text aus Bildern

Zeilen mit `>` nach `[Abbildung – Text per OCR]` wurden per Texterkennung aus Grafiken,
Screenshots oder Scans gelesen. Sie geben den Text der Grafik wieder, nicht ihre Form
(keine Linien, Pfeile, Achsen). OCR kann einzelne Zeichen falsch lesen – bei Zahlen, die
für eine Antwort entscheidend sind, auf mögliche Erkennungsfehler hinweisen.
`[Seite ohne Textebene – gesamter Text per OCR]` kennzeichnet Scans oder Seiten, deren Schrift
nur als Grafik vorliegt; `[Textebene unlesbar – …]` Seiten mit defekter Schriftkodierung.

## Grenzen

Diagramme, Formelsatz und Layout sind nur als Text enthalten. Wenn eine Frage von einer
Grafik abhängt, die hier nur als `[Abbildung]` erscheint, sage das und verweise auf die Seite.
"""


def sources(root: Path) -> list[Path]:
    found = []
    for directory, subdirs, filenames in os.walk(root):
        subdirs[:] = sorted(
            name for name in subdirs
            if not name.startswith(".")
            and not name.casefold().startswith("markdown")
            and name.casefold() not in SKIP_DIRS
            and not (Path(directory) / name).is_symlink()
        )
        for name in sorted(filenames):
            path = Path(directory) / name
            if not name.startswith((".", "~$")) and path.suffix.lower() in SUPPORTED and not path.is_symlink():
                found.append(path.relative_to(root))
    return found


def output_names(relatives: list[Path]) -> dict[Path, Path]:
    """Map originals to Markdown paths; 'X.pdf' and 'X.docx' must not overwrite each other."""
    # APFS treats "Ä"/"A\u0308" and "a"/"A" as the same name, so group on that key.
    stems: dict[str, list[Path]] = {}
    for relative in relatives:
        stems.setdefault(unicodedata.normalize("NFC", relative.with_suffix("").as_posix()).casefold(), []).append(relative)
    result = {}
    for group in stems.values():
        pdfs = [r for r in group if r.suffix.lower() == ".pdf"]
        for relative in group:
            stem = relative.with_suffix("")
            if len(group) == 1 or (len(pdfs) == 1 and relative == pdfs[0]):
                result[relative] = stem.parent / f"{stem.name}.md"
            elif relative.suffix.lower() == ".pdf":
                result[relative] = stem.parent / f"{stem.name} ({relative.suffix.lstrip('.')}).md"
            else:
                result[relative] = stem.parent / f"{stem.name} ({relative.suffix.lstrip('.').lower()}).md"
    # Same name with different extension case ("X.PDF", "x.pdf") cannot coexist on APFS; keep it unique anyway.
    seen: dict[str, int] = {}
    for relative in sorted(result, key=lambda r: r.as_posix()):
        key = unicodedata.normalize("NFC", result[relative].as_posix()).casefold()
        if key in seen:
            seen[key] += 1
            out = result[relative]
            result[relative] = out.with_name(f"{out.stem} {seen[key]}.md")
        else:
            seen[key] = 1
    return result


def front_matter(relative: Path, stats: dict) -> str:
    lines = [
        "---",
        f"quelle: {json.dumps(relative.as_posix(), ensure_ascii=False)}",
        f"kurs: {json.dumps(relative.parts[0], ensure_ascii=False)}",
        f"format: {relative.suffix.lstrip('.').lower()}",
    ]
    if "seiten" in stats:
        lines.append(f"seiten: {stats['seiten']}")
    if stats.get("folien"):
        lines.append(f"folien: {stats['folien']}")
    notes = []
    if stats.get("ocr_seiten"):
        notes.append(f"Seiten per OCR erkannt: {_ranges(stats['ocr_seiten'])}")
    if stats.get("ohne_text"):
        notes.append(f"Seiten ohne erkennbaren Text (nur Grafik?): {_ranges(stats['ohne_text'])}")
    if stats.get("layout_bis"):
        notes.append(f"Ab Seite {stats['layout_bis'] + 1} ohne Layout-Analyse (sehr komplexe Seiten): "
                     "vollständiger Text, aber ohne Überschriften-/Tabellenstruktur")
    if relative.suffix.lower() == ".docx":
        notes.append("Word-Dokument ohne feste Seitenzahlen – Bezug über Überschriften")
    if notes:
        lines.append("hinweise:")
        lines += [f"  - {json.dumps(note, ensure_ascii=False)}" for note in notes]
    lines += [f"konvertiert: {date.today().isoformat()}", "---", "", f"# {relative.name}", ""]
    return "\n".join(lines) + "\n"


def _ranges(numbers: list[int]) -> str:
    """[1, 2, 3, 7] -> '1–3, 7'"""
    spans, start = [], None
    for i, n in enumerate(numbers):
        if start is None:
            start = n
        if i + 1 == len(numbers) or numbers[i + 1] != n + 1:
            spans.append(str(start) if start == n else f"{start}–{n}")
            start = None
    return ", ".join(spans)


def convert_one(source: Path, target: Path, relative: Path) -> None:
    """Worker: write one Markdown file atomically."""
    import converters

    body, stats = converters.convert(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.part")
    temporary.write_text(front_matter(relative, stats) + body.rstrip() + "\n", encoding="utf-8")
    temporary.replace(target)


def write_index(target_root: Path, manifest: dict) -> None:
    courses: dict[str, list[tuple[str, str]]] = {}
    for relative, entry in sorted(manifest.items()):
        if entry.get("out") and not entry.get("error"):
            courses.setdefault(Path(relative).parts[0], []).append((entry["out"], relative))
    lines = ["# Kursmaterial als Markdown", "",
             f"Automatisch erzeugt am {date.today().isoformat()}. Lies zuerst [{GUIDE}]({quote(GUIDE)}) "
             "(Seitenmarker, OCR, Excel-Zellbezüge). Jede Datei nennt im Kopf ihr Original (`quelle`).", ""]
    for course, items in courses.items():
        lines += [f"## {course}", ""]
        lines += [f"- [{Path(out).relative_to(course).with_suffix('')}]({quote(out)}) ← `{source}`" for out, source in items]
        lines.append("")
    (target_root / INDEX).write_text("\n".join(lines), encoding="utf-8")
    (target_root / GUIDE).write_text(GUIDE_TEXT, encoding="utf-8")


def remove_empty_dirs(root: Path) -> None:
    for directory, _, _ in sorted(os.walk(root), key=lambda item: -len(item[0])):
        path = Path(directory)
        if path == root:
            continue
        (path / ".DS_Store").unlink(missing_ok=True)
        try:
            path.rmdir()
        except OSError:
            pass


def run(source_root: Path, target_root: Path, timeout: int, retry_failed: bool,
        only: list[Path] | None = None, jobs: int = 1) -> int:
    target_root.mkdir(parents=True, exist_ok=True)
    manifest_path = target_root / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    lock = threading.Lock()

    def save_manifest() -> None:
        with lock:
            data = json.dumps(manifest, ensure_ascii=False, indent=1)
        temporary = manifest_path.with_suffix(".part")
        temporary.write_text(data, encoding="utf-8")
        temporary.replace(manifest_path)

    print(f"Markdown: durchsuche {source_root} …", flush=True)
    relatives = sources(source_root)
    if only is not None:
        wanted = {unicodedata.normalize("NFC", p.as_posix()) for p in only}
        relatives = [r for r in relatives if unicodedata.normalize("NFC", r.as_posix()) in wanted]
    names = output_names(relatives)
    current = {r.as_posix() for r in relatives}

    removed = 0
    if only is None:  # a partial run must not treat unlisted files as deleted
        for key in [key for key in manifest if key not in current]:
            out = manifest.pop(key).get("out")
            if out and not any(e.get("out") == out for e in manifest.values()):
                (target_root / out).unlink(missing_ok=True)
                removed += 1
    if removed:
        print(f"Markdown: {removed} Dateien entfernt, deren Original nicht mehr existiert", flush=True)

    pending = []
    for relative in relatives:
        key = relative.as_posix()
        stat = (source_root / relative).stat()
        entry = manifest.get(key, {})
        out = names[relative].as_posix()
        unchanged = (entry.get("size") == stat.st_size and entry.get("mtime") == int(stat.st_mtime)
                     and entry.get("version") == CONVERTER_VERSION)
        if unchanged and entry.get("out") == out and (
            (target_root / out).exists() or (entry.get("error") and not retry_failed)
        ):
            continue
        if entry.get("out") and entry["out"] != out:
            (target_root / entry["out"]).unlink(missing_ok=True)
        pending.append((relative, stat))

    print(f"Markdown: {len(relatives)} Originale, {len(pending)} neu oder geändert", flush=True)
    active: set[subprocess.Popen] = set()
    stopping = threading.Event()

    def stop(signum, frame) -> None:
        stopping.set()
        with lock:
            for worker in list(active):
                worker.kill()

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}

    def convert(relative: Path) -> tuple[str | None, float]:
        started = time.monotonic()
        if stopping.is_set():
            return "abgebrochen", 0.0
        worker = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--worker",
             str(source_root / relative), str(target_root / names[relative]), relative.as_posix()],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True,
        )
        with lock:
            active.add(worker)
        try:
            _, stderr = worker.communicate(timeout=timeout)
            if stopping.is_set():
                return "abgebrochen", 0.0
            error = None if worker.returncode == 0 else (stderr.strip().splitlines() or ["Fehler"])[-1]
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.communicate()
            error = f"Zeitüberschreitung nach {timeout} s"
        finally:
            with lock:
                active.discard(worker)
        return error, time.monotonic() - started

    failures = done = 0
    try:
        with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            futures = {pool.submit(convert, relative): (relative, stat) for relative, stat in pending}
            for future in as_completed(futures):
                relative, stat = futures[future]
                error, seconds = future.result()
                if error == "abgebrochen":
                    continue
                done += 1
                key, out = relative.as_posix(), names[relative].as_posix()
                entry = {"size": stat.st_size, "mtime": int(stat.st_mtime), "out": out,
                         "version": CONVERTER_VERSION, "seconds": round(seconds, 1)}
                if error:
                    failures += 1
                    entry["error"] = error[:300]
                    print(f"[{done}/{len(pending)}] FEHLER: {key} ({error[:200]})", flush=True)
                else:
                    print(f"[{done}/{len(pending)}] konvertiert: {out} ({seconds:.1f} s)", flush=True)
                with lock:
                    manifest[key] = entry
                if done % 10 == 0:
                    save_manifest()
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        save_manifest()
        write_index(target_root, manifest)
        remove_empty_dirs(target_root)
    if stopping.is_set():
        print(f"Markdown abgebrochen: {done - failures} konvertiert, Rest beim nächsten Lauf", flush=True)
        return 1
    print(f"Markdown fertig: {done - failures} konvertiert, {failures} Fehler → {target_root}", flush=True)
    return 1 if failures and failures == len(pending) else 0


def main() -> None:
    config = settings.load()
    parser = argparse.ArgumentParser(description="Erzeugt Markdown-Kopien aller Kursdateien für KI-Werkzeuge.")
    parser.add_argument("--source", type=Path, default=Path(config["semester_dir"]))
    parser.add_argument("--target", type=Path, default=Path(config["markdown_dir"]))
    parser.add_argument("--timeout", type=int, default=1800, help="Sekunden pro Datei")
    parser.add_argument("--retry-failed", action="store_true", help="Früher fehlgeschlagene Dateien erneut versuchen")
    parser.add_argument("--jobs", type=int, default=max(1, min(4, (os.cpu_count() or 2) // 2)),
                        help="Parallele Konvertierungen")
    parser.add_argument("--list", type=Path, help="Nur diese Dateien (Textdatei, ein Pfad relativ zur Quelle je Zeile)")
    parser.add_argument("--worker", nargs=3, metavar=("QUELLE", "ZIEL", "RELATIV"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        import converters

        source, target, relative = args.worker
        code = 0
        try:
            convert_one(Path(source), Path(target), Path(relative))
        except converters.ConversionError as exc:
            print(exc, file=sys.stderr)
            code = 2
        except Exception:
            import traceback

            traceback.print_exc()
            code = 1
        sys.stdout.flush()
        sys.stderr.flush()
        # Skip interpreter shutdown: Vision's dispatch threads may still be releasing objects,
        # and Python's finalisation then kills the process (EXC_BREAKPOINT in pthread_exit).
        os._exit(code)
    source = args.source.expanduser().resolve()
    target = args.target.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"Quellordner existiert nicht: {source}")
    if target == source or source in target.parents:
        parser.error("Der Markdown-Ordner darf nicht im Semesterordner liegen.")
    only = None
    if args.list:
        only = [Path(line.strip()) for line in args.list.read_text(encoding="utf-8").splitlines() if line.strip()]
    sys.exit(run(source, target, args.timeout, args.retry_failed, only, args.jobs))


if __name__ == "__main__":
    main()
