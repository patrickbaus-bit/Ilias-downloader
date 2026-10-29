# Anleitung für KI-Assistenten: ILIAS-Downloader einrichten

Diese Datei richtet sich an KI-Assistenten (Claude Code, Claude, Codex, Cursor, Copilot …), die einer Person helfen, den ILIAS-Downloader auf ihrem Mac zu installieren. Die Person ist meist Studierende der Uni Mannheim und hat oft wenig Terminal-Erfahrung. Sprich Deutsch mit ihr (außer sie schreibt in einer anderen Sprache), erkläre kurz, was du tust, und führe die Befehle selbst aus, soweit du ein Terminal hast.

## Regeln, die immer gelten

1. **Frage nie nach dem Uni-Passwort und gib es nirgends ein.** Zugangsdaten trägt die Person selbst ein, indem sie in ihrem eigenen Terminal-Fenster `./setup.sh --zugangsdaten` ausführt (Passwort wird verdeckt abgefragt und nur im macOS-Schlüsselbund gespeichert). Schreibt sie dir das Passwort trotzdem in den Chat, benutze es nicht und empfiehl ihr, es zu ändern.
2. **Melde dich nicht selbst bei ILIAS an.** Wenn sich ein Browserfenster für den Uni-Login öffnet, meldet sich die Person dort selbst an.
3. Ändere den Programmcode nicht, um ein Problem „wegzuhacken“. Funktioniert etwas nicht, nutze die Fehlerbehebung unten oder schlage vor, ein GitHub-Issue anzulegen.
4. Lege keine persönlichen Dateien (Einstellungen, Sitzung, Downloads, Logs) im Repository ab und committe sie nie.
5. Der Downloader läuft nur auf **macOS**. Auf Windows oder Linux: Sag das ehrlich und brich ab.

## Ablauf

Führe die Schritte der Reihe nach aus. Prüfe nach jedem Schritt die Ausgabe, bevor du weitermachst.

### 1. Voraussetzungen prüfen

```zsh
sw_vers -productVersion   # macOS 13 oder neuer
python3 --version          # 3.10 oder neuer
```

Fehlt Python 3.10+, frag, ob du es über Homebrew installieren darfst. Ist Homebrew nicht da (`command -v brew` leer), bitte die Person, den Installationsbefehl von https://brew.sh selbst in ihr Terminal zu kopieren (er fragt nach ihrem Mac-Passwort), und danach:

```zsh
brew install python@3.12
```

### 2. Repository holen

Wenn du nicht schon im Projektordner bist (erkennbar an `install.sh` und dieser Datei):

```zsh
cd ~/Documents
git clone https://github.com/patrickbaus-bit/Ilias-downloader.git
cd Ilias-downloader
```

Ohne Git: Die Person lädt auf GitHub über **Code → Download ZIP** herunter und entpackt; dann in den entpackten Ordner wechseln.

### 3. Installieren

```zsh
chmod +x install.sh
./install.sh --ohne-einrichtung
```

Dauert beim ersten Mal einige Minuten (Python-Pakete und ein WebKit-Browser für Playwright). Am Ende muss „Installation abgeschlossen“ stehen.

### 4. Die Person fragen und einstellen

Frag die Person (eine kurze Nachricht mit allen Fragen):

- Wohin sollen die Kursmaterialien? Vorschlag: `~/Documents/Uni/ILIAS`
- Sollen zusätzlich Markdown-Kopien für KI-Tools entstehen, und wenn ja, wohin? Vorschlag: `~/Documents/Uni/KI-Markdown` (darf **nicht** im Materialordner liegen)
- Soll der Mac täglich automatisch nach neuen Materialien schauen, und um wie viel Uhr?

Dann ohne Rückfragen einstellen, z. B.:

```zsh
./setup.sh --materialordner ~/Documents/Uni/ILIAS \
           --markdown-ordner ~/Documents/Uni/KI-Markdown \
           --markdown-nach-abgleich ja \
           --hintergrund ja \
           --taeglich-um 09:00
```

Kein täglicher Abgleich gewünscht: `--taeglich-um` weglassen. `--hintergrund ja` wirkt nur, wenn Zugangsdaten gespeichert sind; sonst öffnet sich beim täglichen Lauf ein Browserfenster zum Anmelden.

### 5. Zugangsdaten (macht die Person selbst)

Erkläre: Mit gespeicherter Uni-ID und Passwort meldet sich der Downloader selbst an und kann im Hintergrund laufen. Ohne öffnet sich jedes Mal ein Fenster zum Anmelden. Beides ist in Ordnung.

Wenn sie speichern möchte, sag ihr wörtlich, was sie tun soll:

> Öffne das Programm „Terminal“ (Cmd + Leertaste, „Terminal“ tippen), füge diese Zeile ein und drück Enter:
> `cd <PROJEKTORDNER> && ./setup.sh --zugangsdaten`
> Gib dort deine Uni-ID und dein Passwort ein. Das Passwort wird beim Tippen nicht angezeigt, das ist normal.

Ersetze `<PROJEKTORDNER>` durch den echten absoluten Pfad (`pwd`). Warte, bis sie Bescheid gibt, und prüfe dann mit `./setup.sh --status`, ob `zugangsdaten_gespeichert_fuer` gesetzt ist.

### 6. Kurse auswählen

```zsh
./run.sh --kurse-auflisten
```

Ohne gespeicherte Zugangsdaten öffnet sich ein Browserfenster: Bitte die Person, sich dort anzumelden; der Befehl wartet so lange. Danach erscheint eine nummerierte Liste aller Kurse und Gruppen. Zeig sie der Person und frag, welche sie möchte (oft nur die des aktuellen Semesters). Dann:

```zsh
./run.sh --kurse "1 3 5-8"     # oder: --kurse alle
```

Das speichert die Auswahl und startet den ersten Download. Je nach Kursmenge dauert das einige Minuten bis über eine Stunde; lass den Befehl durchlaufen.

### 7. Abschluss prüfen

```zsh
./setup.sh --status
```

Prüfe, dass Ordner, Kurse und (falls gewünscht) die Uhrzeit stimmen, und dass im Materialordner Kursordner mit Dateien liegen. Fasse für die Person in wenigen Sätzen zusammen:

- wo ihre Dateien liegen,
- dass `./run.sh` jederzeit neue Materialien lädt (im Projektordner ausführen),
- dass zum neuen Semester `./run.sh --kurse-waehlen` die Kurse neu auswählt,
- falls ein täglicher Abgleich eingerichtet ist: dass sich zur Uhrzeit ein Terminal-Fenster öffnet und sie es nach dem Lauf schließen kann.

Wenn Markdown aktiv ist und noch keine Kopien da sind, kannst du sie gleich erzeugen: `./markdown.sh` (dauert bei vielen PDFs länger).

## Befehlsübersicht

| Befehl | Zweck |
|---|---|
| `./install.sh --ohne-einrichtung` | Installieren bzw. aktualisieren, ohne Rückfragen |
| `./setup.sh --status` | Aktuelle Einrichtung als JSON |
| `./setup.sh --materialordner P --markdown-ordner P --hintergrund ja\|nein --markdown-nach-abgleich ja\|nein --taeglich-um HH:MM` | Einstellen ohne Rückfragen (nur angegebene Werte ändern sich) |
| `./setup.sh --zeitplan-entfernen` | Täglichen Abgleich ausschalten |
| `./setup.sh --zugangsdaten` | **Nur die Person selbst**, fragt verdeckt nach dem Passwort |
| `./setup.sh --zugangsdaten-loeschen` | Zugangsdaten aus dem Schlüsselbund löschen |
| `./run.sh` | Abgleich mit sichtbarem Browserfenster |
| `./run.sh --headless` | Abgleich ohne Fenster (braucht Zugangsdaten oder gültige Sitzung) |
| `./run.sh --markdown` | Nach dem Abgleich Markdown erzeugen |
| `./run.sh --kurse-auflisten` | Nur Kurse anzeigen, nichts laden |
| `./run.sh --kurse "1 3"` | Kurse ohne Rückfrage wählen und laden |
| `./markdown.sh [--retry-failed]` | Markdown-Kopien erzeugen |

Alles Persönliche liegt in `~/Library/Application Support/ILIAS Downloader/` (Python-Umgebung, `settings.json`, `courses.json`, ILIAS-Sitzung, Protokoll `ilias-downloader.log`), nicht im Repository.

## Fehlerbehebung

| Meldung / Problem | Lösung |
|---|---|
| `Bitte zuerst ./install.sh ausführen` | Schritt 3 wiederholen und die Ausgabe auf Fehler prüfen. |
| `pip` scheitert beim Bauen eines Pakets | Python-Version prüfen; mit Homebrew-Python 3.12 neu installieren: `rm -rf "$HOME/Library/Application Support/ILIAS Downloader/venv"` und `./install.sh --ohne-einrichtung`. |
| `ILIAS-Anmeldung fehlgeschlagen` | Uni-ID/Passwort falsch. Person führt `./setup.sh --zugangsdaten` erneut aus. Nicht mehrfach hintereinander probieren (Kontosperre). |
| `ILIAS verlangt einen weiteren Anmeldeschritt` | `./run.sh` (mit Fenster) starten, Person schließt die Anmeldung selbst ab. |
| `Auf ILIAS wurden keine Kurse gefunden` | Person soll prüfen, ob sie auf ILIAS unter „Meine Kurse und Gruppen“ Kurse hat. Sonst Issue auf GitHub. |
| `Operation not permitted` beim Ordner „Dokumente“ | Systemeinstellungen → Datenschutz & Sicherheit → Dateien und Ordner → dem Terminal (bzw. deiner App) „Dokumente“ erlauben. Alternativ einen Ordner außerhalb von Dokumente wählen. |
| `launchctl bootstrap` schlägt fehl | `./setup.sh --zeitplan-entfernen`, dann `./setup.sh --taeglich-um HH:MM` erneut. |
| Download hängt bei „prüfe vorhandene Originaldateien“ | Dateien liegen nur in iCloud. Der Downloader überspringt sie nach 5 Sekunden je Datei; abwarten. |
| Eine Seite wird nicht gefunden / ILIAS sieht anders aus | ILIAS-Struktur hat sich geändert. Nicht den Code umschreiben, sondern ein Issue auf GitHub vorschlagen. |
