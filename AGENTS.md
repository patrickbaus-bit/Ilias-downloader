# Anleitung für KI-Assistenten: ILIAS-Downloader einrichten

> Aktuelle Fassung dieser Anleitung: https://raw.githubusercontent.com/patrickbaus-bit/Ilias-downloader/main/AGENTS.md
> Repository: https://github.com/patrickbaus-bit/Ilias-downloader
> Kannst du keine Befehle selbst ausführen (z. B. ein Chat im Browser), führe die Person durch dieselben Schritte: Gib ihr jeweils einen Befehl zum Kopieren ins Terminal und lass dir die Ausgabe zurückschicken, bevor du weitermachst.

Diese Datei richtet sich an KI-Assistenten (Claude Code, Claude, Codex, Cursor, Copilot …), die einer Person helfen, den ILIAS-Downloader auf ihrem Mac zu installieren. Die Person ist meist Studierende der Uni Mannheim und hat oft wenig Terminal-Erfahrung. Sprich Deutsch mit ihr (außer sie schreibt in einer anderen Sprache), erkläre kurz, was du tust, und führe die Befehle selbst aus, soweit du ein Terminal hast.

## Regeln, die immer gelten

1. **Frage nie nach dem Uni-Passwort und gib es nirgends ein.** Zugangsdaten trägt die Person selbst ein, per Doppelklick auf „Zugangsdaten eingeben.command“ im Projektordner (Passwort wird verdeckt abgefragt und nur im macOS-Schlüsselbund gespeichert; siehe Schritt 5). Schreibt sie dir das Passwort trotzdem in den Chat, benutze es nicht und empfiehl ihr, es zu ändern.
2. **Melde dich nicht selbst bei ILIAS an.** Wenn sich ein Browserfenster für den Uni-Login öffnet, meldet sich die Person dort selbst an.
3. Ändere den Programmcode nicht, um ein Problem „wegzuhacken“. Funktioniert etwas nicht, nutze die Fehlerbehebung unten oder schlage vor, ein GitHub-Issue anzulegen.
4. Lege keine persönlichen Dateien (Einstellungen, Sitzung, Downloads, Logs) im Repository ab und committe sie nie.
5. Der Downloader läuft nur auf **macOS**. Auf Windows oder Linux: Sag das ehrlich und brich ab.

## Ablauf

Führe die Schritte der Reihe nach aus. Prüfe nach jedem Schritt die Ausgabe, bevor du weitermachst.

### 1. Voraussetzungen prüfen

```zsh
sw_vers -productVersion   # macOS 13 oder neuer
```

Mehr braucht es nicht. Homebrew, Git, Xcode oder ein vorinstalliertes Python sind **nicht** nötig: Der Installer holt sich Python selbst über das Werkzeug `uv` in den Benutzerordner, ohne Admin-Passwort.

### 2. Repository holen

Wenn du nicht schon im Projektordner bist (erkennbar an `install.sh` und dieser Datei), lade es ohne Git herunter (Git würde auf frischen Macs erst die Xcode-Entwicklerwerkzeuge installieren wollen):

```zsh
mkdir -p ~/Documents && cd ~/Documents
curl -L -o ilias-downloader.zip https://github.com/patrickbaus-bit/Ilias-downloader/archive/refs/heads/main.zip
unzip -q -o ilias-downloader.zip && rm ilias-downloader.zip
cd Ilias-downloader-main
```

Ist Git bereits vorhanden (`git --version` funktioniert ohne Dialog), geht auch `git clone https://github.com/patrickbaus-bit/Ilias-downloader.git`; der Ordner heißt dann `Ilias-downloader`. Merke dir den absoluten Pfad (`pwd`), du brauchst ihn später.

### 3. Installieren

```zsh
zsh install.sh --ohne-einrichtung
```

Dauert beim ersten Mal einige Minuten (Python, Pakete und ein WebKit-Browser für die Anmeldung). Am Ende muss „Installation abgeschlossen“ stehen.

### 4. Die Person fragen und einstellen

Frag die Person (eine kurze Nachricht mit allen Fragen, Vorschläge gleich mitgeben):

- Wohin sollen die Kursmaterialien? Vorschlag: `~/Documents/Uni/ILIAS`
- Sollen nach jedem Abgleich Markdown-Kopien für KI-Tools entstehen (empfohlen), und wenn ja, wohin? Vorschlag: `~/Documents/Uni/KI-Markdown` (darf **nicht** im Materialordner liegen)
- Soll der Mac täglich automatisch nach neuen Materialien schauen, und um wie viel Uhr?

Dann ohne Rückfragen einstellen, z. B.:

```zsh
./setup.sh --materialordner ~/Documents/Uni/ILIAS \
           --markdown-ordner ~/Documents/Uni/KI-Markdown \
           --markdown-nach-abgleich ja \
           --hintergrund ja \
           --taeglich-um 09:00
```

Das legt beide Ordner sofort an. `--markdown-nach-abgleich ja` gilt für **jeden** Abgleich, auch den ersten und alle manuellen. Kein täglicher Abgleich gewünscht: `--taeglich-um` weglassen. `--hintergrund ja` betrifft nur den täglichen Lauf und wirkt nur mit gespeicherten Zugangsdaten; sonst öffnet sich dabei ein Browserfenster zum Anmelden.

### 5. Zugangsdaten (macht die Person selbst)

Erkläre kurz: Mit gespeicherter Uni-ID und Passwort meldet sich der Downloader selbst an und der tägliche Abgleich läuft ohne Zutun. Ohne öffnet sich jedes Mal ein Fenster, in dem sie sich anmeldet. Beides ist in Ordnung; empfehlenswert ist Speichern.

Wenn sie speichern möchte, sag ihr (Pfad durch den echten Projektordner ersetzen):

> Öffne im Finder den Ordner `<PROJEKTORDNER>` und mach einen **Doppelklick auf „Zugangsdaten eingeben.command“**. Es öffnet sich ein Terminal-Fenster. Gib dort deine Uni-ID ein (z. B. `mmustermann`) und dann dein Passwort. Das Passwort wird beim Tippen nicht angezeigt, das ist normal. Sag mir Bescheid, wenn dort „Gespeichert“ steht.

Du kannst den Ordner auch selbst öffnen: `open <PROJEKTORDNER>`. Meldet macOS, die Datei könne nicht geöffnet werden: Rechtsklick → **Öffnen** → **Öffnen**. Warte auf ihre Rückmeldung und prüfe mit `./setup.sh --status`, ob `zugangsdaten_gespeichert_fuer` gesetzt ist.

### 6. Kurse auswählen und erster Abgleich

```zsh
./run.sh --kurse-auflisten
```

Ohne gespeicherte Zugangsdaten öffnet sich ein Browserfenster: Bitte die Person, sich dort mit Uni-ID und Passwort anzumelden; der Befehl wartet so lange. Danach erscheint eine nummerierte Liste der Kurse des **laufenden Semesters** (HWS: September bis Februar, FSS: März bis August) plus schon vorhandener Kurse des nächsten; vergangene Semester blendet der Downloader automatisch aus. Tutoriums- und Übungsgruppen hängen an ihrem Kurs und landen in dessen Ordner. Zeig der Person die Liste und frag, ob sie alle Kurse möchte (empfohlen) oder nur einzelne. Dann:

```zsh
./run.sh --kurse aktuell        # alle angezeigten Kurse (empfohlen)
./run.sh --kurse "1 3 5-8"      # nur einzelne Nummern aus der Liste
```

Mit `aktuell` folgt der Downloader künftig von selbst dem Semester: Neue Kurse (auch des nächsten Semesters) kommen bei jedem Abgleich dazu, und nach Semesterende fallen die alten weg. Bei einer Auswahl einzelner Nummern bleibt sie bis zum Semesterwechsel fest; danach nimmt er alle Kurse des neuen Semesters. Ältere Semester nur bei ausdrücklichem Wunsch: `./run.sh --kurse-auflisten --alle-semester`, danach `./run.sh --alle-semester --kurse "…"`.

Der erste Abgleich lädt alle Materialien und erzeugt danach die Markdown-Kopien (falls eingeschaltet). Das dauert grob 3 bis 5 Minuten pro Kurs; lass den Befehl durchlaufen und sag der Person, dass der Mac so lange wach bleiben sollte.

### 7. Täglichen Abgleich testen (falls eingerichtet)

Nach dem ersten Abgleich den geplanten Lauf einmal sofort auslösen, damit macOS seine Berechtigungsfragen jetzt stellt, während die Person da ist, und nicht unbemerkt um 9 Uhr:

```zsh
./setup.sh --zeitplan-testen
```

Es öffnet sich ein neues Terminal-Fenster mit dem Abgleich. Sag der Person vorher: Fragt macOS, ob Terminal auf „Dokumente“ zugreifen darf, oder ob Python den Schlüsselbund-Eintrag „ILIAS Downloader“ verwenden darf, klickt sie **Erlauben** bzw. **Immer erlauben**. Prüfe danach das Ende des Protokolls:

```zsh
tail -20 "$HOME/Library/Application Support/ILIAS Downloader/ilias-downloader.log"
```

Dort muss „beendet mit Status 0“ stehen. Bei einem anderen Status: Meldung darüber lesen und die Fehlerbehebung unten nutzen.

### 8. Abschluss prüfen

```zsh
./setup.sh --status
```

Prüfe, dass Ordner, Kurse und (falls gewünscht) die Uhrzeit stimmen, dass im Materialordner Kursordner mit Dateien liegen und im Markdown-Ordner `INDEX.md` existiert. Öffne beide Ordner für die Person (`open <Ordner>`). Fasse in wenigen Sätzen zusammen:

- wo ihre Dateien und die Markdown-Kopien liegen,
- falls ein täglicher Abgleich eingerichtet ist: dass sich zur Uhrzeit ein Terminal-Fenster öffnet, das sie nach dem Lauf schließen kann,
- dass der Downloader zum neuen Semester automatisch auf die neuen Kurse umstellt (alte Ordner bleiben liegen),
- dass sie Passwortänderungen per Doppelklick auf „Zugangsdaten eingeben.command“ einträgt.

## Befehlsübersicht

| Befehl | Zweck |
|---|---|
| `zsh install.sh --ohne-einrichtung` | Installieren bzw. aktualisieren, ohne Rückfragen |
| `./setup.sh --status` | Aktuelle Einrichtung als JSON |
| `./setup.sh --materialordner P --markdown-ordner P --hintergrund ja\|nein --markdown-nach-abgleich ja\|nein --taeglich-um HH:MM` | Einstellen ohne Rückfragen (nur angegebene Werte ändern sich, Ordner werden angelegt) |
| `./setup.sh --zeitplan-testen` | Geplanten Abgleich sofort einmal auslösen (wie zur eingestellten Uhrzeit) |
| `./setup.sh --zeitplan-entfernen` | Täglichen Abgleich ausschalten |
| „Zugangsdaten eingeben.command“ (Doppelklick) bzw. `./setup.sh --zugangsdaten` | **Nur die Person selbst**, fragt verdeckt nach dem Passwort |
| `./setup.sh --zugangsdaten-loeschen` | Zugangsdaten aus dem Schlüsselbund löschen |
| `./run.sh` | Abgleich mit sichtbarem Browserfenster |
| `./run.sh --headless` | Abgleich ohne Fenster (braucht Zugangsdaten oder gültige Sitzung) |
| `./run.sh --markdown` / `--kein-markdown` | Markdown diesmal erzwingen / auslassen (Standard: laut Einstellung) |
| `./run.sh --kurse-auflisten [--alle-semester]` | Nur Kurse anzeigen (neuestes Semester bzw. alle), nichts laden |
| `./run.sh --kurse aktuell` / `--kurse "1 3"` | Kurse wählen (alle des neuesten Semesters, folgt künftig automatisch / nur diese Nummern) und laden |
| `./markdown.sh [--retry-failed]` | Markdown-Kopien erzeugen |

Alles Persönliche liegt in `~/Library/Application Support/ILIAS Downloader/` (Python-Umgebung, `settings.json`, `courses.json`, ILIAS-Sitzung, Protokoll `ilias-downloader.log`), nicht im Repository.

## Fehlerbehebung

| Meldung / Problem | Lösung |
|---|---|
| `Bitte zuerst ./install.sh ausführen` | Schritt 3 wiederholen und die Ausgabe auf Fehler prüfen. |
| `permission denied: ./run.sh` | `zsh install.sh --ohne-einrichtung` erneut ausführen (setzt die Ausführungsrechte). |
| Installation von uv oder Paketen scheitert | Internetverbindung prüfen (Uni-WLAN/VPN kann blockieren), dann `rm -rf "$HOME/Library/Application Support/ILIAS Downloader/venv"` und `zsh install.sh --ohne-einrichtung`. |
| `ILIAS-Anmeldung fehlgeschlagen` | Uni-ID/Passwort falsch. Person trägt sie per Doppelklick auf „Zugangsdaten eingeben.command“ neu ein. Nicht mehrfach hintereinander probieren (Kontosperre). |
| `ILIAS verlangt einen weiteren Anmeldeschritt` | `./run.sh` (mit Fenster) starten, Person schließt die Anmeldung selbst ab. |
| `Auf ILIAS wurden keine Kurse gefunden` | Person soll prüfen, ob sie auf ILIAS unter „Meine Kurse und Gruppen“ Kurse hat. Sonst Issue auf GitHub. |
| `Operation not permitted` beim Ordner „Dokumente“ | Systemeinstellungen → Datenschutz & Sicherheit → Dateien und Ordner → dem Terminal (bzw. deiner App) „Dokumente“ erlauben. Alternativ einen Ordner außerhalb von Dokumente wählen. |
| Täglicher Abgleich bricht mit `Operation not permitted` ab | Terminal hat keinen Zugriff auf „Dokumente“: Systemeinstellungen → Datenschutz & Sicherheit → Dateien und Ordner → Terminal → Dokumente einschalten, dann `./setup.sh --zeitplan-testen`. |
| Täglicher Abgleich wartet auf eine Schlüsselbund-Abfrage | Passiert nach einer Neuinstallation von Python. Einmal **Immer erlauben** klicken, oder Zugangsdaten per Doppelklick auf „Zugangsdaten eingeben.command“ neu speichern. |
| Täglicher Abgleich findet den Projektordner nicht | Der Ordner wurde verschoben. Im neuen Ordner `./setup.sh --taeglich-um HH:MM` erneut ausführen. |
| `launchctl bootstrap` schlägt fehl | `./setup.sh --zeitplan-entfernen`, dann `./setup.sh --taeglich-um HH:MM` erneut. |
| Download hängt bei „prüfe vorhandene Originaldateien“ | Dateien liegen nur in iCloud. Der Downloader überspringt sie nach 5 Sekunden je Datei; abwarten. |
| Eine Seite wird nicht gefunden / ILIAS sieht anders aus | ILIAS-Struktur hat sich geändert. Nicht den Code umschreiben, sondern ein Issue auf GitHub vorschlagen. |
