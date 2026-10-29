"""Shared settings and macOS Keychain access for the ILIAS downloader."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
# Settings live outside the repository so `git pull` never touches them.
SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "ILIAS Downloader"
SETTINGS_FILE = SUPPORT_DIR / "settings.json"
COURSES_FILE = SUPPORT_DIR / "courses.json"
SESSION_FILE = SUPPORT_DIR / "ilias-session.json"
LOG_FILE = SUPPORT_DIR / "ilias-downloader.log"
LOCK_FILE = Path("/private/tmp/ilias-downloader.lock")
LAUNCH_AGENT_LABEL = "de.ilias-downloader.daily"
KEYCHAIN_SERVICE = "ILIAS Downloader – Uni Mannheim"
# Keychain items are keyed by account; this fixed entry remembers which Uni-ID is stored.
USERNAME_ACCOUNT = "__uni_id__"

DEFAULTS = {
    "semester_dir": str(Path.home() / "Documents" / "Uni" / "ILIAS"),
    # Must not lie inside semester_dir, otherwise the Markdown copies would be scanned as originals.
    "markdown_dir": str(Path.home() / "Documents" / "Uni" / "KI-Markdown"),
    "headless": True,
    "markdown_after_sync": False,
    "depth": 5,
}


def load() -> dict:
    data = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    return data


def save(data: dict) -> None:
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    clean = {key: data.get(key, value) for key, value in DEFAULTS.items()}
    SETTINGS_FILE.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_courses() -> dict[str, list[str]] | None:
    """Return {folder name: [ILIAS targets like 'crs/123']} or None if not chosen yet."""
    if not COURSES_FILE.exists():
        return None
    try:
        data = json.loads(COURSES_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {str(name): [str(t) for t in targets] for name, targets in data.items() if targets}


def save_courses(courses: dict[str, list[str]]) -> None:
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    COURSES_FILE.write_text(json.dumps(courses, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_credentials() -> tuple[str, str] | None:
    """Return (username, password) from the login Keychain, or None."""
    import keyring
    from keyring.errors import KeyringError

    try:
        username = keyring.get_password(KEYCHAIN_SERVICE, USERNAME_ACCOUNT)
        password = keyring.get_password(KEYCHAIN_SERVICE, username) if username else None
    except KeyringError:
        return None
    return (username, password) if username and password else None


def stored_username() -> str | None:
    import keyring
    from keyring.errors import KeyringError

    try:
        return keyring.get_password(KEYCHAIN_SERVICE, USERNAME_ACCOUNT)
    except KeyringError:
        return None


def set_credentials(username: str, password: str) -> None:
    import keyring

    delete_credentials()
    keyring.set_password(KEYCHAIN_SERVICE, username, password)
    keyring.set_password(KEYCHAIN_SERVICE, USERNAME_ACCOUNT, username)


def delete_credentials() -> None:
    import keyring
    from keyring.errors import PasswordDeleteError

    username = stored_username()
    for account in filter(None, (username, USERNAME_ACCOUNT)):
        try:
            keyring.delete_password(KEYCHAIN_SERVICE, account)
        except PasswordDeleteError:
            pass
