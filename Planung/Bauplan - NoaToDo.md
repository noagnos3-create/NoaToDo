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
> Schritt-Baufolge (Phase 0-11). Jeder Schritt hat: **Ziel**, **Tun**, **Abnahme**
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

Zusätzlich kann die App Aufgaben **aus Microsoft To Do lesen** (nur lesend) und lokal
spiegeln. Dieser Sync ist strikt einseitig: Cloud → lokal. Nichts fließt je zurück.

### A.2 Architektur in einem Satz

Ein **Python-Backend** (Logik, SQLite, Microsoft-Sync, Sicherheit) und ein
**Web-Frontend** (HTML/CSS/JS, das gesamte Design) laufen zusammen in einem nativen
Fenster, zusammengehalten von **PyWebView**. Sie reden über die `js_api`-Brücke
(JSON rein, JSON raus).

```
┌───────────────────────────── PyWebView-Fenster (WebView2) ─────────────────────────────┐
│  FRONTEND  (frontend/)                          │  BACKEND  (backend/, main.py)          │
│  index.html · style.css · app.js                │  api.py  (js_api-Klasse)               │
│  - rendert die komplette Oberfläche             │  db.py   (SQLite-Schema, CRUD)         │
│  - hält KEINE Wahrheit, nur Anzeige + Eingabe   │  graph_sync.py (MS Graph → SQLite)     │
│                                                 │  auth.py (MSAL PKCE, keyring)          │
│        ── pywebview.api.methode(args) ──▶       │  notify.py (winotify)                  │
│        ◀──────── JSON-Antwort ─────────         │  security.py (Sperre/Verschlüsselung)  │
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
> Bridge-Verträge (B.2) und das Backend (Phasen 1-4, 8-10) bleiben gleich. Default
> dieses Plans = Vanilla.

---

## TEIL B: Die Verträge (für alle Bausteine verbindlich)

### B.1 Datenmodell (SQLite)

Drei Tabellen. IDs sind Strings (lokale IDs `l…`/`t…` per `uuid`/Zeitstempel,
importierte tragen die stabile Microsoft-Graph-`id`).

```sql
-- Liste
CREATE TABLE lists (
  id          TEXT PRIMARY KEY,         -- lokal: 'l'+uuid; importiert: graph list id
  name        TEXT NOT NULL,
  synced      INTEGER NOT NULL DEFAULT 0,  -- 1 = aus MS To Do importiert, 0 = lokal
  position    INTEGER NOT NULL DEFAULT 0,  -- Sortierreihenfolge in der Sidebar
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- Aufgabe
CREATE TABLE tasks (
  id          TEXT PRIMARY KEY,         -- lokal: 't'+uuid; importiert: graph task id
  list_id     TEXT NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  meta        TEXT,                     -- freie Zusatzzeile (z.B. Autor) oder NULL
  done        INTEGER NOT NULL DEFAULT 0,
  position    INTEGER NOT NULL DEFAULT 0,
  source      TEXT NOT NULL DEFAULT 'local',  -- 'local' | 'graph'
  graph_etag  TEXT,                     -- für Delta-/Konflikterkennung bei Import
  due_at      TEXT,                     -- optional, für Erinnerungen
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

-- Sync-Zustand (ein Eintrag pro Liste): Delta-Link für inkrementellen Sync
CREATE TABLE sync_state (
  list_id     TEXT PRIMARY KEY REFERENCES lists(id) ON DELETE CASCADE,
  delta_link  TEXT,
  last_sync   TEXT
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
- `list.synced` steuert das Badge „synced from MS To Do" vs. „local only".

### B.2 Bridge-API (`pywebview.api.*`): der Vertrag zwischen vorne und hinten

Das ist die **vollständige Methodenliste**, die `backend/api.py` bereitstellt und die
`frontend/app.js` aufruft. Jede gibt JSON-serialisierbare Werte zurück (Promise im JS).

| Methode | Argumente | Rückgabe | Zweck |
|---|---|---|---|
| `get_state()` | (keine) | `{ lists:[…], settings:{…}, online:bool, locked:bool }` | Initialer Gesamtzustand beim App-Start |
| `get_lists()` | (keine) | `[ { id, name, synced, open:[task], done:[task] } ]` | Alle Listen mit eingebetteten Aufgaben |
| `add_list(name)` | `str` | `{ id, name, … }` | Neue lokale Liste |
| `rename_list(id, name)` | `str,str` | `{ ok:true }` | Liste umbenennen |
| `delete_list(id)` | `str` | `{ ok:true }` | Lokale Liste + Aufgaben löschen (synced kommen beim nächsten Sync zurück) |
| `undo_delete_list(id)` | `str` | `{ ok:true }` | Letzte Listen-Löschung rückgängig machen (Undo-Toast; ab Phase 7, siehe Phase 6.5) |
| `add_task(list_id, text, meta?)` | `str,str,str?` | `{ …task }` | Neue lokale Aufgabe |
| `toggle_task(id)` | `str` | `{ id, done:bool }` | Erledigt-Status umschalten |
| `edit_task(id, fields)` | `str,obj` | `{ …task }` | Text/Meta/Fälligkeit ändern |
| `delete_task(id)` | `str` | `{ ok:true }` | Aufgabe löschen |
| `reorder(list_id, ordered_ids)` | `str,[str]` | `{ ok:true }` | Drag-&-Drop-Reihenfolge speichern |
| `export_list(id, format)` | `str,'md'\|'txt'\|'json'` | `{ filename, content }` | Liste exportieren |
| `copy_task(id)` | `str` | `{ ok, clears_in }` | EINE ausgewählte Aufgabe gehärtet ins Clipboard (Backend-seitig, keine Win+V-History, kein Cloud-Clipboard, Auto-Clear nach 60 s; ersetzt das frühere `copy_list`, ganze Listen kopiert man bewusst nicht mehr, dafür gibt es den Export) |
| `set_setting(key, value)` | `str,*` | `{ ok:true }` | Eine Einstellung speichern |
| `get_status()` | (keine) | `{ db, encryption, graph, last_sync, runtime }` | Daten für das „App status"-Modal |
| `sign_in()` | (keine) | `{ ok, account }` | MSAL-Login starten |
| `sign_out()` | (keine) | `{ ok:true }` | Tokens verwerfen |
| `sync_now()` | (keine) | `{ changed:int, lists:int }` | Sofort-Sync gegen MS Graph |
| `set_online(flag)` | `bool` | `{ online:bool }` | „Flugmodus"/Online umschalten (pausiert Sync) |
| `lock()` | (keine) | `{ locked:true }` | App sperren |
| `unlock(passphrase)` | `str` | `{ ok:bool }` | Entsperren |
| `panic()` | (keine) | `{ locked:true }` | Emergency: sperren + Cache leeren + offline |

**Ereignisse Backend → Frontend** (PyWebView kann JS auswärts aufrufen, z.B.
`window.evaluate_js` oder ein Event-Bus): `on_sync_done(summary)`,
`on_notification(payload)`, `on_locked()`. Das Frontend registriert dafür globale
Funktionen `window.noa.onSyncDone` usw.

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
│ • Ideas   3  │  5 open · 3 done · ↯ synced from MS To Do │  ⬆ Export     │
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
- Rechts: Glocke mit roter Zahl-Badge (öffnet **Benachrichtigungs-Menü**), Avatar
  „NA" (öffnet **Profil-Menü**).

**Sidebar** (`renderSidebar`)
- Mono-Label „LISTS" mit Trennlinie.
- Scrollbare Liste der `list-item`: kleiner Punkt, Name, Mono-Zähler (Anzahl offener
  Aufgaben). Aktive Liste: Akzent-Wash-Hintergrund + Akzent-Balken links + Punkt/Zähler
  in Akzentfarbe. Listen mit Zähler 0 zeigen den Zähler blasser.
- Fuß: „**+ New list**" (gestrichelter Akzent-Button; Klick öffnet ein Inline-
  Eingabefeld, Enter = anlegen, Esc/Blur = abbrechen) und „**⚙ Settings**".

**Main** (`renderMain` / `renderTaskView`)
- Banner-Zeile rechtsbündig: **Flugmodus/Online-Pill** (Icon Plane bei offline,
  Globe bei online; Klick schaltet um, siehe `set_online`).
- Großer Listentitel (32px).
- Meta-Zeile (Mono-Tags): „X open", Punkt, „Y done", Punkt, Status-Tag
  „↯ synced from MS To Do" (grün) oder „✦ local only" (blass).
- Abschnitt **OPEN TASKS**: Section-Head (Mono-Titel + Zähler + Linie), darunter die
  Aufgaben-Karten. Ist nichts offen: Mono-Hinweis „// nothing open, you're all caught up".
- **New-task-Eingabe**: gestrichelte Akzent-Karte mit Plus, Platzhalter „New task…",
  Enter legt an, `[↵]`-Kbd rechts.
- Abschnitt **COMPLETED** (nur wenn es erledigte gibt): einklappbarer Section-Head
  (Chevron dreht), animiertes Auf-/Zuklappen, darunter die erledigten Aufgaben.

**Aufgaben-Karte** (`renderTask`)
- Runder Check-Button (Klick → `toggle_task`). Text. Optional Mono-Meta rechts (z.B.
  Autor), nur bei offenen Aufgaben. Drag-Griff, der bei Hover erscheint.
- Erledigt: transparenter Hintergrund, gestrichelter Rand, Text durchgestrichen +
  blass, Check in Grün gefüllt.

**Rechte Toolbar** (`renderToolbar`), vertikale Leiste, zwei Modi über
`data-toolbar`: `flush` (bündig an der Kante) oder `floating` (schwebende, gerundete
Karte, Standard). Buttons mit Tooltip + Hotkey, in Gruppen durch Trenner:
1. **Focus mode** (⤢, `F`), blendet Sidebar+Toolbar aus, nur eine „Exit focus"-X bleibt.
2. **Accent color** (🎨), öffnet Swatch-Popover mit den 6 Akzenten.
3. **Export** (⬆, `Ctrl+E`).
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
- **NotifMenu**, Dropdown unter der Glocke: Liste von Benachrichtigungen (Titel,
  Mono-Unterzeile, farbiger Punkt). Beispiele: „Reminder: …", „Sync complete",
  „Backup written".
- **ProfileMenu**, Dropdown unter dem Avatar: Kopf mit Avatar + Name + „signed in ·
  local"; Einträge Account, Privacy & data, Export database, Sign out.
- **EmergencyModal**, roter Streifen oben, Warn-Icon, Titel „Panic, lock everything?",
  Erklärtext (sperrt sofort, leert Cache, DB offline, nichts wird gelöscht), Buttons
  Cancel / „Lock now" (rot).
- **StatusModal**, Diagnose-Zeilen: Local database (Größe), Encryption (AES-256 +
  ChaCha20 · Argon2id), Microsoft Graph (Tasks.Read · Token / offline), Last sync, WebView2 runtime,
  jeweils mit grünem/blassem Status-Tag. Daten kommen aus `get_status()`.
- **RenameModal**, Eingabefeld (vorbelegt, fokussiert+selektiert), Enter/Save.
- **DeleteModal**, Bestätigung „Delete „Name"?" mit Hinweis, dass synchronisierte
  Listen beim nächsten Sync zurückkommen.
- **ShortcutsModal**, Raster aller Tastenkürzel (siehe B.5).
- **LockScreen**, Vollbild über allem: Akzent-Ring mit Schloss, „NoaToDo is locked",
  Mono-Zeile „LOCAL VAULT · ENCRYPTED · OFFLINE", 4 Punkte, Button. (Im echten Build:
  Passphrase-Eingabe statt der 4 Demo-Taps.)
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

`accent` (Hex), `dark` (bool), `toolbar` (`floating`|`flush`), `density`
(`comfortable`|`compact`), `sidebar` (`open`|`closed`). Werden beim Start aus
`get_state()` gelesen und auf das `.app`-Element als `data-*`/`--accent` gesetzt;
Änderungen sofort via `set_setting` zurückschreiben.

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

**Punkt 4, Microsoft-Tokens getrennt davon: keyring.**
Die Zugangs-Tokens für Microsoft liegen nicht in der DB, sondern im **Windows Credential
Manager** (über `keyring`), ans Benutzerkonto gebunden.

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
> beim DB-Öffnen) und Phase 11 (Argon2, Schicht 2 / Wrap-Unwrap, Lock, Panic).

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
| Klick auf **Lock**-Button (oder `Ctrl+L`) | sofort sperren |
| **Emergency/Panic** (`Ctrl+Shift+!`) | sofort sperren + Cache leeren + offline |
| **Windows-Sperre** (Win+L) bzw. Sitzung gesperrt | App sperrt automatisch mit → bei Rückkehr Passphrase nötig |
| **App-Neustart** (Prozess war beendet) | startet immer im Lock-Screen |
| **Auto-Sperre nach Inaktivität** *(empfohlen, Timeout einstellbar, Default z. B. 15 min)* | sperren |

**Ausdrücklich KEINE Sperre** bei:
- **Minimieren** und wieder Öffnen des App-Fensters,
- Fokus-Wechsel zu einer anderen App (App nur im Hintergrund),
- Verschieben/Größe ändern des Fensters.

> Kernregel: Eine Sperre passiert nur bei **explizitem Sperren**, bei **Windows-
> Sitzungssperre** und bei **echtem Prozess-Neustart**. Reines Fenster-Minimieren ist
> *kein* Sicherheitsereignis und lässt die App entsperrt.

**Technische Umsetzung der Windows-Sperre-Erkennung (Phase 11):** Beim Sitzungswechsel
horchen, über `WTSRegisterSessionNotification` auf das App-Fensterhandle und das
`WM_WTSSESSION_CHANGE`-Ereignis (via `ctypes` oder `pywin32`/`win32ts`). Bei
`WTS_SESSION_LOCK` (Windows wurde gesperrt) → `lock()` aufrufen. Damit ist die App beim
Zurückkommen aus der Windows-Anmeldung garantiert gesperrt.

### B.9 Eingabe-Sicherheit: Schutz vor bösartigem Sync-Inhalt (verbindlich)

> ## ⚠️ SICHERHEITS-HÄRTUNG, STAND & OFFENE PFLICHT-GATES
>
> Aus dem Security-Review (2026-06-08) ergab sich eine klare Trennung in
> „sofort erledigt" und „muss in der jeweiligen Phase erledigt werden".
> **Diese Liste ist verbindlich. Die offenen Punkte sind Gates: Die jeweilige
> Phase gilt erst als fertig, wenn ihr Sicherheitspunkt umgesetzt ist.**
>
> **✅ Bereits erledigt (im Code, vor dem Sync):**
> - **CSP gesetzt** in `frontend/index.html` (Regel 2), strenger als das Minimum
>   (zusätzlich `connect-src 'self'`, `object-src/base-uri/form-action/frame-ancestors 'none'`).
> - **`esc()` gehärtet** in `frontend/app.js`, maskiert jetzt auch `'` (einfach-
>   gequotete Attribute), nicht nur `& < > "`.
>
> **🔒 OFFENE PFLICHT-GATES (NICHT vergessen, pro Phase abhaken):**
>
> | Gate | Phase | Punkt |
> |---|---|---|
> | **G1** | **9 (VOR dem ersten Render von Sync-Daten!)** | Vollständige **`textContent`/`createTextNode`-Umstellung** aller Fremddaten-Renderpfade (Regel 1, Buchstabe). Solange noch `innerHTML` benutzt wird, sind CSP + `esc()` die einzige Absicherung. |
> | **G2** | **9** | **`nextLink`/`deltaLink` Host-Whitelist**: nur Folge-URLs auf `graph.microsoft.com` mit dem Bearer-Token abrufen. Sonst Token-Leak. |
> | **G3** | **9** | **httpx-Timeouts + Limits** (max. Seitenzahl, Feld-Trunkierung nach Regel 4, Mengen-Cap) gegen DoS/Ressourcen-Erschöpfung. |
> | **G4** | **9** | **Schreib-Lock** um alle DB-Writes des Sync-Hintergrund-Threads (Korruptionsschutz, da `check_same_thread=False`). |
> | **G5** | **8** | **OAuth-Härtung**: `state`-Parameter validieren, PKCE-Verifier binden, Loopback-Listener nur an `127.0.0.1`, genau **einen** Request annehmen, danach schließen. **Kein** Client-Secret. Tokens **nie** ins Frontend, **nie** loggen. |
> | **G6** | **11** | **In-Memory-DB** (`:memory:`) statt entschlüsselter Temp-Arbeitskopie, siehe B.7 „Alternative für Puristen". Eliminiert Temp-Datei-Forensik (Secure-Delete auf SSD ist unzuverlässig). |
> | **G7** | **11** | **Roher Hex-Schlüssel** für `PRAGMA key = "x'<64 hex>'"` statt String-Interpolation (`db.py`), damit SQLCipher kein eigenes PBKDF2 über den schon abgeleiteten Key legt. |
> | **G8** | **11** | **Starke Argon2id-Parameter** (Memory ≥ 256-512 MB, time_cost ≥ 3) **und erzwungene Passphrase-Stärke**, die Passphrase ist der einzige reale Schwachpunkt (Offline-Brute-Force). |
> | **🔴 G9** | **11** | **`DEV_AES_KEY` & jeden statischen Schlüssel-Default ersatzlos entfernen.** Es darf **keinen** Code-Pfad geben, der die DB ohne passphrase-abgeleiteten Schlüssel öffnet. Sonst öffnet die „verschlüsselte" DB mit einem öffentlich im Quellcode stehenden String → **effektiv null Verschlüsselung**, während der Status fälschlich „AES-256 + ChaCha20" meldet. Wichtigstes Gate der Phase 11. |
> | **G10** | **8/9** | **Fehlermeldungen ohne Geheimnisse.** Der `bridge`-Dekorator gibt aktuell `str(exc)` ans Frontend (Toast). Für Auth-/Sync-Methoden generische Fehlercodes liefern; Details nur serverseitig loggen, und im Log **keine** Tokens, Delta-Links/Skiptoken, Pfade. |
> | **G11** | **0 / laufend** | **Abhängigkeiten pinnen.** `requirements.txt` listet alles ohne Version. Versionen festnageln, idealerweise mit `pip` Hash-Checking, eine getauschte Lib = Totalkompromittierung der Tresor-App. |
> | **G12** | **3/11** | **WebView-Navigation abriegeln.** Navigations-/New-Window-Events in PyWebView abfangen und jede **externe** Navigation (`window.location`/`window.open` zu externem `http`) verweigern. Die App ist rein lokal und navigiert nie woandershin. |
>
> **Zwei Kleinigkeiten (Hinweis, kein Gate):**
> - **Export/Clipboard:** `export_list` schreibt **unverschlüsselte** Dateien (by
>   design, der Nutzer exportiert bewusst Klartext). Das Kopieren ist seit dem
>   Nachtrag gehärtet und auf eine einzelne Aufgabe begrenzt, siehe G23.
> - **`main.py` `emit()`:** `json.dumps(payload)` muss `ensure_ascii=True` (Default)
>   behalten, sonst können U+2028/U+2029 in Sync-/Notif-Daten den `evaluate_js`-Aufruf
>   brechen. Notif-Payloads mit Task-Titeln hängen zusätzlich an **G1** (textContent).
>
> Diese Gates werden weiter unten in den Phasen 8, 9 und 11 **nochmals
> einzeln** wiederholt. Das ist Absicht, sie dürfen nicht übersehen werden.

> ## 🔒 NACHTRAG: Gates G13 bis G25 (Code-Audit + Testlauf vom 2026-06-10)
>
> Ein vollständiges Code-Audit (Code-Review aller Module plus 23 automatisierte
> Checks gegen die echte Bridge-API auf einer Wegwerf-DB) hat weitere
> Pflichtpunkte ergeben. **Alle folgenden Gates sind verbindlich und vom Nutzer
> bestätigt. KEINER dieser Punkte ist optional, jeder MUSS in der genannten
> Phase umgesetzt werden.** Sie gelten zusätzlich zu G1 bis G12 und werden in
> den Phasen 7, 9 und 11 nochmals einzeln wiederholt.
>
> | Gate | Phase | Punkt |
> |---|---|---|
> | **🔴 G13** | **11** | **Serverseitige Lock-Durchsetzung.** Die Sperre existiert heute nur als Frontend-Overlay: Im Audit wurde nachgewiesen, dass nach `lock()` Aufrufe wie `add_task()` und `get_state()` weiterhin funktionieren und alle Daten liefern (ein einziger JS-Aufruf umgeht den Lock-Screen). Pflicht: Ein zentraler Check im `bridge`-Decorator prüft `self.locked`; ist die App gesperrt, gibt **jede** Methode ausser `unlock(passphrase)` sofort `{"error": "locked"}` zurück, ohne die DB zu berühren. `get_state()` liefert im gesperrten Zustand nur `{"locked": true}` ohne Listen/Settings. |
> | **G14** | **3 (sofort vorsehen) / 11 (hart)** | **Keine WebView2-Datenspuren auf der Platte.** WebView2 legt einen User-Data-Ordner an (Cache, localStorage, GPU-Cache); dort können gerenderte Task-Texte an beiden Verschlüsselungsschichten vorbei landen. Pflicht: `webview.start(..., private_mode=True)` **explizit** setzen (nicht auf den Default verlassen) und verifizieren, dass die Runtime wirklich InPrivate läuft. Legt die Runtime trotzdem einen User-Data-Ordner an: Pfad explizit nach `data/webview2/` legen und beim Sperren/Panic/Beenden löschen. Das Frontend darf localStorage/sessionStorage/IndexedDB **nie** für Aufgabendaten verwenden. |
> | **G15** | **11** | **Schlüsselableitung mit Domain-Separation, KEIN gespeicherter Verifikations-Hash.** Argon2id erzeugt aus Passphrase + Salt **ein** 32-Byte-Master-Secret; daraus per HKDF-SHA256 mit getrennten `info`-Labels (`b"noatodo/aes-v1"`, `b"noatodo/chacha-v1"`) `aes_key` und `chacha_key` ableiten. Es wird **kein** Argon2-Hash der Passphrase gespeichert: Die Prüfung beim Entsperren ist der Erfolg oder Misserfolg der ChaCha20-Poly1305-Entschlüsselung (der Poly1305-Tag verifiziert die Passphrase implizit; falsche Passphrase = AEAD-Exception = Meldung "Passphrase falsch"). So liegt kein zusätzliches Orakel-Material für Offline-Angreifer auf der Platte. Ersetzt die ältere Formulierung in B.7 ("Argon2-Hash zum Prüfen speichern", "Teilstücke des KDF-Outputs"). |
> | **G16** | **11** | **Dateiformat von `tasks.db.enc` + atomares Schreiben.** Header: Magic `NOA1` (4 Byte), Formatversion (1 Byte), Argon2id-Parameter `memory_cost`/`time_cost`/`parallelism` (je u32 little-endian), Salt (16 Byte), Nonce (12 Byte); danach der ChaCha20-Poly1305-Ciphertext. Bei **jedem** Verschlüsseln eine frische Nonce aus `os.urandom(12)`; eine wiederverwendete Nonce bricht die AEAD-Sicherheit vollständig. Schreiben **immer** atomar: erst `tasks.db.enc.tmp` schreiben, `flush()` + `os.fsync()`, bestehende Datei nach `tasks.db.enc.bak` rotieren (genau eine Generation behalten), dann `os.replace()`. Ein Absturz mitten im Sperren darf nie die einzige Kopie der Daten zerstören. |
> | **G17** | **11** | **Write-back-Politik für die In-Memory-DB** (Ergänzung zu G6). Nach jeder mutierenden Bridge-Operation wird die In-Memory-DB debounced persistiert (z.B. 3 s nach der letzten Änderung; zusätzlich **sofort** bei Lock/Panic/Quit), als neues `tasks.db.enc` nach dem Verfahren aus G16. Ein Crash kostet damit höchstens die letzten Sekunden, nie den Tagesstand. |
> | **G18** | **11** | **DPAPI-Pepper gegen Offline-Brute-Force (Pflicht).** Beim Einrichten der Passphrase wird zusätzlich ein zufälliger 32-Byte-Pepper erzeugt und über `keyring` im Windows Credential Manager (DPAPI, ans Windows-Konto gebunden) abgelegt. Der Pepper fliesst zusätzlich zur Passphrase in die Ableitung ein (Argon2id-`secret`-Parameter). Wirkung: Wer nur die Datei `tasks.db.enc` erbeutet (Backup, Cloud-Ordner, ausgebaute SSD), kann offline **gar nicht** raten, ihm fehlt der Pepper aus dem Windows-Konto. Pflichtbestandteil des Einrichtungs-Flows: ein Recovery-Export des Peppers (Datei oder anzeigbarer Code), den der Nutzer getrennt sichern muss; ohne Windows-Profil und ohne Recovery-Export wäre die DB sonst unwiederbringlich verloren. |
> | **G19** | **11 (Umsetzung darf vorgezogen werden)** | **Single-Instance-Schutz.** Beim Start einen benannten Windows-Mutex belegen (`ctypes.windll.kernel32.CreateMutexW(None, False, "Local\\NoaToDoSingleton")`, danach `GetLastError() == ERROR_ALREADY_EXISTS (183)` prüfen). Läuft schon eine Instanz: Hinweis zeigen und den zweiten Prozess sofort beenden. Zwei Instanzen würden sich `tasks.db.enc` bzw. die Arbeitskopie gegenseitig überschreiben (Korruption/Datenverlust). |
> | **G20** | **7** | **Regel-4-Validierung auch für LOKALE Eingaben + Typ-/Key-Prüfung an der Bridge.** Audit-Befunde: ein 1-MB-Tasktext und Steuerzeichen wie U+0000 werden heute anstandslos gespeichert; `reorder(list_id, "string")` iteriert den String zeichenweise und liefert `{"ok": true}`; `set_setting` akzeptiert beliebige Keys. Pflicht in `api.py`: (a) `add_task`/`edit_task`: Text max. 4096 Zeichen, `meta` max. 256; `add_list`/`rename_list`: Name max. 256; Überlänge abschneiden; Steuerzeichen U+0000-U+001F (ausser `\n` und `\t`) vor dem Schreiben strippen. (b) `reorder` lehnt ab, wenn `ordered_ids` keine Liste von Strings ist. (c) `set_setting` akzeptiert nur Keys aus einer Whitelist (`accent`, `dark`, `toolbar`, `density`, `sidebar`, `railPinned`, `sidebarWidth` plus künftig dort dokumentierte), sonst `{"error": "invalid"}`. |
> | **G21** | **7** | **Export-Härtung.** Audit-Befunde: eine Liste namens `CON` exportiert als `CON.md` (reservierter Windows-Gerätename), und Zeilenumbrüche im Task-Text brechen die Markdown-Struktur des Exports (eingeschleuste falsche `- [x]`-Zeilen/Überschriften). Pflicht in `export_list`: (a) Dateiname: reservierte Namen (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9; case-insensitive, auch mit Endung) mit `_`-Präfix entschärfen; führende/abschliessende Punkte und Leerzeichen entfernen; bleibt nichts übrig, Fallback `list`. (b) Inhalt: in md/txt jede Aufgabe einzeilig ausgeben, `\r` und `\n` in Text/Meta durch ein Leerzeichen ersetzen. (c) Echten Save-Dialog umsetzen (`window.create_file_dialog(webview.SAVE_DIALOG, save_filename=...)`) und die Datei wirklich schreiben. Stand heute schreibt der Export **keine** Datei, das Frontend zeigt nur einen Toast. |
> | **G22** | **SOFORT, spätestens mit 7** | **Ehrlicher `get_status()`.** Bis Phase 11 fertig ist, **muss** `get_status()` den realen Zustand melden: Schicht 1 "SQLCipher mit Entwicklungs-Schlüssel (UNSICHER)", Schicht 2 "nicht implementiert", `active: false`; das Status-Modal zeigt das in Warnfarben statt grün. Eine Tresor-App darf nie eine Verschlüsselung anzeigen, die nicht existiert (aktuell meldet der Status "AES-256 + ChaCha20 · active", während der AES-Key öffentlich im Repo steht; im Audit nachgewiesen). Ab Phase 11 zeigt der Status echte Werte (Argon2-Parameter, Pepper vorhanden ja/nein, Zeitpunkt des letzten Wraps). |
> | **G23** | **✅ umgesetzt 2026-06-10** | **Clipboard-Hygiene + Einzel-Task-Kopie.** Windows speichert das Clipboard in der Zwischenablage-History (Win+V) und synchronisiert es ggf. ins Microsoft-Cloud-Clipboard, App-Inhalte würden so den Rechner verlassen. Umgesetzt: (a) Kopiert wird nur noch **eine ausgewählte Aufgabe** (`copy_task`), nie eine ganze Liste; für Listen gibt es den Export. (b) Das Kopieren passiert komplett im **Backend** (`api.py`, Win32 per ctypes, nicht `navigator.clipboard`) und setzt zusätzlich zu `CF_UNICODETEXT` die Formate `ExcludeClipboardContentFromMonitorProcessing`, `CanIncludeInClipboardHistory` (=0) und `CanUploadToCloudClipboard` (=0). (c) Auto-Clear: 60 s nach dem Kopieren wird das Clipboard geleert, sofern es noch unseren Inhalt trägt. (d) Der `Strg+C`-App-Shortcut wurde ersatzlos entfernt. Bei künftigen Copy-Funktionen MUSS derselbe Backend-Pfad verwendet werden. |
> | **G26** | **❌ verworfen 2026-06-20 (zu fehleranfaellig)** | **Screenshot-Schutz (entfernt).** Idee war, das Fenster per `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` aus Bildschirmaufnahmen herauszunehmen. Mehrfach umgesetzt und wieder entfernt, weil er reale Probleme machte: auf manchen GPU-/Treiber-Konstellationen blockiert die Affinity das WebView2-Rendern komplett (Fenster bleibt weiss / reagiert nicht), und die Startup-Verdrahtung verklemmte zudem die Nachrichtenschleife. Zusatznachteile: blendet das Fenster auch in legitimer Freigabe/Aufnahme schwarz aus und nuetzt nichts gegen eine Kamera. **Entscheidung: dauerhaft entfernt, nicht wieder einbauen.** Falls je erneut gewuenscht, zwingend mit Render-Verifikation nach dem Setzen (Affinity automatisch zuruecknehmen, wenn der Inhalt nicht mehr rendert) und ausschliesslich ueber `_run_on_ui_thread`. |
> | **G24** | **9 (VOR dem ersten Sync)** | **Seed-Daten-Kollision auflösen.** Die Seeds markieren Listen als `synced=1`/`source='graph'`, tragen aber lokale UUIDs statt echter Graph-IDs. Beim ersten echten Sync entstünden Duplikate und "Geisterlisten", die nie Updates bekommen. Pflicht: Beim ersten erfolgreichen `sign_in()` eine Migration ausführen: alle Listen mit `synced=1`, deren ID mit `l` beginnt (= Seed, nicht Graph), samt Aufgaben auf `synced=0`/`source='local'` umstellen. Danach existieren keine Pseudo-Sync-Listen mehr. |
> | **G25** | **11** | **RAM-Schlüssel-Hygiene.** `aes_key`, `chacha_key`, Master-Secret und Pepper als `bytearray` (nicht `bytes`/`str`) halten; beim Sperren/Panic/Beenden **vor** dem Verwerfen mit Nullen überschreiben. Die Passphrase unmittelbar nach der Ableitung verwerfen; Passphrase und Schlüssel dürfen **nie** in Logs, Exceptions, `get_status()` oder sonstwie ans Frontend gelangen. Im Code dokumentieren: Python gibt keine harten Garantien (der GC kann Kopien hinterlassen), das Nullen ist Best-Effort und trotzdem Pflicht. |
>
> **Zusätzlich vorgezogen:** G12 (externe WebView-Navigation verweigern) ist mit
> wenigen Zeilen umsetzbar und wird **vor** Phase 7 umgesetzt, nicht erst in
> Phase 11. Ebenso G22 (ehrlicher Status), siehe Tabelle.

Der One-Way-Sync (Cloud → lokal) ist die **größte Angriffsfläche** der App: Ein
Angreifer, der Kontrolle über das Microsoft-Konto hat (oder über eine geteilte Liste
Inhalte einschleust), kann beliebigen Text in Task-Felder schreiben. Dieser Text
landet über `graph_sync.py` in der lokalen DB und wird vom Frontend gerendert.

**Alle Daten, die aus der Microsoft Graph API stammen, gelten als _untrusted input_.**
Dasselbe gilt für jede andere externe Quelle. Folgende Regeln sind Pflicht:

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
(Daten-Exfiltration) oder `sign_out()` aufrufen.

> **🔒 STATUS / GATE G1 (Phase 9):** Die aktuelle `app.js` rendert über
> `root.innerHTML = …` mit `esc()` an jeder Einsetzstelle, das **widerspricht dem
> Buchstaben dieser Regel**. Solange noch **keine** Sync-Daten gerendert werden
> (nur eigene Eingaben = höchstens Self-XSS, keine reale Bedrohung) und CSP +
> gehärtetes `esc()` aktiv sind, ist das tolerierbar. **ABER: Bevor `graph_sync.py`
> (Phase 9) zum ersten Mal Fremddaten anzeigt, MÜSSEN alle Fremddaten-Renderpfade
> (Task-Text, Meta, Listenname, Toast, Notif) auf `textContent`/`createTextNode`
> umgestellt werden.** Dieses Gate ist nicht optional, es ist genau der Tunnel,
> durch den die fremden Daten laufen werden.
>
> **Begründung der Zeitplanung (warum G1 ein Phase-9-Gate ist und nicht „sofort"):**
> Die volle `textContent`-Umstellung (Regel 1, Buchstabe) war im ersten Security-Review
> als „jetzt"-Punkt gelistet. Die Zeitplanung wurde bewusst geändert auf „Gate G1,
> zwingend vor Phase 9". Gründe:
> - **Es fließt aktuell keine Fremddatenquelle.** Bis Phase 9 sind die einzigen
>   renderbaren Daten eigene Eingaben → höchstens Self-XSS, keine reale Bedrohung.
> - **CSP + gehärtetes `esc()` decken das jetzige Risiko vollständig.** Der Exploit-Pfad
>   (Inline-Handler) ist durch die CSP tot.
> - **Während aktiv kosmetisch an `app.js` gearbeitet wird,** würde ein
>   840-Zeilen-Render-Umbau auf DOM-API mit dieser Arbeit kollidieren und Bruchrisiko
>   schaffen, ohne heutigen Sicherheitsgewinn.
> - **Deshalb:** G1 ist ein hartes Gate, das exakt dann fällig ist, wenn der untrusted
>   Kanal (Sync) aktiviert wird, „erst G1, dann Sync".

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

**Alle** SQL-Statements in `backend/db.py` und `backend/graph_sync.py` verwenden
ausschließlich parametrisierte Queries mit `?`-Platzhaltern. Keine String-Formatierung,
kein f-String, kein `.format()` für Werte, **ausnahmslos**:

```python
# ✅ Sicher: Wert wird als Daten behandelt, nie als SQL
cursor.execute("INSERT INTO tasks (id, text) VALUES (?, ?)", (task_id, task_text))

# ❌ Verboten: öffnet SQL Injection
cursor.execute(f"INSERT INTO tasks (id, text) VALUES ('{task_id}', '{task_text}')")
```

#### Regel 4: Längen- und Zeichenvalidierung beim Sync

`graph_sync.py` validiert importierte Daten vor dem Schreiben:

- **Maximale Textlänge** pro Feld (z.B. Task-Text ≤ 4096 Zeichen, Listenname ≤ 256).
  Überlange Werte werden abgeschnitten und ein Warnhinweis geloggt.
- **Steuerzeichen** (U+0000-U+001F außer Newline/Tab) werden entfernt.

#### Regel 5: Zukunftssicherung (Prompt Injection)

Falls in späteren Versionen KI-Features hinzukommen (Zusammenfassung, Priorisierung),
darf **kein** importierter Task-Text direkt in einen System-Prompt eingesetzt werden.
Cloud-importierte Inhalte müssen in einem separaten, klar abgegrenzten User-Kontext
an das Sprachmodell übergeben werden.

> **Auswirkung auf die Funktionalität: Null.** Alle fünf Regeln sind rein defensiv.
> Task-Texte werden exakt gleich angezeigt, die App verhält sich identisch, nur dass
> bösartiger Inhalt wirkungslos bleibt. Es ist wie das Schloss an der Tür: die Tür
> funktioniert genauso, aber ungebetene Gäste kommen nicht rein.

---

## TEIL C: Baufolge (Phase 0 bis 11)

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
   │   ├── graph_sync.py
   │   ├── auth.py
   │   ├── notify.py
   │   └── security.py
   ├── frontend/
   │   ├── index.html
   │   ├── style.css
   │   ├── app.js
   │   └── fonts/            # JetBrains Mono + Space Grotesk als .woff2
   └── data/                 # tasks.db entsteht hier automatisch
   ```
2. `requirements.txt`: `pywebview`, `httpx`, `msal`, `keyring`, `winotify`,
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

**Ziel:** SQLite-Schema steht, CRUD-Funktionen existieren, Seed-Daten lassen sich laden.

> **Wichtig:** Die Datenbank ist von Anfang an **verschlüsselt** (Doppel-Kaskade, B.7).
> In dieser Phase wird nur **Schicht 1** (SQLCipher/AES-256) gebaut; die äußere
> ChaCha20-Schicht und das echte Passphrase-Handling kommen in Phase 11 dazu. In der
> Entwicklung darf man mit einer festen Test-Passphrase / einem festen Test-`aes_key`
> arbeiten.

**Tun:**
1. `connect(aes_key)`, öffnet die SQLCipher-Arbeitskopie, setzt direkt nach dem Öffnen
   `PRAGMA key = ?` (der abgeleitete `aes_key`), dann `PRAGMA foreign_keys = ON`, und
   legt das Schema aus B.1 an, falls noch nicht vorhanden (`CREATE TABLE IF NOT EXISTS`).
   Ohne korrekten Key schlägt der erste Zugriff fehl, genau so soll es sein.
2. Funktionen: `get_lists_with_tasks()`, `add_list`, `rename_list`, `delete_list`,
   `add_task`, `toggle_task`, `edit_task`, `delete_task`, `reorder`,
   `get_setting/set_setting`, `upsert_graph_task` (für den Sync, Phase 9).
3. `get_lists_with_tasks()` liefert genau die Struktur aus B.1 (Liste mit `open`/`done`,
   sortiert nach `position`).
4. **Seed-Daten** beim allerersten Start einspielen (nur wenn Tabellen leer): die Listen
   und Aufgaben aus dem Konzept (`Reading List`, `Ideas`, `Homework`, `Programming`,
   `Travel`, `Life Goals`) als realistische Startfüllung. Liste der Seed-Inhalte siehe
   **Anhang 1**.
5. Alle `*_at`-Felder als ISO-8601-UTC-Strings.

**Abnahme:** Ein kleines Testskript legt eine Liste + Aufgabe an, schaltet sie auf
erledigt und liest sie korrekt einsortiert (`done`) wieder aus.

---

### Phase 2: Bridge-API (`backend/api.py`)

**Ziel:** Die `js_api`-Klasse mit allen Methoden aus B.2, vorerst rein lokal (ohne
Microsoft/Notifications), liefert echte Daten aus der DB.

**Tun:**
1. Klasse `Api` mit je einer Methode pro Zeile in B.2. Methoden rufen `db.py` auf und
   geben JSON-fähige Dicts/Listen zurück.
2. Fehler abfangen und als `{ "error": code, "message": … }` zurückgeben.
3. `get_state()` bündelt `get_lists()` + Einstellungen + `online`/`locked`-Flags.
4. Microsoft-/Sicherheits-Methoden vorerst als Stubs (geben sinnvolle Platzhalter
   zurück), werden in Phasen 8-11 ausgefüllt.

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
   ausführt (für Sync-/Notification-Events).
4. Platzhalter für den **Windows-Sitzungssperre-Hook** vorsehen (Registrierung des
   Fensterhandles für `WM_WTSSESSION_CHANGE`); echte Logik kommt in Phase 11/B.8.

> **🔒 PFLICHT-GATE G12 (WebView-Navigation abriegeln):** Die App ist rein lokal und
> darf das Fenster **nie** woandershin navigieren. Navigations-/New-Window-Events von
> PyWebView/WebView2 abfangen und jede **externe** Navigation (`window.location`/
> `window.open`/Link zu externem `http(s)`) verweigern, nur die lokale `index.html`
> ist erlaubt. Zusammen mit der CSP (`default-src 'self'`) ist das Defense-in-Depth.
> Verdrahtung beim Fensterstart (hier in Phase 3 vorsehen, spätestens in Phase 11 hart).

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
| `NotifMenu`/`ProfileMenu` | `renderMenus()` | die zwei Dropdowns |
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
5. **Backend-Events**: `window.noa.onSyncDone/onNotification/onLocked` definieren.

**Abnahme:** Alle im Konzept sichtbaren Interaktionen funktionieren mit echten Daten:
Aufgaben abhaken, anlegen, Listen wechseln/anlegen/umbenennen/löschen, Toolbar-Aktionen,
Modals, Lock-Screen, Toasts, Theme/Accent/Dichte/Toolbar/Sidebar umschalten,
Tastenkürzel, Focus-Modus. Optisch deckungsgleich mit `NoaToDo UI Konzept.html`.

> **Meilenstein:** Nach Phase 6 ist die App als **lokale** To-Do-App voll benutzbar.
> Die Phasen 7-11 ergänzen Microsoft-Sync, Benachrichtigungen und die Sicherheits-
> Tiefe. Sie sind unabhängig und können einzeln umgesetzt werden.

---

### Phase 6.5: UX-Nacharbeiten am Prototyp (eingeschoben nach dem Audit vom 2026-06-10)

**Stand-Korrektur:** Abgeschlossen ist **Phase 6** (lokal nutzbarer Prototyp).
Phase 7 ist **offen**: `export_list` erzeugt zwar Inhalte, aber es wird noch
keine Datei geschrieben (kein Save-Dialog), siehe Gate G21c. Das Kopieren ist
seit dem 2026-06-10 fertig und gehärtet (`copy_task`, siehe Punkt 5 unten).

**Bereits umgesetzt (2026-06-10), gehört ab jetzt zum Soll-Verhalten:**
1. **Aufgaben inline bearbeiten:** Doppelklick auf eine Aufgaben-Karte öffnet
   Text- und Meta-Eingabe direkt in der Karte. Enter speichert (`edit_task`),
   Esc bricht ab, Klick daneben speichert (bei leerem Text: Abbruch). Leerer
   Text wird abgelehnt.
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
- **Fälligkeits-UI (Phase 10):** `due_at` existiert im Schema und in `edit_task`,
  hat aber kein UI. Pflicht in Phase 10 (zusammen mit den Erinnerungen): Datum
  setzen/ändern/entfernen im Inline-Edit, Anzeige als Mono-Tag an der Karte,
  überfällige Aufgaben in `--danger`.
- **Echte Benachrichtigungen (Phase 10):** Das Glocken-Menü zeigt hartkodierte
  Fake-Einträge. Pflicht: durch echte Ereignisse ersetzen (Sync abgeschlossen,
  Erinnerung fällig, Backup geschrieben), inklusive Leer-Zustand ("keine
  Benachrichtigungen") und echter Zähler-Badge.
- **Echtes Profil-Menü (Phase 8):** Das Profil-Menü zeigt den hartkodierten
  Namen "Noa Andersen" und tote Einträge (Account, Privacy & data, Export
  database). Pflicht: an `sign_in`/`sign_out` und die echten Kontodaten
  anbinden; tote Einträge entweder funktional machen oder entfernen.
- **Export-Save-Dialog (Phase 7):** siehe Gate G21c.

**Abnahme:** Doppelklick-Bearbeiten, Hover-Löschen, das neue `Strg+C`-Verhalten
und Mini-always-on-top funktionieren in der laufenden App; die offenen Punkte
sind in den Phasen 7, 8 und 10 als Pflicht eingeplant.

---

### Phase 7: Export & Kopieren (`backend/api.py` ausbauen)

**Ziel:** Der Export schreibt echte Dateien (Save-Dialog) und das Löschen von
Listen ist per Undo absicherbar. (Das Kopieren ist bereits fertig: `copy_task`
aus Phase 6.5 / Gate G23, es gibt bewusst kein Listen-Kopieren mehr.)

**Tun:**
1. `export_list(id, 'md')` → Markdown (Überschrift = Listenname, `- [ ]`/`- [x]` je
   Aufgabe, Meta in Klammern). `'txt'` und `'json'` analog. Über PyWebViews
   Save-Dialog speichern.
2. **Undo beim Listen-Löschen** (UX-Pflicht aus Phase 6.5): `delete_list` hält
   die gelöschte Liste samt Aufgaben zunächst zurück, neue Bridge-Methode
   `undo_delete_list(id)` stellt wieder her; das Frontend zeigt den Toast
   „List deleted" mit „Undo"-Button (ca. 6 s).

> **🔒 PFLICHT-GATES für Phase 7 (aus dem Audit 2026-06-10, Details in B.9
> Nachtrag G13-G25; keines davon ist optional):**
> - **G20, Validierung lokaler Eingaben:** `add_task`/`edit_task` Text ≤ 4096,
>   `meta` ≤ 256, Listennamen ≤ 256; Steuerzeichen U+0000-U+001F (ausser `\n`/`\t`)
>   strippen; `reorder` lehnt Nicht-Listen ab; `set_setting` nur mit Key-Whitelist
>   (`accent`, `dark`, `toolbar`, `density`, `sidebar`, `railPinned`, `sidebarWidth`).
> - **G21, Export-Härtung:** reservierte Windows-Dateinamen (CON, PRN, AUX, NUL,
>   COM1-COM9, LPT1-LPT9) entschärfen; `\r`/`\n` in Task-Text/Meta beim md/txt-Export
>   durch Leerzeichen ersetzen (keine eingeschleusten Checkbox-Zeilen); echten
>   Save-Dialog umsetzen und die Datei wirklich schreiben.
> - **G22, Ehrlicher Status:** `get_status()` meldet den realen
>   Verschlüsselungszustand (Dev-Key = UNSICHER, Schicht 2 = nicht implementiert),
>   bis Phase 11 fertig ist. Spätestens in dieser Phase umsetzen.
> - **✅ G23 (bereits umgesetzt, 2026-06-10):** Einzel-Task-Kopie über `copy_task`
>   im Backend, History-/Cloud-Ausschluss, Auto-Clear nach 60 s, `Strg+C` entfernt.
>   In dieser Phase nur noch verifizieren (Win+V prüfen) und bei neuen
>   Copy-Funktionen denselben Backend-Pfad verwenden.
> - **G12 vorziehen:** Externe WebView-Navigation verweigern (wenige Zeilen in
>   `main.py`), nicht erst in Phase 11.

**Abnahme:** Export schreibt nach Save-Dialog eine korrekte `.md`-Datei (auch bei
Listennamen wie `CON` oder Tasks mit Zeilenumbrüchen); die Einzel-Task-Kopie taucht
nachweislich nicht in der Win+V-History auf und das Clipboard ist nach 60 s leer;
gelöschte Listen lassen sich per Undo-Toast wiederherstellen;
überlange/Steuerzeichen-Eingaben werden begrenzt bzw. bereinigt; `get_status()`
zeigt den ehrlichen Dev-Zustand.

---

### Phase 8: Microsoft-Login (`backend/auth.py`)

**Ziel:** Anmeldung bei Microsoft mit MSAL (Public Client, Authorization-Code + PKCE),
Scope **`Tasks.Read`**, Tokens sicher über `keyring`.

**Tun:**
1. App-Registrierung im Azure-Portal (Public Client, Redirect `http://localhost`),
   Client-ID in eine lokale Config legen (nicht hartkodiert committen).
2. `sign_in()` startet den PKCE-Flow (lokaler Loopback-Redirect), holt Token, legt
   Refresh-Token via `keyring` im Windows Credential Manager ab (nie im Klartext/in der
   DB).
3. `get_token()` liefert ein gültiges Access-Token (silent refresh, sonst neuer Flow).
4. `sign_out()` löscht die Tokens aus `keyring`.

> **🔒 PFLICHT-GATE G5 (OAuth-Härtung), aus dem Security-Review, NICHT weglassen:**
> - **`state`-Parameter** generieren (zufällig) und beim Loopback-Redirect strikt
>   **validieren** (Schutz vor Auth-Code-Injection/CSRF). Stimmt `state` nicht → abbrechen.
> - **PKCE**: `code_verifier` pro Flow neu erzeugen, an die Session binden (MSAL macht
>   das, wenn man den Public-Client-Flow korrekt nutzt, nicht umgehen).
> - **Loopback-Listener**: nur an `127.0.0.1` binden (nicht `0.0.0.0`), **genau einen**
>   Request annehmen, dann sofort schließen. Keinen dauerhaften lokalen HTTP-Server.
> - **Kein Client-Secret** in der App (Public Client). Ein Secret in einer verteilten
>   Desktop-App ist kein Geheimnis.
> - **Scope strikt `Tasks.Read`** (least privilege). `offline_access` nur fürs
>   Refresh-Token, das ist das Minimum.
> - **Tokens**: nur in `keyring` (Windows Credential Manager). **Nie** in die DB, **nie**
>   ins Frontend zurückgeben, **nie** loggen (auch nicht im Fehlerfall / Stacktrace).
> - **TLS niemals aufweichen**: `httpx` verifiziert per Default, kein `verify=False`,
>   kein Proxy-Vertrauen.
>
> **🔒 PFLICHT-GATE G10 (Fehlermeldungen ohne Geheimnisse), gilt für Phase 8 UND 9:**
> Der `bridge`-Dekorator in `api.py` gibt aktuell `{"error": "internal", "message":
> str(exc)}` ans Frontend, das es als Toast zeigt. Eine httpx-/MSAL-Exception kann
> Tokens, Delta-Links/Skiptoken oder Pfade enthalten. Für **alle Auth-/Sync-Methoden**:
> generische Fehlercodes ans Frontend (z.B. `auth_failed`, `sync_failed`), Details
> **nur serverseitig** loggen, und auch im Log **keine** Tokens/Delta-Links/Pfade.

**Abnahme:** Nach `sign_in()` liefert `get_status()` „Microsoft Graph: Tasks.Read ·
token valid"; nach Neustart bleibt man angemeldet (Refresh-Token). **G5 erfüllt:**
`state` wird validiert, Listener nur an `127.0.0.1`, kein Secret, keine Tokens in
Logs/Frontend/DB. **G10 erfüllt:** Fehler ans Frontend tragen keine Geheimnisse.

---

### Phase 9: Sync Cloud → Lokal (`backend/graph_sync.py`)

**Ziel:** Einseitiger, inkrementeller Import aus Microsoft To Do über Microsoft Graph.

**Tun:**
1. Lesen über `GET /me/todo/lists` und `/me/todo/lists/{id}/tasks` mit `httpx` und dem
   Token aus Phase 8.
2. **Upsert** nach stabiler Graph-`id` (kein blindes Insert): jede importierte Liste/
   Aufgabe trägt ihre Graph-ID als Primärschlüssel, `source='graph'`, `synced=1`.
3. **Delta-Queries**: `delta_link` pro Liste in `sync_state` speichern und beim nächsten
   Sync nur Änderungen holen.
4. **Richtung strikt Graph → SQLite.** Lokale Aufgaben (`source='local'`) werden nie
   angefasst und nie hochgeladen. Scope ist ohnehin nur `Tasks.Read`.
5. **Auslöser:** einmal beim App-Start, danach periodisch (Polling, z.B. alle paar
   Minuten) per Hintergrund-Thread/Timer; pausiert wenn `online=False` (Flugmodus).
6. Nach jedem Sync `on_sync_done(summary)` ans Frontend (Toast „Sync complete",
   Benachrichtigungs-Eintrag, Listen neu laden).
7. **Konfliktregel für importierte Aufgaben:** siehe Entscheidung D.1, Default
   umsetzen.

> **🔒 PFLICHT-GATES G1-G4, Phase 9 ist sicherheitskritisch. Dies ist der eingehende
> Untrusted-Kanal (B.9). Diese vier Punkte sind KEINE Kür, sondern Voraussetzung,
> bevor Sync-Daten überhaupt angezeigt werden dürfen:**
>
> - **G1, `textContent`-Umstellung ZUERST:** Bevor `graph_sync.py` zum ersten Mal
>   Fremddaten rendert, **müssen** alle Fremddaten-Renderpfade in `app.js`
>   (Task-Text, Meta, Listenname, Toast, Notif) von `innerHTML`/`esc()` auf
>   `textContent`/`createTextNode` umgestellt sein (B.9 Regel 1, Buchstabe). **Reihenfolge
>   beachten: erst G1, dann den Sync aktivieren, nicht umgekehrt.**
> - **G2, `nextLink`/`deltaLink` Host-Whitelist:** Folge-/Delta-URLs aus der Graph-
>   Antwort **nur** abrufen, wenn ihr Host `graph.microsoft.com` ist. Sonst abbrechen.
>   Andernfalls könnte eine manipulierte Antwort dich auf einen fremden Server umleiten
>   **mit angehängtem Bearer-Token** (Token-Leak). Basis-URLs immer selbst konstruieren.
> - **G3, Limits & Timeouts gegen DoS:** `httpx`-Timeouts setzen; Obergrenze für die
>   Seitenzahl pro Sync; **Regel 4** anwenden (Task-Text ≤ 4096, Listenname ≤ 256,
>   Steuerzeichen U+0000-U+001F außer `\n`/`\t` strippen); Mengen-Cap, damit ein
>   bösartiges/kompromittiertes Konto nicht Platte/UI-Thread blockiert.
> - **G4, Schreib-Lock:** Der Sync läuft im Hintergrund-Thread und schreibt in dieselbe
>   SQLCipher-Verbindung (`check_same_thread=False`). **Alle** DB-Writes mit einem
>   `threading.Lock` serialisieren → Korruptionsschutz.
> - **G10 (auch hier):** Sync-Fehler ans Frontend nur als generischer Code (`sync_failed`),
>   Details serverseitig loggen, **kein** Delta-Link/Skiptoken/Token in Toast oder Log.
> - **G24, Seed-Migration VOR dem ersten Sync (Audit 2026-06-10):** Die Seed-Listen
>   sind als `synced=1`/`source='graph'` markiert, tragen aber lokale UUIDs statt
>   echter Graph-IDs; der erste Sync würde Duplikate und "Geisterlisten" erzeugen.
>   Beim ersten erfolgreichen `sign_in()` alle Listen mit `synced=1` und ID-Präfix
>   `l` (= Seed) samt Aufgaben auf `synced=0`/`source='local'` migrieren.

**Abnahme:** Eine im Handy/MS-To-Do geänderte Aufgabe erscheint nach dem nächsten Sync
lokal; ein zweiter Sync direkt danach überträgt (dank Delta) (fast) nichts.
**Zusätzlich Pflicht:** G1 (textContent) erledigt **vor** dem ersten Render von
Sync-Daten, G2 (Host-Whitelist), G3 (Limits/Regel 4), G4 (Schreib-Lock) sind umgesetzt.
Ein eingeschleuster `<img src=x onerror=…>` in einem Task-Titel bleibt nachweislich
wirkungslos (per textContent als reiner Text dargestellt, zusätzlich von der CSP geblockt).

---

### Phase 10: Lokale Benachrichtigungen (`backend/notify.py`)

**Ziel:** Erinnerungen und Sync-Hinweise als Windows-Toasts.

**Tun:**
1. `winotify` (Fallback `plyer`) für native Windows-Benachrichtigungen.
2. Auslöser: fällige Aufgaben (`due_at`), abgeschlossener Sync, geschriebenes Backup.
3. Jede Benachrichtigung zusätzlich in das In-App-NotifMenu einspeisen
   (`on_notification`).

**Abnahme:** Eine Aufgabe mit naher Fälligkeit erzeugt zur richtigen Zeit einen
Windows-Toast und einen Eintrag im Glocken-Menü.

---

### Phase 11: Sicherheits-Tiefe (`backend/security.py`)

**Ziel:** Lock-Screen, Emergency/Panic und (optional) Datenbank-Verschlüsselung real
machen, das Kernversprechen „sicherer als Microsoft To Do".

**Tun:**
1. **App-Sperre nach der Sperr-Politik aus B.8:** `lock()` setzt `locked=True`, verwirft
   die Schlüssel, packt die DB wieder zu (Schicht 2) und zeigt den LockScreen über allem.
   `unlock(passphrase)` prüft den Argon2-Hash, leitet die Schlüssel ab und öffnet die DB.
   Sperre auslösen bei: Lock-Button/`Ctrl+L`, Panic, **App-Start** (immer gesperrt starten),
   **Auto-Sperre nach Inaktivität** (einstellbarer Timeout, Default ~15 min) und
   **Windows-Sitzungssperre**. Letztere via `WTSRegisterSessionNotification` +
   `WM_WTSSESSION_CHANGE` → bei `WTS_SESSION_LOCK` `lock()` aufrufen (Registrierung beim
   Fensterstart in Phase 3/`main.py`). **Kein** Sperren bei Minimieren/Fokuswechsel.
2. **Emergency/Panic** (`panic()`): sofort sperren, Frontend-Cache leeren
   (`state.lists=[]` und neu sperren), Sync pausieren/offline schalten. Nichts löschen.
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
4. `get_status()` liefert echte Werte (DB-Größe, Verschlüsselungs-Status, Token-Status,
   letzter Sync, WebView2-Version).

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
> - **🔴 G9, `DEV_AES_KEY` entfernen (WICHTIGSTES Gate der Phase 11):** Der aktuelle
>   `db.py` hat `DEV_AES_KEY = "noatodo-dev-key-phase1"` als Default, und `main.py` ruft
>   `db.connect()` **ohne** Schlüssel auf. Bei der Umsetzung von Phase 11 **muss** dieser
>   statische Default, und jeder andere Schlüssel-Fallback, **ersatzlos verschwinden**.
>   Es darf **keinen** Code-Pfad geben, der die DB ohne den aus der Passphrase abgeleiteten
>   Schlüssel öffnet. Sonst öffnet die „verschlüsselte" DB mit einem öffentlich im
>   Quellcode stehenden String → **effektiv null Verschlüsselung**, während `get_status()`
>   fälschlich „AES-256 + ChaCha20 · aktiv" meldet. Das untergräbt das gesamte
>   Sicherheitsversprechen lautlos. **Ebenso bedenken:** sauberer Erst-Einrichtungs-Flow
>   (Passphrase anlegen) und Migration der bestehenden Dev-DB auf den echten Schlüssel.

> **🔒 PFLICHT-GATES G13 bis G19 und G25 für Phase 11 (aus dem Audit 2026-06-10,
> vollständige Beschreibung in B.9 Nachtrag; KEINES davon ist optional):**
> - **🔴 G13, Lock serverseitig durchsetzen:** Bei `locked=True` weist der
>   `bridge`-Decorator **jede** Methode ausser `unlock(passphrase)` mit
>   `{"error": "locked"}` ab; `get_state()` liefert gesperrt nur `{"locked": true}`.
>   Heute ist die Sperre nur ein Frontend-Overlay (im Audit nachgewiesen:
>   `add_task`/`get_state` funktionieren gesperrt weiter).
> - **G14, WebView2 ohne Datenspuren (fester Profilordner umgesetzt 2026-06-20, sicheres Wischen offen für Phase 11):**
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
>   **Noch offen für Phase 11:** (a) `panic()`/`lock()`/sauberer Quit müssen `PROFILE_DIR`
>   **sicher wischen** (Forensik-Härtung gegen Crash-Dumps, siehe Entwarnung unten); (b) das
>   Wischen muss mit dem Single-Instance-Mutex und dem Lock-Lebenszyklus abgestimmt sein
>   (nicht wischen, während WebView2 den Ordner noch offen hält); (c) **Edge-Case festgestellt
>   2026-06-20:** wird der Prozess hart abgeschossen (Task-Manager), überleben die
>   `msedgewebview2.exe`-Kinder und halten `PROFILE_DIR` gesperrt; der nächste Start scheitert
>   dann an `CreateCoreWebView2Controller` mit `0x800700AA` (ERROR_BUSY, Fenster bliebe weiß).
>   Im Normalbetrieb (Fenster sauber schließen) lösen die Kinder die Sperre selbst; für den
>   Crash-/Kill-Fall sollte Phase 11 verwaiste `msedgewebview2.exe` mit `PROFILE_DIR` als
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
>   fliesst als Argon2id-`secret` in die Ableitung ein; Einrichtungs-Flow enthält
>   zwingend einen Recovery-Export des Peppers.
> - **G19, Single-Instance-Mutex (umgesetzt 2026-06-20, vorgezogen):** benannter
>   Windows-Mutex `Local\NoaToDoSingleton` beim Start (`_acquire_single_instance` in
>   `main.py`), zweite Instanz zeigt einen Hinweis und beendet sich sofort
>   (Korruptionsschutz, Voraussetzung für den festen WebView2-Profilordner aus G14).
> - **G25, RAM-Schlüssel-Hygiene:** Schlüssel/Master-Secret/Pepper als `bytearray`,
>   vor dem Verwerfen nullen; Passphrase nach Ableitung sofort verwerfen; nichts
>   davon je in Logs, Exceptions oder ans Frontend.

**Abnahme:** Sperren/Entsperren funktioniert mit Passphrase; Panic sperrt sofort und
pausiert Sync; bei aktivierter Verschlüsselung ist `tasks.db` ohne Passphrase nicht
lesbar. **G6-G8 erfüllt:** keine entschlüsselte DB-Datei auf der Platte (In-Memory),
Hex-Raw-Key gesetzt, starke Argon2id-Parameter + Passphrase-Stärkeprüfung aktiv.
**G13-G19/G25 erfüllt:** Bridge-Methoden liefern gesperrt nachweislich `locked`-Fehler;
kein WebView2-Datenrest; Entsperren scheitert bei falscher Passphrase über den
AEAD-Tag; `tasks.db.enc` trägt den spezifizierten Header und übersteht einen
simulierten Absturz beim Sperren (`.bak` greift); ohne den Pepper aus dem Credential
Manager ist die Datei offline nicht angreifbar; eine zweite App-Instanz startet nicht.

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
Fälligkeits-UI (UX 7.1) -> Phase 6.5 + Phase 10; echtes Profil-Menü (UX 1.3) ->
Phase 6.5 + Phase 8; echte Benachrichtigungen/Glocke (UX 1.3) -> Phase 6.5 + Phase 10;
Export-Save-Dialog + ehrliches Feedback (UX 1.5) -> Phase 7 / Gate G21c; Undo beim
Listen-Löschen (UX 1.2, 3.3) -> Phase 6.5 + Phase 7; ehrlicher `get_status()` und
Status-Modal (UX 1.4, 8.4) -> Gate G22 + Phase 11; Auto-Lock-Timeout (UX 7.6) -> B.8;
serverseitige Lock-Durchsetzung -> Gate G13 (Screenshot-Schutz / G26 wurde verworfen,
siehe oben). Diese Punkte sind verbindlich an den genannten Stellen, hier nur zur
Vollständigkeit gelistet.

### N1. Phase 8/9: Lade-/Fortschritts-Zustände als Pflicht-Muster (UX 6.2)
Heute laufen alle Bridge-Aufrufe ohne sichtbares Feedback; lokal ist das schnell genug.
Ab Phase 8 (Login) und Phase 9 (Sync) gibt es erstmals **spürbar langsame** Aufrufe
(Netzwerk, Token-Refresh, Delta-Abruf). Pflicht: ein einheitliches Pending-Muster, das
**vor** dem ersten langsamen Call existiert, nicht danach nachgerüstet wird.
- Die auslösende Aktion deaktiviert ihren Button und zeigt einen Inline-Spinner (kein
  modaler Blocker des ganzen Fensters).
- Doppel-Auslösung verhindern (kein zweiter `sign_in`/`sync_now`, solange einer läuft).
- Fehlerfall: generische Meldung (Gate G10), klare Retry-Möglichkeit.
- Der dauerhafte Status (läuft/fertig/Fehler) gehört in die Statuspille aus N2, nicht
  nur in einen flüchtigen Toast.

### N2. Phase 9: Persistente Online-/Sync-Statusanzeige (UX 4.2, 8.3)
Der Online/Offline-Zustand ist heute fast unsichtbar (nur Globus-Icon in der oft
versteckten Rail plus kurzer Toast). Das Konzept sah die `airplane-pill` als
persistenten Banner vor; ihr CSS liegt ungenutzt im Stylesheet. Pflicht ab Phase 9:
- Eine **persistente Statuspille** im Hauptbereich (oder am Dock), sichtbar sobald
  `online=false` („offline, sync paused") und nach erfolgtem Sync („last sync 14:02").
- Diese Pille ist der feste Ort für den Sync-Status (Erfolg, Zeitpunkt, Fehler),
  ergänzend zum Toast aus Phase 9 Punkt 6.
- Damit entschärft sich auch UX 3.12 (versehentliches `G`/Offline ohne sichtbare Folge).

### N3. Phase 9: Konflikt-Benachrichtigung sichtbar machen (UX 8.3, Entscheidung D.1)
Die Konfliktregel (Default A: Cloud überschreibt lokale Änderungen an importierten
Aufgaben, siehe D.1) läuft heute stumm. Pflicht: Wenn ein Sync lokale Änderungen an
importierten Aufgaben überschreibt, erzeugt das einen **Benachrichtigungs-Eintrag** im
Glocken-Menü („cloud overwrote N local edits") und fließt in den Sync-Summary
(`on_sync_done`). So bleibt die bewusst gewählte Cloud-Hoheit für den Nutzer
nachvollziehbar statt unsichtbar.

### N4. Phase 11: Echter Lock-Screen mit Passphrase (UX 8.1) [Sec]
B.4 und Phase 11 nennen die Passphrase-Eingabe, aber nicht die UX-Details. Der heutige
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

### N5. Phase 11: Panik-Flow, Hotkey ohne Rückfrage (UX 8.2) [Sec]
Heute zeigt sowohl der Hotkey als auch der Rail-Button dasselbe Emergency-Modal.
Zielverhalten (B.8: Panik = sofort sperren):
- **Hotkey `Ctrl+Shift+!` sperrt sofort und ohne Rückfrage** (kein Modal); im Notfall
  zählt Geschwindigkeit.
- Das Bestätigungs-Modal erscheint **nur** beim bewussten Maus-Klick auf den
  Rail-Button (Schutz vor Fehlklick).
- Schon jetzt so umsetzen, damit sich kein falsches Muskelgedächtnis einschleift.

### N6. Phase 11: Entsperr-/Boot-Fehlerbildschirm (UX 6.3) [Sec]
`boot()` rendert bei Fehlern heute ein nacktes `<pre>boot error</pre>`. Ab Phase 11 sind
„falsche Passphrase" und „beschädigte/fehlende `tasks.db.enc`" reale Szenarien. Pflicht:
ein gestalteter Fehlerzustand mit Handlungsoption (Retry, Pfadangabe, Hinweis auf die
`.bak`-Generation aus Gate G16 bzw. den Pepper-Recovery-Export aus Gate G18). Der Nutzer
darf bei einem AEAD-Fehler nie ratlos vor einem leeren Fenster stehen.

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
  Erstellt-Datum, Quelle local/graph). Gibt auch dem Graph-Import (Phase 9) einen Ort,
  importierte Felder zu zeigen.
- **„Today/Overdue"-Sammelansicht (UX 7.5):** virtuelle Liste über alle Listen hinweg,
  sobald Fälligkeiten existieren (setzt das `due_at`-UI aus Phase 10 voraus).
- **Volltextsuche/Filter (UX 7.2):** ein `Ctrl+F`-Overlay mit Fuzzy-Filter über alle
  Listen; für eine tastaturorientierte App der größte einzelne Produktivitätsgewinn.
  Hebt den bisherigen D.3-Einzeiler zu einem konkreten Vorschlag.
- **Mini-Modus, Listenwechsel (UX 7.7, 3.14):** ein Dropdown im `mini-bar`-Titel zum
  Wechseln der Liste, ohne den Mini-Modus zu verlassen.
- **Meta-Feld benennen/strukturieren (UX 7.3):** das Freitext-`meta` entweder klar als
  Notiz („note") labeln oder in strukturierte Tags überführen (Entscheidung steht aus).

### N9. Einstellungen, Vorbereitung künftiger Phasen (UX 7.6)
Ergänzend zu den schon geplanten Settings (Auto-Lock-Timeout B.8): **Startverhalten**
(maximiert vs. letzte Fenstergröße) als Einstellung vorsehen.
Die bestehende Settings-Struktur (Zeile + Segment, B.6) trägt das ohne Umbau; jeder neue
Key muss in die `set_setting`-Whitelist aus Gate G20 aufgenommen werden.

---

## TEIL D: Offene Entscheidungen & Erweiterungen

### D.1 Konflikt bei importierten Aufgaben (aus technische Grundlage §6)

Wenn sich eine **importierte** Aufgabe gleichzeitig in der Cloud und lokal ändert:

- **Option A, Cloud besitzt importierte Aufgaben** *(empfohlener Default)*: Beim Sync
  überschreibt der Microsoft-Stand lokale Änderungen an importierten Aufgaben.
  Begründung: Scope ist `Tasks.Read`, der Import ist konzeptionell ein Spiegel. Einfach,
  vorhersehbar, keine Geister-Divergenz.
- **Option B, Eingefrorene Kopie**: Eine importierte Aufgabe wird einmal kopiert und
  danach von Microsoft nicht mehr angefasst. Mehr „local-first", aber keine späteren
  Updates aus der Cloud.

> Rein lokale Aufgaben (`source='local'`) sind **nie** betroffen, sie gehören immer dem
> Nutzer. Default in diesem Plan: **A**. Beim Bau als Einstellung vorsehen, falls der
> Nutzer später B möchte.

### D.2 Was lokal bleibt / was aus der Cloud kommt (Privatsphäre)

- **Lokal:** alle selbst erstellten Aufgaben, alle Bearbeitungen, die gesamte SQLite-DB,
  die Tokens (in `keyring`).
- **Aus der Cloud:** ausschließlich die aus Microsoft To Do **gelesenen** Aufgaben.
- Ehrliche Einordnung: Diese Cloud-Daten liegen ohnehin schon bei Microsoft. Der Gewinn
  ist, dass aus dieser App **nichts** dorthin zurückfließt.

### D.3 Mögliche spätere Erweiterungen (nicht im Kern-Scope)

- Unterpunkte/Checklisten je Aufgabe, Wiederholungen. (Das Fälligkeits-UI ist seit
  dem Nachtrag vom 2026-06-10 keine Erweiterung mehr, sondern Pflicht in Phase 10,
  siehe Phase 6.5.)
- Volltextsuche, Filter „wichtige Aufgaben" (in der Skizze angedeutet).
- Mehrere Akzent-/Theme-Presets, anpassbare Dichte je Liste.
- Automatische lokale Backups von `tasks.db` (verschlüsselt) mit Rotation.

---

## ANHANG 1: Seed-Daten (Startfüllung der DB)

Beim ersten Start einspielen (entspricht dem Konzept). `synced=1` = aus MS To Do
importiert (Mirror), `synced=0` = lokal.

- **Reading List** (`synced`)
  - offen: „Going Zero" (Anthony McCarten), „On Leadership" (Tony Blair),
    „One of Us Is Back" (Karen M. McManus), „Money" (Martin Amis),
    „Fahrenheit 451" (Ray Bradbury)
  - erledigt: „Project Hail Mary" (Andy Weir), „The Every" (Dave Eggers),
    „Klara and the Sun" (Kazuo Ishiguro)
- **Ideas** (lokal)
  - offen: „Local-first note encryption" (sketch), „Weekend pottery class",
    „Build a mechanical keyboard"
- **Homework** (`synced`)
  - erledigt: „Statistics problem set 4" (submitted)
- **Programming** (`synced`)
  - offen: „Wire pywebview js_api bridge", „SQLite schema + upsert by graph id",
    „MSAL PKCE login flow", „Delta-query sync loop", „keyring token storage",
    „winotify reminders"
  - erledigt: „Scaffold project structure", „Decide one-way sync model",
    „Pick warm-terminal theme", „Set up WebView2 window"
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
(`Icons`-Objekt). Benötigte Icons: `Menu, Close, Shield, Bell, Plus, Check, Gear,
Chevron, Grip, Plane, Wifi, Expand, Palette, Share, Help, Lock, Unlock, Alert, Copy,
Pencil, Trash, Diag, Globe, Note, Sun, Moon, User, Logout, Pin, Download`. Das
App-Logo (`NoaToDo Logo.png`, orangenes „N" im Kreis) zusätzlich als Fenster-/Taskbar-
Icon verwenden.

---

## Schnell-Checkliste (für die ausführende KI)

- [ ] Phase 0, Struktur + Abhängigkeiten, leeres Fenster **+ 🔒 G11 (Deps pinnen)**
- [ ] Phase 1, `db.py` Schema + CRUD + Seed
- [ ] Phase 2, `api.py` Bridge (lokal)
- [ ] Phase 3, `main.py` Fenster + Verdrahtung **+ 🔒 G12 (Navigation abriegeln)**
- [ ] Phase 4, `index.html` Gerüst, Bridge im Fenster bewiesen
- [ ] Phase 5, `style.css` (CSS 1:1 aus Konzept) + lokale Fonts
- [x] Phase 6, `app.js` komplette UI + Interaktionen  ← **lokal voll nutzbar (Stand heute)**
- [x] Phase 6.5, UX-Nacharbeiten (Inline-Edit, Task-Löschen, Task-Auswahl, gehärtete Einzel-Task-Kopie ✅G23, Strg+C entfernt, Mini-on-top, Screenshot-Schutz ❌G26 verworfen); Rest-Pflichten in 7/8/10 verplant
- [ ] Phase 7, Export + Undo **+ 🔒 G20 (lokale Eingabe-Validierung), G21 (Export-Härtung + Save-Dialog), G22 (ehrlicher Status), G12 vorziehen, Undo beim Listen-Löschen** (G23 schon erledigt)
- [ ] Phase 8, MSAL-Login (`Tasks.Read`, keyring) **+ 🔒 G5 (OAuth-Härtung), G10 (Fehler ohne Geheimnisse)** + echtes Profil-Menü
- [ ] Phase 9, Delta-Sync Cloud → SQLite (einseitig) **+ 🔒 G1 (textContent ZUERST), G2 (Host-Whitelist), G3 (Limits/Regel 4), G4 (Schreib-Lock), G10 (Fehler ohne Geheimnisse), G24 (Seed-Migration)**
- [ ] Phase 10, Benachrichtigungen (winotify) + Fälligkeits-UI + echtes Glocken-Menü
- [ ] Phase 11, Lock / Emergency / Doppel-Kaskade AES-256 + ChaCha20 (B.7) **+ 🔒 G6 (In-Memory-DB), G7 (Hex-Raw-Key), G8 (Argon2id-Kosten + Passphrase-Stärke), 🔴 G9 (`DEV_AES_KEY` entfernen), 🔴 G13 (Lock serverseitig), G14-Rest (PROFILE_DIR sicher wischen bei lock/panic/quit; fester Ordner + Altlasten-Wisch ✅ 2026-06-20), G15 (HKDF/kein Hash), G16 (.enc-Format), G17 (Write-back), G18 (DPAPI-Pepper), G25 (RAM-Hygiene)** (G19 Single-Instance ✅ 2026-06-20 vorgezogen)
- [ ] UX-Nachtrag 2026-06-13 (Abschnitt vor TEIL D): N1 Lade-Zustände (Phase 8/9), N2 Sync-Statuspille (9), N3 Konflikt-Notif (9), N4 Lock-Screen-Passphrase-UX (11), N5 Panik-Hotkey ohne Rückfrage (11), N6 Entsperr-Fehlerbildschirm (11), N7 move_task/reorder_lists/clear_completed, N8 Roadmap (D.3), N9 Startverhalten-Setting

### 🔒 Sicherheits-Gates auf einen Blick (Details in B.9)

| Gate | Phase | Kurz |
|---|---|---|
| ✅ CSP gesetzt | erledigt | `index.html`, strenger als Minimum |
| ✅ `esc()` gehärtet | erledigt | maskiert jetzt auch `'` |
| 🔒 G1 | 9 | `textContent`-Umstellung **vor** erstem Sync-Render |
| 🔒 G2 | 9 | `nextLink`/`deltaLink` nur zu `graph.microsoft.com` |
| 🔒 G3 | 9 | httpx-Timeouts + Limits + Regel-4-Validierung |
| 🔒 G4 | 9 | Schreib-Lock um Sync-DB-Writes |
| 🔒 G5 | 8 | OAuth: `state`-Validierung, Loopback `127.0.0.1`, kein Secret, Tokens nie ins Frontend/Log |
| 🔒 G6 | 11 | In-Memory-DB statt Temp-Arbeitskopie |
| 🔒 G7 | 11 | Hex-Raw-Key für `PRAGMA key` |
| 🔒 G8 | 11 | Argon2id hohe Kosten + Passphrase-Stärke |
| 🔴 G9 | 11 | **`DEV_AES_KEY` & jeden statischen Schlüssel-Fallback entfernen** (sonst null Verschlüsselung) |
| 🔒 G10 | 8/9 | Fehlermeldungen ans Frontend ohne Tokens/Delta-Links/Pfade |
| 🔒 G11 | 0 / laufend | Abhängigkeiten versions-pinnen (+ Hash-Checking) |
| 🔒 G12 | vor 7 (vorgezogen) | Externe WebView-Navigation verweigern |
| 🔴 G13 | 11 | **Lock serverseitig durchsetzen** (gesperrt = jede Methode ausser `unlock` liefert `locked`-Fehler) |
| 🔒 G14 | teils erledigt (2026-06-20), Rest 11 | WebView2 ohne Datenspuren: fester Profilordner statt Privatmodus ✅, Altlasten-Wisch beim Start ✅; sicheres Wischen bei lock/panic/quit offen (Phase 11) |
| 🔒 G15 | 11 | Argon2id-Master-Secret + HKDF-Domain-Separation; kein Verifikations-Hash, Prüfung via Poly1305-Tag |
| 🔒 G16 | 11 | `tasks.db.enc`-Header (Magic/Version/Params/Salt/Nonce), frische Nonce, atomares Schreiben + `.bak` |
| 🔒 G17 | 11 | Debounced Write-back der In-Memory-DB (Crash kostet höchstens Sekunden) |
| 🔒 G18 | 11 | DPAPI-Pepper im Credential Manager als Zweitfaktor gegen Offline-Brute-Force + Recovery-Export |
| ✅ G19 | erledigt (2026-06-20, vorgezogen) | Single-Instance-Mutex `Local\NoaToDoSingleton` (zweite Instanz zeigt Hinweis und beendet sich) |
| 🔒 G20 | 7 | Regel-4-Validierung auch lokal + `reorder`-Typprüfung + `set_setting`-Key-Whitelist |
| 🔒 G21 | 7 | Export-Härtung: reservierte Windows-Namen, Newline-Ersetzung, echter Save-Dialog |
| 🔒 G22 | sofort/7 | `get_status()` meldet den ehrlichen Verschlüsselungszustand (kein falsches "active") |
| ✅ G23 | erledigt (2026-06-10) | Einzel-Task-Kopie im Backend: keine Win+V-History, kein Cloud-Clipboard, Auto-Clear 60 s, `Strg+C` entfernt |
| 🔒 G24 | 9 | Seed-Listen vor dem ersten Sync auf `local` migrieren (keine Pseudo-Graph-IDs) |
| 🔒 G25 | 11 | RAM-Schlüssel-Hygiene: `bytearray` + Nullen, Passphrase sofort verwerfen, nie loggen |
| ❌ G26 | verworfen + entfernt (2026-06-20) | Screenshot-Schutz `WDA_EXCLUDEFROMCAPTURE` blendete Aufnahmen schwarz aus, verhindert aber auf manchen GPUs das Rendern (Fenster weiss / reagiert nicht). Mehrfach ein-/ausgebaut, endgueltig entfernt. Nicht wieder einbauen ohne Render-Verifikation + Affinity-Rollback |

**Hinweise (kein Gate):** Export schreibt unverschlüsselte Dateien (by design, der
Nutzer exportiert bewusst Klartext); `main.py` `emit()` muss
`json.dumps(..., ensure_ascii=True)` behalten (U+2028/U+2029-Schutz im
`evaluate_js`-Kanal). Das Clipboard-Thema ist seit dem Nachtrag ein Gate (G23).
