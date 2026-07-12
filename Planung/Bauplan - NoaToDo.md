# Bauplan: NoaToDo (lokale, sichere To-Do-App)

> **Zweck dieses Dokuments.** Es ist die vollständige, schrittweise Bauanleitung
> für NoaToDo. Eine KI (oder ein Mensch) soll es von oben nach unten abarbeiten
> können und am Ende eine lauffähige App haben, die **exakt** wie das Design­konzept
> (`NoaToDo UI Konzept.html`) aussieht und auf dem in `technische Grundlage.txt`
> beschriebenen Fundament läuft.
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

---

## TEIL A: Das Gesamtbild

### A.1 Was die App ist

NoaToDo ist eine **local-first Desktop-App** für Windows, optisch an Microsoft To Do
angelehnt, aber mit zwei klaren Eigenschaften:

1. **Komplett lokal.** Alle selbst erstellten Aufgaben, alle Bearbeitungen und die
   gesamte Datenbank liegen auf dem eigenen Rechner. Es gibt keinen eigenen Server.
2. **Sicherheits-/Privatsphäre-Fokus.** Optionale App-Sperre (Lock-Screen), Panik-
   Sperre („Emergency"), verschlüsselte Datenbank, Tokens im Windows Credential
   Manager. Die ganze Optik trägt dieses Motiv: „warmes Terminal / lokaler Tresor".

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
                                     data/tasks.db  (SQLite, lokal, optional verschlüsselt)
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

---

## TEIL B: Die Verträge (für alle Bausteine verbindlich)

### B.1 Datenmodell (SQLite)

Drei Tabellen. IDs sind Strings (lokale IDs `l…`/`t…` per `uuid`/Zeitstempel).

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

-- App-Einstellungen als simples Key/Value (Theme, Accent, Dichte, Toolbar, Sidebar …)
CREATE TABLE settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

**Abgeleitete Sichten, die das Frontend erwartet** (das Backend liefert sie fertig):
- eine Liste hat `open` = Aufgaben mit `done=0` und `done` = Aufgaben mit `done=1`,
  jeweils nach `position` sortiert.

### B.2 Bridge-API (`pywebview.api.*`): der Vertrag zwischen vorne und hinten

Das ist die **vollständige Methodenliste**, die `backend/api.py` bereitstellt und die
`frontend/app.js` aufruft. Jede gibt JSON-serialisierbare Werte zurück (Promise im JS).

| Methode | Argumente | Rückgabe | Zweck |
|---|---|---|---|
| `get_state()` | (keine) | `{ lists:[…], settings:{…}, online:bool, locked:bool }` | Initialer Gesamtzustand beim App-Start |
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
| `reorder_lists(ordered_ids)` | `[str]` | `{ ok:true }` | Reihenfolge der Listen in der Sidebar speichern (ab Phase 7, N11.2) |
| `move_task(id, target_list_id)` | `str,str` | `{ ...task }` | Aufgabe in eine andere Liste verschieben (ans Ende der Ziel-Liste; ab Phase 7, N11.2) |
| `export_list(id, format)` | `str,'md'\|'txt'` | `{ filename, content }` | Eine Liste exportieren (nur noch md/txt, N11.1.5) |
| `export_all(format)` | `'md'\|'txt'` | `{ filename, content }` | Alle Listen mit allen Aufgaben in eine Datei exportieren (Schritt "alle Listen" des zweistufigen Exports, N11.2) |
| `copy_task(id)` | `str` | `{ ok, clears_in }` | EINE ausgewählte Aufgabe gehärtet ins Clipboard (Backend-seitig, keine Win+V-History, kein Cloud-Clipboard, Auto-Clear nach 60 s; ersetzt das frühere `copy_list`, ganze Listen kopiert man bewusst nicht mehr, dafür gibt es den Export) |
| `set_setting(key, value)` | `str,*` | `{ ok:true }` | Eine Einstellung speichern |
| `get_status()` | (keine) | `{ db, encryption, runtime }` | Daten für das „App status"-Modal |
| `set_online(flag)` | `bool` | `{ online:bool }` | Schaltet den **echten** Windows-Flugmodus um (offline = alle Funkgeräte aus, WLAN/Bluetooth), spiegelt externe Änderungen und stellt beim Beenden den Ausgangszustand als letzten Schritt wieder her (N11.5) |
| `lock()` | (keine) | `{ locked:true }` | App sperren; seit 2026-07-08 verstärkt: erst Raum-Bereinigung wie bei Panik (Ansicht leeren, offline), dann Lock-Screen, nichts wird gelöscht (siehe N10) |
| `unlock(passphrase)` | `str` | `{ ok:bool }` | Entsperren; danach wird der Zustand frisch per `get_state()` geladen (der Raum war geleert) |
| `panic()` | (keine) | `{ locked:true }` | Emergency: Raum bereinigen + offline; der Flow endet im Endschirm mit Finish/Killswitch, zurück in die App führt kein Weg (N10) |
| `quit_app()` | (keine) | `{ ok:true }` | App sauber beenden (Off-Knopf des Lock-Screens, „Finish" im Panik-Endschirm, Abschluss des Killswitch); Phase 8: auf diesem Pfad vorher Spuren sicher wischen (G14/G25) |
| `killswitch()` | (keine) | `{ ok:true }` | Unwiderruflich alle Nutzerdaten aus der Datenbank löschen (nur vom Panik-Endschirm aus erreichbar, N10); das Programm selbst bleibt installiert |

**Ereignisse Backend → Frontend** (PyWebView kann JS auswärts aufrufen, z.B.
`window.evaluate_js` oder ein Event-Bus): `on_locked()`.
Das Frontend registriert dafür globale Funktionen wie `window.noa.onLocked`.

**Fehlerkonvention:** Jede Methode kann statt des Erfolgsobjekts
`{ error: "code", message: "…" }` liefern. Das Frontend zeigt das als Toast.

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

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER (Höhe 56)                                                          │
│ [☰] [🛡 NoaToDo] [● LOCAL·ENCRYPTED]            … [🔔3] [NA]               │
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
- Rechts: Avatar „NA" (öffnet **Profil-Menü**).

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

**Rechte Toolbar** (`renderToolbar`), vertikale Leiste, zwei Modi über
`data-toolbar`: `flush` (bündig an der Kante) oder `floating` (schwebende, gerundete
Karte, Standard). Buttons mit Tooltip + Hotkey, in Gruppen durch Trenner:
1. **Focus mode** (⤢, `F`), blendet Sidebar+Toolbar aus, nur eine „Exit focus"-X bleibt.
2. **Accent color** (🎨), öffnet Swatch-Popover mit den 6 Akzenten.
3. **Export** (⬆, `Ctrl+E`), zweistufig: erst Umfang (aktuelle Liste / alle Listen),
   dann Format (md / txt), siehe N11.2.
4. **Shortcuts** (?), öffnet das Tastenkürzel-Modal.
   (Trenner)
5. **Lock / Unlock** (🔒, `Ctrl+L`).
6. **Emergency** (⚠, `Ctrl+Shift+!`, rot), öffnet das Panik-Modal.
   (Trenner)
7. **Copy task** (⧉): kopiert die per Klick **ausgewählte** Aufgabe (gehärtet,
   siehe G23); ohne Auswahl nur ein Hinweis-Toast. Kein Tastenkürzel.
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
  und Verbindlichkeit: Nachtrag N10.
- **StatusModal**, Diagnose-Zeilen: Local database (Größe), Encryption (AES-256 +
  ChaCha20 · Argon2id), Network (local only · online/offline), WebView2 runtime,
  jeweils mit grünem/blassem Status-Tag. Daten kommen aus `get_status()`.
- **RenameModal**, Eingabefeld (vorbelegt, fokussiert+selektiert), Enter/Save.
- **DeleteModal**, Bestätigung „Delete „Name"?".
- **ShortcutsModal**, Raster aller Tastenkürzel (siehe B.5).
- **LockScreen**, Vollbild über allem: Akzent-Ring mit Schloss, „NoaToDo is locked",
  Passwort-Pille (Phase 8: echte Passphrase-Prüfung, siehe N4). Oben rechts ein
  klassischer **Off-Knopf** (Power-Symbol): beendet die App sofort ohne Passphrase
  über `quit_app()`, vernichtet dabei Spuren, löscht aber nie Nutzer- oder App-Daten
  (Nachtrag N10).
- **Toasts**, kurze Bestätigungen unten mittig (z.B. „List created", „Exported list").

### B.5 Tastenkürzel (verbindlich)

| Aktion | Taste |
|---|---|
| Neue Aufgabe | `↵` (im New-task-Feld) |
| Neue Liste | `N` |
| Sidebar umschalten | `Ctrl + B` |
| Focus-Modus | `F` |
| App sperren | `Ctrl + L` |
| Notfall-Sperre | `Ctrl + Shift + !` |
| Liste exportieren | `Ctrl + E` |
| Theme umschalten | `Ctrl + J` |
| Online/Offline | `G` |
| Tastenkürzel-Hilfe | `?` |
| Alles schließen | `Esc` |

Beim Tippen in Eingabefeldern dürfen die Buchstaben-Hotkeys nicht feuern (außer Esc).

### B.6 Einstellungen (persistiert in `settings`-Tabelle)

`accent` (Hex), `theme` (`auto`|`light`|`dark`, Default `auto`, ersetzt das frühere
`dark`, siehe N11.6), `density` (`comfortable`|`compact`), `sidebar` (`open`|`closed`),
`sound` (bool, Erledigt-Ton, Default `true`, N11.6), `autoLock` (Minuten bis zur
Auto-Sperre, `0` = nie, Default `15`, N11.4). Werden beim Start aus `get_state()`
gelesen und auf das `.app`-Element als `data-*`/`--accent` gesetzt; Änderungen sofort
via `set_setting` zurückschreiben. Der frühere Key `toolbar` entfällt (die Rail ist
immer `floating`). Bei `theme=auto` folgt die App live dem Windows-Hell/Dunkel-Zustand
(ereignisbasiert), `Ctrl+J` setzt einen manuellen Override, bis wieder `auto` gewählt
wird.

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
Statt des normalen `sqlite3` wird **SQLCipher** verwendet (Paket `sqlcipher3-binary`):
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
- **Beim Entsperren:** ChaCha20-Schicht entfernen → die SQLCipher-Datei in eine
  geschützte Arbeitskopie schreiben (bevorzugt RAM-Disk/`%TEMP%` mit restriktiven
  Rechten), dann mit `aes_key` öffnen.
- **Beim Sperren/Schließen/Panic:** Arbeitskopie wieder als `tasks.db.enc` mit ChaCha20
  einpacken, **dann die unverschlüsselte SQLCipher-Arbeitskopie sicher löschen**
  (überschreiben/`os.remove`), Schlüssel aus dem Speicher werfen.
- Die ChaCha20-Schicht nutzt **Poly1305** als Authentifizierung (AEAD): manipulierte
  Dateien werden beim Entschlüsseln erkannt, nicht nur stillschweigend falsch entpackt.

> **[Ueberholt durch N11.9: am Ruhezustand schuetzen BEIDE Schichten (ChaCha20 aussen, AES innen); N11.9 gilt vorrangig.]**
> Hinweis zur Ehrlichkeit: *Während die App entsperrt läuft*, ist „live" nur die
> AES-256-Schicht aktiv (die App muss die Daten ja lesen). Die zweite Schicht schützt
> den **Ruhezustand**, das ist der Zustand, der bei Diebstahl/Backup zählt. Ein echter
> gleichzeitiger Per-Page-Doppel-Cipher bräuchte einen eigenen Cipher-Treiber und wäre
> Over-Engineering; *Alternative für Puristen* siehe Ende des Abschnitts.

**Punkt 3, die Schlüssel kommen aus deiner Passphrase und liegen nie auf der Platte.**
- Beim ersten Start legst du eine **Passphrase** fest.
- Daraus werden mit **Argon2id** (hohe Kosten: viel RAM + Zeit pro Versuch) und einem
  zufällig erzeugten, gespeicherten **Salt** die beiden Schlüssel abgeleitet, `aes_key`
  (Schicht 1) und `chacha_key` (Schicht 2) als getrennte Teilstücke aus dem KDF-Output.
- Gespeichert wird **nur** der Argon2-**Hash** der Passphrase (zum Prüfen beim Entsperren)
  und das Salt, **nie** die Passphrase oder die Schlüssel selbst.
- `aes_key`/`chacha_key` existieren nur **im Arbeitsspeicher**, solange die App entsperrt
  ist. Beim Sperren/Panic werden sie verworfen.

> **Präzisierung (verbindlich, Nachtrag 2026-06-10):** Die Gates **G15** und **G18**
> (B.9 Nachtrag) ersetzen zwei Details dieses Abschnitts: (1) Es wird **kein**
> Argon2-Hash der Passphrase gespeichert; die Prüfung beim Entsperren läuft über den
> Poly1305-Tag der ChaCha20-Entschlüsselung. (2) Die beiden Schlüssel entstehen nicht
> als "Teilstücke des KDF-Outputs", sondern per HKDF-SHA256 mit getrennten
> `info`-Labels aus einem Argon2id-Master-Secret. (3) Zusätzlich zur Passphrase geht
> ein DPAPI-gebundener Pepper aus dem Windows Credential Manager in die Ableitung ein.
> Gespeichert auf der Platte werden nur: Salt, Argon2-Parameter, Nonce (im
> `tasks.db.enc`-Header, siehe G16).

**Punkt 4, DPAPI-Pepper getrennt von der DB: keyring.**
Der zusätzliche 32-Byte-Pepper (Zweitfaktor der Schlüsselableitung, siehe G18) liegt
nicht in der DB, sondern im **Windows Credential Manager** (über `keyring`), ans
Benutzerkonto gebunden.

**Punkt 5, Ablauf zusammengefasst:**
```
App-Start → Lock-Screen → Passphrase eingeben
   → Argon2-Hash prüfen → KDF(Passphrase, Salt) → aes_key + chacha_key
   → tasks.db.enc per ChaCha20 entpacken → Arbeitskopie
   → SQLCipher(Arbeitskopie) mit aes_key öffnen → entsperrt, UI lädt
Sperren / Schließen / Panic
   → Arbeitskopie per ChaCha20 → tasks.db.enc  → Arbeitskopie sicher löschen
   → aes_key, chacha_key, Klartext-Cache aus dem Speicher werfen
```

**Punkt 6, was das schützt (und was nicht):**
- *Geschützt:* Wer die Datei in die Finger bekommt (verlorener Laptop, Backup,
  Cloud-Ordner), sieht ohne Passphrase nur doppelt verschlüsselten Zufallsmüll.
- *Nicht magisch geschützt:* Während die App **entsperrt läuft**, sind die Daten im
  Speicher nutzbar, wie bei jeder App. Dagegen helfen die schnelle Sperre, die
  Panik-Sperre und Auto-Sperre bei Inaktivität.

**Alternative für Puristen (optional, nicht Default):** statt Arbeitskopie auf Platte die
ganze (kleine) DB beim Entsperren in eine **In-Memory-SQLite** (`:memory:`) laden und im
Ruhezustand nur als ein einziges, doppelt verschlüsseltes Blob ablegen. Dann existiert
**nie** eine entschlüsselte Datei auf der Platte, Preis: die ganze DB wird bei jeder
Persistierung am Stück geschrieben (für ein paar hundert Aufgaben unkritisch, aber ohne
seitenweise Crash-Transaktionen auf der Platte).

> Konkrete Bibliotheken in Phase 0 (`requirements.txt`); Umsetzung in Phase 1 (Schicht 1
> beim DB-Öffnen) und Phase 8 (Argon2, Schicht 2 / Wrap-Unwrap, Lock, Panic).

> **Beide Schichten sind Pflicht.** AES-256 **und** ChaCha20-Poly1305 werden immer
> gebaut, es gibt keinen Modus ohne die zweite Schicht. Die „Alternative für Puristen"
> oben betrifft nur das *Wo* der entsperrten Arbeitskopie (Platte vs. Arbeitsspeicher),
> **nicht** ob die ChaCha20-Schicht existiert.

### B.8 Sperr-Politik: wann die Passphrase verlangt wird

Die App ist **entweder entsperrt** (Schlüssel im Speicher, UI nutzbar) **oder gesperrt**
(Lock-Screen, DB zu, Schlüssel verworfen). Genau diese Ereignisse lösen eine **Sperre**
aus, sodass danach die **Passphrase neu eingegeben** werden muss:

| Ereignis | Verhalten |
|---|---|
| Klick auf **Lock**-Button (oder `Ctrl+L`) | sofort sperren, davor Raum-Bereinigung wie bei Panik (Ansicht leeren, In-Memory-Zustand verwerfen, offline schalten); es wird **nichts gelöscht** |
| **Emergency/Panic** (`Ctrl+Shift+!`) | Raum-Bereinigung + offline; endet im Panik-Endschirm (Finish/Killswitch, N10), nicht mehr im Lock-Screen |
| **Windows-Sperre** (Win+L) bzw. Sitzung gesperrt | **N11.8.4 gilt vorrangig: Win+L loest KEINE App-Sperre aus (tut nichts). Nur die Auto-Sperre nach Inaktivitaet sperrt, garantiert auch bei gesperrtem PC.** |
| **App-Neustart** (Prozess war beendet) | startet immer im Lock-Screen |
| **Auto-Sperre nach Inaktivität** *(empfohlen, Timeout einstellbar, Default z. B. 15 min)* | sperren |

**Ausdrücklich KEINE Sperre** bei:
- **Minimieren** und wieder Öffnen des App-Fensters,
- Fokus-Wechsel zu einer anderen App (App nur im Hintergrund),
- Verschieben/Größe ändern des Fensters.

> Kernregel: Eine Sperre passiert nur bei **explizitem Sperren**, bei **Windows-
> Sitzungssperre** und bei **echtem Prozess-Neustart**. Reines Fenster-Minimieren ist
> *kein* Sicherheitsereignis und lässt die App entsperrt.

**Verschärfung (2026-07-08, verbindlich, Details in Nachtrag N10):** Sperren ist jetzt
„Panik light". Jede Sperre bereinigt **zuerst den Raum** (Ansicht leeren, In-Memory-
Listen und Auswahl verwerfen, Menüs/Modals schließen, offline schalten), erst dann
erscheint der Lock-Screen mit der Passwort-Pille. Dabei werden **nie** Daten gelöscht;
nach dem Entsperren lädt das Frontend den Zustand frisch per `get_state()`. Der
Lock-Screen trägt oben rechts einen **Off-Knopf**, der die App ohne Passphrase sauber
beendet (`quit_app()`); in Phase 8 wischt genau dieser Pfad zusätzlich alle lokalen
Spuren (G14/G25). Panik führt nicht mehr in den Lock-Screen zurück, sondern endet im
Endschirm mit Finish/Killswitch (N10).

**[Gestrichen durch N11.8.4: Win+L loest KEINE Sperre aus, dieser WTS-Hook wird nicht implementiert. Der folgende Absatz ist nur noch historisch.]**

**Technische Umsetzung der Windows-Sperre-Erkennung (Phase 8):** Beim Sitzungswechsel
horchen, über `WTSRegisterSessionNotification` auf das App-Fensterhandle und das
`WM_WTSSESSION_CHANGE`-Ereignis (via `ctypes` oder `pywin32`/`win32ts`). Bei
`WTS_SESSION_LOCK` (Windows wurde gesperrt) → `lock()` aufrufen. Damit ist die App beim
Zurückkommen aus der Windows-Anmeldung garantiert gesperrt.

### B.9 Eingabe-Sicherheit: Schutz vor bösartigem Inhalt (verbindlich)

> ## ⚠️ SICHERHEITS-HÄRTUNG, STAND & OFFENE PFLICHT-GATES
>
> Aus dem Security-Review (2026-06-08) ergab sich eine klare Trennung in
> „sofort erledigt" und „muss in der jeweiligen Phase erledigt werden".
> **Diese Liste ist verbindlich. Die offenen Punkte sind Gates: Die jeweilige
> Phase gilt erst als fertig, wenn ihr Sicherheitspunkt umgesetzt ist.**
>
> **✅ Bereits erledigt (im Code):**
> - **CSP gesetzt** in `frontend/index.html` (Regel 2), strenger als das Minimum
>   (zusätzlich `connect-src 'self'`, `object-src/base-uri/form-action/frame-ancestors 'none'`).
> - **`esc()` gehärtet** in `frontend/app.js`, maskiert jetzt auch `'` (einfach-
>   gequotete Attribute), nicht nur `& < > "`.
>
> **🔒 OFFENE PFLICHT-GATES (NICHT vergessen, pro Phase abhaken):**
>
> | Gate | Phase | Punkt |
> |---|---|---|
> | **G6** | **8** | **In-Memory-DB** (`:memory:`) statt entschlüsselter Temp-Arbeitskopie, siehe B.7 „Alternative für Puristen". Eliminiert Temp-Datei-Forensik (Secure-Delete auf SSD ist unzuverlässig). |
> | **G7** | **8** | **Roher Hex-Schlüssel** für `PRAGMA key = "x'<64 hex>'"` statt String-Interpolation (`db.py`), damit SQLCipher kein eigenes PBKDF2 über den schon abgeleiteten Key legt. |
> | **G8** | **8** | **Starke Argon2id-Parameter** (Memory ≥ 256-512 MB, time_cost ≥ 3) **und erzwungene Passphrase-Stärke**, die Passphrase ist der einzige reale Schwachpunkt (Offline-Brute-Force). |
> | **🔴 G9** | **8** | **`DEV_AES_KEY` & jeden statischen Schlüssel-Default ersatzlos entfernen.** Es darf **keinen** Code-Pfad geben, der die DB ohne passphrase-abgeleiteten Schlüssel öffnet. Sonst öffnet die „verschlüsselte" DB mit einem öffentlich im Quellcode stehenden String → **effektiv null Verschlüsselung**, während der Status fälschlich „AES-256 + ChaCha20" meldet. Wichtigstes Gate der Phase 8. |
> | **G11** | **0 / laufend** | **Abhängigkeiten pinnen.** `requirements.txt` listet alles ohne Version. Versionen festnageln, idealerweise mit `pip` Hash-Checking, eine getauschte Lib = Totalkompromittierung der Tresor-App. |
> | **G12** | **3/8** | **WebView-Navigation abriegeln.** Navigations-/New-Window-Events in PyWebView abfangen und jede **externe** Navigation (`window.location`/`window.open` zu externem `http`) verweigern. Die App ist rein lokal und navigiert nie woandershin. |
>
> **Zwei Kleinigkeiten (Hinweis, kein Gate):**
> - **Export/Clipboard:** `export_list` schreibt **unverschlüsselte** Dateien (by
>   design, der Nutzer exportiert bewusst Klartext). Das Kopieren ist seit dem
>   Nachtrag gehärtet und auf eine einzelne Aufgabe begrenzt, siehe G23.
> - **`main.py` `emit()`:** `json.dumps(payload)` muss `ensure_ascii=True` (Default)
>   behalten, sonst können U+2028/U+2029 in Event-Daten den `evaluate_js`-Aufruf
>   brechen.
>
> Diese Gates werden weiter unten in Phase 8 **nochmals einzeln** wiederholt. Das
> ist Absicht, sie dürfen nicht übersehen werden.

> ## 🔒 NACHTRAG: Gates G13 bis G25 (Code-Audit + Testlauf vom 2026-06-10)
>
> Ein vollständiges Code-Audit (Code-Review aller Module plus 23 automatisierte
> Checks gegen die echte Bridge-API auf einer Wegwerf-DB) hat weitere
> Pflichtpunkte ergeben. **Alle folgenden Gates sind verbindlich und vom Nutzer
> bestätigt. KEINER dieser Punkte ist optional, jeder MUSS in der genannten
> Phase umgesetzt werden.** Sie gelten zusätzlich zu den übrigen Gates und werden
> in den Phasen 7 und 9 nochmals einzeln wiederholt.
>
> | Gate | Phase | Punkt |
> |---|---|---|
> | **🔴 G13** | **8** | **Serverseitige Lock-Durchsetzung.** Die Sperre existiert heute nur als Frontend-Overlay: Im Audit wurde nachgewiesen, dass nach `lock()` Aufrufe wie `add_task()` und `get_state()` weiterhin funktionieren und alle Daten liefern (ein einziger JS-Aufruf umgeht den Lock-Screen). Pflicht: Ein zentraler Check im `bridge`-Decorator prüft `self.locked`; ist die App gesperrt, gibt **jede** Methode ausser `unlock(passphrase)` sofort `{"error": "locked"}` zurück, ohne die DB zu berühren. `get_state()` liefert im gesperrten Zustand nur `{"locked": true}` ohne Listen/Settings. |
> | **G14** | **3 (sofort vorsehen) / 8 (hart)** | **Keine WebView2-Datenspuren auf der Platte.** WebView2 legt einen User-Data-Ordner an (Cache, localStorage, GPU-Cache); dort können gerenderte Task-Texte an beiden Verschlüsselungsschichten vorbei landen. Pflicht: `webview.start(..., private_mode=True)` **explizit** setzen (nicht auf den Default verlassen) und verifizieren, dass die Runtime wirklich InPrivate läuft. Legt die Runtime trotzdem einen User-Data-Ordner an: Pfad explizit nach `data/webview2/` legen und beim Sperren/Panic/Beenden löschen. Das Frontend darf localStorage/sessionStorage/IndexedDB **nie** für Aufgabendaten verwenden. |
> | **G15** | **8** | **Schlüsselableitung mit Domain-Separation, KEIN gespeicherter Verifikations-Hash.** Argon2id erzeugt aus Passphrase + Salt **ein** 32-Byte-Master-Secret; daraus per HKDF-SHA256 mit getrennten `info`-Labels (`b"noatodo/aes-v1"`, `b"noatodo/chacha-v1"`) `aes_key` und `chacha_key` ableiten. Es wird **kein** Argon2-Hash der Passphrase gespeichert: Die Prüfung beim Entsperren ist der Erfolg oder Misserfolg der ChaCha20-Poly1305-Entschlüsselung (der Poly1305-Tag verifiziert die Passphrase implizit; falsche Passphrase = AEAD-Exception = Meldung "Passphrase falsch"). So liegt kein zusätzliches Orakel-Material für Offline-Angreifer auf der Platte. Ersetzt die ältere Formulierung in B.7 ("Argon2-Hash zum Prüfen speichern", "Teilstücke des KDF-Outputs"). |
> | **G16** | **8** | **Dateiformat von `tasks.db.enc` + atomares Schreiben.** Header: Magic `NOA1` (4 Byte), Formatversion (1 Byte), Argon2id-Parameter `memory_cost`/`time_cost`/`parallelism` (je u32 little-endian), Salt (16 Byte), Nonce (12 Byte); danach der ChaCha20-Poly1305-Ciphertext. Bei **jedem** Verschlüsseln eine frische Nonce aus `os.urandom(12)`; eine wiederverwendete Nonce bricht die AEAD-Sicherheit vollständig. Schreiben **immer** atomar: erst `tasks.db.enc.tmp` schreiben, `flush()` + `os.fsync()`, bestehende Datei nach `tasks.db.enc.bak` rotieren (genau eine Generation behalten), dann `os.replace()`. Ein Absturz mitten im Sperren darf nie die einzige Kopie der Daten zerstören. |
> | **G17** | **8** | **Write-back-Politik für die In-Memory-DB** (Ergänzung zu G6). Nach jeder mutierenden Bridge-Operation wird die In-Memory-DB debounced persistiert (z.B. 3 s nach der letzten Änderung; zusätzlich **sofort** bei Lock/Panic/Quit), als neues `tasks.db.enc` nach dem Verfahren aus G16. Ein Crash kostet damit höchstens die letzten Sekunden, nie den Tagesstand. |
> | **G18** | **8** | **DPAPI-Pepper gegen Offline-Brute-Force (Pflicht).** Beim Einrichten der Passphrase wird zusätzlich ein zufälliger 32-Byte-Pepper erzeugt und über `keyring` im Windows Credential Manager (DPAPI, ans Windows-Konto gebunden) abgelegt. Der Pepper fliesst zusätzlich zur Passphrase in die Ableitung ein (Argon2id-`secret`-Parameter). Wirkung: Wer nur die Datei `tasks.db.enc` erbeutet (ausgebaute SSD, Datei kopiert), kann offline **gar nicht** raten, ihm fehlt der Pepper aus dem Windows-Konto. **Kein Recovery-Export (N11.3, überschreibt die frühere Pflicht):** der Tresor ist bewusst an dieses Windows-Konto/diesen PC gebunden; geht das Windows-Profil verloren, ist die DB auch mit korrekter Passphrase nicht mehr zu öffnen. Der Einrichtungs-Flow enthält daher keinen Recovery-Schritt; der einzige Ausweg bei Verlust ist der Reset (Datenverlust, N11.3). |
> | **G19** | **8 (Umsetzung darf vorgezogen werden)** | **Single-Instance-Schutz.** Beim Start einen benannten Windows-Mutex belegen (`ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\NoaToDoSingleton")`, danach `GetLastError() == ERROR_ALREADY_EXISTS (183)` prüfen). Läuft schon eine Instanz: Hinweis zeigen und den zweiten Prozess sofort beenden. Zwei Instanzen würden sich `tasks.db.enc` bzw. die Arbeitskopie gegenseitig überschreiben (Korruption/Datenverlust). |
> | **G20** | **7** | **Regel-4-Validierung auch für LOKALE Eingaben + Typ-/Key-Prüfung an der Bridge.** Audit-Befunde: ein 1-MB-Tasktext und Steuerzeichen wie U+0000 werden heute anstandslos gespeichert; `reorder(list_id, "string")` iteriert den String zeichenweise und liefert `{"ok": true}`; `set_setting` akzeptiert beliebige Keys. Pflicht in `api.py`: (a) `add_task`/`edit_task`: Text max. 4096 Zeichen (kein `meta` mehr, N11.1.3); `add_list`/`rename_list`: Name max. 256; Überlänge abschneiden; Steuerzeichen U+0000-U+001F (ausser `\n` und `\t`) vor dem Schreiben strippen. (b) `reorder`/`reorder_lists` lehnen ab, wenn `ordered_ids` keine Liste von Strings ist; `move_task` validiert die IDs. (c) `set_setting` akzeptiert nur Keys aus einer Whitelist (`accent`, `theme`, `density`, `sidebar`, `railPinned`, `sidebarWidth`, `sound`, `autoLock` plus künftig dort dokumentierte, N11.7), sonst `{"error": "invalid"}`. |
> | **G21** | **7** | **Export-Härtung.** Audit-Befunde: eine Liste namens `CON` exportiert als `CON.md` (reservierter Windows-Gerätename), und Zeilenumbrüche im Task-Text brechen die Markdown-Struktur des Exports (eingeschleuste falsche `- [x]`-Zeilen/Überschriften). Pflicht in `export_list`: (a) Dateiname: reservierte Namen (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9; case-insensitive, auch mit Endung) mit `_`-Präfix entschärfen; führende/abschliessende Punkte und Leerzeichen entfernen; bleibt nichts übrig, Fallback `list`. (b) Inhalt: in md/txt jede Aufgabe einzeilig ausgeben, `\r` und `\n` im Task-Text durch ein Leerzeichen ersetzen (kein Meta mehr, N11.1.3). (c) Echten Save-Dialog umsetzen (`window.create_file_dialog(webview.SAVE_DIALOG, save_filename=...)`) und die Datei wirklich schreiben. Stand heute schreibt der Export **keine** Datei, das Frontend zeigt nur einen Toast. |
> | **G22** | **SOFORT, spätestens mit 7** | **Ehrlicher `get_status()`.** Bis Phase 8 fertig ist, **muss** `get_status()` den realen Zustand melden: Schicht 1 "SQLCipher mit Entwicklungs-Schlüssel (UNSICHER)", Schicht 2 "nicht implementiert", `active: false`; das Status-Modal zeigt das in Warnfarben statt grün. Eine Tresor-App darf nie eine Verschlüsselung anzeigen, die nicht existiert (aktuell meldet der Status "AES-256 + ChaCha20 · active", während der AES-Key öffentlich im Repo steht; im Audit nachgewiesen). Ab Phase 8 zeigt der Status echte Werte (Argon2-Parameter, Pepper vorhanden ja/nein, Zeitpunkt des letzten Wraps). |
> | **G23** | **✅ umgesetzt 2026-06-10** | **Clipboard-Hygiene + Einzel-Task-Kopie.** Windows speichert das Clipboard in der Zwischenablage-History (Win+V) und synchronisiert es ggf. ins Microsoft-Cloud-Clipboard, App-Inhalte würden so den Rechner verlassen. Umgesetzt: (a) Kopiert wird nur noch **eine ausgewählte Aufgabe** (`copy_task`), nie eine ganze Liste; für Listen gibt es den Export. (b) Das Kopieren passiert komplett im **Backend** (`api.py`, Win32 per ctypes, nicht `navigator.clipboard`) und setzt zusätzlich zu `CF_UNICODETEXT` die Formate `ExcludeClipboardContentFromMonitorProcessing`, `CanIncludeInClipboardHistory` (=0) und `CanUploadToCloudClipboard` (=0). (c) Auto-Clear: 60 s nach dem Kopieren wird das Clipboard geleert, sofern es noch unseren Inhalt trägt. (d) Der `Strg+C`-App-Shortcut wurde ersatzlos entfernt. Bei künftigen Copy-Funktionen MUSS derselbe Backend-Pfad verwendet werden. |
> | **G26** | **❌ verworfen 2026-06-20 (zu fehleranfaellig)** | **Screenshot-Schutz (entfernt).** Idee war, das Fenster per `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` aus Bildschirmaufnahmen herauszunehmen. Mehrfach umgesetzt und wieder entfernt, weil er reale Probleme machte: auf manchen GPU-/Treiber-Konstellationen blockiert die Affinity das WebView2-Rendern komplett (Fenster bleibt weiss / reagiert nicht), und die Startup-Verdrahtung verklemmte zudem die Nachrichtenschleife. Zusatznachteile: blendet das Fenster auch in legitimer Freigabe/Aufnahme schwarz aus und nuetzt nichts gegen eine Kamera. **Entscheidung: dauerhaft entfernt, nicht wieder einbauen.** Falls je erneut gewuenscht, zwingend mit Render-Verifikation nach dem Setzen (Affinity automatisch zuruecknehmen, wenn der Inhalt nicht mehr rendert) und ausschliesslich ueber `_run_on_ui_thread`. |
> | **G25** | **8** | **RAM-Schlüssel-Hygiene.** `aes_key`, `chacha_key`, Master-Secret und Pepper als `bytearray` (nicht `bytes`/`str`) halten; beim Sperren/Panic/Beenden **vor** dem Verwerfen mit Nullen überschreiben. Die Passphrase unmittelbar nach der Ableitung verwerfen; Passphrase und Schlüssel dürfen **nie** in Logs, Exceptions, `get_status()` oder sonstwie ans Frontend gelangen. Im Code dokumentieren: Python gibt keine harten Garantien (der GC kann Kopien hinterlassen), das Nullen ist Best-Effort und trotzdem Pflicht. |
> | **G27** | **9** | **Binary-Härtung gegen Reverse-Engineering + Manipulation.** Authenticode-Signing der `.exe` (Manipulation erkennbar, SmartScreen entschärft); keinen Python-Quelltext mitliefern (vorzugsweise Nuitka statt entpackbarem PyInstaller-Bundle, mindestens Docstrings/`assert`s strippen); optional Obfuskation (PyArmor) als Bonus. **Grundsatz: das Sicherheitsmodell beruht nie auf Code-Geheimhaltung** (Kerckhoffs), sondern allein auf Passphrase + DPAPI-Pepper + Verschlüsselung; die Härtung erhöht nur die Hürde. Keine fragilen Anti-Debugging-Tricks als Schutzbasis. Volltext in Phase 9. |
>
> **Zusätzlich vorgezogen:** G12 (externe WebView-Navigation verweigern) ist mit
> wenigen Zeilen umsetzbar und wird **vor** Phase 7 umgesetzt, nicht erst in
> Phase 8. Ebenso G22 (ehrlicher Status), siehe Tabelle.

Die App ist rein lokal; es gibt keinen eingehenden Netzwerk-Kanal. Trotzdem gelten
die folgenden Regeln als Grundhärtung: Aufgaben-/Listentexte sind Freitext, ein
exportierter oder wieder eingelesener Datenbestand kann manipuliert sein, und die
Regeln kosten nichts. Der Grundsatz „Eingaben nie als Code behandeln" bleibt Pflicht.

**Jeder Text, der ins DOM oder in SQL fließt, gilt als _untrusted input_.** Folgende
Regeln sind Pflicht:

#### Regel 1: Kein `innerHTML` für Nutzerdaten (Anti-XSS)

Im Frontend darf **kein** Task-Text, Listenname oder Meta-Feld jemals über `innerHTML`,
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
   **`sqlcipher3-binary`** (Schicht 1, AES-256, Pflicht), **`cryptography`** (Schicht 2,
   ChaCha20-Poly1305, Pflicht), `argon2-cffi` (Passphrase-Hash + Schlüsselableitung).
   Verschlüsselungs-Design: **Doppel-Kaskade, siehe B.7.**
3. Virtuelle Umgebung anlegen, Abhängigkeiten installieren.

> **🔒 PFLICHT-GATE G11 (Supply Chain):** `requirements.txt` muss die Abhängigkeiten
> auf **feste Versionen pinnen** (`paket==x.y.z`), idealerweise mit `pip` Hash-Checking
> (`--require-hashes`). Für eine Tresor-App ist eine getauschte/kompromittierte Lib eine
> Totalkompromittierung. Gilt laufend: bei jedem Dependency-Update bewusst prüfen.

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
   Frontend einen freundlichen Empty-State („Create your first list"). ANHANG 1 ist damit
   hinfällig.
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
und bekommt die echten Seed-Daten (kurz in der DevTools-Konsole prüfen). **G12:**
externe Navigation wird verweigert.

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
3. `data-theme`, `data-density`, `data-toolbar`, `data-sidebar` und `--accent` werden
   später von `app.js` auf `.app` gesetzt.

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
| Modals (5×) | `renderModal(kind)` | Emergency/Status/Rename/Delete/Shortcuts |
| `LockScreen` | `renderLock()` | Sperrbildschirm |
| `Toasts` | `pushToast()` | Toast-Stack |
| `Icons` | `Icons` (Objekt) | die SVG-Icons (siehe **Anhang 2**, 1:1 aus Konzept) |

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
Modals, Lock-Screen, Toasts, Theme/Accent/Dichte/Toolbar/Sidebar umschalten,
Tastenkürzel, Focus-Modus. Optisch deckungsgleich mit `NoaToDo UI Konzept.html`.

> **Meilenstein:** Nach Phase 6 ist die App als **lokale** To-Do-App voll benutzbar.
> Die Phasen 7-9 ergänzen Export und die Sicherheits-Tiefe. Sie
> sind unabhängig und können einzeln umgesetzt werden.

---

### Phase 6.5: UX-Nacharbeiten am Prototyp (eingeschoben nach dem Audit vom 2026-06-10)

**Stand-Korrektur:** Abgeschlossen ist **Phase 6** (lokal nutzbarer Prototyp).
Phase 7 ist **offen**: `export_list` erzeugt zwar Inhalte, aber es wird noch
keine Datei geschrieben (kein Save-Dialog), siehe Gate G21c. Das Kopieren ist
seit dem 2026-06-10 fertig und gehärtet (`copy_task`, siehe Punkt 5 unten).

**Bereits umgesetzt (2026-06-10), gehört ab jetzt zum Soll-Verhalten:**
1. **Aufgaben inline bearbeiten:** Doppelklick auf eine Aufgaben-Karte öffnet
   die Text-Eingabe direkt in der Karte (kein Meta-Feld mehr, N11.1.3). Enter
   speichert (`edit_task`), Esc bricht ab, Klick daneben speichert (bei leerem
   Text: Abbruch). Leerer Text wird abgelehnt.
2. **Aufgaben einzeln löschen:** Papierkorb-Button erscheint beim Hover auf der
   Karte und ruft `delete_task`.
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

**Noch offen (Pflicht, KEINER dieser Punkte ist optional, je in der genannten Phase):**
- **Undo beim Listen-Löschen (Phase 7):** `delete_list` löscht heute sofort und
  unwiderruflich. Pflicht: Toast "List deleted" mit "Undo"-Button (ca. 6 s
  sichtbar). Umsetzung backendseitig: `delete_list` hält die gelöschte Liste
  samt Aufgaben zunächst im RAM des Backends (oder als `deleted_at`-Soft-Delete),
  eine neue Bridge-Methode `undo_delete_list(id)` stellt wieder her; endgültig
  verworfen wird nach Ablauf der Frist oder beim nächsten App-Start.
- **Profil-Menü aufräumen:** Das Profil-Menü zeigt den hartkodierten Namen
  "Noa Andersen" und tote Einträge (Account, Privacy & data, Export database).
  Pflicht: tote Einträge entweder funktional machen oder entfernen.
- **Export-Save-Dialog (Phase 7):** siehe Gate G21c.

**Abnahme:** Doppelklick-Bearbeiten, Hover-Löschen, das neue `Strg+C`-Verhalten
und Mini-always-on-top funktionieren in der laufenden App; die offenen Punkte
sind in Phase 7 als Pflicht eingeplant.

---

### Phase 7: Export & Kopieren (`backend/api.py` ausbauen)

**Ziel:** Der Export schreibt echte Dateien (Save-Dialog) und das Löschen von
Listen ist per Undo absicherbar. (Das Kopieren ist bereits fertig: `copy_task`
aus Phase 6.5 / Gate G23, es gibt bewusst kein Listen-Kopieren mehr.)

**Tun:**
1. **Zweistufiger Export (N11.2), nur `md` und `txt` (kein JSON, N11.1.5).** Der
   Rail-Button „Export" (bzw. `Ctrl+E`) öffnet zuerst eine kleine Pille links an der
   rechten Rail: **Schritt 1 Umfang** (aktuelle Liste `export_list(id, format)` oder alle
   Listen `export_all(format)`), **Schritt 2 Format** (`md`/`txt`), danach der Save-Dialog.
   `md`: Überschrift = Listenname (bei „alle Listen" jede Liste als größere Überschrift,
   die Aufgaben darunter kleiner), `- [ ]`/`- [x]` je Aufgabe. Kein Meta mehr (N11.1.3).
   `txt` analog als reiner Text.
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

> **🔒 PFLICHT-GATES für Phase 7 (aus dem Audit 2026-06-10, Details in B.9
> Nachtrag G13-G25; keines davon ist optional):**
> - **G20, Validierung lokaler Eingaben:** `add_task`/`edit_task` Text ≤ 4096,
>   Listennamen ≤ 256 (kein `meta` mehr, N11.1.3); Steuerzeichen U+0000-U+001F (ausser
>   `\n`/`\t`) strippen; `reorder`/`reorder_lists` lehnen Nicht-Listen ab; `move_task`
>   validiert IDs; `set_setting` nur mit Key-Whitelist (`accent`, `theme`, `density`,
>   `sidebar`, `railPinned`, `sidebarWidth`, `sound`, `autoLock`; N11.7).
> - **G21, Export-Härtung:** reservierte Windows-Dateinamen (CON, PRN, AUX, NUL,
>   COM1-COM9, LPT1-LPT9) entschärfen; `\r`/`\n` im Task-Text beim md/txt-Export
>   durch Leerzeichen ersetzen (keine eingeschleusten Checkbox-Zeilen); echten
>   Save-Dialog umsetzen und die Datei wirklich schreiben (gilt für `export_list` und
>   `export_all`).
> - **G22, Ehrlicher Status:** `get_status()` meldet den realen
>   Verschlüsselungszustand (Dev-Key = UNSICHER, Schicht 2 = nicht implementiert),
>   bis Phase 8 fertig ist. Spätestens in dieser Phase umsetzen.
> - **✅ G23 (bereits umgesetzt, 2026-06-10):** Einzel-Task-Kopie über `copy_task`
>   im Backend, History-/Cloud-Ausschluss, Auto-Clear nach 60 s, `Strg+C` entfernt.
>   In dieser Phase nur noch verifizieren (Win+V prüfen) und bei neuen
>   Copy-Funktionen denselben Backend-Pfad verwenden.
> - **G12 vorziehen:** Externe WebView-Navigation verweigern (wenige Zeilen in
>   `main.py`), nicht erst in Phase 8.

**Abnahme:** Export schreibt nach Save-Dialog eine korrekte `.md`-Datei (auch bei
Listennamen wie `CON` oder Tasks mit Zeilenumbrüchen); die Einzel-Task-Kopie taucht
nachweislich nicht in der Win+V-History auf und das Clipboard ist nach 60 s leer;
gelöschte Listen lassen sich per Undo-Toast wiederherstellen;
überlange/Steuerzeichen-Eingaben werden begrenzt bzw. bereinigt; `get_status()`
zeigt den ehrlichen Dev-Zustand.

---

### Phase 8: Sicherheits-Tiefe (`backend/security.py`)

**Ziel:** Lock-Screen, Emergency/Panic und (optional) Datenbank-Verschlüsselung real
machen, das Kernversprechen des lokalen, verschlüsselten Tresors.

**Tun:**
1. **App-Sperre nach der Sperr-Politik aus B.8:** `lock()` setzt `locked=True`, verwirft
   die Schlüssel, packt die DB wieder zu (Schicht 2) und zeigt den LockScreen über allem.
   `unlock(passphrase)` prüft den Argon2-Hash, leitet die Schlüssel ab und öffnet die DB.
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
   kein Nullen der Schlüssel, keine sichere Löschung der Klartext-Arbeitskopie).
   In Phase 8 ist das ein Datenspur-Leck und nicht akzeptabel: es darf keinen
   Beenden-Weg geben, der die Spuren stehen lässt, während Off-Knopf/„Finish" sie
   wischen. Umsetzung: einen `closing`-Handler des PyWebView-Fensters registrieren
   (bzw. das X-Ereignis der WinForms-Form abfangen), der **vor** dem tatsächlichen
   Schließen exakt dieselbe sichere Beenden-Routine wie `quit_app()` durchläuft
   (Arbeitskopie sicher löschen und `tasks.db.enc` final schreiben, `PROFILE_DIR`
   nach G14 wischen, Schlüssel/Master-Secret/Pepper nach G25 nullen). `quit_app()`
   und der X-Pfad müssen sich diese Routine teilen (eine gemeinsame Funktion, kein
   duplizierter Ablauf), damit kein Ausgang vergessen wird. Als Rückfalllinie
   zusätzlich `atexit`/`try…finally` um `webview.start()` in `main.py`, das die
   Schlüssel auch bei einem unerwarteten Rückkehren aus dem Message-Loop nullt.
3. **DB-Verschlüsselung, Doppel-Kaskade (Pflicht):** vollständige Umsetzung von **B.7**.
   - Argon2id-Schlüsselableitung aus der Passphrase (Salt erzeugen/speichern, nur den
     Argon2-Hash der Passphrase ablegen) → `aes_key` + `chacha_key`.
   - **Schicht 2 (ChaCha20-Poly1305) Wrap/Unwrap:** beim Entsperren `tasks.db.enc`
     entpacken → SQLCipher-Arbeitskopie; beim Sperren/Schließen/Panic wieder einpacken
     und die Klartext-Arbeitskopie **sicher löschen**.
   - Beim Start ohne korrekte Passphrase bleibt die App im Lock-Screen und kann die DB
     gar nicht öffnen. Damit stimmen Status-Anzeige und Lock-Text
     („LOCAL VAULT · ENCRYPTED") real, nicht nur optisch.
   - `panic()` zusätzlich: Schlüssel + Klartext-Cache sofort verwerfen, Arbeitskopie
     löschen, **den festen WebView2-Profilordner `%LOCALAPPDATA%\NoaToDo\webview` leeren
     (siehe G14)**, offline schalten.
4. `get_status()` liefert echte Werte (DB-Größe, Verschlüsselungs-Status,
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
> - **G8, Argon2id-Kosten + Passphrase-Stärke:** Die Passphrase ist der **einzige reale
>   Schwachpunkt** (ein Angreifer mit der Datei brute-forced offline, App-Sperren bringen
>   da nichts). Daher: hohe Argon2id-Kosten (Memory ≥ 256-512 MB, time_cost ≥ 3,
>   parallelism passend) **und** eine erzwungene Mindest-Stärke der Passphrase
>   (Stärke-Anzeige beim Einrichten). Das ist wichtiger als die zweite Cipher-Schicht.
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

> **🔒 PFLICHT-GATES G13 bis G19 und G25 für Phase 8 (aus dem Audit 2026-06-10,
> vollständige Beschreibung in B.9 Nachtrag; KEINES davon ist optional):**
> - **🔴 G13, Lock serverseitig durchsetzen:** Bei `locked=True` weist der
>   `bridge`-Decorator **jede** Methode ausser `unlock(passphrase)`, `quit_app()`
>   und `killswitch()` mit `{"error": "locked"}` ab; `get_state()` liefert gesperrt
>   nur `{"locked": true}`. Die zwei zusätzlichen Ausnahmen sind bewusst (N10):
>   beide geben nie Daten preis, und Off-Knopf wie Killswitch müssen gerade ohne
>   Passphrase funktionieren. Heute ist die Sperre nur ein Frontend-Overlay (im
>   Audit nachgewiesen: `add_task`/`get_state` funktionieren gesperrt weiter).
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
>   ein Master-Secret → HKDF-SHA256 mit getrennten `info`-Labels → `aes_key` +
>   `chacha_key`; Passphrase-Prüfung ausschliesslich über den Poly1305-Tag der
>   ChaCha20-Entschlüsselung, es wird kein Argon2-Hash gespeichert.
> - **G16, `.enc`-Dateiformat + atomares Schreiben:** Header (Magic `NOA1`,
>   Version, Argon2-Parameter, Salt, Nonce), frische Nonce pro Verschlüsselung,
>   Schreiben über `.tmp` + `fsync` + `os.replace`, eine `.bak`-Generation.
> - **G17, Write-back:** In-Memory-DB nach jeder Mutation debounced (ca. 3 s)
>   und sofort bei Lock/Panic/Quit als neues `tasks.db.enc` persistieren.
> - **G18, DPAPI-Pepper (Pflicht):** 32-Byte-Pepper im Windows Credential Manager,
>   fliesst als Argon2id-`secret` in die Ableitung ein. **Kein Recovery-Export**
>   (N11.3): der Tresor ist bewusst an dieses Windows-Konto gebunden; kein
>   Recovery-Schritt im Einrichtungs-Flow.
> - **G19, Single-Instance-Mutex (umgesetzt 2026-06-20, vorgezogen):** benannter
>   Windows-Mutex `Local\NoaToDoSingleton` beim Start (`_acquire_single_instance` in
>   `main.py`), zweite Instanz zeigt einen Hinweis und beendet sich sofort
>   (Korruptionsschutz, Voraussetzung für den festen WebView2-Profilordner aus G14).
> - **G25, RAM-Schlüssel-Hygiene:** Schlüssel/Master-Secret/Pepper als `bytearray`,
>   vor dem Verwerfen nullen; Passphrase nach Ableitung sofort verwerfen; nichts
>   davon je in Logs, Exceptions oder ans Frontend.

**Abnahme:** Sperren/Entsperren funktioniert mit Passphrase; jede Sperre bereinigt
vorher den Raum (N10); Panic bereinigt sofort und endet im Endschirm;
der Killswitch macht `tasks.db.enc` unwiederbringlich weg und der nächste Start ist
ein Erststart ohne Demo-Daten; bei aktivierter Verschlüsselung ist `tasks.db` ohne
Passphrase nicht lesbar. **G6-G8 erfüllt:** keine entschlüsselte DB-Datei auf der Platte (In-Memory),
Hex-Raw-Key gesetzt, starke Argon2id-Parameter + Passphrase-Stärkeprüfung aktiv.
**G13-G19/G25 erfüllt:** Bridge-Methoden liefern gesperrt nachweislich `locked`-Fehler;
kein WebView2-Datenrest; Entsperren scheitert bei falscher Passphrase über den
AEAD-Tag; `tasks.db.enc` trägt den spezifizierten Header und übersteht einen
simulierten Absturz beim Sperren (`.bak` greift); ohne den Pepper aus dem Credential
Manager ist die Datei offline nicht angreifbar; eine zweite App-Instanz startet nicht.

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
     - `db.py`: CRUD, Seed, parametrisierte Queries, `edit_task`-Spalten-Whitelist.
     - `api.py`-Bridge: Eingabe-Validierung (G20: Längenlimits, Steuerzeichen-Strip,
       `reorder`-Typprüfung, `set_setting`-Key-Whitelist) und Export-Härtung (G21:
       reservierte Windows-Namen, Newline-Ersetzung).
     - Krypto-Roundtrip (Phase 8): KDF-Domain-Separation (G15), `.enc`-Wrap/Unwrap
       inklusive Header und frischer Nonce (G16), falsche Passphrase bzw. fehlender
       Pepper liefern einen AEAD-Fehler, `.bak`-Recovery nach simuliertem Absturz.
     - Lock-Durchsetzung (G13): im gesperrten Zustand liefert jede Bridge-Methode ausser
       `unlock` nachweislich `locked`.
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
   - Reproduzierbarer Build aus `requirements.lock.txt` mit pip-Hash-Checking (Gate G11);
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

4. **Binary-Härtung gegen Reverse-Engineering (neues Gate G27, siehe unten).**

> **🔒 NEUES GATE (Phase 9):**
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

**Abnahme:** `pytest` läuft grün; `NoaToDo.exe` startet auf einem frischen Windows-Profil
ohne installiertes Python, legt bei fehlender DB einen neuen, gesperrten Tresor an und
meldet eine fehlende WebView2-Runtime verständlich; die `.exe` ist signiert (sofern ein
Zertifikat vorliegt) und enthält keinen im Klartext lesbaren Python-Quelltext.

---

## NACHTRAG (2026-06-13): UX-Pflichten und -Erweiterungen aus dem UX/UI-Audit

Nach dem lokal nutzbaren Meilenstein (Phase 6 + 6.5) wurde ein vollständiges
UX/UI-Audit erstellt (`Planung/UX-UI Verbesserungen.md`, Stand 2026-06-12). Dieser
Nachtrag überführt **alle Audit-Punkte, die noch zu bauende Features betreffen**, in
den Bauplan, damit sie nicht verloren gehen. Reine Sofort-Korrekturen (Mac-Symbole,
UI-Sprache) wurden am 2026-06-13 direkt im Code erledigt (siehe Entscheidung unten).
Die verbleibenden **Gegenwarts-Mängel** (z.B. unehrliche Status-/Toast-Texte, fehlende
Tastaturnavigation, A11y, Voll-Re-Render) sind nicht Teil dieses Nachtrags; sie stehen
im Audit (Prioritäten P1 bis P3) und werden separat abgearbeitet. Querverweise in der
Form „(UX x.y)" zeigen auf den jeweiligen Abschnitt im Audit.

**Sprach- und Plattform-Entscheidung (verbindlich, 2026-06-13):**
- **UI-Sprache: durchgehend Englisch.** Die frühere Überlegung „Deutsch" wurde
  verworfen. Alle sichtbaren UI-Strings sind englisch; die zuvor gemischten deutschen
  Tooltips wurden am 2026-06-13 angeglichen (`frontend/app.js`, `index.html` jetzt
  `lang="en"`). Code-Kommentare bleiben Deutsch (Entwickler-Sprache), das ist keine UI.
- **Zielplattform: ausschließlich Windows.** In UI und Plan kommen **keine**
  Mac-Tastensymbole (⌘, ⇧) mehr vor; Tastenkürzel werden als `Ctrl`/`Shift` dargestellt.
  B.4, B.5 und B.8 wurden entsprechend bereinigt.

**Was bereits im Plan steht (nur Querverweis, hier nicht erneut spezifiziert):**
Profil-Menü aufräumen (UX 1.3) -> Phase 6.5; Export-Save-Dialog + ehrliches Feedback (UX 1.5)
-> Phase 7 / Gate G21c; Undo beim Listen-Löschen (UX 1.2, 3.3) -> Phase 6.5 + Phase 7;
ehrlicher `get_status()` und Status-Modal (UX 1.4, 8.4) -> Gate G22 + Phase 8;
Auto-Lock-Timeout (UX 7.6) -> B.8; serverseitige Lock-Durchsetzung -> Gate G13
(Screenshot-Schutz / G26 wurde verworfen, siehe oben). Diese Punkte sind verbindlich
an den genannten Stellen, hier nur zur Vollständigkeit gelistet.

### N2. Persistente Offline-Statusanzeige (UX 4.2, 8.3)
Der Online/Offline-Zustand ist heute fast unsichtbar (nur Globus-/Flugzeug-Icon in
der oft versteckten Rail plus kurzer Toast). Das Konzept sah die `airplane-pill` als
persistenten Banner vor; ihr CSS liegt ungenutzt im Stylesheet. Optionaler UX-Ausbau:
- Eine **persistente Statuspille** im Hauptbereich (oder am Dock), sichtbar sobald
  `online=false` („offline mode"). Der Offline-Schalter ist rein lokal (kein Sync).
- Damit entschärft sich auch UX 3.12 (versehentliches `G`/Offline ohne sichtbare Folge).

### N4. Phase 8: Echter Lock-Screen mit Passphrase (UX 8.1) [Sec]
B.4 und Phase 8 nennen die Passphrase-Eingabe, aber nicht die UX-Details. Der heutige
„4x tippen"-Platzhalter (`renderLock`, `lockTap`) wird ersetzt durch ein echtes
Eingabefeld mit folgenden **Pflicht-Eigenschaften**:
- Passwort-Feld mit Show/Hide-Umschalter.
- Fehlerzustand bei falscher Passphrase: Shake + Meldung „wrong passphrase", **ohne**
  preiszugeben, ob ein Tresor existiert (neutrale Meldung).
- Warnung bei aktiver Feststelltaste (Caps Lock).
- **Fortschritts-/Spinner-Zustand beim Entsperren:** Argon2id mit den Kosten aus
  Gate G8 (Memory ≥ 256 bis 512 MB) braucht spürbar Zeit; das ist gewollt, also braucht
  es eine „unlocking…"-Anzeige, sonst wirkt die App eingefroren.
- **Rate-Limit-Anzeige** nach mehreren Fehlversuchen („try again in 30 s"); bremst
  Offline-Rateversuche zusätzlich zur teuren KDF.
- Hängt an Gate G13 (gesperrt = Backend liefert `locked`), G15 (Prüfung über den
  Poly1305-Tag) und G18 (DPAPI-Pepper): ohne Pepper bzw. richtige Passphrase scheitert
  die ChaCha20-Entschlüsselung, die Fehlermeldung kommt aus dem AEAD-Tag.

### N5. Phase 8: Panik-Flow, Hotkey ohne Rückfrage (UX 8.2) [Sec]
*(Aktualisiert 2026-07-08, siehe N10: der Panik-Flow endet jetzt im Endschirm mit
Finish/Killswitch, nicht mehr im Lock-Screen.)*
- Der volle Panik-Flow (Endschirm, Killswitch) bleibt **bewusst mehrstufig** und nur
  per Maus über den Rail-Button erreichbar (Kippschalter + Confirm): die Mehrfach-
  Bestätigung schützt vor versehentlichem Auslösen, gerade weil der Killswitch
  unwiderruflich ist.
- **Hotkey `Ctrl+Shift+!` löst ohne Rückfrage die verstärkte Sperre aus** (Lock nach
  N10: Raum bereinigen + offline + Lock-Screen); im Notfall zählt Geschwindigkeit,
  und die verstärkte Sperre deckt den „schnell alles zu"-Fall vollständig ab, ohne
  Datenverlust-Risiko.

### N6. Phase 8: Entsperr-/Boot-Fehlerbildschirm (UX 6.3) [Sec]
`boot()` rendert bei Fehlern heute ein nacktes `<pre>boot error</pre>`. Ab Phase 8 sind
„falsche Passphrase" und „beschädigte/fehlende `tasks.db.enc`" reale Szenarien. Pflicht:
ein gestalteter Fehlerzustand mit Handlungsoption (Retry, Pfadangabe, Hinweis auf die
`.bak`-Generation aus Gate G16 und, bei vergessener Passphrase, auf den Reset-Weg aus
N11.3; einen Pepper-Recovery-Export gibt es bewusst nicht). Der Nutzer darf bei einem
AEAD-Fehler nie ratlos vor einem leeren Fenster stehen.

### N7. Neue Fähigkeiten mit Bridge-Erweiterung (einplanen, z.B. Phase 7 oder Folge-Iteration)
Echte Funktionslücken einer Mehrlisten-App, je mit kleiner Backend-Ergänzung. Kein
Sicherheitsthema, daher zeitlich flexibel, aber fest eingeplant:
- **Aufgaben zwischen Listen verschieben (UX 3.7):** neue Bridge-Methode
  `move_task(id, target_list_id)` (oder `edit_task` um `list_id` erweitern); Auslösung
  per Drag auf einen Sidebar-Eintrag und per „Move to…" im Kontextmenü. Validierung wie
  bei `add_task` (Gate G20), Zielposition ans Ende der Ziel-Liste.
- **Listen umsortieren (UX 3.9):** das Schema hat `lists.position`, aber kein UI. Neue
  Methode `reorder_lists(ordered_ids)` analog zu `reorder` (gleiche Typprüfung, Gate
  G20), Drag & Drop in der Sidebar.
- **„Clear completed" (UX 3.8):** Sammel-Löschen aller erledigten Aufgaben einer Liste,
  mit Bestätigung bzw. Undo (analog zum Listen-Undo aus Phase 7). Eigene Methode (z.B.
  `clear_completed(list_id)`), die serverseitig löscht.

### N8. Roadmap-Erweiterungen (ergänzt D.3)
Bewusst kein Kern-Scope, aber als Produktrichtung festgehalten:
- **Aufgaben-Detailansicht (UX 7.4):** ausklappbare Detailzeile (Beschreibung,
  Erstellt-Datum).
- **Volltextsuche/Filter (UX 7.2):** ~~`Ctrl+F`-Overlay mit Fuzzy-Filter~~ **wird nicht
  gebaut** (Entscheidung N11.7).
- **Mini-Modus, Listenwechsel (UX 7.7, 3.14):** ein Dropdown im `mini-bar`-Titel zum
  Wechseln der Liste, ohne den Mini-Modus zu verlassen.
- **Meta-Feld benennen/strukturieren (UX 7.3):** ~~erledigt~~ **hinfällig**: das
  Freitext-`meta` wurde ersatzlos entfernt (N11.1.3).

### N9. Einstellungen, Vorbereitung künftiger Phasen (UX 7.6)
Ergänzend zu den schon geplanten Settings (Auto-Lock-Timeout B.8): **Startverhalten**
(maximiert vs. letzte Fenstergröße) als Einstellung vorsehen.
Die bestehende Settings-Struktur (Zeile + Segment, B.6) trägt das ohne Umbau; jeder neue
Key muss in die `set_setting`-Whitelist aus Gate G20 aufgenommen werden.

### N10. Verstärkter Lock, Off-Knopf und Panik-Endschirm mit Killswitch (2026-07-08) [Sec]
Entscheidung vom 2026-07-08; ersetzt bzw. präzisiert Teile von B.4, B.8, N5 und
Phase 8 Punkt 1/2. Die UI-Anteile sind bereits umgesetzt (Stand Phase 6.5); die
Sicherheits-Anteile (echte Schlüssel, sicheres Wischen) bleiben Pflicht in Phase 8.

**1. Lock wird verstärkt („Panik light").** Jede Sperre (Lock-Button, `Ctrl+L`,
später Auto-Lock und Windows-Sitzungssperre) macht zuerst das, was bisher nur Panik
tat: Raum leeren (`state.lists` verwerfen, keine Liste offen, Menüs/Modals/Auswahl
schließen), offline schalten. Erst dann erscheint der bekannte Lock-Screen mit der
Passwort-Pille. Es werden dabei **keine Daten gelöscht**: das Backend bleibt die
Wahrheit, nach dem Entsperren lädt das Frontend alles frisch per `get_state()` und
startet wie mit leerer Arbeitsfläche (Sidebar zu, keine Liste offen). Offline bleibt
die App, bis der Nutzer es bewusst wieder einschaltet.

**2. Off-Knopf auf dem Lock-Screen.** Oben rechts ein klassischer Power-Knopf. Ein
Klick beendet die App sofort über `quit_app()`, ohne Passphrase. Dabei werden
zufällig hinterlassene Spuren vernichtet (heute: der Raum ist bereits bereinigt,
der WebView2-Cache wird ohnehin beim nächsten Start gewischt; Phase 8: sicheres
Wischen von `PROFILE_DIR` nach G14, Schlüssel nullen nach G25), aber ausdrücklich
**keine Nutzer- und keine App-Daten gelöscht**. Die Passworteingabe bleibt daneben
jederzeit möglich; der Off-Knopf ist nur der zweite Ausgang.

**3. Panik-Endschirm mit zwei Ausgängen.** Der Panik-Einstieg bleibt mehrstufig
(Rail-Knopf, Kippschalter „No/Yes", separate Confirm-Pille): mit dem Mehrmals-
Bestätigen ist man gegen Versehen sicher unterwegs. Nach dem Bestätigen wird sofort
real bereinigt (wie beim Lock: Raum leeren, offline, Zustand verwerfen) und der
„Wipe"-Fortschrittsschirm gezeigt; danach der Endschirm mit der Aussage, die
Maschine sei sicher gewiped (bewusste Außendarstellung). Zurück in die App führt
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

**4. Nach dem Killswitch.** Der nächste Start verhält sich wie ein Erststart auf
einem frischen Rechner, aber **ohne** die Demo-Seed-Daten: keine Listen, alles kann
neu angelegt werden. **N11.8.1 gilt vorrangig: `killswitch()` ist ab Phase 8 eine reine Datei-Loeschung (`tasks.db.enc` + `.bak` + Metadaten + Pepper + Profile), schreibt KEINE Settings und keinen `seeded`-Marker mehr; der naechste Start ist mangels Datei automatisch ein leerer Erststart.** (Frueher, DB-basiert: schrieb Standard-Settings neu und setzte `seeded=true`.) Gelöscht wird nur der Inhalt der
Datenbank, **nie das Programm selbst**. Nirgendwo dürfen danach Daten liegen, die
auf die frühere Nutzung schließen lassen. Ehrliche Einordnung des heutigen Stands:
Zeileninhalte sind weg und `VACUUM` baut die Datei neu auf, aber auf SSD/NTFS ist
das noch kein forensisches Secure-Delete; erst die Phase-8-Härtung (In-Memory-DB
nach G6, `.enc`-Neuaufbau nach G16, `PROFILE_DIR`-Wisch nach G14) macht die Zusage
auch forensisch belastbar.

**5. Bridge-Erweiterung und Phase-8-Folgen.** Neu in B.2: `quit_app()` und
`killswitch()`. `killswitch()` ist nur aus dem Panik-Endschirm erreichbar; ein
direkter Aufruf über eine XSS wäre Datenvernichtung per Fernzugriff, die
`esc()`-Pflicht aus B.9 gilt hier also doppelt. Für Phase 8 gilt: Gate G13 muss
`quit_app()` und `killswitch()` neben `unlock()` **ausdrücklich als erlaubte
Ausnahmen** im gesperrten Zustand definieren (beide sind destruktiv bzw. beendend,
geben aber nie Daten preis; der Killswitch soll gerade ohne Passphrase funktionieren).
Der Phase-8-Killswitch löscht dann `tasks.db.enc` samt `.bak`-Generation und
Vault-Metadaten (Salt, Pepper-Verweis) direkt, wofür keine Schlüssel nötig sind.

---

## NACHTRAG N11 (2026-07-09): Entscheidungen aus der Luecken-Klaerung (verbindlich)

Vorbemerkung: Dieser Nachtrag schliesst gezielt alle Stellen, an denen der Plan
bisher offen war und eine ausfuehrende KI haette raten muessen. Alle Punkte sind
vom Nutzer bestaetigt und **ueberschreiben** frueher anderslautende Formulierungen
an den genannten Stellen. Im Zweifel gilt N11. Phasennummerierung nach der aktuellen
Fassung: Sicherheit = **Phase 8**, Auslieferung/Build = **Phase 9** (die fruehere
Benachrichtigungs-Phase ist entfallen, siehe N11.1.1).

### N11.1 Ersatzlos gestrichene Features

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

4. **Demo-Seed-Daten entfernt.** Ein frischer Tresor startet **immer leer** (Erststart,
   nach Reset, nach Killswitch). Es werden keine Beispiel-Listen mehr eingespielt; nur
   die Default-Settings werden geschrieben. Der leere Zustand bekommt einen freundlichen
   Empty-State (Hinweis "Create your first list"). Ueberschreibt: Phase 1 Punkt 4,
   `seed_if_empty`-Demoinhalt, ANHANG 1.

5. **JSON-Export entfernt.** Es gibt nur noch `txt` und `md`. Ueberschreibt: B.2
   (`export_list(id, format)` Enum wird `'md'|'txt'`), Phase 7 Punkt 1.

### N11.2 Phase 7: Export, Undo, Verschiebe-Features

- **Zweistufiger Export.** Der Rail-Button "Export" (bzw. `Ctrl+E`) speichert **nicht**
  direkt, sondern oeffnet zuerst eine kleine Pille an der **linken Seite der rechten
  Rail**. **Schritt 1: Umfang** ("nur aktuelle Liste" oder "alle Listen mit allen
  Aufgaben"). **Schritt 2: Format** (`md` oder `txt`). Danach der Save-Dialog.
- **md-Formatierung bei "alle Listen".** Sauber strukturiert: Listennamen als groessere
  Ueberschrift (z.B. `#`), die einzelnen Aufgaben darunter kleiner (`- [ ]`/`- [x]`).
  Bei "nur aktuelle Liste" wie bisher.
- **Undo nur beim Listen-Loeschen** (Toast "List deleted" mit "Undo", ca. 6 s). Einzelne
  Aufgaben werden weiterhin sofort und ohne Undo geloescht. "Clear completed" wird
  **nicht** gebaut.
- **N7-Features hier mitbauen:** `move_task(id, target_list_id)` (Drag auf einen
  Sidebar-Eintrag plus "Move to..."-Kontextmenue) und `reorder_lists(ordered_ids)`
  (Drag and Drop in der Sidebar). Validierung wie `add_task` (G20). Volltextsuche und
  "Clear completed" entfallen.

### N11.3 Phase 8: Ersteinrichtung, Passphrase, Reset

- **Keine Bestandsdaten-Uebernahme.** Beim Umstieg auf die echte Verschluesselung wird
  die alte Dev-DB verworfen; der neue Tresor startet leer. Keine Migration.
- **Tresor-Ort beim ersten Start waehlbar.** Der Nutzer legt den Speicherort von
  `tasks.db.enc` bei der Einrichtung fest. Der Pfad kann nicht im Tresor stehen
  (Henne-Ei-Problem), daher liegt er in einer kleinen **unverschluesselten Konfig**
  (z.B. `%LOCALAPPDATA%\NoaToDo\config.json`), die nur diesen Pfad und nicht-geheime
  Startinfos enthaelt, nie Aufgabendaten.
- **Passphrase-Regel: nur Mindestlaenge 12 Zeichen.** Keine weiteren Zeichenregeln, kein
  Staerkemesser-Zwang. Gate G8 bleibt fuer die Argon2id-Kosten gueltig; die dort
  genannte "erzwungene Passphrase-Staerke" wird hier auf "Mindestlaenge 12"
  konkretisiert.
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
  min. 12 Zeichen setzen; der Tresor wird mit dem neuen Schluessel neu verpackt).

### N11.4 Phase 8: Auto-Sperre und Entsperr-Rate-Limit

- **Auto-Sperre nach Inaktivitaet: einstellbar, Default 15 min.** Presets in den
  Einstellungen (z.B. 1/5/15/30/60 min) plus "nie" zum Abschalten. Konkretisiert B.8.
- **Rate-Limit bei falscher Passphrase (konkret):**
  - Nach **jedem** Fehlversuch 2 s Zwangspause bis zum naechsten Versuch.
  - **3 freie Versuche**, dann greift die Eskalations-Leiter.
  - **Leiter:** 10 s, 30 s, 1 min, 5 min, 15 min, 30 min, 1 h, 5 h, 10 h (danach bleibt
    es bei 10 h).
  - **Jede Stufe erlaubt 2 Fehlversuche**, bevor auf die naechste (laengere) Stufe
    hochgeschaltet wird.
  - Gilt zusaetzlich zur ohnehin langsamen Argon2id-Ableitung (G8). Anzeige gemaess N4
    ("try again in ...").

### N11.5 Echter Flugmodus statt Deko-Schalter

- Der Online/Offline-Schalter (Flugzeug/Globus, `set_online`, Taste `G`) **bleibt** und
  wird **funktional:** offline schalten heisst, den **echten Windows-Flugmodus**
  einzuschalten, also **alle Funkgeraete** (WLAN, Bluetooth, was vorhanden ist)
  auszuschalten; online schalten aktiviert sie wieder. Umsetzung ueber die
  Windows-Radio-APIs (WinRT `Windows.Devices.Radios` bzw. Radio-Management), eine
  einmalige Nutzerzustimmung ist akzeptabel. `get_wifi_signal()` bleibt und zeigt real
  den Zustand. Ueberschreibt B.2/B.4 ("rein lokaler Schalter, kein Netzwerkverkehr").
- **Zustand beim Beenden/Sperren wiederherstellen, aber als letzter Schritt.** Beim
  Sperren/Panik/Beenden wird der Funk-Zustand von **vor** dem App-Start wiederhergestellt
  (hat die App den Flugmodus eingeschaltet, wird er wieder ausgeschaltet). Das passiert
  **ganz zuletzt:** erst die Raum-Bereinigung und alle uebrigen Schritte (N10), am Ende
  die Wiederherstellung des Systemzustands.
- **Externe Aenderungen spiegeln.** Aendert der Nutzer den Flugmodus in den
  Windows-Einstellungen, passt sich die App-Anzeige an. Umsetzung **ereignisbasiert**
  (sofortige Reaktion auf die Windows-Radio-Statusaenderung) mit einer seltenen
  Gegenpruefung als Rueckfalllinie. Der Nutzerwunsch "alle 30 s abfragen" wird durch die
  sofortige Ereignis-Erkennung erfuellt und uebertroffen.

### N11.6 Theme, Header, Profil, Fenster, Ton

- **Theme folgt automatisch Windows** (hell/dunkel), mit **sofortiger** Reaktion auf die
  Windows-Theme-Aenderung (ereignisbasiert ueber `WM_SETTINGCHANGE` bzw. den Registry-
  Wert `AppsUseLightTheme`), plus seltene Gegenpruefung. Beim Start sofort das korrekte
  Theme, kein Nachziehen. **Manueller Override bleibt:** `Ctrl+J` bzw. der Theme-Schalter
  setzt bewusst ein festes Theme (hell oder dunkel), bis der Nutzer wieder auf
  "automatisch" stellt. Der Settings-Key `dark` wird dazu durch `theme` mit den Werten
  `auto`|`light`|`dark` ersetzt (Default `auto`); in die G20-Whitelist aufnehmen.
- **Header-Mitte bleibt leer** (die frühere Benachrichtigungs-Pille faellt ersatzlos
  weg). Brand links, Avatar rechts.
- **Profil-Menue eindampfen.** Der fest eingetippte Name ("Noa Andersen") und tote
  Eintraege raus. Es bleibt nur, was echt funktioniert: "Export database" wird der neue
  Alle-Listen-Export (N11.2), optional ein Link zu den Einstellungen. Alles andere
  entfernen.
- **Fenster startet maximiert** (fest verdrahtet, kein Setting noetig). Ueberschreibt N9
  "maximiert vs letzte Groesse".
- **Erledigt-Ton abschaltbar.** Der synthetisierte Blip beim Abhaken bleibt Default an,
  ist aber in den Einstellungen abschaltbar. Neuer Settings-Key `sound` (bool, Default
  `true`); in die G20-Whitelist aufnehmen.

### N11.7 Settings-Whitelist und Roadmap-Folgen

- **Settings-Whitelist (G20) neu:** entfernt werden `notify`, `notifyInApp`,
  `notifyWindows` (bereits weg) und das ohnehin unbenutzte `toolbar`; hinzu kommen
  `theme` (`auto`/`light`/`dark`), `sound` (bool), `autoLock` (Minuten, `0` = nie).
  Weiter gueltig: `accent`, `density`, `sidebar`, `railPinned`, `sidebarWidth`. Der
  `seeded`-Marker bleibt Backend-Marker (verhindert kuenftiges Demo-Seeding generell,
  da ohnehin nie geseedet wird). `dark` entfaellt zugunsten von `theme` (N11.6).
- **N8-Roadmap:** Volltextsuche wird **nicht** gebaut; die Aufgaben-Detailansicht bleibt
  Roadmap (spaeter); die Meta-Feld-Frage ist durch die Entfernung (N11.1.3) erledigt.

### N11.8 Phase 8: Sicherheits-Widersprueche aufgeloest [Sec]

Vier Stellen, an denen sich spaetere Phasen bisher gegenseitig widersprachen. Diese
Entscheidungen ueberschreiben die genannten Passagen; im Zweifel Security first.

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

2. **Start-Weiche eindeutig:** Beim Start entscheidet **allein die Existenz von
   `tasks.db.enc`** (Pfad aus `config.json`, N11.3): vorhanden -> Lock-Screen (nur
   Passphrase, N4); fehlt (frischer Rechner, nach Reset, nach Killswitch) -> Onboarding
   (Speicherort waehlen, Passphrase min. 12, leeren Tresor anlegen; N11.3, N11.1.4).
   *Praezisiert die Absolut-Formulierung "startet immer im Lock-Screen" in B.8.*

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
   Prozess (Single-Instance-Mutex G19 bleibt einer); die genaue PyWebView-Mechanik
   (zweites Fenster vs. Neuerzeugung) ist in Phase 8 zu verifizieren, das Ziel ist fix:
   **App-Profil wischbar, Lock-Screen-Profil springt ein.** Der Startup-Cache-Purge
   (`_purge_webview_cache`) gilt fuer beide Profile getrennt.

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

### N11.9 Phase 8: Verschluesselung, beide Schichten bleiben Pflicht [Sec]

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
- **Ehrliche Neuformulierung (ersetzt die B.7-Notiz "live nur AES"):** Am Ruhezustand
  schuetzen **beide** Schichten. Waehrend die App entsperrt laeuft, existiert der
  Klartext ausschliesslich fluechtig im RAM (SQLite-Page-Cache), wie bei jeder App;
  dagegen helfen schnelle Sperre, Auto-Sperre und Panik, nicht die Cipher.
- **Neues Pflicht-Gate G28 (Verschluesselungs-Beweis, Phase 8):** Vor Phase-8-Abschluss
  ist zu **beweisen**, dass die Arbeits-/Zwischendatei tatsaechlich AES-verschluesselt
  ist: das Oeffnen des inneren Images **ohne** `aes_key` muss fehlschlagen (kein
  SQLite-Klartext-Header, kein lesbarer Task-Text im Roh-Byte-Dump). Schlaegt der Beweis
  fuer den `:memory:`-Serialize-Weg fehl, ist der verschluesselte-Temp-Datei-Fallback
  verbindlich. Kein Auslieferungsbuild ohne bestandenen Beweis.

---

## TEIL D: Offene Entscheidungen & Erweiterungen

### D.1 Privatsphäre: alles bleibt lokal

- **Lokal:** alle Aufgaben, alle Bearbeitungen, die gesamte SQLite-DB. Nichts verlässt
  je den Rechner; es gibt keinen externen Dienst, keine Cloud-Anbindung und keinen Sync.
- Im Windows Credential Manager (über `keyring`) liegt nur der DPAPI-Pepper der
  Schlüsselableitung (siehe G18), keine Aufgabendaten.

### D.3 Mögliche spätere Erweiterungen (nicht im Kern-Scope)

- Unterpunkte/Checklisten je Aufgabe, Wiederholungen.
- Mehrere Akzent-/Theme-Presets, anpassbare Dichte je Liste.

(Volltextsuche und automatische Backups wurden bewusst gestrichen, siehe N11.1.2 und
N11.7.)

---

## ANHANG 1: Seed-Daten (Startfüllung der DB) [HINFÄLLIG]

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

## ANHANG 2: Icon-Set

Das Konzept bringt ein eigenes, konsistentes Line-Art-Icon-Set mit (24er-Grid,
Strichstärke 1.7, runde Enden). Diese SVG-Pfade **1:1 aus dem Konzept übernehmen**
(`Icons`-Objekt). Benötigte Icons: `Menu, Close, Shield, Plus, Check, Gear,
Chevron, Grip, Plane, Wifi, Expand, Palette, Share, Help, Lock, Unlock, Alert, Copy,
Pencil, Trash, Diag, Globe, Note, Sun, Moon, User, Logout, Pin, Download`. Das
App-Logo (`NoaToDo Logo.png`, orangenes „N" im Kreis) zusätzlich als Fenster-/Taskbar-
Icon verwenden.

---

## Schnell-Checkliste (für die ausführende KI)

- [ ] Phase 0, Struktur + Abhängigkeiten, leeres Fenster **+ 🔒 G11 (Deps pinnen)**
- [ ] Phase 1, `db.py` Schema + CRUD (kein Demo-Seed mehr, N11.1.4)
- [ ] Phase 2, `api.py` Bridge (lokal)
- [ ] Phase 3, `main.py` Fenster + Verdrahtung **+ 🔒 G12 (Navigation abriegeln)**
- [ ] Phase 4, `index.html` Gerüst, Bridge im Fenster bewiesen
- [ ] Phase 5, `style.css` (CSS 1:1 aus Konzept) + lokale Fonts
- [x] Phase 6, `app.js` komplette UI + Interaktionen  ← **lokal voll nutzbar (Stand heute)**
- [x] Phase 6.5, UX-Nacharbeiten (Inline-Edit, Task-Löschen, Task-Auswahl, gehärtete Einzel-Task-Kopie ✅G23, Strg+C entfernt, Mini-on-top, Screenshot-Schutz ❌G26 verworfen); Rest-Pflichten in 7 verplant
- [ ] Phase 7, zweistufiger Export (nur md/txt, N11.2) + Undo (nur Listen-Löschen) + `move_task`/`reorder_lists` **+ 🔒 G20 (lokale Eingabe-Validierung), G21 (Export-Härtung + Save-Dialog), G22 (ehrlicher Status), G12 vorziehen** (G23 schon erledigt)
- [ ] Phase 8, Lock / Emergency / Doppel-Kaskade AES-256 + ChaCha20 (B.7) **+ 🔒 G6 (In-Memory-DB), G7 (Hex-Raw-Key), G8 (Argon2id-Kosten + Passphrase-Stärke), 🔴 G9 (`DEV_AES_KEY` entfernen), 🔴 G13 (Lock serverseitig), G14-Rest (PROFILE_DIR sicher wischen bei lock/panic/quit, **Fenster-X = gleicher sicherer Beenden-Pfad wie `quit_app()`**; fester Ordner + Altlasten-Wisch ✅ 2026-06-20), G15 (HKDF/kein Hash), G16 (.enc-Format), G17 (Write-back), G18 (DPAPI-Pepper), G25 (RAM-Hygiene)** (G19 Single-Instance ✅ 2026-06-20 vorgezogen)
- [ ] Phase 9, Auslieferung + Tests + Build (portable `NoaToDo.exe`, PyInstaller/Nuitka, WebView2-Runtime, Erststart auf fremdem Rechner) **+ 🔒 G27 (Binary-Härtung gegen Reverse-Engineering), G11 (Hash-gepinnter Build)**
- [ ] UX-Nachtrag 2026-06-13 (Abschnitt vor TEIL D): N2 Offline-Statuspille, N4 Lock-Screen-Passphrase-UX (8), N5 Panik-Hotkey ohne Rückfrage (8), N6 Entsperr-Fehlerbildschirm (8), N7 move_task/reorder_lists (Phase 7; clear_completed gestrichen), N8 Roadmap (D.3), N9 Fenster startet maximiert (N11.6), N10 verstärkter Lock + Off-Knopf + Killswitch (UI ✅ 2026-07-08, Sicherheits-Rest Phase 8), N11 Lücken-Klärung 2026-07-09 (verbindlich)

### 🔒 Sicherheits-Gates auf einen Blick (Details in B.9)

| Gate | Phase | Kurz |
|---|---|---|
| ✅ CSP gesetzt | erledigt | `index.html`, strenger als Minimum |
| ✅ `esc()` gehärtet | erledigt | maskiert jetzt auch `'` |
| 🔒 G6 | 8 | In-Memory-DB statt Temp-Arbeitskopie |
| 🔒 G7 | 8 | Hex-Raw-Key für `PRAGMA key` |
| 🔒 G8 | 8 | Argon2id hohe Kosten + Passphrase-Stärke |
| 🔴 G9 | 8 | **`DEV_AES_KEY` & jeden statischen Schlüssel-Fallback entfernen** (sonst null Verschlüsselung) |
| 🔒 G11 | 0 / laufend | Abhängigkeiten versions-pinnen (+ Hash-Checking) |
| 🔒 G12 | vor 7 (vorgezogen) | Externe WebView-Navigation verweigern |
| 🔴 G13 | 8 | **Lock serverseitig durchsetzen** (gesperrt = jede Methode ausser `unlock` liefert `locked`-Fehler) |
| 🔒 G14 | teils erledigt (2026-06-20), Rest 8 | WebView2 ohne Datenspuren: fester Profilordner statt Privatmodus ✅, Altlasten-Wisch beim Start ✅; sicheres Wischen bei lock/panic/quit offen (Phase 8), **inkl. Fenster-X = gleicher Beenden-Pfad wie `quit_app()`** |
| 🔒 G15 | 8 | Argon2id-Master-Secret + HKDF-Domain-Separation; kein Verifikations-Hash, Prüfung via Poly1305-Tag |
| 🔒 G16 | 8 | `tasks.db.enc`-Header (Magic/Version/Params/Salt/Nonce), frische Nonce, atomares Schreiben + `.bak` |
| 🔒 G17 | 8 | Debounced Write-back der In-Memory-DB (Crash kostet höchstens Sekunden) |
| 🔒 G18 | 8 | DPAPI-Pepper im Credential Manager als Zweitfaktor gegen Offline-Brute-Force (kein Recovery-Export, Tresor an den PC gebunden, N11.3) |
| ✅ G19 | erledigt (2026-06-20, vorgezogen) | Single-Instance-Mutex `Local\NoaToDoSingleton` (zweite Instanz zeigt Hinweis und beendet sich) |
| 🔒 G20 | 7 | Regel-4-Validierung auch lokal + `reorder`-Typprüfung + `set_setting`-Key-Whitelist |
| 🔒 G21 | 7 | Export-Härtung: reservierte Windows-Namen, Newline-Ersetzung, echter Save-Dialog |
| 🔒 G22 | sofort/7 | `get_status()` meldet den ehrlichen Verschlüsselungszustand (kein falsches "active") |
| ✅ G23 | erledigt (2026-06-10) | Einzel-Task-Kopie im Backend: keine Win+V-History, kein Cloud-Clipboard, Auto-Clear 60 s, `Strg+C` entfernt |
| 🔒 G25 | 8 | RAM-Schlüssel-Hygiene: `bytearray` + Nullen, Passphrase sofort verwerfen, nie loggen |
| ❌ G26 | verworfen + entfernt (2026-06-20) | Screenshot-Schutz `WDA_EXCLUDEFROMCAPTURE` blendete Aufnahmen schwarz aus, verhindert aber auf manchen GPUs das Rendern (Fenster weiss / reagiert nicht). Mehrfach ein-/ausgebaut, endgueltig entfernt. Nicht wieder einbauen ohne Render-Verifikation + Affinity-Rollback |
| 🔒 G27 | 9 | Binary-Härtung: `.exe` signieren, kein Quelltext mitliefern (Nuitka), optional Obfuskation. Sicherheit beruht nie auf Code-Geheimhaltung (Kerckhoffs), nur auf Passphrase + Pepper + Verschlüsselung |

**Hinweise (kein Gate):** Export schreibt unverschlüsselte Dateien (by design, der
Nutzer exportiert bewusst Klartext); `main.py` `emit()` muss
`json.dumps(..., ensure_ascii=True)` behalten (U+2028/U+2029-Schutz im
`evaluate_js`-Kanal). Das Clipboard-Thema ist seit dem Nachtrag ein Gate (G23).
