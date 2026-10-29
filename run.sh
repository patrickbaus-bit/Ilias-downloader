#!/usr/bin/env zsh
# ILIAS-Abgleich starten. Optionen: ./run.sh --help
set -euo pipefail
cd "${0:A:h}"
py="$HOME/Library/Application Support/ILIAS Downloader/venv/bin/python"
[[ -x "$py" ]] || { print "Bitte zuerst ./install.sh ausführen."; exit 1; }
export PYTHONPYCACHEPREFIX="$HOME/Library/Caches/ILIAS Downloader/pycache"
exec "$py" download_ilias.py "$@"
