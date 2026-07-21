# Bauplan: NoaToDo (lokale, sichere To-Do-App)

> **Zweck dieses Dokuments.** Es ist die vollständige, schrittweise Bauanleitung
> für NoaToDo. Eine KI (oder ein Mensch) soll es von oben nach unten abarbeiten
> können und am Ende eine lauffähige App haben, die **exakt** wie das Design­konzept
> (`NoaToDo UI Konzept.html`) aussieht. Der verbindliche technische Stack steht
> ausschliesslich in diesem Bauplan (Teil A/B). `technische Grundlage.txt` ist
> **historisch und nur teilweise gültig** (löst Plananalyse W12): rund die Hälfte
> davon (Microsoft-Graph-Sync, `winotify`-Benachrichtigungen, `sqlite3` ohne
> SQLCipher, Tailwind/React per CDN) ist nach der Sync-/Notification-Entfernung und
> der CSP-Regel G12 nicht mehr Teil des Projekts, und der Krypto-Stack (SQLCipher +
> ChaCha20 + Argon2id) fehlt darin. Bei jedem Widerspruch gilt der Bauplan, nicht
> `technische Grundlage.txt`.
>
> **Wie man dieses Dokument liest.** Teil A erklärt das Gesamtbild. Teil B legt die
> Verträge fest (Datenmodell, Bridge-API, Design-Tokens), das sind die Dinge, an
> die sich *alle* Bausteine halten müssen. Teil C ist die eigentliche Schritt-für-
> Schritt-Baufolge (Phase 0-9). Jeder Schritt hat: **Ziel**, **Tun**, **Abnahme**
> (woran man erkennt, dass der Schritt fertig ist). Teil D sammelt offene
> Entscheidungen und Erweiterungen.
>
> Regel für die ausführende KI: **Eine Phase nach der anderen.** Nicht
> vorgreifen. Nach jeder Phase die Abnahme-Kriterien prüfen, dann erst weiter.
>
> **Konsolidierungs-Stand und Redaktionsregel (2026-07-13, löst Plananalyse S3).**
> Dieses Dokument ist in Schichten gewachsen (Urtext, Audit-Nachtrag in B.9, N10,
> N11). Am 2026-07-13 wurde es konsolidiert: Jede von N10/N11 überschriebene
> Stelle im Haupttext ist **direkt korrigiert**; wo der Alt-Wortlaut noch steht,
> ist er ausdrücklich als gestrichen/überholt markiert. Der Haupttext widerspricht
> den Nachträgen also nicht mehr; die Vorrangregel „im Zweifel gilt N11" bleibt
> nur als Sicherheitsnetz für übersehene Reste bestehen. **Ab jetzt gilt als
> Redaktionsregel:** Neue Entscheidungen werden sofort an Ort und Stelle in den
> Haupttext eingearbeitet (Verträge, Gates, Phasen), der Nachtrag hält nur noch
> das Änderungsprotokoll fest (was entschieden wurde, wann, warum). Es werden
> keine neuen Textschichten mehr angehängt, die den Haupttext überschreiben.
>
> **Struktur-Umbau (2026-07-16, Umbau-Etappen 1 bis 5):** Die Nachträge sind seither
> vollständig in den Haupttext eingearbeitet: jede Norm steht in ihrem Vertrag (Teil B)
> bzw. ihrer Phase (Teil C), das Änderungsprotokoll im Entscheidungsregister (Anhang 1),
> Historisches in Anhang 3. Der Haupttext ist selbsttragend; es gilt allein die
> Leserichtung von oben nach unten, und die frühere Kopf-Anweisung „vor jeder Phase
> zuerst die Nachträge lesen" ist gestrichen.
> Seit Etappe 5 liegen auch die früher als gestrichen/überholt markierten
> Alt-Wortlaute und ANHANG 1 alt (Seed-Daten) gebündelt in Anhang 3.

---

## TEIL A: Das Gesamtbild

### A.1 Was die App ist

NoaToDo ist eine **local-first Desktop-App** für Windows, optisch an Microsoft To Do
angelehnt, aber mit zwei klaren Eigenschaften:

1. **Komplett lokal.** Alle selbst erstellten Aufgaben, alle Bearbeitungen und die
   gesamte Datenbank liegen auf dem eigenen Rechner. Es gibt keinen eigenen Server.
2. **Sicherheits-/Privatsphäre-Fokus.** App-Sperre (Lock-Screen) und Panik-Sperre
   („Emergency"), beide **zwingend, nicht abschaltbar**; die Datenbank ist **immer**
   verschlüsselt (doppelt: SQLCipher-AES-256 plus ChaCha20-Poly1305-Hülle, es gibt
   keinen unverschlüsselten Modus, G9). Im Windows Credential Manager liegt allein der
   **DPAPI-Pepper** der Schlüsselableitung (G18); es gibt keine Tokens (kein Login, kein
   Sync). Die ganze Optik trägt dieses Motiv: „warmes Terminal / lokaler Tresor".

Alle Aufgaben werden **lokal** erstellt und verwaltet. Die App spricht mit keinem
externen Dienst; es gibt keine Cloud-Anbindung und keinen Sync.

### A.2 Architektur in einem Satz

Ein **Python-Backend** (Logik, SQLite, Sicherheit) und ein
**Web-Frontend** (HTML/CSS/JS, das gesamte Design) laufen zusammen in einem nativen
Fenster, zusammengehalten von **PyWebView**. Sie reden über die `js_api`-Brücke
(JSON rein, JSON raus).

```
┌───────────────────────────── PyWebView-Fenster (WebView2) ─────────────────────────────┐
│  FRONTEND  (frontend/)                          │  BACKEND  (backend/, main.py)          │
│  index.html · style.css · app.js                │  api.py  (js_api-Klasse)               │
│  - rendert die komplette Oberfläche             │  db.py   (SQLite-Schema, CRUD)         │
│  - hält KEINE Wahrheit, nur Anzeige + Eingabe   │  security.py (Sperre/Verschlüsselung)  │
│        ── pywebview.api.methode(args) ──▶       │                                        │
│        ◀──────── JSON-Antwort ─────────         │                                        │
└─────────────────────────────────────────────────┴────────────────────────────────────────┘
                                            │
                          data/tasks.db.enc  (lokal, IMMER doppelt verschlüsselt:
                                              ChaCha20-Poly1305 über SQLCipher-AES-256;
                                              kein unverschlüsselter Modus, G9)
```

### A.3 Wichtige Designentscheidung vorweg: Frontend-Technik

Das Konzept `NoaToDo UI Konzept.html` ist ein **React-Prototyp** (React + Babel, im
Browser transpiliert) mit Mock-Daten. Die `technische Grundlage.txt` schreibt aber
**Vanilla HTML/CSS/JS ohne Build-Step** vor.

**Diese Bauanleitung setzt das Vanilla-JS um.** Begründung: kein Build-Step, kleiner,
weniger Angriffsfläche, passt zum local-first-Sicherheitsgedanken. Das ist
**verlustfrei** möglich, weil:

- Das **CSS des Konzepts ist framework-unabhängig**, es wird 1:1 übernommen (Teil B.3
  / Phase 5). Das Aussehen ist damit identisch.
- Die React-Komponenten sind kleine, klar abgegrenzte Render-Funktionen. Jede wird zu
  einer Vanilla-`render…()`-Funktion, die denselben DOM-Baum erzeugt. Teil B.4 listet
  die Zuordnung Komponente → Render-Funktion auf.

> Wer lieber React behalten will, kann React/ReactDOM per CDN laden und die Komponenten
> aus dem Konzept direkt verwenden, dann entfallen die Render-Funktionen, aber die
> Bridge-Verträge (B.2) und das Backend (Phasen 1-3, 8-9) bleiben gleich. Default
> dieses Plans = Vanilla.

### A.4 Global gestrichene Features

*(Wortgleich hierher umgezogen in Umbau-Etappe 3 aus „N11.1 Ersatzlos gestrichene Features“, Nachtrag N11 vom 2026-07-09. Etikett **N11.1**; Register: Anhang 1.)*

1. **Benachrichtigungen komplett entfernt** (wie zuvor der Microsoft-Sync). Es gibt
   keine Benachrichtigungen mehr, weder In-App noch Windows-Toasts: kein `notify.py`,
   keine Abhaengigkeit `winotify`, kein `on_notification`-Event, keine Glocken-Pille im
   Header, keine `notify`/`notifyInApp`/`notifyWindows`-Settings. Die eigene Phase dafuer
   ist entfallen und die Phasen wurden auf 0 bis 9 umnummeriert. In dieser Doku-Fassung
   bereits vollzogen; einzige verbleibende Konsequenz: die **Header-Mitte bleibt leer**
   (Brand links, Avatar rechts).

2. **Backups gestrichen.** Kein automatisches Backup, kein Restore, kein Backup-Ordner.
   Datensicherung laeuft ausschliesslich ueber den manuellen Export (Phase 7).
   Ueberschreibt: D.3 Punkt "Automatische lokale Backups" und alle "Backup written"-
   Beispiele. Die `.bak`-Generation aus Gate G16 bleibt, sie ist reine Absturzsicherung
   beim atomaren Schreiben, **kein** Nutzer-Backup.

3. **Meta-Feld der Aufgabe entfernt.** Eine Aufgabe hat nur noch `text` und `done`.
   Das Freitext-Feld `meta` (bisher z.B. Buch-Autor) faellt ueberall weg: Anzeige
   (keine Meta-Zeile mehr), Inline-Edit (nur noch Textfeld), `add_task`/`edit_task`
   (kein `meta`-Argument/Feld mehr), Export (keine Meta-Klammer). In der DB wird die
   Spalte nicht mehr verwendet. Ueberschreibt: B.1 (`tasks.meta`), B.2
   (`add_task(list_id, text, meta?)` wird `add_task(list_id, text)`; `edit_task` nur noch
   Text), B.4 (Meta-Zeile in `renderMain`/`renderTask`), Phase 6.5 Punkt 1 (Meta-Eingabe),
   Phase 7 Punkt 1 ("Meta in Klammern"), G20/G21 (Meta-Laenge/Meta-Newline entfallen),
   N8 "Meta-Feld benennen".
   **Im Code umgesetzt (2026-07-17, mit Phase 7):** Schema, `db.py`, `api.py`, Render,
   Inline-Edit und Export sind meta-frei; eine Einmal-Migration
   (`db._drop_legacy_columns()`) entfernt beim Verbinden die `meta`-Spalte samt der
   verwaisten Sync-/Faelligkeits-Altspalten (`synced`/`source`/`graph_etag`/`due_at`)
   aus Bestands-Entwicklungs-DBs.

4. **Demo-Seed-Daten entfernt.** Ein frischer Tresor startet **immer leer** (Erststart,
   nach Reset, nach Killswitch). Es werden keine Beispiel-Listen mehr eingespielt; nur
   die Default-Settings werden geschrieben. Der leere Zustand bekommt einen freundlichen
   Empty-State (Hinweis "Create your first list"). Ueberschreibt: Phase 1 Punkt 4,
   `seed_if_empty`-Demoinhalt, ANHANG 1 alt (jetzt in Anhang 3).

5. **JSON-Export entfernt.** Es gibt nur noch `txt` und `md`. Ueberschreibt: B.2
   (`export_list(id, format)` Enum wird `'md'|'txt'`), Phase 7 Punkt 1.

6. **Faelligkeiten und Erinnerungen ersatzlos gestrichen (Entscheid 2026-07-13, W15).**
   Eine Aufgabe hat **kein** Faelligkeitsdatum, kein Start-/Enddatum, keine Uhrzeit,
   keine Wiederholung, keine Erinnerung, keine Schlummerfunktion und keine
   "heute/ueberfaellig"-Sicht. Das frueher vorhandene Feld `due_at` ist aus Schema und
   Bridge entfernt und wird **nicht** wieder eingefuehrt. Eine Aufgabe ist genau `text`
   + `done` (siehe Punkt 3).
   - **Nicht gebaut werden:** DB-Spalte `due_at` (oder aehnlich benannt), ein
     Datums-Argument in `add_task`/`edit_task`, ein Datumspicker oder Datums-Chip in der
     Aufgabenzeile bzw. im Inline-Edit, Sortierung/Filter/Gruppierung nach Datum, eine
     Faelligkeits-Spalte im Export, ein Hintergrund-Timer, der Termine prueft.
   - **Warum:** Faelligkeiten sind ohne Benachrichtigungen (Punkt 1: ersatzlos gestrichen)
     weitgehend zahnlos, und Benachrichtigungen kommen nicht zurueck. Die App ist eine
     ruhige, lokale Liste, kein Terminplaner.
   - **Ueberschreibt ausdruecklich das UX-Audit:** Dort stehen Faelligkeiten als
     "Produktluecke Nummer 1". Dieser Punkt hat Vorrang. Wer das Audit abarbeitet,
     ueberspringt diesen Befund und baut `due_at` **nicht** ein. Kein Spekulationsraum:
     im Kern-Scope gibt es keine Termine.
   - **Spaeter denkbar, aber nicht jetzt:** als reine Roadmap-Idee in D.3 notiert
     (Anzeige-only, ohne Erinnerungen). Roadmap heisst: nicht Teil des Bauplans, kein
     Schema-Platzhalter, keine Vorbereitung im Code. Erst wenn es einen neuen,
     ausdruecklichen Entscheid gibt.


### A.5 Sprach- und Plattform-Basis

*(Wortgleich hierher umgezogen in Umbau-Etappe 3 aus dem Kopf des UX-Nachtrags vom 2026-06-13. Register: Anhang 1.)*

**Sprach- und Plattform-Entscheidung (verbindlich, 2026-06-13):**
- **UI-Sprache: durchgehend Englisch.** Die frühere Überlegung „Deutsch" wurde
  verworfen. Alle sichtbaren UI-Strings sind englisch; die zuvor gemischten deutschen
  Tooltips wurden am 2026-06-13 angeglichen (`frontend/app.js`, `index.html` jetzt
  `lang="en"`). Code-Kommentare bleiben Deutsch (Entwickler-Sprache), das ist keine UI.
- **Zielplattform: ausschließlich Windows.** In UI und Plan kommen **keine**
  Mac-Tastensymbole (⌘, ⇧) mehr vor; Tastenkürzel werden als `Ctrl`/`Shift` dargestellt.
  B.4, B.5 und B.8 wurden entsprechend bereinigt.


---

## TEIL B: Die Verträge (für alle Bausteine verbindlich)

### B.1 Datenmodell (SQLite)

Drei Tabellen. IDs sind Strings: `'l' + uuid4().hex` für Listen, `'t' + uuid4().hex` für
Aufgaben (verbindlich, so auch im Code). **Keine Zeitstempel-IDs** (kollisionsanfällig).

```sql
-- Liste
CREATE TABLE lists (
  id          TEXT PRIMARY KEY,         -- 'l'+uuid
  name        TEXT NOT NULL,
  position    INTEGER NOT NULL DEFAULT 0,  -- Sortierreihenfolge in der Sidebar
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- Aufgabe
CREATE TABLE tasks (
  id          TEXT PRIMARY KEY,         -- 't'+uuid
  list_id     TEXT NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  done        INTEGER NOT NULL DEFAULT 0,
  position    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- App-Einstellungen als simples Key/Value (Theme, Accent, Dichte, Sidebar …; Keys siehe B.6)
CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

**Abgeleitete Sichten, die das Frontend erwartet** (das Backend liefert sie fertig):
- eine Liste hat `open` = Aufgaben mit `done=0` und `done` = Aufgaben mit `done=1`,
  jeweils nach `position` sortiert.

**Positions-Invariante beim Abhaken (U13-Entscheid 2026-07-15, verbindlich).** `position`
wird **je Sektion** gefuehrt: die Werte sind nur innerhalb derselben `done`-Gruppe einer
Liste vergleichbar (`open` und `done` haben je ihre eigene 0..n-Sequenz). Daraus folgt:
- **Abhaken** (`toggle_task` auf erledigt) haengt die Aufgabe **ans Ende von `done`**:
  neue `position = MAX(position der erledigten Aufgaben dieser Liste) + 1`.
- **Wieder-Oeffnen** haengt sie **ans Ende von `open`**:
  `position = MAX(position der offenen Aufgaben dieser Liste) + 1`.
- **Neue Aufgabe** (`add_task`) landet am Ende von `open` (MAX+1 unter den offenen).
- **`reorder(list_id, ordered_ids)`** vergibt 0..n **innerhalb einer Sektion**. Die
  uebergebenen ids sind dabei nach N11.2.2 (U11) **exakt die Gesamtmenge** der Liste
  (offene und erledigte zusammen); das Backend teilt sie anhand von `done` auf die
  beiden Sektionen auf und nummeriert je Sektion 0..n-1 in der uebergebenen
  Reihenfolge. (Korrigiert 2026-07-17: der fruehere Satz "die uebergebenen ids
  gehoeren alle zur selben done-Gruppe" widersprach N11.2.2 und ist ersetzt.)
- Innerhalb jeder Sektion sortiert das Backend nach `(position, created_at)`; `created_at`
  bricht Gleichstaende.

Der Sinn: Die Reihenfolge ist damit ein fester Vertrag statt eines Nebenprodukts der
Query, das der naechste Refactor stillschweigend kippt (genau die Sorge aus Befund U13).
**Im Code umgesetzt (2026-07-17, mit Phase 7):** `toggle_task` setzt beim Umschalten die
neue `position` ans Ende der Zielsektion, `add_task` zaehlt `MAX(position) + 1` nur
unter `done=0`, `reorder` nummeriert je Sektion 0..n-1 (Mengenpruefung nach N11.2.2),
und der Frontend-Cache haengt eine abgehakte Aufgabe ebenfalls ans Ende von `done`
(push statt unshift). `get_lists` sortierte bereits nach `(position, created_at)` und
teilt nach `done`, es blieb unveraendert.

### B.2 Bridge-API (`pywebview.api.*`): der Vertrag zwischen vorne und hinten

Das ist die **vollständige Methodenliste**, die `backend/api.py` bereitstellt und die
`frontend/app.js` aufruft. Jede gibt JSON-serialisierbare Werte zurück (Promise im JS).

| Methode | Argumente | Rückgabe | Zweck |
|---|---|---|---|
| `get_boot_state()` | (keine) | `{ state:'onboarding'\|'locked'\|'unlocked'\|'vault_error', vault_path:str\|null, reason:str\|null }` | **Die Start-Weiche (N11.8.2, U1-Entscheid; vierter Zustand aus dem U2-Entscheid, N11.15.3).** Der einzige Aufruf, den das Frontend beim Boot macht, bevor es irgendetwas rendert. `onboarding` = kein Tresor da und **`config.json` fehlt ganz** (frischer Rechner, nach Reset, nach Killswitch), `locked` = Tresor da, Passphrase nötig, `unlocked` = Schlüssel im RAM, **`vault_error`** = Konfig oder Tresor da, aber unbrauchbar; `reason` ist dann `config_damaged`, `vault_unreachable` oder `vault_damaged` und führt in den Fehlerbildschirm N6 (N11.15.2/N11.15.3), **nie** stillschweigend ins Onboarding. `vault_path` dient nur der Anzeige (Ort im Lock-Screen/Status), nie als Geheimnis. Gesperrt und im Onboarding erlaubt (G13-Allowlist) |
| `get_state()` | (keine) | `{ lists:[…], settings:{…}, online:bool, locked:bool }` | Initialer Gesamtzustand **nach** dem Entsperren. Gesperrt liefert er nur `{ locked:true }` (G13); den dritten Zustand (`onboarding`) kann er nicht ausdrücken, dafür ist `get_boot_state()` da |
| `get_lists()` | (keine) | `[ { id, name, open:[task], done:[task] } ]` | Alle Listen mit eingebetteten Aufgaben |
| `add_list(name)` | `str` | `{ id, name, … }` | Neue lokale Liste |
| `rename_list(id, name)` | `str,str` | `{ ok:true }` | Liste umbenennen |
| `delete_list(id)` | `str` | `{ ok:true }` | Liste + Aufgaben löschen |
| `undo_delete_list(id)` | `str` | `{ ok:true }` | Letzte Listen-Löschung rückgängig machen (Undo-Toast; ab Phase 7, siehe Phase 6.5) |
| `add_task(list_id, text)` | `str,str` | `{ …task }` | Neue lokale Aufgabe (kein Meta-Feld mehr, N11.1.3) |
| `toggle_task(id)` | `str` | `{ id, done:bool }` | Erledigt-Status umschalten |
| `edit_task(id, fields)` | `str,obj` | `{ …task }` | Aufgaben-Text ändern (nur noch `text`, N11.1.3) |
| `delete_task(id)` | `str` | `{ ok:true }` | Aufgabe löschen |
| `reorder(list_id, ordered_ids)` | `str,[str]` | `{ ok:true }` | Drag-&-Drop-Reihenfolge der Aufgaben speichern |
| `reorder_lists(ordered_ids)` | `[str]` | `{ ok:true }` | Reihenfolge der Listen in der Sidebar speichern (Phase 7, N11.2; Randfaelle nach N11.2.2; im Code umgesetzt 2026-07-17: Drag and Drop der Sidebar-Eintraege) |
| `move_task(id, target_list_id)` | `str,str` | `{ ...task }` | Aufgabe in eine andere Liste verschieben (behaelt `done`, ans Ende ihrer Sektion in der Ziel-Liste; Phase 7, N11.2; Randfaelle nach N11.2.2; im Code umgesetzt 2026-07-17: Drag auf einen Sidebar-Eintrag plus "Move to..."-Kontextmenue per Rechtsklick auf die Karte) |
| `export_list(id, format)` | `str,'md'\|'txt'` | `{ ok:true, filename }` | Eine Liste exportieren (nur noch md/txt, N11.1.5). Zeigt den Save-Dialog im Backend und schreibt die Datei wirklich (G21c); Dialog-Abbruch -> `canceled` (still), zweiter Dialog -> `busy`. (Rückgabe bis 2026-07-17 `{ filename, content }` ohne Datei; mit der G21-Umsetzung ersetzt.) |
| `export_all(format)` | `'md'\|'txt'` | `{ ok:true, filename }` | Alle Listen mit allen Aufgaben in eine Datei exportieren (Schritt "alle Listen" des zweistufigen Exports, N11.2); Sidebar-Reihenfolge, Vorschlag `NoaToDo-Export-YYYY-MM-DD.<format>` (U10); Save-Dialog/`canceled`/`busy` wie `export_list` (im Code umgesetzt 2026-07-17) |
| `copy_task(id)` | `str` | `{ ok, clears_in }` | EINE ausgewählte Aufgabe gehärtet ins Clipboard (Backend-seitig, keine Win+V-History, kein Cloud-Clipboard, Auto-Clear nach 60 s; ersetzt das frühere `copy_list`, ganze Listen kopiert man bewusst nicht mehr, dafür gibt es den Export) |
| `copy_errors()` | (keine) | `{ ok, clears_in }` | Kopiert den redigierten G29-Fehler-Ringpuffer als Text über denselben gehärteten G23-Clipboard-Pfad wie `copy_task` (Kopier-Knopf der "Recent errors"-Sektion im Status-Modal, N11.12.1; der Puffer ist bereits redigiert, `<path>` statt Pfaden, keine Bridge-Argumente; ergänzt 2026-07-17 mit der G29-Umsetzung) |
| `set_setting(key, value)` | `str,*` | `{ ok:true }` | Eine Einstellung speichern |
| `get_status()` | (keine) | `{ db, encryption, runtime }` | Daten für das „App status"-Modal |
| `set_online(flag)` | `bool` | `{ online:bool, partial:bool }` | Schaltet den **echten** Windows-Flugmodus um (offline = alle Funkgeräte aus, WLAN/Bluetooth); **antwortet erst nach Abschluss mit dem verifizierten realen Zustand** (`partial:true`, wenn ein Radio nicht gehorcht; beim Offline-Schalten gilt `online:true`, sobald noch irgendein Radio an ist, U15). Spiegelt externe Änderungen und stellt beim Beenden den Ausgangszustand als letzten Schritt wieder her (N11.5) |
| `activity_ping()` | (keine) | `{ ok:true }` | Meldet Nutzer-Eingabe im App-Fenster und setzt den Auto-Sperr-Timer zurück (N11.4.2). Vom Frontend **gedrosselt** (führende Flanke, danach höchstens alle 30 s). Setzt **nur** `last_activity` auf die monotone Backend-Uhr, nimmt keinen Zeitwert entgegen und kann den Timer nicht abschalten. **Nicht** in `ALLOWED_WHEN_LOCKED`: gesperrt liefert sie `locked` und rührt den Timer nicht an (G13). Kein anderer Bridge-Aufruf zählt als Aktivität |
| `choose_vault_dir()` | (keine) | `{ path:str, has_vault:bool }` oder `{ error:'canceled' }` | Onboarding-Schritt 1: öffnet den **nativen Ordner-Dialog** im Backend (`create_file_dialog`, FOLDER_DIALOG) und gibt den gewählten Ordner zurück. Prüft Schreibbarkeit und warnt bei Cloud-Sync-Pfaden (OneDrive/Dropbox, G32). **Liegt im gewählten Ordner schon eine `tasks.db.enc`, meldet er `has_vault:true`; das Onboarding bietet dann NICHT „neuen Tresor anlegen" an, sondern nur „diesen Tresor öffnen" (Pfad in `config.json` schreiben, dann Lock-Screen), damit ein bestehender Tresor nie überschrieben wird (N11.15.6).** Legt **nichts** an. Im Onboarding erlaubt |
| `create_vault(path, passphrase)` | `str,str` | `{ ok:true }` | Onboarding-Schritt 2: legt den leeren Tresor an: Passphrase prüfen (**nur** Mindestlänge 12, N11.3, sonst `invalid`), 32-Byte-Pepper erzeugen und im Credential Manager ablegen (G18), Salt + Argon2-Parameter erzeugen, Schlüssel ableiten (G15), leere DB anlegen (nur Default-Settings, keine Demo-Daten, N11.1.4), als `tasks.db.enc` unter `path` schreiben (G16, atomar über `.tmp` + `os.replace`) und den Pfad in `config.json` speichern. **Bricht mit `invalid` ab, falls unter `path` schon eine `tasks.db.enc` liegt: ein bestehender Tresor wird NIE überschrieben (Datenverlust-Schutz, N11.15.6). Diesen Fall fängt regulär schon `choose_vault_dir()` ab (`has_vault:true`); der Backend-Riegel ist die letzte Sicherung gegen einen Aufruf an der UI vorbei.** Danach ist die App **entsperrt**. Im Onboarding erlaubt |
| `change_passphrase(old, new)` | `str,str` | `{ ok:true }` | Passphrase in den Einstellungen ändern (N11.3). Falsches `old` → `passphrase` (Rate-Limit wie beim Entsperren, N11.4), zu kurzes `new` → `invalid`. Der Tresor wird mit **frischem Salt und frischer Nonce** neu verpackt; der Pepper bleibt (er ist konto-, nicht passphrase-gebunden). **Nur entsperrt aufrufbar.** Die `.bak`-Generation (sie trägt sonst weiter den mit der alten Passphrase lesbaren Stand) wird im selben Zug mit dem **neuen** Schlüssel neu geschrieben oder über den Secure-Delete-Pfad entfernt; nach dem Wechsel ist keine Datei mehr mit der alten Passphrase lesbar, und die Argon2-Parameter werden auf den G8-Soll-Stand gehoben (Befund U8, entschieden 2026-07-13; die vier Details a bis d stehen im N11.3-Abschnitt unten in B.2) |
| `reset_vault()` | (keine) | `{ ok:true }` | **Reset vom Lock-Screen** (N11.3): der Ausweg für die vergessene Passphrase. Läuft die gemeinsame Sequenz mit `reason='reset'` (N11.11): Tresor-Datei samt `.bak`, Vault-Metadaten und der DPAPI-Pepper werden gelöscht, danach startet das Onboarding neu (Ort wählen, neue Passphrase, frischer Pepper). **Wischt alle Daten unwiderruflich** und ist deshalb im UI wie der Killswitch abgesichert (Bestätigung, dann `RESET` tippen). Gesperrt erlaubt (G13-Allowlist), braucht keine Schlüssel |
| `lock()` | (keine) | `{ locked:true }` | App sperren; seit 2026-07-08 verstärkt: erst Raum-Bereinigung wie bei Panik (Ansicht leeren; seit N11.10 OHNE offline zu schalten), dann Lock-Screen, nichts wird gelöscht (siehe B.8.2; Etiketten N10, N11.10) |
| `unlock(passphrase)` | `str` | `{ ok:bool }` | Entsperren; danach wird der Zustand frisch per `get_state()` geladen (der Raum war geleert) |
| `panic()` | (keine) | `{ locked:true }` | Emergency: Raum bereinigen + offline; der Flow endet im Endschirm mit Finish/Killswitch, zurück in die App führt kein Weg (N10) |
| `quit_app()` | (keine) | `{ ok:true }` | App sauber beenden (Off-Knopf des Lock-Screens, „Finish" im Panik-Endschirm, Abschluss des Killswitch); Phase 8: auf diesem Pfad vorher Spuren sicher wischen (G14/G25) |
| `killswitch()` | (keine) | `{ ok:true }` | Unwiderruflich alle Nutzerdaten aus der Datenbank löschen (nur vom Panik-Endschirm aus erreichbar, N10); das Programm selbst bleibt installiert |

**Ereignisse Backend → Frontend** (PyWebView kann JS auswärts aufrufen, z.B.
`window.evaluate_js` oder ein Event-Bus): `on_locked()`.
Das Frontend registriert dafür globale Funktionen wie `window.noa.onLocked`.

**Fehlerkonvention (verbindlich, Fassung nach N11.12 / Gate G29):** Jede Methode kann statt
des Erfolgsobjekts `{ error: "code", message: "…", ref: "…" }` liefern.

- `code` ist **immer** einer der Codes aus der Tabelle unten, nie ein freier Text.
- `message` ist ein **statischer, generischer** Satz aus dieser Tabelle. Es wird
  **nie** `str(exc)` ans Frontend gegeben (eine banale `OSError` trägt sonst
  absolute Pfade samt Windows-Benutzernamen ins UI und bei Screen-Sharing auf fremde
  Bildschirme). Verboten sind auch Tracebacks, SQL-Fragmente, Datei-Pfade,
  Aufgaben-/Listentexte, Passphrase und Schlüssel.
- `ref` ist eine kurze Referenz (z.B. `E4F1`) auf den **In-Memory-Ringpuffer**
  (N11.12.1). Nur dort liegen die technischen Details, einsehbar im Status-Modal.
  `ref` wird ausschliesslich bei `internal` gesetzt.

**Fehlercode-Katalog (kanonisch, einzige Wahrheit; jeder neue Code wird hier ergänzt):**

| Code | Bedeutung | `message` (statisch) | Frontend-Verhalten |
|---|---|---|---|
| `not_found` | Unbekannte ID (Liste/Aufgabe existiert nicht mehr) | „Item not found." | **kein Toast** (N11.16), nur still `get_state()` neu laden (die Ansicht war veraltet) |
| `invalid` | Argument verletzt die Validierung aus G20 (falscher Typ, unbekannter Settings-Key, unbrauchbare ID) | „Invalid input." | **kein Toast** (N11.16); die Eingabe bleibt stehen, damit sie korrigiert werden kann |
| `locked` | App ist gesperrt, Methode steht nicht in `ALLOWED_WHEN_LOCKED` (G13) | „App is locked." | **stumm** (kein Toast): Frontend zeigt den Lock-Screen. Der Code ist im Normalbetrieb ein Renn-Fall (z.B. Auto-Lock während einer laufenden Aktion) und keine Nutzer-Fehlermeldung |
| `passphrase` | `unlock()`: falsche Passphrase (AEAD-Tag schlägt fehl, G15) | „Wrong passphrase." | **kein Toast**, sondern die Fehleranzeige im Lock-Screen (N4/N6), plus Rate-Limit-Ladder aus B.8.4 (N11.4) |
| `rate_limited` | `unlock()`: Sperrzeit der Ladder läuft noch; zusätzliches Feld `retry_in` (Sekunden) | „Too many attempts." | **kein Toast**, sondern Countdown im Lock-Screen; Eingabefeld deaktiviert |
| `vault` | Tresor-Datei fehlt, ist beschädigt oder der Pepper aus dem Credential Manager ist weg (Windows-Konto verloren, N11.3) | „Vault cannot be opened." | **kein Toast**, sondern der Boot-/Entsperr-Fehlerbildschirm (N6) mit den Auswegen Wiederholen und Reset |
| `canceled` | Nutzer hat einen nativen Dialog abgebrochen (Save-Dialog des Exports) | „Canceled." | **stumm** (kein Toast, kein Fehlerbild): ein Abbruch ist kein Fehler |
| `busy` | Es ist bereits ein **nativer Dialog offen** (Export-Save, Onboarding-Ordnerwahl); ein zweiter wird abgelehnt (N11.11.5) | „A dialog is already open." | **kein Toast** (N11.16); kein Zustandswechsel. Tritt im Normalbetrieb nicht auf (der Dialog ist modal), fängt aber Doppelklick-Renner und Bridge-Aufrufe an der UI vorbei ab |
| `memory` | `unlock()`/`create_vault()`/`change_passphrase()`: die Argon2id-Allokation scheiterte (`MemoryError`), die Maschine hat gerade zu wenig freien RAM. **Kein** falsches Passwort, **keine** Beschädigung (N11.4.3) | „Not enough memory. Close other apps and try again." | **kein Toast**, sondern inline im jeweiligen Auth-Screen (Lock-Screen bzw. Onboarding/Passphrase ändern), mit Wiederholen; **kein** Shake, **kein** Reset-Angebot, **kein** Countdown, und die Rate-Limit-Ladder wird **nicht** vorangetrieben |
| `internal` | Alles Unerwartete (letzte Auffanglinie im `@bridge`-Decorator) | „Something went wrong." | **kein Toast** (N11.16); der Fehler (mit `ref`) bleibt nur über das Status-Modal (G29-Ringpuffer „Recent errors") einsehbar |

Diese Tabelle ist die einzige Wahrheit für Fehlercodes. Wer einen Code hinzufügt,
ergänzt ihn hier **und** in der Frontend-Behandlung; ein Code ohne Zeile in dieser
Tabelle darf nicht ans Frontend gehen. Ringpuffer und Logging-Politik: siehe den
Abschnitt „Fehler-Hygiene, Fehlercode-Katalog und Logging-Politik" (Etikett N11.12)
unten in B.2.

**Toast-Politik auf einen Blick (löst U23; seit N11.16, 2026-07-17, verschärft, Nutzerwunsch:
keine Benachrichtigungen):** **Kein** Fehlercode erzeugt mehr einen Toast. `not_found` lädt
die veraltete Ansicht **still** neu, `locked` zeigt den Lock-Screen, `invalid`/`busy`/`canceled`
sind **stumm**, `internal` bleibt nur über das Status-Modal (G29-Ringpuffer „Recent errors",
mit `ref`) einsehbar, und die Entsperr-Fehler `passphrase`/`rate_limited`/`vault`/`memory` haben
ihre **eigene Darstellung im Lock-/Fehlerbildschirm** (N4/N6). Der **einzige** verbliebene Toast
in der ganzen App ist der **Undo-Toast** beim Listen-Löschen (N11.2.1). Der frühere Zustand
(Toast bei `not_found`/`invalid`/`busy`/`internal`) ist damit überholt.
**„Kein Tresor" ist kein Fehlercode:** es gibt kein `no_vault`; der Fall ist der
Onboarding-**Boot-Zustand** aus `get_boot_state()` (N11.8.2, U7) und damit ebenfalls
toastfrei. Ein fehlender oder beschädigter Tresor **zur Laufzeit** ist dagegen `vault`
(Fehlerbildschirm N6).

#### Serverseitige Lock-Durchsetzung (als Allowlist) (Etikett G13) [Sec]

*(Wortgleich hierher gezogen in Umbau-Etappe 6 aus der G13-Zeile der B.9-Gate-Tabelle; Status, Stand und Pruefweg des Gates stehen weiter in B.9.)*

**Serverseitige Lock-Durchsetzung (als Allowlist).** Die Sperre existiert heute nur als
Frontend-Overlay: Im Audit wurde nachgewiesen, dass nach `lock()` Aufrufe wie `add_task()` und
`get_state()` weiterhin funktionieren und alle Daten liefern (ein einziger JS-Aufruf umgeht den
Lock-Screen). Pflicht: Ein zentraler Check im `bridge`-Decorator prüft `self.locked` und
arbeitet gegen eine **explizite Allowlist**, nicht gegen eine Ausnahmenliste:
`ALLOWED_WHEN_LOCKED = {"unlock", "quit_app", "killswitch", "get_state", "get_boot_state",
"choose_vault_dir", "create_vault", "reset_vault"}` (die letzten vier ergänzt mit dem
U1-Entscheid 2026-07-13, N11.13: Onboarding und Reset laufen gerade **ohne** Schlüssel und wären
sonst blockiert). Jede Methode, die **nicht** in dieser Menge steht, gibt gesperrt sofort
`{"error": "locked"}` zurück, ohne die DB zu berühren. Das gilt ausdrücklich auch für `lock()`
und `panic()` (gesperrt ohnehin sinnlos) und für jede künftig ergänzte Bridge-Methode: **neue
Methoden sind per Default gesperrt** und müssen bewusst in die Allowlist aufgenommen werden (die
Formulierung „jede ausser X" driftete in der Vergangenheit auseinander, siehe Plananalyse
W4/V4). Zu den erlaubten Methoden: `get_state()` liefert gesperrt nur `{"locked": true}` ohne
Listen/Settings; `get_boot_state()` liefert nur den dreiwertigen Zustand plus den Vault-Pfad
(kein Geheimnis, N11.13); `quit_app()` (Off-Knopf im Lock-Screen) und `killswitch()`
(Panik-Endschirm) sind bewusste Ausnahmen aus N10, weil beide nie Daten preisgeben und gerade
**ohne** Passphrase funktionieren müssen; `choose_vault_dir()`/`create_vault()` sind der
Onboarding-Weg (es gibt noch keinen Tresor, also nichts preiszugeben) und `reset_vault()` der
Weg der vergessenen Passphrase (löscht nur, gibt nie Daten heraus, doppelt bestätigt, N11.13);
`unlock(passphrase)` ist der einzige Weg zurück in die Daten. **Ausdrücklich NICHT in der
Allowlist:** `change_passphrase()` (braucht die Schlüssel, also den entsperrten Zustand). Dieser
Abschnitt ist die normative Fassung von G13 (Regel im B.9-Kopf: Phasen und Schnellübersicht
führen nur noch die Nummer).

#### Entsperr-Fehlerlogik von `unlock()` (Etikett N6, U7-Entscheid 2026-07-15) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N6. Phase 8: Entsperr-/Boot-Fehlerbildschirm (UX 6.3)“; der Screen-Teil von N6 steht in B.4. Register: Anhang 1.)*

**Entscheidbare Fehlerlogik beim Entsperren (verbindlich, löst Plananalyse U7;
entschieden 2026-07-15, im Zweifel pro Sicherheit).** Der AEAD-Tag allein kann „falsche
Passphrase" und „manipulierte Datei" nicht trennen. Deshalb wird die Fehlerquelle **vor**
der teuren Ableitung anhand des unverschlüsselten Container-Kopfs entschieden, in genau
dieser Reihenfolge:
1. **Datei fehlt am Entsperr-Pfad** (der Pfad aus `config.json` zeigt auf keine
   `tasks.db.enc`): Rückgabe `vault`. **Kein** stilles Umschalten auf Onboarding.
   Onboarding entscheidet ausschliesslich `get_boot_state()` beim Start (N11.8.2);
   verschwindet die Datei zur Laufzeit, ist das ein Fehler (Fehlerbildschirm mit
   Wiederholen und Reset), kein Freibrief, einen neuen Tresor anzulegen. Sicherheitsgrund:
   sonst könnte das blosse Löschen der Datei den „neuen Tresor"-Weg erzwingen und den
   alten Zustand verschleiern.
2. **Kopf unlesbar** (Magic falsch, unbekannte Version, Länge/Struktur unplausibel,
   Salt / Argon2-Parameter / Nonce fehlen oder sind fehlerhaft): Rückgabe `vault`,
   Fehlerbildschirm „Vault cannot be opened" mit `.bak`-Angebot. Diese Prüfung liest
   **nur** den bauartbedingt nicht geheimen Container-Kopf (Magic, Version, Salt,
   KDF-Parameter, Nonce), nie Schlüsselmaterial, und läuft **ohne** Passphrase und
   **ohne** Argon2.
3. **Kopf lesbar, aber der AEAD-Tag schlägt fehl:** Rückgabe `passphrase`
   („Wrong passphrase"). Nur dieser Fall ist ein Rateversuch.

**Rückgabeformat: die kanonischen B.2-Codes, kein paralleles `reason`-Feld.** Der
U7-Vorschlag `{ok:false, reason:'wrong_pass'|'locked_out'|'file_damaged'|'no_vault'}`
wird **nicht** übernommen; er dupliziert die einzige Wahrheit aus B.2 und verletzt G29.
Verbindliche Abbildung: falsche Passphrase -> `passphrase`; laufende Ladder ->
`rate_limited` mit `retry_in`; fehlende oder beschädigte Datei bzw. fehlender Pepper ->
`vault`; „kein Tresor" ist **kein** `unlock`-Ergebnis, sondern ein Boot-Zustand.
`unlock()` liefert bei Erfolg `{ ok:true }`, sonst `{ error:<code>, retry_in?:<s> }`.

**Sicherheitsregeln (im Zweifel pro Sicherheit):**
- **Nur `passphrase` treibt die Rate-Limit-Ladder (N11.4) voran.** Ein `vault`-Ergebnis
  ist kein Rateversuch und erhöht `fails`/`stage` nicht (bei kaputtem Kopf läuft die
  AEAD-Prüfung gar nicht, es wird nichts geraten). So kann ein manipulierter Kopf die
  Ladder weder zurücksetzen noch umgehen.
- **Jede `passphrase`-Antwort trägt `retry_in: 2`** (die 2-s-Wartezeit aus N11.4); sind
  die 3 Freiversuche verbraucht, werden weitere Versuche zu `rate_limited` mit der
  Ladder-Dauer. Die Anzeige zeigt in beiden Fällen denselben Countdown.
- **Die Meldung bleibt neutral (N4):** „Wrong passphrase" gibt nicht preis, wie nah die
  Eingabe war; der Fehlerbildschirm gibt nicht preis, ob ein Tresor existiert (auf dem
  Lock-Screen existiert er ohnehin).
- **`.bak`-Wiederherstellung ist ein vollwertiger Entsperr-Versuch:** sie tauscht den
  Container gegen die `.bak`-Generation (Gate G16) und ruft dieselbe Logik erneut auf,
  **unter derselben Ladder** (kein Rate-Limit-Bypass). Die aktuelle (womöglich
  beschädigte) Primärdatei wird dabei **erst überschrieben, wenn die `.bak` erfolgreich
  entsperrt**, nie vorher, sonst zerstört ein Fehlversuch gegen `.bak` die letzte
  vorhandene Datei.

**Sekundärhinweis „vielleicht beschädigt" nach Schwelle.** Weil eine falsche Passphrase
(Fall 3) und ein subtil manipulierter Inhalt (Kopf intakt, Body verfälscht) beide als
`passphrase` erscheinen, blendet der Lock-Screen nach `DAMAGE_HINT_AFTER = 5`
aufeinanderfolgenden `passphrase`-Ergebnissen zusätzlich den unaufdringlichen Hinweis ein:
„Or the file may be damaged. Try a backup?" mit Verweis auf die `.bak`-Wiederherstellung.
Der Hinweis ist rein informativ, ändert die neutrale Hauptmeldung nicht und schaltet
keinen Weg an der Ladder vorbei.

#### Undo beim Listen-Loeschen: die verbindliche Architektur (Etikett N11.2.1, U9-Entscheid 2026-07-13)

*(Wortgleich umgezogen in Umbau-Etappe 3. Register: Anhang 1.)*

**Die Ratestelle:** Der fruehere Plantext bot zwei Architekturen mit "oder" an ("im RAM des
Backends **oder** als `deleted_at`-Soft-Delete"). Das war eine echte Ratestelle, dazu vier
offene Detailfragen (wie viele Loeschungen gehalten, Wiederherstellung an welcher Position,
wem gehoert der 6-s-Timer, was passiert beim Sperren/Beenden).

**Entscheidung (verbindlich, Security first):**

- **Genau RAM, kein Soft-Delete.** Die "oder Soft-Delete"-Variante ist **gestrichen**. B.1
  bekommt **kein** `deleted_at`-Feld: ein solches Feld waere ein Schema-Eingriff, der **jede**
  Abfrage in `db.py` mit einem `WHERE deleted_at IS NULL` belasten wuerde (eine vergessene
  Stelle zeigt geloeschte Daten wieder an), und es wuerde geloeschten Aufgabentext dauerhaft im
  Tresor liegen lassen, obwohl der Nutzer ihn geloescht hat. Der RAM-Puffer haelt geloeschte
  Daten nur, solange die Sitzung entsperrt laeuft, genau wie alle anderen Aufgabendaten auch.
- **Genau eine Loeschung.** Das Backend haelt **die letzte** geloeschte Liste samt allen ihren
  Aufgaben (mit deren Text, `done`-Status und `position`) in **einem** In-RAM-Puffer. Kein
  Stapel, keine Historie. Eine neue Loeschung **ueberschreibt** den Puffer und verwirft die
  vorher gepufferte Liste endgueltig.
- **Wiederherstellung an der alten Stelle.** `undo_delete_list(id)` fuegt die Liste an ihrer
  gemerkten `position` wieder ein (nachfolgende Listen ruecken zurueck) und stellt die Aufgaben
  mit ihren alten Positionen wieder her. Die IDs bleiben dieselben. Stimmt `id` **nicht** mit
  der aktuell gepufferten Liste ueberein (der Puffer wurde inzwischen durch eine neue Loeschung
  ersetzt oder ist verfallen), liefert die Methode `not_found`, und das Frontend laedt still
  per `get_state()` neu; sie legt **nie** eine zweite Kopie an.
- **Der Timer gehoert der UI, nicht dem Puffer.** Der 6-s-Toast "List deleted" mit "Undo" ist
  **reine Frontend-Anzeige**. Der Backend-Puffer hat **keinen** eigenen Verfalls-Timer: er lebt,
  bis er ueberschrieben (naechste Loeschung) oder verworfen wird (siehe naechster Punkt). Ein
  **spaetes Undo** nach dem Verschwinden des Toasts darf deshalb gelingen, solange der Puffer
  noch lebt; das ist gewollt und kein Fehler.
- **Verfall beim Sperren/Beenden (sicherheitsrelevant).** Der Puffer ist fluechtiger
  Sitzungs-RAM und wird bei **jedem** Austritt aus dem entsperrten Zustand verworfen: Lock,
  Auto-Lock, Panik, Killswitch, Reset, Quit und App-Ende. Umgesetzt in der einen
  `teardown(reason)`-Sequenz (N11.11.2 in B.8.5, Schritt 7, zusammen mit dem Schluessel-Nullen), damit
  eine **gesperrte** App **nie** geloeschten Aufgabentext im RAM haelt. Ein Undo im gesperrten
  Zustand gibt es nicht: `undo_delete_list` steht **nicht** in der G13-Allowlist und liefert
  gesperrt `locked`.

#### Randfaelle von `reorder`/`reorder_lists`/`move_task` (Etikett N11.2.2, U11-Entscheid 2026-07-15) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3; die Validierung faellt unter G20. Register: Anhang 1.)*

*Loest U11 der Plananalyse: Es war offen, was bei unvollstaendigen `ordered_ids`, fremden
IDs oder Duplikaten passiert, wie die `position` vergeben wird und ob eine verschobene
erledigte Aufgabe ihren `done`-Status behaelt. Im Zweifel gilt "alles oder nichts" und die
konsistente Neunummerierung; die Validierung faellt unter G20.*

- **`reorder(list_id, ordered_ids)`:** `ordered_ids` muss **exakt** die Menge **aller**
  Aufgaben-IDs dieser Liste sein, offene **und** erledigte zusammen (die Sektionstrennung
  macht das Frontend beim Rendern anhand von `done`, nicht die Reihenfolge). Als Menge
  gleich: keine fehlende, keine doppelte, keine fremde oder listenfremde ID, ein echtes
  Array von Strings. **Jede** Abweichung -> `{"error":"invalid"}`, und es wird **nichts**
  geschrieben (kein Teil-Reorder, keine "besten Bemuehungen"). Bei gueltiger Eingabe
  vergibt das Backend `position` **neu als 0..n-1** in der uebergebenen Reihenfolge.
- **`reorder_lists(ordered_ids)`:** dieselbe Regel auf die Listenmenge angewandt: exakt
  alle Listen-IDs, sonst `invalid`; Neunummerierung 0..n-1.
- **`move_task(id, target_list_id)`:** beide IDs werden geprueft. Fehlt die Aufgabe oder
  die Zielliste -> `not_found`; ist `target_list_id` die aktuelle Liste der Aufgabe (oder
  kein String) -> `invalid`. Die Aufgabe **behaelt ihren `done`-Status** und wird **ans
  Ende ihrer Sektion in der Zielliste** gehaengt: sie bekommt die hoechste `position` der
  Zielliste, und weil das Frontend je Sektion nach `position` sortiert, landet eine
  erledigte am Ende der Erledigt-, eine offene am Ende der offenen Aufgaben. Danach werden
  **Quell- und Zielliste** konsistent 0..n-1 durchnummeriert.
- Alle drei sind rein lokal, loesen keine weitere Aktion aus und werden gegen
  Nicht-Array-/Nicht-String-Eingaben gehaertet (G20).

#### Regel-4-Validierung auch für LOKALE Eingaben + Typ-/Key-Prüfung an der Bridge (Etikett G20) [Sec]

*(Wortgleich hierher gezogen in Umbau-Etappe 6 aus der G20-Zeile der B.9-Gate-Tabelle; Status, Stand und Pruefweg des Gates stehen weiter in B.9.)*

**Regel-4-Validierung auch für LOKALE Eingaben + Typ-/Key-Prüfung an der Bridge.**
Audit-Befunde: ein 1-MB-Tasktext und Steuerzeichen wie U+0000 werden heute anstandslos
gespeichert; `reorder(list_id, "string")` iteriert den String zeichenweise und liefert `{"ok":
true}`; `set_setting` akzeptiert beliebige Keys. Pflicht in `api.py`: (a)
`add_task`/`edit_task`: Text max. 4096 Zeichen (kein `meta` mehr, N11.1.3);
`add_list`/`rename_list`: Name max. 256; Überlänge abschneiden; Steuerzeichen U+0000-U+001F
(ausser `\n` und `\t`) vor dem Schreiben strippen. (b) `reorder`/`reorder_lists` lehnen ab, wenn
`ordered_ids` keine Liste von Strings ist; `move_task` validiert die IDs. (c) `set_setting`
akzeptiert nur Keys aus einer Whitelist (`accent`, `theme`, `density`, `sidebar`, `railPinned`,
`sidebarWidth`, `sound`, `autoLock`, `exportDone` plus künftig dort dokumentierte, N11.7), sonst `{"error":
"invalid"}`. (d) **Werte und Typen prüfen, nicht nur Keys und Längen (V5, 2026-07-15):**
`set_setting` validiert auch den **Wert** je Key: `theme` gegen `auto|light|dark`,
`density`/`sidebar` gegen ihre Enum-Werte, `accent` gegen die feste Preset-Whitelist (die sechs
Hex-Werte aus B.3/B.6; der Wert landet als CSS-Variable im DOM, mit der Whitelist ist
CSS-Injection über Settings komplett tot), `sidebarWidth` wird schon beim **Schreiben** auf
180-520 geklemmt (nicht erst beim Lesen geparst), `sound` bool, `autoLock` ganzzahlig aus {0, 1,
5, 15, 30, 60}, `exportDone` bool; `edit_task.fields` wird typgeprüft (nur bekannte Felder, `text` String, `done`
bool). Bevorzugte Umsetzung: ein kleines **deklaratives Schema pro Bridge-Methode am
`@bridge`-Decorator**, das Phase 9 direkt gegen die Regeln testen kann.

#### Ersteinrichtung, Passphrase-Politik und Reset (Etikett N11.3, U8-Entscheid 2026-07-13)

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.3 Phase 8: Ersteinrichtung, Passphrase, Reset“. Die Onboarding-Screens stehen in B.4, der KDF-Upgrade-Bezug in B.7/G8. Register: Anhang 1.)*

- **Keine Bestandsdaten-Uebernahme.** Beim Umstieg auf die echte Verschluesselung wird
  die alte Dev-DB verworfen; der neue Tresor startet leer. Keine Migration.
  **Wie** verworfen wird, regelt seit dem A3-Entscheid (2026-07-15) Gate G33 (normative
  Zeile in B.9): `tasks.db` samt `-journal`/`-wal`/`-shm` wird beim ersten
  `create_vault()` ueber den Secure-Delete-Pfad entsorgt (bestmoeglich ueberschreiben,
  dann entlinken; derselbe Pfad wie beim `.bak`-Wegraeumen unter (c) unten), nie per
  blankem `os.remove`; dazu ein Einmal-Hinweis an den Nutzer mit der ehrlichen
  SSD-Restgrenze (Wear-Leveling; wer Dev-Reste ausschliessen muss, braucht ein
  vollverschluesseltes System, G31/B.10.4).
- **Tresor-Ort beim ersten Start waehlbar.** Der Nutzer legt den Speicherort von
  `tasks.db.enc` bei der Einrichtung fest. Der Pfad kann nicht im Tresor stehen
  (Henne-Ei-Problem), daher liegt er in einer kleinen **unverschluesselten Konfig**
  (z.B. `%LOCALAPPDATA%\NoaToDo\config.json`), die nur diesen Pfad und nicht-geheime
  Startinfos enthaelt, nie Aufgabendaten.
- **Passphrase-Regel: ausschliesslich Mindestlaenge 12 Zeichen. Sonst nichts.** Die
  einzige Pruefung beim Einrichten und beim Passphrase-Wechsel ist
  `len(passphrase) >= 12`. Ausdruecklich **nicht** gebaut werden:
  - kein Staerkemesser und keine Staerke-Anzeige (auch keine rein informative Balken-
    oder Ampel-Anzeige, auch nicht "nur als Hinweis"),
  - keine Zeichenklassen-Regeln (keine Pflicht zu Gross-/Kleinbuchstaben, Ziffern,
    Sonderzeichen),
  - keine Woerterbuch-, Blacklist- oder zxcvbn-artige Pruefung,
  - keine Obergrenze ausser einer technischen Laengenschranke.

  Gate G8 bleibt fuer die **Argon2id-Kosten** gueltig; die dort urspruenglich genannte
  "erzwungene Passphrase-Staerke (Staerke-Anzeige beim Einrichten)" ist hiermit
  **gestrichen**, nicht nur konkretisiert. Wer die Gate-Liste als Checkliste abarbeitet:
  G8 ist erfuellt, sobald die Argon2id-Parameter stimmen und die Laengenpruefung
  greift. Ein Staerkemesser waere ein Regelverstoss, kein Bonus.

  **Ehrliche Konsequenz (bewusst akzeptiert):** `aaaaaaaaaaaa` ist eine gueltige
  Passphrase. Waehlt der Nutzer so etwas, verteidigen nur noch die hohen
  Argon2id-Kosten (jeder Rateversuch kostet Speicher und Zeit) und der DPAPI-Pepper
  (ohne das Windows-Konto ist die gestohlene Datei auch mit korrekt geratener
  Passphrase nicht zu oeffnen). Das ist eine bewusste Komfort-Entscheidung des
  Nutzers gegen Gaengelung, kein uebersehener Mangel. Die deutliche Verlust-Warnung
  unten bleibt der einzige erzieherische Text im Flow.
- **Deutliche Verlust-Warnung bei der Einrichtung.** Klarer Hinweis, dass eine
  vergessene Passphrase **nicht** wiederherstellbar ist und der einzige Ausweg der
  Reset (mit Datenverlust) ist; der Nutzer muss das aktiv bestaetigen.
- **Kein Pepper-Recovery-Export.** Ueberschreibt Gate G18: Der DPAPI-Pepper bleibt als
  Zweitfaktor (Schutz der gestohlenen Datei), aber es gibt **keinen** Recovery-Export.
  Bewusst akzeptierte Folge: Der Tresor ist an diesen Windows-PC/dieses Konto gebunden;
  ohne dieses Konto ist er auch mit korrekter Passphrase nicht mehr zu oeffnen. Der
  Einrichtungs-Flow enthaelt also **keinen** Recovery-Schritt mehr.
- **Passphrase vergessen: Reset-Weg.** Kein Recovery, aber ein Reset auf dem Lock-Screen
  loescht den Tresor unwiderruflich und startet neu. Ablauf: erst der **gleiche
  zweistufige, bewusst umstaendliche Bestaetigungs-Mechanismus wie der Panik-Killswitch**
  (Kippschalter, "OK"), danach muss der Nutzer das Wort **"RESET"** abtippen. Danach
  verhaelt sich die App wie ein echter Erststart: **Speicherort neu abfragen UND neue
  Passphrase** festlegen.
- **Passphrase aenderbar** in den Einstellungen (alte Passphrase eingeben, neue mit
  min. 12 Zeichen setzen; nur im entsperrten Zustand, ueber `change_passphrase(old, new)`,
  N11.12). Der Tresor wird mit dem neuen Schluessel neu verpackt, verbindlich mit
  diesen vier Details (Entscheid 2026-07-13, loest Plananalyse U8):
  - **(a) Frisches Salt, frische Nonce (Pflicht).** Der Wechsel erzeugt ein neues,
    zufaelliges Argon2-Salt; die frische Nonce liefert ohnehin jedes Verschluesseln
    (G16). Vom alten Schluesselmaterial wird nichts weiterverwendet.
  - **(b) Der DPAPI-Pepper bleibt.** Er ist konto-gebunden, nicht passphrase-gebunden
    (G18), und wird beim Wechsel **nicht** rotiert. Einen neuen Pepper gibt es nur
    ueber Reset bzw. Tresor-Neuanlage.
  - **(c) Die `.bak`-Generation wird sofort mitgezogen (sicherheitsrelevant).** Die
    G16-Rotation wuerde beim Neuverpacken ausgerechnet den **alten** Stand (mit der
    alten Passphrase lesbar) als `tasks.db.enc.bak` liegen lassen. Deshalb: im selben
    Zug wie das neue `tasks.db.enc` wird die `.bak`-Generation mit dem **neuen**
    Schluessel neu geschrieben (bevorzugt, so bleibt die G16-Absturzsicherung erhalten)
    oder, falls nicht neu geschrieben, geloescht; nach Abschluss des Wechsels darf keine
    Datei mehr existieren, die mit der alten Passphrase entschluesselbar ist. Wer
    wegen einer kompromittierten Passphrase wechselt, waere sonst genau ueber `.bak`
    weiter angreifbar. **Das Wegraeumen des alten Stands laeuft ueber denselben
    Secure-Delete-Pfad wie der uebrige Tresor-Abbau (ueberschreiben, dann entlinken),
    nicht ueber ein blankes `os.remove`**, sonst blieben die alt-lesbaren Chiffrat-Bytes
    in freigegebenen Sektoren rekonstruierbar. Ehrliche Restgrenze (gehoert ins
    Bedrohungsmodell): auf SSDs mit Wear-Leveling ist auch das Ueberschreiben nicht
    garantiert; die letzte Deckung des rekonstruierten `.bak` bleibt dann der
    DPAPI-Pepper (ohne das Windows-Konto ist auch der alte Stand nicht zu oeffnen).
    Pruefweg: fester Phase-9-Testfall (siehe Phase 9, Krypto-Tests).
  - **(d) KDF-Upgrade-Pfad.** Beim Wechsel werden die Argon2id-Parameter auf den
    aktuellen Soll-Stand aus G8 gehoben (im `.enc`-Header koennen aeltere Werte
    stehen). Der Passphrase-Wechsel ist damit zugleich der definierte Weg, veraltete
    KDF-Kosten anzuheben; einen separaten Migrationsmechanismus gibt es nicht.

#### Echter Flugmodus: `set_online` und `get_wifi_signal` (Etikett N11.5, U14-/U15-Entscheide 2026-07-15)

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.5 Echter Flugmodus statt Deko-Schalter“. Die Abhaengigkeits-Festlegung (PyWinRT-Pakete, G11) ist nach Phase 0 umgezogen. Register: Anhang 1.)*

- Der Online/Offline-Schalter (Flugzeug/Globus, `set_online`, Taste `G`) **bleibt** und
  wird **funktional:** offline schalten heisst, den **echten Windows-Flugmodus**
  einzuschalten, also **alle Funkgeraete** (WLAN, Bluetooth, was vorhanden ist)
  auszuschalten; online schalten aktiviert sie wieder. Umsetzung ueber die
  Windows-Radio-APIs (WinRT `Windows.Devices.Radios` bzw. Radio-Management), eine
  einmalige Nutzerzustimmung ist akzeptabel. `get_wifi_signal()` bleibt und zeigt real
  den Zustand. Ueberschreibt B.2/B.4 ("rein lokaler Schalter, kein Netzwerkverkehr").
- **Technische Basis, verbindlich (U14-Entscheid, 2026-07-15).**
  - **"Flugmodus einschalten" heisst technisch "alle Radios aus".** Der System-Flugmodus
    als *ein* Flag ist ueber keine oeffentliche API schaltbar; schaltbar sind nur die
    einzelnen Funkgeraete. Umsetzung ist daher **Radio-Enumeration + `SetStateAsync` je
    Radio**, nicht das Setzen eines Flugmodus-Flags. Der Wortlaut "Windows-Flugmodus"
    oben ist als genau das zu lesen (Windows blendet das Flugzeug-Symbol ohnehin erst
    ein, wenn wirklich alle Radios aus sind). Konkret: `Radio.GetRadiosAsync()`
    aufzaehlen, nach `RadioKind` filtern (`WiFi`, `Bluetooth`, `MobileBroadband`; `Other`
    und GPS/`FM` werden nicht angefasst), je Treffer `SetStateAsync(RadioState.Off)` bzw.
    `.On`, danach `.State` je Radio zurueckgelesen (verifizierte Realitaet, siehe
    U15-`{online, partial}`-Vertrag oben).

  - **Verweigerter Zugriff degradiert sichtbar statt still zu scheitern.** Vor dem ersten
    Schalten wird `Radio.RequestAccessAsync()` einmalig ausgewertet. Ist das Ergebnis
    **nicht** `Allowed` (also `DeniedByUser`, `DeniedBySystem` oder `Unspecified`), wird
    **kein** Radio angefasst: der Schalter geht in einen sichtbar degradierten Zustand
    (Tooltip **"no radio access"**, statischer englischer Text nach G29), der reale
    Funk-Zustand bleibt **unveraendert** und die Pille zeigt weiter den tatsaechlichen
    Zustand. `set_online` liefert in diesem Fall `{ online:<real>, partial:true }` und
    aendert nichts. Ein blosses stilles Fehlschlagen (die App "schaltet offline", ohne
    dass ein Radio ausgeht) ist ausdruecklich verboten, das waere genau die verbotene
    Falschbehauptung "dunkel" aus dem U15-Aggregations-Vertrag.
  - **Kein Sicherheits-Riegel (B.10).** Auch mit echter Hardware bleibt der Schalter ein
    Privatsphaere-/Bequemlichkeits-Werkzeug gegen beilaeufiges Funken, kein Schutz gegen
    Schadsoftware, die Radios selbst wieder anschalten koennte; er darf nur nie behaupten,
    dunkel zu sein, wenn er es nicht ist.
- **Zustand nur beim Beenden wiederherstellen, als letzter Schritt (praezisiert durch
  N11.10).** Beim Beenden (Off-Knopf/`quit_app`, Panik-Finish, Killswitch-Ende,
  Fenster-X) wird der Funk-Zustand von **vor** dem App-Start wiederhergestellt (hat die
  App den Flugmodus eingeschaltet, wird er wieder ausgeschaltet). Das passiert **ganz
  zuletzt:** erst die Raum-Bereinigung und alle uebrigen Schritte (N10), am Ende die
  Wiederherstellung des Systemzustands. **Beim Sperren passiert dagegen KEINE
  Funk-Aenderung, in keiner Richtung: weder offline schalten noch wiederherstellen
  (N11.10); der Zustand bleibt einfach stehen und gilt nach dem Entsperren unveraendert
  weiter.**
- **Externe Aenderungen spiegeln.** Aendert der Nutzer den Flugmodus in den
  Windows-Einstellungen, passt sich die App-Anzeige an. Umsetzung **ereignisbasiert**
  (sofortige Reaktion auf die Windows-Radio-Statusaenderung) mit einer seltenen
  Gegenpruefung als Rueckfalllinie. Der Nutzerwunsch "alle 30 s abfragen" wird durch die
  sofortige Ereignis-Erkennung erfuellt und uebertroffen.
- **`set_online`-Vertrag bei echter Hardware (U15-Entscheid, 2026-07-15).** Der Aufruf ist
  asynchron und kann je Funkgeraet einzeln scheitern (WLAN geht aus, Bluetooth verweigert):
  - **Antwort erst nach Abschluss, nie feuern-und-vergessen.** `set_online(flag)` schaltet
    jedes Ziel-Radio (`SetStateAsync`), **liest danach den echten Zustand aller Radios neu
    ein** und antwortet erst dann. Der zurueckgegebene Zustand ist immer die **verifizierte
    Realitaet**, nie die blosse Absicht.
  - **Rueckgabe `{ online, partial }`** (ersetzt das alte `{ online }` in B.2). `partial:true`
    heisst: nicht jedes Ziel-Radio hat gehorcht.
  - **Sicherheits-Aggregation, Offline ist die schutzrelevante Richtung.** Beim
    Offline-Schalten gilt `online:true`, **sobald auch nur ein Radio noch an ist.** Die App
    behauptet also **nie** "offline/dunkel", solange irgendein Funkgeraet noch sendet; die
    Pille zeigt dann weiter online, `partial:true`. Beim Online-Schalten (unkritische
    Richtung) genuegt ein aktives Radio fuer `online:true`. Im Zweifel immer die ehrlichere,
    weniger "sichere" Anzeige.
  - **UI bei Teil-Erfolg:** die Pille springt auf den real erreichten Zustand, nicht auf den
    gewuenschten (`partial:true`), und benennt das verweigernde Radio (z.B. "Bluetooth could
    not be turned off") ueber Tooltip/Statuszeile. Einen **Toast** gibt es dafuer seit N11.16
    nicht mehr; der ehrliche Pillen-Zustand ist die Meldung.
  - **Kein Doppel-Schalten.** Hoechstens **eine** Radio-Operation gleichzeitig; waehrend eine
    laeuft, ist die Pille im Warte-Zustand und weitere `G`-/Klick-Ausloeser werden ignoriert
    (kein Ueberlappen, kein inkonsistenter Mischzustand).
  - **Verweigerter Gesamt-Zugriff** (`RequestAccessAsync` -> Denied) ist Sache von **U14**:
    der Schalter degradiert sichtbar (Tooltip "no radio access"), der reale Zustand bleibt
    unveraendert stehen.
  - **Ehrliche Einordnung:** Der Schalter ist ein Privatsphaere-/Bequemlichkeits-Werkzeug,
    **kein** Sicherheits-Riegel gegen Schadsoftware (B.10). Er darf nur nie *behaupten*,
    dunkel zu sein, wenn er es nicht ist.
- **`get_wifi_signal()`-Kadenz (U15).** Rein kosmetisch (Balken im Rail-WLAN-Icon). Das
  Frontend pollt **alle 10 s**, aber **nur** wenn (a) online, (b) das Fenster sichtbar ist
  (nicht minimiert) und (c) die App entsperrt ist; es **pausiert** bei offline (nichts
  anzuzeigen), bei verstecktem/minimiertem Fenster und im Lock-Screen (Bridge eingefroren,
  G13). Die Verbindung an/aus kommt ohnehin ereignisbasiert (oben), nur die Balkenstaerke
  braucht den Poll. Ein `get_wifi_signal`-Aufruf zaehlt **nicht** als Aktivitaet fuer die
  Auto-Sperre (U4): den Timer setzt allein `activity_ping` zurueck, nie ein kosmetischer
  Hintergrund-Poll.

#### Fehler-Hygiene, Fehlercode-Katalog und Logging-Politik (Etikett N11.12, 2026-07-13, S6-Entscheid, Gate G29) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3. Vorgefundener Defekt, hier behoben: die N11.12-Ueberschrift war im Nachtrag verloren gegangen, nur ihr Schluss „(2026-07-13, S6-Entscheid, Gate G29) [Sec]“ stand noch am Ende von N11.11.5.4; der Titel ist aus der Schnell-Checkliste rekonstruiert. Register: Anhang 1.)*

*Loest S6 der Plananalyse. Mit dem Sync fiel das alte Gate G10 ("Fehlermeldungen ohne
Geheimnisse") weg, obwohl sein Kern rein lokal weitergilt. Heute gibt der
`@bridge`-Decorator `str(exc)` ans Frontend (`api.py`), d.h. schon eine banale `OSError`
traegt absolute Pfade samt Windows-Benutzernamen als Toast auf den Bildschirm (bei
Screen-Sharing auf fremde Bildschirme). Ausserdem fehlten ein kanonischer Fehlercode-Katalog
und jede Aussage darueber, ob und wo das Backend loggt. Angreiferklassen: K3 (kurzer
physischer Zugriff, abgelesener Bildschirm) und K5 (Reverse-Engineer, der Interna
geschenkt bekommt), siehe B.10.6.*

##### N11.12.1 Generische Fehler nach vorne, Details nur in den RAM

- **Kein `str(exc)` ans Frontend, nie.** Der `@bridge`-Decorator faengt weiterhin jede
  Ausnahme, gibt aber ausschliesslich `{"error": <Code>, "message": <statischer Text>}`
  zurueck; bei `internal` zusaetzlich `{"ref": "<4 Hexzeichen>"}`. Die statischen Texte und
  die Codes stehen in **B.2** (Fehlercode-Katalog), das ist die einzige Wahrheit.
- **Verboten in jeder Meldung, die das Backend verlaesst:** Aufgaben-/Listentext,
  Passphrase, abgeleitete Schluessel, Pepper, Datei-Pfade, Tracebacks, SQL-Fragmente,
  Exception-Text der darunterliegenden Bibliothek.
- **In-Memory-Ringpuffer (Diagnose):** `Api` haelt einen Ringpuffer der letzten **50**
  Fehler, ausschliesslich im RAM (`collections.deque(maxlen=50)`), nie auf der Platte.
  Ein Eintrag ist: Zeitstempel, Bridge-Methodenname, Fehlercode, Exception-Klassenname,
  `ref` und eine **redigierte** Kurzmeldung. Redigieren heisst: jeder Pfad
  (alles, was wie `X:\...` oder `\\...` oder `/...` aussieht) wird durch `<path>` ersetzt,
  die Meldung auf 200 Zeichen gekuerzt. Aufgabentext gelangt gar nicht erst hinein: der
  Puffer speichert **niemals** Argumente der Bridge-Methode.
- **Einsehbar nur im Status-Modal** ("Recent errors", eingeklappt, mit Kopier-Knopf ueber
  den gehaerteten Backend-Clipboard-Pfad aus G23; Bridge-Methode `copy_errors()`, Zeile in
  der B.2-Methodenliste). Damit hat der Nutzer eine echte
  Fehlersuche, ohne dass Details ungefragt ins Bild springen.
- **Der Ringpuffer wird in Schritt 3 der `teardown(reason)`-Sequenz (N11.11, B.8.5) geleert**,
  also bei Sperre, Panik, Killswitch, Reset und Beenden. Ein gesperrter Bildschirm zeigt
  keine Diagnose-Historie mehr an.

##### N11.12.2 Logging-Politik (verbindlich)

- **Im Release gibt es kein persistentes Logfile.** Kein `logging.FileHandler`, kein
  `basicConfig(filename=...)`, keine Absturz-Tracebacks in eine Datei, kein
  `faulthandler.enable(file=...)`, keine Crash-Reports nach aussen (es gibt ohnehin kein
  Netz, N11.5). Eine Tresor-App, die nebenher eine Klartext-Logdatei schreibt, unterlaeuft
  beide Verschluesselungsschichten.
- **Konsolen-Ausgaben nur als Entwickler-Modus:** Die vorhandenen `print()`-Zeilen
  (`[NoaToDo] Start ...`) bleiben erlaubt, solange sie **nur** Programm-Zustand melden.
  Ausfuehrliche Diagnose haengt an `NOATODO_DEBUG=1` (schon vorhanden fuer die DevTools)
  und darf auch dann weder Passphrase noch Schluessel noch Aufgabentext ausgeben.
- **Der ausgelieferte Build laeuft nie im Debug-Modus:** in Phase 9 wird geprueft, dass
  `NOATODO_DEBUG` im Build nicht gesetzt ist und die DevTools aus sind (Abnahmepunkt
  dort ergaenzt).
- **Windows-eigene Kanaele:** Es wird nichts ins Windows-Ereignisprotokoll geschrieben und
  keine Telemetrie erhoben. (Was WebView2 selbst protokolliert, deckt G14 ab: der
  Profilordner wird gewischt.)

##### N11.12.3 Neues Pflicht-Gate G29

> **🔒 G29 (SOFORT, spaetestens mit Phase 7), Fehler-Hygiene:** (a) Der `@bridge`-Decorator
> gibt **nur** Codes und statische Texte aus dem Katalog in B.2 zurueck, nie `str(exc)`,
> nie Pfade, nie Tracebacks, nie Nutzertext. (b) Der Fehlercode-Katalog in B.2 ist
> vollstaendig und wird bei jedem neuen Code mitgepflegt; ein Code ohne Zeile dort darf
> nicht ans Frontend. (c) Details landen ausschliesslich im redigierten In-Memory-Ringpuffer
> (50 Eintraege, Status-Modal, Leerung in `teardown`). (d) Im Release existiert kein
> persistentes Logfile. **Abnahme:** Ein kuenstlich erzeugter `OSError` in einer
> Bridge-Methode zeigt im UI nur "Something went wrong." samt `ref`, im Ringpuffer steht
> `<path>` statt des echten Pfades, und im gesamten Repo findet sich kein `FileHandler`
> und kein `basicConfig(filename=...)`.

### B.3 Design-Tokens (aus dem Konzept übernehmen: nicht neu erfinden)

Schriften: **Space Grotesk** (UI-Sans) + **JetBrains Mono** (mono, Labels, Tags,
Zähler, „terminal"-Texte). Lokal als `woff2` einbinden (kein externer Font-Load →
passt zu local-first; siehe Phase 5).

Farbwelt: „warm" statt kaltes Neon. Zwei Themes über `data-theme`:

| Token | Light (warmes Papier) | Dark (warme Kohle) |
|---|---|---|
| `--bg` | `#efe8db` | `#15120d` |
| `--bg-grid` | `#e6ddcc` | `#1c1812` |
| `--surface` | `#faf6ee` | `#1f1b14` |
| `--surface-2` | `#f1ebdf` | `#272218` |
| `--surface-3` | `#e9e1d1` | `#322b20` |
| `--border` | `#ddd0ba` | `#3a3326` |
| `--border-strong` | `#cdbfa4` | `#4a4231` |
| `--text` | `#2c2519` | `#ece3d2` |
| `--text-dim` | `#6d6150` | `#a89a80` |
| `--text-faint` | `#9b8d75` | `#73684f` |
| `--secure` (grün) | `#4f8b5e` | `#6fb87f` |
| `--danger` (rot) | `#cf5638` | `#e0623e` |

Akzentfarbe `--accent` standard **`#d97757`** (Terrakotta). Auswählbare Akzente:
`#d97757 #c75d3a #5a9d6b #4a86c5 #d4a23c #a66a9c`.

Dichte über `data-density`: `comfortable` (Standard) und `compact` (kleinere Paddings,
Schrift, Abstände).

> Die **komplette `<style>`-Sektion** aus `NoaToDo UI Konzept.html` (rund 800 Zeilen
> CSS, inkl. `@font-face`, `:root`, `.app`-Grid, Header, Sidebar, Main, Toolbar,
> Overlays, Lock-Screen, Toasts, Scrollbars, Media-Query) wird in `frontend/style.css`
> übernommen. In Phase 5 steht, wie man sie extrahiert. **Nicht** von Hand nachbauen
> 1:1 kopieren, damit das Aussehen exakt stimmt.

### B.4 UI-Aufbau: die Abschnitte (genau so wie im Konzept und in der Skizze)

Die Oberfläche ist ein CSS-Grid: **Header** über die volle Breite, darunter drei
Spalten **Sidebar | Main | Toolbar**.

> **Fenstertitel-Regel (verbindlich, 2026-07-15, Plananalyse A7):** Der native
> Fenstertitel ist konstant "NoaToDo" und enthält **nie** Nutzerinhalte: keine
> Listennamen, keine Task-Texte, keine Zähler, in keinem Modus (ausdrücklich auch
> nicht im Mini-Modus, wo ein Listenname im Titel naheliegend wäre). Grund: der
> Titel ist für jeden Prozess ohne Privilegien lesbar (Fenster-Enumeration) und
> erscheint in Task-Switchern, Screen-Sharing-Übersichten und Tools wie PowerToys;
> er läge damit ausserhalb jeder Verschlüsselungsschicht. Dasselbe gilt für alle
> anderen nativ sichtbaren Metadaten (Taskbar-Tooltip, Jumplist-Einträge,
> Taskbar-Fortschritt). Bewusst kein eigenes Gate: die Regel ist eine Zeile, ihr
> Prüfweg ein Grep nach `set_title`/`window.title` ausserhalb der Konstante.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER (Höhe 56)                                                          │
│ [☰] [🛡 NoaToDo] [● LOCAL·ENCRYPTED]                      [NA]               │
├──────────────┬───────────────────────────────────────────┬───────────────┤
│ SIDEBAR 256  │ MAIN (zentriert, max 720)                 │ TOOLBAR (Rail) │
│              │                                           │               │
│ LISTS        │                       [✈ Flugmodus an]    │  ⤢ Focus      │
│ • Reading 5  │  Reading List                             │  🎨 Accent    │
│ • Ideas   3  │  5 open · 3 done                          │  ⬆ Export     │
│ • Homework 0 │                                           │  ? Shortcuts  │
│ • Program. 6 │  OPEN TASKS ──────────────────── 5        │  ───          │
│ • Travel  6  │  ○ Going Zero          Anthony McCarten   │  🔒 Lock      │
│ • Life    5  │  ○ On Leadership       Tony Blair         │  ⚠ Emergency │
│              │  ○ One of Us Is Back   Karen M. McManus   │  ───          │
│              │  …                                        │  ⧉ Copy       │
│              │  ⊕ New task…                        [↵]   │  ✎ Rename     │
│              │                                           │  🗑 Delete     │
│ + New list   │  ▸ COMPLETED ─────────────────── 3        │  ───          │
│ ⚙ Settings   │  ⊘ Project Hail Mary (durchgestrichen)    │  📈 Status    │
│              │                                           │  🌐 Online    │
└──────────────┴───────────────────────────────────────────┴───────────────┘
```

**Header** (`renderHeader`)
- Links: Hamburger-Button (toggelt Sidebar; Icon `Menu`/`Close`).
- Brand: quadratisches Akzent-Logo mit Schild-Icon, Wortmarke „Noa**ToDo**" (das
  „ToDo" in Akzentfarbe), danach Status-Pill „**LOCAL · ENCRYPTED**" mit pulsierendem
  grünen Punkt.
- **Mitte: leer.** Die frühere Benachrichtigungs-Glocke (`🔔`) ist ersatzlos gestrichen,
  die App hat keine Benachrichtigungen mehr (N11.1.1). Nichts nimmt ihren Platz ein.
- Rechts: heute leer. Der im Konzept vorgesehene Avatar „NA" samt **Profil-Menü**
  existiert im Code nicht; das Menü war unerreichbarer toter Code und wurde am
  2026-07-17 restlos entfernt (Phase 6.5, Audit 1.3). Ob der Avatar zurückkommt,
  regelt der N11.6-Header-Umbau (unten in B.4, U24); dann gilt die dortige
  Eindampf-Entscheidung (nur echte Funktionen).

**Sidebar** (`renderSidebar`)
- Mono-Label „LISTS" mit Trennlinie.
- Scrollbare Liste der `list-item`: kleiner Punkt, Name, Mono-Zähler (Anzahl offener
  Aufgaben). Aktive Liste: Akzent-Wash-Hintergrund + Akzent-Balken links + Punkt/Zähler
  in Akzentfarbe. Listen mit Zähler 0 zeigen den Zähler blasser.
- Fuß: „**+ New list**" (gestrichelter Akzent-Button; Klick öffnet ein Inline-
  Eingabefeld, Enter = anlegen, Esc/Blur = abbrechen) und „**⚙ Settings**".

**Main** (`renderMain` / `renderTaskView`)
- Banner-Zeile rechtsbündig: **Flugmodus/Online-Pill** (Icon Plane bei offline,
  Globe bei online; Klick schaltet den echten Windows-Flugmodus um, siehe `set_online`
  und N11.5).
- Großer Listentitel (32px).
- Meta-Zeile (Mono-Tags): „X open", Punkt, „Y done".
- Abschnitt **OPEN TASKS**: Section-Head (Mono-Titel + Zähler + Linie), darunter die
  Aufgaben-Karten. Ist nichts offen: Mono-Hinweis „// nothing open, you're all caught up".
- **New-task-Eingabe**: gestrichelte Akzent-Karte mit Plus, Platzhalter „New task…",
  Enter legt an, `[↵]`-Kbd rechts.
- Abschnitt **COMPLETED** (nur wenn es erledigte gibt): einklappbarer Section-Head
  (Chevron dreht), animiertes Auf-/Zuklappen, darunter die erledigten Aufgaben.

**Aufgaben-Karte** (`renderTask`)
- Runder Check-Button (Klick → `toggle_task`). Text (kein Meta-Feld mehr, N11.1.3).
  Drag-Griff, der bei Hover erscheint.
- Erledigt: transparenter Hintergrund, gestrichelter Rand, Text durchgestrichen +
  blass, Check in Grün gefüllt.

**Rechte Toolbar** (`renderToolbar`), vertikale Leiste, **immer schwebend** (gerundete
Karte). Es gibt **keine zwei Modi mehr**: das frühere `flush`/`floating` samt dem
Settings-Key `toolbar` und dem `data-toolbar`-Attribut ist gestrichen (N11.7), die Rail
schwebt immer. Sie ist an-/abheftbar (`railPinned`). Buttons mit Tooltip + Hotkey, in
Gruppen durch Trenner:
1. **Focus mode** (⤢, `F`), blendet Sidebar+Toolbar aus, nur eine „Exit focus"-X bleibt.
2. **Accent color** (🎨), öffnet Swatch-Popover mit den 6 Akzenten.
3. **Export** (⬆, `Ctrl+E`), zweistufig: erst Umfang (aktuelle Liste / alle Listen),
   dann Format (md / txt), siehe Phase 7 (N11.2).
4. **Shortcuts** (?), öffnet das Tastenkürzel-Modal.
   (Trenner)
5. **Lock / Unlock** (🔒, `Ctrl+L`).
6. **Emergency** (⚠, rot), öffnet das **PanicPanel** (Pille an der Rail, kein Modal mehr, N10); bewusst ohne Tastenkürzel, Panik ist nur per Maus erreichbar (N5).
   (Trenner)
7. **Copy task** (⧉): kopiert die per Klick **ausgewählte** Aufgabe (gehärtet,
   siehe G23); ohne Auswahl passiert still nichts (kein Hinweis-Toast mehr, N11.16). Kein Tastenkürzel.
8. **Rename list / Edit task** (✎), kontextuell: Ist eine Aufgabe ausgewählt,
   öffnet der Stift deren Inline-Bearbeitung; sonst das Umbenennen-Modal der Liste.
9. **Delete list** (🗑), öffnet Löschen-Modal.
   (Trenner)
10. **App status** (📈), öffnet Diagnose-Modal.
11. **Go online/offline** (🌐, `G`), aktiv-Zustand wenn online.

**Overlays** (`renderOverlays`)
- **ProfileMenu**, Dropdown unter dem Avatar (auf Funktionierendes eingedampft, N11.6):
  kein fest eingetippter Name mehr, nur ein neutraler „local"-Kopf; Einträge nur, was
  echt funktioniert: „Export database" (= Alle-Listen-Export, N11.2) und ein Link zu
  den Einstellungen. Tote Einträge (Account, Privacy & data mit Platzhalterinhalt)
  entfallen.
- **PanicPanel** (hat das frühere EmergencyModal ersetzt): schwebende Pille an der
  Rail, zweistufig entsichert (Kippschalter „No/Yes", dann separate „Confirm"-Pille).
  Nach dem Bestätigen: sofortige Raum-Bereinigung, „Wipe"-Fortschrittsschirm, danach
  der Endschirm mit den zwei Ausgängen Finish (Akzent, App beenden) und Killswitch
  (grau, zweistufig im Knopf, löscht unwiderruflich die Datenbank-Inhalte). Details
  und Verbindlichkeit: Etikett N10.3, unten in diesem Abschnitt.
- **SettingsModal** (existiert im Code, wird über „⚙ Settings" in der Sidebar
  geöffnet; der frühere zweite Weg über das Profil-Menü ist mit dessen Entfernung
  2026-07-17 weggefallen, siehe Phase 6.5). Es ist das **einzige** Einstellungs-UI der App;
  jeder Key aus B.6 hat hier genau eine Bedienstelle. Sektionen (Zeile + Segment-
  Schalter, wie im Konzept):
  1. **Appearance:** `theme` (Segment `Auto` | `Light` | `Dark`, Default `Auto`, folgt
     bei `Auto` live dem Windows-Theme; `Ctrl+J` setzt hier den manuellen Override,
     N11.6), `accent` (die 6 Swatches), `density` (`Comfortable` | `Compact`).
  2. **Sound:** `sound` (Schalter, Erledigt-Blip an/aus, Default an, N11.6).
  3. **Export:** `exportDone` (Segment `Include` | `Exclude`, ob erledigte Aufgaben in
     die Export-Dateien kommen, Default `Include` = an, U10 Punkt 6, 2026-07-17).
  4. **Security:** `autoLock` (Minuten bis zur Auto-Sperre, `0` = nie, Default 15,
     N11.4) und **Passphrase ändern** (Phase 8, N11.3: alte Passphrase, neue Passphrase
     mindestens 12 Zeichen, Wiederholung, Warnung „kein Recovery").
  Kein Toolbar-Modus-Schalter mehr (gestrichen, N11.7), keine Benachrichtigungs-Sektion
  mehr (gestrichen, N11.1.1). Änderungen schreiben sofort über `set_setting` zurück und
  wirken sofort auf `.app` (`data-*`/`--accent`).
- **StatusModal**, Diagnose-Zeilen: Local database (Größe), Encryption (AES-256 +
  ChaCha20 · Argon2id), Network (local only · online/offline), WebView2 runtime,
  jeweils mit grünem/blassem Status-Tag. Daten kommen aus `get_status()`.
- **RenameModal**, Eingabefeld (vorbelegt, fokussiert+selektiert), Enter/Save.
- **DeleteModal: gestrichen (2026-07-17, Audit 1.2).** Aufgaben werden bewusst ohne
  Bestätigungs-Modal sofort gelöscht (Rail-Papierkorb; Undo gibt es nur beim
  Listen-Löschen, N11.2.1), und Listen bestätigen inline in der Sidebar
  (`confirmDeleteId`), nicht per Modal. Der nie erreichbare Modal-Code wurde entfernt.
- **ShortcutsModal**, Raster aller Tastenkürzel (siehe B.5).
- **LockScreen**, Vollbild über allem: Akzent-Ring mit Schloss, „NoaToDo is locked",
  Passwort-Pille (Phase 8: echte Passphrase-Prüfung, siehe den N4-Abschnitt unten in
  B.4). Oben rechts ein
  klassischer **Off-Knopf** (Power-Symbol): beendet die App sofort ohne Passphrase
  über `quit_app()`, vernichtet dabei Spuren, löscht aber nie Nutzer- oder App-Daten
  (N10.2, Volltext unten in B.4). Unten ein unauffälliger, **nicht** akzentuierter Link
  „**Forgot passphrase?**": er führt zum **Reset** (N11.3), dem einzigen Ausweg aus der
  vergessenen Passphrase. Der Reset ist wie der Killswitch abgesichert (erst
  Bestätigung mit dem Klartext-Hinweis, dass **alle** Daten unwiderruflich verloren
  gehen, dann `RESET` tippen) und ruft `reset_vault()`; danach beginnt das Onboarding
  von vorn.
- **OnboardingScreens** (Phase 8, N11.13), Vollbild, drei Schritte, kein Header/keine
  Sidebar/keine Rail. Sie erscheinen genau dann, wenn `get_boot_state()`
  `state: 'onboarding'` liefert (frischer Rechner, nach Reset, nach Killswitch).
  Details unten.
- **Toasts** gibt es bewusst nur noch **einen einzigen**: den **Undo-Toast** beim
  Listen-Löschen (N11.2.1). Er steht **unten links, direkt rechts neben der Sidebar**
  (Nutzerwunsch 2026-07-17: gut sichtbar und klickbar an der Stelle, wo die gelöschte
  Liste stand), verankert an der Sidebar-Breite (0 wenn geschlossen), mit sichtbarem
  Ablaufbalken über die ca. 6 s Standzeit. **Alle anderen Toasts sind gestrichen
  (N11.16, Nutzerwunsch: keine Benachrichtigungen):** weder Erfolgs-Bestätigungen
  („List created", „Task updated", „Exported", „Task moved", „Back online" usw.) noch
  Fehler-/Validierungshinweise poppen auf; eine geglückte Aktion wird nicht quittiert,
  Fehler laufen still bzw. bleiben im Status-Modal („Recent errors", G29) einsehbar
  (Toast-Politik: B.2).

**Onboarding: die drei Screens (verbindlich, N11.13)**

Der Boot rendert **nichts** von der App, bevor `get_boot_state()` geantwortet hat:
`onboarding` → diese Screens, `locked` → LockScreen, `unlocked` → normale App.
Zurück-Navigation ist in Schritt 1 und 2 erlaubt, nach dem Anlegen nicht mehr.

1. **Willkommen und Ort wählen.** Kurzer, ehrlicher Text: NoaToDo ist ein lokaler,
   verschlüsselter Tresor; es gibt keine Cloud, kein Konto, keinen Sync. Ein Button
   „Choose location" ruft `choose_vault_dir()` (nativer Ordner-Dialog im Backend). Der
   gewählte Pfad wird angezeigt; Default-Vorschlag ist `%LOCALAPPDATA%\NoaToDo` (G32).
   Liegt der Pfad in einem Cloud-Ordner (OneDrive/Dropbox), erscheint eine deutliche
   Warnung: die verschlüsselte Datei würde synchronisiert, und der **Killswitch löscht
   keine Cloud-Versionen** (G32). Weiter erst, wenn ein beschreibbarer Ort gewählt ist.
   Liegt im gewählten Ordner **schon eine `tasks.db.enc`** (`choose_vault_dir()` meldet
   `has_vault:true`), schaltet der Screen um: statt „neuen Tresor anlegen" bietet er nur
   „**Diesen Tresor öffnen**" an (schreibt den Pfad in `config.json` und geht zum
   Lock-Screen). Ein bestehender Tresor wird im Onboarding **nie** überschrieben
   (N11.15.6); wer wirklich neu anlegen will, wählt einen anderen Ort.
2. **Passphrase setzen.** Zwei Felder (Passphrase, Wiederholung). Einzige Regel:
   **mindestens 12 Zeichen** (N11.3), kein Stärkemesser, keine Zeichenklassen-Regeln.
   Darüber, nicht kleingedruckt, sondern als **Pflichttext** die Verlust-Warnung:
   > **Es gibt keine Wiederherstellung.** Wer die Passphrase vergisst, verliert alle
   > Daten; niemand kann sie zurückholen (auch der Entwickler nicht). Der Tresor ist
   > zusätzlich **an dieses Windows-Konto gebunden**: neu aufgesetztes Windows-Profil
   > oder anderer PC bedeutet Datenverlust, selbst mit korrekter Passphrase (G18/V2).
   Darunter eine **aktive Bestätigung** (Checkbox „I understand there is no recovery"),
   ohne die der Weiter-Button deaktiviert bleibt. Kein vorangekreuztes Häkchen.
3. **Fertig.** `create_vault(path, passphrase)` legt den leeren Tresor an (Pepper, Salt,
   Argon2-Parameter, leere DB, `tasks.db.enc`, Pfad in `config.json`). Kurze
   Bestätigung, was jetzt existiert und wo, dann startet die App **entsperrt** mit einer
   leeren Listen-Ansicht (keine Demo-Daten, N11.1.4). Schlägt das Anlegen fehl (Pfad
   nicht beschreibbar, Credential Manager verweigert den Pepper), zeigt der Screen den
   N6-Fehlerbildschirm mit „erneut versuchen" und „anderen Ort wählen"; ein halb
   angelegter Tresor wird dabei restlos entfernt.

Der Onboarding-Flow ist ein **Boot-Zustand, kein Modal**: Er ist nicht mit `Esc`
schliessbar, hat keinen Weg in die App vorbei am Anlegen, und die Rail/Shortcuts sind
inaktiv. Einzige Ausnahme: das Fenster-X beendet die App (und läuft dabei durch die
Sequenz aus B.8.5, N11.11).

#### Persistente Offline-Statusanzeige (Etikett N2, UX 4.2/8.3)

*(Wortgleich umgezogen in Umbau-Etappe 3. Register: Anhang 1.)*

Der Online/Offline-Zustand ist heute fast unsichtbar (nur Globus-/Flugzeug-Icon in
der oft versteckten Rail plus kurzer Toast). Das Konzept sah die `airplane-pill` als
persistenten Banner vor; ihr CSS liegt ungenutzt im Stylesheet. Optionaler UX-Ausbau:
- Eine **persistente Statuspille** im Hauptbereich (oder am Dock), sichtbar sobald
  `online=false` („offline mode"). Der Schalter steuert seit N11.5 den **echten**
  Windows-Flugmodus (das frühere „rein lokales Flag" ist überholt), umso wichtiger
  ist die sichtbare Anzeige.
- Damit entschärft sich auch UX 3.12 (versehentliches `G`/Offline ohne sichtbare Folge).

#### Echter Lock-Screen mit Passphrase: UX-Pflichten (Etikett N4, UX 8.1, Phase 8) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3. Register: Anhang 1.)*

B.4 und Phase 8 nennen die Passphrase-Eingabe, aber nicht die UX-Details. Der heutige
„4x tippen"-Platzhalter (`renderLock`, `lockTap`) wird ersetzt durch ein echtes
Eingabefeld mit folgenden **Pflicht-Eigenschaften**:
- Passwort-Feld mit Show/Hide-Umschalter.
- Fehlerzustand bei falscher Passphrase: Shake + Meldung „wrong passphrase", **ohne**
  preiszugeben, ob ein Tresor existiert (neutrale Meldung).
- Warnung bei aktiver Feststelltaste (Caps Lock).
- **Fortschritts-/Spinner-Zustand beim Entsperren:** Argon2id mit den Kosten aus
  Gate G8 (256 MiB, `time_cost=3`, `parallelism=4`, N11.4.3) braucht spürbar Zeit; das
  ist gewollt, also braucht es eine „unlocking…"-Anzeige, sonst wirkt die App
  eingefroren. Scheitert die Speicher-Allokation (`MemoryError`), zeigt der Screen den
  eigenen `memory`-Zustand („Not enough memory…", N11.4.3), **nicht** den
  Falsch-Passwort-Shake.
- **Rate-Limit-Anzeige** nach mehreren Fehlversuchen („try again in 30 s"); bremst
  Offline-Rateversuche zusätzlich zur teuren KDF.
- **Verbindliche Fehlerunterscheidung (falsche Passphrase / beschädigte Datei /
  fehlender Tresor) samt Rückgabeformat steht in der Entsperr-Fehlerlogik N6 im
  `unlock()`-Vertrag in B.2 (löst U7).** Kurz: `passphrase`
  erzeugt Shake + neutrale Meldung, `vault` führt in den Fehlerbildschirm mit
  `.bak`-Angebot, „kein Tresor" ist ein Boot-Zustand, kein `unlock`-Ergebnis.
- Hängt an Gate G13 (gesperrt = Backend liefert `locked`), G15 (Prüfung über den
  Poly1305-Tag) und G18 (DPAPI-Pepper): ohne Pepper bzw. richtige Passphrase scheitert
  die ChaCha20-Entschlüsselung, die Fehlermeldung kommt aus dem AEAD-Tag.

#### Entsperr-/Boot-Fehlerbildschirm (Etikett N6, UX 6.3, Phase 8) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3; die entscheidbare Fehlerlogik samt Rueckgabeformat, der zweite Teil von N6, steht im `unlock()`-Vertrag in B.2. Register: Anhang 1.)*

`boot()` rendert bei Fehlern heute ein nacktes `<pre>boot error</pre>`. Ab Phase 8 sind
„falsche Passphrase" und „beschädigte/fehlende `tasks.db.enc`" reale Szenarien. Pflicht:
ein gestalteter Fehlerzustand mit Handlungsoption (Retry, Pfadangabe, Hinweis auf die
`.bak`-Generation aus Gate G16 und, bei vergessener Passphrase, auf den Reset-Weg aus
N11.3; einen Pepper-Recovery-Export gibt es bewusst nicht). Der Nutzer darf bei einem
AEAD-Fehler nie ratlos vor einem leeren Fenster stehen.

#### Off-Knopf auf dem Lock-Screen (Etikett N10.2, 2026-07-08)

*(Wortgleich umgezogen in Umbau-Etappe 3, Punkt 2 des Nachtrags N10. Register: Anhang 1.)*

**2. Off-Knopf auf dem Lock-Screen.** Oben rechts ein klassischer Power-Knopf. Ein
Klick beendet die App sofort über `quit_app()`, ohne Passphrase. Dabei werden
zufällig hinterlassene Spuren vernichtet (heute: der Raum ist bereits bereinigt,
der WebView2-Cache wird ohnehin beim nächsten Start gewischt; Phase 8: sicheres
Wischen von `PROFILE_DIR` nach G14, Schlüssel nullen nach G25), aber ausdrücklich
**keine Nutzer- und keine App-Daten gelöscht**. Die Passworteingabe bleibt daneben
jederzeit möglich; der Off-Knopf ist nur der zweite Ausgang.

#### Panik-Endschirm mit zwei Ausgaengen (Etikett N10.3, 2026-07-08)

*(Wortgleich umgezogen in Umbau-Etappe 3, Punkt 3 des Nachtrags N10; die Abwaegung zur bewussten Aussendarstellung steht in B.10.5. Register: Anhang 1.)*

**3. Panik-Endschirm mit zwei Ausgängen.** Der Panik-Einstieg bleibt mehrstufig
(Rail-Knopf, Kippschalter „No/Yes", separate Confirm-Pille): mit dem Mehrmals-
Bestätigen ist man gegen Versehen sicher unterwegs. Nach dem Bestätigen wird sofort
real bereinigt (Raum leeren und Zustand verwerfen wie beim Lock, **zusätzlich**
offline schalten; das Offline-Schalten gibt es seit N11.10 nur noch hier im
Panik-Flow, nicht mehr beim Sperren) und der
„Wipe"-Fortschrittsschirm gezeigt; danach der Endschirm. Wipe-Schirm und Endschirm
tragen **dauerhaft** ehrliche Texte („Clearing workspace" / „Workspace cleared",
umgestellt 2026-07-17): der früher für Phase 8 vorgesehene, bewusst falsche
Aussenschirm („All data securely wiped") kommt **nicht** zurück (Entscheidung N11.17,
2026-07-21; Abwägung und Begründung in B.10.5). Zurück in die App führt
von dort **kein Weg mehr**. Unten zwei Knöpfe:
- **Links, Akzentfarbe: „Finish".** Beendet nur die App (`quit_app()`). Alle Daten
  bleiben vollständig erhalten; der nächste Start ist ein normaler Start.
- **Rechts, grau: „Killswitch",** zweistufig im Knopf selbst: der erste Klick fährt
  den Schriftzug „Killswitch" nach rechts und ein „OK" fährt herein; erst der Klick
  auf „OK" löst aus. Dann läuft ein Fortschrittsbalken mit Statuszeilen („Deleting
  user data", „Deleting lists", …), währenddessen löscht `killswitch()` die
  Datenbank-Inhalte **real und unwiderruflich** (alle `lists`/`tasks`
  und `settings`, danach `VACUUM`, damit die gelöschten Zeilen nicht in freien
  Seiten der Datei liegen bleiben). Anschließend beendet sich die App von selbst.

#### Header, Profil-Menue, Fensterzustand und Mini-Bounds (Etikett N11.6, U24-Entscheid 2026-07-15)

*(Wortgleich umgezogen in Umbau-Etappe 3 aus N11.6; der Theme- und der Ton-Teil von N11.6 stehen in B.6. Register: Anhang 1.)*

- **Header-Mitte bleibt leer** (die frühere Benachrichtigungs-Pille faellt ersatzlos
  weg). Brand links, Avatar rechts.
- **Profil-Menue eindampfen.** Der fest eingetippte Name ("Noa Andersen") und tote
  Eintraege raus. Es bleibt nur, was echt funktioniert: "Export database" wird der neue
  Alle-Listen-Export (N11.2), optional ein Link zu den Einstellungen. Alles andere
  entfernen. *(Stand 2026-07-17: das Menue wurde als unerreichbarer toter Code komplett
  entfernt, Phase 6.5/Audit 1.3; dieser Punkt beschreibt den Zielzustand, falls der
  Header mit diesem Umbau wieder einen Avatar samt Menue bekommt.)*
- **Fenster startet maximiert** (fest verdrahtet, kein Setting noetig). Ueberschreibt N9
  "maximiert vs letzte Groesse".
- **Fensterzustand um den Mini-Modus (U24-Entscheid, 2026-07-15).** Beim Wechsel in den
  Mini-Modus werden die aktuellen Fenster-Bounds (Position, Groesse, Maximiert-Flag)
  gemerkt; beim Verlassen des Mini-Modus (Rail-Knopf oder `Esc`) werden **genau diese**
  wiederhergestellt (reines WinForms-Bounds-Merken in `set_mini`, ueber den UI-Thread, kein
  Setting, keine Spike-Abhaengigkeit). **Der Mini-Modus ueberlebt keine Sperre:** nach dem
  Entsperren ist das Fenster immer maximiert und nie mini (der Vor-Sperr-Fensterzustand wird
  pro Sicherheit bewusst nicht ueber die Sperrgrenze getragen, N11.8.3 Spike-Frage 4).

### B.5 Tastenkürzel (verbindlich, einzige Wahrheit)

*(Vollständig neu abgeleitet 2026-07-13 aus dem realen Code, `app.js` `onKeyGlobal`
plus Feld-Handler; behebt Plananalyse W6. Diese Tabelle ist die **einzige Wahrheit**
für Tastenkürzel: Wer ein Kürzel ändert oder ergänzt, ändert Code, diese Tabelle,
das Shortcuts-Modal und die CLAUDE.md-Tabelle im selben Zug. Frühere Fassungen sind
ungültig; insbesondere gibt es kein blankes `N` für "Neue Liste" mehr.)*

| Aktion | Taste | Bedingung |
|---|---|---|
| Neue Aufgabe anlegen | `↵` | im New-task-Feld |
| New-task-Feld öffnen/schließen | `Ctrl+N` | braucht eine offene Liste; Toggle, feuert auch aus dem Feld heraus |
| New-list-Feld öffnen/schließen | `Ctrl+Shift+N` | Toggle, feuert auch aus dem Feld heraus |
| Sidebar umschalten | `Ctrl+B` | |
| Focus-Modus | `F` | braucht eine offene Liste; Verlassen geht immer |
| Liste wechseln | `Ctrl+↑` / `Ctrl+↓` | Sidebar offen UND eine Liste offen; stoppt an den Enden, kein Umlauf |
| Liste 1-9 öffnen | `Ctrl+1` bis `Ctrl+9` | nur bei offener Sidebar (eine offene Liste bei geschlossener Sidebar reicht nicht); 1 = oberste; dieselbe Nummer erneut schließt die Liste (Toggle) |
| App sperren | `Ctrl+L` | |
| Exportieren | `Ctrl+E` | öffnet die zweistufige Export-Pille (erst Umfang, dann Format; zweiter Druck oder `Esc` schließt sie; umgesetzt 2026-07-17, N11.2); ohne offene Liste ist die Umfang-Option "aktuelle Liste" ausgegraut, nur "alle Listen" wählbar (N11.2.3); im Mini-Modus bewusst ohne Funktion (reines Lesefenster) |
| Theme umschalten | `Ctrl+J` | aus `auto` heraus: Override auf das Gegenteil des aktuell angezeigten Themes; aus einem festen Theme: das andere feste; Rückkehr zu `auto` nur über das Settings-Segment (U16) |
| Online/Offline | `G` | |
| Tastenkürzel-Hilfe | `?` | |
| Alles schließen | `Esc` | schließt Menüs, Modals, Eingabefelder, Kontextmenü, Inline-Edit; hebt Auswahl und Focus-Modus auf; im Mini-Modus: Mini verlassen; schließt das Panik-Panel, aber NICHT den laufenden/fertigen Wipe-Schirm; funktioniert auch beim Tippen |

**Bewusst OHNE Tastenkürzel** (verbindlich so gewollt, nicht vergessen):

- **Panik-Flow:** nur über den Rail-Knopf, zweistufig entsichert (N5); die
  Mehrfach-Bestätigung ist Absicht.
- **Kopieren:** es gibt kein `Ctrl+C`-App-Kürzel mehr (Phase 6.5); kopiert wird nur
  die ausgewählte Aufgabe über den Rail-Knopf (Gate G23).
- **Mini-Modus:** nur über den Rail-Knopf erreichbar; `Esc` verlässt ihn.

**Maus-Gesten** (kein Tastenkürzel, gehören aber ins Shortcuts-Modal): Einfachklick
auf eine Aufgabe = Auswahl, Doppelklick = Inline-Edit, Ziehen = Sortieren; seit
Phase 7 (N11.2, 2026-07-17) ausserdem: Listen-Eintrag in der Sidebar ziehen =
Listen sortieren (`reorder_lists`), Aufgabe auf einen Sidebar-Eintrag ziehen oder
Rechtsklick auf die Karte ("Move to...") = Aufgabe verschieben (`move_task`).

**Gestrichen:** `Ctrl+Shift+!` (früher als Notfall-Sperre, zuletzt als verstärkte
Sperre ohne Rückfrage gedacht) ist ersatzlos entfernt und darf nicht wieder
eingeführt werden (N5, Entscheid 2026-07-13, löst Plananalyse W5). Seit N10 ist
ohnehin jede Sperre verstärkt (Raum-Bereinigung vor dem Lock-Screen), `Ctrl+L`
deckt den "schnell alles zu"-Fall damit vollständig ab.

**Regeln:**

- Beim Tippen in Eingabefeldern feuern die Buchstaben-Hotkeys (`F`, `G`, `?`) nicht.
  Ausnahmen: `Esc` sowie `Ctrl+N`/`Ctrl+Shift+N` (damit der zweite Druck das gerade
  geöffnete und fokussierte Feld wieder schließen kann, Toggle).
- Im gesperrten Zustand sind alle Kürzel deaktiviert; jede druckbare Taste fokussiert
  stattdessen das Passwortfeld des Lock-Screens (das Zeichen wird danach normal
  eingefügt).
- Das Shortcuts-Modal (`?`) zeigt dieselbe Menge wie diese Tabelle, einschließlich
  `Esc` und `?` selbst, plus die Maus-Gesten und den Hinweis, dass Panik, Kopieren
  und Mini-Modus bewusst nur über die Rail laufen.
- **Layout-Regel (Lektion aus dem gestrichenen `Ctrl+Shift+!`, Plananalyse U22):** Ein
  künftiges Kürzel, das eine **Modifikatortaste mit einem Satzzeichen** kombiniert, wird
  **über `e.code`** definiert (die physische Taste, z.B. `Ctrl+Shift+Digit1`), nie über
  `e.key === '!'`. Auf Layouts, die das Zeichen erst über AltGr erzeugen, feuert eine
  `e.key`-Prüfung sonst nie. Die heutigen Buchstaben-/Zeichen-Hotkeys ohne solche
  Kombination (`F`, `G`, `?`) bleiben korrekt bei `e.key`: dort ist genau das erzeugte
  Zeichen gemeint, layoutunabhängig (`?` feuert, wann immer der Nutzer ein `?` erzeugt).

### B.6 Einstellungen (persistiert in `settings`-Tabelle)

`accent` (Hex), `theme` (`auto`|`light`|`dark`, Default `auto`, ersetzt das frühere
`dark`, siehe die N11.6-Detail-Festlegungen unten in B.6), `density` (`comfortable`|`compact`), `sidebar` (`open`|`closed`),
`sound` (bool, Erledigt-Ton, Default `true`, N11.6), `autoLock` (Minuten bis zur
Auto-Sperre, `0` = nie, Default `15`, N11.4), `exportDone` (bool, erledigte Aufgaben in
den Export aufnehmen, Default `true` = an, 2026-07-17, U10 Punkt 6). Werden beim Start aus `get_state()`
gelesen und auf das `.app`-Element als `data-*`/`--accent` gesetzt; Änderungen sofort
via `set_setting` zurückschreiben. Der frühere Key `toolbar` entfällt (die Rail ist
immer `floating`). Bei `theme=auto` folgt die App live dem Windows-Hell/Dunkel-Zustand
(ereignisbasiert), `Ctrl+J` setzt einen manuellen Override, bis wieder `auto` gewählt
wird.

**Detail-Festlegungen zu Theme und Ton (Etikett N11.6, U16-Entscheid 2026-07-15; wortgleich umgezogen in Umbau-Etappe 3; Register: Anhang 1):**

- **Theme folgt automatisch Windows** (hell/dunkel), mit **sofortiger** Reaktion auf die
  Windows-Theme-Aenderung (ereignisbasiert ueber `WM_SETTINGCHANGE` bzw. den Registry-
  Wert `AppsUseLightTheme`), plus **eine seltene Gegenpruefung alle 60 s** als
  Rueckfalllinie (Intervall festgelegt 2026-07-15, loest Plananalyse U16; das Ereignis
  bleibt der Hauptweg). Beim Start sofort das korrekte Theme, kein Nachziehen.
  **Manueller Override bleibt:** `Ctrl+J` bzw. der Theme-Schalter setzt bewusst ein festes
  Theme, bis der Nutzer wieder auf "automatisch" stellt. Die drei bisher offenen Details
  sind entschieden (U16):
  - **`Ctrl+J` aus `theme=auto` heraus** setzt den Override auf das **Gegenteil des
    aktuell angezeigten (effektiven) Themes**: zeigt die App gerade hell, schaltet es auf
    festes Dunkel und umgekehrt. Aus einem festen Theme heraus schaltet `Ctrl+J` auf das
    jeweils andere feste Theme.
  - **Zurueck zu `auto`** geht **nur** ueber das Appearance-Segment in den Einstellungen
    (`Auto`|`Light`|`Dark`); `Ctrl+J` kehrt nie von selbst nach `auto` zurueck, es bewegt
    sich ausschliesslich zwischen den beiden festen Themes.
  - **Intervall der Gegenpruefung: 60 s** (siehe oben).

  Der Settings-Key `dark` wird dazu durch `theme` mit den Werten
  `auto`|`light`|`dark` ersetzt (Default `auto`); in die G20-Whitelist aufnehmen.

- **Erledigt-Ton abschaltbar.** Der synthetisierte Blip beim Abhaken bleibt Default an,
  ist aber in den Einstellungen abschaltbar. Neuer Settings-Key `sound` (bool, Default
  `true`); in die G20-Whitelist aufnehmen.

### B.7 Verschlüsselung (verbindlich): Doppel-Kaskade AES-256 + ChaCha20

Die lokale Datenbank ist **immer verschlüsselt**, und zwar in **zwei unabhängigen
Schichten** (Tresor im Tresor, VeraCrypt-Prinzip). Beide Algorithmen sind etablierte,
jahrzehntelang geprüfte Standards, **kein Eigenbau**. Ein Angreifer müsste *beide*
unabhängig brechen.

> **Ehrliche Einordnung (steht bewusst im Plan):** AES-256 allein wäre bereits jenseits
> jeder realistischen Bedrohung, auch für Geheimdienste, nicht knackbar. Die zweite
> Schicht ist **Defense-in-Depth** (Sicherheitsmarge + bewusst gewählter „Bunker-Vibe"),
> kein notwendiger Schutz gegen einen praktischen Angriff. Der *wahre* Schwachpunkt
> bleibt in beiden Fällen die Passphrase, deshalb ist die starke Schlüsselableitung
> (Punkt 3) genauso wichtig wie die Cipher selbst.

**Schicht 1, die Datenbank selbst: SQLCipher (AES-256).**
Statt des normalen `sqlite3` wird **SQLCipher** verwendet (Paket **`sqlcipher3-wheels`**,
importiert als `import sqlcipher3`; **nicht** `sqlcipher3-binary`, das keine
Windows-Wheels liefert und bei der Installation scheitert, die API ist identisch):
dieselbe SQLite-API, aber die Datei ist seitenweise mit AES-256 verschlüsselt und behält
alle DB-Vorteile (gezielte Abfragen, Transaktionen, Crash-Sicherheit). Direkt nach dem
Öffnen wird der Schlüssel gesetzt:
```python
conn = sqlcipher3.connect(working_db_path)
conn.execute("PRAGMA key = ?", (aes_key,))     # aes_key = abgeleitet, s. Punkt 3
conn.execute("PRAGMA foreign_keys = ON")
```

**Schicht 2, die ganze DB-Datei nochmal: ChaCha20.**
Die im Ruhezustand auf der Platte liegende Datei ist **`tasks.db.enc` = ChaCha20-
Poly1305( SQLCipher-AES-256-Datei )**. Das ist der einzige Artefakt, das dauerhaft
auf der Festplatte existiert, also genau in dem Moment doppelt geschützt, in dem die
Gefahr real ist (App geschlossen / Laptop verloren / Backup / Cloud-Ordner).
- **Beim Entsperren:** ChaCha20-Schicht entfernen (die Poly1305-Prüfung ist zugleich
  die Passphrase-Prüfung, siehe Punkt 3) → das innere SQLCipher-Image **bevorzugt
  direkt in eine In-Memory-SQLite** (`:memory:`, Gate G6) laden und mit `aes_key`
  öffnen. Nur wenn die gewählte SQLCipher-Build-Variante das verlässliche
  Serialisieren aus `:memory:` nicht hergibt, gilt der N11.9-Fallback: eine
  **SQLCipher-verschlüsselte** Arbeitsdatei in einem ACL-beschränkten
  Temp-/RAM-Disk-Pfad. In beiden Fällen liegt **nie** eine Klartext-Arbeitskopie
  auf der Platte (N11.9); die Arbeitsdatei wäre reiner AES-Chiffretext.
- **Beim Sperren/Schließen/Panic:** das DB-Image wieder als `tasks.db.enc` mit
  ChaCha20-Poly1305 einpacken (atomar nach G16), eine allfällige verschlüsselte
  Arbeitsdatei entfernen, Schlüssel und Master-Secret aus dem Speicher werfen (G25).
- Die ChaCha20-Schicht nutzt **Poly1305** als Authentifizierung (AEAD): manipulierte
  Dateien werden beim Entschlüsseln erkannt, nicht nur stillschweigend falsch entpackt.

> **Hinweis zur Ehrlichkeit (Fassung N11.9):** Am Ruhezustand schützen **beide**
> Schichten (ChaCha20 außen, AES innen), `tasks.db.enc` enthält real beide. Während
> die App entsperrt läuft, existiert der Klartext ausschließlich flüchtig im RAM
> (SQLite-Page-Cache), wie bei jeder App; dagegen helfen schnelle Sperre, Auto-Sperre
> und Panik, nicht die Cipher. Ein echter gleichzeitiger Per-Page-Doppel-Cipher
> bräuchte einen eigenen Cipher-Treiber und wäre Over-Engineering.

**Punkt 3, die Schlüssel kommen aus deiner Passphrase und liegen nie auf der Platte.**
- Beim ersten Start legst du eine **Passphrase** fest (min. 12 Zeichen, N11.3).
- Aus der Passphrase **plus dem DPAPI-Pepper** (Punkt 4, Gate G18; die Passphrase
  wird vorab per `HKDF-Extract(salt=pepper, ikm=passphrase)` an den Pepper gebunden,
  verbindliche Konstruktion in G18, V2a) wird mit
  **Argon2id** (hohe Kosten: viel RAM + Zeit pro Versuch) und einem zufällig
  erzeugten, gespeicherten **Salt** genau **ein 32-Byte-Master-Secret** abgeleitet;
  daraus entstehen per **HKDF-SHA256 mit getrennten `info`-Labels** die beiden
  Schlüssel `aes_key` (Schicht 1) und `chacha_key` (Schicht 2). Domain-Separation,
  keine rohen Teilstücke des KDF-Outputs (Gate G15).
- Gespeichert werden **nur** Salt, Argon2-Parameter und Nonce (im
  `tasks.db.enc`-Header, Gate G16), **nie** die Passphrase, ein Passphrase-Hash
  oder die Schlüssel selbst. Ein gespeicherter Verifikations-Hash wäre ein
  Offline-Orakel; die Passphrase-Prüfung beim Entsperren läuft stattdessen
  **implizit über den Poly1305-Tag** der ChaCha20-Entschlüsselung (falsche
  Passphrase = AEAD-Fehler, Gate G15).
- `aes_key`/`chacha_key` und das Master-Secret existieren nur **im Arbeitsspeicher**,
  solange die App entsperrt ist. Beim Sperren/Panic werden sie verworfen (G25).

> Verbindliche Detail-Definitionen dazu: Gates **G15**, **G16** und **G18** im
> B.9-Nachtrag.

**Punkt 4, DPAPI-Pepper getrennt von der DB: keyring.**
Der zusätzliche 32-Byte-Pepper (Zweitfaktor der Schlüsselableitung, siehe G18) liegt
nicht in der DB, sondern im **Windows Credential Manager** (über `keyring`), ans
Benutzerkonto gebunden.

**Punkt 5, Ablauf zusammengefasst:**
```
App-Start → Lock-Screen → Passphrase eingeben
   → Argon2id(Passphrase + Pepper, Salt) → Master-Secret
   → HKDF-SHA256 (getrennte info-Labels) → aes_key + chacha_key
   → tasks.db.enc per ChaCha20-Poly1305 entpacken
     (Tag ok = Passphrase korrekt; Tag-Fehler = falsche Passphrase,
      es gibt keinen gespeicherten Hash zum Prüfen)
   → inneres SQLCipher-Image mit aes_key öffnen
     (bevorzugt in-memory, G6; Fallback: verschlüsselte Arbeitsdatei, N11.9)
   → entsperrt, UI lädt
Sperren / Schließen / Panic
   → DB-Image per ChaCha20-Poly1305 → tasks.db.enc (atomar, G16)
   → allfällige verschlüsselte Arbeitsdatei entfernen (nie Klartext auf Platte, N11.9)
   → aes_key, chacha_key, Master-Secret, Klartext-Cache aus dem Speicher werfen (G25)
```

**Punkt 6, was das schützt (und was nicht):**
- *Geschützt:* Wer die Datei in die Finger bekommt (verlorener Laptop, Backup,
  Cloud-Ordner), sieht ohne Passphrase nur doppelt verschlüsselten Zufallsmüll.
- *Nicht magisch geschützt:* Während die App **entsperrt läuft**, sind die Daten im
  Speicher nutzbar, wie bei jeder App. Dagegen helfen die schnelle Sperre, die
  Panik-Sperre und Auto-Sperre bei Inaktivität.

**Alternative für Puristen (per Gate G6 inzwischen der gewählte Default; Präzisierung
im N11.9-Abschnitt unten in B.7):** statt Arbeitsdatei auf Platte die ganze (kleine) DB beim Entsperren in eine
**In-Memory-SQLite** (`:memory:`) laden und im Ruhezustand nur als ein einziges, doppelt
verschlüsseltes Blob ablegen. Dann existiert **nie** eine entschlüsselte Datei auf der
Platte, Preis: die ganze DB wird bei jeder Persistierung am Stück geschrieben (für ein
paar hundert Aufgaben unkritisch, aber ohne seitenweise Crash-Transaktionen auf der
Platte; Write-back-Politik siehe G17).

> Konkrete Bibliotheken in Phase 0 (`requirements.txt`); Umsetzung in Phase 1 (Schicht 1
> beim DB-Öffnen) und Phase 8 (Argon2, Schicht 2 / Wrap-Unwrap, Lock, Panic).

> **Beide Schichten sind Pflicht.** AES-256 **und** ChaCha20-Poly1305 werden immer
> gebaut, es gibt keinen Modus ohne die zweite Schicht. Die „Alternative für Puristen"
> oben betrifft nur das *Wo* des entsperrten Arbeitsstands (Arbeitsspeicher vs.
> verschlüsselte Arbeitsdatei, N11.9), **nicht** ob die ChaCha20-Schicht existiert.

#### Verschluesselung praezisiert: Arbeitskopie, Write-back, Gate G28 (Etikett N11.9, 2026-07-09) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.9 Phase 8: Verschluesselung, beide Schichten bleiben Pflicht“. Register: Anhang 1.)*

*Loest den Konflikt Gate G6 (In-Memory, nie eine entschluesselte Datei auf der Platte)
vs. B.7 (beide Schichten immer am Ruhezustand). Ersetzt die B.7-Ehrlichkeits-Notiz und
praezisiert die "Alternative fuer Puristen".*

- **Am Ruhezustand liegt weiterhin genau ein Artefakt:** `tasks.db.enc` = ChaCha20-
  Poly1305( SQLCipher-AES-256-Datenbank-Image ). **Beide Schichten sind darin real
  vorhanden** (innerer Blob AES, aeussere Huelle ChaCha20). B.7 bleibt voll erfuellt.
- **Die Arbeitskopie beim Entsperren ist NIE eine Klartext-Datei.** Bevorzugt in-memory
  (`:memory:`, G6). Gibt die gewaehlte SQLCipher-Build-Variante das verlaessliche
  Serialisieren des verschluesselten Images aus `:memory:` nicht her, ist der
  verbindliche Fallback eine **SQLCipher-verschluesselte** Arbeitsdatei in einem
  ACL-beschraenkten Temp-/RAM-Disk-Pfad. Diese Datei ist am Ruhezustand **AES-Chiffretext,
  kein Klartext** (SQLCipher entschluesselt Seiten nur in den RAM, auch Journal/WAL sind
  verschluesselt). G6s eigentliche Sorge (Klartext-Temp-Forensik auf SSD) ist damit
  gegenstandslos: selbst wenn Secure-Delete auf SSD versagt, bleibt nur Chiffretext.
  Die Wahl "nie Klartext auf Platte" schlaegt im Zweifel die Wahl "unbedingt reines
  `:memory:`", weil das Sicherheitsziel so oder so erreicht ist.
- **G17-Write-back ist in BEIDEN Varianten identisch (U19), damit hier nichts
  geraten wird.** Persistenzziel am Ruhezustand ist **immer** `tasks.db.enc`, auch im
  Fallback-Modus: der G17-Debounce (ca. 3 s nach der letzten Aenderung, spaetestens
  alle 30 s, U20) schreibt in beiden Faellen das gesamte `tasks.db.enc` neu
  (`.tmp` + `fsync` + `os.replace`, eine `.bak`-Generation, G16). Die
  SQLCipher-Arbeitsdatei des Fallbacks ist **kein** zweites Persistenzziel und **nie**
  die Quelle der Wahrheit am Ruhezustand, sondern ein **reines Betriebsmittel**: sie
  wird beim Entsperren frisch aus `tasks.db.enc` erzeugt, bei Lock/Panik/Quit
  abgebaut (Teardown N11.11) und beim Start **kommentarlos geloescht/ersetzt**, falls
  eine verwaiste (evtl. veraltete) Kopie eines Absturzes herumliegt. **Keine
  Crash-Recovery aus der Arbeitsdatei:** nach einem Absturz wird sie **verworfen**, nie
  gelesen; der Wiederherstellungsstand ist ausschliesslich das zuletzt debounced
  geschriebene `tasks.db.enc` (bzw. dessen `.bak`, G16). Damit gilt G17 in beiden
  Modi woertlich und es gibt keinen Pfad, auf dem ein moeglicherweise verfaelschtes
  Betriebsmittel als Wahrheit durchgeht (pro Sicherheit: nur das authentifizierte
  `.enc` ist Quelle).
- **Ehrliche Neuformulierung (ersetzt die B.7-Notiz "live nur AES"):** Am Ruhezustand
  schuetzen **beide** Schichten. Waehrend die App entsperrt laeuft, existiert der
  Klartext ausschliesslich fluechtig im RAM (SQLite-Page-Cache), wie bei jeder App;
  dagegen helfen schnelle Sperre, Auto-Sperre und Panik, nicht die Cipher.
- **Neues Pflicht-Gate G28 (Verschluesselungs-Beweis, Phase 8):** Vor Phase-8-Abschluss
  ist zu **beweisen**, dass die Arbeits-/Zwischendatei tatsaechlich AES-verschluesselt
  ist: das Oeffnen des inneren Images **ohne** `aes_key` muss fehlschlagen (kein
  SQLite-Klartext-Header, kein lesbarer Task-Text im Roh-Byte-Dump). Schlaegt der Beweis
  fuer den `:memory:`-Serialize-Weg fehl, ist der verschluesselte-Temp-Datei-Fallback
  verbindlich. Kein Auslieferungsbuild ohne bestandenen Beweis. **Automatisierung
  (V12, 2026-07-15):** der Beweis ist als pytest-Test in der Phase-9-Testliste
  verankert (Scan des Arbeits-Artefakts auf den SQLite-Klartext-Header
  `SQLite format 3` und einen bekannten Task-String, jeder Fund ist ein Fail),
  damit er nicht als Einmal-Handgriff verrottet.

#### Dateiformat von `tasks.db.enc` + atomares Schreiben (Etikett G16) [Sec]

*(Wortgleich hierher gezogen in Umbau-Etappe 6 aus der G16-Zeile der B.9-Gate-Tabelle; Status, Stand und Pruefweg des Gates stehen weiter in B.9.)*

**Dateiformat von `tasks.db.enc` + atomares Schreiben.** Header: Magic `NOA1` (4 Byte),
Formatversion (1 Byte), Argon2id-Parameter `memory_cost`/`time_cost`/`parallelism` (je u32
little-endian), Salt (16 Byte), Nonce (12 Byte); danach der ChaCha20-Poly1305-Ciphertext. Bei
**jedem** Verschlüsseln eine frische Nonce aus `os.urandom(12)`; eine wiederverwendete Nonce
bricht die AEAD-Sicherheit vollständig. Schreiben **immer** atomar: erst `tasks.db.enc.tmp`
schreiben, `flush()` + `os.fsync()`, bestehende Datei nach `tasks.db.enc.bak` rotieren (genau
eine Generation behalten), dann `os.replace()`. Ein Absturz mitten im Sperren darf nie die
einzige Kopie der Daten zerstören. **Ergänzungen V1 (2026-07-15):** (1) Der **komplette Header
geht als `associated_data`** in `ChaCha20Poly1305.encrypt/decrypt` ein: jede Header-Manipulation
(auch heruntergedrehte Argon2-Parameter oder eine getauschte Formatversion, sprich
Format-Downgrade) wird damit zum sauberen AEAD-Fehler statt still wirksam. (2) Das frisch
geschriebene `.tmp` wird **vor** der `.bak`-Rotation einmal **probeweise entschlüsselt** (Header
parsen + AEAD-Tag prüfen); erst nach Erfolg wird rotiert, sonst können zwei fehlerhafte
Schreibzyklen nacheinander beide Generationen zerstören. (3) **Freier Plattenplatz wird vor dem
Wrap geprüft** (mindestens Ciphertext-Größe plus Reserve); reicht er nicht, bleibt der alte
Stand unangetastet und nach vorn geht der Code `vault`. (4) Die zufällige 12-Byte-Nonce aus
`os.urandom(12)` ist bei dieser Schreibfrequenz (debounced Write-back, G17) **geprüft
unbedenklich**, kein Zähler-Schema nötig.

#### Konkrete Argon2id-Parameter und der MemoryError-Randfall (Etikett N11.4.3, U17-Entscheid 2026-07-15) [Sec]

*(Wortgleich umgezogen in Umbau-Etappe 3. Register: Anhang 1.)*

*Loest U17. G8 nannte bisher nur Spannen ("Memory >= 256 bis 512 MB, time_cost >= 3,
parallelism passend"); in den G16-Header muessen aber feste Zahlen, sonst raet die
umsetzende Seite. Zusaetzlich kann eine zu grosse Speicher-Allokation auf einer
RAM-knappen Maschine scheitern, und weil der Tresor per Pepper genau an diesen PC
gebunden ist (G18), waere er dort dann nicht zu oeffnen; ein `MemoryError` mitten im
Entsperren darf weder als "falsche Passphrase" erscheinen noch die App abstuerzen
lassen. Im Zweifel pro Sicherheit, wobei **Verfuegbarkeit** (kein dauerhafter
Selbst-Aussperr, kein Datenverlust) hier ausdruecklich als Sicherheitsziel zaehlt.*

- **Fest verdrahtete Soll-Parameter (der einzige Wahrheitswert; G8 wird damit konkret):**
  - Typ **Argon2id**, Version **0x13** (Argon2 v1.3),
  - `memory_cost = 262144` KiB (**256 MiB**),
  - `time_cost = 3`,
  - `parallelism = 4`,
  - `hash_len = 32` (das eine Master-Secret; die Aufteilung in `aes_key`/`chacha_key`
    macht danach HKDF, G15),
  - `salt = 16` Byte, pro Tresor zufaellig, im Header (G16).

  **Warum 256 MiB und nicht 512:** Der Tresor ist per DPAPI-Pepper an dieses
  Windows-Konto gebunden (G18); ein Angreifer ohne das Konto kann die gestohlene Datei
  gar nicht offline angreifen, gegen ihn wirkt der Pepper, nicht die Argon2-Speichermenge.
  Der Zugewinn von 512 gegenueber 256 MiB (Faktor 2 an Offline-Kosten) ist damit gering,
  das Aussperr-Risiko aus genau diesem Befund dagegen real. 256 MiB liegt weit ueber den
  OWASP-Mindestwerten, allokiert auf jeder modernen Windows-Maschine zuverlaessig und wird
  nur **einmal** gebraucht (beide Schluessel stammen aus demselben Argon2-Durchlauf).
  Verfuegbarkeit zaehlt hier als Sicherheitsziel: ein dauerhaft nicht mehr zu oeffnender
  Tresor ist ein Datenverlust, kein Schutz.

- **Die Parameter stehen im `.enc`-Header (G16) und werden authentifiziert (V1).** Der
  Header (Magic, Version, Typ, `memory_cost`, `time_cost`, `parallelism`, `hash_len`,
  Salt, Nonce) geht als `associated_data` in ChaCha20-Poly1305 ein; eine nachtraegliche
  Manipulation der Parameter macht die Entschluesselung zum sauberen AEAD-Fehler. Der
  Header ist bauartbedingt nicht geheim (er enthaelt nie Schluesselmaterial).

- **Akzeptanzbereich gegen einen aufgeblaehten Header (DoS-Schutz, pro Sicherheit).** Die
  KDF-Parameter werden **vor** der Allokation gegen einen festen Bereich geprueft:
  `memory_cost` in **64 MiB bis 512 MiB**, `time_cost` **1 bis 10**, `parallelism`
  **1 bis 16**, `hash_len == 32`, Version `0x13`, Typ Argon2id. Liegt ein Wert
  ausserhalb, gilt der Kopf als **unlesbar** im Sinne von N6 Schritt 2 (B.2): Rueckgabe `vault`
  (Fehlerbildschirm), **kein** Argon2-Lauf, **kein** Rateversuch. Ohne diese Klammer
  koennte ein manipulierter Header (z.B. `memory_cost = 16 GiB`) beim naechsten Entsperren
  eine garantierte Speicher-Erschoepfung erzwingen; die AEAD-Pruefung liefe erst **nach**
  Argon2 und kaeme zu spaet. Die Obergrenze 512 MiB ist zugleich die Kappe fuer den
  Schaden eines solchen Versuchs und wird nur zusammen mit dem Default angehoben. (Ein
  nach unten manipulierter Header liefe ohnehin in den AEAD-Fehler, weil ein anderer
  Schluessel entstuende; die Untergrenze ist Guertel-und-Hosentraeger und faengt
  zusaetzlich Korruption ab.)

- **`MemoryError` im Normalfall (korrekte Parameter, Maschine momentan zu knapp) ist ein
  eigener Zustand, nie "falsche Passphrase".** Die Argon2-Ableitung in `unlock()`,
  `create_vault()` und `change_passphrase()` wird in `try/except` gegen `MemoryError` (und
  die entsprechende Allokations-Ausnahme von `argon2-cffi`) gekapselt, **vor** der
  generischen `internal`-Auffanglinie des `@bridge`-Decorators. Bei Ausloesung:
  - **kein Absturz** der App; die laufende Sitzung bleibt intakt (bei `unlock` bleibt die
    App gesperrt, bei `change_passphrase` unveraendert entsperrt, bei `create_vault` im
    Onboarding-Schritt);
  - Rueckgabe des **neuen Fehlercodes `memory`** (B.2), nicht `passphrase`, nicht
    `internal`, nicht `vault`;
  - **die Rate-Limit-Leiter (N11.4) wird nicht vorangetrieben**: ein Speicher-Engpass ist
    kein Rateversuch, sonst sperrte sich der rechtmaessige Nutzer unter Speicherdruck
    selbst in die Eskalations-Leiter (wieder ein Verfuegbarkeits-Schaden);
  - kein Schluesselmaterial und keine Tresor-Datei werden angefasst; eine etwaige
    Teil-Allokation wird freigegeben.

- **Frontend-Verhalten von `memory`:** inline im jeweiligen Auth-Screen (Lock-Screen bzw.
  Onboarding-/Passphrase-aendern-Dialog), Text "Not enough memory. Close other apps and
  try again.", mit Wiederholen-Moeglichkeit; **kein** Shake (es ist keine falsche
  Passphrase), **kein** Reset-Angebot (der Tresor ist intakt, ein Reset waere hier ein
  grundloser Datenverlust), **kein** Countdown. Nach dem Freigeben von Speicher fuehrt
  derselbe Versuch normal zum Ziel.

- **Anhebung nur ueber den Passphrase-Wechsel (N11.3 (d)).** Aeltere, niedrigere
  Header-Werte werden nicht automatisch migriert; der KDF-Upgrade-Pfad aus N11.3 (d) in B.2 hebt
  sie beim naechsten Passphrase-Wechsel auf den dann geltenden Soll-Stand. Wird der Default
  je erhoeht, wandert die Akzeptanz-Obergrenze im selben Build mit.

### B.8 Sperr-, Auto-Sperr- und Beenden-Politik: wann die Passphrase verlangt wird

#### B.8.1 Was sperrt, was nicht

*(Zusammengefuehrt in Umbau-Etappe 3: der bisherige B.8-Kopf (Ausloeser-Tabelle, Kernregel) und die Win+L-Regel; die N11.8.4-Entscheidung dazu steht als Historie in Anhang 3. Register: Anhang 1.)*

Die App ist **entweder entsperrt** (Schlüssel im Speicher, UI nutzbar) **oder gesperrt**
(Lock-Screen, DB zu, Schlüssel verworfen). Genau diese Ereignisse lösen eine **Sperre**
aus, sodass danach die **Passphrase neu eingegeben** werden muss:

| Ereignis | Verhalten |
|---|---|
| Klick auf **Lock**-Button (oder `Ctrl+L`) | sofort sperren, davor Raum-Bereinigung wie bei Panik (Ansicht leeren, In-Memory-Zustand verwerfen); **N11.10 gilt vorrangig: die Sperre schaltet NICHT mehr offline, der Online-/Funkzustand bleibt unangetastet**; es wird **nichts gelöscht** |
| **Emergency/Panic** (nur per Maus über den Rail-Knopf, bewusst ohne Tastenkürzel, N5) | Raum-Bereinigung + offline; endet im Panik-Endschirm (Finish/Killswitch, N10), nicht mehr im Lock-Screen |
| **App-Neustart** (Prozess war beendet) | startet immer im Lock-Screen |
| **Auto-Sperre nach Inaktivität** *(Timeout einstellbar, Default 15 min, `0` = nie; N11.4)* | sperren |

**Ausdrücklich KEINE Sperre** bei:
- **Minimieren** und wieder Öffnen des App-Fensters,
- Fokus-Wechsel zu einer anderen App (App nur im Hintergrund),
- Verschieben/Größe ändern des Fensters,
- **Windows-Sitzungssperre (Win+L)**: sie tut für NoaToDo **nichts** (N11.8.4). Wer den
  PC sperrt, sperrt damit nicht die App; die Auto-Sperre nach Inaktivität greift trotzdem,
  denn ihr Hintergrund-Timer läuft auch bei gesperrtem PC weiter.

> Kernregel: Eine Sperre passiert nur bei **explizitem Sperren**, bei **abgelaufener
> Auto-Sperre** und bei **echtem Prozess-Neustart**. Reines Fenster-Minimieren, ein
> Fokuswechsel und die Windows-Sitzungssperre sind *keine* Sperr-Ereignisse und lassen
> die App entsperrt.

**Keine Windows-Sperre-Erkennung (N11.8.4, verbindlich):** Es wird **kein** Session-Hook
gebaut (kein `WTSRegisterSessionNotification`, kein `WM_WTSSESSION_CHANGE`, kein
`WTS_SESSION_LOCK`-Handler), weder in `main.py` noch sonstwo. Die verlässliche Sperre ist
allein die Auto-Sperre nach Inaktivität (N11.4), umgesetzt als Hintergrund-Timer auf einer
monotonen Uhr, unabhängig von Fensterfokus und Windows-Sitzungszustand.


#### B.8.2 Verstärkte Sperre / Raum-Bereinigung

*(Zusammengefuehrt in Umbau-Etappe 3: die B.8-Verschaerfung vom 2026-07-08, N10.1 („Panik light“) und N11.10 (W1-Entscheid), wortgleich. Register: Anhang 1.)*

**Verschärfung (2026-07-08, verbindlich, Etikett N10):** Sperren ist jetzt
„Panik light". Jede Sperre bereinigt **zuerst den Raum** (Ansicht leeren, In-Memory-
Listen und Auswahl verwerfen, Menüs/Modals schließen; **das frühere „offline schalten"
ist durch N11.10 gestrichen, der Online-/Funkzustand bleibt beim Sperren unangetastet**),
erst dann
erscheint der Lock-Screen mit der Passwort-Pille. Dabei werden **nie** Daten gelöscht;
nach dem Entsperren lädt das Frontend den Zustand frisch per `get_state()`. Der
Lock-Screen trägt oben rechts einen **Off-Knopf**, der die App ohne Passphrase sauber
beendet (`quit_app()`); in Phase 8 wischt genau dieser Pfad zusätzlich alle lokalen
Spuren (G14/G25). Panik führt nicht mehr in den Lock-Screen zurück, sondern endet im
Endschirm mit Finish/Killswitch (N10).

**1. Lock wird verstärkt („Panik light").** Jede Sperre (Lock-Button, `Ctrl+L`,
später die Auto-Sperre nach Inaktivität; die Windows-Sitzungssperre sperrt nicht, N11.8.4)
macht zuerst das, was bisher nur Panik tat: Raum leeren (`state.lists` verwerfen, keine Liste offen, Menüs/Modals/Auswahl
schließen). **N11.10 gilt vorrangig: offline geschaltet wird beim Sperren NICHT mehr,
der Online-/Funkzustand bleibt exakt so, wie er gerade ist.** Erst dann erscheint der
bekannte Lock-Screen mit der Passwort-Pille. Es werden dabei **keine Daten gelöscht**:
das Backend bleibt die Wahrheit, nach dem Entsperren lädt das Frontend alles frisch per
`get_state()` und startet wie mit leerer Arbeitsfläche (Sidebar zu, keine Liste offen).
*(Der durch N11.10 gestrichene Alt-Wortlaut liegt wortgleich in Anhang 3,
Umbau-Etappe 5.)*

**Sperre schaltet nicht mehr offline (Etikett N11.10, 2026-07-13, W1-Entscheid) [Sec]**

*Loest den Widerspruch W1 der Plananalyse (N10.1 "jede Sperre schaltet offline, und
offline bleibt es" vs. N11.5 "beim Sperren wird der Funk-Zustand von vor dem App-Start
wiederhergestellt"). Entscheidung: Linie 1, entkoppeln. Ueberschreibt N10.1 (den
Offline-Teil), die B.8-Tabelle/Verschaerfung und die N11.5-Wiederherstellungsregel
fuer den Sperr-Fall.*

- **Die Sperre schaltet die App NICHT mehr offline.** Das gilt fuer **jede** Sperre:
  Lock-Button, `Ctrl+L` und Auto-Sperre nach Inaktivitaet (N11.4). Beim Sperren bleibt der
  Online-/Funkzustand **exakt so, wie er gerade ist**, in keiner Richtung angefasst:
  es wird **weder** der Flugmodus eingeschaltet **noch** ein frueherer Funk-Zustand
  wiederhergestellt. Das Internet bleibt normal verfuegbar; nach dem Entsperren gilt
  derselbe Zustand unveraendert weiter.
- **Begruendung:** Seit N11.5 heisst "offline" nicht mehr "lokales Flag", sondern echte
  Funkgeraete des ganzen PCs aus (WLAN, Bluetooth). Eine Sperre, die offline schaltet,
  wuerde mit dem Auto-Lock-Default (15 min Inaktivitaet) alle 15 Minuten das WLAN und
  Bluetooth des gesamten Rechners abschalten, etwa waehrend nebenan ein Video streamt.
  Die App hat seit der Sync-Entfernung zudem keinerlei eigene Netzwerkfunktion mehr,
  das Offline-Schalten beim Sperren schuetzt also nichts App-eigenes.
- **Die Raum-Bereinigung beim Sperren bleibt vollstaendig erhalten** (N10.1: Ansicht
  leeren, `state.lists` verwerfen, Menues/Modals/Auswahl schliessen, dann Lock-Screen).
  Es entfaellt **nur** der Offline-Schritt.
- **Funk geschaltet wird nur noch an zwei Stellen:** (1) beim **expliziten
  Nutzer-Toggle** (Flugzeug/Globus-Pill bzw. Taste `G`, N11.5) und (2) im
  **Panik-Flow** (bewusste, mehrstufig bestaetigte Notfall-Aktion; dort bleibt das
  Offline-Schalten wie in N10.3 beschrieben). Die Wiederherstellung des Funk-Zustands
  von vor dem App-Start passiert **nur noch beim Beenden** (als letzter Schritt,
  N11.5), nie beim Sperren.
- **Crash-Fall (Praezisierung aus dem W1-Entscheid):** Stuerzt die App ab, bleibt der
  Funk ehrlich so geschaltet, wie er zuletzt war (die Wiederherstellung laeuft nur im
  sauberen Beenden-Pfad). Damit das nicht dauerhaft haengen bleibt, wird der gemerkte
  Funk-Ausgangszustand beim Einschalten des Flugmodus durch die App in `config.json`
  persistiert (N11.3, nicht nur im RAM); findet der naechste Start dort einen nicht
  aufgeraeumten Eintrag, stellt er den Ausgangszustand wieder her und loescht den
  Eintrag.
- **Umsetzungsfolge fuer den heutigen Code:** `clearWorkspace()` in `app.js` schaltet
  derzeit auch offline. Kuenftig darf der **Lock-Pfad** (`doLock()`, Auto-Lock)
  den Online-Zustand nicht mehr anfassen; nur der **Panik-Flow**
  (Confirm im Panik-Panel) behaelt das Offline-Schalten.


#### B.8.3 Auto-Sperre: Definition der Inaktivität

*(Zusammengefuehrt in Umbau-Etappe 3 aus N11.4 (Auto-Sperre-Teil) und N11.4.2 (U4-Entscheid), wortgleich. Register: Anhang 1.)*

- **Auto-Sperre nach Inaktivitaet: einstellbar, Default 15 min.** Presets in den
  Einstellungen (z.B. 1/5/15/30/60 min) plus "nie" zum Abschalten. Konkretisiert B.8.

**Was „Inaktivitaet“ der Auto-Sperre heisst (Etikett N11.4.2, 2026-07-15, U4-Entscheid) [Sec]**

*Loest U4 der Plananalyse: "Inaktivitaet" war undefiniert. Nur Bridge-Aufrufe zu zaehlen
waere falsch (15 Minuten eine Liste **lesen** ohne Klick spraeche die Sperre mitten im
Gebrauch aus); die globale System-Idle-Zeit (GetLastInputInfo) waere das andere Extrem
(die App sperrte nie, solange irgendwo auf dem PC getippt wird, auch wenn NoaToDo
stundenlang unberuehrt offen liegt: genau das Szenario, das N11.8.4 absichern will). Im
Zweifel gilt hier durchweg die sicherere Richtung.*

- **Aktivitaet = Eingabe-Ereignisse im DOM des App-Fensters:** Maus-Bewegung/Klick,
  Tastatur, Wheel/Scroll, Touch. **Nicht** die globale System-Idle-Zeit, **nicht** allein
  Bridge-Aufrufe. Ein Fenster ohne Fokus bekommt keine solchen Ereignisse, also haelt ein
  im Hintergrund liegendes NoaToDo sich **nicht** selbst wach.
- **Meldung gedrosselt ueber `activity_ping()`.** Das Frontend meldet Aktivitaet mit einer
  fuehrenden Flanke (das erste Ereignis feuert sofort), danach **hoechstens alle 30 s** ein
  weiterer Ping. Die Drosselung meldet nur *unter*, verschiebt die Sperre also nie nach
  hinten, hoechstens (um bis zu die Drossel-Spanne) nach **vorn**. Das ist die gewollte
  Richtung; der kuerzeste Preset (1 min) sperrt damit im Zweifel etwas frueher, nie
  spaeter.
- **Der Backend-Timer ist die alleinige Autoritaet und fail-safe.** Ein Hintergrund-Timer
  (monotone Uhr `time.monotonic()`, eigener Thread, N11.8.4) tickt (z.B. jede Sekunde) und
  ruft bei `now - last_activity > timeout` die gemeinsame `teardown(reason='autolock')`
  (N11.11). `activity_ping()` setzt **nur** `last_activity` auf die **Backend**-Uhr; es
  nimmt **keinen** Zeitwert vom Frontend entgegen (dessen Uhr ist ungeprueft), kann
  `last_activity` **nie in die Zukunft** setzen und den Timer **nicht** abschalten.
  Bleiben die Pings aus, weil das Frontend haengt, abstuerzt oder per XSS stillgelegt
  wird, sperrt die App. **Das Frontend kann die Sperre nur *aufschieben*, nie
  *verhindern*.** Genau diese Richtung ist gewollt.
- **Nur `activity_ping` zaehlt.** **Kein** anderer Bridge-Aufruf setzt den Timer zurueck.
  Ein Hintergrund-Poll (z.B. `get_wifi_signal()` alle paar Sekunden fuer das Rail-Icon)
  haelt die App also **nicht** wach; nur echte Nutzer-Eingabe tut das.
- **Kein Lese-Ausnahme.** 15 Minuten eine Liste lesen ohne jede Eingabe fuehrt zur Sperre.
  Bewusst so, zugunsten der Sicherheit.
- **Gesperrt kein Ping.** `activity_ping` steht **nicht** in `ALLOWED_WHEN_LOCKED` (G13):
  gesperrt liefert es `locked` und ruehrt `last_activity` nicht an. Eine gesperrte App
  laesst sich so nicht "wachhalten".
- **Initialisierung.** `last_activity` wird beim Entsperren bzw. Tresor-Oeffnen auf jetzt
  gesetzt; eine frisch entsperrte, danach unberuehrte App sperrt nach Ablauf des Timeouts.
- **`autoLock = 0` (nie).** Der Timer ist dann aus; es sperren nur noch Lock-Button /
  `Ctrl+L`, die Panik und der **Prozess-Neustart** (der immer gesperrt startet, B.8).
  "Nie" heisst also nicht "nie eine Sperre".
- **Setting-Aenderung greift live.** Ein kleinerer Timeout wird beim naechsten Tick gegen
  das bestehende `last_activity` geprueft und kann sofort sperren (sichere Richtung).
- **Offener nativer Dialog ist keine Aktivitaet (Verweis N11.11.5, Punkt 6).** Der Timer
  laeuft weiter, die Ping-Schleife ruht solange; feuert die Sperre bei offenem Dialog,
  gilt die aufgeteilte Sequenz aus N11.11.5.
- **Ehrliche Einordnung.** `activity_ping` ist **keine** Sicherheitsgrenze gegen ein
  *kompromittiertes* Frontend (XSS = RCE per Sicherheitsmodell; dann hat der Angreifer
  ohnehin `pywebview.api.*`-Vollzugriff). Die Sperr-Garantie kommt allein aus dem
  autoritativen, fail-safe Backend-Timer; der Ping regelt nur die **Bequemlichkeit**
  (nicht mitten im aktiven Gebrauch sperren).


#### B.8.4 Entsperr-Rate-Limit und seine Persistenz

*(Zusammengefuehrt in Umbau-Etappe 3 aus N11.4 (Rate-Limit-Teil) und N11.4.1 (U6-Entscheid), wortgleich. Register: Anhang 1.)*

- **Rate-Limit bei falscher Passphrase (konkret):**
  - Nach **jedem** Fehlversuch 2 s Zwangspause bis zum naechsten Versuch.
  - **3 freie Versuche**, dann greift die Eskalations-Leiter.
  - **Leiter:** 10 s, 30 s, 1 min, 5 min, 15 min, 30 min, 1 h, 5 h, 10 h (danach bleibt
    es bei 10 h).
  - **Jede Stufe erlaubt 2 Fehlversuche**, bevor auf die naechste (laengere) Stufe
    hochgeschaltet wird.
  - Gilt zusaetzlich zur ohnehin langsamen Argon2id-Ableitung (G8). Anzeige gemaess N4 (B.4)
    ("try again in ...").

**Der Rate-Limit-Zustand wird persistiert (Etikett N11.4.1, 2026-07-13, U6-Entscheid) [Sec]**

*Loest U6 der Plananalyse: Die Leiter lag bisher nur im RAM. Der Lock-Screen hat einen
prominenten Off-Knopf, also braucht ein Rater genau zwei Klicks (beenden, neu starten),
um jede Sperrzeit zu loeschen; die Leiter war damit wirkungslos. Zugleich ist die Wanduhr
manipulierbar (Systemzeit vorstellen) und die monotone Uhr ueberlebt keinen Neustart.*

- **Persistiert wird `{fails, stage, next_try_at, locked_at, duration}`** in `config.json`
  (unverschluesselt, ausserhalb des Tresors, denn er ist beim Entsperren ja gerade zu;
  das exakte Gesamt-Schema der Datei steht in N11.15.1 (B.11), Befund U2 erledigt). Der Zustand
  ueberlebt Beenden und Neustart: Wer im 30-min-Riegel steckt und die App neu startet,
  steckt weiter im 30-min-Riegel. Die App enthaelt **keinen** Weg, den Zustand aus der
  UI zu loeschen.
- **Zurueckgesetzt wird nur durch Erfolg:** Ein erfolgreiches `unlock()` setzt
  `fails = 0`, `stage = 0` und loescht `next_try_at`. Auch der `reset_vault()`-Weg
  raeumt ihn auf (er loescht ohnehin alles, N11.11 Schritt 8).
- **Uhrbasis, zwei Uhren, bewusst getrennt:**
  - **Innerhalb einer Sitzung** zaehlt die **monotone** Uhr (`time.monotonic()`); sie ist
    gegen jedes Verstellen der Systemzeit immun.
  - **Ueber einen Neustart hinweg** gibt es nur die Wanduhr: `next_try_at` und
    `locked_at` werden als UTC-Zeitstempel geschrieben, dazu die `duration` der laufenden
    Stufe.
  - **Rueckwaerts-Sprung-Regel:** Ist beim Start `jetzt < locked_at` (die Systemuhr wurde
    zurueckgestellt) oder fehlen/widersprechen sich die Werte, wird die laufende Sperrzeit
    **komplett neu gestartet** (`locked_at = jetzt`, `next_try_at = jetzt + duration`),
    nicht etwa verkuerzt. Im Zweifel immer zugunsten der Sperre. Ein Vorwaerts-Sprung
    (Uhr vorstellen) laesst die Sperre ablaufen; das ist hingenommen, siehe die
    Ehrlichkeits-Notiz unten.
  - Fehlt oder ist `config.json` unlesbar, gilt der Zustand als "voll gesperrt auf der
    zuletzt bekannten Stufe" nur, wenn die Datei existiert und kaputt ist; fehlt sie ganz
    (frischer Rechner), ist das ein Erststart und es gibt nichts zu bremsen (die genaue
    Fehlerbehandlung der Datei steht in N11.15.2 (B.11): kaputte Datei nach `config.json.bad`,
    Fehlerbildschirm, danach frische, leere Leiter).
- **Reihenfolge: erst zaehlen und schreiben, dann pruefen (pro Sicherheit).** Ein
  Fehlversuch wird gezaehlt (`fails += 1`, Stufe/`duration`/`next_try_at`/`locked_at` neu)
  und `config.json` wird **synchron und atomar (N11.15.1) geschrieben, BEVOR** die teure
  Argon2id-Ableitung und die AEAD-Pruefung ueberhaupt starten und **bevor** irgendeine
  Antwort ans Frontend geht. Sonst gaebe es denselben billigen Ausweg wie ueber den
  Off-Knopf: Versuch schicken, den Prozess toeten, solange die Pruefung noch laeuft, und der
  Fehlschlag landet nie auf Platte. Nur ein **erfolgreiches** `unlock()` setzt anschliessend
  zurueck; jeder andere Ausgang (falsch, Absturz, Kill, Stromausfall) laesst den bereits
  erhoehten Stand stehen.
- **Eine deterministische Stufenfunktion, ein Codepfad.** Aus `fails` allein ergeben sich
  Stufe, `duration` und `next_try_at` durch **eine** reine Funktion, die im laufenden Betrieb
  und beim Start (aus dem persistierten `fails`) identisch rechnet, damit kein Pfad die Leiter
  anders auslegt: die ersten 3 Fehlversuche sind frei (nur die 2-s-Pause aus N11.4), ab dem 4.
  greift die Leiter, und **je 2 weitere Fehlversuche** schalten eine Stufe hoch (Fehlversuch
  4-5 -> 10 s, 6-7 -> 30 s, 8-9 -> 1 min, ... bis 10 h, dann Deckel). `stage` ist damit nur
  eine redundante, bequeme Spiegelung von `fails`; widersprechen sich beide in einer geladenen
  Datei, gilt der **hoehere** Wert (im Zweifel zugunsten der Sperre).
- **Innerhalb der Sitzung die laengere Restzeit (pro Sicherheit).** Solange die App laeuft,
  existieren beide Uhren; die noch zu wartende Sperrzeit ist `max(monoton abgeleitet, aus der
  Wanduhr abgeleitet)`, nie die kuerzere. So verkuerzt weder ein Vorstellen der Systemuhr noch
  ein Eingriff an der monotonen Uhr die Wartezeit. (Der reine Neustart-Fall, in dem nur die
  Wanduhr vorliegt, bleibt wie oben geregelt: Rueckwaerts-Sprung -> Sperre komplett neu.)
- **Ehrliche Einordnung (gehoert ins Bedrohungsmodell, K3):** Die Leiter bremst den
  **beilaeufigen Rater am Geraet** (Mitbewohner, Kollege, die zehn Minuten Zeit haben).
  Sie ist **kein** Schutz gegen den ernsthaften Angreifer: Der kopiert `tasks.db.enc` und
  raet **offline**, wo weder Leiter noch Auto-Sperre existieren. Dagegen stehen
  ausschliesslich die Argon2id-Kosten (G8) und der DPAPI-Pepper (G18). Ebenso ehrlich:
  Wer Dateizugriff hat, kann `config.json` loeschen und die Leiter zuruecksetzen, aber
  genau dieser Angreifer kopiert lieber gleich den Tresor und raet offline. Die Leiter
  wird deshalb nie als Schutz gegen K1 **verkauft**.


#### B.8.5 Die gemeinsame teardown(reason)-Sequenz

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.11 Die gemeinsame Sperr-/Beenden-Sequenz (2026-07-13, S5-Entscheid, Gate G35) [Sec]“ samt N11.11.1 bis N11.11.4. Register: Anhang 1.)*

*Loest Befund S5 der Plananalyse: die Ablaeufe Sperren, Beenden, Panik, Killswitch und
Reset waren ueber fuenf Stellen verstreut (B.8, N10, N11.5, N11.8.1/N11.8.3, Phase 8
Punkt 2) und nirgends als eine pruefbare Sequenz definiert; mehrere Schritte standen
ueberhaupt nirgends. Dieser Abschnitt ist ab sofort die **einzige Wahrheit** fuer alle
Ausgaenge und bindet zugleich U5, U21, V7 und V8 ein. Er praezisiert die genannten
Stellen, widerspricht ihnen aber nicht.*

##### N11.11.1 Eine Funktion, alle Ausgaenge

In `backend/security.py` entsteht **genau eine** Routine:

```python
def teardown(reason: Reason) -> None: ...
# Reason = "lock" | "autolock" | "quit" | "panic_finish" | "killswitch" | "reset" | "atexit"
```

**Alle** Ausgaenge rufen ausschliesslich sie, keiner baut seinen eigenen Ablauf:
Lock-Button/`Ctrl+L` (`lock`), Auto-Sperre (`autolock`), Off-Knopf des Lock-Screens
(`quit`), Panik-Endschirm "Finish" (`quit`), Killswitch-Ende (`killswitch`),
Lock-Screen-Reset (`reset`), **natives Fenster-X** (`quit`, per `closing`-Handler, siehe
Phase 8 Punkt 2) und die Rueckfalllinie `atexit`/`try…finally` um `webview.start()`
(`atexit`). Der Panik-Confirm selbst ist **kein** Ausgang: er raeumt den Raum, schaltet
offline (N11.10) und fuehrt in den Endschirm; erst dessen Knoepfe rufen `teardown`.

**Nicht verhandelbar:** Wer einen neuen Ausgang baut (neuer Knopf, neuer Hotkey, neues
Fenster-Ereignis), ruft `teardown`. Ein zweiter, handgeschriebener Beenden-Pfad ist ein
Gate-Verstoss (G35), auch wenn er "dasselbe" tut.

##### N11.11.2 Die Soll-Sequenz (verbindliche Reihenfolge)

`teardown(reason)` laeuft **immer** in dieser Reihenfolge; welche Schritte fuer welchen
Grund gelten, steht in der Tabelle in N11.11.3. Die Reihenfolge ist selbst
sicherheitsrelevant (Schritt 7 darf nie vor Schritt 5/6 laufen, U21; Schritt 10 ist
immer der letzte, N11.5).

1. **Eintritt absichern (Idempotenz).** Ein Prozess-weites Flag plus Lock: `teardown`
   laeuft **hoechstens einmal** durch. Ein zweiter Aufruf (X waehrend die Auto-Sperre
   schon laeuft, `atexit` nach `quit_app`) kehrt sofort zurueck oder wartet auf den
   laufenden Durchlauf. Ein `lock`, das ein `quit` ueberholt, wird verworfen: ein
   begonnenes Beenden gewinnt immer gegen ein begonnenes Sperren.
2. **Offene native Dialoge aufloesen (U5).** Ist ein nativer Dialog offen (Export-Save,
   Onboarding-Ordnerwahl), darf **nie** unter ihm das Hauptfenster abgebaut werden
   (N11.8.3). Kurzfassung der Regel: **jeder Grund ausser `autolock`** bricht den Dialog
   sofort ab (Cancel) und faehrt fort (der Nutzer steht davor, er hat es selbst
   ausgeloest); **`autolock`** laeuft trotzdem sofort bis Schritt 7 durch (die Daten
   werden gesichert, die Ansicht wird gesperrt) und schiebt **nur die nativen Schritte
   9 bis 11** auf, bis der Dialog zu ist, wobei die Sequenz den Dialog selbst
   schliesst, statt auf ihn zu warten. **Der vollstaendige Ablauf samt der
   Angriffsvektoren, die eine naive Aufschiebung erst erzeugen wuerde, steht in
   N11.11.5 (B.8.6); er ist Teil dieses Schrittes und nicht optional.**
3. **Eingaben einfrieren.** Backend setzt sofort `locked = True` (bzw. `shutting_down`),
   damit ab hier jede Bridge-Methode ausserhalb der G13-Allowlist `{"error": "locked"}`
   liefert und keine neue Mutation mehr hereinkommt. Frontend leert den Raum
   (`clearWorkspace()`: Listen, Auswahl, Menues, Modals, Eingaben; **ohne** den
   Online-Zustand anzufassen, N11.10).
4. **Timer stoppen und ausstehende Aenderungen synchron persistieren (G17).** Den
   Auto-Sperr-Timer und den **G17-Debounce-Timer abbrechen**; steht noch eine ungesicherte
   Aenderung an, wird sie **synchron** und **vor** allen weiteren Schritten nach
   `tasks.db.enc` geschrieben (atomar nach G16). `teardown` wartet auf den Abschluss, kein
   Feuern-und-Vergessen. Fuer `killswitch` und `reset` entfaellt dieser Schritt
   ersatzlos (die Daten werden ohnehin sofort geloescht; ein letzter Write-back waere
   sinnlose Schreiblast auf genau die Datei, die gleich stirbt). **Fehlerfall:** Scheitert
   das Schreiben bei `lock`/`autolock`/`quit`, bricht die Sequenz ab und zeigt den
   N6-Fehlerbildschirm; es wird **nicht** weitergewischt und **nicht** beendet (sonst
   kostet der Beenden-Pfad Daten). Die `.bak`-Generation aus G16 bleibt unangetastet.
5. **Clipboard sofort leeren (V7, G23).** Traegt das Windows-Clipboard noch App-Inhalt
   (dieselbe Pruefung "ist es noch unser Inhalt", die schon der 60-s-Auto-Clear nutzt),
   wird es **jetzt** geleert und der 60-s-Timer abgebrochen. Sonst laege bis zu eine
   Minute Aufgabentext im Clipboard, waehrend die App laengst gesperrt oder beendet ist.
   Fremder Inhalt (der Nutzer hat inzwischen etwas anderes kopiert) bleibt unangetastet.
6. **DB schliessen.** SQLCipher-Verbindung sauber schliessen, In-Memory-Image freigeben,
   eine allfaellige **verschluesselte** Arbeitsdatei (N11.9-Fallback) loeschen. Erst
   danach darf irgendetwas an Dateien angefasst werden (U21).
7. **Schluessel nullen (G25) und fluechtige RAM-Puffer verwerfen.** `aes_key`,
   `chacha_key`, Master-Secret und die RAM-Kopie des Pepper als `bytearray` ueberschreiben
   und verwerfen; die Passphrase ist ohnehin direkt nach der Ableitung verworfen. **Hier
   wird auch der Undo-Puffer der letzten geloeschten Liste (N11.2.1) verworfen**, damit eine
   gesperrte App nie geloeschten Aufgabentext im RAM haelt. Ab hier ist der Prozess
   schluessellos. Gilt auch fuer `lock`/`autolock`: eine Sperre ohne Schluessel-Nullen (und
   ohne Verwerfen dieses Puffers) waere keine.
8. **Nur `killswitch` und `reset`: loeschen.** Erst **nach** Schritt 6 und 7 (offene
   Handles, U21): `tasks.db.enc` samt `.bak` und Vault-Metadaten loeschen, den
   DPAPI-Pepper aus dem Credential Manager entfernen (`keyring.delete_password`, G18),
   den Vault-Eintrag in `config.json` (und den Rate-Limit-Zustand, U6) verwerfen. Der
   Killswitch ist ab Phase 8 eine reine **Datei**-Operation und braucht keine Schluessel
   (N11.8.1), funktioniert also gesperrt wie entsperrt; im entsperrten Zustand sorgen
   6 und 7 dafuer, dass er nicht gegen offene Handles laeuft. **Dokumentierter
   Nebeneffekt:** Mit dem Pepper sterben auch alle **frueher kopierten** `.enc`-Staende
   endgueltig, selbst wenn der Angreifer spaeter die Passphrase erfuehre (U21).
   Unterschied der beiden Gruende: `killswitch` beendet danach den Prozess (Schritte 9
   bis 11), `reset` beendet **nicht**, sondern springt in das Onboarding (Speicherort
   waehlen, neue Passphrase, frischer Pepper, N11.3) und die Sequenz endet hier.
9. **WebView2-Profil freigeben und sicher wischen (G14).** Die Haupt-Ansicht abbauen
   (das WebView2, das `PROFILE_DIR` offen haelt, schliessen), dann `PROFILE_DIR` sicher
   wischen. **`LOCK_PROFILE_DIR` wird nie gewischt** (inhaltsfrei, N11.8.3). Bei
   `lock`/`autolock` uebernimmt danach der Lock-Screen aus `LOCK_PROFILE_DIR`, und die
   Sequenz **endet hier** (Schritte 10 und 11 sind Beenden-Schritte). Gewischt wird immer
   der **real beschriebene** Pfad, nicht der literale: unter Store-Python liegt er
   umgeleitet unter `...\Packages\PythonSoftwareFoundation.Python.3.11_*\LocalCache\Local\`
   (V8).
10. **Funk-Zustand wiederherstellen (N11.5/N11.10), als letzter fachlicher Schritt.** Nur
    auf den Beenden-Gruenden (`quit`, `killswitch`, `atexit`): hat die App den Flugmodus
    eingeschaltet, wird der beim Start gemerkte Zustand wiederhergestellt und der
    Merker in `config.json` geloescht. **Beim Sperren passiert hier nichts** (N11.10, die
    Sequenz ist da ohnehin schon beendet). Zuletzt, damit der Raum erst geraeumt ist,
    bevor die Funkgeraete wieder angehen.
11. **Prozess-Ende.** Single-Instance-Mutex (G19) freigeben, verbleibende Handles
    schliessen, WinForms-Form ueber `BeginInvoke` auf dem UI-Thread schliessen, Prozess
    beenden.

**Fehlerregel fuer die Schritte 5 bis 11:** Sie laufen **best effort**. Scheitert einer
(Clipboard-API belegt, Profilordner gesperrt, Radio-API verweigert), wird er
uebersprungen und die Sequenz laeuft weiter; **nie** darf ein gescheiterter Schritt die
folgenden verhindern, sonst bleibt ausgerechnet im Fehlerfall der Schluessel im RAM oder
das Profil ungewischt. Einzige Ausnahme ist Schritt 4 (Datenverlust, siehe dort).

##### N11.11.3 Welcher Schritt gilt fuer welchen Ausgang

| Schritt | `lock` / `autolock` | `quit` (Off, Finish, Fenster-X) | `killswitch` | `reset` | `atexit` |
|---|---|---|---|---|---|
| 1 Idempotenz | ja | ja | ja | ja | ja |
| 2 Dialog aufloesen | `autolock`: Schritte 3-7 sofort, 9-11 aufgeschoben, Dialog wird geschlossen (N11.11.5) | Cancel | Cancel | Cancel | entfaellt |
| 3 Einfrieren | ja | ja | ja | ja | ja |
| 4 Debounce-Flush | ja | ja | **nein** | **nein** | ja (falls moeglich) |
| 5 Clipboard leeren | ja | ja | ja | ja | ja |
| 6 DB schliessen | ja | ja | ja (entsperrt) | ja (entsperrt) | ja |
| 7 Schluessel nullen | ja | ja | ja | ja | **ja (Pflicht)** |
| 8 Dateien/Pepper loeschen | nein | nein | **ja** | **ja** | nein |
| 9 `PROFILE_DIR` wischen | ja, dann Lock-Screen | ja | ja | ja | ja (falls moeglich) |
| 10 Funk wiederherstellen | **nein** (N11.10) | ja | ja | nein (App laeuft weiter) | ja |
| 11 Prozess-Ende | nein (Lock-Screen) | ja | ja | **nein** (Onboarding) | ja |

`atexit` ist die Rueckfalllinie fuer den Fall, dass der Message-Loop unerwartet
zurueckkehrt: Es laeuft dieselbe Funktion, aber nur noch, was ohne UI moeglich ist. Die
Pflichtschritte dort sind 5, 7, 10 und 11 (Clipboard, Schluessel, Funk, Mutex).

##### N11.11.4 Neues Pflicht-Gate G35

> **🔒 G35 (Phase 8), gemeinsame Sperr-/Beenden-Sequenz:** Es gibt **genau eine**
> `teardown(reason)`-Routine, und **jeder** Ausgang (Lock-Button, `Ctrl+L`, Auto-Sperre,
> Off-Knopf, Panik-Finish, Killswitch, Reset, natives Fenster-X, `atexit`) laeuft
> ausschliesslich durch sie, in der Reihenfolge aus N11.11.2. Abnahme: Fuer **jeden** der
> neun Ausgaenge ist nachzuweisen, dass (a) ein ausstehender G17-Debounce synchron
> geschrieben wurde (ausser Killswitch/Reset), (b) das Clipboard keinen App-Inhalt mehr
> traegt, (c) die Schluessel genullt sind, (d) `PROFILE_DIR` gewischt ist, (e) der
> Funk-Zustand nur auf den Beenden-Wegen und nur als letzter Schritt wiederhergestellt
> wurde, (f) der Mutex freigegeben ist. Ein zweiter, handgeschriebener Beenden-/Sperr-Pfad
> im Code ist ein Gate-Verstoss.
>
> **Ergaenzung (U5, siehe N11.11.5 in B.8.6):** Die Abnahme gilt zusaetzlich fuer den Fall
> "Auto-Sperre feuert, waehrend ein nativer Dialog offen ist". Nachzuweisen ist, dass
> dabei (g) das Hauptfenster **nicht** unter dem modalen Dialog abgebaut wird, (h) die
> Schluessel trotzdem sofort genullt sind, (i) der Dialog geschlossen und sein Ergebnis
> verworfen wird (keine Export-Datei entsteht nach dem Sperren) und (j) die Sperre sich
> durch einen offenen Dialog **nicht unbegrenzt hinausschieben** laesst.



##### Keine WebView2-Datenspuren auf der Platte (Etikett G14) [Sec]

*(Wortgleich hierher gezogen in Umbau-Etappe 6 aus der G14-Zeile der B.9-Gate-Tabelle; Status, Stand und Pruefweg des Gates stehen weiter in B.9.)*

**Keine WebView2-Datenspuren auf der Platte.** WebView2 legt einen User-Data-Ordner an (Cache,
localStorage, GPU-Cache); dort können gerenderte Task-Texte an beiden Verschlüsselungsschichten
vorbei landen. **Umgesetzter Stand (Pflicht, so bleiben):** **ein fester, benutzerprivater
Profilordner** statt Privatmodus, d.h. `webview.start(..., private_mode=False,
storage_path=PROFILE_DIR)` mit `PROFILE_DIR = %LOCALAPPDATA%\NoaToDo\webview`, **zwingend
zusammen mit dem Single-Instance-Mutex aus G19** (zwei Instanzen würden den geteilten Ordner
sperren/korrumpieren); `_cleanup_stale_webview_profiles()` räumt beim Start die alten
Temp-Profile weg. **`private_mode=True` ist ersatzlos gestrichen und darf nicht wieder eingebaut
werden:** der Privatmodus legte pro Start ein neues `%TEMP%\tmp...\EBWebView` an, das bei hartem
Beenden liegen blieb (real bis 55 Altlasten) und zusammen mit verwaisten `msedgewebview2.exe`
Starthänger über eine Minute verursachte. **Offen für Phase 8:** (a) `PROFILE_DIR` bei
`lock()`/`panic()`/sauberem Beenden **sicher wischen**, wobei das native Fenster-X ausdrücklich
als sauberes Beenden zählt und denselben Wisch-Pfad wie `quit_app()` durchlaufen muss; (b)
verwaiste `msedgewebview2.exe` (überleben einen harten Kill und sperren den Ordner, nächster
Start sonst `0x800700AA` ERROR_BUSY) vor dem Wischen beenden, dabei nur Prozesse mit
`PROFILE_DIR` als Arbeitsverzeichnis, nicht pauschal alle (andere Apps nutzen WebView2 auch);
(c) das Wischen mit Mutex und Lock-Lebenszyklus abstimmen (nicht wischen, solange WebView2 den
Ordner offen hält). **Entwarnung zur Vertraulichkeit:** Aufgabentexte erreichen keine
persistierbare WebView2-Fläche (kein localStorage/IndexedDB, keine Cookies, kein fetch/XHR; alle
Daten kommen über die In-Memory-Bridge ins DOM), im Profil liegt nur nicht-sensibler UI-Cache;
einziger Randfall ist ein WebView2-Crash-Dump mit DOM-Fragmenten, genau dagegen ist das Wischen
Pflicht. Das Frontend darf localStorage/sessionStorage/IndexedDB **nie** für Aufgabendaten
verwenden. **Store-Python-Redirect (V8, 2026-07-15; Volltext in N11.15.5, B.11):** unter
Microsoft-Store-Python wird `%LOCALAPPDATA%` real nach
`...\Packages\PythonSoftwareFoundation...\LocalCache\Local\NoaToDo\...` umgeleitet. Der Wisch
operiert deshalb **immer in-process auf dem effektiven Pfad** (die Python-API sieht die
Umleitung automatisch); externe Werkzeuge oder Anleitungen mit dem literalen Pfad verfehlen die
echten Daten. Und weil die Phase-9-`.exe` ohne Redirect läuft, bekommt Phase 9 einen
**einmaligen Erststart-Schritt**, der die bekannten alten Redirect-Pfade entfernt (nur den
umgeleiteten `NoaToDo\webview`-Ordner und eine dortige `config.json`; eine `tasks.db.enc` wird
dabei **niemals** angefasst), sonst bleibt der alte umgeleitete Profilordner für immer liegen.

#### B.8.6 Native Dialoge und die aufgeteilte Auto-Sperre

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.11.5 Native Dialoge und die aufgeschobene Auto-Sperre (2026-07-13, U5-Entscheid) [Sec]“ samt N11.11.5.1 bis N11.11.5.4. Register: Anhang 1.)*

*Loest U5 der Plananalyse. Native Dialoge (Export-Save-Dialog aus G21, Ordnerwahl im
Onboarding aus N11.3) sind die einzige Stelle, an der ein **modales Windows-Fenster** dem
Hauptfenster gehoert. Feuert die Auto-Sperre (N11.4, Default 15 min) genau dann, baut die
Sequenz in Schritt 9 die WebView-Ansicht unter einem noch offenen modalen Dialog ab: im
guenstigen Fall haengt die App, im ungueenstigen stuerzt sie ab und hinterlaesst genau den
Zustand, den die Sperre verhindern sollte (Schluessel im RAM eines abgestuerzten Prozesses,
ungewischtes `PROFILE_DIR`, WER-Dump, A1). Angreiferklasse: **K3** (kurzer physischer
Zugriff), siehe B.10.2.*

##### N11.11.5.1 Die naive Loesung waere ein neues Loch

Der naheliegende Patch ("Flag um `create_file_dialog`, Sperre aufschieben, nach dem
Schliessen nachholen") behebt den Absturz und **oeffnet dabei drei neue Wege**. Sie sind
hier benannt, weil genau diese Art von Folgeschaden die Regel aus B.10 verlangt, jede
Massnahme gegen ihre Angreiferklasse zu pruefen:

1. **Die Auto-Sperre laesst sich beliebig lange aushebeln (K3).** Ein offener Dialog wuerde
   die Sperre auf unbestimmte Zeit aufschieben. Wer kurz Zugriff auf den entsperrten
   Rechner hat, drueckt `Ctrl+E`, laesst den Save-Dialog offen stehen und geht: Die App
   sperrt **nie** wieder, und die Aufgaben stehen weiter sichtbar im Hauptfenster hinter
   dem Dialog. Damit waere ausgerechnet die einzige verlaessliche Sperre (N11.8.4) durch
   einen Mausklick abschaltbar. **Dasselbe passiert versehentlich:** Nutzer laesst den
   Dialog offen, klappt den Laptop zu, die App bleibt entsperrt.
2. **Ein Export, der nach dem Sperren noch schreibt.** Kehrt der Dialog nach der Sperre
   zurueck und die Sequenz nimmt sein Ergebnis noch entgegen, schreibt eine **gesperrte**
   App eine Klartext-Datei mit Aufgaben auf die Platte, an G13 vorbei (der Inhalt lag beim
   Aufruf schon im Speicher der Methode, der `locked`-Check des Decorators hat sie laengst
   durchgelassen).
3. **Das Flag als Dauerzustand.** Bleibt das Flag durch eine Ausnahme, einen abgestuerzten
   Dialog oder einen zweiten, parallel geoeffneten Dialog haengen, ist die Auto-Sperre
   dauerhaft tot, ohne dass es jemand merkt (der schlimmste Fehlerfall: ein Schutz, der
   still nicht mehr laeuft).

##### N11.11.5.2 Verbindliche Regel: nicht "aufschieben", sondern **aufteilen**

Der Kern der Loesung: **Gefaehrlich ist nur der native Teil der Sequenz, nicht die
Sperre selbst.** Schritte 3 bis 7 (einfrieren, Write-back, Clipboard, DB schliessen,
Schluessel nullen) sind reine Python-/DOM-Operationen und beruehren kein natives Fenster;
sie laufen problemlos, waehrend ein modaler Dialog offen ist. Nur die Schritte 9 bis 11
(WebView-Ansicht abbauen, `PROFILE_DIR` wischen, Form schliessen) duerfen das nicht.

Feuert `autolock` bei offenem Dialog, gilt daher:

1. **Sofort und ohne Aufschub laufen die Schritte 1 bis 7.** Nach wenigen Millisekunden
   ist die App gesperrt (`locked = True`, G13-Allowlist greift), der ausstehende
   Write-back ist geschrieben (G17/G16), das Clipboard ist geleert (V7), die DB ist zu
   und **die Schluessel sind genullt** (G25). Ab hier gibt es nichts mehr zu holen, egal
   wie lange der Dialog noch steht.
2. **Die Ansicht wird sofort zugemacht.** Das Frontend bekommt `onLocked()` und rendert
   `clearWorkspace()` plus Lock-Screen. Das ist reines DOM im schon laufenden WebView
   (`evaluate_js`), also **keine** native Fensteroperation; hinter dem Dialog steht damit
   der Lock-Screen und keine Aufgabenliste mehr. **Nachweispflicht in Phase 8:** dass
   `evaluate_js` waehrend eines offenen modalen Dialogs zuverlaessig durchkommt (der
   modale Dialog pumpt die Nachrichtenschleife weiter, gesendete Nachrichten laufen also;
   sollte es in der Praxis doch haengen, gilt Punkt 3 zuerst und die Ansicht wird erst
   danach umgestellt).
3. **Die Sequenz schliesst den Dialog selbst, sie wartet nicht auf ihn** (Antwort auf
   Angriffsvektor 1). Auf dem UI-Thread (nur dort, `_run_on_ui_thread`) wird der offene
   modale Dialog beendet (Best effort: `WM_CLOSE`/`EndDialog` an das Dialog-Fenster,
   ermittelt ueber das Besitzer-Fenster des Hauptformulars). Das entspricht einem "Abbrechen"
   und ist verlustfrei: der Nutzer verliert nur einen Dateinamen, keine Daten.
4. **Erst wenn kein Dialog mehr offen ist, laufen die Schritte 9 bis 11** (Ansicht abbauen,
   `PROFILE_DIR` wischen, Lock-Screen aus `LOCK_PROFILE_DIR`). Gelingt Punkt 3 nicht
   (kein Handle, Dialog reagiert nicht), bleibt genau dieser Rest geparkt und laeuft, sobald
   der Dialog zurueckkehrt. **Das ist vertretbar, weil die Sperre inhaltlich schon
   vollzogen ist:** ohne Schluessel und ohne offene DB haengt an den geparkten Schritten
   kein Geheimnis mehr, nur noch Aufraeumarbeit (der WebView2-Cache, den ohnehin auch der
   naechste Start purgen wuerde).
5. **Das Ergebnis des Dialogs ist nichtig** (Antwort auf Angriffsvektor 2). Kehrt
   `create_file_dialog` zurueck, nachdem eine Sperre gefeuert hat, wird der gewaehlte Pfad
   **verworfen**, es wird **keine Datei geschrieben**, der schon aufgebaute Export-Inhalt
   wird aus dem Speicher genullt, und die Bridge-Methode liefert `{"error": "locked"}`
   (stumm im Frontend, B.2). Gleiches gilt fuer die Onboarding-Ordnerwahl: nach einer
   zwischenzeitlichen Sperre/Teardown wird kein Tresor angelegt.
6. **Der offene Dialog ist keine Aktivitaet.** Er setzt den Auto-Sperr-Timer **nicht**
   zurueck (U4 definiert Aktivitaet als Eingabe im App-Fenster), und Interaktion **im**
   nativen Dialog zaehlt ausdruecklich auch nicht. Ein offener Dialog verzoegert die
   Sperre also nicht, er verzoegert nur ihre letzten drei Schritte.

##### N11.11.5.3 Dialog-Buchfuehrung (Antwort auf Angriffsvektor 3)

- **Hoechstens ein nativer Dialog gleichzeitig.** Jeder Aufruf von `create_file_dialog`
  laeuft in `api.py` durch **einen** gemeinsamen Kontextmanager (`_native_dialog(...)`),
  der ein Prozess-Flag samt Zeitstempel setzt und es im `finally` **immer** wieder
  freigibt, auch bei Ausnahme. Ist das Flag schon gesetzt, wird der zweite Dialog gar
  nicht geoeffnet, sondern die Methode liefert `{"error": "busy"}` (B.2). Damit kann weder
  ein Doppelklick noch ein Bridge-Aufruf an der UI vorbei (XSS, DevTools) Dialoge stapeln
  und so eine Kette bauen, die nie endet.
- **Kein eigener Dialog-Pfad.** Wer einen neuen nativen Dialog einfuehrt, benutzt diesen
  Kontextmanager. Ein `create_file_dialog` ohne ihn ist ein G35-Verstoss, genau wie ein
  zweiter Beenden-Pfad.
- **Waechter gegen ein haengendes Flag.** Der Auto-Sperr-Thread prueft bei jedem Tick: Ist
  das Flag gesetzt, aber **kein** modales Fenster mehr vorhanden (oder steht das Flag
  laenger, als ein Dialog plausibel offen sein kann), gilt es als verwaist, wird
  zurueckgesetzt und die geparkten Schritte laufen an. Ein stiller Dauer-Aufschub darf es
  nicht geben.
- **Sichtbar im Status-Modal (G22-Geist):** Steht die Sperre wegen eines Dialogs im
  Zustand "gesperrt, Aufraeumen geparkt", meldet `get_status()` das ehrlich, statt "alles
  sauber" zu behaupten.

##### N11.11.5.4 Was ausdruecklich **nicht** gilt

- **Kein Aufschub fuer irgendetwas ausser `autolock`.** Lock-Button, `Ctrl+L`, Panik,
  Killswitch, Reset, Off-Knopf, Fenster-X: alle brechen den Dialog sofort ab und laufen
  durch. Bei ihnen steht der Nutzer davor, ein Aufschub waere nur ein Weg, die eigene
  Panik-Taste zu verzoegern.
- **Kein "Auto-Sperre wird uebersprungen, weil der Nutzer ja gerade exportiert".** Ein
  offener Dialog ist kein Anwesenheitsbeweis; genau darauf baut Angriffsvektor 1.
- **Keine Verlaengerung der Sperrfrist,** solange ein Dialog offen ist. Der Timer laeuft
  unveraendert.


#### B.8.7 Killswitch und Reset als Datei-Operation

*(Zusammengefuehrt in Umbau-Etappe 3 aus N11.8.1 (Killswitch = Datei-Operation, Punkt 1 des frueheren N11.8) und N10.4 (Verhalten nach dem Killswitch), wortgleich. Register: Anhang 1.)*

1. **Killswitch wird auf reine Datei-Loeschung umgebaut (Prioritaet).**
   *Ueberschreibt N10.4 (Killswitch "schreibt Standard-Settings neu und setzt
   `seeded=true`") und die heutige `db.killswitch()`-Implementierung.* Der aktuelle
   `killswitch()` oeffnet die DB und loescht Zeilen. Das ist mit dem gesperrten
   Phase-8-Zustand unvereinbar (keine Schluessel im RAM, DB ist nur ein ChaCha20-Blob)
   und mit G13, das den Aufruf gerade im gesperrten Zustand erlaubt. Ab Phase 8 ist der
   Killswitch daher **keine DB-Operation, sondern eine Datei-Operation:** `tasks.db.enc`
   samt `.bak` und Vault-Metadaten loeschen, den DPAPI-Pepper aus dem Credential Manager
   entfernen (`keyring.delete_password`, G18), `PROFILE_DIR` (und `LOCK_PROFILE_DIR`,
   Punkt 3) wischen (G14), dann beenden. **Keine Schluessel noetig.** Der `seeded`-Marker
   wird dabei **nicht** geschrieben (der Datei-Killswitch beruehrt die DB nicht mehr); er
   bleibt der passive Backend-Guard aus N11.7. Weil es ohnehin keine Demo-Seed-Daten mehr
   gibt (N11.1.4), ist der naechste Start nach dem Killswitch automatisch ein **leerer
   Erststart** (Punkt 2).

**4. Nach dem Killswitch.** Der nächste Start verhält sich wie ein Erststart auf
einem frischen Rechner, aber **ohne** die Demo-Seed-Daten: keine Listen, alles kann
neu angelegt werden. **N11.8.1 gilt vorrangig: `killswitch()` ist ab Phase 8 eine reine Datei-Loeschung (`tasks.db.enc` + `.bak` + Metadaten + Pepper + Profile), schreibt KEINE Settings und keinen `seeded`-Marker mehr; der naechste Start ist mangels Datei automatisch ein leerer Erststart.** (Frueher, DB-basiert: schrieb Standard-Settings neu und setzte `seeded=true`.) Gelöscht wird nur der Inhalt der
Datenbank, **nie das Programm selbst**. Nirgendwo dürfen danach Daten liegen, die
auf die frühere Nutzung schließen lassen. Ehrliche Einordnung des heutigen Stands:
Zeileninhalte sind weg und `VACUUM` baut die Datei neu auf, aber auf SSD/NTFS ist
das noch kein forensisches Secure-Delete; erst die Phase-8-Härtung (In-Memory-DB
nach G6, `.enc`-Neuaufbau nach G16, `PROFILE_DIR`-Wisch nach G14) macht die Zusage
auch forensisch belastbar.


### B.9 Eingabe-Sicherheit: Schutz vor bösartigem Inhalt (verbindlich)

> ## ⚠️ SICHERHEITS-HÄRTUNG, STAND & OFFENE PFLICHT-GATES
>
> **Diese Liste ist verbindlich. Die offenen Punkte sind Gates: Die jeweilige
> Phase gilt erst als fertig, wenn ihr Sicherheitspunkt umgesetzt ist.**
> **Alle folgenden Gates sind verbindlich und vom Nutzer bestätigt. KEINER
> dieser Punkte ist optional, jeder MUSS in der genannten Phase umgesetzt
> werden.** Die Entstehungsgeschichte der Gates (wann welches Gate aus welchem
> Review/Audit kam) steht als Protokoll-Absatz im Entscheidungsregister
> (Anhang 1, dorthin verschoben in Umbau-Etappe 2).
>
> **NORMATIVE QUELLE (Regel seit 2026-07-13, behebt Plananalyse S1/S2):** Diese
> Tabelle (seit Umbau-Etappe 2 die eine, aus den früheren zwei B.9-Tabellen
> zusammengeführte Gate-Tabelle) ist die
> **einzige normative Quelle** für alle Sicherheits-Gates. Definition, Status,
> Stand (Datum) und Prüfweg eines Gates stehen nur hier und werden nur hier
> gepflegt. Nennt eine Zeile ausdrücklich einen Volltext-Anker (G13: B.2, G14: B.8.5,
> G16: B.7, G20: B.2, G21: Phase 7, G27: Phase 9, G28: B.7 (N11.9), G29: B.2 (N11.12),
> G30: B.10, G34: Phase 9, G35: B.8.5 (N11.11)), gehört genau dieser eine
> Volltext zur Definition dazu. Alle
> anderen Stellen sind nachrangig: die Phasen-Abschnitte listen nur noch
> Gate-Nummern mit Stichwort und verweisen hierher, die Schnellübersicht am
> Dokumentende ist ausdrücklich nicht normativ, CLAUDE.md fasst zusammen.
> **Redaktionsregel (Pflicht):** Wer ein Gate ändert (Definition, Status,
> Termin oder Streichung), ändert im selben Commit alle vier Stellen: diese
> Tabelle, die betroffene Phasen-Gateliste, die Schnellübersicht und CLAUDE.md.
>
> **✅ Bereits erledigt (im Code):**
> - **CSP gesetzt** in `frontend/index.html` (Regel 2), strenger als das Minimum
>   (zusätzlich `connect-src 'self'`, `object-src/base-uri/form-action/frame-ancestors 'none'`).
> - **`esc()` gehärtet** in `frontend/app.js`, maskiert jetzt auch `'` (einfach-
>   gequotete Attribute), nicht nur `& < > "`.
>
> **🔒 PFLICHT-GATES (Status, Stand und Prüfweg je Zeile; pro Phase abhaken):**
>
> | Gate | Phase | Status | Stand | Prüfweg | Punkt |
> |---|---|---|---|---|---|
> | **G6** | **8** | offen | seit 2026-06-08 | Im entsperrten Betrieb existiert zu keinem Zeitpunkt eine entschlüsselte DB-Datei auf der Platte (Datei-Monitor auf `%TEMP%` und den App-Ordner während Unlock, Arbeit und Lock). | **In-Memory-DB** (`:memory:`) statt entschlüsselter Temp-Arbeitskopie, siehe B.7 „Alternative für Puristen". Eliminiert Temp-Datei-Forensik (Secure-Delete auf SSD ist unzuverlässig). |
> | **G7** | **8** | offen | seit 2026-06-08 | `db.py` setzt `PRAGMA key` als Raw-Key mit 64 Hex-Zeichen; nirgends mehr ein String-Key oder eine `'%s'`-Interpolation. | **Roher Hex-Schlüssel** für `PRAGMA key = "x'<64 hex>'"` statt String-Interpolation (`db.py`), damit SQLCipher kein eigenes PBKDF2 über den schon abgeleiteten Key legt (und das Quote-Escaping entfällt). Den Dev-Platzhalter in `db.py` bei dieser Gelegenheit ersetzen. |
> | **G8** | **8** | offen | seit 2026-06-08 | Argon2id-Parameter im Code ablesen (Memory ≥ 256 MB, time_cost ≥ 3); das Setup akzeptiert 12 gleiche Zeichen als Passphrase, und die UI zeigt keinerlei Stärkemesser oder Zeichenregeln. | **Starke Argon2id-Parameter** (Memory ≥ 256-512 MB, time_cost ≥ 3) **plus die Passphrase-Politik aus N11.3 (B.2): ausschliesslich Mindestlänge 12 Zeichen, kein Stärkemesser, keine Zeichenregeln.** Die Passphrase ist der einzige reale Schwachpunkt (Offline-Brute-Force), abgefedert wird das allein über die Argon2id-Kosten und den Pepper; das ist wichtiger als die zweite Cipher-Schicht. Frühere Fassungen verlangten eine „erzwungene Passphrase-Stärke mit Stärke-Anzeige"; das ist bewusst gestrichen und darf nicht wieder eingebaut werden (ehrliche Konsequenz: `aaaaaaaaaaaa` ist gültig). |
> | **🔴 G9** | **8** | offen | seit 2026-06-08 | `grep DEV_AES_KEY` über `Code/` liefert 0 Treffer; `db.connect()` ohne passphrase-abgeleiteten Schlüssel schlägt fehl. | **`DEV_AES_KEY` & jeden statischen Schlüssel-Default ersatzlos entfernen.** Es darf **keinen** Code-Pfad geben, der die DB ohne passphrase-abgeleiteten Schlüssel öffnet. Sonst öffnet die „verschlüsselte" DB mit einem öffentlich im Quellcode stehenden String → **effektiv null Verschlüsselung**, während der Status fälschlich „AES-256 + ChaCha20" meldet. Wichtigstes Gate der Phase 8. Dazu gehören der saubere Erst-Einrichtungs-Flow (Passphrase anlegen) und die Migration der bestehenden Dev-DB auf den echten Schlüssel. |
> | **G11** | **0 / 9 (Build)** | ✅ erfüllt über `requirements.lock.txt`; Rest (Hash-Checking im Build) offen für Phase 9 | 2026-07-13 | Jede Zeile in `requirements.lock.txt` trägt eine feste `==`-Version; der Release-Build (Phase 9) installiert ausschliesslich aus der Lock-Datei mit `--require-hashes`; die Ziel-Python-Version ist auf **3.11.x** festgeschrieben (Doku und Build-Umgebung), und der Release-Build laeuft nachweislich unter 3.11.x. | **Abhängigkeiten pinnen.** Die verbindliche gepinnte Menge ist `requirements.lock.txt` (liegt vor; `requirements.txt` bleibt bewusst die lose Liste des Direktbedarfs; frühere Fassungen dieses Gates verlangten das Pinning fälschlich in `requirements.txt` selbst). Rest-Pflicht in Phase 9: der Release-Build installiert nur aus der Lock-Datei, mit `pip` Hash-Checking. Eine getauschte Lib = Totalkompromittierung der Tresor-App. **Auch der Interpreter ist eine gepinnte Abhaengigkeit (U25):** die Ziel-Python-Version ist **3.11.x** (heutiges Setup: Microsoft-Store-Python 3.11), festgehalten in der Doku und in der Build-Umgebung (Phase 9), weil `sqlcipher3-wheels` Wheels nur fuer bestimmte CPython-Versionen liefert (eine falsche Version = kein passendes Wheel = stiller Bruch) und die `.exe` gegen genau diesen Interpreter gebaut werden muss. Gilt laufend: bei jedem Dependency-Update bewusst prüfen. |
> | **G12** | **vor 7 (vorgezogen aus 3/8)** | ✅ umgesetzt 2026-07-17 (`_wire_navigation_guard` in `main.py`: `NavigationStarting`-Waechter verwirft alles ausser `about:` und `file:` in den eigenen `frontend`-Ordner; `webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False` leitet `window.open` in denselben Waechter statt in den System-Browser; DevTools-Prüfweg mit der Phase-7-Abnahme verifiziert. **Loopback-Ausnahme, korrigiert 2026-07-17:** PyWebView 5.x liefert das Frontend NICHT per `file://` aus, sondern grundsaetzlich ueber einen eigenen lokalen HTTP-Server (`http://127.0.0.1:<port>/`), und zwar in JEDEM Modus, nicht nur mit `NOATODO_DEBUG`. Erlaubt wird deshalb `http://` auf Loopback (127.0.0.1/localhost/::1) BEDINGUNGSLOS, nie an den Debug-Modus gekoppelt. Die zuerst nachgetragene, NUR-im-Debug-Variante (Phase-7-Abnahme, beruhte auf der falschen Annahme, nur der Debug-Modus nutze den HTTP-Server) liess das normale Fenster schwarz, weil G12 den eigenen Startaufruf verwarf (per instrumentiertem Lauf 2026-07-17 nachgewiesen: auch ohne Debug laedt `http://127.0.0.1:<port>/index.html`), und haette den Release-Build ebenso geschwaerzt, weil der Build `NOATODO_DEBUG` hart ignoriert (G34), `_debug_enabled()` dort also `False` ist und eine debug-gekoppelte Ausnahme verschwaende. Nur Loopback ist erlaubt; jede ENTFERNTE `http`/`https`-Adresse (der eigentliche Exfiltrations-Vektor) bleibt verweigert, die Sicherheitsabsicht ist unveraendert) | festgestellt 2026-07-13 (kein Navigations-Handler in `main.py`) | Mit `NOATODO_DEBUG=1` in der DevTools-Konsole `window.location='https://example.com'` und `window.open('https://example.com')` ausführen: beides wird verweigert, die App bleibt auf der lokalen `index.html`. | **WebView-Navigation abriegeln.** Navigations-/New-Window-Events in PyWebView abfangen und jede **externe** Navigation (`window.location`/`window.open` zu externem `http`) verweigern. Die App ist rein lokal und navigiert nie woandershin. |
> | **🔴 G13** | **8** | offen | seit 2026-06-10 | Test iteriert gesperrt über ALLE Bridge-Methoden: alles ausserhalb der Allowlist liefert `{"error": "locked"}`, `get_state()` nur `{"locked": true}`, während `quit_app()`/`killswitch()` gesperrt funktionieren. | **Serverseitige Lock-Durchsetzung (als Allowlist).** Volltext in B.2 (Etikett G13). |
> | **G14** | **8 (Teile vorgezogen)** | teils erledigt: fester Profilordner + Altlasten-Wisch ✅, sicheres Wischen offen | 2026-06-20 | Nach normalem Betrieb liegen keine `%TEMP%\tmp*\EBWebView`-Altlasten; ab Phase 8: nach Lock/Panic/Quit (auch Fenster-X) ist `PROFILE_DIR` gewischt, und ein Neustart nach hartem Kill scheitert nicht mit `0x800700AA`. | **Keine WebView2-Datenspuren auf der Platte.** Volltext in B.8.5 (Etikett G14). |
> | **G15** | **8** | offen | seit 2026-06-10 | Im `.enc`-Header existiert kein Hash-Feld; eine falsche Passphrase erzeugt einen AEAD-Fehler mit der Meldung "Passphrase falsch"; die getrennten HKDF-`info`-Labels stehen im Code. | **Schlüsselableitung mit Domain-Separation, KEIN gespeicherter Verifikations-Hash.** Argon2id erzeugt aus dem Pepper-gebundenen `ikm` (verbindliche Konstruktion in G18, V2a) + Salt **ein** 32-Byte-Master-Secret; daraus per HKDF-SHA256 mit getrennten `info`-Labels (`b"noatodo/aes-v1"`, `b"noatodo/chacha-v1"`) `aes_key` und `chacha_key` ableiten. Es wird **kein** Argon2-Hash der Passphrase gespeichert: Die Prüfung beim Entsperren ist der Erfolg oder Misserfolg der ChaCha20-Poly1305-Entschlüsselung (der Poly1305-Tag verifiziert die Passphrase implizit; falsche Passphrase = AEAD-Exception = Meldung "Passphrase falsch"). So liegt kein zusätzliches Orakel-Material für Offline-Angreifer auf der Platte. Ersetzt die ältere Formulierung in B.7 ("Argon2-Hash zum Prüfen speichern", "Teilstücke des KDF-Outputs"). |
> | **G16** | **8** | offen | seit 2026-06-10 | Hexdump von `tasks.db.enc` beginnt mit `NOA1`; zwei aufeinanderfolgende Wraps tragen verschiedene Nonces; nach einem simulierten Absturz mitten im Sperren greift `.bak`. Zusätzlich (V1): ein manipuliertes Header-Byte lässt die Entschlüsselung mit einem sauberen AEAD-Fehler scheitern; ein Wrap auf ein (simuliert) volles Laufwerk lässt `.enc` und `.bak` unangetastet; das `.tmp` wird nachweislich vor der `.bak`-Rotation probeentschlüsselt. | **Dateiformat von `tasks.db.enc` + atomares Schreiben.** Volltext in B.7 (Etikett G16). |
> | **G17** | **8** | offen | seit 2026-06-10 | Mutation ausführen, ca. 5 s warten, Prozess hart beenden: der Neustart zeigt die Änderung. | **Write-back-Politik für die In-Memory-DB** (Ergänzung zu G6). Nach jeder mutierenden Bridge-Operation wird die In-Memory-DB debounced persistiert (z.B. 3 s nach der letzten Änderung; zusätzlich **sofort** bei Lock/Panic/Quit), als neues `tasks.db.enc` nach dem Verfahren aus G16. Ein Crash kostet damit höchstens die letzten Sekunden, nie den Tagesstand. |
> | **G18** | **8** | offen (Zusage konditioniert 2026-07-13, B.10.4) | seit 2026-06-10 | Der Credential-Manager-Eintrag existiert; eine Kopie von `tasks.db.enc` lässt sich auf einem fremden Windows-Konto auch mit korrekter Passphrase nicht öffnen. | **DPAPI-Pepper gegen Offline-Brute-Force (Pflicht).** Beim Einrichten der Passphrase wird zusätzlich ein zufälliger 32-Byte-Pepper erzeugt und über `keyring` im Windows Credential Manager (DPAPI, ans Windows-Konto gebunden) abgelegt. Der Pepper fliesst zusätzlich zur Passphrase in die Ableitung ein. **Verbindliche, versionierte Konstruktion (V2a, 2026-07-15; ersetzt die frühere Angabe „Argon2id-`secret`-Parameter", die so nicht umsetzbar ist, weil `argon2-cffi` Argon2s Keyed-Secret-Parameter nicht exponiert):** die Passphrase wird **vor** Argon2id an den Pepper gebunden: `ikm = HKDF-Extract(salt=pepper, ikm=passphrase_utf8)` (per Definition identisch mit `HMAC-SHA256(key=pepper, msg=passphrase_utf8)`, Ergebnis 32 Byte), danach `master_secret = Argon2id(password=ikm, salt=<Salt aus dem G16-Header>, Parameter aus N11.4.3, B.7)`. Die Konstruktion hängt an der Formatversion im G16-Header; eine spätere Änderung erhöht die Version und braucht einen Migrationspfad. **Wirkung, konditioniert (B.10.4, Plananalyse S4; die frühere Formulierung "kann offline gar nicht raten" war ein Überversprechen und ist gestrichen):** Wer **nur die Tresordatei** `tasks.db.enc` kopiert hat (Klasse K1), kann offline nichts anfangen, ihm fehlt der Pepper aus dem Windows-Konto. Wer die **ganze, unverschlüsselte Platte** hat (gestohlener Laptop, ausgebaute SSD), kann den DPAPI-Master-Key offline angreifen; der Pepper hängt dann an der Stärke des **Windows-Anmeldepassworts**. Die Zusage gilt daher nur mit BitLocker/Geräteverschlüsselung **oder** starkem Windows-Passwort, und genau so (mit dieser Bedingung) muss sie in UI und Doku stehen. **Kein Recovery-Export (N11.3, überschreibt die frühere Pflicht):** der Tresor ist bewusst an dieses Windows-Konto/diesen PC gebunden; geht das Windows-Profil verloren, ist die DB auch mit korrekter Passphrase nicht mehr zu öffnen. Der Einrichtungs-Flow enthält daher keinen Recovery-Schritt; der einzige Ausweg bei Verlust ist der Reset (Datenverlust, N11.3). |
> | **G19** | **8, vorgezogen** | ✅ umgesetzt; Nachbesserung offen (V3: Mutex-Namensraum) | 2026-06-20, V3 ergänzt 2026-07-15 | Zweite Instanz starten: Hinweisbox erscheint, der zweite Prozess beendet sich, die erste Instanz läuft ungestört weiter. Zusätzlich (V3): dieselbe Prüfung aus einer zweiten Logon-Session desselben Benutzers (RDP/schnelle Benutzerumschaltung); auch dort darf keine zweite Instanz auf dieselbe DB starten. | **Single-Instance-Schutz.** Beim Start einen benannten Windows-Mutex belegen (`ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\NoaToDoSingleton")`, danach `GetLastError() == ERROR_ALREADY_EXISTS (183)` prüfen). Läuft schon eine Instanz: Hinweis zeigen und den zweiten Prozess sofort beenden. Zwei Instanzen würden sich `tasks.db.enc` bzw. die Arbeitskopie gegenseitig überschreiben (Korruption/Datenverlust). **Nachbesserung V3 (2026-07-15): Mutex-Namensraum.** `Local\NoaToDoSingleton` ist nur **pro Logon-Session** eindeutig: derselbe Benutzer über RDP oder schnelle Benutzerumschaltung startet damit eine zweite Instanz auf demselben Profil und derselben DB, exakt die Korruption, die dieses Gate verhindern soll. Zielname: **`Global\NoaToDo-<User-SID>`** (`Global\` gilt über alle Sessions hinweg, die User-SID hält verschiedene Windows-Konten weiterhin getrennt). Der Code nutzt heute noch `Local\...`; die Umstellung ist Rest-Pflicht dieses Gates, spätestens in Phase 8. |
> | **G20** | **7** | ✅ umgesetzt 2026-07-17 (deklaratives Schema am `@bridge`-Decorator, introspektierbar via `_schema`; Text-/Namens-Kappung + Steuerzeichen-Strip, ID-/Listen-Typpruefung, `reorder` mit exakter Mengenpruefung nach N11.2.2, `set_setting`-Whitelist mit Wert-Pruefung je Key nach V5. Hinweis: der Key `dark` bleibt uebergangsweise in der Whitelist, bis N11.6 ihn durch `theme` ersetzt; `theme`/`sound`/`autoLock` sind bereits validiert) | seit 2026-06-10 | Ein 1-MB-Text wird auf 4096 Zeichen gekürzt; `reorder(list_id, "string")` liefert einen Fehler; `set_setting("foo", 1)` liefert `{"error": "invalid"}`. Zusätzlich (V5): `set_setting("accent", "red;} body{...")` liefert `invalid`; `set_setting("sidebarWidth", 9999)` speichert höchstens 520; `set_setting("autoLock", 7)` liefert `invalid`. | **Regel-4-Validierung auch für LOKALE Eingaben + Typ-/Key-Prüfung an der Bridge.** Volltext in B.2 (Etikett G20). |
> | **G21** | **7** | erledigt (2026-07-17): Sanitisierung (a)/(a2), Einzeiligkeit (b) und echter Save-Dialog mit realem Schreiben (c) in `api.py` umgesetzt, gilt für `export_list` und `export_all` | seit 2026-06-10 | Eine Liste namens `CON` exportiert als `_CON.md`; ein Task mit Zeilenumbruch bleibt im Export einzeilig; die Datei liegt real am im Save-Dialog gewählten Ort. Zusätzlich (V6): eine Liste namens `a<b>:c?*` bzw. `..\..\evil` ergibt einen Dateinamens-Vorschlag ohne diese Zeichen und ohne `..`; ein 300-Zeichen-Listenname wird auf ca. 120 Zeichen gekappt; dasselbe gilt für `export_all`. | **Export-Härtung.** Volltext in Phase 7 (Etikett G21). |
> | **G22** | **SOFORT, spätestens mit 7** | erledigt (2026-07-17): `get_status()` + Status-Modal ehrlich seit 2026-07-16 (`active:false`, Warnfarbe, `dev_key`-Flag); Header-Pill/Lock-Untertitel existieren im Code nicht; Panik-Endschirm ("Workspace cleared" statt "All data securely wiped") und Wipe-Fortschritt (nur reale Schritte: Workspace/Cache verwerfen, offline) seit 2026-07-17 ehrlich und bleiben es dauerhaft (N11.17): der bewusst falsche Aussenschirm des Endschirms wird nicht gebaut (B.10.5); ab Phase 8 zeigt der Status echte Werte | seit 2026-06-10 | Solange `DEV_AES_KEY` in `db.py` existiert, darf nirgends in der App "active", "ENCRYPTED" oder "securely wiped" stehen: Status-Modal öffnen sowie Header-Pill, Lock-Screen-Untertitel und Panik-Endschirm prüfen. | **Ehrliche Sicherheits-Behauptungen in der gesamten UI (ausgeweitet 2026-07-13, Plananalyse S2; vorher nur `get_status()`).** Bis Phase 8 fertig ist, darf **keine** Stelle der App eine Verschlüsselung oder einen sicheren Wipe behaupten, die es nicht gibt. (a) `get_status()` meldet den realen Zustand: Schicht 1 "SQLCipher mit Entwicklungs-Schlüssel (UNSICHER)", Schicht 2 "nicht implementiert", `active: false`; das Status-Modal zeigt das in Warnfarben statt grün (aktuell meldet der Status "AES-256 + ChaCha20 · active", während der AES-Key öffentlich im Repo steht; im Audit nachgewiesen). (b) Dieselbe Ehrlichkeit gilt für **alle** weiteren Verschlüsselungs-/Wipe-Behauptungen der UI: die Header-Pill ("LOCAL · ENCRYPTED"), den Lock-Screen-Untertitel ("LOCAL VAULT · ENCRYPTED") und den Panik-Endschirm ("All data securely wiped") bis Phase 8 auf ehrliche Texte umstellen (z.B. "LOCAL · DEV BUILD"). Der Panik-Endschirm bleibt auch nach Phase 8 dauerhaft ehrlich (Entscheidung N11.17): die früher für Phase 8 vorgesehene "bewusste Aussendarstellung" aus N10.3 wird nicht gebaut, die Abwägung dazu steht in B.10.5. Ab Phase 8 zeigt der Status echte Werte (Argon2-Parameter, Pepper vorhanden ja/nein, Zeitpunkt des letzten Wraps). |
> | **G23** | **6.5** | ✅ umgesetzt | 2026-06-10 | Der kopierte Task erscheint nicht in der Win+V-History; das Clipboard ist 60 s nach dem Kopieren leer. | **Clipboard-Hygiene + Einzel-Task-Kopie.** Windows speichert das Clipboard in der Zwischenablage-History (Win+V) und synchronisiert es ggf. ins Microsoft-Cloud-Clipboard, App-Inhalte würden so den Rechner verlassen. Umgesetzt: (a) Kopiert wird nur noch **eine ausgewählte Aufgabe** (`copy_task`), nie eine ganze Liste; für Listen gibt es den Export. (b) Das Kopieren passiert komplett im **Backend** (`api.py`, Win32 per ctypes, nicht `navigator.clipboard`) und setzt zusätzlich zu `CF_UNICODETEXT` die Formate `ExcludeClipboardContentFromMonitorProcessing`, `CanIncludeInClipboardHistory` (=0) und `CanUploadToCloudClipboard` (=0). (c) Auto-Clear: 60 s nach dem Kopieren wird das Clipboard geleert, sofern es noch unseren Inhalt trägt. (d) Der `Strg+C`-App-Shortcut wurde ersatzlos entfernt. Bei künftigen Copy-Funktionen MUSS derselbe Backend-Pfad verwendet werden. |
> | **G25** | **8** | offen | seit 2026-06-10 | Code-Review: Schlüssel/Master-Secret/Pepper als `bytearray` mit Nullung an allen Ausgängen (Lock, Panic, Quit, Fenster-X, `atexit`); kein Geheimnis in Logs, Exceptions oder `get_status()`. | **RAM-Schlüssel-Hygiene.** `aes_key`, `chacha_key`, Master-Secret und Pepper als `bytearray` (nicht `bytes`/`str`) halten; beim Sperren/Panic/Beenden **vor** dem Verwerfen mit Nullen überschreiben. Die Passphrase unmittelbar nach der Ableitung verwerfen; Passphrase und Schlüssel dürfen **nie** in Logs, Exceptions, `get_status()` oder sonstwie ans Frontend gelangen. Im Code dokumentieren: Python gibt keine harten Garantien (der GC kann Kopien hinterlassen), das Nullen ist Best-Effort und trotzdem Pflicht. |
> | **G26** | **entfällt** | ❌ verworfen (zu fehleranfällig) | 2026-06-20 | Nur noch Regressions-Check: `SetWindowDisplayAffinity` kommt im Code nicht vor. | **Screenshot-Schutz (entfernt).** Idee war, das Fenster per `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` aus Bildschirmaufnahmen herauszunehmen. Mehrfach umgesetzt und wieder entfernt, weil er reale Probleme machte: auf manchen GPU-/Treiber-Konstellationen blockiert die Affinity das WebView2-Rendern komplett (Fenster bleibt weiss / reagiert nicht), und die Startup-Verdrahtung verklemmte zudem die Nachrichtenschleife. Zusatznachteile: blendet das Fenster auch in legitimer Freigabe/Aufnahme schwarz aus und nuetzt nichts gegen eine Kamera. **Entscheidung: dauerhaft entfernt, nicht wieder einbauen.** Falls je erneut gewuenscht, zwingend mit Render-Verifikation nach dem Setzen (Affinity automatisch zuruecknehmen, wenn der Inhalt nicht mehr rendert) und ausschliesslich ueber `_run_on_ui_thread`. |
> | **G27** | **9** | offen | seit 2026-06-20; Frontend-Integrität ergänzt 2026-07-15 (Plananalyse A5) | `signtool verify` besteht; das Bundle enthält keinen Python-Quelltext; ein Hexdump der `.exe` zeigt keine Klartext-Docstrings; eine nachträglich veränderte `app.js` verhindert den Start mit einer Integritäts-Meldung. | **Binary-Härtung gegen Reverse-Engineering + Manipulation.** Authenticode-Signing der `.exe` (Manipulation erkennbar, SmartScreen entschärft); keinen Python-Quelltext mitliefern (vorzugsweise Nuitka statt entpackbarem PyInstaller-Bundle, mindestens Docstrings/`assert`s strippen); optional Obfuskation (PyArmor) als Bonus. **Grundsatz: das Sicherheitsmodell beruht nie auf Code-Geheimhaltung** (Kerckhoffs), sondern allein auf Passphrase + DPAPI-Pepper + Verschlüsselung; die Härtung erhöht nur die Hürde. Keine fragilen Anti-Debugging-Tricks als Schutzbasis. **Ergänzung Frontend-Integrität (2026-07-15, Plananalyse A5):** Die Signatur deckt nur die `.exe`; `index.html`/`app.js`/`style.css` lägen daneben (One-Folder) oder werden entpackt und wären bei intakter Exe-Signatur austauschbar. Wer sie einmal schreiben kann, besitzt die App dauerhaft: das nächste `boot()` lädt das manipulierte JS mit voller Bridge und liest die Passphrase-Eingabe des HTML-Lock-Screens mit. Pflicht: Frontend-Assets ins signierte Binary einbetten und von dort laden, **oder** beim Start jeden Asset-Hash gegen ein im Binary eingebettetes Manifest prüfen; bei Abweichung verweigert die App den Start mit einer klaren Meldung (kein "trotzdem fortfahren"). Das erschwert stille K4-Persistenz, wird aber nie als vollständiger K4-Schutz verkauft (B.10.3 Punkt 1). Volltext in Phase 9. |
> | **G28** | **8** | offen | seit 2026-07-09 (N11.9) | Der dokumentierte Beweis liegt vor: das Öffnen des inneren Images ohne `aes_key` scheitert, ein Roh-Byte-Dump zeigt weder SQLite-Klartext-Header noch Task-Text. | **Verschlüsselungs-Beweis (aus N11.9, 2026-07-09).** Vor Phase-8-Abschluss ist zu **beweisen**, dass die Arbeits-/Zwischendatei tatsächlich AES-verschlüsselt ist: das Öffnen des inneren Images **ohne** `aes_key` muss fehlschlagen (kein SQLite-Klartext-Header, kein lesbarer Task-Text im Roh-Byte-Dump). Schlägt der Beweis für den `:memory:`-Serialize-Weg fehl, ist der Fallback mit SQLCipher-verschlüsselter Arbeitsdatei verbindlich. Kein Auslieferungsbuild ohne bestandenen Beweis. **Automatisiert (V12, 2026-07-15):** der Beweis ist kein Einmal-Handgriff, sondern ein pytest-Test der Phase-9-Testliste (Scan des Arbeits-Artefakts auf den SQLite-Klartext-Header `SQLite format 3` und einen bekannten Task-String; jeder Fund ist ein Fail). Volltext in B.7 (Etikett N11.9). |
> | **G29** | **SOFORT, spätestens 7** | ✅ umgesetzt 2026-07-17 (vor dem Termin 2026-07-20; Fehlercode-Katalog + statische Texte im `@bridge`-Decorator, redigierter Ringpuffer `Api._errors` mit "Recent errors"-Sektion + `copy_errors()` im Status-Modal, Toast-Politik im Frontend, Puffer-Leerung bei Lock/Panik/Killswitch/Quit; die Buildprüfung "kein Debug/kein Logfile im Release" bleibt Phase 9) | seit 2026-07-13 | Eine provozierte `OSError` (z.B. Export auf ein nicht erreichbares Laufwerk) zeigt im Toast nur den Katalog-Text ohne Pfad/Benutzernamen; im Release existiert kein Logfile. | **Fehler-Hygiene, Fehlercode-Katalog, Logging-Politik (aus N11.12, 2026-07-13, Plananalyse S6).** Mit dem Sync fiel das alte G10 („Fehlermeldungen ohne Geheimnisse") weg, sein lokaler Kern gilt weiter: Der `@bridge`-Decorator gibt heute `str(exc)` ans Frontend (`api.py`), eine banale `OSError` trägt damit absolute Pfade samt Windows-Benutzernamen als Toast auf den Bildschirm (und bei Screen-Sharing auf fremde Bildschirme). Pflicht: (a) **Generische Fehler nach vorne**: nur Code + statischer Text aus dem Katalog in **B.2**, nie `str(exc)`, nie Pfade, Tracebacks, SQL-Fragmente, Aufgabentext, Passphrase oder Schlüssel. (b) **Fehlercode-Katalog in B.2** ist kanonisch (`not_found`, `invalid`, `locked`, `passphrase`, `rate_limited`, `vault`, `canceled`, `internal`), inklusive der Spalte „Frontend-Verhalten" und der Codes, die **stumm** bleiben (`locked`, `canceled`); jeder neue Code wird dort eingetragen, sonst darf er nicht ans Frontend. (c) **Details nur in einen In-Memory-Ringpuffer** (50 Einträge, redigiert: Pfade werden zu `<path>`, nie Bridge-Argumente), einsehbar im Status-Modal, geleert in Schritt 3 der `teardown()`-Sequenz (G35). (d) **Logging-Politik:** im Release **kein** persistentes Logfile (kein `FileHandler`, kein `basicConfig(filename=...)`, keine Traceback-Datei), Diagnose nur hinter `NOATODO_DEBUG`, und auch dort nie Passphrase/Schlüssel/Aufgabentext; der Auslieferungsbuild läuft nie im Debug-Modus (Prüfung in Phase 9). Volltext in B.2 (Etikett N11.12). |
> | **G30** | **Doku, vor 8** | ✅ B.10 verankert; Arbeitsregel gilt laufend | 2026-07-13 | B.10 existiert, und jedes Gate steht mit seiner Angreiferklasse in der Zuordnungstabelle B.10.6; ein neues Gate ohne Klassen-Eintrag verletzt das Gate. | **Bedrohungsmodell (B.10, ergänzt 2026-07-13 aus Plananalyse S4).** Der Plan definierte Gegenmassnahmen, ohne je die Angreifer zu benennen. Pflicht: Abschnitt **B.10** ist verbindlicher Teil des Plans und **vor** Beginn von Phase 8 zu lesen. Er legt fest: die sechs Angreiferklassen K1 bis K6 (Datei-/Plattendieb, Forensik, kurzer physischer Zugriff, Malware im eigenen Konto, Reverse-Engineer, Zwangs-Situation), die ausdrücklichen **Nicht-Ziele** (allen voran **Malware-als-Nutzer, K4**: dagegen gibt es im selben Sicherheitskontext keine Verteidigung, und es wird keine vorgetäuscht, das ist die G26-Lektion), die **Voraussetzungen** (BitLocker/Geräteverschlüsselung dringend empfohlen, starkes Windows-Passwort, Passphrase min. 12 Zeichen), die **konditionierte G18-Zusage** (kein "gar nicht raten" ohne die Bedingung, siehe G18 und B.10.4) und die **dokumentierte Abwägung zum Panik-Endschirm** (bei "Finish" behauptet er einen Wipe, den es nicht gab; bewusst so gewollt, mit dem Restrisiko in K6, B.10.5). **Arbeitsregel ab sofort:** Jedes neue Gate trägt sich in die Zuordnungstabelle B.10.6 ein und nennt seine Angreiferklasse(n). Eine Massnahme ohne Klasse wird nicht gebaut. |
> | **G31** | **8** | offen | seit 2026-07-15 (Plananalyse A1) | Das Status-Modal zeigt den realen BitLocker-Status des Tresor-Laufwerks (oder ehrlich "unbekannt", wenn die Abfrage scheitert, nie ein falsches "geschützt"); die Einrichtungs-UI enthält die BitLocker-Empfehlung; Code-Review: alle Schlüssel-`bytearray`s werden nach der Ableitung per `VirtualLock` gesperrt und vor dem G25-Nullen per `VirtualUnlock` freigegeben; `faulthandler` schreibt nie in eine Datei, und es existiert kein Code-Pfad, der Tracebacks oder Dumps auf die Platte schreibt. | **RAM-auf-Platte-Lecks minimieren (Pagefile, Ruhezustand, Crash-Dumps).** Die entsperrte DB lebt im RAM (G6/N11.9), aber Windows schreibt RAM auf die Platte: `pagefile.sys` (Auslagerung), `hiberfil.sys` (Ruhezustand = kompletter RAM-Abzug inkl. Schlüsseln und Klartext) und WER-Minidumps beim Crash des **Python-Prozesses** (G14 behandelt nur WebView2-Dumps). Ein Offline-Angreifer (K2) liest daraus Schlüssel und Inhalte, ohne die Kaskade anzufassen; das G25-Nullen verkürzt nur das Zeitfenster. Pflicht, dreiteilig: **(a) Ehrlichkeit zuerst:** BitLocker/Geräteverschlüsselung ist die einzige vollständige Antwort und steht als Voraussetzung im Bedrohungsmodell (B.10.4). Die Einrichtungs-UI empfiehlt sie, und das Status-Modal zeigt den realen BitLocker-Status des Tresor-Laufwerks an (WMI-Abfrage `Win32_EncryptableVolume`; ohne Adminrechte ggf. nicht lesbar, dann ehrlich "Status unbekannt" anzeigen, im Sinne von G22 nie ein ungeprüftes "geschützt"). **(b) `VirtualLock` für Schlüsselmaterial (Best-Effort):** `aes_key`, `chacha_key`, Master-Secret und Pepper werden als `bytearray` (G25) nach der Ableitung per `VirtualLock` (ctypes, über die Buffer-Adresse) gegen Auslagern gesperrt und vor dem Nullen per `VirtualUnlock` freigegeben. Schlägt `VirtualLock` fehl (Working-Set-Quota), läuft die App normal weiter, kein Fehler an den Nutzer (Verfügbarkeit zählt als Sicherheitsziel, dieselbe Abwägung wie N11.4.3). Ehrlich dokumentieren: `VirtualLock` hält Seiten aus dem Pagefile, **nicht** aus `hiberfil.sys` (der Ruhezustand schreibt auch gesperrte Seiten) und nicht aus Crash-Dumps; gegen diese Rest-Kanäle hilft nur (a). **(c) Dump-/Traceback-Minimierung:** kein `faulthandler.enable()` mit Datei-Ziel, keine Traceback-Dateien (deckt sich mit der G29-Logging-Politik), WER-Fehlerdialoge/-Dumps für den eigenen Prozess minimieren, soweit ohne Adminrechte möglich (z.B. `SetErrorMode`). Dass ein Nutzer oder Admin über die WER-LocalDumps-Registry trotzdem Prozess-Dumps erzwingen kann, ist eine dokumentierte Restgrenze (K4-Terrain), keine App-Aufgabe. |
> | **G32** | **8 (mit dem Onboarding, N11.13)** | offen | seit 2026-07-15 (Plananalyse A2) | Onboarding-Schritt 1 schlägt `%LOCALAPPDATA%\NoaToDo` vor; ein testweise gewählter Pfad unter OneDrive/Dropbox zeigt die Warnung mit beiden Kernsätzen (Versionshistorie beim Anbieter; Killswitch/Reset löschen dort nichts), ein lokaler Pfad zeigt keine; die Killswitch-/Reset-Bestätigung enthält den Cloud-Satz, wenn der Tresor auf einem erkannten Sync-Pfad liegt. | **Tresor-Ort: sicherer Default + Cloud-Sync-Warnung.** Der Nutzer wählt den Speicherort frei (N11.3); landet `tasks.db.enc` in einem Sync-Ordner (naheliegend: "Dokumente" ist oft umgeleitet), erzeugt das G17-Rewriting hunderte serverseitige Versionen pro Tag. Jeder alte Stand bleibt beim Anbieter wiederherstellbar (gelöschte Aufgaben leben in Cloud-Versionen weiter; **Killswitch und Reset löschen dort nichts**), und Änderungsfrequenz plus Dateigrösse ergeben ein präzises Nutzungsprofil. Verschlüsselt bleibt alles, aber Retention und Metadaten entwerten das Local-first-Versprechen und den Killswitch teilweise. Pflicht: **(a)** Das Onboarding schlägt `%LOCALAPPDATA%\NoaToDo` als Default vor (wird von keinem üblichen Sync-Client erfasst). **(b)** Liegt der gewählte Pfad unter einer erkennbaren Sync-Wurzel, erscheint eine deutliche Warnung, die **beide** Fakten nennt: die verschlüsselte Datei wird synchronisiert und beim Anbieter versioniert, und Killswitch/Reset löschen Cloud-Versionen **nicht**. Erkennung Best-Effort: OneDrive über die Umgebungsvariablen (`OneDrive`, `OneDriveConsumer`, `OneDriveCommercial`), Dropbox über `info.json` (`%APPDATA%\Dropbox\info.json` bzw. `%LOCALAPPDATA%\Dropbox\info.json`), zusätzlich Pfadbestandteile ("OneDrive", "Dropbox", "Google Drive", "iCloudDrive", case-insensitive). Ein nicht erkannter Sync-Ordner bleibt möglich; deshalb steht der Killswitch-Satz zusätzlich in der Killswitch-/Reset-Doku und im Bedrohungsmodell (B.10.3 Punkt 6). **(c)** Die Warnung ist eine Warnung, keine Sperre: die freie Ortswahl aus N11.3 bleibt, der Nutzer darf bewusst fortfahren. Wechseldatenträger und Netz-/UNC-Pfade behandelt N11.15.4 (B.11) (eigene Warnung "Tresor nicht erreichbar"). |
> | **G33** | **8 (Erststart, `create_vault()`)** | offen | seit 2026-07-15 (Plananalyse A3) | Nach dem ersten `create_vault()` auf einem Rechner mit Dev-Bestand existieren `Code/data/tasks.db` samt `tasks.db-journal`/`-wal`/`-shm` nicht mehr (vorher bestmöglich überschrieben, nicht nur entlinkt); der Einmal-Hinweis mit der forensischen Restgrenze wurde angezeigt. | **Dev-Altdaten entsorgen.** `DEV_AES_KEY` steht im Repo-Quelltext; die heutige `data/tasks.db` mit den echten Aufgaben ist damit faktisch Klartext (im Git-Repo liegt sie dank `.gitignore` korrekt **nicht**, das wurde geprüft). N11.3 sagt nur "die alte Dev-DB wird verworfen"; dieses Gate legt das **Wie** fest: Der Phase-8-Erststart (im Zuge von `create_vault()`, bevor der neue Tresor in Betrieb geht) löscht `tasks.db` **samt** `tasks.db-journal`, `tasks.db-wal` und `tasks.db-shm` über den Secure-Delete-Pfad (bestmöglich überschreiben, dann entlinken; derselbe Pfad wie beim `.bak`-Wegräumen in N11.3 (c)), nie per blankem `os.remove` (ein `os.remove` hinterlässt auf SSD forensische Reste, dasselbe Argument, mit dem G6 die Temp-Kopien eliminiert). **Ehrliche Restgrenze, einmal sichtbar für den Nutzer:** Daten, die während der Dev-Phase geschrieben wurden, können auf einer SSD (Wear-Leveling) forensisch verbleiben, ebenso alte Export-Dateien aus der Dev-Zeit (eigene Dateien des Nutzers; die App sucht und löscht sie nicht, der Hinweis nennt sie); wer das ausschliessen muss, braucht ein frisches, vollverschlüsseltes System (BitLocker, G31/B.10.4). Dieser Hinweis wird beim Umstieg **einmal** angezeigt (nur wenn eine Dev-DB gefunden und entsorgt wurde), damit der Nutzer ihn bewusst gelesen hat. |
> | **G34** | **9; Teilpunkt (b) SOFORT** | (b) `text_select=False` explizit gesetzt ✅ 2026-07-16 (`main.py` `create_window`); Rest offen für Phase 9: (a) DevTools/`NOATODO_DEBUG` im Release hart aus, (c) `AreBrowserAcceleratorKeysEnabled=false` (kein `Strg+P`) + `AreDefaultContextMenusEnabled=false`. Regressionstest für `text_select` folgt mit der Phase-9-Testliste (heute kein Test-Setup) | seit 2026-07-15 (Plananalyse A4/A6) | Release-`.exe` mit gesetztem `NOATODO_DEBUG=1` starten: keine DevTools erreichbar (F12 und Rechtsklick tot); `Strg+P` öffnet keinen Druckdialog; Rechtsklick zeigt kein WebView2-Kontextmenü; Task-/Listentext ist nicht selektierbar, Eingabefelder bleiben es (Regressionstest für `text_select=False`, läuft schon vor Phase 9). | **Release-Härtung: Debug-Schalter, DevTools, Kopier-/Auslass-Kanäle.** Volltext in Phase 9 (Etikett G34). |
> | **🔴 G35** | **8** | offen | seit 2026-07-13 (N11.11, S5-Entscheid) | Es existiert im Code genau eine `teardown(reason)`-Routine, und für jeden der neun Ausgänge ist der N11.11-Nachweis einzeln erbracht (Debounce synchron geschrieben, Clipboard geleert, Schlüssel genullt, `PROFILE_DIR` gewischt, Funk nur auf Beenden-Wegen als letzter Schritt, Mutex frei). | **Gemeinsame Sperr-/Beenden-Sequenz.** Sperren, Beenden, Panik-Ende, Killswitch und Reset laufen durch genau **eine** Routine `teardown(reason)` in `security.py`, in der Reihenfolge aus N11.11.2: Idempotenz-Sperre, offene native Dialoge auflösen (U5), Eingaben einfrieren (G13), G17-Debounce abbrechen und ausstehende Änderungen synchron persistieren, Clipboard sofort leeren, wenn es noch App-Inhalt trägt (G23/V7), DB schließen, Schlüssel nullen (G25), erst dann (nur Killswitch/Reset) Dateien und Pepper löschen (U21), `PROFILE_DIR` wischen (G14), Funk-Zustand ganz zuletzt wiederherstellen (nur auf den Beenden-Wegen, N11.5/N11.10), Mutex freigeben. Jeder Ausgang (Lock-Button, `Ctrl+L`, Auto-Sperre, Off-Knopf, Panik-Finish, Killswitch, Reset, natives Fenster-X, `atexit`) ruft diese Routine; ein zweiter, handgeschriebener Beenden-/Sperr-Pfad ist ein Gate-Verstoss. Volltext in B.8.5 (Etikett N11.11). |
>
> **Zwei Kleinigkeiten (Hinweis, kein Gate):**
> - **Export/Clipboard:** `export_list` schreibt **unverschlüsselte** Dateien (by
>   design, der Nutzer exportiert bewusst Klartext). Das Kopieren ist seit dem
>   Nachtrag gehärtet und auf eine einzelne Aufgabe begrenzt, siehe G23.
> - **`main.py` `emit()`:** `json.dumps(payload)` muss `ensure_ascii=True` (Default)
>   behalten, sonst können U+2028/U+2029 in Event-Daten den `evaluate_js`-Aufruf
>   brechen.
>
> Die Phasen-Abschnitte wiederholen diese Gates **nicht** mehr im Wortlaut,
> sondern listen nur die Gate-Nummern mit Stichwort und Verweis hierher
> (Plananalyse S1: die früheren Wortlaut-Kopien sind mehrfach
> auseinandergedriftet, siehe W3/W4/W8/W18).
>
> **Zusätzlich vorgezogen:** G12 (externe WebView-Navigation verweigern) ist mit
> wenigen Zeilen umsetzbar und wird **vor** Phase 7 umgesetzt, nicht erst in
> Phase 8. Ebenso G22 (ehrliche Sicherheits-Behauptungen in der ganzen UI,
> Termin 2026-07-20), siehe Tabelle. *(Beide sind seit 2026-07-17 umgesetzt,
> Status in der Tabelle.)*

Die App ist rein lokal; es gibt keinen eingehenden Netzwerk-Kanal. Trotzdem gelten
die folgenden Regeln als Grundhärtung: Aufgaben-/Listentexte sind Freitext, ein
exportierter oder wieder eingelesener Datenbestand kann manipuliert sein, und die
Regeln kosten nichts. Der Grundsatz „Eingaben nie als Code behandeln" bleibt Pflicht.

**Jeder Text, der ins DOM oder in SQL fließt, gilt als _untrusted input_.** Folgende
Regeln sind Pflicht:

#### Regel 1: Kein `innerHTML` für Nutzerdaten (Anti-XSS)

Im Frontend darf **kein** Task-Text und kein Listenname (jeder Nutzer-Freitext) jemals über `innerHTML`,
`outerHTML` oder `insertAdjacentHTML` in den DOM eingefügt werden. Stattdessen
ausschließlich:

```js
// ✅ Sicher, Text wird als reiner Text gerendert, HTML-Tags sind wirkungslos
element.textContent = task.text;
// oder
element.appendChild(document.createTextNode(task.text));

// ❌ Verboten, öffnet XSS: <img src=x onerror="pywebview.api.panic()">
element.innerHTML = task.text;
```

**Warum kritisch:** Das Frontend läuft in PyWebView mit vollem Zugriff auf
`pywebview.api.*`. Ein XSS ist hier keine Kosmetik, sondern **Remote Code Execution
gegen das Backend**, ein Angreifer könnte `delete_list()`, `panic()`, `get_state()`
(Daten-Exfiltration) oder `killswitch()` aufrufen.

> **🔒 STATUS (aktuell tolerierbar):** Die `app.js` rendert über
> `root.innerHTML = …` mit `esc()` an jeder Einsetzstelle, das **widerspricht dem
> Buchstaben dieser Regel**. Da die App rein lokal ist und **keine** Fremddatenquelle
> fließt (nur eigene Eingaben = höchstens Self-XSS, keine reale Bedrohung) und CSP +
> gehärtetes `esc()` aktiv sind, ist das tolerierbar: der Exploit-Pfad (Inline-Handler)
> ist durch die CSP tot. `esc()` bleibt an **jeder** Einsetzstelle von Freitext Pflicht.

#### Regel 2: Content Security Policy (CSP)

In `frontend/index.html` wird im `<head>` eine strikte CSP gesetzt:

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
```

Das verhindert Inline-Scripts (`<script>…</script>` im DOM) selbst dann, wenn durch
einen Bug doch einmal `innerHTML` verwendet wird, **Defense-in-Depth**, genau wie bei
der Doppel-Kaskade (B.7). Die eigene `app.js` (als externe Datei) läuft weiterhin
normal.

> **✅ ERLEDIGT (2026-06-08):** CSP ist in `frontend/index.html` gesetzt, sogar
> strenger als oben: zusätzlich `connect-src 'self'` (das Frontend macht selbst nie
> Netzwerk-Calls; aller Traffic läuft über das Python-Backend), sowie
> `object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none';`.
> Wichtig: `'unsafe-inline'` steht **nur** bei `style-src` (das Frontend nutzt inline
> `style=""`), **nicht** bei `script-src`, dadurch bleiben eingeschleuste
> Inline-Handler (`<img onerror=…>`) wirkungslos. Verifiziert: `app.js` nutzt
> Event-Delegation über `data-act`, **keine** Inline-`on*`-Handler.
>
> **⚠️ Zu prüfen beim nächsten Start:** Manche PyWebView-Versionen injizieren die
> `window.pywebview`-Bridge per Skript. Falls die CSP die Bridge bricht (Symptom:
> `get_state()` schlägt fehl, App bleibt bei „Unpacking vault…" hängen), mit
> `NOATODO_DEBUG=1` die Konsole prüfen. Die Bridge läuft normalerweise in einem
> privilegierten Kontext außerhalb der Seiten-CSP; sollte es doch klemmen, ist der
> Fix ein gezielter Skript-Hash, **nicht** `'unsafe-inline'` bei `script-src`.

#### Regel 3: Parametrisierte SQL-Queries (Anti-SQL-Injection)

**Alle** SQL-Statements in `backend/db.py` verwenden ausschließlich parametrisierte
Queries mit `?`-Platzhaltern. Keine String-Formatierung,
kein f-String, kein `.format()` für Werte, **ausnahmslos**:

```python
# ✅ Sicher: Wert wird als Daten behandelt, nie als SQL
cursor.execute("INSERT INTO tasks (id, text) VALUES (?, ?)", (task_id, task_text))

# ❌ Verboten: öffnet SQL Injection
cursor.execute(f"INSERT INTO tasks (id, text) VALUES ('{task_id}', '{task_text}')")
```

#### Regel 4: Längen- und Zeichenvalidierung der Eingaben

Die Bridge (`api.py`) validiert Eingaben vor dem Schreiben (Gate G20):

- **Maximale Textlänge** pro Feld (Task-Text ≤ 4096 Zeichen, Listenname ≤ 256; kein
  Meta-Feld mehr, N11.1.3).
  Überlange Werte werden abgeschnitten.
- **Steuerzeichen** (U+0000-U+001F außer Newline/Tab) werden entfernt.

#### Regel 5: Zukunftssicherung (Prompt Injection)

Falls in späteren Versionen KI-Features hinzukommen (Zusammenfassung, Priorisierung),
darf **kein** Task-Text direkt in einen System-Prompt eingesetzt werden. Freitext-
Inhalte müssen in einem separaten, klar abgegrenzten User-Kontext an das Sprachmodell
übergeben werden.

> **Auswirkung auf die Funktionalität: Null.** Alle Regeln sind rein defensiv.
> Task-Texte werden exakt gleich angezeigt, die App verhält sich identisch, nur dass
> bösartiger Inhalt wirkungslos bleibt. Es ist wie das Schloss an der Tür: die Tür
> funktioniert genauso, aber ungebetene Gäste kommen nicht rein.

---

### B.10 Bedrohungsmodell (verbindlich, Gate G30, ergänzt 2026-07-13)

> **Warum dieser Abschnitt existiert (Plananalyse S4):** Der Plan hat bisher
> Gegenmassnahmen definiert, ohne je zu sagen, **gegen wen**. Das hatte drei
> messbare Folgen: G18 versprach mehr, als es halten kann; für Malware im eigenen
> Konto entstanden Schein-Gegenmassnahmen (die G26-Lektion: ein Schutz, der real
> nichts abwehrt, aber die App kaputtmacht); und der Panik-Endschirm behauptet einen
> Wipe, den es bei "Finish" nicht gab, ohne dass irgendwo stand, warum das trotzdem
> gewollt ist. **Regel ab sofort:** Jede neue Sicherheitsmassnahme und jedes neue
> Gate muss sagen, **welche Angreiferklasse** es adressiert. Massnahmen ohne Klasse
> sind keine Sicherheit, sondern Theater, und werden nicht gebaut.

#### B.10.1 Was geschützt wird

Schutzgut sind **die Aufgabeninhalte** (Task-Texte, Listennamen) und der Umstand,
**dass und wie** die App genutzt wird (Nutzungsprofil, Metadaten). Kein Schutzgut
sind: die Existenz der App auf dem Rechner (sichtbar, das ist Absicht), das Programm
selbst und der Quellcode (Kerckhoffs, siehe G27).

Die App ist rein lokal: es gibt keinen Server, kein Konto, keinen Sync, keinen
eingehenden Netzwerk-Kanal. Damit entfallen ganze Angreiferklassen (Server-Einbruch,
Man-in-the-Middle, Konto-Übernahme) ersatzlos. Was bleibt, ist **lokal** und
überschaubar.

#### B.10.2 Angreiferklassen (K1 bis K6)

| Klasse | Wer / was | Wirksame Massnahmen | Was bleibt (ehrlich) |
|---|---|---|---|
| **K1** | **Dieb der Datei oder der Platte** (Laptop weg, SSD ausgebaut, `tasks.db.enc` kopiert). Hat die Datei, nicht das laufende System. | Doppel-Kaskade (B.7), Argon2id-Kosten (G8), Domain-Separation (G15), `.enc`-Format mit frischer Nonce (G16), DPAPI-Pepper (G18), kein Verifikations-Hash auf der Platte (G15) | Offline-Rateangriff auf die Passphrase, **falls** der Angreifer zusätzlich an den Pepper kommt (siehe B.10.4, G18-Konditionierung). Ohne Pepper: nach heutigem Stand der Technik chancenlos. |
| **K2** | **Forensik am ausgeschalteten Gerät** (Behörde, Datenrettung, Käufer der gebrauchten SSD). Sucht Reste ausserhalb des Tresors. | In-Memory-DB statt Temp-Arbeitskopie (G6), `PROFILE_DIR` sicher wischen (G14), Killswitch als reine Datei-Löschung (N11.8.1), Pagefile/Hiberfil/Crash-Dumps (G31), Löschen der Dev-Altdaten (G33) | **Ohne BitLocker verliert diese Klasse die App.** SSD-Wear-Levelling macht "sicheres Überschreiben" unzuverlässig; Reste aus der Dev-Phase (A3) und aus Auslagerungsdateien können forensisch überleben. Siehe B.10.4. |
| **K3** | **Person mit kurzem physischen Zugriff** auf den laufenden oder gesperrten Rechner (Mitbewohner, Kollege, Grenzkontrolle mit dem Gerät in der Hand). Hat Zeit in Minuten, nicht in Tagen. | Sperre serverseitig als Allowlist (G13), Auto-Sperre nach Inaktivität (N11.4), Rate-Limit-Leiter, **persistiert über Neustarts** und gegen Uhr-Rückstellung abgesichert (N11.4.1), Lock beim Start, Panik-Knopf, kein Klartext im Fenstertitel (Titel-Regel in B.4, A7), Release ohne DevTools/Debug-Schalter (G34) | Ist die App **entsperrt** und der Nutzer weg, ist alles offen (dagegen hilft nur die Auto-Sperre, Default 15 min). Ein Foto vom Bildschirm ist nicht verhinderbar (siehe Nicht-Ziele). Die Rate-Limit-Leiter bremst **nur diese Klasse**: Wer die Datei kopieren kann, rät offline (K1), dort greift keine Leiter, sondern nur Argon2id + Pepper; wer Dateizugriff hat, kann zudem `config.json` löschen und die Leiter zurücksetzen (N11.4.1). |
| **K4** | **Malware im selben Windows-Benutzerkonto** (Infostealer, Trojaner, RAT). Läuft mit **denselben Rechten wie die App**. | Keine wirksamen. Härtungen (CSP, `esc()`, G13, G23, G27, G34) erhöhen nur die Hürde und verhindern **stille Persistenz**, nicht den Zugriff. | **Ausdrückliches Nicht-Ziel, siehe B.10.3.** |
| **K5** | **Reverse-Engineer der `.exe`** (analysiert das Programm, sucht Hintertüren, statische Schlüssel, schwache Ableitung). | Binary-Härtung (G27), aber vor allem: **es gibt kein Geheimnis im Code.** Sicherheit beruht ausschliesslich auf Passphrase + Pepper + Verschlüsselung (Kerckhoffs). `DEV_AES_KEY` muss dafür restlos verschwinden (G9). | Nichts, was schadet. Wer den Code vollständig versteht, kommt an die Daten kein Stück näher. Genau so ist es gedacht. |
| **K6** | **Zwangs-Situation** (jemand mit Autorität oder Gewalt fordert, dass der Nutzer die App öffnet oder die Passphrase nennt). | Panik-Flow (N10): Raum leeren, Wipe-Schirm, Endschirm; Killswitch als echte, unwiderrufliche Löschung; Reset auf dem Lock-Screen (N11.3) | Gegen einen Angreifer, der wartet und zusieht, hilft keine Software. Der Panik-Flow kauft Sekunden und deckt den Bildschirm zu; er ersetzt keine Plausible Deniability (die die App bewusst **nicht** bietet, siehe B.10.5). |

#### B.10.3 Ausdrückliche Nicht-Ziele (wird nicht verteidigt, und das ist eine Entscheidung)

Ein Nicht-Ziel ist kein Versäumnis. Es ist die Zusage, dafür **keine
Schein-Gegenmassnahme** zu bauen. Genau daran ist G26 gescheitert: ein Schutz, der
die reale Bedrohung (Foto vom Bildschirm) nicht abwehrte, aber die App auf manchen
GPUs unbenutzbar machte.

1. **Malware oder ein Angreifer mit Codeausführung im selben Benutzerkonto (K4).**
   Wer als "der Nutzer" läuft, liest den Pepper über `keyring` (DPAPI entschlüsselt
   für dieses Konto), hängt sich in die Tastatur, liest den entsperrten
   Prozessspeicher oder tauscht `app.js` aus (A5). Dagegen kann eine Anwendung im
   selben Sicherheitskontext nichts ausrichten, **auch keine App, die das behauptet.**
   Die Verteidigung liegt eine Ebene tiefer: sauberes Windows, keine Schadsoftware.
   Zulässig bleiben Massnahmen, die **Persistenz und stilles Mitlesen erschweren**
   (Frontend-Hashes gegen ein signiertes Manifest, G27/A5; keine DevTools im Release,
   G34), aber sie werden nie als Schutz gegen K4 **verkauft**.
2. **Ein kompromittiertes oder feindliches Windows** (Admin-Angreifer, Kernel-Malware,
   manipulierte WebView2-Runtime). Gleiche Begründung, eine Ebene grober.
3. **Optische und physische Kanäle:** Foto vom Bildschirm, Schulterblick, Kamera im
   Raum, Hardware-Keylogger, Evil-Maid/DMA-Angriffe auf das laufende Gerät. Der
   Bildschirm zeigt Klartext, das ist der Zweck der App. (Deshalb G26 verworfen.)
4. **Der bewusste Export.** `export_list`/`export_all` schreiben Klartext-Dateien.
   Das ist gewollt und der ausdrückliche Wunsch des Nutzers; ab dem Speichern liegt
   die Datei ausserhalb des Tresors und ausserhalb dieses Modells.
5. **Vergessene Passphrase und verlorenes Windows-Konto.** Kein Recovery, kein
   Backdoor-Schlüssel, kein Support (N11.3). Das ist Teil des Schutzes gegen K1/K2,
   nicht ein fehlendes Feature.
6. **Retention bei Dritten.** Legt der Nutzer den Tresor in einen Cloud-Sync-Ordner,
   konserviert der Anbieter Versionen; Killswitch und Reset löschen dort nichts (A2).
   Die App warnt davor (G32), verhindern kann sie es nicht.
7. **Plausible Deniability / versteckter Zweit-Tresor.** Nicht geplant, siehe B.10.5.
8. **Copy aus Eingabefeldern (G34 (d), 2026-07-15).** Eingabefelder bleiben
   selektierbar (Phase 6.5 Punkt 3, bewusst akzeptiert); ihr natives `Strg+C` landet
   ungehärtet in der Win+V-History und ggf. im Cloud-Clipboard. G23 härtet nur den
   Rail-Kopierpfad, G34 schliesst DevTools, `Strg+P` und das Standard-Kontextmenü;
   der Eingabefeld-Kanal bleibt offen und wird nicht als geschlossen dargestellt.
   Wer einen Task-Text vertraulich kopieren will, nutzt den Rail-Button (G23).

#### B.10.4 Voraussetzungen (was der Nutzer beisteuern muss)

Die Zusagen dieses Plans gelten **nur** unter diesen Bedingungen. Sie gehören in die
Einrichtungs-UI (Phase 8) und ins Status-Modal, nicht nur in dieses Dokument.

1. **Geräteverschlüsselung (BitLocker oder Windows-Geräteverschlüsselung) ist dringend
   empfohlen, faktisch Voraussetzung gegen K1 und K2.** Ohne sie liegen Pagefile,
   Ruhezustandsdatei und Crash-Dumps im Klartext auf der Platte (A1), Dev-Reste
   bleiben forensisch auffindbar (A3), und der DPAPI-Pepper hängt allein an der
   Stärke des Windows-Anmeldepassworts. Der BitLocker-Status ist per WMI abfragbar
   und wird im Status-Modal angezeigt (G31).
2. **Starkes Windows-Anmeldepasswort.** Es schützt den DPAPI-Speicher, in dem der
   Pepper liegt.
3. **Starke, einmalige Passphrase (Mindestlänge 12, N11.3).** Sie ist der einzige
   Faktor, den ein Angreifer mit Pepper-Zugriff noch raten muss. Argon2id-Kosten (G8)
   verteuern jeden Versuch, sie ersetzen aber keine kurze, geratene Passphrase.
4. **Ein nicht kompromittiertes Windows** und keine zweite Person mit Adminrechten
   auf demselben Rechner (folgt aus K4/Nicht-Ziel 1 und 2).

> **Konditionierung der G18-Zusage (S4, Punkt 1):** G18 sagte bisher, wer nur die
> Datei erbeutet, könne "offline **gar nicht** raten". Das gilt **nicht
> unbedingt**. Richtig ist: Der Pepper liegt DPAPI-geschützt im Credential Manager,
> also **im Windows-Profil auf derselben Platte**. Wer nur die Datei `tasks.db.enc`
> kopiert (typischer K1-Fall: Datei per USB mitgenommen), hat den Pepper nicht und
> kann offline nichts anfangen. Wer dagegen die **ganze Platte** hat (gestohlener
> Laptop, ausgebaute SSD) und die Platte ist **nicht** mit BitLocker verschlüsselt,
> kann den DPAPI-Master-Key offline angreifen; dessen Schutz hängt dann an der Stärke
> des Windows-Anmeldepassworts. Fällt das Windows-Passwort, fällt der Pepper, und
> übrig bleibt allein die Passphrase (immerhin durch Argon2id teuer, G8).
> **Verbindliche Formulierung überall (Gate, UI, Doku):** "Der Pepper macht einen
> Offline-Angriff aussichtslos, **solange** der Angreifer nur die Tresordatei hat
> oder die Platte mit BitLocker verschlüsselt ist." Kein "gar nicht" ohne diese
> Bedingung.

#### B.10.5 Der Panik-Endschirm bleibt ehrlich (kein behaupteter Wipe, Entscheidung N11.17)

Der Panik-Endschirm bietet zwei Ausgänge: **Finish** (beendet nur, alle Daten
bleiben) und **Killswitch** (löscht wirklich). Seit 2026-07-17 (G22) tragen
Wipe-Schirm und Endschirm ehrliche Texte ("Clearing workspace" / "Workspace
cleared").

**Entscheidung N11.17 (2026-07-21): diese ehrlichen Texte bleiben dauerhaft.** Der
früher (N10.3) für Phase 8 vorgesehene, bewusst falsche Aussenschirm ("All data
securely wiped" bei "Finish", obwohl die Daten bleiben) wird **nicht** gebaut. Die
Abwägung, die zu dieser Umkehr führt, gehört hierher, nicht in eine UI-Beschreibung:

- **Was für den falschen Text sprach:** Gegen einen flüchtigen Beobachter (K3, teils
  K6) hätte ein "sicher gewiped"-Schirm abschreckend gewirkt und die Situation ohne
  Datenverlust beendet; der Nutzer hätte den Schirm zeigen und **später** immer noch
  den Killswitch drücken können.
- **Was dagegen entscheidet (und jetzt den Ausschlag gibt):** Gegen einen Angreifer,
  der die Platte behält und untersucht (K1/K2 nach K6), wäre die Behauptung eine
  **überprüfbare Lüge**. Findet er die Daten anschliessend doch, steht der Nutzer als
  jemand da, der aktiv getäuscht hat, was seine Lage verschlechtern kann. Der
  abschreckende Nutzen ist bloßes Theater gegen Gelegenheits-Zugriff und wiegt dieses
  konkrete Risiko nicht auf. Wer in einem echten Zwangs-Szenario ist, drückt ohnehin
  den **Killswitch** (echte, unwiderrufliche Löschung), nicht "Finish".
- **Konsequenz für die UI:** Der Endschirm sagt, was wirklich passiert ist
  ("Workspace cleared"), und nichts darüber hinaus. Der Killswitch-Knopf bleibt der
  zweite, bewusst gewählte Ausgang für den echten Ernstfall und wird nicht versteckt.
  **G22 (ehrliche Sicherheits-Behauptungen) gilt damit ohne jede Ausnahme im ganzen
  Plan;** die früher hier verzeichnete einzige G22-Ausnahme entfällt ersatzlos.
- **Plausible Deniability wird nicht gebaut.** Ein versteckter Zweit-Tresor mit
  Schein-Passphrase wäre die einzige echte Antwort auf K6. Er ist bewusst
  **nicht geplant** (Komplexität, und in der Praxis verrät die Dateigrösse ihn
  ohnehin oft). Wer K6 ernsthaft fürchtet, nutzt den Killswitch.

#### B.10.6 Gate-zu-Klassen-Zuordnung (jedes Gate kennt seinen Gegner)

Diese Tabelle ist der geforderte Rückbezug ("jedes Gate referenziert seine Klasse").
**Pflicht für neue Gates:** ohne Eintrag hier wird kein Gate aufgenommen.

| Gate | Klassen | Wirkt gegen |
|---|---|---|
| G6 (In-Memory-DB) | K2 | Temp-Datei-Reste auf der SSD |
| G7 (Hex-Raw-Key) | K1 | Schwächung der Ableitung durch doppeltes KDF |
| G8 (Argon2id-Kosten, Passphrase-Politik) | K1 | Offline-Brute-Force |
| G9 (`DEV_AES_KEY` weg) | K1, K2, K5 | "Verschlüsselung", die mit einem Repo-String aufgeht |
| G11 (Deps pinnen) | K4 (vorgelagert) | Supply-Chain: getauschte Lib = Totalkompromittierung |
| G12 (Navigation abriegeln) | K4 | Exfiltration über eine erzwungene externe Navigation |
| G13 (Lock als Allowlist) | K3 | Ein JS-Aufruf, der den Lock-Screen umgeht |
| G14 (WebView2-Spuren) | K2 | Task-Texte im Browser-Cache, an beiden Schichten vorbei |
| G15 (HKDF, kein Verifikations-Hash) | K1 | Offline-Orakel auf der Platte |
| G16 (`.enc`-Format, Nonce, atomar) | K1 | Nonce-Wiederverwendung; Datenverlust beim Absturz |
| G17 (Write-back) | (Robustheit) | Kein Angreifer: Crash-Sicherheit |
| G18 (DPAPI-Pepper) | K1 | Offline-Raten **ohne** Plattenzugriff (konditioniert, B.10.4) |
| G19 (Single-Instance) | (Robustheit) | Kein Angreifer: Korruption durch zwei Instanzen |
| G20 (Eingabe-Validierung) | K4 (Härtung) | Fehlerhafte/bösartige Eingaben an der Bridge |
| G21 (Export-Härtung) | (Korrektheit) | Reservierte Dateinamen, kaputte Export-Struktur |
| G22 (ehrlicher Status) | (Nutzer-Ehrlichkeit) | Falsche Sicherheitsanzeige. Ohne Ausnahme, auch der Panik-Endschirm bleibt ehrlich (N11.17, B.10.5) |
| G23 (Clipboard-Hygiene) | K2, K4 | Win+V-History und Cloud-Clipboard als Auslass-Kanal |
| G25 (RAM-Schlüssel-Hygiene) | K2 | Schlüssel im Speicherabbild, best effort |
| G26 (Screenshot-Schutz) | ❌ **keine** | Nichts. Genau deshalb verworfen: Massnahme ohne Klasse. |
| G27 (Binary-Härtung) | K5, K4 (Persistenz) | Manipulation der `.exe`/Assets, nicht Geheimhaltung |
| G28 (Verschlüsselungs-Beweis) | K1, K2 | Die Annahme, es sei verschlüsselt, ohne es zu prüfen |
| G29 (Fehler-Hygiene) | K3, K5 | Interna/Pfade in Fehlermeldungen und Logdateien |
| **G30 (dieser Abschnitt)** | alle | Massnahmen ohne Gegner; Zusagen ohne Bedingung |
| G31 (Pagefile/Hiberfil/Dumps) | K2 | RAM-Inhalte, die an allen Schichten vorbei auf die Platte gelangen |
| G32 (Vault-Ort, Cloud-Warnung) | K1 (Dritte) | Versionshistorie beim Cloud-Anbieter |
| G33 (Dev-Altdaten löschen) | K2 | Die mit öffentlichem Schlüssel lesbare `tasks.db` von heute |
| G34 (Release-Härtung) | K3, K4 | DevTools, Strg+P-Druck-Export, Kontextmenü, Textselektion |
| G35 (Sperr-/Beenden-Sequenz) | K3 | Lücken zwischen Lock, Quit, Panik und Fenster-X |

> **Lesehinweis zu G29 bis G35:** Diese Nummern stammen aus der Plananalyse (Teil 6)
> und sind inzwischen **alle** als Gates in B.9 aufgenommen: G29, G30 und G35 am
> 2026-07-13, G31 bis G34 am 2026-07-15 (Befunde A1 bis A4/A6; A5 wurde in G27
> eingearbeitet, A7 als Titel-Regel in B.4). Die Arbeitsregel bleibt für alle
> künftigen Vorschläge: ein neues Gate trägt sich **zuerst** hier mit seiner
> Angreiferklasse ein, damit beim Aufnehmen nichts ohne Klasse durchrutscht. Ein
> verworfener Vorschlag behält seine Zeile und wird als verworfen markiert (siehe
> G26: "keine Klasse", genau deshalb verworfen).

### B.11 Unverschlüsselte Konfiguration (`config.json`)

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.15 `config.json`: Schema, Fehlerfaelle, unerreichbarer Tresor (2026-07-13, U2-Entscheid) [Sec]“ samt N11.15.1 bis N11.15.6; der tote Zeiger „N11.16“ ist dabei auf die Entsperr-Fehlerlogik N6 in B.2 umgebogen (Umbauplan A.1). Register: Anhang 1.)*

*Loest U2. Die unverschluesselte Konfig wurde in N11.3 (Tresor-Pfad), N11.4.1 (Rate-Limit)
und N11.10 (Funk-Ausgangszustand) dreimal benutzt, ohne je definiert zu sein. Offen waren:
Schema samt Versionsfeld, Verhalten bei fehlender/korrupter Datei, Verhalten bei
unerreichbarem Tresor-Pfad (USB-Stick abgezogen), Wechseldatentraeger-/UNC-Pfade und der
Store-Python-Redirect (Befund V8).*

#### N11.15.1 Ort, Inhalt, Schema

- **Ort:** `%LOCALAPPDATA%\NoaToDo\config.json`, aufgeloest ueber **eine** Hilfsfunktion
  (`config_path()`), nie hartkodiert.
- **Inhalt: nur nicht-geheime Startinfos.** Es liegen dort **niemals** Aufgaben-/Listentexte,
  Passphrase, Schluessel, Pepper, Salt oder Argon2-Parameter (die gehoeren in den
  Tresor-Header, G16, bzw. in den Credential Manager, G18). Wer die Datei liest, erfaehrt
  **wo** der Tresor liegt, nicht was drin steht; das ist hingenommen (K1/K3 finden eine
  `.enc`-Datei ohnehin).
- **Verbindliches Schema (Version 1):**

```json
{
  "version": 1,
  "vault_path": "D:\\Tresor\\tasks.db.enc",
  "radio_baseline": null,
  "unlock_ratelimit": { "fails": 0, "stage": 0, "next_try_at": null, "locked_at": null, "duration": 0 }
}
```

- `version` (int, Pflicht): Schema-Version. **Unbekannt oder groesser als bekannt** heisst:
  eine neuere App hat geschrieben, die Datei wird **nicht** angefasst (siehe N11.15.2).
- `vault_path` (str, Pflicht): absoluter Pfad auf `tasks.db.enc`.
- `radio_baseline` (Objekt oder `null`, N11.10): gesetzt **nur**, solange die App den
  Flugmodus selbst eingeschaltet hat, Form
  `{ "wifi": true, "bluetooth": true, "set_at": "<UTC-ISO8601>" }`. Beim Wiederherstellen
  im `teardown` (Schritt 10) wird der Eintrag auf `null` gesetzt. Findet ein Start hier
  einen Rest (Absturz), stellt er den Funk-Ausgangszustand her und raeumt den Eintrag weg.
- `unlock_ratelimit` (Objekt, N11.4.1): `{fails, stage, next_try_at, locked_at, duration}`,
  geloescht nur durch erfolgreiches `unlock()` und durch `reset_vault()`.
- **Schreiben immer atomar und vollstaendig:** `config.json.tmp` schreiben, `flush()` +
  `os.fsync()`, dann `os.replace()` (dasselbe Verfahren wie G16). Ein Absturz mitten im
  Schreiben darf nie eine halbe Datei hinterlassen. Einziger Schreiber ist die eine Instanz
  (Single-Instance-Mutex, G19).

#### N11.15.2 Fehlende, korrupte oder zu neue Datei

- **Datei fehlt komplett** (frischer Rechner, nach Reset/Killswitch): **Erststart**, also
  Onboarding (N11.13). Kein Fehlerbildschirm, das ist der Normalfall.
- **Datei existiert, ist aber unbrauchbar** (kein gueltiges JSON, `version` unbekannt/zu
  neu, Pflichtfeld fehlt oder hat den falschen Typ): **kein** stiller Erststart. Die Datei
  wird **nicht ueberschrieben**, sondern nach `config.json.bad` umbenannt (genau eine
  Generation), und der Boot endet im **Fehlerbildschirm** (N6) mit dem ehrlichen Text
  „Konfiguration unlesbar, der Tresor-Pfad ist unbekannt" und **zwei** Auswegen:
  1. **Tresor suchen**: nativer Datei-Dialog, der Nutzer zeigt auf seine `tasks.db.enc`;
     der Pfad wird in eine frische `config.json` geschrieben, danach normaler Lock-Screen.
  2. **Neuen Tresor anlegen**: Onboarding, **mit dem ausdruecklichen Hinweis, dass ein
     eventuell vorhandener alter Tresor NICHT geloescht wird** und weiter dort liegt, wo er
     liegt.
  **Begruendung:** Ein stiller Erststart saehe fuer den Nutzer wie Datenverlust aus und
  wuerde ihn dazu verleiten, einen zweiten Tresor anzulegen, waehrend der echte unberuehrt
  auf der Platte liegt. Ehrlichkeit vor Bequemlichkeit.
- **Ehrliche Konsequenz (steht schon in N11.4.1, B.8.4):** Wer die Datei loeschen **oder
  beschaedigen** kann, setzt damit auch die Rate-Limit-Leiter zurueck (der `.bad`-Weg oben
  schreibt nach dem Wiederfinden eine frische, leere Leiter). Das ist hingenommen; genau
  dieser Angreifer kopiert lieber gleich den Tresor und raet offline (K1). Die Leiter wird
  nie als Schutz gegen K1 verkauft (N11.4.1).

#### N11.15.3 Tresor-Pfad unerreichbar (USB-Stick weg, Netzlaufwerk down)

- **Unerreichbar ist NICHT dasselbe wie „kein Tresor".** Ist `vault_path` gesetzt, die Datei
  aber nicht da (Laufwerk fehlt, Ordner geloescht, Netzlaufwerk offline), fuehrt das
  **niemals** ins Onboarding, sondern in den **Fehlerbildschirm** (N6): „Tresor nicht
  erreichbar" plus den Pfad, mit drei Auswegen: **Erneut versuchen** (Stick wieder
  einstecken, ein Klick), **Pfad neu waehlen** (Datei-Dialog, falls der Tresor umgezogen
  ist) und **Neuen Tresor anlegen** (Onboarding, wieder mit dem Hinweis, dass der alte
  Tresor nicht geloescht wird).
- **Erweiterung von `get_boot_state()` (N11.13):** Der Boot-Zustand ist damit
  **vierwertig**: `{ state: 'onboarding'|'locked'|'unlocked'|'vault_error', vault_path,
  reason }` mit `reason` aus `config_damaged`, `vault_unreachable`, `vault_damaged`. Das
  ist eine Ergaenzung, kein Widerspruch: `get_state()` bleibt zweiwertig (G13), und die
  drei alten Zustaende behalten ihre Bedeutung. Die Vokabeln sind dieselben wie in der
  Entsperr-Fehlerlogik (N6, jetzt in B.2).

#### N11.15.4 Wechseldatentraeger, Netz- und UNC-Pfade

Erlaubt, aber **nur mit Warnung** bei der Wahl (dieselbe Stelle wie die Cloud-Warnung aus
G32, `choose_vault_dir()`): Bei Wechseldatentraegern (`DRIVE_REMOVABLE`) und Netz-/UNC-Pfaden
(`\\server\share`, `DRIVE_REMOTE`) warnt der Dialog, dass (a) die App bei fehlendem
Laufwerk im Fehlerbildschirm landet (N11.15.3), (b) das sichere Ueberschreiben beim
Killswitch/Reset dort **nicht** zuverlaessig ist (fremdes Dateisystem, Server-Cache,
Schattenkopien), und (c) die Datei dort fuer andere leichter erreichbar ist (K1). Die
Warnung ist Pflicht, das Verbot nicht. **Folge fuer G17:** Ein fehlgeschlagener Write-back
(Stick mitten im Betrieb abgezogen) ist **kein** stiller Datenverlust, sondern fuehrt in den
N6-Fehlerbildschirm mit der Moeglichkeit, den Tresor an einem anderen Ort zu speichern.

#### N11.15.5 Store-Python-Redirect (Befund V8)

Laeuft die App unter Microsoft-Store-Python (heutiges Entwickler-Setup), werden Schreibzugriffe
auf `%LOCALAPPDATA%` umgeleitet; `config.json` liegt dann real unter
`...\Packages\PythonSoftwareFoundation.Python.3.11_*\LocalCache\Local\NoaToDo\`. **Im Prozess
ist das transparent** (dieselbe API sieht dieselbe Datei), fuer externes Werkzeug und fuer den
spaeteren `.exe`-Build (Phase 9, **kein** Redirect) nicht. Regeln: (a) Der Pfad wird nur ueber
`config_path()` aufgeloest, nie hartkodiert, auch nicht in Tools. (b) Es wird **keine
Migration** gebaut: Wer vom Dev-Python zur `.exe` wechselt, findet keine Konfig, landet also
im Onboarding und zeigt mit „Tresor suchen" (N11.15.2) auf seine vorhandene `tasks.db.enc`.
Das ist bewusst so, ein Auto-Import aus einem fremden Paketpfad waere mehr Risiko als Nutzen.
(c) Dasselbe gilt fuer `PROFILE_DIR` (G14), das denselben Redirect erlebt. (d) **Aufraeumen ja,
Migration nein (V8, 2026-07-15):** Der Erststart der Phase-9-`.exe` entfernt die bekannten
alten Redirect-Pfade **einmalig** (den umgeleiteten `NoaToDo\webview`-Ordner und eine dortige
`config.json`), liest sie aber nie ein; eine `tasks.db.enc` wird dabei **niemals** angefasst
(der Tresor liegt am vom Nutzer gewaehlten Ort, ein Loeschen waere Datenverlust). Ohne diesen
Schritt blieben der alte umgeleitete Profilordner und die alte Konfig fuer immer liegen,
niemand wischt sie je (G14-Luecke).

#### N11.15.6 Onboarding zeigt auf einen Ordner mit vorhandenem Tresor (Datenverlust-Schutz)

**Die Ratestelle (U1-Nachschlag, 2026-07-15):** Das Onboarding laeuft, wenn `config.json`
fehlt (N11.15.2). Die Tresordatei `tasks.db.enc` kann dann aber physisch trotzdem am alten
Ort liegen: genau der von N11.15.5 selbst erzeugte Fall (Wechsel Dev-Python zur `.exe`,
Config weg, Tresor noch da), ebenso nach manuell geloeschter `config.json`. Waehlt der Nutzer
im Onboarding-Schritt 1 diesen Ordner, war bisher offen, was `create_vault(path, passphrase)`
tut. Ein blindes „`tasks.db.enc` unter `path` schreiben" wuerde den vorhandenen, verschluesselten
Tresor **still und unwiderruflich ueberschreiben**, also echten Datenverlust ausloesen und
zugleich das N11.15.2-Versprechen brechen („ein vorhandener alter Tresor wird NICHT geloescht").

**Entscheidung (Security first, U1):** Ein bestehender Tresor wird beim Anlegen **nie**
ueberschrieben. Zwei Riegel, Guertel und Hosentraeger:

- **UI-Weiche in `choose_vault_dir()`:** Der Backend-Dialog prueft, ob im gewaehlten Ordner
  schon eine `tasks.db.enc` liegt, und meldet `has_vault:true`. Der Onboarding-Screen bietet
  dann **nicht** „neuen Tresor anlegen" an, sondern nur „**Diesen Tresor oeffnen**": der Pfad
  wandert in eine frische `config.json`, und der Boot geht in den normalen **Lock-Screen**
  (dasselbe Ergebnis wie „Tresor suchen", N11.15.2). Wer stattdessen wirklich neu anlegen will,
  muss einen anderen, leeren Ort waehlen.
- **Backend-Riegel in `create_vault()`:** Existiert unter `path` schon eine `tasks.db.enc`,
  bricht die Methode **vor** jedem Schreiben mit `invalid` ab und ruehrt die Datei nicht an.
  Das faengt jeden Aufruf ab, der an der UI-Weiche vorbeikommt (Bridge-Aufruf von Hand,
  Renn-Fall, kuenftiger Code-Pfad). Der Schreibvorgang selbst bleibt atomar (`.tmp` +
  `os.replace`, wie G16/N11.15.1), sodass auch ein Abbruch mittendrin nie eine halbe Datei
  hinterlaesst.

**Abgrenzung:** Das gilt nur fuer das **Anlegen** (Onboarding/`create_vault`). Der Reset
(`reset_vault()`) loescht den Tresor bewusst und legt danach neu an, das ist gewollt und kein
Widerspruch. Das Ueberschreiben beim regulaeren Write-back eines bereits geoeffneten Tresors
(G16/G17) ist ebenfalls nicht gemeint, dort ist es der Sinn der Sache.


## TEIL C: Baufolge (Phase 0 bis 9)

### Phase 0: Projektgerüst & Umgebung

**Ziel:** Ordnerstruktur und Abhängigkeiten stehen, ein leeres Fenster lässt sich öffnen.

**Tun:**
1. Struktur anlegen (im `Code/`-Ordner des Projekts):
   ```
   Code/
   ├── main.py
   ├── requirements.txt
   ├── backend/
   │   ├── __init__.py
   │   ├── api.py
   │   ├── db.py
   │   └── security.py
   ├── frontend/
   │   ├── index.html
   │   ├── style.css
   │   ├── app.js
   │   └── fonts/            # JetBrains Mono + Space Grotesk als .woff2
   └── data/                 # tasks.db entsteht hier automatisch
   ```
2. `requirements.txt`: `pywebview`, `keyring` (DPAPI-Pepper, siehe G18),
   **`sqlcipher3-wheels`** (Schicht 1, AES-256, Pflicht; importiert als `import sqlcipher3`.
   **Nicht** `sqlcipher3-binary` nehmen: das hat keine Windows-Wheels und die Installation
   scheitert. `sqlcipher3-wheels` bringt sie mit, bei identischer API), **`cryptography`** (Schicht 2,
   ChaCha20-Poly1305, Pflicht), `argon2-cffi` (Passphrase-Hash + Schlüsselableitung).
   Verschlüsselungs-Design: **Doppel-Kaskade, siehe B.7.**
3. Virtuelle Umgebung anlegen, Abhängigkeiten installieren.

**Abhaengigkeit fuer den echten Flugmodus (Etikett N11.5/U14, 2026-07-15; wortgleich umgezogen in Umbau-Etappe 3):**

  - **Neue Abhaengigkeit, benannt und gepinnt (G11-relevant).** Python braucht ein
    WinRT-Projektionspaket; heute fehlt das in Phase 0 / `requirements` / G11. Gewaehlt
    werden die **modularen PyWinRT-Pakete** (kleinere Abhaengigkeitsflaeche als das
    Sammelpaket `winsdk`, im Zweifel pro Sicherheit die schmalere Wahl):
    `winrt-runtime`, `winrt-Windows.Devices.Radios`, `winrt-Windows.Devices.Enumeration`
    sowie `winrt-Windows.Foundation` (fuer die `IAsyncOperation`-Awaits). Alle werden in
    `requirements.txt` **und** exakt versionsgepinnt in `requirements.lock.txt`
    aufgenommen und fallen unter die Pinning-/Supply-Chain-Pruefung aus **G11**.
    `winsdk` bleibt nur die dokumentierte Rueckfalloption, falls die modularen Pakete auf
    der Zielplattform nicht sauber installieren.

> **🔒 PFLICHT-GATE für Phase 0: G11 (Supply Chain, Abhängigkeiten pinnen).**
> Definition, Status und Prüfweg ausschliesslich in der normativen Gate-Tabelle in
> B.9 (Regel aus Plananalyse S1). Stand 2026-07-13: erfüllt über
> `requirements.lock.txt`; das Hash-Checking im Release-Build folgt in Phase 9.

**Abnahme:** `python main.py` öffnet ein leeres PyWebView-Fenster ohne Fehler.
**G11:** Alle Abhängigkeiten in `requirements.txt` sind versions-gepinnt.

---

### Phase 1: Datenbank (`backend/db.py`)

**Ziel:** SQLite-Schema steht, CRUD-Funktionen existieren, ein frischer Tresor startet
leer (keine Demo-Daten, N11.1.4).

> **Wichtig:** Die Datenbank ist von Anfang an **verschlüsselt** (Doppel-Kaskade, B.7).
> In dieser Phase wird nur **Schicht 1** (SQLCipher/AES-256) gebaut; die äußere
> ChaCha20-Schicht und das echte Passphrase-Handling kommen in Phase 8 dazu. In der
> Entwicklung darf man mit einer festen Test-Passphrase / einem festen Test-`aes_key`
> arbeiten.

**Tun:**
1. `connect(aes_key)`, öffnet die SQLCipher-Arbeitskopie, setzt direkt nach dem Öffnen
   `PRAGMA key = ?` (der abgeleitete `aes_key`), dann `PRAGMA foreign_keys = ON`, und
   legt das Schema aus B.1 an, falls noch nicht vorhanden (`CREATE TABLE IF NOT EXISTS`).
   Ohne korrekten Key schlägt der erste Zugriff fehl, genau so soll es sein.
2. Funktionen: `get_lists_with_tasks()`, `add_list`, `rename_list`, `delete_list`,
   `add_task`, `toggle_task`, `edit_task`, `delete_task`, `reorder`,
   `get_setting/set_setting`.
3. `get_lists_with_tasks()` liefert genau die Struktur aus B.1 (Liste mit `open`/`done`,
   sortiert nach `position`).
4. **Keine Demo-Seed-Daten** (N11.1.4): ein frischer Tresor startet immer leer. Beim
   allerersten Start werden nur die Default-Settings geschrieben und der `seeded`-Marker
   gesetzt; es werden keine Beispiel-Listen mehr eingespielt. Der leere Zustand zeigt im
   Frontend einen freundlichen Empty-State („Create your first list"). ANHANG 1 alt (jetzt in Anhang 3) ist
   damit hinfällig.
5. Alle `*_at`-Felder als ISO-8601-UTC-Strings.

**Abnahme:** Ein kleines Testskript legt eine Liste + Aufgabe an, schaltet sie auf
erledigt und liest sie korrekt einsortiert (`done`) wieder aus.

---

### Phase 2: Bridge-API (`backend/api.py`)

**Ziel:** Die `js_api`-Klasse mit allen Methoden aus B.2, vorerst rein lokal,
liefert echte Daten aus der DB.

**Tun:**
1. Klasse `Api` mit je einer Methode pro Zeile in B.2. Methoden rufen `db.py` auf und
   geben JSON-fähige Dicts/Listen zurück.
2. Fehler abfangen und als `{ "error": code, "message": … }` zurückgeben.
3. `get_state()` bündelt `get_lists()` + Einstellungen + `online`/`locked`-Flags.
4. Sicherheits-Methoden vorerst als Stubs (geben sinnvolle
   Platzhalter zurück), werden in Phase 8 ausgefüllt.

**Abnahme:** Aus einer Python-REPL lassen sich die Api-Methoden aufrufen und liefern
plausible Daten.

---

### Phase 3: Fenster & Verdrahtung (`main.py`)

**Ziel:** Backend und Frontend hängen zusammen; das Frontend kann `pywebview.api.*`
aufrufen.

**Tun:**
1. `Api`-Instanz erzeugen, `webview.create_window("NoaToDo", "frontend/index.html",
   js_api=api, width=1200, height=800, min_size=(900, 600))`.
2. `webview.start()`, unter Windows die WebView2-Engine.
3. Backend → Frontend: eine Hilfsfunktion, die `window.evaluate_js("window.noa.…")`
   ausführt (für Lock-Events).
4. **Entfaellt, N11.8.4 gilt vorrangig: Win+L loest keine Sperre aus, ein WTS-Hook wird nicht verdrahtet.** (Frueher: Platzhalter für den Windows-Sitzungssperre-Hook, `WM_WTSSESSION_CHANGE`.)

> **🔒 PFLICHT-GATE G12 (WebView-Navigation abriegeln):** Die App ist rein lokal und
> darf das Fenster **nie** woandershin navigieren. Navigations-/New-Window-Events von
> PyWebView/WebView2 abfangen und jede **externe** Navigation (`window.location`/
> `window.open`/Link zu externem `http(s)`) verweigern, nur die lokale `index.html`
> ist erlaubt. Zusammen mit der CSP (`default-src 'self'`) ist das Defense-in-Depth.
> Verdrahtung beim Fensterstart (hier in Phase 3 vorsehen, spätestens in Phase 8 hart).

**Abnahme:** Das geladene `index.html` kann `await pywebview.api.get_state()` aufrufen
und bekommt eine echte Antwort aus dem Backend (kurz in der DevTools-Konsole prüfen).
Auf einem frischen Tresor heisst das **nicht** Demo-Daten (die gibt es seit N11.1.4
nicht mehr), sondern: `lists` ist eine **leere Liste**, und `settings` enthält die
geschriebenen Default-Settings. Genau das ist das Abnahmekriterium, ein leeres `lists`
ist hier der Erfolgsfall und kein Fehler. **G12:** externe Navigation wird verweigert.

---

### Phase 4: Frontend-Gerüst (`frontend/index.html`)

**Ziel:** Grundgerüst der Seite mit `#root`, eingebundenem CSS/JS, ohne fertiges Design.

**Tun:**
1. `index.html`: `<head>` mit `style.css`, `<body>` mit `<div class="app" id="root">`,
   am Ende `<script src="app.js">`.
2. Eine `boot()`-Funktion in `app.js`, die auf `pywebviewready` wartet,
   `get_state()` holt und einen Platzhalter rendert.

**Abnahme:** Beim Start erscheint kurz „Unpacking/Loading" bzw. ein Platzhalter, dann
die geladenen Listennamen als simple `<ul>`, Beweis, dass die Bridge im echten Fenster
funktioniert.

---

### Phase 5: Design-System (`frontend/style.css`) + Fonts

**Ziel:** Das komplette, exakte Aussehen aus dem Konzept ist verfügbar.

**Tun:**
1. **CSS extrahieren:** Die `<style>`-Sektion aus `NoaToDo UI Konzept.html` ist im
   eingebetteten Template hinterlegt (das HTML ist ein „Bundler", der echte Markup-/
   CSS-Inhalt steckt im `<script type="__bundler/template">`-Block als JSON-String, das
   große Asset-Manifest in `<script type="__bundler/manifest">`). Den Template-String
   JSON-dekodieren, daraus die `<style>…</style>` nehmen und nach `style.css` schreiben.
   *Alternativ* das Konzept-HTML einmal im Browser öffnen und das gerenderte CSS
   übernehmen. Wichtig: **unverändert** übernehmen (Tokens aus B.3 sind darin enthalten).
2. **Fonts lokal:** JetBrains Mono (400/500/600/700) und Space Grotesk (400/500/600/700)
   als `.woff2` in `frontend/fonts/` legen und die `@font-face`-`src`-URLs im CSS auf
   diese lokalen Dateien zeigen lassen (statt der UUID-Platzhalter aus dem Bundle). Kein
   externer Google-Fonts-Abruf, passt zu local-first.
3. `data-theme`, `data-density`, `data-sidebar` und `--accent` werden später von `app.js`
   auf `.app` gesetzt. (`data-toolbar` entfällt, N11.7: die Rail schwebt immer, es gibt
   keinen `flush`-Modus. Historisch stand hier auch `data-toolbar`.)

**Abnahme:** Eine statische Test-Markup-Probe (z.B. ein Header + zwei Task-Karten)
sieht exakt aus wie im Konzept, Farben, Schriften, Rundungen, Schatten stimmen in Dark
und Light.

---

### Phase 6: Frontend-Logik (`frontend/app.js`)

**Ziel:** Die komplette Oberfläche wird aus dem Backend-Zustand gerendert und ist
interaktiv. Dies ist die Vanilla-Umsetzung der React-Komponenten.

**Tun (Render-Funktionen, 1:1 zu den Konzept-Komponenten):**

| Konzept-Komponente | Vanilla-Funktion | rendert |
|---|---|---|
| `App` | `boot()` + `render()` | Wurzel, hält den Zustand, setzt `data-*`/`--accent` |
| `Header` | `renderHeader()` | B.4 Header |
| `Sidebar` | `renderSidebar()` | B.4 Sidebar inkl. Inline-„New list" |
| `TaskView` | `renderMain()` | Banner-Pill, Titel, Meta, Sektionen, New-task |
| `Task` | `renderTask()` | eine Aufgaben-Karte |
| `Toolbar` / `ToolBtn` | `renderToolbar()` | die 11 Werkzeug-Buttons + Tooltips |
| `ProfileMenu` | `renderMenus()` | das Profil-Dropdown |
| Modals | `renderModal(kind)` | Status/Rename/Delete/Shortcuts/Settings (Panik ist kein Modal mehr, sondern das PanicPanel an der Rail, N10) |
| `LockScreen` | `renderLock()` | Sperrbildschirm |
| `Undo-Toast` | `pushUndoToast()` | nur der Listen-Undo (N11.2.1); der generische `pushToast()` ist mit N11.16 entfernt |
| `Icons` | `Icons` (Objekt) | die SVG-Icons (siehe **Anhang 4**, 1:1 aus Konzept) |

1. **Zustand** im Frontend ist nur ein Cache (`state = { lists, activeId, settings,
   online, locked, menu, modal, focus, colorOpen, toasts }`). Wahrheit bleibt das
   Backend. Nach jeder mutierenden Aktion: optimistisch updaten **oder** Backend-Antwort
   übernehmen, dann betroffenen Teil neu rendern.
2. **Interaktionen** verdrahten:
   - Sidebar-Auswahl → `activeId` setzen, Main neu rendern.
   - Check-Klick → `toggle_task`, Aufgabe zwischen open/done verschieben (Animation wie
     im Konzept).
   - New-task Enter → `add_task`.
   - New-list (Inline) Enter → `add_list`.
   - Toolbar-Buttons → jeweilige Aktion/Modal (Tabelle B.4).
   - Accent-Swatch → `set_setting('accent', …)` + `--accent` live setzen.
   - Flugmodus-Pill / Globe → `set_online`.
   - Section „Completed" ein-/ausklappen (CSS-Grid-Animation aus dem Konzept).
3. **Tastenkürzel** (B.5) global registrieren, Tipp-Schutz beachten.
4. **Theme-Switch-Flackern** vermeiden: beim Umschalten kurz `.theme-switching` setzen
   (killt Transitions für einen Frame), exakt wie im Konzept.
5. **Backend-Events**: `window.noa.onLocked` definieren.

**Abnahme:** Alle im Konzept sichtbaren Interaktionen funktionieren mit echten Daten:
Aufgaben abhaken, anlegen, Listen wechseln/anlegen/umbenennen/löschen, Toolbar-Aktionen,
Modals, Lock-Screen, Toasts, Theme/Accent/Dichte/Sidebar umschalten (kein
Toolbar-Modus mehr, N11.7), Tastenkürzel, Focus-Modus. Optisch deckungsgleich mit `NoaToDo UI Konzept.html`.

> **Meilenstein:** Nach Phase 6 ist die App als **lokale** To-Do-App voll benutzbar.
> Die Phasen 7-9 ergänzen Export und die Sicherheits-Tiefe. Sie
> sind unabhängig und können einzeln umgesetzt werden. *(Stand 2026-07-17:
> Phase 7 ist abgeschlossen, offen sind die Phasen 8 und 9.)*

---

### Phase 6.5: UX-Nacharbeiten am Prototyp (eingeschoben nach dem Audit vom 2026-06-10)

**Stand-Korrektur:** Abgeschlossen ist **Phase 6** (lokal nutzbarer Prototyp).
(Der frühere Zusatz "Phase 7 ist offen, der Export schreibt keine Datei" ist seit
dem 2026-07-17 überholt: G21c ist umgesetzt, der Export schreibt real, siehe
Phase 7.) Das Kopieren ist
seit dem 2026-06-10 fertig und gehärtet (`copy_task`, siehe Punkt 5 unten).

**Bereits umgesetzt (2026-06-10), gehört ab jetzt zum Soll-Verhalten:**
1. **Aufgaben inline bearbeiten:** Doppelklick auf eine Aufgaben-Karte öffnet
   die Text-Eingabe direkt in der Karte (kein Meta-Feld mehr, N11.1.3). Enter
   speichert (`edit_task`), Esc bricht ab, Klick daneben speichert (bei leerem
   Text: Abbruch). Leerer Text wird abgelehnt.
2. **Aufgaben einzeln löschen: über den Papierkorb in der rechten Tool-Rail**, der
   auf die **ausgewählte** Aufgabe wirkt (`delete_task`), ohne Bestätigung und ohne
   Undo (bewusst: Undo bekommt nur das Listen-Löschen, N11.2). **Korrigiert am
   2026-07-13 (Plananalyse S7):** Hier stand früher „Papierkorb-Button erscheint beim
   Hover auf der Karte". Das war **nie** so gebaut: `renderTask` (`app.js`) rendert
   keinen Papierkorb, die CSS-Klasse `.t-del` und der `del-task`-Handler sind
   ungenutzte Reste (Audit 1.6). Der Plan behauptete damit etwas, das der Code nicht
   tut. **Verbindlicher Stand: Löschen über die Rail.** Der offene UX-Punkt, ob ein
   Hover-Papierkorb auf der Karte nachgerüstet wird (Audit 1.6/3.4), ist in Phase 7
   entschieden (2026-07-17): **nein**, es bleibt bei der Rail-Löschung (eine einzige,
   bewusste Löschgeste; die ungenutzten Reste `.t-del`/`del-task`-Handler sowie
   `.t-grip`/`.title-row`/`.airplane-pill` wurden gelöscht, Audit 1.6).
3. **`Strg+C` als App-Shortcut ersatzlos entfernt** (zweiter Schritt am selben
   Tag, ersetzt die anfängliche "nur ohne Textauswahl"-Variante): Kopiert wird
   nur noch gezielt über den Rail-Button, siehe Punkt 5. Das normale Kopieren
   von markiertem Text in Eingabefeldern bleibt Browser-Standard.
4. **Mini-Modus ist always-on-top** (`window.on_top = True` beim Anheften, beim
   Verlassen wieder `False`), sonst verschwindet das kleine Lesefenster hinter
   der nächsten App.
5. **Aufgaben-Auswahl + gezieltes Kopieren (Gate G23):** Klick auf eine
   Aufgaben-Karte wählt sie aus (Akzent-Rahmen, Wash, Akzent-Balken links;
   erneuter Klick oder Esc hebt auf). Der Rail-Button "Copy task" kopiert
   **nur** die ausgewählte Aufgabe, gehärtet im Backend (`copy_task`: keine
   Win+V-History, kein Cloud-Clipboard, Auto-Clear nach 60 s); ohne Auswahl
   erscheint nur der Hinweis "Select a task first". `copy_list` wurde entfernt,
   ganze Listen verlassen die App nur noch über den Export.
6. **Kontextueller Stift in der Rail:** Mit ausgewählter Aufgabe öffnet der
   Stift deren Inline-Bearbeitung, ohne Auswahl wie bisher das
   Listen-Umbenennen-Modal.
7. **Screenshot-Schutz (Gate G26), 2026-06-20 dauerhaft verworfen und entfernt:**
   Der Ansatz `SetWindowDisplayAffinity` mit `WDA_EXCLUDEFROMCAPTURE` in `main.py`
   sollte das Fenster in Screenshots und Bildschirmfreigaben schwarz erscheinen
   lassen. **Problem (real aufgetreten):** auf manchen GPU-/Treiber-Konstellationen
   verhindert genau diese Affinity, dass der WebView2-Inhalt rendert, das Fenster
   bleibt weiss bzw. reagiert nicht. Mehrfach ein- und wieder ausgebaut. **Endgueltige
   Entscheidung: entfernt und nicht wieder einbauen.** Falls je erneut gewuenscht,
   nur mit Render-Verifikation nach dem Setzen (Affinity automatisch zuruecknehmen,
   wenn der Inhalt nicht mehr rendert) und ausschliesslich ueber `_run_on_ui_thread`.

**Frühere Rest-Pflichten (inzwischen ALLE erledigt, je in der genannten Phase umgesetzt):**
- **Undo beim Listen-Löschen (Phase 7):** `delete_list` löscht heute sofort und
  unwiderruflich. Pflicht: Toast "List deleted" mit "Undo"-Button (ca. 6 s
  sichtbar). Umsetzung backendseitig **genau nach N11.2.1 in B.2 (U9-Entscheid 2026-07-13):
  ein RAM-Puffer für die letzte gelöschte Liste, kein Soft-Delete** (die frühere
  „oder als `deleted_at`-Soft-Delete"-Variante ist gestrichen), `undo_delete_list(id)`
  stellt an der alten Position wieder her. **Erledigt 2026-07-17** (mit Phase 7
  umgesetzt: RAM-Puffer in `db.py`/`api.py`, Undo-Toast im Frontend; der Puffer wird
  bei Lock/Panik/Killswitch/Quit verworfen, N11.2.1).
- **Profil-Menü aufräumen:** Das Profil-Menü zeigt den hartkodierten Namen
  "Noa Andersen" und tote Einträge (Account, Privacy & data, Export database).
  Pflicht: tote Einträge entweder funktional machen oder entfernen.
  **Erledigt 2026-07-17 (entfernt):** das Menü war komplett unerreichbarer toter
  Code (im Header existiert kein Avatar/Trigger, `renderProfileMenu` wurde nie
  aufgerufen) und wurde samt `state.menu`/`open-profile` restlos entfernt. Der
  Zielzustand, falls der Header nach N11.6 wieder einen Avatar bekommt, bleibt
  die dortige Eindampf-Entscheidung (nur echte Funktionen: "Export database" =
  Alle-Listen-Export, optional Settings-Link).
- **Export-Save-Dialog (Phase 7):** siehe Gate G21c. **Erledigt 2026-07-17** (mit der
  G21-Umsetzung in Phase 7).

**Abnahme:** Doppelklick-Bearbeiten, Löschen der ausgewählten Aufgabe über den
Rail-Papierkorb (nicht über die Karte, siehe Punkt 2), das neue `Strg+C`-Verhalten
und Mini-always-on-top funktionieren in der laufenden App; die offenen Punkte
sind in Phase 7 als Pflicht eingeplant.

---

### Phase 7: Export & Kopieren (`backend/api.py` ausbauen)

**Status: abgeschlossen am 2026-07-17.** Alle drei Tun-Punkte sind umgesetzt
(siehe die „Im Code umgesetzt"-Absätze unten), alle Pflicht-Gates der Phase
stehen auf ✅ in der B.9-Tabelle, die Abnahme unten ist durchlaufen.

**Ziel:** Der Export schreibt echte Dateien (Save-Dialog) und das Löschen von
Listen ist per Undo absicherbar. (Das Kopieren ist bereits fertig: `copy_task`
aus Phase 6.5 / Gate G23, es gibt bewusst kein Listen-Kopieren mehr.)

**Tun:**
1. **Zweistufiger Export (N11.2), nur `md` und `txt` (kein JSON, N11.1.5).** Der
   Rail-Button „Export" (bzw. `Ctrl+E`) öffnet zuerst eine kleine Pille links an der
   rechten Rail: **Schritt 1 Umfang** (aktuelle Liste `export_list(id, format)` oder alle
   Listen `export_all(format)`), **Schritt 2 Format** (`md`/`txt`), danach der Save-Dialog.
   **Ohne offene Liste (N11.2.3, 2026-07-17):** Export-Button und `Ctrl+E` öffnen die Pille
   trotzdem, aber die Umfang-Option "aktuelle Liste" ist **ausgegraut** (sichtbar, nicht
   wählbar, kein Fehler-Toast); nur "alle Listen" ist wählbar. Ein `export_list`-Aufruf ohne
   gültige Listen-ID bleibt davon unberührt `not_found` (die Ausgrauung ist UI-Führung,
   keine Ersatz-Validierung, die Bridge prüft weiter selbst, G20).
   `md`: Überschrift = Listenname (bei „alle Listen" jede Liste als größere Überschrift,
   die Aufgaben darunter kleiner), `- [ ]`/`- [x]` je Aufgabe. Kein Meta mehr (N11.1.3).
   `txt` analog als reiner Text. **Doppelte Listennamen sind erlaubt (U12):** der Name ist
   ein reiner Anzeigewert, Schlüssel ist überall die Listen-ID (`'l'+uuid`), es gibt keine
   Eindeutigkeitsprüfung beim Anlegen oder Umbenennen. Bei `export_all` stehen die
   Überschriften **wörtlich** und in **Sidebar-Reihenfolge** (zwei Listen „Ideas" ergeben
   zwei „Ideas"-Überschriften in Sichtreihenfolge, es wird nichts still umbenannt oder
   zusammengeführt). Bei `export_list` kollidieren zwei gleichnamige Listen nur als **Datei
   auf der Platte**, das regelt der Save-Dialog (Überschreiben/Umbenennen). Die
   **Sicherheit** des Dateinamens hängt nicht an der Eindeutigkeit des Namens, sondern an
   **G21** (reservierte Windows-Namen wie `CON`, verbotene Windows-Zeichen, Pfadtrenner,
   `..`, Laengenkappung ca. 120 Zeichen, Newline-Ersetzung; V6);
   „Duplikate erlaubt" betrifft nur den Anzeigenamen und lockert G21 nicht.

   **Fünf Festlegungen zum Exportformat (U10), damit hier nichts geraten wird:**
   1. **Vorgeschlagener Dateiname** (nur Default im Save-Dialog, der Nutzer kann
      überschreiben): `export_list` schlägt `<sanitisierter Listenname>.md`/`.txt` vor,
      `export_all` schlägt `NoaToDo-Export-YYYY-MM-DD.md`/`.txt` vor (lokales Datum,
      z.B. `NoaToDo-Export-2026-07-15.md`). Sanitisierung des Listennamens **immer
      über G21** (reservierte Namen, verbotene Windows-Zeichen, Pfadtrenner, `..`,
      Steuerzeichen/Newline ersetzt, Kappung auf ca. 120 Zeichen; V6);
      sanitisiert der Name zu leer, ist der Default `NoaToDo-Liste.md`/`.txt`. Die
      Endung setzt das gewählte Format, nie der Nutzer-Text.
   2. **Konkretes `txt`-Format:** je Aufgabe eine Zeile mit ASCII-Präfix `[ ] ` bzw.
      `[x] ` (offen/erledigt), **keine Einrückung**. Der Listenname steht als eigene
      Zeile darüber, gefolgt von einer Zeile `=` gleicher Sichtbarkeit (dekorativ, nur
      `txt`). Bei `export_all` trennt **eine Leerzeile** je Liste; die Reihenfolge ist
      Punkt 5. Kein Meta (N11.1.3).
   3. **Kodierung: UTF-8 ohne BOM**, Zeilenenden **CRLF (`\r\n`)** (Windows-Editoren
      wie Notepad zeigen die Datei sonst als eine Zeile). Gilt für `md` und `txt`.
   4. **Verhalten bei Dialog-Abbruch:** bricht der Nutzer den Save-Dialog ab, wird
      **keine Datei geschrieben und keine Meldung** gezeigt. Die Methode gibt
      den Code `canceled` zurück, der nach G29/B.2 **bewusst still** ist (kein Toast,
      keine Fehlermeldung, keine falsche Erfolgsmeldung, G22). Dies ist ein
      **Abnahmepunkt von G21c** (Save-Dialog): Abbruch = kein Nebeneffekt, keine
      Meldung. (Ein **Erfolg** wird seit N11.16 ebenfalls nicht mehr per Toast quittiert.)
   5. **Listen-Reihenfolge im Gesamtexport:** `export_all` schreibt die Listen in
      **Sidebar-Reihenfolge** (`lists.position`, dieselbe wie am Bildschirm), damit der
      Export der sichtbaren Ordnung entspricht; gilt für `md` und `txt`.
   6. **Erledigte Aufgaben ein-/ausblendbar (Setting `exportDone`, Default an, 2026-07-17):**
      Ob abgehakte Aufgaben (die `done`-Sektion, `- [x]` bzw. `[x] `) im Export erscheinen,
      steuert der Bool-Setting `exportDone` (Standard `true` = an) aus der Sektion "Export"
      im Settings-Modal (B.7). Bei `false` entfallen nur die erledigten Zeilen; die
      Listen-Überschrift (`# Name` bzw. Name + `=`-Zeile) und alle offenen Aufgaben bleiben.
      Gilt für `export_list` **und** `export_all`, für `md` **und** `txt`. Der Setting wirkt
      global (keine Pro-Export-Abfrage), damit die zweistufige Pille schlank bleibt.

   **Im Code umgesetzt (2026-07-17):** zweistufige Export-Pille im Frontend
   (`renderExportPill` in `app.js`, links neben der Rail; Rail-Button und `Ctrl+E`
   toggeln sie, `Esc`/Klick daneben schliesst, N11.2.3-Ausgrauung ohne offene Liste),
   `export_all(format)` als neue Bridge-Methode, JSON-Zweig entfernt; alle sechs
   U10-Festlegungen und die G21-Härtung siehe den G21-Block unten. Der `exportDone`-Filter
   sitzt in `_export_md`/`_export_txt` (Parameter `include_done`), gespeist aus
   `Api._export_include_done()`.
2. **Undo beim Listen-Löschen** (UX-Pflicht aus Phase 6.5): `delete_list` hält
   die gelöschte Liste samt Aufgaben zunächst zurück, neue Bridge-Methode
   `undo_delete_list(id)` stellt wieder her; das Frontend zeigt den Toast
   „List deleted" mit „Undo"-Button (ca. 6 s). Nur Listen-Löschen bekommt Undo; einzelne
   Aufgaben werden weiterhin sofort gelöscht (N11.2).
3. **Aufgaben verschieben und Listen umsortieren (N7, hier mitbauen, N11.2):**
   `move_task(id, target_list_id)` (Drag auf einen Sidebar-Eintrag plus „Move to…"-
   Kontextmenü, Zielposition ans Ende der Ziel-Liste) und `reorder_lists(ordered_ids)`
   (Drag and Drop der Listen in der Sidebar). Validierung wie `add_task` (G20).
   „Clear completed" und Volltextsuche werden nicht gebaut.
   **Im Code umgesetzt (2026-07-17):** beide Methoden in `db.py`/`api.py` mit den
   N11.2.2-Randfällen (alles oder nichts, Neunummerierung je Sektion 0..n-1,
   `done` bleibt beim Verschieben erhalten); Frontend: Sidebar-Einträge sind
   draggable (Sortieren), eine gezogene Aufgabe kann auf einen Sidebar-Eintrag
   fallen gelassen werden, Rechtsklick auf eine Aufgaben-Karte öffnet das
   „Move to…"-Kontextmenü; die Maus-Gesten stehen in B.5 und im Shortcuts-Modal.

#### Export-Härtung (Etikett G21) [Sec]

*(Wortgleich hierher gezogen in Umbau-Etappe 6 aus der G21-Zeile der B.9-Gate-Tabelle; Status, Stand und Pruefweg des Gates stehen weiter in B.9.)*

**Export-Härtung.** Audit-Befunde: eine Liste namens `CON` exportiert als `CON.md` (reservierter
Windows-Gerätename), und Zeilenumbrüche im Task-Text brechen die Markdown-Struktur des Exports
(eingeschleuste falsche `- [x]`-Zeilen/Überschriften). Pflicht in `export_list`: (a) Dateiname:
reservierte Namen (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9; case-insensitive, auch mit Endung)
mit `_`-Präfix entschärfen; führende/abschliessende Punkte und Leerzeichen entfernen; bleibt
nichts übrig, Fallback `NoaToDo-Liste` (vereinheitlicht 2026-07-17 mit U10 Punkt 1, der
frühere Fallback-Wortlaut `list` hier widersprach dem dortigen Default). (a2) **Verbotene Zeichen und Längenkappung (V6, 2026-07-15):**
die unter Windows unzulässigen Zeichen `<`, `>`, `:`, `"`, `/`, `\`, `|`, `?`, `*` sowie
`..`-Sequenzen im vorgeschlagenen Dateinamen durch `_` ersetzen (Listennamen sind Freitext) und
das Ergebnis auf ca. 120 Zeichen kürzen. Reihenfolge: erst Zeichen ersetzen, dann kürzen, dann
die Gerätenamen-Prüfung aus (a). Gilt für `export_list` **und** `export_all`. (b) Inhalt: in
md/txt jede Aufgabe einzeilig ausgeben, `\r` und `\n` im Task-Text durch ein Leerzeichen
ersetzen (kein Meta mehr, N11.1.3). (c) Echten Save-Dialog umsetzen
(`window.create_file_dialog(webview.SAVE_DIALOG, save_filename=...)`) und die Datei wirklich
schreiben.

**Im Code umgesetzt (2026-07-17):** `_sanitize_export_name()` in `api.py` setzt (a)/(a2)
in der G21-Reihenfolge um (Zeichen ersetzen, auf 120 kappen, Punkte/Leerzeichen strippen,
Gerätenamen-Präfix; Fallback `NoaToDo-Liste` nach U10), `_one_line()` setzt (b) um
(gilt auch für Listennamen in Überschriften), und `_export_via_dialog()` setzt (c) um:
Save-Dialog über den `_native_dialog()`-Kontext (N11.11.5: höchstens ein Dialog, zweiter
Aufruf -> `busy`), Datei UTF-8 ohne BOM mit CRLF (U10 Punkt 3), Abbruch -> `canceled`
ohne Nebeneffekt (U10 Punkt 4). Gilt für `export_list` und `export_all`; ein echter
Schreibfehler laeuft ueber `handleError`, ein Erfolg wird seit N11.16 nicht mehr per
Toast quittiert (Nutzerwunsch: keine Bestaetigungs-Benachrichtigungen).

> **🔒 PFLICHT-GATES für Phase 7 (keines optional; Definition, Status, Termin und
> Prüfweg stehen ausschliesslich in der normativen Gate-Tabelle in B.9, diese
> Liste nennt nur die Nummern; Regel aus Plananalyse S1):**
> - **✅ G20** (Validierung lokaler Eingaben an der Bridge; umgesetzt 2026-07-17, Volltext in B.2, Etikett G20)
> - **✅ G21** (Export-Härtung + echter Save-Dialog, gilt für `export_list` und `export_all`; umgesetzt 2026-07-17, Volltext oben in dieser Phase, Etikett G21)
> - **✅ G22** (ehrliche Sicherheits-Behauptungen in der ganzen UI; Rest umgesetzt 2026-07-17: Panik-Endschirm und Wipe-Fortschritt auf ehrliche Texte umgestellt, seit N11.17 dauerhaft)
> - **✅ G29** (Fehler-Hygiene, Fehlercode-Katalog B.2, Logging-Politik; umgesetzt 2026-07-17, Volltext in B.2, Etikett N11.12)
> - **✅ G12** (externe WebView-Navigation verweigern; vorgezogen, umgesetzt 2026-07-17)
> - **✅ G23** (Einzel-Task-Kopie, umgesetzt 2026-06-10; hier nur per Prüfweg verifizieren,
>   neue Copy-Funktionen nehmen denselben Backend-Pfad)

**Abnahme:** Export schreibt nach Save-Dialog eine korrekte `.md`-Datei (auch bei
Listennamen wie `CON` oder Tasks mit Zeilenumbrüchen); die Einzel-Task-Kopie taucht
nachweislich nicht in der Win+V-History auf und das Clipboard ist nach 60 s leer;
gelöschte Listen lassen sich per Undo-Toast wiederherstellen;
überlange/Steuerzeichen-Eingaben werden begrenzt bzw. bereinigt; `get_status()`
zeigt den ehrlichen Dev-Zustand. **G29:** ein künstlich ausgelöster `OSError` in einer
Bridge-Methode zeigt im UI nur „Something went wrong." samt `ref` (kein Pfad, kein
Benutzername), der Ringpuffer im Status-Modal führt den Eintrag mit `<path>` statt des
echten Pfades, und im Repo existiert kein `FileHandler`/`basicConfig(filename=...)`.
*(Abnahme durchlaufen am 2026-07-17; die Gate-Prüfwege stehen mit Status in B.9,
u.a. wurde der G12-DevTools-Prüfweg mit dieser Abnahme verifiziert.)*

---

### Phase 8: Sicherheits-Tiefe (`backend/security.py`)

**Ziel:** Lock-Screen, Emergency/Panic und die **immer aktive** doppelte Datenbank-
Verschlüsselung real machen, das Kernversprechen des lokalen, verschlüsselten Tresors.
Verschlüsselung ist **kein Modus und keine Einstellung**: es gibt keinen Weg, sie
abzuschalten (G9), und keinen Zustand, in dem eine unverschlüsselte DB auf der Platte
liegt (G6).

> **🔒 Vor dem ersten Handgriff dieser Phase: B.10 (Bedrohungsmodell) lesen, Gate G30.**
> Dort steht, **gegen wen** jede Massnahme dieser Phase wirkt (Klassen K1 bis K6), was
> ausdrücklich **nicht** verteidigt wird (allen voran Malware im selben Benutzerkonto,
> K4) und unter welchen **Voraussetzungen** die Zusagen überhaupt gelten (BitLocker,
> starkes Windows-Passwort). Wer das überspringt, baut wieder Massnahmen ohne Gegner
> (G26) oder schreibt Zusagen ohne Bedingung (der alte G18-Wortlaut). Jede in dieser
> Phase ergänzte Massnahme trägt ihre Angreiferklasse in B.10.6 nach.

> **🔒 Erster Handgriff der Phase: der Zweitprofil-Spike (U3, N11.8.3).** Die
> Lock-Screen-Architektur dieser Phase steht auf einer ungeklärten Grundannahme:
> zwei WebView2-Profile im selben Prozess, obwohl `private_mode`/`storage_path` bei
> PyWebView Parameter von `webview.start()` und damit global pro Prozess sind. Bevor
> Sperre, G14-Wisch und Lock-Screen gebaut werden, die neun Spike-Fragen aus N11.8.3
> beantworten (zwei Profile ja/nein, js_api-Umfang des Lock-Fensters, Taskbar,
> Fensterzustand nach Unlock, X-Knopf, Boot-Reihenfolge, WebView2-Prozesse vor dem
> Wischen beendet, DevTools am Lock-Fenster aus, Tastatur im gesperrten Zustand). Der
> WebView-Weg ist **beweispflichtig** (zwei isolierte Profile UND `PROFILE_DIR` im
> gesperrten Zustand nachweislich freigegeben und gewischt); ohne vollen Beweis gilt
> im Zweifel der native Fallback (schlankes Lock-Fenster ohne WebView), der
> prozess-interne WebView-Neustart ist als Fallback verworfen.

**Der Zweitprofil-Spike im Wortlaut (Etikett N11.8.3, U3-Entscheid; Punkt 3 des frueheren N11.8, wortgleich hierher umgezogen in Umbau-Etappe 3; Register: Anhang 1):**

3. **Eigenes kleines WebView2-Profil fuer den Lock-Screen.** *Loest "PROFILE_DIR bei
   `lock()` sicher wischen" (G14) vs. "WebView2 haelt den Ordner offen, solange der
   Lock-Screen laeuft".* Der Lock-Screen bekommt ein getrenntes, minimales Profil
   `LOCK_PROFILE_DIR` (z.B. `%LOCALAPPDATA%\NoaToDo\webview-lock`) mit eigenem kleinem
   HTML/CSS/JS **inklusive aller Lock-Screen-Animationen**; es sieht **nie**
   Aufgabendaten. Beim Sperren: die Haupt-App-Ansicht abbauen (das WebView2, das
   `PROFILE_DIR` offen haelt, schliessen), `PROFILE_DIR` freigeben und **sicher wischen**
   (G14), der Lock-Screen uebernimmt aus `LOCK_PROFILE_DIR` (muss nie gewischt werden,
   da inhaltsfrei). Beim Entsperren die Haupt-Ansicht mit `PROFILE_DIR` neu aufbauen und
   frisch `get_state()` laden (N10). Praktisch zwei WebView2-Oberflaechen im selben
   Prozess (Single-Instance-Mutex G19 bleibt einer). Der Startup-Cache-Purge
   (`_purge_webview_cache`) gilt fuer beide Profile getrennt.

   **Ungeloeste Grundannahme, Spike-Pflicht (U3): dieser Punkt ist als ERSTES in
   Phase 8 zu klaeren, bevor irgendein anderer Baustein auf dem Zweitprofil aufsetzt.**
   `private_mode` und `storage_path` sind bei PyWebView Parameter von `webview.start()`,
   also **global pro Prozess**, nicht pro Fenster. Zwei Fenster mit zwei verschiedenen
   Profilen im selben Prozess gibt die PyWebView-API damit moeglicherweise gar nicht
   her; genau darauf baut dieser Punkt aber. **Grundhaltung des Spikes (pro
   Sicherheit, im Zweifel): der Zwei-Profil-WebView-Weg ist keine dokumentierte
   PyWebView-Faehigkeit und wird nur beschritten, wenn der Spike ihn positiv
   BEWEIST; kann er es nicht, gilt ohne weitere Abwaegung der native Fallback unten.
   Nicht annehmen, sondern beweisen.** Der Spike beantwortet diese Fragen:
   1. **Zwei Profile im selben Prozess (Kernfrage, Beweis-, nicht Annahme-Pflicht):**
      Laesst sich empirisch zeigen, dass PyWebView bzw. das darunterliegende WebView2
      zwei Fenster mit getrennten `storage_path` betreibt UND dass `PROFILE_DIR`
      dabei im gesperrten Zustand tatsaechlich **freigegeben und sicher gewischt** ist
      (kein `msedgewebview2.exe` haelt es mehr offen)? Nur wenn **beides** bewiesen
      ist, ist der WebView-Weg erlaubt. Bleibt auch nur einer der beiden Punkte offen
      oder unsicher, ist der Fallback unten **verbindlich** (pro Sicherheit: ein nicht
      beweisbar gewischtes `PROFILE_DIR` verletzt G14 still).
   2. **js_api-Umfang des Lock-Fensters:** eigene, minimale Bridge nur mit dem, was
      die G13-Allowlist gesperrt erlaubt (`unlock`, `quit_app`, die Reset-Methode
      nach N11.3, `get_state` in der Gesperrt-Fassung), oder dieselbe volle
      Api-Instanz, abgesichert allein durch G13? Festlegen (die minimale Bridge ist
      die sauberere Linie, Defense-in-Depth).
   3. **Taskbar-Verhalten:** Erzeugen Haupt- und Lock-Fenster zwei Taskbar-Eintraege
      bzw. zwei Icons? Es darf fuer den Nutzer nur ein App-Eintrag sichtbar sein.
   4. **Fensterzustand nach dem Entsperren (entschieden, U24, nur noch zu verifizieren):**
      Nach dem Neuaufbau der Haupt-Ansicht kommt das Fenster **immer maximiert** zurueck
      (der N11.6-Grundzustand) und **nie im Mini-Modus.** Fenstergroesse/Position und der
      Mini-Zustand von vor der Sperre werden **bewusst nicht** ueber die Sperrgrenze
      getragen (pro Sicherheit: der Lock setzt auf den neutralen Grundzustand zurueck, kein
      Vor-Sperr-Fensterzustand ueberlebt; der Mini-Modus ist ohnehin Teil des von
      `clearWorkspace()` verworfenen Workspace). Der Spike muss das nur noch **nachweisen**,
      nicht mehr entscheiden. Der Fensterzustand nach **Mini-Ende ohne** Sperre ist separat
      in N11.6 (B.4) entschieden (exakte Wiederherstellung der Vor-Mini-Bounds).
   5. **X-Knopf des Lock-Fensters:** nimmt zwingend denselben Pfad wie der Off-Knopf,
      also `teardown("quit")` (N11.11, G35). Es darf keinen Lock-Fenster-Ausgang
      geben, der die gemeinsame Sequenz umgeht.
   6. **Boot-Reihenfolge:** Bei vorhandenem Tresor startet zuerst das Lock-Fenster;
      das Hauptfenster wird erst nach erfolgreichem Unlock erzeugt und ruft erst dann
      `get_state()` (Start-Weiche aus N11.8.2, B.2, beachten).
   7. **WebView2-Prozesse vor dem Wischen wirklich beendet:** Vor dem Freigeben und
      Wischen von `PROFILE_DIR` ist zu bestaetigen, dass die `msedgewebview2.exe`, die
      den Ordner offen hielten, beendet sind; sonst scheitert der Wisch an `0x800700AA`
      (ERROR_BUSY) und `PROFILE_DIR` bliebe ungewischt (G14-Bruch). Der Spike legt den
      verlaesslichen Weg fest (WebView-Teardown abwarten, notfalls verwaiste Prozesse
      gezielt beenden, dann wischen).
   8. **DevTools/Remote-Debugging am Lock-Fenster hart aus:** Das Lock-Fenster startet
      **nie** mit offenem WebView2-DevTools/Remote-Debugging, auch wenn `NOATODO_DEBUG`
      gesetzt ist (ein Debugger am Lock-Screen waere ein Umgehungspfad an G13 vorbei).
      Festlegen und pruefen.
   9. **Tastatur im gesperrten Zustand:** Wer den Lock-Screen rendert (WebView **oder**
      nativer Fallback) muss die B.8-Regel umsetzen, dass jede druckbare Taste das
      Passwortfeld fokussiert und das Zeichen dort landet und dass alle App-Shortcuts
      gesperrt sind.

   **Fallback (verbindlich, und im Zweifel der Default): natives Lock-Fenster ohne
   WebView.** Ergibt Frage 1 nicht den vollen Beweis, wird der Lock-Screen ein
   schlankes **natives Fenster ohne WebView** (WinForms: Logo, Passwortfeld, Off-Knopf,
   Reset-Einstieg; die Web-Animationen entfallen dann bewusst). Der fruehere zweite
   Vorschlag (prozess-interner Neustart des WebView-Teils mit eigenem
   `LOCK_PROFILE_DIR`) ist als Fallback **verworfen**: er zieht eine zweite
   Browser-Engine samt eigenem Cache in den gesperrten Zustand und vergroessert die
   Flaeche, ohne einen Sicherheitsvorteil zu bieten. Der native Weg hat die kleinste,
   vollstaendig pruefbare Flaeche: keine Engine kann `PROFILE_DIR` offen halten, es
   existiert gar kein zweiter Cache, und Aufgabendaten koennen den Lock-Screen baulich
   nicht erreichen. Im nativen Fallback gibt es folglich **kein** `LOCK_PROFILE_DIR`
   (nichts zu wischen). Die Zielvorgabe ist in beiden Varianten fix und nicht
   verhandelbar: **`PROFILE_DIR` ist im gesperrten Zustand freigegeben und sicher
   gewischt (G14); was den Lock-Screen anzeigt, sieht nie Aufgabendaten und muss nie
   gewischt werden.** Abnahme (G35-nah): vor Anzeige des Lock-Screens ist `PROFILE_DIR`
   nachweislich freigegeben und gewischt; andernfalls ist der Build nicht
   abnahmefaehig.

**Spike-Ergebnis (2026-07-21, ausgefuehrt als `Code/tools/spike_u3_lockwindow.py`, Register N11.18):**

Der Spike wurde als erster Handgriff der Phase 8 real ausgefuehrt; alle Pruefpunkte
liefen auf der Zielmaschine durch. Ergebnisse entlang der neun Fragen:

1. **Kein Zwei-Profil-Beweis moeglich, der native Fallback ist damit verbindlich.**
   `storage_path`/`private_mode` sind in PyWebView 5.x ausschliesslich Parameter von
   `webview.start()` (global pro Prozess); `create_window()` kennt sie nicht. Zwei
   Fenster mit getrennten Profilen bietet die API schlicht nicht an, der Beweis kann
   also nicht erbracht werden. Gemaess der Spike-Grundhaltung (nicht annehmen,
   sondern beweisen) gilt der native Fallback: **das Lock-Fenster ist ein schlankes
   natives WinForms-Fenster ohne WebView, es gibt kein `LOCK_PROFILE_DIR`.**
   Zusaetzlich empirisch bewiesen (Tragfaehigkeit des Fallbacks): (a) nach
   `window.destroy()` kehrt `webview.start()` zurueck, (b) die
   `msedgewebview2.exe`-Kindprozesse enden von selbst und `PROFILE_DIR` laesst sich
   danach restlos loeschen (G14-Wisch bewiesen), (c) ein **zweiter**
   `create_window()`+`start()`-Zyklus im selben Prozess funktioniert (Sperren =
   Hauptfenster komplett abbauen, Entsperren = neu aufbauen), (d) reine
   WinForms-Fenster (`Application.Run`) laufen vor, zwischen und nach den
   WebView-Zyklen. **Betriebsbedingung (im Code zu dokumentieren):** PyWebViews
   `setup_app()` (ruft `SetCompatibleTextRenderingDefault`) muss VOR dem ersten
   nativen Fenster einmal aufgerufen werden; es ist idempotent geschuetzt, der
   spaetere `webview.start()` ueberspringt es dann. Ohne diesen Aufruf wirft der
   erste WebView-Start nach einem nativen Fenster `InvalidOperationException`.
2. **js_api-Umfang:** entfaellt im nativen Fallback; das Lock-Fenster hat gar keine
   Bridge, `unlock`/`quit_app`/`reset_vault` laufen als direkte Backend-Aufrufe.
   Die G13-Allowlist gilt unveraendert fuer die (einzige) Bridge des Hauptfensters.
3. **Taskbar:** baulich immer nur ein Fenster zur Zeit (das Hauptfenster ist beim
   Anzeigen des Lock-Fensters bereits abgebaut), also ein Eintrag; Sichtpruefung in
   der Phase-8-Abnahme.
4. **Fensterzustand nach Unlock:** durch Neuaufbau mit `maximized=True` baulich
   immer maximiert, nie Mini (U24 bestaetigt).
5. **X-Knopf des Lock-Fensters:** FormClosing-Handler ruft `teardown("quit")`
   (Umsetzungspflicht, kein Spike-Risiko).
6. **Boot-Reihenfolge:** bei vorhandenem Tresor startet das native Lock-Fenster vor
   jedem WebView; das Hauptfenster entsteht erst nach erfolgreichem Unlock (durch
   Punkt 1 (d) bewiesen moeglich).
7. **WebView2-Prozesse vor dem Wischen beendet:** bewiesen (Punkt 1 (b)); der
   Teardown wartet auf das Prozess-Ende, bevor gewischt wird.
8. **DevTools am Lock-Fenster:** baulich ausgeschlossen (kein WebView, keine Engine).
9. **Tastatur im gesperrten Zustand:** das native Fenster fokussiert per
   KeyDown-Handler jede druckbare Taste ins Passwortfeld; App-Shortcuts existieren
   dort baulich nicht (Umsetzungspflicht im Lock-Fenster-Code).

**G6-Nebenbefund desselben Spikes:** `sqlcipher3` 2.6.0 (SQLite 3.51.1) exponiert
**kein** `Connection.serialize`/`deserialize`; das verlaessliche Serialisieren des
verschluesselten Images aus `:memory:` gibt die Build-Variante damit nicht her.
Gemaess B.7/N11.9 ist der Fallback **verbindlich**: die Arbeitskopie ist eine
**SQLCipher-verschluesselte Arbeitsdatei** in einem benutzerprivaten Pfad (nie
Klartext auf der Platte); Persistenzziel bleibt in jedem Fall `tasks.db.enc` (G17,
U19/U20). Schnappschuesse fuer den Write-back entstehen ueber `VACUUM INTO` (liefert
eine mit demselben Schluessel verschluesselte, konsistente Kopie, ohne die
Verbindung zu schliessen).

**Tun:**
1. **App-Sperre nach der Sperr-Politik aus B.8:** `lock()` setzt `locked=True`, verwirft
   die Schlüssel, packt die DB wieder zu (Schicht 2) und zeigt den LockScreen über allem.
   `unlock(passphrase)` leitet die Schlüssel ab (Argon2id aus Passphrase + Pepper →
   Master-Secret → HKDF-SHA256 → `aes_key` + `chacha_key`, G15/G18) und versucht,
   `tasks.db.enc` zu entschlüsseln; die Passphrase gilt genau dann als korrekt, wenn
   der Poly1305-Tag aufgeht (es gibt **keinen** gespeicherten Passphrase-Hash, G15).
   Danach wird die DB geöffnet.
   Sperre auslösen bei: Lock-Button/`Ctrl+L`, Panic, **App-Start** (immer gesperrt starten),
   **Auto-Sperre nach Inaktivität** (einstellbarer Timeout, Default ~15 min).
   **N11.8.4 gilt vorrangig: die Windows-Sitzungssperre (Win+L) ist KEIN Sperr-Ausloeser mehr; der `WTSRegisterSessionNotification`/`WM_WTSSESSION_CHANGE`-Hook entfaellt. Die Auto-Sperre laeuft als Hintergrund-Timer weiter, auch bei gesperrtem PC.** **Kein** Sperren bei Minimieren/Fokuswechsel.
2. **Emergency/Panic** (`panic()`), Zielverhalten nach N10: sofort bereinigen
   (Raum leeren, `state.lists=[]`, Schlüssel verwerfen), offline schalten, dann
   der Endschirm mit Finish/Killswitch. `panic()` selbst löscht
   nichts; die unwiderrufliche Löschung passiert nur über den separaten,
   zweistufig bestätigten `killswitch()` (löscht in Phase 8 `tasks.db.enc` samt
   `.bak` und Vault-Metadaten). Der Off-Knopf des Lock-Screens und „Finish"
   beenden über `quit_app()`, das vorher `PROFILE_DIR` sicher wischt (G14) und
   Schlüssel nullt (G25).
   **Pflicht (offener Phase-8-Punkt, festgehalten 2026-07-09): das native
   Fenster-X muss denselben sicheren Beenden-Pfad nehmen wie der Off-Knopf.**
   Heute endet ein Schließen über das X einfach mit dem Rückkehren aus
   `webview.start()` in `main.py`, ganz ohne Bereinigung (kein `PROFILE_DIR`-Wisch,
   kein Nullen der Schlüssel, kein finales Zurückschreiben nach `tasks.db.enc`).
   In Phase 8 ist das ein Datenspur-Leck und nicht akzeptabel: es darf keinen
   Beenden-Weg geben, der die Spuren stehen lässt, während Off-Knopf/„Finish" sie
   wischen. Umsetzung: einen `closing`-Handler des PyWebView-Fensters registrieren
   (bzw. das X-Ereignis der WinForms-Form abfangen), der **vor** dem tatsächlichen
   Schließen exakt dieselbe sichere Beenden-Routine wie `quit_app()` durchläuft
   (`tasks.db.enc` final schreiben und eine allfällige verschlüsselte Arbeitsdatei
   entfernen, `PROFILE_DIR` nach G14 wischen, Schlüssel/Master-Secret/Pepper nach
   G25 nullen). `quit_app()`
   und der X-Pfad müssen sich diese Routine teilen (eine gemeinsame Funktion, kein
   duplizierter Ablauf), damit kein Ausgang vergessen wird. Als Rückfalllinie
   zusätzlich `atexit`/`try…finally` um `webview.start()` in `main.py`, das die
   Schlüssel auch bei einem unerwarteten Rückkehren aus dem Message-Loop nullt.
   **Diese gemeinsame Routine ist ab dem S5-Entscheid (2026-07-13) verbindlich
   ausformuliert: `teardown(reason)` mit der nummerierten Soll-Sequenz aus N11.11 in B.8.5
   (Gate G35). Die Punkte 1 und 2 hier beschreiben nur noch das Was; das Wie, die
   Reihenfolge und die Zuordnung Schritt/Ausgang stehen abschliessend in N11.11 (B.8.5).**
3. **Gemeinsame Sperr-/Beenden-Sequenz (N11.11, Gate G35):** Sperren, Beenden, Panik-Ende,
   Killswitch und Reset laufen durch **genau eine** Routine `teardown(reason)` in
   `security.py`, in der festgelegten Reihenfolge: Idempotenz-Sperre, offene native Dialoge
   auflösen (U5), Eingaben einfrieren (G13), **G17-Debounce-Timer abbrechen und ausstehende
   Änderungen synchron persistieren**, **Clipboard sofort leeren, wenn es noch App-Inhalt
   trägt** (G23/V7), DB schließen, Schlüssel nullen (G25), erst dann (nur Killswitch/Reset)
   Dateien und Pepper löschen (U21), `PROFILE_DIR` wischen (G14), **Funk-Zustand ganz zuletzt
   wiederherstellen** (nur auf den Beenden-Wegen, N11.5/N11.10), Mutex freigeben, beenden.
   Jeder Ausgang (Lock-Button, `Ctrl+L`, Auto-Sperre, Off-Knopf, Panik-Finish, Killswitch,
   Reset, Fenster-X, `atexit`) ruft diese Routine, keiner baut seinen eigenen Ablauf.
4. **DB-Verschlüsselung, Doppel-Kaskade (Pflicht):** vollständige Umsetzung von **B.7**
   (in der G15/N11.9-Fassung).
   - Schlüsselableitung nach G15/G18: Argon2id(Passphrase + DPAPI-Pepper, Salt) →
     ein 32-Byte-Master-Secret → HKDF-SHA256 mit getrennten `info`-Labels →
     `aes_key` + `chacha_key`. Gespeichert werden nur Salt, Argon2-Parameter und
     Nonce (im `.enc`-Header, G16); es wird **kein** Passphrase-/Verifikations-Hash
     abgelegt, die Passphrase-Prüfung läuft implizit über den Poly1305-Tag der
     ChaCha20-Entschlüsselung (falsche Passphrase = AEAD-Fehler).
   - **Schicht 2 (ChaCha20-Poly1305) Wrap/Unwrap:** beim Entsperren `tasks.db.enc`
     entpacken → das innere SQLCipher-Image bevorzugt **in-memory** (`:memory:`, G6)
     öffnen; gibt die SQLCipher-Build-Variante das nicht verlässlich her, ist der
     Fallback eine **SQLCipher-verschlüsselte** Arbeitsdatei in einem
     ACL-beschränkten Pfad (N11.9), es liegt **nie Klartext auf der Platte**. Beim
     Sperren/Schließen/Panic wieder einpacken (atomar nach G16) und eine allfällige
     verschlüsselte Arbeitsdatei entfernen.
   - Beim Start ohne korrekte Passphrase bleibt die App im Lock-Screen und kann die DB
     gar nicht öffnen. Damit stimmen Status-Anzeige und Lock-Text
     („LOCAL VAULT · ENCRYPTED") real, nicht nur optisch.
   - `panic()` zusätzlich: Schlüssel + Klartext-Cache (RAM) sofort verwerfen, eine
     allfällige verschlüsselte Arbeitsdatei löschen, **den festen WebView2-Profilordner
     `%LOCALAPPDATA%\NoaToDo\webview` leeren (siehe G14)**, offline schalten.
5. `get_status()` liefert echte Werte (DB-Größe, Verschlüsselungs-Status,
   WebView2-Version).

> **🔒 PFLICHT-GATES G6-G8, aus dem Security-Review, NICHT vergessen:**
> - **G6, In-Memory-DB statt Temp-Arbeitskopie:** Die „Alternative für Puristen" aus
>   B.7 ist hier **der gewählte Default**: Beim Entsperren die (kleine) DB in eine
>   In-Memory-SQLite (`:memory:`) laden, im Ruhezustand nur als ein doppelt
>   verschlüsseltes Blob (`tasks.db.enc`) ablegen. Damit existiert **nie** eine
>   entschlüsselte DB-Datei auf der Platte, das eliminiert die ganze Klasse
>   „Temp-Datei-Forensik" (Secure-Delete ist auf SSD/NTFS wegen Wear-Leveling/Journaling
>   unzuverlässig). Bei ein paar hundert Aufgaben ist der Preis vernachlässigbar.
> - **G7, Roher Hex-Schlüssel für SQLCipher:** Den aus Argon2id abgeleiteten Key als
>   `PRAGMA key = "x'<64 Hex-Zeichen>'"` setzen (raw key), **nicht** als String per
>   `'%s'`-Interpolation (so wie der aktuelle Dev-Platzhalter in `db.py:~82`). Vorteil:
>   SQLCipher legt kein eigenes PBKDF2 über den schon teuer abgeleiteten Key, und das
>   Quote-Escaping entfällt. **Den Dev-Pfad in `db.py` bei dieser Gelegenheit ersetzen.**
> - **G8, Argon2id-Kosten + Passphrase-Politik:** Die Passphrase ist der **einzige reale
>   Schwachpunkt** (ein Angreifer mit der Datei brute-forced offline, App-Sperren bringen
>   da nichts). Daher: hohe Argon2id-Kosten. **Konkrete, fest verdrahtete Soll-Parameter
>   (N11.4.3, löst U17): Argon2id v0x13, `memory_cost = 262144` KiB (256 MiB),
>   `time_cost = 3`, `parallelism = 4`, `hash_len = 32`, 16-Byte-Salt.** Die frühere
>   Spanne („Memory ≥ 256-512 MB, parallelism passend") ist damit auf feste Zahlen
>   festgeschrieben; sie stehen im `.enc`-Header (G16), werden vor der Allokation gegen
>   einen Akzeptanzbereich geprüft (64 bis 512 MiB, sonst `vault`) und beim
>   Passphrase-Wechsel auf den Soll-Stand gehoben (N11.3 (d)). Ein `MemoryError` bei der
>   Ableitung ist ein eigener Zustand (Fehlercode `memory`), nie „falsche Passphrase" und
>   nie ein Absturz (N11.4.3). Das ist wichtiger als die zweite Cipher-Schicht.
>   **Die Passphrase-Regel selbst ist in N11.3 (B.2) abschliessend entschieden und lautet:
>   ausschliesslich Mindestlänge 12 Zeichen.** Kein Stärkemesser, keine Stärke-Anzeige,
>   keine Zeichenklassen-Regeln, keine Wörterbuch-/Blacklist-Prüfung. Frühere Fassungen
>   dieses Gates verlangten eine „erzwungene Passphrase-Stärke mit Stärke-Anzeige"; das
>   ist **bewusst gestrichen** und darf beim Abarbeiten der Gate-Liste nicht doch wieder
>   eingebaut werden. Ehrliche Konsequenz: `aaaaaaaaaaaa` ist damit eine gültige
>   Passphrase, und gegen eine schwache Passphrase verteidigen dann nur noch die
>   Argon2id-Kosten und der DPAPI-Pepper (der die gestohlene Datei ohne das
>   Windows-Konto unbrauchbar macht). Das ist eine bewusst getroffene
>   Komfort-Entscheidung, kein Versehen.
> - **🔴 G9, `DEV_AES_KEY` entfernen (WICHTIGSTES Gate der Phase 8):** Der aktuelle
>   `db.py` hat `DEV_AES_KEY = "noatodo-dev-key-phase1"` als Default, und `main.py` ruft
>   `db.connect()` **ohne** Schlüssel auf. Bei der Umsetzung von Phase 8 **muss** dieser
>   statische Default, und jeder andere Schlüssel-Fallback, **ersatzlos verschwinden**.
>   Es darf **keinen** Code-Pfad geben, der die DB ohne den aus der Passphrase abgeleiteten
>   Schlüssel öffnet. Sonst öffnet die „verschlüsselte" DB mit einem öffentlich im
>   Quellcode stehenden String → **effektiv null Verschlüsselung**, während `get_status()`
>   fälschlich „AES-256 + ChaCha20 · aktiv" meldet. Das untergräbt das gesamte
>   Sicherheitsversprechen lautlos. **Ebenso bedenken:** sauberer Erst-Einrichtungs-Flow
>   (Passphrase anlegen) und Migration der bestehenden Dev-DB auf den echten Schlüssel.

> **🔒 PFLICHT-GATES G13 bis G19, G25, G28, G31 bis G33 und G35 für Phase 8 (G13-G25
> aus dem Audit 2026-06-10, G28 aus N11.9, G31-G33 aus den A1-A3-Entscheiden vom
> 2026-07-15, G35 aus dem S5-Entscheid/N11.11; vollständige Beschreibung in B.9
> bzw. an den Volltext-Ankern B.2 (G13), B.8.5 (G14, N11.11), B.7 (G16, N11.9); KEINES davon ist optional):**
> - **🔴 G13, Lock serverseitig durchsetzen (als Allowlist):** Bei `locked=True`
>   prüft der `bridge`-Decorator gegen eine **explizite Allowlist**, nicht gegen eine
>   Ausnahmenliste:
>   ```python
>   ALLOWED_WHEN_LOCKED = {
>       "unlock", "quit_app", "killswitch", "get_state",
>       "get_boot_state", "choose_vault_dir", "create_vault", "reset_vault",
>   }
>   ```
>   Alles, was nicht in dieser Menge steht, wird gesperrt mit `{"error": "locked"}`
>   abgewiesen, ohne die DB zu berühren; das schliesst `lock()` und `panic()`
>   ausdrücklich ein (gesperrt ohnehin sinnlos) und sorgt dafür, dass **jede künftig
>   ergänzte Bridge-Methode per Default gesperrt** ist, statt versehentlich offen zu
>   stehen. `get_state()` liefert gesperrt nur `{"locked": true}` (keine Listen, keine
>   Settings). `quit_app()` und `killswitch()` sind die bewussten Ausnahmen aus N10:
>   Off-Knopf und Killswitch müssen gerade **ohne** Passphrase funktionieren und geben
>   nie Daten preis. Die vier Onboarding-/Reset-Methoden (`get_boot_state`,
>   `choose_vault_dir`, `create_vault`, `reset_vault`) sind mit dem U1-Entscheid
>   (N11.13) dazugekommen: Sie laufen gerade **ohne** Schlüssel (es gibt noch keinen
>   Tresor bzw. die Passphrase ist vergessen) und geben nie Daten heraus.
>   `change_passphrase()` steht bewusst **nicht** drin, es braucht den entsperrten
>   Zustand.
>   Heute ist die Sperre nur ein Frontend-Overlay (im Audit nachgewiesen:
>   `add_task`/`get_state` funktionieren gesperrt weiter). Normative Fassung: B.2 (Etikett G13).
> - **G14, WebView2 ohne Datenspuren (fester Profilordner umgesetzt 2026-06-20, sicheres Wischen offen für Phase 8):**
>   **Erledigt (vorgezogen mit G19):** Der Privatmodus ist abgeschaltet. `main.py` startet
>   PyWebView jetzt mit `private_mode=False` + `storage_path=PROFILE_DIR`
>   (`%LOCALAPPDATA%\NoaToDo\webview`), also genau einem festen, benutzerprivaten
>   Profilordner. Das frühere Verhalten (`private_mode=True`, pro Start ein neues
>   `%TEMP%\tmp...\EBWebView`, das bei hartem Beenden liegen blieb und sich anhäufte, real
>   bis 55 Altlasten, mit verwaisten `msedgewebview2.exe` zeitweise Starthänger über eine
>   Minute) entfällt damit. `_cleanup_stale_webview_profiles()` wischt die alten Temp-Profile
>   beim Start einmalig weg (nur `tmp*`-Ordner mit `EBWebView`-Signatur, gesperrte werden
>   übersprungen). Der frühere Sperrkonflikt auf dem geteilten Profil (zweite/verwaiste
>   Instanz, weißes Fenster, „reagiert nicht") ist abgefangen, weil der feste Ordner nur
>   **zusammen mit G19** (Single-Instance-Mutex, ebenfalls 2026-06-20 vorgezogen) eingeführt
>   wurde.
>   **Noch offen für Phase 8:** (a) `panic()`/`lock()`/sauberer Quit müssen `PROFILE_DIR`
>   **sicher wischen** (Forensik-Härtung gegen Crash-Dumps, siehe Entwarnung unten); **dabei
>   zählt das native Fenster-X ausdrücklich als „sauberer Quit" und muss denselben Wisch-/
>   Nullungs-Pfad wie `quit_app()` durchlaufen** (heute kehrt das X ohne jede Bereinigung aus
>   `webview.start()` zurück, siehe B.8 Punkt 2: `closing`-Handler abfangen, gemeinsame
>   Beenden-Routine, `atexit`-Rückfalllinie); (b) das
>   Wischen muss mit dem Single-Instance-Mutex und dem Lock-Lebenszyklus abgestimmt sein
>   (nicht wischen, während WebView2 den Ordner noch offen hält); (c) **Edge-Case festgestellt
>   2026-06-20:** wird der Prozess hart abgeschossen (Task-Manager), überleben die
>   `msedgewebview2.exe`-Kinder und halten `PROFILE_DIR` gesperrt; der nächste Start scheitert
>   dann an `CreateCoreWebView2Controller` mit `0x800700AA` (ERROR_BUSY, Fenster bliebe weiß).
>   Im Normalbetrieb (Fenster sauber schließen) lösen die Kinder die Sperre selbst; für den
>   Crash-/Kill-Fall sollte Phase 8 verwaiste `msedgewebview2.exe` mit `PROFILE_DIR` als
>   Arbeitsverzeichnis vor dem Start beenden (nicht pauschal alle, andere Apps nutzen WebView2).
>   **Wichtige Entwarnung zur Vertraulichkeit (gilt für den festen Ordner genauso):**
>   Aufgabentexte erreichen **keine** persistierbare WebView2-Fläche. Das Frontend nutzt
>   kein localStorage/sessionStorage/IndexedDB, keine Cookies, kein fetch/XHR; alle Daten
>   kommen ausschliesslich über die In-Memory-Bridge `pywebview.api.*` ins DOM. Im Profil
>   liegt nur **nicht-sensibler** UI-Cache (eigene HTML/CSS/JS/Fonts, GPU-/Netz-Status), nie
>   Aufgabeninhalte. Einziger Randfall: ein WebView2-Crash könnte einen Dump mit DOM-Fragmenten
>   schreiben, genau dagegen ist das Wischen Pflicht. Weiterhin gilt: nie
>   localStorage/IndexedDB für Aufgabendaten.
> - **G15, KDF mit Domain-Separation, kein Verifikations-Hash:** Argon2id →
>   ein 32-Byte-Master-Secret → HKDF-SHA256 mit getrennten `info`-Labels → `aes_key` +
>   `chacha_key`; Passphrase-Prüfung ausschliesslich über den Poly1305-Tag der
>   ChaCha20-Entschlüsselung, es wird kein Argon2-Hash gespeichert.
>   **Verbindliche HKDF-Parameter (U18, damit zwei Implementierungen bit-gleich ableiten):**
>   `HKDF-SHA256(ikm=master_secret, salt=None, info=<label>, length=32)`, zweimal aufgerufen,
>   `ikm` ist jeweils dasselbe Master-Secret. `salt=None` ist bewusst (das Master-Secret ist
>   schon ein gleichverteilter Argon2id-Schlüssel, die Extract-Stufe braucht kein zusätzliches
>   Salt; das Onboarding-Salt sitzt bereits in Argon2id, G16-Header). Die beiden `info`-Labels
>   sind fest und versioniert: `b"noatodo/aes-key/v1"` für `aes_key`, `b"noatodo/chacha-key/v1"`
>   für `chacha_key`. Die Labels sind Teil des Formatvertrags; eine spätere Änderung erhöht die
>   `v`-Nummer und braucht einen Migrationspfad.
> - **G16, `.enc`-Dateiformat + atomares Schreiben:** Header (Magic `NOA1`,
>   Version, Argon2-Parameter (Typ, `memory_cost`, `time_cost`, `parallelism`,
>   `hash_len`; konkrete Soll-Werte in N11.4.3, B.7), Salt, Nonce), frische Nonce pro
>   Verschlüsselung, Schreiben über `.tmp` + `fsync` + `os.replace`, eine
>   `.bak`-Generation. Der Header geht als `associated_data` in die AEAD ein (V1) und
>   die KDF-Parameter werden vor der Ableitung gegen den Akzeptanzbereich aus N11.4.3 (B.7)
>   geprüft (aufgeblähter oder unplausibler Kopf: `vault`, kein Argon2-Lauf). Ausserdem
>   (V1): das frische `.tmp` vor der `.bak`-Rotation probeweise entschlüsseln, freien
>   Plattenplatz vor dem Wrap prüfen; die zufällige 12-Byte-Nonce ist bei dieser
>   Schreibfrequenz geprüft unbedenklich.
> - **G17, Write-back:** In-Memory-DB nach jeder Mutation debounced (ca. 3 s nach
>   der letzten Aenderung), **mit harter Obergrenze: spaetestens alle 30 s wird auch
>   bei fortlaufenden Aenderungen geschrieben** (ohne die Kappe schoebe Dauereingabe
>   den Write-back unbegrenzt auf, "3 s nach der letzten Aenderung" hiesse bei
>   Dauertippen "nie", und ein Crash kostete mehr als die zugesagten Sekunden;
>   U20-Entscheid 2026-07-15); und sofort bei Lock/Panic/Quit als neues
>   `tasks.db.enc` persistieren.
> - **G18, DPAPI-Pepper (Pflicht):** 32-Byte-Pepper im Windows Credential Manager,
>   wird **vor** Argon2id an die Passphrase gebunden: `ikm = HKDF-Extract(salt=pepper,
>   ikm=passphrase_utf8)`, dann Argon2id über `ikm` (verbindliche Konstruktion in der
>   normativen G18-Zeile, V2a; `argon2-cffi` exponiert Argon2s `secret`-Parameter
>   nicht). **Kein Recovery-Export**
>   (N11.3): der Tresor ist bewusst an dieses Windows-Konto gebunden; kein
>   Recovery-Schritt im Einrichtungs-Flow.
> - **G19, Single-Instance-Mutex (umgesetzt 2026-06-20, vorgezogen):** benannter
>   Windows-Mutex `Local\NoaToDoSingleton` beim Start (`_acquire_single_instance` in
>   `main.py`), zweite Instanz zeigt einen Hinweis und beendet sich sofort
>   (Korruptionsschutz, Voraussetzung für den festen WebView2-Profilordner aus G14).
>   **Rest-Pflicht (V3, 2026-07-15):** Namensraum auf `Global\NoaToDo-<User-SID>`
>   umstellen; `Local\...` ist nur pro Logon-Session eindeutig, RDP/Benutzerumschaltung
>   startet sonst eine zweite Instanz auf derselben DB.
> - **G25, RAM-Schlüssel-Hygiene:** Schlüssel/Master-Secret/Pepper als `bytearray`,
>   vor dem Verwerfen nullen; Passphrase nach Ableitung sofort verwerfen; nichts
>   davon je in Logs, Exceptions oder ans Frontend.
> - **G28, Verschlüsselungs-Beweis (N11.9):** vor Phase-8-Abschluss beweisen, dass
>   das innere Image **ohne** `aes_key` nicht lesbar ist (kein SQLite-Klartext-Header,
>   kein Task-Text im Roh-Byte-Dump); scheitert der Beweis für den `:memory:`-Weg,
>   ist der Fallback mit SQLCipher-verschlüsselter Arbeitsdatei verbindlich. Kein
>   Auslieferungsbuild ohne bestandenen Beweis. Der Beweis läuft automatisiert als
>   pytest-Test (V12, Phase-9-Testliste).
> - **G31, RAM-auf-Platte-Lecks (A1-Entscheid 2026-07-15):** BitLocker-Empfehlung in
>   der Einrichtungs-UI plus realer BitLocker-Status im Status-Modal (sonst ehrlich
>   "unbekannt"); alle Schlüssel-`bytearray`s nach der Ableitung per `VirtualLock`
>   sperren (Best-Effort; hilft nicht gegen `hiberfil.sys`, das steht so in der Doku);
>   keine Traceback-/Dump-Dateien (deckt sich mit G29). Normative Fassung: B.9.
> - **G32, Tresor-Ort + Cloud-Warnung (A2-Entscheid 2026-07-15):** Onboarding-Default
>   `%LOCALAPPDATA%\NoaToDo`; deutliche Warnung bei erkannten Sync-Pfaden
>   (OneDrive-Env-Vars, Dropbox-`info.json`, Pfad-Heuristik) mit beiden Kernsätzen:
>   Versionshistorie beim Anbieter, und Killswitch/Reset löschen dort **nichts**.
>   Warnung, keine Sperre. Normative Fassung: B.9; Screens: N11.13/B.4.
> - **G33, Dev-Altdaten entsorgen (A3-Entscheid 2026-07-15):** beim ersten
>   `create_vault()` die alte `tasks.db` samt `-journal`/`-wal`/`-shm` über den
>   Secure-Delete-Pfad wegräumen (nie blankes `os.remove`); Einmal-Hinweis mit der
>   ehrlichen SSD-Restgrenze. Normative Fassung: B.9.
> - **🔴 G35, gemeinsame Sperr-/Beenden-Sequenz (N11.11):** genau **eine**
>   `teardown(reason)`-Routine in `security.py`, durch die **jeder** Ausgang läuft
>   (Lock-Button, `Ctrl+L`, Auto-Sperre, Off-Knopf, Panik-Finish, Killswitch, Reset,
>   natives Fenster-X, `atexit`), in der Reihenfolge aus N11.11.2 (B.8.5): Idempotenz, native
>   Dialoge auflösen (U5), einfrieren (G13), G17-Debounce abbrechen und synchron
>   persistieren, Clipboard leeren (V7), DB schließen, Schlüssel nullen (G25), erst dann
>   löschen (Killswitch/Reset, U21), `PROFILE_DIR` wischen (G14), Funk-Wiederherstellung
>   ganz zuletzt (N11.5/N11.10), Mutex freigeben. Ein zweiter, handgeschriebener
>   Beenden-/Sperr-Pfad ist ein Gate-Verstoss.

**Abnahme:** Sperren/Entsperren funktioniert mit Passphrase; jede Sperre bereinigt
vorher den Raum (N10); Panic bereinigt sofort und endet im Endschirm;
der Killswitch macht `tasks.db.enc` unwiederbringlich weg und der nächste Start ist
ein Erststart ohne Demo-Daten; das einzige Ruhe-Artefakt ist `tasks.db.enc` und es ist
ohne Passphrase nicht lesbar (ein Hexdump zeigt nur Header plus Rauschen, kein
SQLite-/SQLCipher-Klartext), eine unverschlüsselte `tasks.db` existiert im Ruhezustand
nirgends. **G6-G8 erfüllt:** keine entschlüsselte DB-Datei auf der Platte (In-Memory),
Hex-Raw-Key gesetzt, starke Argon2id-Parameter aktiv, Passphrase-Prüfung ist genau
eine Längenprüfung (mindestens 12 Zeichen, sonst nichts; kein Stärkemesser vorhanden).
**G13-G19/G25 erfüllt:** gesperrt liefert jede Bridge-Methode ausserhalb der Allowlist
(`unlock`, `quit_app`, `killswitch`, `get_state`) nachweislich einen `locked`-Fehler,
während Off-Knopf und Killswitch gesperrt weiterhin funktionieren;
kein WebView2-Datenrest; Entsperren scheitert bei falscher Passphrase über den
AEAD-Tag; `tasks.db.enc` trägt den spezifizierten Header und übersteht einen
simulierten Absturz beim Sperren (`.bak` greift); ohne den Pepper aus dem Credential
Manager ist die Datei offline nicht angreifbar; eine zweite App-Instanz startet nicht.
**G28 erfüllt:** der Verschlüsselungs-Beweis ist erbracht und dokumentiert: das
Öffnen des inneren Images ohne `aes_key` scheitert nachweislich, ein Roh-Byte-Dump
der Arbeits-/Zwischendatei zeigt weder SQLite-Klartext-Header noch Task-Text (N11.9).
**G31-G33 erfüllt:** das Status-Modal zeigt den realen BitLocker-Status (oder ehrlich
"unbekannt"), die Schlüssel-Puffer sind per `VirtualLock` gesperrt, und es entsteht
nachweislich keine Traceback-/Dump-Datei; ein testweise unter OneDrive gewählter
Tresor-Pfad löst im Onboarding die Cloud-Warnung mit dem Killswitch-Satz aus; nach
dem ersten `create_vault()` existiert keine mit `DEV_AES_KEY` lesbare Datei mehr
(auch kein `-journal`/`-wal`/`-shm`), und der Einmal-Hinweis zur SSD-Restgrenze wurde
angezeigt.
**G35 erfüllt:** es gibt im Code genau eine `teardown(reason)`-Routine, und für **jeden**
der neun Ausgänge (Lock-Button, `Ctrl+L`, Auto-Sperre, Off-Knopf, Panik-Finish,
Killswitch, Reset, Fenster-X, `atexit`) ist einzeln nachgewiesen: ein ausstehender
G17-Debounce wurde synchron geschrieben (ausser Killswitch/Reset), das Clipboard trägt
keinen App-Inhalt mehr, die Schlüssel sind genullt, `PROFILE_DIR` ist gewischt, der
Funk-Zustand wurde nur auf den Beenden-Wegen und nur als letzter Schritt wiederhergestellt
(beim Sperren gar nicht, N11.10), der Mutex ist freigegeben. Killswitch und Reset
schliessen die DB und nullen die Schlüssel nachweislich **vor** der Datei-Löschung
(N11.11).

---

### Phase 9: Auslieferung, Tests und Build (`.exe`, Packaging)

**Ziel:** Aus dem lauffähigen Projekt eine verteilbare `NoaToDo.exe` machen, die sich auf
einem fremden Windows-Rechner korrekt verhält, plus eine echte Testbasis und einen
reproduzierbaren Build. Erst **nach** Phase 8 starten: die Verschlüsselung muss real
sein, bevor man verteilt (sonst gibt man eine „Tresor-App" mit `DEV_AES_KEY` heraus).

**Tun:**

1. **Testbasis (heute existiert keine, kein `tests/`, kein pytest):**
   - `pytest` als Dev-Abhängigkeit aufnehmen, `tests/` anlegen.
   - Unit-Tests für die sicherheitskritischen Pfade:
     - `db.py`: CRUD, parametrisierte Queries, `edit_task`-Spalten-Whitelist und der
       **leere Erststart** (N11.1.4): `seed_if_empty()` schreibt nur die Default-Settings
       und den `seeded`-Marker, legt **keine** Listen und Aufgaben an; ein zweiter Aufruf
       bei gesetztem Marker ändert nichts. Es gibt keine Demo-Seed-Daten mehr, also auch
       nichts, was ein Test darauf prüfen könnte.
     - `api.py`-Bridge: Eingabe-Validierung (G20: Längenlimits, Steuerzeichen-Strip,
       `reorder`-Typprüfung, `set_setting`-Key-Whitelist) und Export-Härtung (G21:
       reservierte Windows-Namen, Newline-Ersetzung).
     - Krypto-Roundtrip (Phase 8): KDF-Domain-Separation (G15), `.enc`-Wrap/Unwrap
       inklusive Header und frischer Nonce (G16), falsche Passphrase bzw. fehlender
       Pepper liefern einen AEAD-Fehler, `.bak`-Recovery nach simuliertem Absturz.
     - **Passphrase-Wechsel (N11.3, Befund U8c):** nach `change_passphrase(old, new)`
       ist **weder** `tasks.db.enc` **noch** `tasks.db.enc.bak` mit der alten
       Passphrase entschlüsselbar (beide liefern einen AEAD-Fehler); die alte
       `.bak`-Generation wurde dabei über den Secure-Delete-Pfad weggeräumt, nicht per
       blankem `os.remove`; der neue Header trägt ein frisches Salt und die aktuellen
       Soll-Argon2-Parameter aus G8 (KDF-Upgrade-Pfad); mit der neuen Passphrase öffnet
       der Tresor normal.
     - Lock-Durchsetzung (G13, Allowlist): Der Test iteriert über **alle** Bridge-Methoden
       und prüft, dass im gesperrten Zustand jede Methode ausserhalb von
       `ALLOWED_WHEN_LOCKED` (`unlock`, `quit_app`, `killswitch`, `get_state`,
       `get_boot_state`, `choose_vault_dir`, `create_vault`, `reset_vault`)
       nachweislich `locked` liefert, `get_state()` gesperrt nur `{"locked": true}`
       zurückgibt und `quit_app()`/`killswitch()`/die Onboarding-Methoden **nicht**
       blockiert werden (sie müssen
       gerade im gesperrten Zustand funktionieren, siehe G13 in B.9, Etiketten N10/N11.13). Der Test liest die
       Methodenliste dynamisch aus der `Api`-Klasse, damit eine neu ergänzte Methode
       auffällt, statt still durchzurutschen.
     - **G28-Beweis automatisiert (V12):** ein pytest-Test speichert einen bekannten
       Task-String, erzeugt das Arbeits-Artefakt (das `:memory:`-Serialisat bzw. die
       Fallback-Arbeitsdatei, N11.9) und scannt es auf den SQLite-Klartext-Header
       (`SQLite format 3`) und auf den Task-String; jeder Fund ist ein Fail. So
       verrottet der G28-Beweis nicht als Einmal-Handgriff.
     - **XSS-Trägheitstest (V12):** ein Task mit Text `<img src=x onerror=alert(1)>`
       wird als Text gerendert (`esc()`-Pfad, B.9 Regel 1), es feuert kein Handler;
       prüfbar über den CDP-Testweg aus der Dev-Doku oder einen DOM-Snapshot.
     - **Rate-Limit-Leiter inkl. Persistenz (U6, V12):** nach den drei Freiversuchen
       eskaliert die Leiter (10 s, 30 s, ...), `unlock` liefert währenddessen
       `rate_limited` + `retry_in`, und der Zustand überlebt einen Prozess-Neustart
       (`config.json`, N11.4.1); ein Kill mitten im Versuch senkt den Zähler nicht
       (Persist-before-verify).
     - **Datei-Killswitch (V12):** `killswitch()` entfernt `tasks.db.enc`, `.bak` und
       den Pepper nachweislich (U21); der Folgestart meldet
       `get_boot_state() == 'onboarding'`.
   - Manuelle Smoke-Test-Checkliste für die WebView-UI (kein Headless-Browser nötig):
     Liste/Aufgabe anlegen, Inline-Edit, Mini-Modus, Sperren/Entsperren, Erststart auf
     frischem Profil.

2. **Build / Packaging (Bauprozess):**
   - PyInstaller (erst one-folder zum Debuggen, dann one-file prüfen) baut `NoaToDo.exe`.
   - Icon fest einbetten (`frontend/icon.ico`); das löst zugleich den noch offenen
     Taskleisten-Icon-Punkt, der bisher bewusst auf die `.exe` mit eingebettetem Icon
     vertagt war.
   - WebView2-Runtime: NoaToDo bündelt **kein** Chromium und braucht die
     Evergreen-WebView2-Runtime auf dem Zielrechner. Klären und dokumentieren, ob der
     Evergreen-Bootstrapper mitgeliefert oder eine Fixed-Version-Runtime gebündelt wird,
     und sicherstellen, dass eine fehlende Runtime eine **verständliche Meldung** ergibt
     statt eines weissen Fensters oder Absturzes.
   - Reproduzierbarer Build aus `requirements.lock.txt` mit pip-Hash-Checking (Gate G11),
     **unter Python 3.11.x** (die gepinnte Interpreter-Version, U25; `sqlcipher3-wheels`
     liefert Wheels nur fuer bestimmte CPython-Versionen);
     Version und Build-Datum in die `.exe`-Ressourcen schreiben.

3. **Verhalten auf einem fremden Rechner (Erststart):**
   - Keine `tasks.db.enc` vorhanden, also Onboarding: Speicherort wählen (N11.3), neue
     Passphrase anlegen (min. 12 Zeichen plus Verlust-Warnung, N11.3), Pepper erzeugen
     (kein Recovery-Export, N11.3), frischen (leeren) Tresor anlegen. Die App startet
     danach gesperrt (B.8).
   - Eine untergeschobene oder manipulierte `tasks.db.enc` scheitert am AEAD-Tag
     (G15/G16); auf einem fremden Windows-Konto fehlt zusätzlich der DPAPI-gebundene
     Pepper (G18). Das ist Phase-8-Mechanik, hier nur als Auslieferungs-Abnahme
     verankert, damit „fremder Rechner: neuer, gesperrter Tresor" ein geprüftes
     Verhalten ist.

4. **Binary-Härtung gegen Reverse-Engineering + Frontend-Integrität (Gate G27 samt
   A5-Ergänzung vom 2026-07-15, siehe unten).**

5. **Release-Härtung WebView2/Debug (Gate G34, A4/A6-Entscheid 2026-07-15; normative
   Fassung in B.9):**
   - Der gefrorene Build ignoriert `NOATODO_DEBUG` hart (Build-Konstante:
     `_debug_enabled()` liefert im Release immer `False`); DevTools aus, zusätzlich
     `AreDevToolsEnabled=false` in den CoreWebView2-Settings, soweit erreichbar.
     Sonst wäre die DevTools-Konsole voller Bridge-Zugriff für jeden mit kurzem
     Zugriff, inklusive `killswitch()` (per G13 gesperrt erlaubt).
   - Im Release `AreBrowserAcceleratorKeysEnabled=false` (tötet den
     `Strg+P`-Klartext-PDF-Export an G21 vorbei; die B.5-Shortcuts laufen über den
     eigenen JS-Handler und bleiben unberührt) und `AreDefaultContextMenusEnabled=false`.
   - `text_select=False` ist zu diesem Zeitpunkt längst explizit gesetzt (Sofort-Teil
     von G34, Termin 2026-07-20) und wird im Build-Test erneut geprüft
     (Regressionstest: Task-Text nicht selektierbar, Eingabefelder schon).

6. **Update-/Release-Story (V10, ergänzt 2026-07-15):**
   - **Version sichtbar:** das Status-Modal zeigt Versionsnummer und Build-Datum an
     (dieselben Werte, die in die `.exe`-Ressourcen geschrieben werden).
   - **Bewusst kein Auto-Update und kein Update-Check übers Netz** (die App ist
     offline und ruft nie nach Hause). Stattdessen ein manueller Weg: das
     Status-Modal nennt die Bezugsquelle im Klartext, dort prüft der Nutzer selbst
     auf neue Versionen.
   - **Gepinnte Abhängigkeiten altern:** bei relevanten CVEs in `cryptography`,
     `pywebview` oder `sqlcipher3-wheels` wird ein Rebuild auch ohne
     Funktionsänderung veröffentlicht (Rebuild-Kadenz); der Browser-Anteil ist über
     die Evergreen-WebView2-Runtime automatisch versorgt.

> **🔒 GATES (Phase 9): G27 und G34 (Volltext je hier):**
> - **G27, Binary-Härtung gegen Reverse-Engineering + Manipulation.** Eine als Datei
>   verteilte App ist grundsätzlich entpack- und disassemblierbar; das Sicherheitsmodell
>   darf deshalb **nie** auf Code-Geheimhaltung beruhen (Kerckhoffs-Prinzip: die
>   Sicherheit steckt allein in Passphrase + DPAPI-Pepper + Verschlüsselung, nicht im
>   Verbergen des Codes). Die Härtung erhöht nur die Hürde und macht Manipulation
>   erkennbar. Pflicht bzw. empfohlen:
>   - **Authenticode-Code-Signing der `.exe`** (Pflicht, sobald ein Zertifikat verfügbar
>     ist): macht Manipulation am Binary erkennbar (gebrochene Signatur = veränderte
>     Datei) und entschärft den SmartScreen-Warnscreen beim Verteilen.
>   - **Keinen Python-Quelltext mitliefern, vorzugsweise Nuitka** statt PyInstaller:
>     Nuitka kompiliert nach C-Niveau und ist deutlich schwerer zu lesen als ein
>     PyInstaller-Bundle, das nur gepackte `.pyc` enthält und mit Standard-Tools
>     entpackbar ist. Mindestens: Docstrings und `assert`s beim Build entfernen.
>   - **Optional Obfuskation** (z.B. PyArmor) als zusätzliche Hürde, bewusst als Bonus,
>     nicht als Schutzgrundlage.
>   - **Keine fragilen Anti-Debugging-/Anti-VM-Tricks** als Sicherheitsbasis: sie stören
>     legitime Nutzung und werden trivial umgangen.
>   - **Frontend-Integrität (Ergänzung 2026-07-15, Plananalyse A5):** Die Signatur
>     der `.exe` deckt die danebenliegenden `index.html`/`app.js`/`style.css` (samt
>     Fonts) **nicht** ab. Wer sie einmal schreiben kann, besitzt die App dauerhaft:
>     das nächste `boot()` lädt das manipulierte JS mit voller Bridge, liest die
>     Passphrase-Eingabe des HTML-Lock-Screens mit und greift nach dem Entsperren
>     alles ab, bei intakter Exe-Signatur. Pflicht: Frontend-Assets ins signierte
>     Binary einbetten und von dort (bzw. aus einem frisch entpackten Pfad) laden,
>     **oder** beim Start jeden Asset-Hash gegen ein im Binary eingebettetes Manifest
>     prüfen; bei Abweichung verweigert die App den Start mit einer klaren Meldung
>     (kein "trotzdem fortfahren"-Knopf). Einordnung nach B.10: erschwert stille
>     K4-Persistenz und wird nie als vollständiger K4-Schutz verkauft (B.10.3
>     Punkt 1); gegen einen Angreifer, der auch das Binary tauschen kann, hilft nur
>     die Signaturprüfung durch den Nutzer.
>
>   **Leitlinie:** Jede der unten genannten Analyse-Methoden soll mit einer Hürde
>   umstellt werden (Signing gegen Manipulation, Nuitka/kein Quelltext gegen
>   Dekompilieren, optional Obfuskation), aber **keine Härtung darf die Funktionsweise
>   der App einschränken** (kein langsamerer Start, keine blockierte WebView2-Anzeige,
>   keine Fehlfunktion in VMs oder bei Bildschirmfreigabe, kein verweigerter Lauf auf
>   legitimen Rechnern). Im Zweifel hat die Funktion Vorrang vor der Härtung; sie erhöht
>   nur die Hürde, sie ist nicht die Sicherheitsbasis (das bleiben Passphrase + Pepper +
>   Verschlüsselung). Das ist die gleiche Lehre wie bei G26 (Screenshot-Schutz), der
>   genau deshalb verworfen wurde, weil eine „Härtung" das Rendern verhinderte.
>
>   **Begründung, wie eine `.exe` überhaupt analysiert wird (so entstehen die Hürden):**
>   (1) **Strings auslesen** (`strings`): zieht lesbare Textfragmente, findet sofort fest
>   eingebackene Geheimnisse wie ein `DEV_AES_KEY`; Hürde: gar keine Geheimnisse im
>   Binary (Kerckhoffs). (2) **PyInstaller-Bundle entpacken** (`pyinstxtractor`): zerlegt
>   die `.exe` in die einzelnen `.pyc`. (3) **Bytecode dekompilieren** (`decompyle3`):
>   macht aus `.pyc` fast den Originalquelltext, deshalb ist reines PyInstaller schwach;
>   Hürde: Nuitka (Kompilat auf C-Niveau) plus Docstring-/`assert`-Strip. (4)
>   **Disassembler/Decompiler** (Ghidra, IDA) für echtes Maschinencode-Binary: deutlich
>   mühsamer, aber möglich; Hürde: optional Obfuskation. (5) **Dynamische Analyse**
>   (Debugger, Speicher-Dump): liest Schlüssel/Daten zur Laufzeit aus dem RAM, ohne den
>   Code zu verstehen; dagegen helfen nicht Code-Hürden, sondern die schnelle Sperre,
>   Panic und das RAM-Nullen (G25).
>
> - **G34, Release-Härtung: Debug-Schalter, DevTools, Kopier-/Auslass-Kanäle.** Zwei
>   Befund-Gruppen: **(A4)** `NOATODO_DEBUG=1` aktiviert heute DevTools; respektierte die
>   Phase-9-`.exe` dieselbe Env-Var, bekäme jeder mit kurzem Zugriff (K3) eine Konsole mit
>   vollem `pywebview.api.*`-Zugriff auf die laufende App, inklusive `killswitch()`
>   (Datenvernichtung ohne Passphrase, per G13 gesperrt erlaubt!). **(A6)** G23 härtet nur den
>   Rail-Button-Pfad; daneben existieren Kopier-/Auslass-Kanäle: Textselektion plus natives
>   `Strg+C` (PyWebView deaktiviert die Selektion nur per Default; `main.py` setzt `text_select`
>   nicht explizit, der Schutz ist also unbeabsichtigt und ungetestet, und ein künftiges
>   `text_select=True` "für Komfort" würde G23 lautlos aushebeln), Drag-out von markiertem Text
>   in andere Apps, `Strg+P` (der WebView2-Browser-Accelerator öffnet den Druckdialog, "Als PDF
>   drucken" exportiert die komplette Ansicht als Klartext-PDF an G21 vorbei) und das
>   WebView2-Standard-Kontextmenü. Pflicht: **(a)** Der Release-Build ignoriert `NOATODO_DEBUG`
>   hart (Build-Konstante: `_debug_enabled()` liefert im gefrorenen Build immer `False`),
>   DevTools aus, zusätzlich `AreDevToolsEnabled=false` in den CoreWebView2-Settings, soweit
>   über PyWebView erreichbar. **(b) SOFORT, nicht erst Phase 9:** `text_select=False` explizit
>   in `create_window` setzen (aus dem unbeabsichtigten Default eine bewusste, getestete
>   Entscheidung machen) plus Regressionstest. **(c)** Im Release
>   `AreBrowserAcceleratorKeysEnabled=false` (tötet `Strg+P` und die übrigen Browser-Tasten; die
>   App-Shortcuts aus B.5 laufen über den eigenen JS-Handler und bleiben unberührt) und
>   `AreDefaultContextMenusEnabled=false`. **(d)** Der Rest wird nicht "gelöst", sondern steht
>   ehrlich im Bedrohungsmodell (B.10.3 Punkt 8): Eingabefelder bleiben selektierbar (Phase 6.5
>   Punkt 3, akzeptiert), ihr natives `Strg+C` landet ungehärtet in Win+V-History und
>   Cloud-Clipboard; das Foto vom Bildschirm bleibt Nicht-Ziel. *(Wortgleich hierher gezogen in
>   Umbau-Etappe 6 aus der G34-Zeile der B.9-Gate-Tabelle; Status, Stand und Pruefweg des Gates
>   stehen weiter in B.9.)*

**Abnahme:** `pytest` läuft grün; `NoaToDo.exe` startet auf einem frischen Windows-Profil
ohne installiertes Python, legt bei fehlender DB einen neuen, gesperrten Tresor an und
meldet eine fehlende WebView2-Runtime verständlich; das Status-Modal zeigt Version und
Build-Datum (V10); die `.exe` ist signiert (sofern ein
Zertifikat vorliegt) und enthält keinen im Klartext lesbaren Python-Quelltext.
**G29-Prüfung im Build (N11.12.2):** der Auslieferungsbuild läuft nicht im Debug-Modus
(`NOATODO_DEBUG` nicht gesetzt, DevTools aus), schreibt beim Testlauf nachweislich keine
Log-/Traceback-Datei, und im Quellbaum existiert kein `FileHandler` bzw.
`basicConfig(filename=...)`.
**G34-Prüfung:** die Release-`.exe` startet mit gesetztem `NOATODO_DEBUG=1` ohne
DevTools (F12 und Rechtsklick tot), `Strg+P` öffnet keinen Druckdialog, das
Standard-Kontextmenü erscheint nicht, Task-Text ist nicht selektierbar (Eingabefelder
schon).
**G27-Frontend-Integrität:** eine nachträglich veränderte `app.js` (ein Byte genügt)
verhindert den Start mit einer Integritäts-Meldung.

---


## TEIL D: Offene Entscheidungen & Erweiterungen

### D.1 Privatsphäre: alles bleibt lokal

- **Lokal:** alle Aufgaben, alle Bearbeitungen, die gesamte SQLite-DB. Nichts verlässt
  je den Rechner; es gibt keinen externen Dienst, keine Cloud-Anbindung und keinen Sync.
- Im Windows Credential Manager (über `keyring`) liegt nur der DPAPI-Pepper der
  Schlüsselableitung (siehe G18), keine Aufgabendaten.

### D.3 Mögliche spätere Erweiterungen (nicht im Kern-Scope)

- Unterpunkte/Checklisten je Aufgabe.
- Mehrere Akzent-/Theme-Presets, anpassbare Dichte je Liste.
- **Fälligkeiten, reine Anzeige (nicht im Kern-Scope, siehe A.4 Punkt 6, Etikett N11.1.6).** Falls das je
  gebaut wird: ein optionales Datum an der Aufgabe, das nur **angezeigt** wird (Chip in
  der Zeile, evtl. eine Sortierung), **ohne** Erinnerungen, ohne Toasts, ohne
  Hintergrund-Timer, ohne Wiederholungen, ohne Schlummern. Benachrichtigungen bleiben
  gestrichen (N11.1.1), und ohne sie wäre eine Fälligkeit nur eine Notiz mit Datum.
  Ausdrücklich **kein** Auftrag: kein `due_at` im Schema, kein Platzhalter, keine
  Vorbereitung im Code, bis es einen neuen ausdrücklichen Entscheid gibt.
- Wiederholende Aufgaben: nur zusammen mit dem obigen Punkt denkbar, heute gestrichen.

(Volltextsuche und automatische Backups wurden bewusst gestrichen, siehe N11.1.2 (A.4
Punkt 2) und N11.7 (Register: Anhang 1). Fälligkeiten/Erinnerungen sind aus dem
Kern-Scope gestrichen, siehe N11.1.6 (A.4 Punkt 6).)

**Roadmap-Erweiterungen aus dem UX-Nachtrag (Etikett N8, 2026-06-13; wortgleich umgezogen in Umbau-Etappe 3, ergaenzt D.3):**

Bewusst kein Kern-Scope, aber als Produktrichtung festgehalten:
- **Aufgaben-Detailansicht (UX 7.4):** ausklappbare Detailzeile (Beschreibung,
  Erstellt-Datum).
- **Mini-Modus, Listenwechsel (UX 7.7, 3.14):** ein Dropdown im `mini-bar`-Titel zum
  Wechseln der Liste, ohne den Mini-Modus zu verlassen.

(Zwei hinfällige Punkte dieser Liste, Volltextsuche UX 7.2 und Meta-Feld UX 7.3,
liegen durchgestrichen in Anhang 3, Umbau-Etappe 5.)

---

## ANHANG 1: Entscheidungsregister (N10 + N11 als Protokoll)

*(Umbau-Etappe 3, 2026-07-16: Dieses Register loest die frueheren Nachtrag-Bloecke N2 bis N10 und N11.1 bis N11.15 als reines Aenderungsprotokoll ab. Jede ID ist ein stabiles Etikett (Umbauplan, Abschnitt 4): die Spalte „Norm jetzt in“ zeigt auf den einen normativen Ort; Blocktexte, deren Norm schon im Haupttext stand, liegen wortgleich als Historie in Anhang 3. Neue Entscheidungen bekommen die naechste freie Nummer in derselben Systematik, ihr Inhalt geht sofort in den Vertrag, hier kommt nur die Protokollzeile dazu.)*

| ID | Datum | Thema | Norm jetzt in |
|---|---|---|---|
| Kopf UX-Nachtrag | 2026-06-13 | UI durchgehend Englisch; Zielplattform ausschliesslich Windows, keine Mac-Symbole | A.5 (Historie: Anhang 3) |
| N2 | 2026-06-13 | Persistente Offline-Statusanzeige (UX 4.2, 8.3) | B.4 |
| N4 | 2026-06-13 | Echter Lock-Screen mit Passphrase, UX-Pflichten (UX 8.1) | B.4 |
| N5 / W5 | 2026-07-13 | Panik-Flow nur per Maus, kein Panik-Hotkey; `Ctrl+Shift+!` ersatzlos gestrichen | B.5 (Historie: Anhang 3) |
| N6 / U7 | 2026-07-15 | Entsperr-/Boot-Fehlerbildschirm und entscheidbare Entsperr-Fehlerlogik | B.2 (`unlock()`) + B.4 |
| N7 | 2026-06-13 | `move_task`/`reorder_lists`; „Clear completed“ gestrichen | B.2 + Phase 7 (Historie: Anhang 3) |
| N8 | 2026-06-13 | Roadmap-Erweiterungen | Teil D (D.3) |
| N9 | 2026-06-13 | Startverhalten-Setting; ueberholt durch N11.6 (Fenster startet fest maximiert) | Anhang 3 (ueberholt) |
| N10.1 | 2026-07-08 | Verstaerkte Sperre („Panik light“), Raum-Bereinigung | B.8.2 |
| N10.2 | 2026-07-08 | Off-Knopf auf dem Lock-Screen | B.4 |
| N10.3 | 2026-07-08 | Panik-Endschirm mit Finish/Killswitch | B.4 (Abwaegung: B.10.5) |
| N10.4 | 2026-07-08 | Verhalten nach dem Killswitch | B.8.7 |
| N10.5 | 2026-07-08 | Bridge-Erweiterung `quit_app`/`killswitch`, G13-Folgen | B.2 + B.9 (G13) (Historie: Anhang 3) |
| N11.1.1-N11.1.6 | 2026-07-09 (N11.1.6: 2026-07-13, W15) | Ersatzlos gestrichene Features (Benachrichtigungen, Backups, Meta, Seed, JSON-Export, Faelligkeiten) | A.4 |
| N11.2 / U10, U12 | 2026-07-09 | Zweistufiger Export (md/txt), Undo nur beim Listen-Loeschen | Phase 7 + B.2 (Historie: Anhang 3) |
| N11.2.1 / U9 | 2026-07-13 | Undo-Architektur: RAM-Puffer, kein Soft-Delete | B.2 |
| N11.2.2 / U11 | 2026-07-15 | Randfaelle von `reorder`/`reorder_lists`/`move_task` | B.2 (Validierung: G20) |
| N11.2.3 | 2026-07-17 | Export ohne offene Liste: Umfang-Option "aktuelle Liste" ausgegraut, nur "alle Listen" waehlbar | Phase 7 (+ B.5 `Ctrl+E`) |
| N11.2.4 | 2026-07-17 | Setting `exportDone`: erledigte Aufgaben im Export ein-/ausblendbar (Default an), global fuer `export_list`/`export_all`, md und txt | Phase 7 (U10 Punkt 6) + B.6 (+ G20 Whitelist) |
| N11.3 / U8 | 2026-07-09, U8-Details 2026-07-13 | Ersteinrichtung, Passphrase-Regel (nur Mindestlaenge 12), Reset, Passphrase-Wechsel (a bis d) | B.2 (+ B.4 Onboarding, B.7/G8 KDF-Upgrade) |
| N11.4 | 2026-07-09 | Auto-Sperre-Default und Entsperr-Rate-Limit-Leiter | B.8.3 + B.8.4 |
| N11.4.1 / U6 | 2026-07-13 | Rate-Limit-Zustand persistiert (config.json, zwei Uhren, persist-before-verify) | B.8.4 (+ B.11) |
| N11.4.2 / U4 | 2026-07-15 | Definition der „Inaktivitaet“ der Auto-Sperre | B.8.3 |
| N11.4.3 / U17 | 2026-07-15 | Fest verdrahtete Argon2id-Parameter und der MemoryError-Randfall | B.7 (+ Code `memory` in B.2) |
| N11.5 / U14, U15 | 2026-07-09, praezisiert 2026-07-15 | Echter Windows-Flugmodus, `set_online`-/`get_wifi_signal`-Vertrag | B.2 (+ B.4; Abhaengigkeiten: Phase 0) |
| N11.6 / U16, U24 | 2026-07-09, praezisiert 2026-07-15 | Theme folgt Windows, Header, Profil, Fenster maximiert, Ton, Mini-Bounds | B.6 + B.4 (+ B.5 `Ctrl+J`) |
| N11.7 | 2026-07-09 | Settings-Whitelist neu; Roadmap-Folgen (keine Volltextsuche) | B.6 + G20 (Historie: Anhang 3) |
| N11.8.1 | 2026-07-09 | Killswitch = reine Datei-Operation | B.8.7 |
| N11.8.2 | 2026-07-09 | Start-Weiche: allein die Existenz von `tasks.db.enc` entscheidet | B.2 (`get_boot_state`) (Historie: Anhang 3) |
| N11.8.3 / U3 | 2026-07-09 | Zweitprofil-Spike (neun Fragen) und nativer Fallback | Phase 8 |
| N11.8.4 | 2026-07-09 | Win+L loest keine App-Sperre aus | B.8.1 (Historie: Anhang 3) |
| N11.9 / G28 | 2026-07-09 | Beide Verschluesselungs-Schichten, Arbeitskopie nie Klartext, Write-back identisch (U19/U20) | B.7 |
| N11.10 / W1 | 2026-07-13 | Sperre schaltet nicht mehr offline | B.8.2 |
| N11.11 (.1-.4) / S5, G35 | 2026-07-13 | `teardown(reason)`: eine Funktion, Soll-Sequenz, Schritt-/Ausgangs-Tabelle | B.8.5 |
| N11.11.5 (.1-.4) / U5 | 2026-07-13 | Native Dialoge und die aufgeteilte Auto-Sperre | B.8.6 |
| N11.12 (.1-.3) / S6, G29 | 2026-07-13 | Fehler-Hygiene, Ringpuffer, Logging-Politik | B.2 |
| N11.13 / U1 | 2026-07-13 | Onboarding-/Tresor-Bridge, dreiwertiger Boot-Zustand | B.2 + B.4 (Historie: Anhang 3) |
| N11.14 / S7 | 2026-07-13 | Triage des UX/UI-Audits | Anhang 2 |
| N11.15 (.1-.6) / U2, V8 | 2026-07-13, .5/.6: 2026-07-15 | `config.json`: Schema, Fehlerfaelle, unerreichbarer Tresor, Redirect, Ueberschreib-Schutz | B.11 |
| N11.16 | 2026-07-17 | Alle Toasts bis auf den Undo-Toast (N11.2.1) ersatzlos entfernt (Nutzerwunsch: keine Benachrichtigungen): erst die Erfolgs-Bestaetigungen, dann auch die Fehler-/Validierungs-Toasts; Fehler laufen still bzw. bleiben ueber das Status-Modal (G29-Ringpuffer) einsehbar | B.4 + B.2 (Toast-Politik + Fehlercode-Katalog) |
| N11.17 | 2026-07-21 | Panik-Endschirm bleibt dauerhaft ehrlich („Workspace cleared"); der fuer Phase 8 vorgesehene, bewusst falsche Aussenschirm („All data securely wiped") wird nicht gebaut, damit gilt G22 ausnahmslos (kehrt die frueher einzige G22-Ausnahme aus N10.3/B.10.5 um) | B.10.5 (+ B.4 N10.3, B.9 G22) |
| N11.18 / U3-Ergebnis | 2026-07-21 | Zweitprofil-Spike ausgefuehrt (`Code/tools/spike_u3_lockwindow.py`): kein Zwei-Profil-Beweis moeglich, **nativer Lock-Fenster-Fallback verbindlich** (kein `LOCK_PROFILE_DIR`); WebView-Abbau/Neuaufbau im selben Prozess samt G14-Wischbarkeit bewiesen; `setup_app()`-Vorbedingung dokumentiert; G6-Nebenbefund: `sqlcipher3` ohne `serialize` -> N11.9-Arbeitsdatei-Fallback (Schnappschuss via `VACUUM INTO`) verbindlich | Phase 8 (Spike-Ergebnis) |



### Herkunft der Sicherheits-Gates (Einleitungstexte der früheren zwei B.9-Tabellen)

Bis Umbau-Etappe 2 (2026-07-16) standen die Gates in B.9 in zwei Tabellen: dem
Grundset aus dem Security-Review und der Nachtragstabelle „NACHTRAG: Gates G13 bis
G35 (Code-Audit + Testlauf vom 2026-06-10, seither fortgeschrieben)". Die beiden
historischen Einleitungstexte (wann welches Gate kam), wortgleich hierher verschoben:

Zur ersten Tabelle: Aus dem Security-Review (2026-06-08) ergab sich eine klare
Trennung in „sofort erledigt" und „muss in der jeweiligen Phase erledigt werden".

Zur Nachtragstabelle: Ein vollständiges Code-Audit (Code-Review aller Module plus
23 automatisierte Checks gegen die echte Bridge-API auf einer Wegwerf-DB) hat
weitere Pflichtpunkte ergeben. Sie gelten zusätzlich zu den übrigen Gates; die
Phasen-Abschnitte listen nur noch die Gate-Nummern mit Stichwort und Verweis
auf diese Tabelle (normative Quelle, siehe Regel oben). Die Tabelle wird seit dem
Audit fortgeschrieben (behebt Plananalyse W18): G24 wurde mit der
Microsoft-Integration entfernt, G26 (Screenshot-Schutz, verworfen) und G27 kamen
später hinzu, G28 (Verschlüsselungs-Beweis) stammt aus N11.9 (2026-07-09)
und ist hier nur zusammengefasst (Volltext in N11.9). Am 2026-07-13 kamen aus
der Plananalyse dazu: G29 (Fehler-Hygiene, S6, Volltext in N11.12), G30
(Bedrohungsmodell, S4, Volltext in **B.10**) und G35 (gemeinsame
Sperr-/Beenden-Sequenz, S5, Volltext in N11.11). Am 2026-07-15 wurden die
Angriffsvektoren-Befunde A1 bis A7 der Plananalyse (Teil 5) entschieden und
eingearbeitet: **G31** (RAM-auf-Platte-Lecks, A1), **G32** (Tresor-Ort und
Cloud-Warnung, A2), **G33** (Dev-Altdaten, A3) und **G34** (Release-Härtung,
A4/A6) stehen jetzt als Gates in dieser Tabelle (die Zeile hier ist jeweils der
normative Volltext); A5 (Frontend-Integrität) ist als Ergänzung in G27
eingearbeitet, A7 (Fenstertitel) als verbindliche Regel in B.4 (bewusst kein
eigenes Gate, eine Zeile Regel genügt).

## ANHANG 2: Audit-Status (Triage des UX/UI-Audits)

*(Wortgleich umgezogen in Umbau-Etappe 3 aus „N11.14 Triage des UX/UI-Audits (2026-07-13, S7-Entscheid)“. Register: Anhang 1.)*

*Loest S7 der Plananalyse. Der Bauplan verwies bisher pauschal auf das Audit
(`Planung/weiteres/UX-UI Verbesserungen.md`, Stand 2026-06-12, "wird separat
abgearbeitet"). Inzwischen enthaelt es drei Sorten Punkte ohne Kennzeichnung, und wer es
als Arbeitsliste nimmt, baut Dinge, die laengst gestrichen sind (Suche, Faelligkeiten,
Meta-Feld, Sync-Statuspille). **Diese Triage ist ab sofort der Status des Audits.** Sie
gilt vor dem Audit-Dokument: bei Widerspruch gewinnt diese Tabelle.*

**Legende:** ✅ **erledigt** (gebaut oder anderweitig aufgeloest) · 🔵 **eingeplant**
(entschieden, steht in einer Phase) · 🟡 **gueltig** (offener Punkt, weiter zu tun) ·
❌ **hinfaellig** (durch spaetere Entscheidungen gegenstandslos, **nicht mehr bauen**).

| Audit | Status | Ein Satz |
|---|---|---|
| 1.1 Listen loeschen | ✅ erledigt | Loeschen ueber Sidebar-Kontextmenue mit Inline-Bestaetigung ist gebaut (`ctxList`, `confirmDeleteId`). |
| 1.2 Task-Loeschen ohne Bestaetigung, totes Delete-Modal | ✅/❌ erledigt (2026-07-17) | Sofort-Loeschen **bleibt** bewusst so (Undo gibt es nur fuer Listen, N11.2); der tote `case 'delete'`-Modalcode (Render-Block, `doDelete`, `do-delete`-Handler, Enum-Eintrag im State-Kommentar) wurde restlos entfernt. |
| 1.3 Glocke + Profil-Menue (tot, Fake-Daten) | ✅/❌ erledigt (2026-07-17) | Glocke ist **hinfaellig** (Benachrichtigungen ersatzlos entfernt, 2026-07-09); das Profil-Menue war komplett unerreichbarer toter Code (kein Avatar/Trigger im Header) und wurde samt `state.menu`/`open-profile` restlos entfernt (Phase 6.5 "Profil-Menue aufraeumen", mit Phase 7 umgesetzt). |
| 1.4 Status-Modal mit Fantasiewerten **[Sec]** | ✅ erledigt (2026-07-17) | Gate **G22** umgesetzt: das Status-Modal zeigt seit 2026-07-16 den ehrlichen Dev-Zustand (`active:false`, Warnfarbe, `dev_key`), dazu seit 2026-07-17 der G29-Ringpuffer ("Recent errors", N11.12); echte Verschluesselungswerte zeigt der Status erst ab Phase 8 (G22-Restsatz in B.9, siehe auch 8.4). |
| 1.5 Export meldet Erfolg ohne Datei | ✅ erledigt (2026-07-17) | Gate **G21c** umgesetzt: echter Save-Dialog, Datei wird wirklich geschrieben, Abbruch still (`canceled`); Format `md`/`txt` (N11.1.5), JSON hinfaellig. (Der frühere Erfolgs-Toast quittierte nur echten Schreiberfolg; er ist seit N11.16 ganz entfernt, ein Erfolg wird nicht mehr gemeldet.) |
| 1.6 CSS-/Handler-Leichen (`.t-del`, `.t-grip`, `.title-row`, `.airplane-pill`) | ✅ erledigt (2026-07-17) | Entscheid Phase 7: **loeschen**, alle vier CSS-Bloecke plus `del-task`-Handler entfernt; ein Hover-Papierkorb wird nicht nachgeruestet (Loeschen bleibt bewusst ueber die Rail, S7). |
| 1.7 Neue-Liste-Feld unsichtbar bei geschlossener Sidebar | 🟡 gueltig | Die Taste heisst heute `Ctrl+Shift+N` (B.5), der Bug ist derselbe: sie setzt `state.adding = true`, ohne die Sidebar zu oeffnen (`app.js`), das Feld liegt dann unsichtbar hinter der zugeklappten Sidebar. |
| 2.1 Sprachmix DE/EN | ✅ erledigt | UI ist durchgehend englisch, deutsche `title`-Tooltips gibt es nicht mehr (am Code geprueft). |
| 2.2 Mac-Symbole (⌘) | ✅ erledigt | Ueberall `Ctrl`/`Shift`. |
| 2.3 Shortcuts-Modal unvollstaendig | ✅ erledigt / ❌ teils | Modal ist aus B.5 vollstaendig (inkl. `Esc`, `?`, Maus-Gesten); der geforderte **Mini-Shortcut ist hinfaellig** (bewusst kein Shortcut, B.5: Mini nur per Rail). |
| 2.4 Irrefuehrende Toast-Texte | ✅ erledigt (2026-07-17) | "Back online, syncing" existiert nicht mehr; **alle** Toasts bis auf den Undo-Toast sind seit N11.16 entfernt (Nutzerwunsch, erst die Erfolgs-, dann die Fehler-/Validierungs-Toasts), es kann also gar kein irrefuehrender Toast-Text mehr erscheinen; interne Fehler bleiben ueber das Status-Modal (G29) einsehbar; die Verschluesselungs-/Wipe-Behauptungen sind ueber G22 ehrlich (Status-Modal seit 2026-07-16, Panik-Schirme seit 2026-07-17). |
| 2.5 Empty-States fuehren nicht | 🟡 gueltig | Kleine Politur, unverbindlich. |
| 3.1 `Esc` raeumt alles gleichzeitig ab | 🟡 gueltig | Gestaffeltes `Esc` (Modal -> Eingabe -> Auswahl -> Fokus/Mini) ist weiter offen; B.5 beschreibt heute bewusst das Alles-auf-einmal-Verhalten, eine Aenderung muss B.5 mitziehen. |
| 3.2 Blur legt eine Liste an | 🟡 gueltig | Am Code bestaetigt (`app.js`, `blur` committet das Neue-Liste-Feld): Wegklicken erzeugt ungewollt eine Liste. |
| 3.3 Kein Undo, nirgends | 🔵/❌ entschieden | Undo gibt es **nur** beim Listen-Loeschen (Phase 7, N11.2); Undo fuer Tasks/Abhaken/Umbenennen ist **hinfaellig**. |
| 3.4 Doppelklick/Klick sind unsichtbare Konventionen | ✅ erledigt/entschieden (2026-07-17) | Maus-Gesten stehen im Shortcuts-Modal; Hover-Aktionen auf der Karte kommen **nicht** (Entscheid mit 1.6: Loeschen bleibt ueber die Rail). |
| 3.5 Kein Rechtsklick-Kontextmenue | ✅ erledigt (2026-07-17) | Sidebar-Listen: `ctxList`; Task-Karten: „Move to…"-Kontextmenue (`ctxTask`, Phase 7/N11.2). |
| 3.6 Drag ohne Affordance/Alternative | 🟡 gueltig (reduziert) | Sidebar-Eintraege zeigen als Drop-Ziel jetzt einen Akzent-Rahmen (`.drop-target`); Griff-Affordance und Tastatur-Alternative fehlen weiterhin. |
| 3.7 Aufgaben zwischen Listen verschieben | ✅ erledigt (2026-07-17) | `move_task(id, target_list_id)` umgesetzt (Phase 7, N7/N11.2; Drag auf Sidebar-Eintrag + „Move to…"-Kontextmenue). |
| 3.8 Completed-Sektion | 🟡/❌ gemischt | `doneOpen`-Reset beim Listenwechsel bleibt **gueltig**; **"Clear completed" ist gestrichen** (N11.1) und das Meta-Argument **hinfaellig** (Meta-Feld entfaellt, N11.1.3). |
| 3.9 Listen nicht sortierbar | ✅ erledigt (2026-07-17) | `reorder_lists(ordered_ids)` umgesetzt (Phase 7, N7/N11.2; Drag and Drop in der Sidebar). |
| 3.10 Keine Tastaturnavigation fuer Aufgaben | 🟡 gueltig | Pfeile/Space/F2/Entf fehlen weiterhin; groesster offener A11y- und Power-User-Punkt. |
| 3.11 Listenwechsel per Tastatur | ✅ erledigt | `Ctrl+1` bis `Ctrl+9` und `Ctrl+Pfeil hoch/runter` (B.5). |
| 3.12 Einzeltasten-Hotkeys riskant (`G`, `F`) | 🟡 gueltig (**gewichtiger geworden**) | Die Sync-Begruendung ist hinfaellig, aber `G` schaltet seit N11.5 den **echten Windows-Flugmodus** (alle Funkgeraete des PCs): ein versehentliches `G` hat jetzt reale Folgen, Bestaetigung oder deutlich sichtbarer Indikator (4.2) sind zu entscheiden. |
| 3.13 Rail-Auto-Hide schwer zu entdecken | 🟡 gueltig | Pin sichtbarer machen oder Rail per Default gepinnt ausliefern. |
| 3.14 Mini-Modus-Haerten | 🟡 gueltig (reduziert) | Der `Esc`-Teil haengt an 3.1; Listenwechsel im Mini-Fenster ist Roadmap (D.3). |
| 3.15 Rail-Aktionen ohne Auswahl wirken tot | 🟡 gueltig | Copy/Edit/Delete ohne Auswahl dimmen und einheitlich "Select a task first" melden. |
| 3.16 Doppelklick-Reset des Sidebar-Resize | 🟡 gueltig | Kleine Konvention, offen. |
| 4.1 Kein Listentitel im Hauptbereich | 🟡 gueltig | Orientierung fehlt bei geschlossener Sidebar. |
| 4.2 Online/Offline fast unsichtbar | 🔵 eingeplant (**wichtiger geworden**) | N2 (persistente Offline-Pille); seit N11.5 zeigt sie einen echten Funk-Zustand des ganzen PCs an, siehe 3.12. |
| 4.3 Hardcodierte Farben statt Tokens | 🟡 gueltig | `#e07a2c`, hartes `#fff`: auf `--accent`/`--danger`/`--accent-ink` umstellen. |
| 4.4 Inline-Styles in JS-Templates **[Sec]** | 🟡 gueltig | Ziel bleibt: Styles in Klassen, danach CSP auf `style-src 'self'` verschaerfen (Defense in Depth, passt zu B.9). |
| 4.5 Sehr kleine Schriftgrade | 🟡 gueltig | Nichts unter 10px (Sidebar-Zaehler 8,5px). |
| 4.6 Kontrast (WCAG) | 🟡 gueltig | Kontrast-Audit steht aus. |
| 4.7 Theme "System" fehlt | 🔵 eingeplant | N11.6: `theme` = `auto\|light\|dark`, Default `auto`, folgt Windows live. |
| 4.8 Scrollbars inkonsistent | 🟡 gueltig | Mini/Fokus haben Default-Scrollbars. |
| 4.9 Toast-Verhalten (Dauer, Stapel, Position) | ⬜ groesstenteils hinfaellig (N11.16) | Erfolgs- und Fehler-Toasts gibt es nicht mehr; es bleibt nur der **eine** Undo-Toast (unten links, ca. 6 s, mit Ablaufbalken, kein Stapel). Nur dessen Standzeit/Position ist ueberhaupt noch eine Frage. |
| 4.10 Enter-Hinweis in der Dock-Eingabe | 🟡 gueltig | Kleine Politur. |
| 4.11 Selektion vs. Bearbeiten-Optik | 🟡 gueltig | `.editing` staerker differenzieren. |
| 4.12 Sidebar-Toggle-Icon (Plus) | 🟡 gueltig | Panel-/Menue-Icon statt Plus (`Icons.Menu` liegt ungenutzt bereit). |
| 5.1 bis 5.7 Barrierefreiheit | 🟡 gueltig (komplett) | Fokus-Stile, Rollen/`aria`, Modal-Semantik + Fokus-Trap, `aria-live` fuer Toasts, `prefers-reduced-motion`, Zielgroessen, Tooltip-Labels: **kein** Punkt davon ist erledigt oder hinfaellig. |
| 6.1 Voll-Re-Render (Scrollverlust) | 🟡 gueltig | Scrollposition sichern/wiederherstellen bleibt Pflichtkandidat; **hinfaellig ist nur** die dort erwaehnte "`textContent`-Umstellung als Gate": ein solches Gate existiert nicht, es gilt weiter die `esc()`-Regel aus B.9. |
| 6.2 Kein Pending-/Loading-Zustand | 🟡 gueltig (reduziert) | Login/Sync sind weg, aber das **Entsperren** braucht einen Fortschritt (Argon2id dauert spuerbar, N4), und der Export-Save-Dialog blockiert. |
| 6.3 Boot-Fehlerbildschirm | 🔵 eingeplant | N6 (Phase 8), zusammen mit dem `vault`-Fehlercode aus B.2/N11.12. |
| 6.4 Doppelte Sidebar-Toggle-Logik | 🟡 gueltig | Code-Hygiene, haengt mit 1.7 zusammen. |
| 7.1 Faelligkeiten (`due_at`) | ❌ hinfaellig | `due_at` ist entfernt (W15-Entscheid); keine Faelligkeiten, keine Erinnerungen. |
| 7.2 Suche/Filter | ❌ hinfaellig | Volltextsuche ist ersatzlos gestrichen (N11.1). |
| 7.3 Meta-Feld erklaeren/strukturieren | ❌ hinfaellig | Das Meta-Feld faellt komplett weg (N11.1.3): eine Aufgabe ist nur `text` + `done`. |
| 7.4 Aufgaben-Notizen/Details | ❌ hinfaellig (Kern) | Widerspricht "nur `text` + `done`"; allenfalls spaetere Roadmap (D.3). |
| 7.5 "Heute"-/Smart-Ansicht | ❌ hinfaellig | Setzt Faelligkeiten voraus (7.1). |
| 7.6 Settings fuer kommende Phasen | 🔵/❌ gemischt | `autoLock` (N11.4) und Startverhalten "maximiert" (N11.6) sind **eingeplant**; der **Screenshot-Schalter ist hinfaellig** (G26 verworfen, nicht wieder einbauen). |
| 7.7 Mini-Modus-Erweiterungen | 🟡 gueltig (Roadmap) | Listenwechsel im Mini-Fenster, D.3. |
| 8.1 Lock-Screen mit echtem Passphrase-Feld **[Sec]** | 🔵 eingeplant | N4 + N11.3/N11.4 (Show/Hide, Fehlerzustand, Caps-Lock-Hinweis, Rate-Limit-Anzeige, Entsperr-Fortschritt); Phase 8 (nicht mehr "Phase 11"). |
| 8.2 Panik-Flow | ✅ erledigt/ueberholt | N5 (kein Hotkey, nur Maus) + N10 (Endschirm mit Finish/Killswitch). |
| 8.3 Sign-in/Sync-UX | ❌ hinfaellig | Es gibt keinen Login und keinen Sync mehr; nur die Statuspille lebt weiter als Offline-Pille (4.2). |
| 8.4 Status-Modal als ehrliches Security-Dashboard **[Sec]** | 🔵 teils erledigt (2026-07-17) | Ehrlicher Dev-Status (G22) und der G29-Ringpuffer sind da (siehe 1.4); das volle Dashboard mit echten Werten (Argon2-Parameter, Pepper vorhanden, letzter Wrap, BitLocker-Status G31) kommt mit Phase 8. |
| 9. Priorisierte Uebersicht | 🟡 teils ueberholt | Die P1/P2/P3-Tabellen des Audits enthalten hinfaellige Zeilen (Sync, Suche, Faelligkeiten); **verbindlich ist diese Triage**, nicht die alte Prioritaet. |
| 10. Was bereits gut ist | ✅ unveraendert gueltig | Design-System, Dichte-Umschaltung, Dock-/Collapse-Animationen, Toast-Layer, `esc()`/CSP-Disziplin: beim Aufraeumen erhalten. |

**Redaktionsregel:** Das Audit-Dokument selbst wird nicht mehr fortgeschrieben. Wer einen
Audit-Punkt umsetzt oder verwirft, aendert **diese** Tabelle (Status + ein Satz). Ein
Audit-Punkt ohne Zeile hier gilt als nicht entschieden und wird nicht gebaut.


## ANHANG 3: Historie / hinfällige Stände

> **Gefüllt (Umbau-Etappen 3 und 5, 2026-07-16):** Hier liegt die Historie: die in
> Etappe 3 eingedampften Nachtrag-Blöcke, seit Etappe 5 auch die durchgestrichenen
> bzw. überholten Reste aus dem Baupfad und ANHANG 1 alt (Seed-Daten). Teil A bis C
> enthält keine hinfälligen Passagen mehr, nur noch Verweise hierher.

### Eingedampfte Nachtrag-Bloecke (Umbau-Etappe 3)

Die folgenden Bloecke sind reine Historie: ihre Norm steht vollstaendig im Haupttext (Zeiger je Zeile im Entscheidungsregister, Anhang 1). Die Blocktexte sind wortgleich hierher verschoben, damit nichts geloescht wird (Umbauplan, G-Erhalt-4).

#### NACHTRAG (2026-06-13): UX-Pflichten und -Erweiterungen aus dem UX/UI-Audit (Kopf)

Nach dem lokal nutzbaren Meilenstein (Phase 6 + 6.5) wurde ein vollständiges
UX/UI-Audit erstellt (`Planung/UX-UI Verbesserungen.md`, Stand 2026-06-12). Dieser
Nachtrag überführt **alle Audit-Punkte, die noch zu bauende Features betreffen**, in
den Bauplan, damit sie nicht verloren gehen. Reine Sofort-Korrekturen (Mac-Symbole,
UI-Sprache) wurden am 2026-06-13 direkt im Code erledigt (siehe Entscheidung unten).
Die verbleibenden **Gegenwarts-Mängel** (z.B. unehrliche Status-/Toast-Texte, fehlende
Tastaturnavigation, A11y, Voll-Re-Render) sind nicht Teil dieses Nachtrags; sie stehen
im Audit (Prioritäten P1 bis P3) und werden separat abgearbeitet. Querverweise in der
Form „(UX x.y)" zeigen auf den jeweiligen Abschnitt im Audit.

**Was bereits im Plan steht (nur Querverweis, hier nicht erneut spezifiziert):**
Profil-Menü aufräumen (UX 1.3) -> Phase 6.5; Export-Save-Dialog + ehrliches Feedback (UX 1.5)
-> Phase 7 / Gate G21c; Undo beim Listen-Löschen (UX 1.2, 3.3) -> Phase 6.5 + Phase 7;
ehrlicher `get_status()` und Status-Modal (UX 1.4, 8.4) -> Gate G22 + Phase 8;
Auto-Lock-Timeout (UX 7.6) -> B.8; serverseitige Lock-Durchsetzung -> Gate G13
(Screenshot-Schutz / G26 wurde verworfen, siehe oben). Diese Punkte sind verbindlich
an den genannten Stellen, hier nur zur Vollständigkeit gelistet.

#### N5. Phase 8: Panik-Flow nur per Maus, kein Panik-Hotkey (UX 8.2) [Sec]

*(Aktualisiert 2026-07-08, siehe N10: der Panik-Flow endet jetzt im Endschirm mit
Finish/Killswitch, nicht mehr im Lock-Screen. Entschieden 2026-07-13, löst W5 der
Plananalyse: der Hotkey `Ctrl+Shift+!` ist ersatzlos gestrichen.)*
- Der volle Panik-Flow (Endschirm, Killswitch) bleibt **bewusst mehrstufig** und nur
  per Maus über den Rail-Button erreichbar (Kippschalter + Confirm): die Mehrfach-
  Bestätigung schützt vor versehentlichem Auslösen, gerade weil der Killswitch
  unwiderruflich ist.
- **Es gibt keinen Panik- oder Notfall-Hotkey.** Die früher geplante Belegung
  `Ctrl+Shift+!` (zeitweise als Panik-Auslöser, zuletzt als verstärkte Sperre ohne
  Rückfrage gedacht) ist ersatzlos entfernt und darf nicht wieder eingeführt werden.
  Begründung: seit N10 ist ohnehin **jede** Sperre verstärkt (Raum-Bereinigung vor
  dem Lock-Screen), `Ctrl+L` deckt den „schnell alles zu"-Fall damit vollständig und
  ohne Datenverlust-Risiko ab; der Panik-Modus mit seinem unwiderruflichen Killswitch
  gehört bewusst nicht auf die Tastatur. Im Code ist entsprechend kein solcher Hotkey
  verdrahtet; die Layout-Tücke von `!` auf Nicht-DE-Layouts (U22 der Plananalyse)
  entfällt damit ebenfalls.

#### N7. Neue Fähigkeiten mit Bridge-Erweiterung (einplanen, z.B. Phase 7 oder Folge-Iteration)

Echte Funktionslücken einer Mehrlisten-App, je mit kleiner Backend-Ergänzung. Kein
Sicherheitsthema, daher zeitlich flexibel, aber fest eingeplant:
- **Aufgaben zwischen Listen verschieben (UX 3.7):** neue Bridge-Methode
  `move_task(id, target_list_id)` (oder `edit_task` um `list_id` erweitern); Auslösung
  per Drag auf einen Sidebar-Eintrag und per „Move to…" im Kontextmenü. Validierung wie
  bei `add_task` (Gate G20), Zielposition ans Ende der Ziel-Liste.
- **Listen umsortieren (UX 3.9):** das Schema hat `lists.position`, aber kein UI. Neue
  Methode `reorder_lists(ordered_ids)` analog zu `reorder` (gleiche Typprüfung, Gate
  G20), Drag & Drop in der Sidebar.
- **„Clear completed" (UX 3.8):** ~~Sammel-Löschen aller erledigten Aufgaben einer
  Liste, mit Bestätigung bzw. Undo (analog zum Listen-Undo aus Phase 7). Eigene Methode
  (z.B. `clear_completed(list_id)`), die serverseitig löscht.~~ **wird nicht gebaut**
  (Entscheidung N11.2/N11.7).

#### N9. Einstellungen, Vorbereitung künftiger Phasen (UX 7.6)

~~Ergänzend zu den schon geplanten Settings (Auto-Lock-Timeout B.8): **Startverhalten**
(maximiert vs. letzte Fenstergröße) als Einstellung vorsehen.~~ **[Überholt durch
N11.6: das Fenster startet fest maximiert, ohne Setting.]**
Weiter gültig: Die bestehende Settings-Struktur (Zeile + Segment, B.6) trägt neue Keys
ohne Umbau; jeder neue Key muss in die `set_setting`-Whitelist aus Gate G20
aufgenommen werden.

#### N10. Verstärkter Lock, Off-Knopf und Panik-Endschirm mit Killswitch (2026-07-08) [Sec] (Kopf und Punkt 5)

Entscheidung vom 2026-07-08; ersetzt bzw. präzisiert Teile von B.4, B.8, N5 und
Phase 8 Punkt 1/2. Die UI-Anteile sind bereits umgesetzt (Stand Phase 6.5); die
Sicherheits-Anteile (echte Schlüssel, sicheres Wischen) bleiben Pflicht in Phase 8.

**5. Bridge-Erweiterung und Phase-8-Folgen.** Neu in B.2: `quit_app()` und
`killswitch()`. `killswitch()` ist nur aus dem Panik-Endschirm erreichbar; ein
direkter Aufruf über eine XSS wäre Datenvernichtung per Fernzugriff, die
`esc()`-Pflicht aus B.9 gilt hier also doppelt. Für Phase 8 gilt: Gate G13 ist als
**Allowlist** formuliert (`ALLOWED_WHEN_LOCKED = {"unlock", "quit_app", "killswitch",
"get_state", "get_boot_state", "choose_vault_dir", "create_vault", "reset_vault"}`,
normative Fassung in B.9); `quit_app()` und `killswitch()` stehen dort
neben `unlock()` **ausdrücklich als erlaubt** (beide sind destruktiv bzw. beendend,
geben aber nie Daten preis; der Killswitch soll gerade ohne Passphrase funktionieren).
Der Phase-8-Killswitch löscht dann `tasks.db.enc` samt `.bak`-Generation und
Vault-Metadaten (Salt, Pepper-Verweis) direkt, wofür keine Schlüssel nötig sind.

#### NACHTRAG N11 (2026-07-09): Entscheidungen aus der Luecken-Klaerung (verbindlich) (Kopf/Vorbemerkung)

Vorbemerkung: Dieser Nachtrag schliesst gezielt alle Stellen, an denen der Plan
bisher offen war und eine ausfuehrende KI haette raten muessen. Alle Punkte sind
vom Nutzer bestaetigt und **ueberschreiben** frueher anderslautende Formulierungen
an den genannten Stellen. Im Zweifel gilt N11. Phasennummerierung nach der aktuellen
Fassung: Sicherheit = **Phase 8**, Auslieferung/Build = **Phase 9** (die fruehere
Benachrichtigungs-Phase ist entfallen, siehe N11.1.1).

**Konsolidierungs-Stand (2026-07-13, Plananalyse S3):** Alle von diesem Nachtrag
(und von N10) ueberschriebenen Stellen im Haupttext sind inzwischen direkt
korrigiert bzw. ausdruecklich als gestrichen markiert. N10 und N11 dienen seither
als **Aenderungsprotokoll** (Entscheidung, Datum, Begruendung), nicht mehr als
vorrangige Korrekturschicht; die Vorrangregel oben bleibt nur als Sicherheitsnetz
fuer uebersehene Reste. Neue Entscheidungen werden nach der Redaktionsregel in der
Einleitung sofort an Ort und Stelle eingearbeitet und hier nur noch protokolliert.

#### N11.2 Phase 7: Export, Undo, Verschiebe-Features

- **Zweistufiger Export.** Der Rail-Button "Export" (bzw. `Ctrl+E`) speichert **nicht**
  direkt, sondern oeffnet zuerst eine kleine Pille an der **linken Seite der rechten
  Rail**. **Schritt 1: Umfang** ("nur aktuelle Liste" oder "alle Listen mit allen
  Aufgaben"). **Schritt 2: Format** (`md` oder `txt`). Danach der Save-Dialog.
- **md-Formatierung bei "alle Listen".** Sauber strukturiert: Listennamen als groessere
  Ueberschrift (z.B. `#`), die einzelnen Aufgaben darunter kleiner (`- [ ]`/`- [x]`).
  Bei "nur aktuelle Liste" wie bisher.
- **Undo nur beim Listen-Loeschen** (Toast "List deleted" mit "Undo", ca. 6 s). Einzelne
  Aufgaben werden weiterhin sofort und ohne Undo geloescht. "Clear completed" wird
  **nicht** gebaut. **Die verbindliche Architektur (RAM-Puffer, kein Soft-Delete, genau
  eine Loeschung, Wiederherstellung an alter Position, Verfall beim Sperren/Beenden) steht
  in N11.2.1.**
- **N7-Features hier mitbauen:** `move_task(id, target_list_id)` (Drag auf einen
  Sidebar-Eintrag plus "Move to..."-Kontextmenue) und `reorder_lists(ordered_ids)`
  (Drag and Drop in der Sidebar). Validierung wie `add_task` (G20). Volltextsuche und
  "Clear completed" entfallen.

#### N11.7 Settings-Whitelist und Roadmap-Folgen

- **Settings-Whitelist (G20) neu:** entfernt werden `notify`, `notifyInApp`,
  `notifyWindows` (bereits weg) und das ohnehin unbenutzte `toolbar`; hinzu kommen
  `theme` (`auto`/`light`/`dark`), `sound` (bool), `autoLock` (Minuten, `0` = nie),
  `exportDone` (bool, erledigte Aufgaben in den Export, Default an, 2026-07-17).
  Weiter gueltig: `accent`, `density`, `sidebar`, `railPinned`, `sidebarWidth`. Der
  `seeded`-Marker bleibt Backend-Marker (verhindert kuenftiges Demo-Seeding generell,
  da ohnehin nie geseedet wird). `dark` entfaellt zugunsten von `theme` (N11.6).
- **N8-Roadmap:** Volltextsuche wird **nicht** gebaut; die Aufgaben-Detailansicht bleibt
  Roadmap (spaeter); die Meta-Feld-Frage ist durch die Entfernung (N11.1.3) erledigt.

#### N11.8 Phase 8: Sicherheits-Widersprueche aufgeloest [Sec] (Kopf, Punkt 2 und Punkt 4)

Vier Stellen, an denen sich spaetere Phasen bisher gegenseitig widersprachen. Diese
Entscheidungen ueberschreiben die genannten Passagen; im Zweifel Security first.

2. **Start-Weiche eindeutig:** Beim Start entscheidet **allein die Existenz von
   `tasks.db.enc`** (Pfad aus `config.json`, N11.3): vorhanden -> Lock-Screen (nur
   Passphrase, N4); fehlt (frischer Rechner, nach Reset, nach Killswitch) -> Onboarding
   (Speicherort waehlen, Passphrase min. 12, leeren Tresor anlegen; N11.3, N11.1.4).
   *Praezisiert die Absolut-Formulierung "startet immer im Lock-Screen" in B.8.*

4. **Windows-Sitzungssperre (Win+L) loest KEINE App-Sperre aus.** *Ueberschreibt die
   "Windows-Sperre"-Zeile in der B.8-Tabelle, die B.8-Kernregel und den
   `WTSRegisterSessionNotification`/`WM_WTSSESSION_CHANGE`-Absatz in B.8/Phase 8; der
   Platzhalter in `main.py` und in Phase 3 wird entfernt, nicht verdrahtet.* Win+L tut
   fuer NoaToDo **nichts**. Die verlaessliche Sperre ist allein die **Auto-Sperre nach
   Inaktivitaet** (N11.4), und die ist **garantiert, auch waehrend der PC gesperrt ist:**
   ein Hintergrund-Timer (monotone Uhr, eigener Thread) laeuft **unabhaengig von
   Fensterfokus und Windows-Sitzungszustand** weiter und feuert nach Ablauf des Timeouts
   (Default 15 min, N11.4), auch wenn der PC zwischenzeitlich per Win+L gesperrt wurde.
   Kommt der Nutzer zurueck, ist NoaToDo garantiert gesperrt. Ein reiner **Fokuswechsel
   sperrt nicht** (B.8 bleibt hier gueltig), ebenso wenig Minimieren/Verschieben; **nur**
   der abgelaufene Timeout sperrt.

#### N11.13 Einrichtung, Tresor-Verwaltung und der dreiwertige Boot-Zustand (2026-07-13, U1-Entscheid) [Sec]

*Loest U1 der Plananalyse. B.2 nannte sich "vollstaendige Methodenliste", hatte aber
keine einzige Methode fuer Tresor anlegen, Speicherort waehlen, Passphrase aendern und
Reset, und `get_state().locked` kann den dritten Boot-Zustand ("es gibt noch keinen
Tresor", N11.8.2) gar nicht ausdruecken; B.4 hatte keinen Onboarding-Abschnitt. Ohne das
haette die ausfuehrende KI die halbe Phase 8 frei geraten. Die Vertraege stehen jetzt in
B.2 (Methoden + Fehlercodes) und B.4 (Screens); dieser Abschnitt haelt die Entscheidungen
dahinter fest.*

- **Der Boot-Zustand ist dreiwertig, nicht zweiwertig.** Neue Bridge-Methode
  `get_boot_state()` -> `{ state: 'onboarding'|'locked'|'unlocked', vault_path }`. Sie ist
  der **erste und einzige** Aufruf beim Start; das Frontend rendert vorher nichts. Die
  Weiche ist genau die aus N11.8.2 (allein die Existenz von `tasks.db.enc` am Pfad aus
  `config.json` entscheidet). `get_state()` bleibt, wie es ist (Gesamtzustand **nach** dem
  Entsperren, gesperrt nur `{"locked": true}`); es wird **nicht** um einen dritten Zustand
  aufgebohrt, damit die G13-Regel "gesperrt gibt `get_state` nichts heraus" scharf bleibt.
- **Vier neue Methoden fuer Einrichtung und Verwaltung** (Vertraege in B.2):
  `choose_vault_dir()` (nativer Ordner-Dialog im Backend, prueft Schreibbarkeit, warnt bei
  Cloud-Pfaden, G32), `create_vault(path, passphrase)` (Pepper + Salt + Argon2-Parameter
  erzeugen, leere DB, `tasks.db.enc` schreiben, Pfad in `config.json`; danach entsperrt),
  `change_passphrase(old, new)` (Einstellungen, nur entsperrt) und `reset_vault()`
  (Lock-Screen, der Ausweg der vergessenen Passphrase).
- **G13-Allowlist waechst um genau vier Namen:** `get_boot_state`, `choose_vault_dir`,
  `create_vault`, `reset_vault`. Begruendung: Alle vier muessen **ohne Schluessel**
  laufen (es gibt noch keinen Tresor, oder die Passphrase ist vergessen) und geben nie
  Daten heraus; `reset_vault` loescht nur. `change_passphrase` steht bewusst **nicht**
  drin: es braucht die Schluessel und damit den entsperrten Zustand. Das ist genau der
  von G13 vorgesehene Weg, eine Methode **bewusst** freizuschalten, statt die
  Ausnahmenliste driften zu lassen.
- **`reset_vault()` ist kein eigener Loesch-Pfad.** Es ruft die gemeinsame Sequenz aus
  N11.11 mit `reason='reset'`: DB schliessen, Schluessel nullen, dann erst
  `tasks.db.enc` + `.bak` + Vault-Metadaten + DPAPI-Pepper loeschen, `PROFILE_DIR`
  wischen, danach **nicht** beenden, sondern in das Onboarding springen (Schritte 6 bis 9
  der Sequenz, kein Schritt 10/11). Im UI ist es wie der Killswitch abgesichert
  (Bestaetigung, dann `RESET` tippen), erreichbar ueber einen unauffaelligen
  "Forgot passphrase?"-Link im Lock-Screen.
- **Die Verlust-Warnung ist Pflichttext mit aktiver Bestaetigung** (B.4, Onboarding-Screen
  2). Sie nennt **beides**: keine Wiederherstellung bei vergessener Passphrase **und** die
  Bindung an dieses Windows-Konto (anderer PC / neu aufgesetztes Profil = Datenverlust,
  auch mit korrekter Passphrase, V2/G18). Ohne gesetzte Checkbox kein Weiter; kein
  vorangekreuztes Haekchen.
- **Neue Fehlercodes waren nicht noetig:** zu kurze Passphrase und untauglicher Pfad sind
  `invalid`, falsche alte Passphrase ist `passphrase` (samt Rate-Limit, N11.4), ein
  abgebrochener Ordner-Dialog ist `canceled`, ein unerreichbarer oder kaputter Tresor ist
  `vault` (Fehlerbildschirm N6 mit Wiederholen und Reset). Der Katalog in B.2 bleibt
  unveraendert gueltig.
- **Seit 2026-07-15 entschieden (war offen):** das genaue `config.json`-Schema samt Verhalten
  bei fehlender/korrupter Datei und unerreichbarem Vault-Pfad (Befund U2) steht jetzt
  vollstaendig in **N11.15**. (Die vier Details des Passphrase-Wechsels, Befund U8, sind seit
  dem 2026-07-13 entschieden und stehen direkt in N11.3: frisches Salt/Nonce, Pepper
  bleibt, `.bak` sofort mitziehen, Argon2-Parameter auf G8-Soll heben.)


### Durchgestrichene und überholte Reste aus dem Baupfad (Umbau-Etappe 5)

Die folgenden Passagen sind wortgleich hierher verschoben (Umbauplan, Etappe 5);
an der Ursprungsstelle steht nur noch ein Verweis auf Anhang 3.

**Aus B.8.2 (Verstärkte Sperre), der durch N11.10 gestrichene Alt-Wortlaut:**

**[Gestrichen durch N11.10: „offline schalten" und „Offline bleibt die App, bis der
Nutzer es bewusst wieder einschaltet." Die Sperre fasst den Online-Zustand nicht mehr
an; nach dem Entsperren gilt der vorherige Zustand unverändert weiter.]**

**Aus D.3 (Roadmap-Erweiterungen, Etikett N8), die zwei hinfälligen Listenpunkte:**

- **Volltextsuche/Filter (UX 7.2):** ~~`Ctrl+F`-Overlay mit Fuzzy-Filter~~ **wird nicht
  gebaut** (Entscheidung N11.7).
- **Meta-Feld benennen/strukturieren (UX 7.3):** ~~erledigt~~ **hinfällig**: das
  Freitext-`meta` wurde ersatzlos entfernt (N11.1.3).

### ANHANG 1 alt: Seed-Daten (Startfüllung der DB) [HINFÄLLIG]

> **Hinfällig seit N11.1.4:** Es werden **keine** Demo-Seed-Daten mehr eingespielt; ein
> frischer Tresor startet immer leer. Dieser Anhang bleibt nur als historische Referenz
> (frühere Startfüllung) stehen und ist nicht mehr umzusetzen.

Beim ersten Start einspielen (entspricht dem Konzept), alle Listen sind rein lokal.

- **Reading List**
  - offen: „Going Zero" (Anthony McCarten), „On Leadership" (Tony Blair),
    „One of Us Is Back" (Karen M. McManus), „Money" (Martin Amis),
    „Fahrenheit 451" (Ray Bradbury)
  - erledigt: „Project Hail Mary" (Andy Weir), „The Every" (Dave Eggers),
    „Klara and the Sun" (Kazuo Ishiguro)
- **Ideas**
  - offen: „Local-first note encryption" (sketch), „Weekend pottery class",
    „Build a mechanical keyboard"
- **Homework**
  - erledigt: „Statistics problem set 4" (submitted)
- **Programming**
  - offen: „Wire pywebview js_api bridge", „SQLite schema + migrations",
    „Harden Content Security Policy", „Local task reminders"
  - erledigt: „Scaffold project structure", „Pick warm-terminal theme",
    „Set up WebView2 window"
- **Travel** (lokal)
  - offen: „Lisbon, Alfama walking route", „Kyoto in shoulder season",
    „Dolomites hut-to-hut", „Reykjavík stopover", „Faroe Islands",
    „Patagonia (someday)"
- **Life Goals** (lokal)
  - offen: „Run a half marathon", „Learn conversational Japanese",
    „Read 24 books this year", „Visit grandparents monthly",
    „Plant a small herb garden"

## ANHANG 4: Icon-Set

Das Konzept bringt ein eigenes, konsistentes Line-Art-Icon-Set mit (24er-Grid,
Strichstärke 1.7, runde Enden). Diese SVG-Pfade **1:1 aus dem Konzept übernehmen**
(`Icons`-Objekt). Benötigte Icons: `Menu, Close, Shield, Plus, Check, Gear,
Chevron, Grip, Plane, Wifi, Expand, Palette, Share, Help, Lock, Unlock, Alert, Copy,
Pencil, Trash, Diag, Globe, Note, Sun, Moon, User, Logout, Pin, Download`. Das
App-Logo (`NoaToDo Logo.png`, orangenes „N" im Kreis) zusätzlich als Fenster-/Taskbar-
Icon verwenden.

---

## Schnell-Checkliste (für die ausführende KI)

*(Stand 2026-07-17: Phasen 0 bis 7 sind abgeschlossen, die App laeuft lokal. Die Haken
fuer 0 bis 5 wurden am 2026-07-13 nachgetragen. Pflege-Regel: Diese Liste wird bei
**jedem** Phasenabschluss sofort mit Datum abgehakt. Ein offener Haken bei einer laengst
fertigen Phase ist eine Einladung, von vorne zu bauen.)*

- [x] Phase 0, Struktur + Abhängigkeiten, leeres Fenster (erledigt; `requirements.lock.txt` liegt vor, 🔒 G11 damit umgesetzt)
- [x] Phase 1, `db.py` Schema + CRUD (erledigt; kein Demo-Seed mehr, N11.1.4)
- [x] Phase 2, `api.py` Bridge (lokal) (erledigt)
- [x] Phase 3, `main.py` Fenster + Verdrahtung (erledigt) **, inkl. 🔒 G12 (Navigation abriegeln): vorgezogen und am 2026-07-17 mit Phase 7 umgesetzt**
- [x] Phase 4, `index.html` Gerüst, Bridge im Fenster bewiesen (erledigt)
- [x] Phase 5, `style.css` (CSS 1:1 aus Konzept) + lokale Fonts (erledigt)
- [x] Phase 6, `app.js` komplette UI + Interaktionen  ← **Meilenstein: lokal voll nutzbar**
- [x] Phase 6.5, UX-Nacharbeiten (Inline-Edit, Task-Löschen, Task-Auswahl, gehärtete Einzel-Task-Kopie ✅G23, Strg+C entfernt, Mini-on-top, Screenshot-Schutz ❌G26 verworfen); Rest-Pflichten in 7 verplant
- [x] Phase 7, zweistufiger Export (nur md/txt, N11.2) + Undo (nur Listen-Löschen) + `move_task`/`reorder_lists` **+ 🔒 G20 (lokale Eingabe-Validierung), G21 (Export-Härtung + Save-Dialog), G22 (ehrlicher Status), G29 (Fehler-Hygiene + Fehlercode-Katalog B.2 + Logging-Politik, N11.12), G12 vorgezogen: alle ✅** (erledigt 2026-07-17; G23 schon 2026-06-10)
- [ ] 🔒 G30 (Doku, **vor** Phase 8): Bedrohungsmodell **B.10** gelesen und beim Bauen zugrunde gelegt (Angreiferklassen K1-K6, Nicht-Ziele, Voraussetzungen; Abschnitt ergänzt 2026-07-13 aus Plananalyse S4). Jedes neue Gate trägt seine Klasse in B.10.6 nach
- [ ] Phase 8, Lock / Emergency / Doppel-Kaskade AES-256 + ChaCha20 (B.7) **+ 🔒 G6 (In-Memory-DB), G7 (Hex-Raw-Key), G8 (Argon2id-Kosten; Passphrase nur Mindestlänge 12, kein Stärkemesser, N11.3), 🔴 G9 (`DEV_AES_KEY` entfernen), 🔴 G13 (Lock serverseitig), G14-Rest (PROFILE_DIR sicher wischen bei lock/panic/quit, **Fenster-X = gleicher sicherer Beenden-Pfad wie `quit_app()`**; fester Ordner + Altlasten-Wisch ✅ 2026-06-20), G15 (HKDF/kein Hash), G16 (.enc-Format), G17 (Write-back), G18 (DPAPI-Pepper), G25 (RAM-Hygiene), G28 (Verschlüsselungs-Beweis, N11.9), G31 (RAM-auf-Platte-Lecks: BitLocker-Anzeige, `VirtualLock`, keine Dump-Dateien; A1, 2026-07-15), G32 (Tresor-Ort-Default + Cloud-Warnung; A2, 2026-07-15), G33 (Dev-Altdaten sicher entsorgen; A3, 2026-07-15), 🔴 G35 (eine gemeinsame `teardown(reason)`-Sequenz für alle Ausgänge, N11.11)** (G19 Single-Instance ✅ 2026-06-20 vorgezogen)
- [ ] Phase 9, Auslieferung + Tests + Build (portable `NoaToDo.exe`, PyInstaller/Nuitka, WebView2-Runtime, Erststart auf fremdem Rechner) **+ 🔒 G27 (Binary-Härtung + Frontend-Integritäts-Manifest, A5 2026-07-15), G34 (Release-Härtung: `NOATODO_DEBUG` wirkungslos, DevTools/Accelerator-Keys/Kontextmenü aus; Sofort-Teil `text_select=False` mit Termin 2026-07-20; A4/A6, 2026-07-15), G11 (Hash-gepinnter Build), G29-Buildprüfung (kein Debug-Modus, kein Logfile, N11.12.2)**
- [ ] UX-Nachtrag 2026-06-13 (Normen in den Verträgen; Protokoll: Anhang 1, Historie: Anhang 3): N2 Offline-Statuspille, N4 Lock-Screen-Passphrase-UX (8), N5 Panik nur per Maus, kein Hotkey (Entscheid 2026-07-13), N6 Entsperr-Fehlerbildschirm (8), N7 move_task/reorder_lists (Phase 7; clear_completed gestrichen), N8 Roadmap (D.3), N9 Fenster startet maximiert (N11.6), N10 verstärkter Lock + Off-Knopf + Killswitch (UI ✅ 2026-07-08, Sicherheits-Rest Phase 8), N11 Lücken-Klärung 2026-07-09 (verbindlich), N11.10 Sperre schaltet nicht mehr offline (2026-07-13, W1-Entscheid), N11.11 gemeinsame Sperr-/Beenden-Sequenz + Gate G35 (2026-07-13, S5-Entscheid), N11.12 Fehler-Hygiene + Fehlercode-Katalog + Logging-Politik + Gate G29 (2026-07-13, S6-Entscheid), N11.14 Triage des UX/UI-Audits (2026-07-13, S7-Entscheid; **die Triage-Tabelle ist der Status des Audits, nicht das Audit-Dokument**), N11.13 Onboarding-/Tresor-Bridge + dreiwertiger Boot-Zustand + Onboarding-Screens (2026-07-13, U1-Entscheid)

### 🔒 Sicherheits-Gates auf einen Blick (Details in B.9)

| Gate | Phase | Kurz |
|---|---|---|
| ✅ CSP gesetzt | erledigt | `index.html`, strenger als Minimum |
| ✅ `esc()` gehärtet | erledigt | maskiert jetzt auch `'` |
| 🔒 G6 | 8 | In-Memory-DB statt Temp-Arbeitskopie |
| 🔒 G7 | 8 | Hex-Raw-Key für `PRAGMA key` |
| 🔒 G8 | 8 | Argon2id feste Soll-Kosten (256 MiB, t=3, p=4, hash_len 32; N11.4.3) + Passphrase-Politik nach N11.3: **nur** Mindestlänge 12, kein Stärkemesser; `MemoryError` -> Code `memory`, nie Absturz/Falsch-Passwort |
| 🔴 G9 | 8 | **`DEV_AES_KEY` & jeden statischen Schlüssel-Fallback entfernen** (sonst null Verschlüsselung) |
| 🔒 G11 | 0 / laufend | Abhängigkeiten versions-pinnen (+ Hash-Checking, + Python 3.11.x, U25) |
| ✅ G12 | erledigt (2026-07-17, vorgezogen) | Externe WebView-Navigation verweigern (`NavigationStarting`-Waechter + `OPEN_EXTERNAL_LINKS_IN_BROWSER=False` in `main.py`) |
| 🔴 G13 | 8 | **Lock serverseitig durchsetzen, als Allowlist** (gesperrt erlaubt: `unlock`, `quit_app`, `killswitch`, `get_state` sowie die Onboarding-/Reset-Methoden `get_boot_state`, `choose_vault_dir`, `create_vault`, `reset_vault` (N11.13); alles andere liefert `locked`-Fehler, `get_state` nur `{"locked": true}`) |
| 🔒 G14 | teils erledigt (2026-06-20), Rest 8 | WebView2 ohne Datenspuren: fester Profilordner statt Privatmodus ✅, Altlasten-Wisch beim Start ✅; sicheres Wischen bei lock/panic/quit offen (Phase 8), **inkl. Fenster-X = gleicher Beenden-Pfad wie `quit_app()`**; Wisch immer in-process auf dem effektiven Pfad (Store-Python-Redirect, V8/N11.15.5), Phase-9-Erststart räumt alte Redirect-Pfade einmalig weg |
| 🔒 G15 | 8 | Argon2id-Master-Secret + HKDF-Domain-Separation; kein Verifikations-Hash, Prüfung via Poly1305-Tag |
| 🔒 G16 | 8 | `tasks.db.enc`-Header (Magic/Version/Params/Salt/Nonce; Params konkret N11.4.3), Header als AEAD-`associated_data` (V1), Param-Akzeptanzbereich vor Ableitung, frische Nonce, atomares Schreiben + `.bak`, `.tmp` vor der `.bak`-Rotation probeentschlüsselt + Plattenplatz-Prüfung vor dem Wrap (V1) |
| 🔒 G17 | 8 | Debounced Write-back der In-Memory-DB (ca. 3 s, Kappe spätestens alle 30 s bei Dauereingabe, U20; Crash kostet höchstens Sekunden) |
| 🔒 G18 | 8 | DPAPI-Pepper im Credential Manager als Zweitfaktor gegen Offline-Brute-Force (kein Recovery-Export, Tresor an den PC gebunden, N11.3). **Zusage nur konditioniert (B.10.4):** wirkt gegen den, der **nur die Tresordatei** hat; bei gestohlener, **unverschlüsselter Platte** hängt der Pepper an der Stärke des Windows-Passworts. Nie "gar nicht raten" ohne diese Bedingung schreiben |
| ✅ G19 | erledigt (2026-06-20, vorgezogen); Rest V3 offen | Single-Instance-Mutex, heute `Local\NoaToDoSingleton` (zweite Instanz zeigt Hinweis und beendet sich); Rest-Pflicht V3 (2026-07-15): Namensraum auf `Global\NoaToDo-<User-SID>` umstellen, sonst startet derselbe Benutzer per RDP/Benutzerumschaltung eine zweite Instanz |
| ✅ G20 | erledigt (2026-07-17) | Regel-4-Validierung auch lokal + `reorder`-Typprüfung + `set_setting`-Key-Whitelist + Wert-/Typ-Prüfung je Key (Enums, Akzent-Hex-Whitelist, `sidebarWidth` beim Schreiben geklemmt, `autoLock`-Stufen, `edit_task.fields` typgeprüft; deklaratives Schema am Decorator, V5) |
| ✅ G21 | erledigt (2026-07-17) | Export-Härtung: reservierte Windows-Namen, verbotene Windows-Zeichen + `..` durch `_`, Kappung auf ca. 120 Zeichen (V6), Newline-Ersetzung, echter Save-Dialog; gilt für `export_list` und `export_all` |
| ✅ G22 | erledigt (2026-07-17) | Ehrliche Sicherheits-Behauptungen in der ganzen UI: `get_status()`/Status-Modal (2026-07-16) + Panik-Endschirm/Wipe-Fortschritt (2026-07-17, "Workspace cleared"); der Endschirm bleibt dauerhaft ehrlich, kein „Wipe"-Aussenschirm ab Phase 8 (N11.17, B.10.5) |
| ✅ G23 | erledigt (2026-06-10) | Einzel-Task-Kopie im Backend: keine Win+V-History, kein Cloud-Clipboard, Auto-Clear 60 s, `Strg+C` entfernt |
| 🔒 G25 | 8 | RAM-Schlüssel-Hygiene: `bytearray` + Nullen, Passphrase sofort verwerfen, nie loggen |
| ❌ G26 | verworfen + entfernt (2026-06-20) | Screenshot-Schutz `WDA_EXCLUDEFROMCAPTURE` blendete Aufnahmen schwarz aus, verhindert aber auf manchen GPUs das Rendern (Fenster weiss / reagiert nicht). Mehrfach ein-/ausgebaut, endgueltig entfernt. Nicht wieder einbauen ohne Render-Verifikation + Affinity-Rollback |
| 🔒 G27 | 9 | Binary-Härtung: `.exe` signieren, kein Quelltext mitliefern (Nuitka), optional Obfuskation. Sicherheit beruht nie auf Code-Geheimhaltung (Kerckhoffs), nur auf Passphrase + Pepper + Verschlüsselung. **Ergänzung Frontend-Integrität (A5, 2026-07-15):** Assets ins signierte Binary einbetten oder Start-Hash-Prüfung gegen ein eingebettetes Manifest; Abweichung = Startabbruch mit klarer Meldung |
| 🔒 G28 | 8 | Verschlüsselungs-Beweis (N11.9): Öffnen des inneren Images ohne `aes_key` muss nachweislich fehlschlagen (kein SQLite-Klartext-Header, kein Task-Text im Roh-Byte-Dump); scheitert das für den `:memory:`-Weg, gilt verbindlich der Fallback mit SQLCipher-verschlüsselter Arbeitsdatei; kein Auslieferungsbuild ohne bestandenen Beweis; Beweis automatisiert als pytest-Test (V12) |
| ✅ G29 | erledigt (2026-07-17); Buildprüfung Rest 9 | Fehler-Hygiene (N11.12, Plananalyse S6): generische Fehler ans Frontend (Code + statischer Text aus dem **Fehlercode-Katalog in B.2**, nie `str(exc)`, nie Pfade/Benutzername/Tracebacks/Aufgabentext), Details nur im redigierten In-Memory-Ringpuffer (Status-Modal, Leerung im `teardown`), im Release **kein** persistentes Logfile |
| 🔒 G31 | 8 | RAM-auf-Platte-Lecks (A1, 2026-07-15): BitLocker-Empfehlung + realer BitLocker-Status im Status-Modal (sonst ehrlich "unbekannt"), `VirtualLock` für alle Schlüssel-Puffer (Best-Effort; hilft nicht gegen `hiberfil.sys`, nur BitLocker deckt das), keine Traceback-/Dump-Dateien (deckt sich mit G29) |
| 🔒 G32 | 8 | Tresor-Ort (A2, 2026-07-15): Onboarding-Default `%LOCALAPPDATA%\NoaToDo`; deutliche Warnung bei erkannten Cloud-Sync-Pfaden (OneDrive-Env-Vars, Dropbox-`info.json`, Pfad-Heuristik) inkl. "Killswitch/Reset löschen Cloud-Versionen nicht"; Warnung, keine Sperre |
| 🔒 G33 | 8 | Dev-Altdaten (A3, 2026-07-15): beim ersten `create_vault()` alte `tasks.db` samt `-journal`/`-wal`/`-shm` über den Secure-Delete-Pfad entsorgen (nie blankes `os.remove`); Einmal-Hinweis mit der ehrlichen SSD-Restgrenze (Wear-Leveling) |
| 🔒 G34 | 9; Teil SOFORT | Release-Härtung (A4/A6, 2026-07-15): `NOATODO_DEBUG` im Release wirkungslos (Build-Konstante), DevTools aus (`AreDevToolsEnabled=false`), `AreBrowserAcceleratorKeysEnabled=false` (kein `Strg+P`-Klartext-PDF an G21 vorbei), Standard-Kontextmenü aus; **`text_select=False` explizit setzen + Regressionstest: SOFORT, Termin 2026-07-20**; Eingabefeld-Copy bleibt offener Kanal (B.10.3 Punkt 8) |
| 🔴 G35 | 8 | **Eine gemeinsame, nummerierte Sperr-/Beenden-Sequenz `teardown(reason)` für alle neun Ausgänge** (Lock, `Ctrl+L`, Auto-Sperre, Off-Knopf, Panik-Finish, Killswitch, Reset, Fenster-X, `atexit`), Reihenfolge nach N11.11.2: Idempotenz, native Dialoge auflösen, einfrieren, G17-Debounce synchron flushen, Clipboard leeren, DB schließen, Schlüssel nullen, erst dann löschen (Killswitch/Reset), `PROFILE_DIR` wischen, Funk-Restore ganz zuletzt, Mutex freigeben. Kein zweiter, handgeschriebener Beenden-Pfad |
| 🔒 G30 | Doku, vor 8 | **Bedrohungsmodell B.10** (2026-07-13, Plananalyse S4): Angreiferklassen K1 bis K6, ausdrückliche Nicht-Ziele (**Malware-als-Nutzer K4 ist unverteidigbar**, keine Schein-Gegenmassnahmen, G26-Lektion), Voraussetzungen (BitLocker/Geräteverschlüsselung empfohlen, starkes Windows-Passwort), G18-Zusage konditioniert, Panik-Endschirm-Falschaussage als bewusste Abwägung dokumentiert. Neue Gates ohne Angreiferklasse (B.10.6) werden nicht gebaut |

**Hinweise (kein Gate):** Export schreibt unverschlüsselte Dateien (by design, der
Nutzer exportiert bewusst Klartext); `main.py` `emit()` muss
`json.dumps(..., ensure_ascii=True)` behalten (U+2028/U+2029-Schutz im
`evaluate_js`-Kanal). Das Clipboard-Thema ist seit dem Nachtrag ein Gate (G23).
