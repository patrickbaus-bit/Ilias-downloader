# ILIAS-Downloader – Uni Mannheim

Lädt automatisch alle Materialien aus deinen ILIAS-Kursen auf deinen Mac, sortiert sie in einen Ordner pro Kurs und erzeugt auf Wunsch Markdown-Kopien, die du KI-Tools (ChatGPT, Claude, NotebookLM …) als Kontext geben kannst.

- Lädt nur, was du in ILIAS ohnehin sehen darfst. Es werden keine Zugriffsrechte umgangen.
- Lädt nur **neue** Dateien. Was du schon hast, wird am Inhalt erkannt, auch wenn du es umbenannt oder verschoben hast.
- Läuft auf Wunsch jeden Tag automatisch zu einer festen Uhrzeit.
- Uni-ID und Passwort bleiben im macOS-Schlüsselbund. Sie werden nirgendwohin geschickt außer an das Uni-Login `idp.uni-mannheim.de`.

**Voraussetzungen:** ein Mac mit macOS 13 oder neuer (Apple-Silicon oder Intel) und Internet. Python, Homebrew oder Admin-Rechte brauchst du nicht, der Installer holt sich alles Nötige selbst.

---

## Einrichtung mit KI (empfohlen)

Du musst nichts selbst im Terminal machen: Ein KI-Assistent mit Terminal-Zugriff richtet alles für dich ein, zum Beispiel **Claude** (Claude-Desktop-App mit Zugriff auf deinen Mac, oder Claude Code), **Codex** oder **Cursor**. Kopiere einfach diesen Text hinein:

```text
Richte mir bitte den ILIAS-Downloader auf meinem Mac ein:
https://github.com/patrickbaus-bit/Ilias-downloader

Lade das Repository nach ~/Documents herunter, lies zuerst die Datei AGENTS.md
und folge genau dieser Anleitung. Frag mich, wenn du eine Entscheidung von mir brauchst.
```

Das passiert danach, und das machst du dabei:

1. **Erlauben.** Die KI fragt vor jedem Befehl um Erlaubnis. Fragt macOS, ob die App auf „Dokumente“ zugreifen darf: **Erlauben**.
2. **Drei Fragen beantworten:** wohin die Kursmaterialien sollen, ob (und wohin) Markdown-Kopien für KI-Tools entstehen sollen, und ob der Mac täglich nach neuen Materialien schauen soll und wann. Die KI macht Vorschläge, „passt so“ reicht.
3. **Zugangsdaten speichern (empfohlen):** Die KI bittet dich, im Downloader-Ordner auf **„Zugangsdaten eingeben.command“** doppelzuklicken. Im Fenster, das sich öffnet, tippst du Uni-ID und Passwort ein (das Passwort bleibt beim Tippen unsichtbar) und sagst der KI Bescheid. **Dein Passwort gibst du nie in den Chat ein**, es landet nur im macOS-Schlüsselbund.
4. **Falls du nichts gespeichert hast:** im Browserfenster, das sich öffnet, ganz normal beim Uni-Login anmelden.
5. **Kurse auswählen:** Die KI zeigt dir eine nummerierte Liste deiner ILIAS-Kurse. Du antwortest z. B. „1, 3 und 5 bis 8“.
6. **Warten:** Der erste Download (samt Markdown) dauert je nach Menge Minuten bis über eine Stunde. Der Mac sollte so lange wach bleiben.

Danach musst du nichts mehr tun.

Nutzt du eine KI ohne Terminal-Zugriff (z. B. ChatGPT im Browser), funktioniert der gleiche Text auch: Dann erklärt sie dir Schritt für Schritt, was du ins Terminal kopieren sollst.

---

## Installation von Hand (einmalig, ca. 5 Minuten)

### 1. Downloader herunterladen

Öffne das Programm **Terminal** (Cmd + Leertaste → „Terminal“) und kopiere diese Zeilen hinein:

```zsh
mkdir -p ~/Documents && cd ~/Documents
curl -L -o ilias-downloader.zip https://github.com/patrickbaus-bit/Ilias-downloader/archive/refs/heads/main.zip
unzip -q -o ilias-downloader.zip && rm ilias-downloader.zip
```

Der Ordner heißt dann `Dokumente/Ilias-downloader-main`. Mit Git geht auch `git clone https://github.com/patrickbaus-bit/Ilias-downloader.git`.

### 2. Installieren und einrichten

```zsh
cd ~/Documents/Ilias-downloader-main
zsh install.sh
```

Der Installer lädt beim ersten Mal Python und alle Pakete in deinen Benutzerordner (einige Minuten, kein Admin-Passwort nötig).

Danach fragt er:

1. **Uni-ID und Passwort** – optional. Mit gespeicherten Daten meldet sich der Downloader selbst an und kann im Hintergrund laufen. Ohne öffnet sich jedes Mal ein Fenster, in dem du dich selbst anmeldest.
2. **Ordner und Optionen** – wohin die Kursmaterialien sollen (Standard: `Dokumente/Uni/ILIAS`), ob nach jedem Abgleich Markdown-Kopien entstehen sollen und wohin, und ob der tägliche Abgleich ohne Browserfenster laufen soll.
3. **Täglicher Abgleich** – ob und um welche Uhrzeit der Mac jeden Tag nach neuen Materialien schauen soll.

### 3. Erster Abgleich

```zsh
./run.sh
```

Beim ersten Mal listet der Downloader alle Kurse und Gruppen auf, in denen du auf ILIAS eingeschrieben bist. Du gibst die Nummern der Kurse ein, die du haben willst (z. B. `1 3 5-8`, oder Enter für alle). Danach beginnt der Download.

Falls macOS fragt, ob das Terminal auf den Ordner „Dokumente“ zugreifen darf: **Erlauben** klicken.

---

## Benutzung

| Was | Befehl |
|---|---|
| Neue Materialien laden (mit sichtbarem Browserfenster) | `./run.sh` |
| Ohne Browserfenster (braucht gespeicherte Zugangsdaten) | `./run.sh --headless` |
| Markdown diesmal auslassen / erzwingen (Standard: laut Einstellung) | `./run.sh --kein-markdown` / `./run.sh --markdown` |
| Kurse neu auswählen (z. B. neues Semester) | `./run.sh --kurse-waehlen` |
| Nur Markdown-Kopien erzeugen | `./markdown.sh` |
| Fehlgeschlagene Markdown-Dateien erneut versuchen | `./markdown.sh --retry-failed` |
| Alles neu einrichten | `./setup.sh` |
| Zugangsdaten ändern / löschen | Doppelklick auf „Zugangsdaten eingeben.command“ / `./setup.sh --zugangsdaten-loeschen` |
| Nur Ordner und Optionen ändern | `./setup.sh --ordner` |
| Uhrzeit ändern / täglichen Abgleich ausschalten | `./setup.sh --zeitplan` / `./setup.sh --zeitplan-entfernen` |

**Kurzbefehl:** Wenn du nicht jedes Mal in den Ordner wechseln willst, einmal ausführen (Pfad ggf. anpassen):

```zsh
echo 'alias iliasdl="$HOME/Documents/Ilias-downloader-main/run.sh"' >> ~/.zshrc
source ~/.zshrc
```

Danach genügt überall `iliasdl`.

### Täglicher Abgleich

Zur eingestellten Uhrzeit öffnet sich ein Terminal-Fenster und lädt neue Dateien. Läuft alles glatt, kannst du es einfach schließen. Bei einem Fehler bleibt es offen, damit du die Meldung lesen kannst. War der Mac zu der Zeit aus oder zugeklappt, läuft der Abgleich nach dem nächsten Aufwachen.

Ein Protokoll aller Läufe liegt in `~/Library/Application Support/ILIAS Downloader/ilias-downloader.log`.

---

## Wie die Dateien sortiert werden

Im Zielordner entsteht ein Unterordner pro Kurs, darin:

```
Vorlesung/                 Folien, Skripte, Handouts
Übung/Aufgaben/            Übungsblätter
Übung/Loesungen/           Lösungen
Tutorium/Aufgaben/
Tutorium/Loesungen/
Prüfung/Aufgaben/          Altklausuren
Prüfung/Loesungen/
Organisatorisches/         Syllabus, Termine, Infoblätter
Sonstiges/                 alles, was keiner Regel entspricht
```

Die Einordnung richtet sich nach Datei- und ILIAS-Ordnernamen. Du kannst Dateien danach frei verschieben oder umbenennen, sie werden trotzdem nicht erneut heruntergeladen. Gibt es eine Datei mit gleichem Namen, aber neuem Inhalt, wird die neue Version mit einem kurzen Kürzel am Namensende daneben gelegt.

**Kursordner umbenennen oder zusammenlegen:** Die Kursauswahl steht in `~/Library/Application Support/ILIAS Downloader/courses.json`. Dort kannst du den Ordnernamen ändern (vorher den Ordner im Finder genauso umbenennen) oder eine Tutoriumsgruppe zu einem Kurs hinzufügen:

```json
{
  "Finanzmathematik": ["crs/1234567", "grp/1234570"]
}
```

## Markdown für KI-Tools

Aus allen PDF-, Word-, PowerPoint-, Excel-, CSV-, HTML- und Bilddateien entstehen Markdown-Kopien in derselben Ordnerstruktur. Ist Markdown eingeschaltet, passiert das automatisch nach jedem Abgleich; `./markdown.sh` erzeugt sie auch ohne Abgleich. Die Dateien sind als Kontext für KI-Modelle gedacht:

- Vor jeder PDF-Seite steht `[Seite 12 von 80]`, vor jeder Folie `[Folie 7 von 30]`. So können du und die KI über dieselben Stellen sprechen.
- Text in Bildern, Scans und Screenshots wird lokal per Texterkennung (Apple Vision) gelesen.
- Excel-Tabellen behalten Spaltenbuchstaben, Zeilennummern und Formeln.
- Im Zielordner erklärt `_KI-ANLEITUNG.md` der KI diese Konventionen, `INDEX.md` listet alle Dateien.
- Nur neue oder geänderte Dateien werden umgewandelt. Alles läuft offline auf deinem Mac, ohne KI-Dienst.

Der Konverter funktioniert auch unabhängig von ILIAS für beliebige Ordner:

```zsh
./markdown.sh --source '/irgendein/Ordner' --target '/Ziel/Ordner'
```

---

## Probleme?

- **„Bitte zuerst ./install.sh ausführen“** – die Installation ist nicht durchgelaufen. `zsh install.sh` erneut starten und auf Fehlermeldungen achten (Uni-WLAN oder VPN können Downloads blockieren).
- **„ILIAS-Anmeldung fehlgeschlagen“** – Uni-ID oder Passwort stimmen nicht. Per Doppelklick auf „Zugangsdaten eingeben.command“ neu eingeben. Der Downloader versucht es pro Lauf nur einmal, damit dein Konto nicht gesperrt wird.
- **„ILIAS verlangt einen weiteren Anmeldeschritt“** – z. B. Zwei-Faktor-Abfrage. Einmal `./run.sh` starten und die Anmeldung im sichtbaren Fenster abschließen. Danach merkt sich der Downloader die Sitzung eine Weile. Für den täglichen Abgleich ggf. mit `./setup.sh --ordner` die Hintergrund-Option ausschalten.
- **„Operation not permitted“ / keine Dateien im Ordner „Dokumente“** – Systemeinstellungen → Datenschutz & Sicherheit → Dateien und Ordner → beim Terminal „Dokumente“ erlauben.
- **Ein Kurs fehlt in der Liste** – der Downloader liest die Kurse aus „Meine Kurse und Gruppen“ auf ILIAS. Kurs dort beitreten und `./run.sh --kurse-waehlen` ausführen.
- **Dateien werden nicht gefunden** – ILIAS ändert gelegentlich seine Seitenstruktur. Bitte ein Issue hier auf GitHub anlegen (ohne persönliche Daten).

## Aktualisieren

Neue Version wie in Schritt 1 herunterladen (bzw. `git pull`) und `zsh install.sh` ausführen. Deine Einstellungen, Kursauswahl und Zugangsdaten bleiben erhalten.

## Deinstallieren

```zsh
./setup.sh --zeitplan-entfernen
./setup.sh --zugangsdaten-loeschen
rm -rf "$HOME/Library/Application Support/ILIAS Downloader" "$HOME/Library/Caches/ILIAS Downloader"
```

Danach den Downloader-Ordner löschen. Deine heruntergeladenen Kursmaterialien bleiben erhalten.

## Wo liegt was?

| Was | Wo |
|---|---|
| Programm | dieser Ordner |
| Python-Umgebung, Einstellungen, Kursauswahl, ILIAS-Sitzung, Protokoll | `~/Library/Application Support/ILIAS Downloader/` |
| Uni-ID und Passwort | macOS-Schlüsselbund, Eintrag „ILIAS Downloader – Uni Mannheim“ |
| Zeitplan | `~/Library/LaunchAgents/de.ilias-downloader.daily.plist` |

## Lizenz und Hinweise

Privates Projekt, nicht von der Universität Mannheim. Nutzung auf eigene Verantwortung; beachte die Nutzungsbedingungen von ILIAS und das Urheberrecht an den Kursmaterialien (nur für den eigenen Gebrauch, nicht weiterverbreiten).

PyMuPDF/pymupdf4llm, die für die PDF-Umwandlung verwendet werden, stehen unter der AGPL-3.0.
