# Bauplan — NoaToDo (lokale, sichere To-Do-App)

> **Zweck dieses Dokuments.** Es ist die vollständige, schrittweise Bauanleitung
> für NoaToDo. Eine KI (oder ein Mensch) soll es von oben nach unten abarbeiten
> können und am Ende eine lauffähige App haben, die **exakt** wie das Design­konzept
> (`NoaToDo UI Konzept.html`) aussieht und auf dem in `technische Grundlage.txt`
> beschriebenen Fundament läuft.
>
> **Wie man dieses Dokument liest.** Teil A erklärt das Gesamtbild. Teil B legt die
> Verträge fest (Datenmodell, Bridge-API, Design-Tokens) — das sind die Dinge, an
> die sich *alle* Bausteine halten müssen. Teil C ist die eigentliche Schritt-für-
> Schritt-Baufolge (Phase 0–11). Jeder Schritt hat: **Ziel**, **Tun**, **Abnahme**
> (woran man erkennt, dass der Schritt fertig ist). Teil D sammelt offene
> Entscheidungen und Erweiterungen.
>
> Regel für die ausführende KI: **Eine Phase nach der anderen.** Nicht
> vorgreifen. Nach jeder Phase die Abnahme-Kriterien prüfen, dann erst weiter.

---

## TEIL A — Das Gesamtbild

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

- Das **CSS des Konzepts ist framework-unabhängig** — es wird 1:1 übernommen (Teil B.3
  / Phase 5). Das Aussehen ist damit identisch.
- Die React-Komponenten sind kleine, klar abgegrenzte Render-Funktionen. Jede wird zu
  einer Vanilla-`render…()`-Funktion, die denselben DOM-Baum erzeugt. Teil B.4 listet
  die Zuordnung Komponente → Render-Funktion auf.

> Wer lieber React behalten will, kann React/ReactDOM per CDN laden und die Komponenten
> aus dem Konzept direkt verwenden — dann entfallen die Render-Funktionen, aber die
> Bridge-Verträge (B.2) und das Backend (Phasen 1–4, 8–10) bleiben gleich. Default
> dieses Plans = Vanilla.

---

## TEIL B — Die Verträge (für alle Bausteine verbindlich)

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

### B.2 Bridge-API (`pywebview.api.*`) — der Vertrag zwischen vorne und hinten

Das ist die **vollständige Methodenliste**, die `backend/api.py` bereitstellt und die
`frontend/app.js` aufruft. Jede gibt JSON-serialisierbare Werte zurück (Promise im JS).

| Methode | Argumente | Rückgabe | Zweck |
|---|---|---|---|
| `get_state()` | – | `{ lists:[…], settings:{…}, online:bool, locked:bool }` | Initialer Gesamtzustand beim App-Start |
| `get_lists()` | – | `[ { id, name, synced, open:[task], done:[task] } ]` | Alle Listen mit eingebetteten Aufgaben |
| `add_list(name)` | `str` | `{ id, name, … }` | Neue lokale Liste |
| `rename_list(id, name)` | `str,str` | `{ ok:true }` | Liste umbenennen |
| `delete_list(id)` | `str` | `{ ok:true }` | Lokale Liste + Aufgaben löschen (synced kommen beim nächsten Sync zurück) |
| `add_task(list_id, text, meta?)` | `str,str,str?` | `{ …task }` | Neue lokale Aufgabe |
| `toggle_task(id)` | `str` | `{ id, done:bool }` | Erledigt-Status umschalten |
| `edit_task(id, fields)` | `str,obj` | `{ …task }` | Text/Meta/Fälligkeit ändern |
| `delete_task(id)` | `str` | `{ ok:true }` | Aufgabe löschen |
| `reorder(list_id, ordered_ids)` | `str,[str]` | `{ ok:true }` | Drag-&-Drop-Reihenfolge speichern |
| `export_list(id, format)` | `str,'md'\|'txt'\|'json'` | `{ filename, content }` | Liste exportieren |
| `copy_list(id)` | `str` | `{ text }` | Liste als Text fürs Clipboard |
| `set_setting(key, value)` | `str,*` | `{ ok:true }` | Eine Einstellung speichern |
| `get_status()` | – | `{ db, encryption, graph, last_sync, runtime }` | Daten für das „App status"-Modal |
| `sign_in()` | – | `{ ok, account }` | MSAL-Login starten |
| `sign_out()` | – | `{ ok:true }` | Tokens verwerfen |
| `sync_now()` | – | `{ changed:int, lists:int }` | Sofort-Sync gegen MS Graph |
| `set_online(flag)` | `bool` | `{ online:bool }` | „Flugmodus"/Online umschalten (pausiert Sync) |
| `lock()` | – | `{ locked:true }` | App sperren |
| `unlock(passphrase)` | `str` | `{ ok:bool }` | Entsperren |
| `panic()` | – | `{ locked:true }` | Emergency: sperren + Cache leeren + offline |

**Ereignisse Backend → Frontend** (PyWebView kann JS auswärts aufrufen, z.B.
`window.evaluate_js` oder ein Event-Bus): `on_sync_done(summary)`,
`on_notification(payload)`, `on_locked()`. Das Frontend registriert dafür globale
Funktionen `window.noa.onSyncDone` usw.

**Fehlerkonvention:** Jede Methode kann statt des Erfolgsobjekts
`{ error: "code", message: "…" }` liefern. Das Frontend zeigt das als Toast.

### B.3 Design-Tokens (aus dem Konzept übernehmen — nicht neu erfinden)

Schriften: **Space Grotesk** (UI-Sans) + **JetBrains Mono** (mono — Labels, Tags,
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
> übernommen. In Phase 5 steht, wie man sie extrahiert. **Nicht** von Hand nachbauen —
> 1:1 kopieren, damit das Aussehen exakt stimmt.

### B.4 UI-Aufbau — die Abschnitte (genau so wie im Konzept und in der Skizze)

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
  Globe bei online; Klick schaltet um — siehe `set_online`).
- Großer Listentitel (32px).
- Meta-Zeile (Mono-Tags): „X open", Punkt, „Y done", Punkt, Status-Tag
  „↯ synced from MS To Do" (grün) oder „✦ local only" (blass).
- Abschnitt **OPEN TASKS**: Section-Head (Mono-Titel + Zähler + Linie), darunter die
  Aufgaben-Karten. Ist nichts offen: Mono-Hinweis „// nothing open — you're all caught up".
- **New-task-Eingabe**: gestrichelte Akzent-Karte mit Plus, Platzhalter „New task…",
  Enter legt an, `[↵]`-Kbd rechts.
- Abschnitt **COMPLETED** (nur wenn es erledigte gibt): einklappbarer Section-Head
  (Chevron dreht), animiertes Auf-/Zuklappen, darunter die erledigten Aufgaben.

**Aufgaben-Karte** (`renderTask`)
- Runder Check-Button (Klick → `toggle_task`). Text. Optional Mono-Meta rechts (z.B.
  Autor) — nur bei offenen Aufgaben. Drag-Griff, der bei Hover erscheint.
- Erledigt: transparenter Hintergrund, gestrichelter Rand, Text durchgestrichen +
  blass, Check in Grün gefüllt.

**Rechte Toolbar** (`renderToolbar`) — vertikale Leiste, zwei Modi über
`data-toolbar`: `flush` (bündig an der Kante) oder `floating` (schwebende, gerundete
Karte, Standard). Buttons mit Tooltip + Hotkey, in Gruppen durch Trenner:
1. **Focus mode** (⤢, `F`) — blendet Sidebar+Toolbar aus, nur eine „Exit focus"-X bleibt.
2. **Accent color** (🎨) — öffnet Swatch-Popover mit den 6 Akzenten.
3. **Export** (⬆, `⌘E`).
4. **Shortcuts** (?) — öffnet das Tastenkürzel-Modal.
   — Trenner —
5. **Lock / Unlock** (🔒, `⌘L`).
6. **Emergency** (⚠, `⌘⇧!`, rot) — öffnet das Panik-Modal.
   — Trenner —
7. **Copy list** (⧉, `⌘C`).
8. **Rename list** (✎) — öffnet Umbenennen-Modal.
9. **Delete list** (🗑) — öffnet Löschen-Modal.
   — Trenner —
10. **App status** (📈) — öffnet Diagnose-Modal.
11. **Go online/offline** (🌐, `G`) — aktiv-Zustand wenn online.

**Overlays** (`renderOverlays`)
- **NotifMenu** — Dropdown unter der Glocke: Liste von Benachrichtigungen (Titel,
  Mono-Unterzeile, farbiger Punkt). Beispiele: „Reminder: …", „Sync complete",
  „Backup written".
- **ProfileMenu** — Dropdown unter dem Avatar: Kopf mit Avatar + Name + „signed in ·
  local"; Einträge Account, Privacy & data, Export database, Sign out.
- **EmergencyModal** — roter Streifen oben, Warn-Icon, Titel „Panic — lock everything?",
  Erklärtext (sperrt sofort, leert Cache, DB offline, nichts wird gelöscht), Buttons
  Cancel / „Lock now" (rot).
- **StatusModal** — Diagnose-Zeilen: Local database (Größe), Encryption (AES-256 +
  ChaCha20 · Argon2id), Microsoft Graph (Tasks.Read · Token / offline), Last sync, WebView2 runtime
  — jeweils mit grünem/blassem Status-Tag. Daten kommen aus `get_status()`.
- **RenameModal** — Eingabefeld (vorbelegt, fokussiert+selektiert), Enter/Save.
- **DeleteModal** — Bestätigung „Delete „Name"?" mit Hinweis, dass synchronisierte
  Listen beim nächsten Sync zurückkommen.
- **ShortcutsModal** — Raster aller Tastenkürzel (siehe B.5).
- **LockScreen** — Vollbild über allem: Akzent-Ring mit Schloss, „NoaToDo is locked",
  Mono-Zeile „LOCAL VAULT · ENCRYPTED · OFFLINE", 4 Punkte, Button. (Im echten Build:
  Passphrase-Eingabe statt der 4 Demo-Taps.)
- **Toasts** — kurze Bestätigungen unten mittig (z.B. „List created", „Exported list").

### B.5 Tastenkürzel (verbindlich)

| Aktion | Taste |
|---|---|
| Neue Aufgabe | `↵` (im New-task-Feld) |
| Neue Liste | `N` |
| Sidebar umschalten | `⌘/Strg + B` |
| Focus-Modus | `F` |
| App sperren | `⌘/Strg + L` |
| Notfall-Sperre | `⌘/Strg + ⇧ + !` |
| Liste exportieren | `⌘/Strg + E` |
| Liste kopieren | `⌘/Strg + C` |
| Theme umschalten | `⌘/Strg + J` |
| Online/Offline | `G` |
| Tastenkürzel-Hilfe | `?` |
| Alles schließen | `Esc` |

Beim Tippen in Eingabefeldern dürfen die Buchstaben-Hotkeys nicht feuern (außer Esc).

### B.6 Einstellungen (persistiert in `settings`-Tabelle)

`accent` (Hex), `dark` (bool), `toolbar` (`floating`|`flush`), `density`
(`comfortable`|`compact`), `sidebar` (`open`|`closed`). Werden beim Start aus
`get_state()` gelesen und auf das `.app`-Element als `data-*`/`--accent` gesetzt;
Änderungen sofort via `set_setting` zurückschreiben.

### B.7 Verschlüsselung (verbindlich) — Doppel-Kaskade AES-256 + ChaCha20

Die lokale Datenbank ist **immer verschlüsselt**, und zwar in **zwei unabhängigen
Schichten** (Tresor im Tresor, VeraCrypt-Prinzip). Beide Algorithmen sind etablierte,
jahrzehntelang geprüfte Standards — **kein Eigenbau**. Ein Angreifer müsste *beide*
unabhängig brechen.

> **Ehrliche Einordnung (steht bewusst im Plan):** AES-256 allein wäre bereits jenseits
> jeder realistischen Bedrohung — auch für Geheimdienste — nicht knackbar. Die zweite
> Schicht ist **Defense-in-Depth** (Sicherheitsmarge + bewusst gewählter „Bunker-Vibe"),
> kein notwendiger Schutz gegen einen praktischen Angriff. Der *wahre* Schwachpunkt
> bleibt in beiden Fällen die Passphrase — deshalb ist die starke Schlüsselableitung
> (Punkt 3) genauso wichtig wie die Cipher selbst.

**Schicht 1 — die Datenbank selbst: SQLCipher (AES-256).**
Statt des normalen `sqlite3` wird **SQLCipher** verwendet (Paket `sqlcipher3-binary`):
dieselbe SQLite-API, aber die Datei ist seitenweise mit AES-256 verschlüsselt und behält
alle DB-Vorteile (gezielte Abfragen, Transaktionen, Crash-Sicherheit). Direkt nach dem
Öffnen wird der Schlüssel gesetzt:
```python
conn = sqlcipher3.connect(working_db_path)
conn.execute("PRAGMA key = ?", (aes_key,))     # aes_key = abgeleitet, s. Punkt 3
conn.execute("PRAGMA foreign_keys = ON")
```

**Schicht 2 — die ganze DB-Datei nochmal: ChaCha20.**
Die im Ruhezustand auf der Platte liegende Datei ist **`tasks.db.enc` = ChaCha20-
Poly1305( SQLCipher-AES-256-Datei )**. Das ist der einzige Artefakt, das dauerhaft
auf der Festplatte existiert — also genau in dem Moment doppelt geschützt, in dem die
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
> den **Ruhezustand** — das ist der Zustand, der bei Diebstahl/Backup zählt. Ein echter
> gleichzeitiger Per-Page-Doppel-Cipher bräuchte einen eigenen Cipher-Treiber und wäre
> Over-Engineering; *Alternative für Puristen* siehe Ende des Abschnitts.

**Punkt 3 — die Schlüssel kommen aus deiner Passphrase und liegen nie auf der Platte.**
- Beim ersten Start legst du eine **Passphrase** fest.
- Daraus werden mit **Argon2id** (hohe Kosten: viel RAM + Zeit pro Versuch) und einem
  zufällig erzeugten, gespeicherten **Salt** die beiden Schlüssel abgeleitet — `aes_key`
  (Schicht 1) und `chacha_key` (Schicht 2) als getrennte Teilstücke aus dem KDF-Output.
- Gespeichert wird **nur** der Argon2-**Hash** der Passphrase (zum Prüfen beim Entsperren)
  und das Salt — **nie** die Passphrase oder die Schlüssel selbst.
- `aes_key`/`chacha_key` existieren nur **im Arbeitsspeicher**, solange die App entsperrt
  ist. Beim Sperren/Panic werden sie verworfen.

**Punkt 4 — Microsoft-Tokens getrennt davon: keyring.**
Die Zugangs-Tokens für Microsoft liegen nicht in der DB, sondern im **Windows Credential
Manager** (über `keyring`), ans Benutzerkonto gebunden.

**Punkt 5 — Ablauf zusammengefasst:**
```
App-Start → Lock-Screen → Passphrase eingeben
   → Argon2-Hash prüfen → KDF(Passphrase, Salt) → aes_key + chacha_key
   → tasks.db.enc per ChaCha20 entpacken → Arbeitskopie
   → SQLCipher(Arbeitskopie) mit aes_key öffnen → entsperrt, UI lädt
Sperren / Schließen / Panic
   → Arbeitskopie per ChaCha20 → tasks.db.enc  → Arbeitskopie sicher löschen
   → aes_key, chacha_key, Klartext-Cache aus dem Speicher werfen
```

**Punkt 6 — was das schützt (und was nicht):**
- *Geschützt:* Wer die Datei in die Finger bekommt (verlorener Laptop, Backup,
  Cloud-Ordner), sieht ohne Passphrase nur doppelt verschlüsselten Zufallsmüll.
- *Nicht magisch geschützt:* Während die App **entsperrt läuft**, sind die Daten im
  Speicher nutzbar — wie bei jeder App. Dagegen helfen die schnelle Sperre, die
  Panik-Sperre und Auto-Sperre bei Inaktivität.

**Alternative für Puristen (optional, nicht Default):** statt Arbeitskopie auf Platte die
ganze (kleine) DB beim Entsperren in eine **In-Memory-SQLite** (`:memory:`) laden und im
Ruhezustand nur als ein einziges, doppelt verschlüsseltes Blob ablegen. Dann existiert
**nie** eine entschlüsselte Datei auf der Platte — Preis: die ganze DB wird bei jeder
Persistierung am Stück geschrieben (für ein paar hundert Aufgaben unkritisch, aber ohne
seitenweise Crash-Transaktionen auf der Platte).

> Konkrete Bibliotheken in Phase 0 (`requirements.txt`); Umsetzung in Phase 1 (Schicht 1
> beim DB-Öffnen) und Phase 11 (Argon2, Schicht 2 / Wrap-Unwrap, Lock, Panic).

> **Beide Schichten sind Pflicht.** AES-256 **und** ChaCha20-Poly1305 werden immer
> gebaut — es gibt keinen Modus ohne die zweite Schicht. Die „Alternative für Puristen"
> oben betrifft nur das *Wo* der entsperrten Arbeitskopie (Platte vs. Arbeitsspeicher),
> **nicht** ob die ChaCha20-Schicht existiert.

### B.8 Sperr-Politik — wann die Passphrase verlangt wird

Die App ist **entweder entsperrt** (Schlüssel im Speicher, UI nutzbar) **oder gesperrt**
(Lock-Screen, DB zu, Schlüssel verworfen). Genau diese Ereignisse lösen eine **Sperre**
aus, sodass danach die **Passphrase neu eingegeben** werden muss:

| Ereignis | Verhalten |
|---|---|
| Klick auf **Lock**-Button (oder `⌘/Strg+L`) | sofort sperren |
| **Emergency/Panic** (`⌘/Strg+⇧+!`) | sofort sperren + Cache leeren + offline |
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
horchen — über `WTSRegisterSessionNotification` auf das App-Fensterhandle und das
`WM_WTSSESSION_CHANGE`-Ereignis (via `ctypes` oder `pywin32`/`win32ts`). Bei
`WTS_SESSION_LOCK` (Windows wurde gesperrt) → `lock()` aufrufen. Damit ist die App beim
Zurückkommen aus der Windows-Anmeldung garantiert gesperrt.

### B.9 Eingabe-Sicherheit — Schutz vor bösartigem Sync-Inhalt (verbindlich)

Der One-Way-Sync (Cloud → lokal) ist die **größte Angriffsfläche** der App: Ein
Angreifer, der Kontrolle über das Microsoft-Konto hat (oder über eine geteilte Liste
Inhalte einschleust), kann beliebigen Text in Task-Felder schreiben. Dieser Text
landet über `graph_sync.py` in der lokalen DB und wird vom Frontend gerendert.

**Alle Daten, die aus der Microsoft Graph API stammen, gelten als _untrusted input_.**
Dasselbe gilt für jede andere externe Quelle. Folgende Regeln sind Pflicht:

#### Regel 1 — Kein `innerHTML` für Nutzerdaten (Anti-XSS)

Im Frontend darf **kein** Task-Text, Listenname oder Meta-Feld jemals über `innerHTML`,
`outerHTML` oder `insertAdjacentHTML` in den DOM eingefügt werden. Stattdessen
ausschließlich:

```js
// ✅ Sicher — Text wird als reiner Text gerendert, HTML-Tags sind wirkungslos
element.textContent = task.text;
// oder
element.appendChild(document.createTextNode(task.text));

// ❌ Verboten — öffnet XSS: <img src=x onerror="pywebview.api.panic()">
element.innerHTML = task.text;
```

**Warum kritisch:** Das Frontend läuft in PyWebView mit vollem Zugriff auf
`pywebview.api.*`. Ein XSS ist hier keine Kosmetik, sondern **Remote Code Execution
gegen das Backend** — ein Angreifer könnte `delete_list()`, `panic()`, `get_state()`
(Daten-Exfiltration) oder `sign_out()` aufrufen.

#### Regel 2 — Content Security Policy (CSP)

In `frontend/index.html` wird im `<head>` eine strikte CSP gesetzt:

```html
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
```

Das verhindert Inline-Scripts (`<script>…</script>` im DOM) selbst dann, wenn durch
einen Bug doch einmal `innerHTML` verwendet wird — **Defense-in-Depth**, genau wie bei
der Doppel-Kaskade (B.7). Die eigene `app.js` (als externe Datei) läuft weiterhin
normal.

#### Regel 3 — Parametrisierte SQL-Queries (Anti-SQL-Injection)

**Alle** SQL-Statements in `backend/db.py` und `backend/graph_sync.py` verwenden
ausschließlich parametrisierte Queries mit `?`-Platzhaltern. Keine String-Formatierung,
kein f-String, kein `.format()` für Werte — **ausnahmslos**:

```python
# ✅ Sicher — Wert wird als Daten behandelt, nie als SQL
cursor.execute("INSERT INTO tasks (id, text) VALUES (?, ?)", (task_id, task_text))

# ❌ Verboten — öffnet SQL Injection
cursor.execute(f"INSERT INTO tasks (id, text) VALUES ('{task_id}', '{task_text}')")
```

#### Regel 4 — Längen- und Zeichenvalidierung beim Sync

`graph_sync.py` validiert importierte Daten vor dem Schreiben:

- **Maximale Textlänge** pro Feld (z.B. Task-Text ≤ 4096 Zeichen, Listenname ≤ 256).
  Überlange Werte werden abgeschnitten und ein Warnhinweis geloggt.
- **Steuerzeichen** (U+0000–U+001F außer Newline/Tab) werden entfernt.

#### Regel 5 — Zukunftssicherung (Prompt Injection)

Falls in späteren Versionen KI-Features hinzukommen (Zusammenfassung, Priorisierung),
darf **kein** importierter Task-Text direkt in einen System-Prompt eingesetzt werden.
Cloud-importierte Inhalte müssen in einem separaten, klar abgegrenzten User-Kontext
an das Sprachmodell übergeben werden.

> **Auswirkung auf die Funktionalität: Null.** Alle fünf Regeln sind rein defensiv.
> Task-Texte werden exakt gleich angezeigt, die App verhält sich identisch — nur dass
> bösartiger Inhalt wirkungslos bleibt. Es ist wie das Schloss an der Tür: die Tür
> funktioniert genauso, aber ungebetene Gäste kommen nicht rein.

---

## TEIL C — Baufolge (Phase 0 bis 11)

### Phase 0 — Projektgerüst & Umgebung

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
   **`sqlcipher3-binary`** (Schicht 1, AES-256 — Pflicht), **`cryptography`** (Schicht 2,
   ChaCha20-Poly1305 — Pflicht), `argon2-cffi` (Passphrase-Hash + Schlüsselableitung).
   Verschlüsselungs-Design: **Doppel-Kaskade, siehe B.7.**
3. Virtuelle Umgebung anlegen, Abhängigkeiten installieren.

**Abnahme:** `python main.py` öffnet ein leeres PyWebView-Fenster ohne Fehler.

---

### Phase 1 — Datenbank (`backend/db.py`)

**Ziel:** SQLite-Schema steht, CRUD-Funktionen existieren, Seed-Daten lassen sich laden.

> **Wichtig:** Die Datenbank ist von Anfang an **verschlüsselt** (Doppel-Kaskade, B.7).
> In dieser Phase wird nur **Schicht 1** (SQLCipher/AES-256) gebaut; die äußere
> ChaCha20-Schicht und das echte Passphrase-Handling kommen in Phase 11 dazu. In der
> Entwicklung darf man mit einer festen Test-Passphrase / einem festen Test-`aes_key`
> arbeiten.

**Tun:**
1. `connect(aes_key)` — öffnet die SQLCipher-Arbeitskopie, setzt direkt nach dem Öffnen
   `PRAGMA key = ?` (der abgeleitete `aes_key`), dann `PRAGMA foreign_keys = ON`, und
   legt das Schema aus B.1 an, falls noch nicht vorhanden (`CREATE TABLE IF NOT EXISTS`).
   Ohne korrekten Key schlägt der erste Zugriff fehl — genau so soll es sein.
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

### Phase 2 — Bridge-API (`backend/api.py`)

**Ziel:** Die `js_api`-Klasse mit allen Methoden aus B.2, vorerst rein lokal (ohne
Microsoft/Notifications), liefert echte Daten aus der DB.

**Tun:**
1. Klasse `Api` mit je einer Methode pro Zeile in B.2. Methoden rufen `db.py` auf und
   geben JSON-fähige Dicts/Listen zurück.
2. Fehler abfangen und als `{ "error": code, "message": … }` zurückgeben.
3. `get_state()` bündelt `get_lists()` + Einstellungen + `online`/`locked`-Flags.
4. Microsoft-/Sicherheits-Methoden vorerst als Stubs (geben sinnvolle Platzhalter
   zurück), werden in Phasen 8–11 ausgefüllt.

**Abnahme:** Aus einer Python-REPL lassen sich die Api-Methoden aufrufen und liefern
plausible Daten.

---

### Phase 3 — Fenster & Verdrahtung (`main.py`)

**Ziel:** Backend und Frontend hängen zusammen; das Frontend kann `pywebview.api.*`
aufrufen.

**Tun:**
1. `Api`-Instanz erzeugen, `webview.create_window("NoaToDo", "frontend/index.html",
   js_api=api, width=1200, height=800, min_size=(900, 600))`.
2. `webview.start()` — unter Windows die WebView2-Engine.
3. Backend → Frontend: eine Hilfsfunktion, die `window.evaluate_js("window.noa.…")`
   ausführt (für Sync-/Notification-Events).
4. Platzhalter für den **Windows-Sitzungssperre-Hook** vorsehen (Registrierung des
   Fensterhandles für `WM_WTSSESSION_CHANGE`); echte Logik kommt in Phase 11/B.8.

**Abnahme:** Das geladene `index.html` kann `await pywebview.api.get_state()` aufrufen
und bekommt die echten Seed-Daten (kurz in der DevTools-Konsole prüfen).

---

### Phase 4 — Frontend-Gerüst (`frontend/index.html`)

**Ziel:** Grundgerüst der Seite mit `#root`, eingebundenem CSS/JS, ohne fertiges Design.

**Tun:**
1. `index.html`: `<head>` mit `style.css`, `<body>` mit `<div class="app" id="root">`,
   am Ende `<script src="app.js">`.
2. Eine `boot()`-Funktion in `app.js`, die auf `pywebviewready` wartet,
   `get_state()` holt und einen Platzhalter rendert.

**Abnahme:** Beim Start erscheint kurz „Unpacking/Loading" bzw. ein Platzhalter, dann
die geladenen Listennamen als simple `<ul>` — Beweis, dass die Bridge im echten Fenster
funktioniert.

---

### Phase 5 — Design-System (`frontend/style.css`) + Fonts

**Ziel:** Das komplette, exakte Aussehen aus dem Konzept ist verfügbar.

**Tun:**
1. **CSS extrahieren:** Die `<style>`-Sektion aus `NoaToDo UI Konzept.html` ist im
   eingebetteten Template hinterlegt (das HTML ist ein „Bundler" — der echte Markup-/
   CSS-Inhalt steckt im `<script type="__bundler/template">`-Block als JSON-String, das
   große Asset-Manifest in `<script type="__bundler/manifest">`). Den Template-String
   JSON-dekodieren, daraus die `<style>…</style>` nehmen und nach `style.css` schreiben.
   *Alternativ* das Konzept-HTML einmal im Browser öffnen und das gerenderte CSS
   übernehmen. Wichtig: **unverändert** übernehmen (Tokens aus B.3 sind darin enthalten).
2. **Fonts lokal:** JetBrains Mono (400/500/600/700) und Space Grotesk (400/500/600/700)
   als `.woff2` in `frontend/fonts/` legen und die `@font-face`-`src`-URLs im CSS auf
   diese lokalen Dateien zeigen lassen (statt der UUID-Platzhalter aus dem Bundle). Kein
   externer Google-Fonts-Abruf — passt zu local-first.
3. `data-theme`, `data-density`, `data-toolbar`, `data-sidebar` und `--accent` werden
   später von `app.js` auf `.app` gesetzt.

**Abnahme:** Eine statische Test-Markup-Probe (z.B. ein Header + zwei Task-Karten)
sieht exakt aus wie im Konzept — Farben, Schriften, Rundungen, Schatten stimmen in Dark
und Light.

---

### Phase 6 — Frontend-Logik (`frontend/app.js`)

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
| `Icons` | `Icons` (Objekt) | die SVG-Icons (siehe **Anhang 2** — 1:1 aus Konzept) |

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
   (killt Transitions für einen Frame) — exakt wie im Konzept.
5. **Backend-Events**: `window.noa.onSyncDone/onNotification/onLocked` definieren.

**Abnahme:** Alle im Konzept sichtbaren Interaktionen funktionieren mit echten Daten:
Aufgaben abhaken, anlegen, Listen wechseln/anlegen/umbenennen/löschen, Toolbar-Aktionen,
Modals, Lock-Screen, Toasts, Theme/Accent/Dichte/Toolbar/Sidebar umschalten,
Tastenkürzel, Focus-Modus. Optisch deckungsgleich mit `NoaToDo UI Konzept.html`.

> **Meilenstein:** Nach Phase 6 ist die App als **lokale** To-Do-App voll benutzbar.
> Die Phasen 7–11 ergänzen Microsoft-Sync, Benachrichtigungen und die Sicherheits-
> Tiefe. Sie sind unabhängig und können einzeln umgesetzt werden.

---

### Phase 7 — Export & Kopieren (`backend/api.py` ausbauen)

**Ziel:** `export_list` und `copy_list` erzeugen echte Inhalte.

**Tun:**
1. `export_list(id, 'md')` → Markdown (Überschrift = Listenname, `- [ ]`/`- [x]` je
   Aufgabe, Meta in Klammern). `'txt'` und `'json'` analog. Über PyWebViews
   Save-Dialog speichern.
2. `copy_list(id)` → Klartext der Liste; das Frontend legt ihn via
   `navigator.clipboard.writeText` ab und zeigt Toast „Copied to clipboard".

**Abnahme:** Export schreibt eine korrekte `.md`-Datei; Kopieren landet im Clipboard.

---

### Phase 8 — Microsoft-Login (`backend/auth.py`)

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

**Abnahme:** Nach `sign_in()` liefert `get_status()` „Microsoft Graph: Tasks.Read ·
token valid"; nach Neustart bleibt man angemeldet (Refresh-Token).

---

### Phase 9 — Sync Cloud → Lokal (`backend/graph_sync.py`)

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
7. **Konfliktregel für importierte Aufgaben:** siehe Entscheidung D.1 — Default
   umsetzen.

**Abnahme:** Eine im Handy/MS-To-Do geänderte Aufgabe erscheint nach dem nächsten Sync
lokal; ein zweiter Sync direkt danach überträgt (dank Delta) (fast) nichts.

---

### Phase 10 — Lokale Benachrichtigungen (`backend/notify.py`)

**Ziel:** Erinnerungen und Sync-Hinweise als Windows-Toasts.

**Tun:**
1. `winotify` (Fallback `plyer`) für native Windows-Benachrichtigungen.
2. Auslöser: fällige Aufgaben (`due_at`), abgeschlossener Sync, geschriebenes Backup.
3. Jede Benachrichtigung zusätzlich in das In-App-NotifMenu einspeisen
   (`on_notification`).

**Abnahme:** Eine Aufgabe mit naher Fälligkeit erzeugt zur richtigen Zeit einen
Windows-Toast und einen Eintrag im Glocken-Menü.

---

### Phase 11 — Sicherheits-Tiefe (`backend/security.py`)

**Ziel:** Lock-Screen, Emergency/Panic und (optional) Datenbank-Verschlüsselung real
machen — das Kernversprechen „sicherer als Microsoft To Do".

**Tun:**
1. **App-Sperre nach der Sperr-Politik aus B.8:** `lock()` setzt `locked=True`, verwirft
   die Schlüssel, packt die DB wieder zu (Schicht 2) und zeigt den LockScreen über allem.
   `unlock(passphrase)` prüft den Argon2-Hash, leitet die Schlüssel ab und öffnet die DB.
   Sperre auslösen bei: Lock-Button/`⌘L`, Panic, **App-Start** (immer gesperrt starten),
   **Auto-Sperre nach Inaktivität** (einstellbarer Timeout, Default ~15 min) und
   **Windows-Sitzungssperre**. Letztere via `WTSRegisterSessionNotification` +
   `WM_WTSSESSION_CHANGE` → bei `WTS_SESSION_LOCK` `lock()` aufrufen (Registrierung beim
   Fensterstart in Phase 3/`main.py`). **Kein** Sperren bei Minimieren/Fokuswechsel.
2. **Emergency/Panic** (`panic()`): sofort sperren, Frontend-Cache leeren
   (`state.lists=[]` und neu sperren), Sync pausieren/offline schalten. Nichts löschen.
3. **DB-Verschlüsselung — Doppel-Kaskade (Pflicht):** vollständige Umsetzung von **B.7**.
   - Argon2id-Schlüsselableitung aus der Passphrase (Salt erzeugen/speichern, nur den
     Argon2-Hash der Passphrase ablegen) → `aes_key` + `chacha_key`.
   - **Schicht 2 (ChaCha20-Poly1305) Wrap/Unwrap:** beim Entsperren `tasks.db.enc`
     entpacken → SQLCipher-Arbeitskopie; beim Sperren/Schließen/Panic wieder einpacken
     und die Klartext-Arbeitskopie **sicher löschen**.
   - Beim Start ohne korrekte Passphrase bleibt die App im Lock-Screen und kann die DB
     gar nicht öffnen. Damit stimmen Status-Anzeige und Lock-Text
     („LOCAL VAULT · ENCRYPTED") real, nicht nur optisch.
   - `panic()` zusätzlich: Schlüssel + Klartext-Cache sofort verwerfen, Arbeitskopie
     löschen, offline schalten.
4. `get_status()` liefert echte Werte (DB-Größe, Verschlüsselungs-Status, Token-Status,
   letzter Sync, WebView2-Version).

**Abnahme:** Sperren/Entsperren funktioniert mit Passphrase; Panic sperrt sofort und
pausiert Sync; bei aktivierter Verschlüsselung ist `tasks.db` ohne Passphrase nicht
lesbar.

---

## TEIL D — Offene Entscheidungen & Erweiterungen

### D.1 Konflikt bei importierten Aufgaben (aus technische Grundlage §6)

Wenn sich eine **importierte** Aufgabe gleichzeitig in der Cloud und lokal ändert:

- **Option A — Cloud besitzt importierte Aufgaben** *(empfohlener Default)*: Beim Sync
  überschreibt der Microsoft-Stand lokale Änderungen an importierten Aufgaben.
  Begründung: Scope ist `Tasks.Read`, der Import ist konzeptionell ein Spiegel. Einfach,
  vorhersehbar, keine Geister-Divergenz.
- **Option B — Eingefrorene Kopie**: Eine importierte Aufgabe wird einmal kopiert und
  danach von Microsoft nicht mehr angefasst. Mehr „local-first", aber keine späteren
  Updates aus der Cloud.

> Rein lokale Aufgaben (`source='local'`) sind **nie** betroffen — sie gehören immer dem
> Nutzer. Default in diesem Plan: **A**. Beim Bau als Einstellung vorsehen, falls der
> Nutzer später B möchte.

### D.2 Was lokal bleibt / was aus der Cloud kommt (Privatsphäre)

- **Lokal:** alle selbst erstellten Aufgaben, alle Bearbeitungen, die gesamte SQLite-DB,
  die Tokens (in `keyring`).
- **Aus der Cloud:** ausschließlich die aus Microsoft To Do **gelesenen** Aufgaben.
- Ehrliche Einordnung: Diese Cloud-Daten liegen ohnehin schon bei Microsoft. Der Gewinn
  ist, dass aus dieser App **nichts** dorthin zurückfließt.

### D.3 Mögliche spätere Erweiterungen (nicht im Kern-Scope)

- Unterpunkte/Checklisten je Aufgabe, Fälligkeiten-UI, Wiederholungen.
- Volltextsuche, Filter „wichtige Aufgaben" (in der Skizze angedeutet).
- Mehrere Akzent-/Theme-Presets, anpassbare Dichte je Liste.
- Automatische lokale Backups von `tasks.db` (verschlüsselt) mit Rotation.

---

## ANHANG 1 — Seed-Daten (Startfüllung der DB)

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
  - offen: „Lisbon — Alfama walking route", „Kyoto in shoulder season",
    „Dolomites hut-to-hut", „Reykjavík stopover", „Faroe Islands",
    „Patagonia (someday)"
- **Life Goals** (lokal)
  - offen: „Run a half marathon", „Learn conversational Japanese",
    „Read 24 books this year", „Visit grandparents monthly",
    „Plant a small herb garden"

## ANHANG 2 — Icon-Set

Das Konzept bringt ein eigenes, konsistentes Line-Art-Icon-Set mit (24er-Grid,
Strichstärke 1.7, runde Enden). Diese SVG-Pfade **1:1 aus dem Konzept übernehmen**
(`Icons`-Objekt). Benötigte Icons: `Menu, Close, Shield, Bell, Plus, Check, Gear,
Chevron, Grip, Plane, Wifi, Expand, Palette, Share, Help, Lock, Unlock, Alert, Copy,
Pencil, Trash, Diag, Globe, Note, Sun, Moon, User, Logout, Pin, Download`. Das
App-Logo (`NoaToDo Logo.png`, orangenes „N" im Kreis) zusätzlich als Fenster-/Taskbar-
Icon verwenden.

---

## Schnell-Checkliste (für die ausführende KI)

- [ ] Phase 0 — Struktur + Abhängigkeiten, leeres Fenster
- [ ] Phase 1 — `db.py` Schema + CRUD + Seed
- [ ] Phase 2 — `api.py` Bridge (lokal)
- [ ] Phase 3 — `main.py` Fenster + Verdrahtung
- [ ] Phase 4 — `index.html` Gerüst, Bridge im Fenster bewiesen
- [ ] Phase 5 — `style.css` (CSS 1:1 aus Konzept) + lokale Fonts
- [ ] Phase 6 — `app.js` komplette UI + Interaktionen  ← **lokal voll nutzbar**
- [ ] Phase 7 — Export & Copy
- [ ] Phase 8 — MSAL-Login (`Tasks.Read`, keyring)
- [ ] Phase 9 — Delta-Sync Cloud → SQLite (einseitig)
- [ ] Phase 10 — Benachrichtigungen (winotify)
- [ ] Phase 11 — Lock / Emergency / Doppel-Kaskade AES-256 + ChaCha20 (B.7)
