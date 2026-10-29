#!/usr/bin/env python3
"""Download ILIAS course materials into one local folder per course (Uni Mannheim)."""

from __future__ import annotations

import argparse
import hashlib
import html
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import Error, Page, sync_playwright

import settings

HOST = "ilias.uni-mannheim.de"
HOME = f"https://{HOST}/ilias.php?baseClass=ilDashboardGUI&cmd=jumpToSelectedItems"
# Pages that list the courses and groups the user is a member of (ILIAS 7–9 variants).
MEMBERSHIP_PAGES = (
    f"https://{HOST}/ilias.php?baseClass=ilDashboardGUI&cmd=jumpToMemberships",
    f"https://{HOST}/ilias.php?baseClass=ilmembershipoverviewgui",
    HOME,
)
IDP_HOST = "idp.uni-mannheim.de"
OUTPUT = Path(settings.load()["semester_dir"])

FILE_LINK = re.compile(r"/goto\.php/(?:file|f|zip|exc|pdf)/|sendfile|cmd=deliver|cmd=download|cmd=sendfile|cmdclass=ilobjfilegui", re.I)
FOLDER_LINK = re.compile(r"/goto\.php/fold/|cmdclass=ilobjfoldergui", re.I)
HTML = ("text/html", "application/xhtml")


def ilias_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == HOST


def traversal_key(url: str) -> str:
    """Collapse ILIAS action/tab URLs pointing to the same repository object."""
    parsed = urlparse(url)
    direct = re.search(r"/goto\.php/(crs|grp|fold)/(\d+)", parsed.path, re.I)
    if direct:
        return f"{direct.group(1).lower()}:{direct.group(2)}"
    if FOLDER_LINK.search(url):
        ref_ids = parse_qs(parsed.query).get("ref_id")
        if ref_ids:
            return f"fold:{ref_ids[0]}"
    return url


def safe_name(value: str, fallback: str = "Material") -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", value).strip(". ")
    return value[:160] or fallback


def response_filename(url: str, headers: dict[str, str], label: str) -> str:
    disposition = headers.get("content-disposition", "")
    encoded = re.search(r"filename\*=\s*[^']*''([^;]+)", disposition, re.I)
    quoted = re.search(r'filename\s*=\s*"([^"]+)"', disposition, re.I)
    plain = re.search(r'filename\s*=\s*([^;]+)', disposition, re.I)
    if encoded:
        name = unquote(encoded.group(1))
    elif quoted:
        name = quoted.group(1)
    elif plain:
        name = unquote(plain.group(1))
    else:
        link_label = label.rsplit("\n", 1)[-1]
        name = link_label if Path(link_label).suffix else Path(urlparse(url).path).name
        if not Path(name).suffix or name.lower() in ("goto.php", "ilias.php"):
            extension = mimetypes.guess_extension(headers.get("content-type", "").split(";", 1)[0]) or ""
            name = safe_name(link_label or "ilias-datei") + extension
    name = html.unescape(name)
    if not Path(name).suffix:
        name += mimetypes.guess_extension(headers.get("content-type", "").split(";", 1)[0]) or ""
    return safe_name(name, "ilias-datei")


def existing_hashes(course_dir: Path) -> set[str]:
    # Generated Markdown/assets are not downloaded course originals. In particular,
    # reading cloud-backed generated files can block indefinitely.
    hashes = set()
    skipped = 0

    hash_worker = """import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1])
if not p.is_file() or p.is_symlink():
    sys.exit(0)
h = hashlib.sha256()
with p.open('rb') as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b''):
        h.update(chunk)
print(h.hexdigest())
"""

    print("  prüfe vorhandene Originaldateien …", flush=True)
    for directory, subdirs, filenames in os.walk(course_dir):
        subdirs[:] = [name for name in subdirs
                      if not name.startswith('.') and not name.casefold().startswith('markdown')
                      and not (Path(directory) / name).is_symlink()]
        for name in filenames:
            path = Path(directory) / name
            if name.startswith('.') or path.is_symlink():
                continue
            worker = None
            try:
                # Isolate filesystem reads: a cloud-provider read may not respond
                # to Python signal timers. The main process must remain responsive.
                worker = subprocess.Popen([sys.executable, '-c', hash_worker, str(path)],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, error = worker.communicate(timeout=5)
                if worker.returncode:
                    raise OSError(error.decode(errors='replace').strip()[-300:])
                digest = output.decode().strip()
                if re.fullmatch(r'[0-9a-f]{64}', digest):
                    hashes.add(digest)
            except (OSError, subprocess.TimeoutExpired) as exc:
                skipped += 1
                reason = 'Datei reagiert nicht innerhalb von 5 Sekunden' if isinstance(exc, subprocess.TimeoutExpired) else str(exc)
                print(f"  lokale Datei übersprungen: {path.relative_to(course_dir)} ({reason})", flush=True)
            finally:
                if worker is not None:
                    if worker.poll() is None:
                        worker.kill()
                        try:
                            worker.communicate(timeout=0.2)
                        except subprocess.TimeoutExpired:
                            pass
                    if worker.stdout:
                        worker.stdout.close()
                    if worker.stderr:
                        worker.stderr.close()
    print(f"  {len(hashes)} Dateiinhalte geprüft, {skipped} lokale Dateien übersprungen", flush=True)
    return hashes


def object_target(url: str) -> str | None:
    """Return 'crs/123' or 'grp/123' for a link to an ILIAS course or group, else None."""
    if not ilias_url(url):
        return None
    parsed = urlparse(url)
    patterns = (
        r"/goto\.php/(crs|grp)/(\d+)",          # ILIAS 9: /goto.php/crs/123
        r"/goto_[^/]*?_(crs|grp)_(\d+)\.html",   # static links: goto_client_crs_123.html
    )
    for pattern in patterns:
        match = re.search(pattern, parsed.path, re.I)
        if match:
            return f"{match.group(1).lower()}/{match.group(2)}"
    query = parse_qs(parsed.query)
    target = re.fullmatch(r"(crs|grp)_(\d+)", (query.get("target") or [""])[0], re.I)
    if target:
        return f"{target.group(1).lower()}/{target.group(2)}"
    ref = (query.get("ref_id") or [""])[0]
    cmd_class = (query.get("cmdClass") or query.get("cmdclass") or [""])[0].lower()
    if ref.isdigit() and cmd_class in ("ilobjcoursegui", "ilobjgroupgui"):
        return f"{'crs' if cmd_class == 'ilobjcoursegui' else 'grp'}/{ref}"
    return None


def discover_courses(page: Page) -> dict[str, str]:
    """Return {ILIAS target: title} for all courses and groups linked from the membership pages."""
    found: dict[str, str] = {}
    for url in MEMBERSHIP_PAGES:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        except Error:
            continue
        if not ilias_url(page.url):
            continue
        for href, label in content_links(page):
            target = object_target(href)
            title = re.sub(r"\s+", " ", label.split("\n", 1)[0]).strip()
            if target and title and len(title) > 2 and target not in found:
                found[target] = title
        if found and url != HOME:
            break
    return found


def sorted_found(found: dict[str, str]) -> list[tuple[str, str]]:
    """Courses first, then groups, each alphabetically – the numbering shown to the user."""
    return sorted(found.items(), key=lambda item: (item[0].startswith("grp"), item[1].casefold()))


def print_found(items: list[tuple[str, str]]) -> None:
    print("\nDiese Kurse und Gruppen habe ich auf ILIAS gefunden:\n")
    for number, (target, title) in enumerate(items, 1):
        kind = "Gruppe" if target.startswith("grp") else "Kurs"
        print(f"  {number:>2}. {title}  ({kind}, {target})")


def parse_selection(answer: str, count: int) -> list[int]:
    """Parse '1 3 5-8' or 'alle' into 1-based numbers; raise ValueError on bad input."""
    answer = answer.strip()
    if not answer or answer.casefold() in ("alle", "all"):
        return list(range(1, count + 1))
    chosen: list[int] = []
    for part in re.split(r"[\s,;]+", answer):
        if "-" in part:
            start, end = (int(x) for x in part.split("-", 1))
            chosen.extend(range(start, end + 1))
        elif part:
            chosen.append(int(part))
    if not all(1 <= n <= count for n in chosen):
        raise ValueError(f"Bitte nur Nummern von 1 bis {count} verwenden.")
    return list(dict.fromkeys(chosen))


def choose_courses(found: dict[str, str], selection: str | None = None) -> dict[str, list[str]]:
    """Return {folder name: [targets]}; asks in the terminal unless `selection` is given."""
    if not found:
        raise RuntimeError("Auf ILIAS wurden keine Kurse gefunden. Bist du in Kursen eingeschrieben?")
    items = sorted_found(found)
    if selection is not None:
        try:
            chosen = parse_selection(selection, len(items))
        except ValueError as exc:
            print_found(items)
            raise RuntimeError(f"Ungültige Kursauswahl '{selection}': {exc}") from None
    else:
        print_found(items)
        print("\nWelche sollen heruntergeladen werden? Nummern mit Leerzeichen oder Komma trennen,")
        print("Bereiche mit Bindestrich (z. B. 1 3 5-8). Enter ohne Eingabe = alle.")
        while True:
            try:
                chosen = parse_selection(input("> "), len(items))
                break
            except ValueError as exc:
                print(str(exc) if "Nummern" in str(exc) else "Bitte nur Zahlen eingeben, z. B. 1 3 5-8.")
    courses: dict[str, list[str]] = {}
    for n in chosen:
        target, title = items[n - 1]
        name = safe_name(title, target.replace("/", "-"))
        while name in courses:
            name += " (2)"
        courses[name] = [target]
    print(f"\n{len(courses)} Kurse gespeichert in {settings.COURSES_FILE}:")
    for name in courses:
        print(f"  – {name}")
    print("Neu auswählen (z. B. zum neuen Semester): ./run.sh --kurse-waehlen\n")
    return courses


def category(text: str, course_name: str) -> Path:
    from material_layout import download_category
    return download_category(text, course_name)


def content_links(page: Page) -> list[tuple[str, str]]:
    return page.evaluate(
        """() => {
            const area = document.querySelector('main, #mainspacekeeper, .ilContent') || document;
            return [...area.querySelectorAll('a[href]')].map(a => [
                a.href, (a.innerText || a.getAttribute('aria-label') || a.title || '').trim()
            ]);
        }"""
    )


def save_file(page: Page, url: str, label: str, course_name: str, course_dir: Path, hashes: set[str]) -> int:
    cookies = page.context.cookies([url])
    cookie_header = "; ".join(f"{item['name']}={item['value']}" for item in cookies)
    request = Request(url, headers={"Cookie": cookie_header, "User-Agent": "Mozilla/5.0"})
    temporary = None
    print(f"  lade: {label.rsplit(chr(10), 1)[-1] or urlparse(url).path}", flush=True)
    try:
        with urlopen(request, timeout=30) as response:
            headers = dict(response.headers.items())
            content_type = headers.get("Content-Type", "").lower()
            if any(content_type.startswith(kind) for kind in HTML):
                if "login.php" in response.url:
                    raise RuntimeError("ILIAS-Sitzung abgelaufen. Bitte erneut anmelden und starten.")
                return 0
            digest_builder = hashlib.sha256()
            with tempfile.NamedTemporaryFile(dir=course_dir, prefix=".ilias-", suffix=".part", delete=False) as output:
                temporary = Path(output.name)
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    digest_builder.update(chunk)
            if temporary.stat().st_size == 0:
                return 0
            digest = digest_builder.hexdigest()
            name = response_filename(response.url, {key.lower(): value for key, value in headers.items()}, label)
            if digest in hashes:
                print(f"  vorhanden: {name}")
                return 0
            destination = course_dir / category(f"{label}\n{name}", course_name)
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / name
            if target.exists():
                target = destination / f"{target.stem}-{digest[:8]}{target.suffix}"
            temporary.replace(target)
            temporary = None
            hashes.add(digest)
            print(f"  neu: {target.relative_to(course_dir)}")
            return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def crawl_course(page: Page, course_name: str, starts: tuple[str, ...], root: Path, depth: int) -> int:
    course_dir = root / course_name
    course_dir.mkdir(parents=True, exist_ok=True)
    hashes = existing_hashes(course_dir)
    queue = deque((f"https://{HOST}/goto.php/{start}", 0, "") for start in starts)
    visited: set[str] = set()
    count = 0
    while queue:
        url, level, label = queue.popleft()
        key = traversal_key(url)
        if key in visited or level > depth:
            continue
        visited.add(key)
        try:
            if FILE_LINK.search(url):
                count += save_file(page, url, label, course_name, course_dir, hashes)
                continue
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            if response is None or not ilias_url(page.url):
                continue
            if "login.php" in page.url:
                raise RuntimeError("ILIAS-Sitzung abgelaufen. Bitte erneut anmelden und starten.")
            content_type = (response.header_value("content-type") or "").lower()
            if not any(content_type.startswith(kind) for kind in HTML):
                count += save_file(page, url, label, course_name, course_dir, hashes)
                continue
            if level == depth:
                continue
            links = content_links(page)
            print(f"  Ebene {level}: {page.title()} – {len(links)} Links", flush=True)
            for href, child_label in links:
                if ilias_url(href) and traversal_key(href) not in visited and (FILE_LINK.search(href) or FOLDER_LINK.search(href)):
                    queue.append((href, level + 1, f"{label}\n{child_label}".strip()))
        except (Error, URLError, TimeoutError) as exc:
            if page.is_closed():
                raise RuntimeError("ILIAS-Browser geschlossen. Der Abgleich ist unvollständig; bitte erneut starten.") from exc
            print(f"  übersprungen: {url} ({exc})", file=sys.stderr)
    return count


def auto_login(page: Page, credentials: tuple[str, str] | None) -> bool:
    """Fill the Shibboleth form once with Keychain credentials; never retried to avoid lockouts."""
    if credentials is None or urlparse(page.url).hostname != IDP_HOST:
        return False
    try:
        page.wait_for_selector("#username", timeout=15_000)
    except Error:
        return False
    username, password = credentials
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("button[name=_eventId_proceed]")
    print(f"Anmeldung als {username} mit Daten aus dem macOS-Schlüsselbund …", flush=True)
    return True


def login_problem(page: Page) -> str:
    if urlparse(page.url).hostname == IDP_HOST and page.locator("#password").count():
        return "ILIAS-Anmeldung fehlgeschlagen. Bitte Uni-ID und Passwort in der App prüfen."
    return "ILIAS verlangt einen weiteren Anmeldeschritt. Bitte mit sichtbarem Browserfenster starten."


def main() -> None:
    parser = argparse.ArgumentParser(description="Lädt ILIAS-Kursmaterialien in einen Ordner pro Kurs.")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Zielordner (darin entsteht ein Ordner pro Kurs)")
    parser.add_argument("--depth", type=int, default=settings.load()["depth"], help="Maximale Unterordnertiefe")
    parser.add_argument("--kurse-waehlen", dest="choose", action="store_true", help="Kurse neu auswählen (fragt im Terminal)")
    parser.add_argument("--kurse-auflisten", dest="list_courses", action="store_true",
                        help="Nur anmelden und die gefundenen Kurse nummeriert anzeigen, nichts herunterladen")
    parser.add_argument("--kurse", dest="selection", metavar="AUSWAHL",
                        help="Kurse ohne Rückfrage wählen, z. B. '1 3 5-8' oder 'alle' (Nummern aus --kurse-auflisten)")
    parser.add_argument("--browser", choices=("webkit", "chromium", "firefox"), default="webkit")
    parser.add_argument("--session-file", type=Path, help="Lokale ILIAS-Sitzungsdatei")
    parser.add_argument("--headless", action="store_true", help="Ohne Browserfenster; erfordert gültige Sitzung oder gespeicherte Zugangsdaten")
    parser.add_argument("--no-auto-login", action="store_true", help="Zugangsdaten aus dem Schlüsselbund nicht verwenden")
    md = parser.add_mutually_exclusive_group()
    md.add_argument("--markdown", action="store_true", default=None,
                    help="Danach Markdown-Kopien erzeugen (Standard: laut Einstellung)")
    md.add_argument("--kein-markdown", dest="markdown", action="store_false",
                    help="Diesmal keine Markdown-Kopien erzeugen")
    parser.add_argument("--use-settings", action="store_true", help="Hintergrund- und Markdown-Option aus settings.json übernehmen (für den Zeitplan)")
    args = parser.parse_args()
    if args.use_settings:
        config = settings.load()
        args.headless = args.headless or (config["headless"] and settings.get_credentials() is not None)
    if args.markdown is None:
        args.markdown = bool(settings.load()["markdown_after_sync"])
    root = args.output.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    reselect = args.choose or args.selection is not None or args.list_courses
    courses = None if reselect else settings.load_courses()
    if courses is None and args.selection is None and not args.list_courses and not sys.stdin.isatty():
        raise RuntimeError("Noch keine Kurse ausgewählt. Erst ./run.sh --kurse-auflisten, "
                           "dann ./run.sh --kurse '1 3 5' (oder im Terminal ./run.sh --kurse-waehlen).")
    settings.SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    session_file = (args.session_file or settings.SESSION_FILE).expanduser().resolve()
    with sync_playwright() as playwright:
        browser = getattr(playwright, args.browser).launch(headless=args.headless)
        context = browser.new_context(
            accept_downloads=True,
            storage_state=str(session_file) if session_file.exists() else None,
        )
        page = context.new_page()
        page.goto(HOME, wait_until="domcontentloaded")
        logged_in = "ildashboardgui" in page.url.lower()
        submitted = not logged_in and not args.no_auto_login and auto_login(page, settings.get_credentials())
        if args.headless and not logged_in and not submitted:
            raise RuntimeError("ILIAS-Anmeldung erforderlich. Bitte Zugangsdaten in der App speichern "
                               "oder mit sichtbarem Browserfenster starten.")
        if not logged_in and not submitted:
            print("Bitte im geöffneten ILIAS-Fenster anmelden. Der Abgleich beginnt danach automatisch.", flush=True)
        deadline = 60 if args.headless else None
        waited = 0
        while True:
            dashboards = [
                candidate for candidate in context.pages
                if ilias_url(candidate.url) and "ildashboardgui" in candidate.url.lower()
            ]
            if dashboards:
                page = dashboards[-1]
                context.storage_state(path=str(session_file))
                session_file.chmod(0o600)
                break
            if deadline is not None and waited >= deadline:
                raise RuntimeError(login_problem(page))
            if submitted and waited == 15 and not args.headless:
                print(login_problem(page) + " Du kannst es im geöffneten Fenster selbst abschließen.", flush=True)
            # Playwright must process browser events while waiting for SAML.
            page.wait_for_timeout(1000)
            waited += 1
        if args.list_courses:
            items = sorted_found(discover_courses(page))
            if not items:
                raise RuntimeError("Auf ILIAS wurden keine Kurse gefunden. Bist du in Kursen eingeschrieben?")
            print_found(items)
            print("\nAuswahl übernehmen und herunterladen mit: ./run.sh --kurse '1 3 5-8'  (oder 'alle')")
            context.close()
            browser.close()
            return
        if courses is None:
            courses = choose_courses(discover_courses(page), args.selection)
            settings.save_courses(courses)
        total = 0
        for course_name, starts in courses.items():
            print(f"Kurs: {course_name}", flush=True)
            total += crawl_course(page, course_name, tuple(starts), root, args.depth)
        context.close()
        browser.close()
    print(f"Fertig: {total} neue Dateien in {root}", flush=True)
    if args.markdown:
        import md_convert
        target = Path(settings.load()["markdown_dir"]).expanduser().resolve()
        md_convert.run(root, target, timeout=1800, retry_failed=False, jobs=max(1, min(4, (os.cpu_count() or 2) // 2)))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, Error) as exc:
        print(f"FEHLER: {str(exc).splitlines()[0]}", file=sys.stderr, flush=True)
        sys.exit(1)
