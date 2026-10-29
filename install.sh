#!/usr/bin/env zsh
# Einmalige Installation des ILIAS-Downloaders auf macOS.
# ./install.sh                     installiert und startet danach die Einrichtung mit Rückfragen
# ./install.sh --ohne-einrichtung  nur installieren (z. B. wenn ein KI-Assistent einrichtet)
set -euo pipefail
cd "${0:A:h}"

if [[ "$(uname)" != "Darwin" ]]; then
  print "Dieser Downloader läuft nur auf macOS."; exit 1
fi

# Python 3.10 oder neuer suchen (Homebrew bevorzugt).
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
  print "Es wird Python 3.10 oder neuer benötigt."
  print "Am einfachsten über Homebrew (https://brew.sh):  brew install python@3.12"
  print "Danach ./install.sh erneut ausführen."
  exit 1
fi
print "Verwende $python ($("$python" --version))"

# Bewusst außerhalb von ~/Documents: iCloud lagert dort Dateien aus, dann hängen Python-Importe.
support="$HOME/Library/Application Support/ILIAS Downloader"
venv="$support/venv"
mkdir -p "$support"
if [[ ! -x "$venv/bin/python" ]]; then
  "$python" -m venv "$venv"
fi
"$venv/bin/python" -m pip install --quiet --upgrade pip
print "Installiere Abhängigkeiten (das dauert beim ersten Mal ein paar Minuten) …"
"$venv/bin/python" -m pip install --quiet -r requirements.txt
"$venv/bin/python" -m playwright install webkit

chmod +x run.sh setup.sh markdown.sh
if [[ "${1:-}" == "--ohne-einrichtung" || ! -t 0 ]]; then
  print "\nInstallation abgeschlossen. Einrichtung: ./setup.sh (mit Rückfragen) oder ./setup.sh --help"
else
  print "\nInstallation abgeschlossen. Jetzt folgt die Einrichtung.\n"
  ./setup.sh
fi
