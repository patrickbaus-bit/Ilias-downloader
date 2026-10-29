#!/usr/bin/env zsh
# Einmalige Installation (und Aktualisierung) des ILIAS-Downloaders auf macOS.
# ./install.sh                     installiert und startet danach die Einrichtung mit Rückfragen
# ./install.sh --ohne-einrichtung  nur installieren (z. B. wenn ein KI-Assistent einrichtet)
#
# Braucht weder Homebrew noch Admin-Rechte: Python und alle Pakete holt das Werkzeug „uv“
# (https://docs.astral.sh/uv/) in den eigenen Benutzerordner.
set -euo pipefail
cd "${0:A:h}"

if [[ "$(uname)" != "Darwin" ]]; then
  print "Dieser Downloader läuft nur auf macOS."; exit 1
fi

# Bewusst außerhalb von ~/Documents: iCloud lagert dort Dateien aus, dann hängen Python-Importe.
support="$HOME/Library/Application Support/ILIAS Downloader"
venv="$support/venv"
mkdir -p "$support"

# 1. uv finden oder in ~/.local/bin installieren (ohne Admin-Passwort, ohne Änderung an ~/.zshrc).
uv=""
for candidate in "$(command -v uv 2>/dev/null || true)" "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then uv="$candidate"; break; fi
done
if [[ -z "$uv" ]]; then
  print "Installiere das Python-Werkzeug uv nach ~/.local/bin …"
  if curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh >/dev/null; then
    uv="$HOME/.local/bin/uv"
  fi
fi

if [[ -n "$uv" && -x "$uv" ]]; then
  # 2a. Normaler Weg: uv besorgt Python 3.12 und installiert die Pakete.
  print "Richte Python 3.12 ein (beim ersten Mal ein paar Minuten) …"
  if [[ ! -x "$venv/bin/python" ]] || ! "$venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    rm -rf "$venv"
    "$uv" venv --quiet --python 3.12 "$venv"
  fi
  print "Installiere Abhängigkeiten …"
  "$uv" pip install --quiet --python "$venv/bin/python" -r requirements.txt
else
  # 2b. Ersatzweg ohne Internetzugriff auf astral.sh: vorhandenes Python 3.10+ verwenden.
  python=""
  for candidate in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
                   /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 \
                   python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && \
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      python="$(command -v "$candidate")"; break
    fi
  done
  if [[ -z "$python" ]]; then
    print "uv konnte nicht installiert werden und es gibt kein Python 3.10 oder neuer."
    print "Bitte Internetverbindung prüfen und ./install.sh erneut starten."
    exit 1
  fi
  print "Verwende $python ($("$python" --version))"
  [[ -x "$venv/bin/python" ]] || "$python" -m venv "$venv"
  "$venv/bin/python" -m pip install --quiet --upgrade pip
  print "Installiere Abhängigkeiten (beim ersten Mal ein paar Minuten) …"
  "$venv/bin/python" -m pip install --quiet -r requirements.txt
fi

print "Lade den Browser für die ILIAS-Anmeldung …"
"$venv/bin/python" -m playwright install webkit

chmod +x run.sh setup.sh markdown.sh "Zugangsdaten eingeben.command"
# Aus dem Internet geladene ZIP-Dateien sind markiert; sonst blockiert macOS den Doppelklick auf .command-Dateien.
xattr -dr com.apple.quarantine . 2>/dev/null || true

if [[ "${1:-}" == "--ohne-einrichtung" || ! -t 0 ]]; then
  print "\nInstallation abgeschlossen. Einrichtung: ./setup.sh (mit Rückfragen) oder ./setup.sh --help"
else
  print "\nInstallation abgeschlossen. Jetzt folgt die Einrichtung.\n"
  ./setup.sh
fi
