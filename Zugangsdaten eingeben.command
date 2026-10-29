#!/bin/zsh
# Doppelklick im Finder: Uni-ID und Passwort für ILIAS im macOS-Schlüsselbund speichern.
cd "${0:A:h}" || exit 1
clear
print "ILIAS-Downloader – Zugangsdaten speichern"
print "=========================================="
print "Uni-ID und Passwort werden nur im macOS-Schlüsselbund gespeichert"
print "und nur beim Uni-Login (idp.uni-mannheim.de) eingetragen.\n"
./setup.sh --zugangsdaten
print "\nDu kannst dieses Fenster jetzt schließen."
read -k 1 '?Taste drücken zum Schließen … '
