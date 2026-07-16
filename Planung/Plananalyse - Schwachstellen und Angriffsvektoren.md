# Plananalyse: Widersprüche, strukturelle Mängel, Ratestellen und Angriffsvektoren

Stand: 2026-07-12, **Neufassung nach Commit 157cc66** ("Microsoft-Sync und Notifications
entfernt, N11-Planung eingearbeitet"). Diese Fassung ersetzt die frühere vollständig
(die analysierte noch den Stand mit Microsoft-Sync und ist damit hinfällig).

Analysierte Dokumente: `Planung/Bauplan - NoaToDo.md` (Hauptgegenstand, 1747 Zeilen),
`CLAUDE.md`, `Planung/weiteres/technische Grundlage.txt`,
`Planung/weiteres/UX-UI Verbesserungen.md`. Wo der Plan Aussagen über den Code macht,
wurde der tatsächliche Code auf dem Stand von 157cc66 als Beleg herangezogen
(`Code/backend/api.py`, `Code/backend/db.py`, `Code/main.py`, `Code/frontend/*`).
Zeilenangaben beziehen sich auf diesen Stand.

## Vorbemerkung: was N11 bereits sauber gelöst hat

Zur Einordnung, damit dieses Dokument nicht Erledigtes wiederkäut. Der Nachtrag N11
(2026-07-09) hat mehrere der schwersten früheren Plan-Probleme explizit und gut gelöst:

- **N11.9 + Gate G28** lösen den früheren Kernkonflikt "G6 In-Memory vs. Doppel-Kaskade
  am Ruhezustand" (beide Schichten bleiben real, Klartext nie auf Platte, Fallback
  definiert, Beweis-Gate). Das war zuvor die grösste ungeklärte Designfrage.
- **N11.8.1** löst den Konflikt "Killswitch braucht DB-Zugriff vs. G13 erlaubt ihn
  gesperrt" (Datei-Löschung statt DB-Operation).
- **N11.8.2** definiert die Start-Weiche (Onboarding vs. Lock-Screen) eindeutig.
- **N11.8.4** entscheidet die Win+L-Frage bewusst (kein WTS-Hook, Auto-Sperre als
  einzige verlässliche Sperre).
- **N11.3/N11.4** legen Passphrase-Politik, Reset-Weg und ein konkretes
  Entsperr-Rate-Limit fest und entscheiden die Recovery-Frage bewusst (kein Export,
  Konto-Bindung akzeptiert).
- **Phase 8 Punkt 2** benennt das Fenster-X-Leck (X muss denselben sicheren
  Beenden-Pfad nehmen wie `quit_app()`), inklusive gemeinsamer Routine und
  `atexit`-Rückfalllinie.
- Die Entfernung von Sync und Benachrichtigungen eliminiert nebenbei ganze
  Angriffsklassen (eingehender Untrusted-Kanal, Token-Handling, Toast-Inhalte in der
  Windows-Notification-DB). Die zugehörigen Gates G1-G5, G10, G24 wurden folgerichtig
  entfernt; zu einem dabei entstandenen Loch siehe S6.

Der Rest dieses Dokuments listet, was **danach noch** widersprüchlich, lückenhaft
oder ungeklärt ist. Gliederung:

- **Teil 1 (W1-W18):** Stellen, an denen der Plan sich selbst (oder CLAUDE.md/Code) widerspricht.
- **Teil 2 (S1-S7):** strukturelle Mängel des Plans als Dokument und Prozess.
- **Teil 3 (U1-U25):** Unklarheiten und Ratestellen: überall dort müsste eine
  ausführende KI heute raten. Das ist der Schwerpunkt dieser Fassung.
- **Teil 4 (V1-V12):** Detail-Verbesserungen an bestehenden Gates.
- **Teil 5 (A1-A7):** Angriffsvektoren, die der Plan nicht abdeckt. ✅ Alle sieben
  am 2026-07-15 entschieden und in den Bauplan übernommen (Gates G31 bis G34,
  G27-Ergänzung, B.4-Titelregel).
- **Teil 6:** Vorschläge für neue Gates (ab **G29**, da N11.9 die Nummer G28 inzwischen
  selbst vergeben hat) und eine priorisierte Reihenfolge.

---

## TEIL 1: Widersprüche

### W1. Sperre vs. echter Flugmodus: N10 und N11.5 widersprechen sich, und die Kopplung ist als Ganzes gefährlich [Sec]

> **[ENTSCHIEDEN 2026-07-13, im Bauplan als Nachtrag N11.10 festgeschrieben: Linie 1
> (entkoppeln). Die Sperre (Lock-Button, `Ctrl+L`, Auto-Sperre) schaltet
> nicht mehr offline und fasst den Funkzustand in keiner Richtung an, das Internet
> bleibt beim Sperren normal verfügbar. Funk wird nur noch beim expliziten Nutzer-Toggle
> (Pill/`G`) und im Panik-Flow geschaltet; die Wiederherstellung des Ausgangszustands
> passiert nur beim Beenden als letzter Schritt; für den Crash-Fall wird der
> Funk-Ausgangszustand in `config.json` persistiert. Die entsprechenden Stellen im
> Bauplan (B.8-Tabelle, B.8-Verschärfung, Bridge-Tabelle `lock()`, N5, N10.1, N11.5)
> wurden revidiert. Das Problem ist damit behoben.]**

Der schwerste neue Widerspruch, weil er reales Fehlverhalten am System des Nutzers
produzierte:

- **N10.1** (Zeile 1339-1346): Jede Sperre "schaltet offline", und: "Offline bleibt
  die App, bis der Nutzer es bewusst wieder einschaltet."
- **N11.5** (Zeile 1509-1513): "Beim **Sperren**/Panik/Beenden wird der Funk-Zustand
  von **vor** dem App-Start wiederhergestellt", als letzter Schritt.

Für den Sperr-Fall sind das zwei unvereinbare Anweisungen: bleibt die App nach dem
Sperren offline (N10) oder werden die Funkgeräte wiederhergestellt (N11.5)? Eine
ausführende KI muss raten.

Dahinter liegt ein grösseres Problem: Seit N11.5 heisst "offline schalten" nicht mehr
"ein lokales Flag setzen", sondern **die physischen Funkgeräte des ganzen Rechners
ausschalten**. In Kombination mit N10 ("jede Sperre schaltet offline") und der
Auto-Sperre (Default 15 Minuten, N11.4) ergibt sich wörtlich gelesen: **Die To-Do-App
schaltet alle 15 Minuten Inaktivität das WLAN und Bluetooth des gesamten PCs ab**,
z.B. während der Nutzer in einem anderen Fenster ein Video streamt. Dazu kommt: Nach
einem App-Crash bleibt der Funk aus (die Wiederherstellung läuft nur im sauberen
Beenden-Pfad), und die App hat seit der Sync-Entfernung **gar keine eigene
Netzwerkfunktion mehr**, das Offline-Schalten beim Sperren schützt also nichts
App-eigenes.

**Patch-Vorschlag (Entscheidung nötig, eine der beiden Linien):**
1. **Entkoppeln (empfohlen):** Die Funk-Schaltung passiert ausschliesslich bei
   explizitem Nutzer-Toggle (Pill/`G`-Taste). Sperre/Auto-Sperre fassen den Funk
   **nicht** an; der N10-Satz "offline schalten" wird gestrichen oder auf "App-Anzeige
   auf offline" reduziert. Wiederherstellung des Ausgangszustands nur beim Beenden
   (und dort als letzter Schritt, wie N11.5 sagt). Zusätzlich definieren, was bei
   einem Crash gilt (ehrlich: Funk bleibt wie zuletzt geschaltet; ein Wiederanlauf
   stellt den gemerkten Ausgangszustand wieder her, der dafür in `config.json`
   persistiert sein muss, nicht nur im RAM).
2. Oder: Sperre schaltet bewusst funkstill (Bunker-Verhalten), dann muss N11.5 die
   Wiederherstellung beim **Sperren** streichen (nur beim Beenden) und der Plan muss
   die Auto-Sperren-Konsequenz (WLAN-Kill alle 15 min) ausdrücklich benennen und
   wollen. Realistisch will das niemand; darum Empfehlung Linie 1.

### W2. Phase 8 "Tun" beschreibt weiterhin das alte, verworfene Krypto-Design  ✅ ERLEDIGT

> **[ERLEDIGT: im Bauplan behoben (Marker 2026-07-16 nachgetragen). Die
> normative G15-Zeile, B.7 (Schlüsselableitung) und der Phase-8-Unlock-Ablauf
> beschreiben jetzt durchgängig das G15/N11.9-Design: Pepper-gebundenes `ikm` ->
> Argon2id -> **ein** Master-Secret -> HKDF-SHA256 mit getrennten `info`-Labels;
> es wird **kein** Argon2-/Verifikations-Hash gespeichert (Prüfung implizit über den
> Poly1305-Tag), und es gibt keine unverschlüsselte Klartext-Arbeitskopie
> (In-Memory bevorzugt, sonst SQLCipher-verschlüsselte Arbeitsdatei). Die alten
> Formulierungen ("Argon2-Hash prüfen/ablegen", "Klartext-Arbeitskopie") sind
> ersetzt, G15 vermerkt das ausdrücklich ("Ersetzt die ältere Formulierung in
> B.7"). Der ursprüngliche Befund steht unverändert darunter.]**

Die Arbeitsanweisung der wichtigsten Phase widerspricht ihren eigenen Gates:

- Phase 8 Tun 1 (Zeile 978): "`unlock(passphrase)` **prüft den Argon2-Hash**".
- Phase 8 Tun 3 (Zeile 1007-1008): "nur den **Argon2-Hash der Passphrase ablegen**".
- Phase 8 Tun 3 (Zeile 1009-1011): Arbeitskopie auf Platte entpacken und
  "Klartext-Arbeitskopie **sicher löschen**".

Alle drei sind durch G15 (kein Verifikations-Hash, Prüfung über den Poly1305-Tag)
bzw. N11.9 (nie eine Klartext-Arbeitskopie auf der Platte, In-Memory bevorzugt)
verbindlich überholt, stehen aber uneingeschränkt in der Tun-Liste. Dasselbe alte
Design steht ausserdem unverändert in B.7 Punkt 3 (Zeile 381-383: "Argon2-Hash ...
gespeichert", "Teilstücke aus dem KDF-Output") und B.7 Punkt 5 (Zeile 405:
"Argon2-Hash prüfen"); die "Präzisierung"-Box (Zeile 387) korrigiert das zwar, aber
der falsche Text bleibt der Haupttext. Der B.7-Schicht-2-Absatz (Zeile 361-366) nennt
die Arbeitskopie zudem "unverschlüsselt", was N11.9 direkt widerspricht (die
Arbeitskopie ist dort per Definition AES-Chiffretext); nur die Ehrlichkeits-Notiz
darunter trägt einen "[Ueberholt durch N11.9]"-Marker, der Schicht-2-Absatz selbst
nicht.

**Wirkung:** Wer Phase 8 "von oben nach unten" abarbeitet (die erklärte Leseregel des
Plans), baut einen gespeicherten Passphrase-Hash (= das Offline-Orakel, das G15
verhindern soll) und eine Klartext-Temp-Datei (= die Forensik-Klasse, die G6/N11.9
eliminieren sollen).

**Patch:** Phase 8 Tun 1 und 3 sowie B.7 Punkt 3/Punkt 5/Schicht-2-Absatz auf den
G15/N11.9-Stand umschreiben (Master-Secret, HKDF, AEAD-Prüfung, In-Memory bzw.
verschlüsselter Fallback). Die "Präzisierung"-Box wird danach überflüssig.

### W3. Die G14-Definitionszeile fordert immer noch `private_mode=True`  ✅ ERLEDIGT

> **[ERLEDIGT: im Bauplan behoben (Marker 2026-07-16 nachgetragen). Die normative
> G14-Zeile schreibt jetzt den umgesetzten Stand fest: fester, benutzerprivater
> Profilordner mit `private_mode=False` + `storage_path=PROFILE_DIR`, zwingend
> zusammen mit dem G19-Mutex; `private_mode=True` ist ausdrücklich "ersatzlos
> gestrichen und darf nicht wieder eingebaut werden". Offen bleibt (korrekt, als
> Phase-8-Rest) nur das sichere Wischen bei Lock/Panik/Quit inkl. Fenster-X und die
> verwaisten `msedgewebview2.exe`. Der ursprüngliche Befund steht unverändert
> darunter.]**

Die B.9-Tabellenzeile G14 (Zeile 525) sagt wörtlich: "Pflicht: `webview.start(...,
private_mode=True)` **explizit** setzen". Das Gegenteil ist seit 2026-06-20 umgesetzt
und dokumentiert: fester Profilordner mit `private_mode=False` (Phase-8-G14-Langtext
Zeile 1059 ff., CLAUDE.md: "Do NOT reintroduce `private_mode=True`", N11.8.3 baut
darauf auf). Der Privatmodus verursachte real die Temp-Profil-Altlasten und
Starthänger. Diese Zeile hat jetzt zwei grosse Plan-Überarbeitungen überlebt; sie ist
eine scharfe Regressionsfalle, weil die B.9-Tabelle als "verbindlich und vom Nutzer
bestätigt" markiert ist.

**Patch:** Die Zeile neu schreiben: fester Profilordner + Mutex = umgesetzter Stand;
offen nur sicheres Wischen bei lock/panic/quit inkl. Fenster-X sowie verwaiste
`msedgewebview2.exe`. `private_mode=True` muss ersatzlos raus.

### W4. G13 existiert in drei Fassungen, zwei davon veraltet  ✅ ERLEDIGT

> **[ERLEDIGT: im Bauplan behoben (Marker 2026-07-16 nachgetragen). G13 ist jetzt
> **eine** normative Zeile in der B.9-Tabelle, formuliert als explizite Allowlist
> `ALLOWED_WHEN_LOCKED` (acht Methoden nach dem U1/N11.13-Entscheid), mit dem
> ausdrücklichen Vermerk, dass Phasen und Schnellübersicht nur noch die Nummer
> führen. Die Phase-8-Gateliste und die Phase-9-Testliste sind angeglichen (Test:
> "jede Bridge-Methode ausserhalb der Allowlist liefert `locked`", `quit_app`/
> `killswitch` funktionieren gesperrt). `lock`/`panic` sind bewusst gesperrt (V4).
> Der ursprüngliche Befund steht unverändert darunter.]**

- Phase-8-G13 (Zeile 1052-1058) und N10.5 (Zeile 1386-1389): erlaubt im gesperrten
  Zustand sind `unlock`, `quit_app`, `killswitch` (bewusste Ausnahmen).
- B.9-Tabellenzeile G13 (Zeile 524): "jede Methode ausser `unlock(passphrase)`".
- Schnellübersicht (Zeile 1729): "jede Methode ausser `unlock`".
- Phase-9-Testliste (Zeile 1148-1149): Der Test soll prüfen, dass "jede Bridge-Methode
  ausser `unlock`" gesperrt `locked` liefert. Wer diesen Test schreibt, markiert
  `quit_app`/`killswitch` fälschlich als Sicherheitslücke oder blockt sie, womit
  Off-Knopf und Killswitch im gesperrten Zustand brechen (genau dort müssen sie
  funktionieren).

**Patch:** Alle drei Nebenfassungen auf die Dreier-Ausnahme angleichen; besser noch
als Allowlist formulieren (siehe V4).

### W5. Der Panik-/Notfall-Hotkey: vier Quellen, drei verschiedene Aussagen

> **[ENTSCHIEDEN 2026-07-13, im Bauplan in N5 festgeschrieben: Der Hotkey
> `Ctrl+Shift+!` ist ersatzlos gestrichen. Es gibt keinen Panik- oder
> Notfall-Hotkey; der Panik-Flow ist nur per Maus über den Rail-Knopf erreichbar,
> und `Ctrl+L` deckt den "schnell alles zu"-Fall ab (jede Sperre ist seit N10
> verstärkt). B.4, B.5, B.8, N5, N11.10 und CLAUDE.md wurden angeglichen; im Code
> war der Hotkey nie verdrahtet, dort war nichts zu entfernen. U22 entfällt damit
> ebenfalls. Das Problem ist damit behoben.]**

- B.5 (Zeile 310) und B.4 Toolbar Punkt 6 (Zeile 265): `Ctrl+Shift+!` existiert als
  "Notfall-Sperre" bzw. öffnet das Panik-Modal.
- N5 (Zeile 1290-1293), Soll: `Ctrl+Shift+!` löst **ohne Rückfrage die verstärkte
  Sperre** aus (nicht den Panik-Flow).
- Code (app.js:1722-1723): "Der Panik-Trigger hat **bewusst KEIN Tastenkuerzel**";
  tatsächlich ist im globalen Key-Handler gar kein `Ctrl+Shift+!` verdrahtet, der
  Hotkey tut heute **nichts**.
- CLAUDE.md B.5: "Panic lock | `Ctrl+Shift+!`" als bestehender Shortcut.

**Patch:** Entscheidung fixieren (die N5-Linie ist die durchdachteste: Hotkey =
sofortige verstärkte Sperre, Panik-Flow nur per Maus) und dann B.4, B.5, CLAUDE.md
und den Code (Hotkey implementieren!) in einem Zug angleichen. Falls der Hotkey
kommt: Layout-Tücke beachten (U22).

### W6. B.5 (als "verbindlich" markiert) beschreibt nicht die verbindlichen Shortcuts

> **[ERLEDIGT 2026-07-13: B.5 wurde vollständig aus dem realen `onKeyGlobal` (plus
> Feld-Handler) neu abgeleitet und als einzige Wahrheit markiert, inklusive
> Bedingungen (offene Liste, Sidebar offen, Toggle-Verhalten), der bewusst
> kürzel-losen Aktionen (Panik, Kopieren, Mini-Modus), der Maus-Gesten und der
> Tipp-/Sperr-Regeln. Die Lücken aus UX-Audit 2.3 sind mitgeschlossen: das
> Shortcuts-Modal in `app.js` zeigt jetzt auch `Esc`, `?`, die Maus-Gesten und den
> Rail-only-Hinweis (reine Anzeige-Ergänzung, an den Kürzeln selbst wurde nichts
> geändert). Die CLAUDE.md-Tabelle wurde angeglichen. `Ctrl+Shift+!` ist inzwischen
> ersatzlos gestrichen (W5-Entscheid vom 2026-07-13, Bauplan N5) und kommt weder in
> B.5 noch im Shortcuts-Modal noch im Code vor.]**

Bauplan B.5 (Zeile 301-317) sagt "Neue Liste | `N`" und kennt weder `Ctrl+N` (neue
Aufgabe) noch `Ctrl+Shift+N` (neue Liste) noch `Ctrl+1`-`Ctrl+9` (Liste öffnen) noch
`Ctrl+Pfeil` (Listenwechsel). Der Code (app.js:1686-1740) und CLAUDE.md haben genau
diese; ein blankes `N` gibt es nicht mehr. Eine "verbindliche" Tabelle, die falsch
ist, ist schlimmer als keine: Sie lädt dazu ein, das alte Verhalten
"wiederherzustellen".

**Patch:** B.5 einmal vollständig aus dem realen `onKeyGlobal` ableiten und als
einzige Wahrheit führen (CLAUDE.md verweist darauf oder wird mitgepflegt). Dabei die
Lücken aus dem UX-Audit 2.3 mitschliessen (Shortcuts-Modal: `Esc`, `?`, Doppelklick,
Mini-Modus).

### W7. Win+L-Reste: drei Stellen behaupten weiterhin die Sitzungssperre als Auslöser

**[ERLEDIGT am 2026-07-13.]** Alle drei Stellen sind gepatcht: die B.8-Kernregel nennt
jetzt explizites Sperren, abgelaufene Auto-Sperre und Prozess-Neustart (Win+L steht in der
"KEINE Sperre"-Liste), die B.8-Tabellenzeile "Windows-Sperre" und der WTS-Hook-Absatz sind
entfernt, N10.1 nennt statt der Sitzungssperre die Auto-Sperre, und die Lock-Policy in
CLAUDE.md führt Win+L unter "No lock on" mit dem ausdrücklichen Verbot, einen WTS-Hook
nachzurüsten. Der Befund unten ist nur noch Historie.

N11.8.4 entscheidet: Win+L löst **keine** App-Sperre aus. Unkorrigiert blieben:

- B.8-Kernregel (Zeile 454-456): "Eine Sperre passiert nur bei explizitem Sperren,
  bei **Windows-Sitzungssperre** und bei echtem Prozess-Neustart."
- N10.1 (Zeile 1339-1340): "Jede Sperre (Lock-Button, `Ctrl+L`, später Auto-Lock und
  **Windows-Sitzungssperre**) ..."
- **CLAUDE.md**, Abschnitt "Lock policy (B.8)": listet "Windows session lock
  (`WTS_SESSION_LOCK` via `WTSRegisterSessionNotification`)" als Sperr-Trigger.
  CLAUDE.md ist die Datei, die jede Arbeits-Session zuerst liest; sie widerspricht
  hier direkt dem verbindlichen N11.8.4.

**Patch:** Alle drei Stellen streichen/anpassen (die B.8-Tabellenzeile wurde ja
bereits vorbildlich mit dem N11.8.4-Vermerk gepatcht, nur der Rest fehlt).

### W8. G8 verlangt einen Stärkemesser, N11.3 verbietet ihn  ✅ ERLEDIGT (2026-07-13)

**Status: behoben im Bauplan.** Der G8-Text ist an allen vier Stellen (Gate-Tabelle
B.9, Phase-8-Gate-Text, Abnahme Phase 8, Gate-Übersicht am Ende) auf die
Passphrase-Politik aus N11.3 umgestellt: **ausschliesslich Mindestlänge 12 Zeichen**,
kein Stärkemesser, keine Stärke-Anzeige, keine Zeichenklassen-Regeln, keine
Wörterbuch-Prüfung. Die alte Forderung "erzwungene Passphrase-Stärke mit
Stärke-Anzeige" ist gestrichen, nicht nur konkretisiert; ein Stärkemesser wäre jetzt
ein Regelverstoss. N11.3 hält die ehrliche Konsequenz fest: `aaaaaaaaaaaa` ist gültig,
und gegen schwache Passphrasen verteidigen dann nur noch die Argon2id-Kosten und der
DPAPI-Pepper. Das ist eine bewusste Entscheidung des Nutzers, keine offene Lücke.
Der ursprüngliche Befund steht unverändert darunter.

G8 (Zeile 497 und 1037-1038) verlangte "**erzwungene Passphrase-Stärke**
(Stärke-Anzeige beim Einrichten)". N11.3 (Zeile 1465-1468) entscheidet: "nur
Mindestlänge 12 Zeichen. Keine weiteren Zeichenregeln, **kein Stärkemesser-Zwang**"
und erklärt, G8 werde damit konkretisiert. Die Vorrangregel ("im Zweifel gilt N11")
rettet das formal, aber der Gate-Text selbst ist unkorrigiert; wer die Gates als
Checkliste abarbeitet, baut den Stärkemesser.

**Patch:** G8-Text an beiden Stellen um einen Halbsatz ergänzen ("Passphrase-Politik
konkretisiert in N11.3: nur Mindestlänge 12"). Eine ehrliche Restnotiz lohnt sich:
Mit "nur Länge 12" ist `aaaaaaaaaaaa` gültig; das ist die bewusste Entscheidung des
Nutzers, aber der Plan sollte festhalten, dass dann Argon2-Kosten und Pepper die
einzige Verteidigung gegen schwache Passphrasen sind (keine erneute Debatte nötig,
nur die Konsequenz dokumentieren).

### W9. N7 plant "Clear completed" weiterhin fest ein, N11 hat es gestrichen

> **[ERLEDIGT 2026-07-13: Der N7-Punkt "Clear completed (UX 3.8)" ist im Bauplan
> durchgestrichen und als "wird nicht gebaut" markiert (gleiches Muster wie in N8,
> mit Verweis auf N11.2/N11.7). Das Problem ist damit behoben.]**

N7 (Zeile 1313-1315) führt "Clear completed (UX 3.8)" unter "fest eingeplant"; N11.2
(Zeile 1449-1450) und N11.7 (Zeile 1549) sagen "wird **nicht** gebaut". N8 hat für
seine gestrichenen Punkte Durchstreichungen bekommen, N7 nicht.

**Patch:** Den N7-Punkt durchstreichen oder entfernen (gleiches Muster wie in N8).

### W10. "Optional"-Reste und Geister-Features in A.1/A.2/Phase 8

**[ERLEDIGT am 2026-07-13.]** Alle fünf Stellen sind bereinigt: A.1 Punkt 2 nennt die
Sperre zwingend, die Verschlüsselung immer aktiv (doppelt, kein abschaltbarer Modus, G9)
und im Credential Manager ausdrücklich nur den DPAPI-Pepper statt Tokens; das
A.2-Diagramm zeigt `data/tasks.db.enc` als immer doppelt verschlüsseltes Ruhe-Artefakt;
das Phase-8-Ziel sagt "immer aktive" Verschlüsselung mit dem Zusatz, dass sie kein Modus
und keine Einstellung ist; die Phase-8-Abnahme prüft `tasks.db.enc` (Hexdump zeigt nur
Header plus Rauschen) und dass im Ruhezustand nirgends eine unverschlüsselte `tasks.db`
liegt. Der Befund unten ist nur noch Historie.

- A.1 (Zeile 30): "**Optionale** App-Sperre": die Sperre ist seit B.7/B.8/N11.3
  zwingend (ohne Passphrase existiert kein Schlüssel; die App startet immer gesperrt).
- A.1 (Zeile 31-32): "**Tokens im Windows Credential Manager**": es gibt keine Tokens
  mehr (Sync entfernt); im Credential Manager liegt nur noch der Pepper.
- A.2-Diagramm (Zeile 54): "data/tasks.db (SQLite, lokal, **optional verschlüsselt**)".
- Phase 8 Ziel (Zeile 972): "und **(optional)** Datenbank-Verschlüsselung real machen".
- Phase 8 Abnahme (Zeile 1118): "**bei aktivierter Verschlüsselung** ist `tasks.db`
  ohne Passphrase nicht lesbar": es gibt keinen deaktivierten Modus, und das
  Ruhe-Artefakt heisst `tasks.db.enc`.

**Wirkung:** Ein "optionaler" Verschlüsselungsmodus wäre G9 durch die Hintertür
(ein legitimer Codepfad ohne passphrase-abgeleiteten Schlüssel).

**Patch:** Alle fünf Stellen bereinigen; A.1 Punkt 2 neu formulieren (Pepper statt
Tokens).

### W11. `sqlcipher3-binary` vs. `sqlcipher3-wheels`  ✅ ERLEDIGT (2026-07-13)

**Status: behoben im Bauplan.** Beide Stellen (B.7, Schicht 1 und Phase 0 Tun 2)
nennen jetzt **`sqlcipher3-wheels`** (importiert als `import sqlcipher3`), jeweils mit
der Begründung, dass `sqlcipher3-binary` keine Windows-Wheels hat und die Installation
scheitern lässt, die API aber identisch ist. Der ursprüngliche Befund steht unverändert
darunter.

B.7 (Zeile 346) und Phase 0 Tun 2 (Zeile 671) schrieben `sqlcipher3-binary` vor.
Real (requirements.txt, CLAUDE.md): `sqlcipher3-binary` hat keine Windows-Wheels,
verwendet wird `sqlcipher3-wheels` (identische API). Wer Phase 0 nach Plan ausführt,
scheitert bei der Installation.

**Patch:** Beide Stellen korrigieren (ein Satz inkl. Begründung steht schon in
requirements.txt und kann übernommen werden).

### W12. `technische Grundlage.txt` beschreibt eine Architektur, die es nicht mehr gibt  ✅ ERLEDIGT (2026-07-16)

> **[ERLEDIGT 2026-07-16: Die Bauplan-Einleitung ist umformuliert. Der verbindliche
> technische Stack steht jetzt ausschliesslich im Bauplan (Teil A/B);
> `technische Grundlage.txt` ist ausdrücklich als "historisch und nur teilweise
> gültig" markiert (die Sync-/Notification-/`sqlite3`-/CDN-Teile sind hinfällig, der
> Krypto-Stack fehlt darin), mit der Vorrangregel "bei jedem Widerspruch gilt der
> Bauplan". Der ursprüngliche Befund steht unverändert darunter.]**

Die Bauplan-Einleitung (Zeile 6-7) verspricht eine App "auf dem in `technische
Grundlage.txt` beschriebenen Fundament". Dieses Dokument beschreibt aber: SQLite über
das eingebaute `sqlite3` (kein SQLCipher, keine Verschlüsselung), Microsoft-Graph-Sync
mit `httpx`/`msal`, Tokens via `keyring`, `winotify`-Benachrichtigungen, optional
Tailwind per CDN (verstösst gegen die CSP `default-src 'self'`). Nach der
Sync-/Notification-Entfernung ist rund die Hälfte des "Fundaments" schlicht nicht
mehr Teil des Projekts, und die andere Hälfte (Krypto-Stack) fehlt darin.

**Patch:** Entweder das Dokument auf den heutigen Stack kürzen (PyWebView, SQLCipher +
ChaCha20, argon2, keyring nur für den Pepper, kein Netz) oder es als "historisch,
ersetzt durch Bauplan Teil A/B" markieren und den Einleitungs-Verweis anpassen. Die
CDN-Sätze (auch der React-CDN-Absatz in A.3, Zeile 73-76) gehören gestrichen oder
mit dem Vermerk "unvereinbar mit CSP/G12" versehen.

### W13. Seed-Reste nach N11.1.4 (keine Demo-Daten mehr)  ✅ ERLEDIGT (2026-07-13)

**Status: behoben im Bauplan.** Beide Stellen sind auf den leeren Erststart
umformuliert. Die Phase-3-Abnahme verlangt jetzt eine echte Backend-Antwort auf
`get_state()` und hält ausdrücklich fest, dass auf einem frischen Tresor ein **leeres
`lists`** plus die Default-Settings der Erfolgsfall ist, kein Fehler. Die
Phase-9-Testliste prüft nicht mehr "Seed", sondern den leeren Erststart:
`seed_if_empty()` schreibt nur Default-Settings und den `seeded`-Marker, legt keine
Listen/Aufgaben an, und ein zweiter Aufruf bei gesetztem Marker ändert nichts. Der
ursprüngliche Befund steht unverändert darunter.

- Phase 3 Abnahme (Zeile 758): "bekommt die **echten Seed-Daten**": es gibt keine
  Seeds mehr; die Abnahme ist auf einem frischen Tresor nicht erfüllbar wie
  beschrieben (leere Listen + Default-Settings wären korrekt).
- Phase 9 Testliste (Zeile 1141): "db.py: CRUD, **Seed**, ...".

**Patch:** Beide Stellen auf den leeren Erststart umformulieren.

### W14. B.4 beschreibt an vier Stellen eine UI, die N11 abgeschafft hat

**[ERLEDIGT am 2026-07-13.]** B.4 ist konsolidiert: die Glocke ist aus dem ASCII-Diagramm
raus und der Header-Absatz sagt ausdrücklich "Mitte leer" (N11.1.1); der Toolbar-Absatz
kennt nur noch die immer schwebende Rail (`flush`/`floating`, der `toolbar`-Key und
`data-toolbar` sind gestrichen, N11.7); die Overlay-Liste hat jetzt einen vollen
**SettingsModal**-Abschnitt mit den drei Sektionen Appearance (`theme`, `accent`,
`density`), Sound (`sound`) und Security (`autoLock`, Passphrase ändern); der Emergency-
Rail-Knopf öffnet laut B.4 das PanicPanel, kein Modal. Nachgezogen: Phase 5 Tun 3 (kein
`data-toolbar` mehr), Phase 6 Modal-Tabelle (Status/Rename/Delete/Shortcuts/Settings,
Panik ist kein Modal) und Phase 6 Abnahme (kein Toolbar-Modus-Umschalten). Der Befund
unten ist nur noch Historie.

- ASCII-Diagramm (Zeile 200): Der Header zeigt weiterhin die Glocke "[🔔3]", gegen
  N11.1.1 ("Header-Mitte bleibt leer").
- Toolbar (Zeile 255-257): "zwei Modi über `data-toolbar`: `flush` oder `floating`",
  gegen N11.7 (Key `toolbar` entfällt, Rail immer floating). Auch Phase 5 Tun 3
  (Zeile 795) und Phase 6 Abnahme (Zeile 846, "Toolbar ... umschalten") nennen den
  Toolbar-Modus noch.
- Die B.4-Overlay-Liste enthält **kein Settings-Modal**, obwohl es existiert
  (app.js `state.modal='settings'`) und B.6/N11.4/N11.6 laufend darauf verweisen
  (Auto-Lock-Presets, Theme-Override, Sound-Schalter, Passphrase-Wechsel sollen alle
  dort leben). Das wichtigste kommende Einstellungs-UI hat keinen Vertragsabschnitt.
- Phase-6-Tabelle (Zeile 820): "Modals (5x) ... **Emergency**/Status/Rename/Delete/
  Shortcuts": das Emergency-Modal wurde durch das PanicPanel ersetzt (B.4 selbst
  beschreibt das weiter oben korrekt).

**Patch:** B.4 einmal konsolidieren (Diagramm, Toolbar-Absatz, Overlay-Liste inkl.
Settings-Modal mit seinen Sektionen); Phase 5/6 nur als historisch kennzeichnen oder
die zwei Wörter anpassen.

### W15. Fälligkeiten wurden stillschweigend mitentfernt, ohne Entscheid im Plan  ✅ ERLEDIGT (2026-07-13)

**Status: entschieden und im Bauplan festgehalten.** Der Nutzer hat entschieden:
**Fälligkeiten und Erinnerungen sind ersatzlos gestrichen.** Das steht jetzt als
**N11.1.6** in der Liste der gestrichenen Features: kein Fälligkeitsdatum, keine
Uhrzeit, keine Wiederholung, keine Erinnerung, keine "heute/überfällig"-Sicht; `due_at`
kommt nicht zurück, eine Aufgabe bleibt `text` + `done`. N11.1.6 zählt ausdrücklich
auf, was **nicht** gebaut wird (Spalte, Datums-Argument, Datumspicker, Datums-Sortierung,
Export-Spalte, Hintergrund-Timer) und **überschreibt das UX-Audit ausdrücklich**, das
Fälligkeiten als "Produktlücke Nummer 1" führt: wer das Audit abarbeitet, überspringt
diesen Befund. Als spätere Möglichkeit (kein Auftrag, keine Vorbereitung im Code) steht
in **D.3** eine Anzeige-only-Variante ohne Erinnerungen. Der ursprüngliche Befund steht
unverändert darunter.

Mit dem Sync-Commit wurde `due_at` aus Schema und Bridge entfernt (CLAUDE.md
dokumentiert das ausdrücklich). Der Bauplan enthält aber **keine** Entscheidung dazu:
N11.1 ("ersatzlos gestrichene Features") listet Benachrichtigungen, Backups, Meta,
Seeds und JSON, **nicht** Fälligkeiten. Zuvor waren Fälligkeits-UI und
Überfällig-Anzeige ausdrücklich Pflicht (alte Phase 6.5/10). Das UX-Audit führt
Fälligkeiten weiter als Produktlücke Nummer 1 (UX 7.1). Eine ausführende KI, die das
Audit oder alte Verweise abarbeitet, baut `due_at` wieder ein; eine andere hält es
für gestrichen.

**Patch:** In N11.1 einen Punkt 6 ergänzen: "Fälligkeiten/Erinnerungen gestrichen
(mit den Benachrichtigungen entfallen)" oder bewusst "Roadmap D.3" (Anzeige-only
ohne Erinnerungen wäre auch ohne Notifications denkbar). Hauptsache entschieden und
notiert.

### W16. B.1: "IDs per `uuid`/Zeitstempel"

**[ERLEDIGT am 2026-07-13.]** B.1 schreibt jetzt verbindlich `'l' + uuid4().hex` bzw.
`'t' + uuid4().hex` und schliesst Zeitstempel-IDs ausdrücklich aus (deckt sich mit
`db.py:30`). Der Befund unten ist nur noch Historie.

Zeile 84 lässt offen, ob IDs aus UUIDs oder Zeitstempeln bestehen (der Code nutzt
`uuid4`). Zeitstempel-IDs wären kollisionsanfällig. Kleinigkeit, aber eine echte
Ratestelle in einem Vertragsabschnitt.

**Patch:** "per `uuid4`" schreiben.

### W17. Schnell-Checkliste widerspricht dem erreichten Stand

**[ERLEDIGT am 2026-07-13.]** Phasen 0 bis 5 sind abgehakt (Nachtrag mit Datum), die Liste
traegt jetzt einen Stand-Vermerk und eine Pflege-Regel (bei jedem Phasenabschluss sofort
abhaken). Ein Detail wurde dabei sichtbar und ist im Haken vermerkt: Phase 3 ist fertig,
aber **G12 (WebView-Navigation abriegeln) ist nicht umgesetzt** (in `main.py` gibt es
keinen Navigations-Handler) und bleibt als vorgezogene Pflicht in Phase 7 stehen. G11
(Deps pinnen) gilt mit `requirements.lock.txt` als erfuellt. Der Befund unten ist nur noch
Historie.

Phasen 0-5 sind unangehakt (Zeile 1704-1709), obwohl Phase 6 (angehakt) sie
voraussetzt und die App läuft. Für eine KI mit der Regel "eine Phase nach der
anderen, nicht vorgreifen" ist das eine Einladung, bei Phase 0 zu beginnen.

**Patch:** Phasen 0-5 mit Datum abhaken; künftig bei jedem Phasenabschluss pflegen.

### W18. Das neue Gate G28 fehlt in sämtlichen Gate-Übersichten

> **[ERLEDIGT 2026-07-13: G28 steht jetzt (a) als eigene Zeile in der
> B.9-Nachtragstabelle (Zusammenfassung mit Verweis "Volltext in N11.9"), (b) in der
> Phase-8-Gateliste (Überschrift dort auf "G13 bis G19, G25 und G28" erweitert) samt
> neuem "G28 erfüllt"-Punkt in der Phase-8-Abnahme, (c) in der Phasen-Checkliste am
> Ende und (d) in der Schnellübersicht "Sicherheits-Gates auf einen Blick". Die
> Nachtrags-Überschrift lautet jetzt "Gates G13 bis G28 (Code-Audit + Testlauf vom
> 2026-06-10, seither fortgeschrieben)" mit einem Intro-Satz zur Fortschreibung
> (G24 entfernt, G26/G27 nachgekommen, G28 aus N11.9); bewusst NICHT "G6 bis G28",
> weil G6-G12 aus dem früheren Security-Review stammen und im Block davor stehen.
> Die Tabellenzeilen sind numerisch sortiert (G25 vor G26).]**

G28 (Verschlüsselungs-Beweis, N11.9) existiert nur im N11.9-Text. Es fehlt in der
"Sicherheits-Gates auf einen Blick"-Tabelle (Zeile 1719-1742 enden bei G27), in den
B.9-Tabellen und in der Phase-8-Gateliste. Zusätzlich stimmt die
Nachtrags-Überschrift "Gates G13 bis G25" (Zeile 513) nicht mehr (die Tabelle enthält
G26/G27, G24 ist zu Recht weg), und die Zeilenreihenfolge ist G23, G26, G25, G27.

**Wirkung:** Wer die Übersichtstabelle als Vollständigkeits-Anker benutzt (genau ihr
Zweck), verliert ausgerechnet das neueste Pflicht-Gate.

**Patch:** G28-Zeile in Übersicht + Phase-8-Gateliste aufnehmen; Überschrift auf
"G6 bis G28" o.ä. ändern; Tabelle numerisch sortieren.

---

## TEIL 2: Strukturelle Mängel

### S1. Gate-Mehrfachbuchführung ohne führende Quelle; die Drift ist messbar  ✅ ERLEDIGT

> **[ERLEDIGT: im Bauplan behoben (Marker 2026-07-16 nachgetragen). B.9 ist zur
> **einzigen normativen Quelle** erklärt: Definition, Status, Stand (Datum) und
> Prüfweg eines Gates stehen nur noch dort (eigene Spalten je Zeile), Phasen und
> Schnellübersicht führen nur noch die Gate-Nummer. Die geforderte Redaktionsregel
> ist als Pflicht verankert ("wer ein Gate ändert, ändert es an genau dieser einen
> Stelle"). Damit ist die von W3/W4/W8/W18 belegte Kopier-Drift strukturell
> geschlossen. Der ursprüngliche Befund steht unverändert darunter.]**

Jedes Gate existiert bis zu viermal (B.9-Definition, Phasen-Wiederholung,
Schnellübersicht, CLAUDE.md). W3, W4, W8 und W18 sind genau die vorhergesagten
Kopier-Drifts, und bemerkenswert: Die grosse N11-Überarbeitung hat G18 in allen
Kopien nachgezogen, G13/G14 aber nur in je einer. Ohne Mechanik passiert das wieder.

**Patch:** B.9 zur einzigen normativen Quelle erklären (Definition + Status + Datum);
Phasen listen nur Gate-Nummern mit Verweis; die Schnellübersicht wird als "nicht
normativ, Stand <Datum>" markiert oder bei jeder Gate-Änderung mit editiert
(Redaktionsregel: "ein Gate ändern = alle vier Stellen in einem Commit").

### S2. "SOFORT"-Gates ohne Termin und Prüfweg; G22 und G11 sind seit Wochen überfällig, und G22 ist zu eng gefasst  ✅ ERLEDIGT (Plan); Code-Rest terminiert

> **[ERLEDIGT im Plan (Marker 2026-07-16 nachgetragen), mit terminiertem Code-Rest.
> (a) Die normative Gate-Tabelle B.9 hat jetzt die drei geforderten Spalten
> **Status / Stand / Prüfweg** je Zeile. (b) Jedes "SOFORT" hat einen Termin
> bekommen: G22 und G29 mit **2026-07-20**, G34 (b) `text_select` ebenfalls
> **2026-07-20**. (c) G22 ist auf **alle** UI-Claims ausgeweitet (Status-Modal,
> Header-Pill, Lock-Screen-Untertitel, Panik-Endschirm), nicht mehr nur
> `get_status()`. (d) G11/V9 ist entschieden (`requirements.lock.txt` ist führend,
> Release-Install nur daraus mit `--require-hashes`) und der Python-Pin 3.11.x
> (U25) steht in G11.
> **Code-Stand 2026-07-16:** G22 teilweise umgesetzt (`get_status()` + Status-Modal
> jetzt ehrlich, `active:false`/Warnfarbe/`dev_key`-Flag); `text_select=False`
> gesetzt (G34 b). **Offen bis zum Termin 2026-07-20:** der Panik-Endschirm-Text
> ("securely wiped") und der G29-Basisschutz (`str(exc)` raus). Der ursprüngliche
> Befund steht unverändert darunter.]**

- **G22** ("SOFORT, spätestens mit 7", seit 2026-06-10): Stand heute zeigt
  `app.js:517` weiterhin hartkodiert "AES-256 + ChaCha20 · Argon2id / active",
  während der AES-Key als `DEV_AES_KEY` öffentlich in `db.py` steht. Das ist seit
  32 Tagen ein offener "Sofort"-Punkt.
- **G11** (Phase 0 / laufend): `requirements.txt` ist weiterhin ungepinnt (nur die
  Lock-Datei ist gepinnt; der Gate-Text verlangt das Pinning aber ausdrücklich in
  `requirements.txt`).
- **G22 ist ausserdem zu eng formuliert:** Es verlangt nur einen ehrlichen
  `get_status()`. Die Header-Pill "LOCAL · ENCRYPTED", der Lock-Screen-Untertitel
  ("LOCAL VAULT · ENCRYPTED") und der Panik-Endschirm ("All data securely wiped",
  laut N10.4 heute forensisch nicht belastbar) behaupten dieselben Unwahrheiten und
  sind vom Gate-Wortlaut nicht erfasst.

**Patch:** (a) In der normativen Gate-Tabelle drei Spalten: Status, Datum, Prüfweg
(für G22 z.B.: "Status-Modal öffnen; solange `DEV_AES_KEY` existiert, darf nirgends
'active'/'ENCRYPTED' stehen"). (b) "SOFORT" bekommt ein Datum oder wird sofort
erledigt. (c) G22 auf **alle** Verschlüsselungs-/Wipe-Behauptungen der UI ausweiten.

### S3. Nachträge werden angehängt statt eingearbeitet; der Plan hat inzwischen vier Textschichten

> **[ERLEDIGT 2026-07-13: Konsolidierungs-Pass durchgeführt und beide Regeln im
> Bauplan verankert. (a) Konsolidierung: die grossen überschriebenen Stellen waren
> durch die W-Fixes (W2 bis W18) bereits direkt korrigiert; die letzten Altreste
> wurden jetzt nachgezogen (B.1-Settings-Kommentar ohne `Toolbar`, B.9 Regel 1 ohne
> Meta-Feld, Gate-Nachtrag-Intro "Phasen 7, 8 und 9", N2 auf den echten Flugmodus
> aus N11.5 umformuliert, N9-Startverhalten als überholt durch N11.6 markiert,
> N10.3 "offline nur noch im Panik-Flow, N11.10", Schnell-Checkliste G8 ohne
> "Passphrase-Stärke"). Der Haupttext widerspricht N10/N11 nicht mehr.
> (b) Leseregel ergänzt: die Einleitung verlangt jetzt ausdrücklich, vor Beginn
> jeder Phase zuerst N10/N11 (das Änderungsprotokoll) zu lesen.
> (c) Redaktionsregel festgeschrieben (Einleitung plus N11-Vorbemerkung): neue
> Entscheidungen werden sofort an Ort und Stelle in den Haupttext eingearbeitet,
> N10/N11 sind nur noch Änderungsprotokoll, es werden keine neuen überschreibenden
> Textschichten mehr angehängt; die Vorrangregel "im Zweifel gilt N11" bleibt als
> Sicherheitsnetz. Das Problem ist damit behoben.]**

Der Plan besteht aus Urtext, Audit-Nachtrag (06-10), N10 und N11, mit der Vorrangregel
"im Zweifel gilt N11". N11 hat vorbildlich einige Altstellen mit Markern versehen
("[Ueberholt durch N11.9]", "[Gestrichen durch N11.8.4]"), aber die Mehrzahl der
überschriebenen Stellen blieb unmarkiert (Belege: W2, W7, W8, W9, W10, W13, W14).
Die Leseregel des Plans ("von oben nach unten abarbeiten") kollidiert direkt mit der
Vorrangregel ("das Hinterste gewinnt"): Eine KI, die Phase 8 erreicht, hat N11 noch
nie gesehen.

**Patch:** Einmaliger Konsolidierungs-Pass vor Phase 7: jede von N10/N11
überschriebene Stelle wird direkt korrigiert (Alt-Wortlaut allenfalls als Fussnote).
Danach Redaktionsregel: Neue Entscheidungen werden an Ort und Stelle eingearbeitet,
der Nachtrag dokumentiert nur noch das Änderungsprotokoll. Zusätzlich gehört die
Leseregel ergänzt: "Vor Beginn jeder Phase zuerst N10/N11 (bzw. das
Änderungsprotokoll) lesen."

### S4. Es gibt kein Bedrohungsmodell, und einzelne Zusagen überdehnen [Sec]  ✅ ERLEDIGT (2026-07-13)

> **[ERLEDIGT 2026-07-13: Der Bauplan hat jetzt den Abschnitt **B.10
> "Bedrohungsmodell"** (verbindlich, als **Gate G30** in beide Gate-Tabellen und in
> die Schnell-Checkliste eingetragen, plus ein Lese-Hinweis am Kopf von Phase 8).
> Er enthält: B.10.1 Schutzgut; B.10.2 die sechs Angreiferklassen **K1 bis K6** mit
> wirksamen Massnahmen und ehrlichem Restrisiko; B.10.3 die ausdrücklichen
> **Nicht-Ziele** (Malware-als-Nutzer K4, kompromittiertes Windows, optische/physische
> Kanäle, bewusster Export, vergessene Passphrase, Cloud-Retention, keine Plausible
> Deniability), samt der Regel, dafür **keine Schein-Gegenmassnahme** zu bauen
> (G26-Lektion); B.10.4 die **Voraussetzungen** (BitLocker/Geräteverschlüsselung
> dringend empfohlen, starkes Windows-Passwort, Passphrase min. 12) **inklusive der
> konditionierten G18-Zusage**: "gar nicht raten" gilt nur, wenn der Angreifer bloss
> die Tresordatei hat oder die Platte mit BitLocker verschlüsselt ist, sonst hängt der
> Pepper an der Stärke des Windows-Anmeldepassworts (der G18-Gate-Text und die
> Schnellübersicht sind entsprechend umformuliert); B.10.5 die **Abwägung zum
> Panik-Endschirm** (bei "Finish" ist die Wipe-Behauptung nachweislich falsch; bleibt
> bewusst so als Abschreckung gegen Gelegenheits-Zugriff, mit dem klar benannten
> Risiko im Zwangs-Szenario K6 und der Konsequenz "wer wirklich in K6 ist, drückt den
> Killswitch"; einzige dokumentierte Ausnahme von G22); B.10.6 die Tabelle
> **Gate -> Angreiferklasse** für alle Gates, mit der Arbeitsregel: **eine Massnahme
> ohne Klasse wird nicht gebaut.**]**

Nach der Sync-Entfernung ist die Angreiferliste klein und gut beschreibbar:
(1) Dieb der Datei/Platte, (2) forensischer Zugriff auf den Rechner,
(3) Person mit kurzem Zugriff auf die laufende/gesperrte App, (4) Malware im selben
Benutzerkonto, (5) Reverse-Engineer der `.exe`, (6) Zwangs-Situation (jemand zwingt
den Nutzer, die App zu zeigen). Der Plan adressiert diese implizit, benennt sie aber
nie, mit drei konkreten Folgen:

1. **Überversprechen G18** ("kann offline **gar nicht** raten"): Der Pepper liegt
   DPAPI-geschützt; bei gestohlener, unverschlüsselter Platte hängt DPAPI an der
   Stärke des Windows-Anmeldepassworts (offline angreifbar). Die Zusage gilt nur mit
   BitLocker oder starkem Windows-Passwort; das gehört in den Text.
2. **Malware-als-Nutzer ist unadressierbar** (liest Pepper via keyring, Tastatur,
   RAM) und sollte ausdrücklich als "ausserhalb des Modells" stehen; sonst entstehen
   wieder Schein-Gegenmassnahmen (die G26-Lektion).
3. **Der Panik-Endschirm behauptet bewusst einen Wipe, der (bei "Finish") nicht
   stattfand** (N10.3 "bewusste Aussendarstellung"). Im Zwangs-Szenario ist eine
   nachweislich falsche Wipe-Behauptung zweischneidig: Findet der Angreifer die Daten
   später doch, hat der Nutzer "gelogen", was seine Lage verschlechtern kann. Das
   kann man bewusst so wollen (Abschreckungs-Theater), aber es gehört als Abwägung
   ins Bedrohungsmodell, nicht nur als UI-Beschreibung.

**Patch:** Neuer Abschnitt B.10 "Bedrohungsmodell" (eine Seite): Tabelle
Angreiferklasse -> wirksame Massnahmen -> ausdrückliche Nicht-Ziele ->
Voraussetzungen (BitLocker-Empfehlung). Jedes Gate referenziert seine Klasse(n).
(Vorschlag Gate G30, Teil 6.)

### S5. Die gemeinsamen Abläufe (Sperren, Beenden, Panik, Killswitch, Reset) sind über fünf Stellen verstreut und nirgends als eine Sequenz definiert  ✅ ERLEDIGT (2026-07-13)

> **[ERLEDIGT 2026-07-13: Der Bauplan hat jetzt den Nachtrag **N11.11 "Die gemeinsame
> Sperr-/Beenden-Sequenz"** mit (a) genau einer Routine `teardown(reason)` in
> `security.py`, die **alle neun Ausgänge** aufrufen (Lock-Button, `Ctrl+L`, Auto-Sperre,
> Off-Knopf, Panik-Finish, Killswitch, Reset, natives Fenster-X, `atexit`), (b) der
> nummerierten Soll-Sequenz in 11 Schritten (N11.11.2), die alle unten geforderten Punkte
> enthält: G17-Debounce abbrechen und synchron persistieren (Schritt 4), Clipboard sofort
> leeren wenn es noch App-Inhalt trägt (Schritt 5, V7), Auto-Sperre bei offenem nativem
> Dialog aufschieben statt das Fenster darunter abzubauen (Schritt 2, U5),
> Killswitch/Reset schliessen die DB und nullen die Schlüssel **vor** der Datei-Löschung
> (Schritte 6 bis 8, U21), Funk-Wiederherstellung als letzter fachlicher Schritt und nur
> auf den Beenden-Wegen (Schritt 10, N11.5/N11.10), Mutex-Freigabe (Schritt 11);
> `LOCK_PROFILE_DIR` wird nie gewischt (Schritt 9, N11.8.3), gewischt wird der real
> beschriebene Store-Python-Pfad (V8), (c) einer Tabelle Schritt/Ausgang (N11.11.3), (d)
> einer Fehlerregel (Schritt 4 bricht ab und zeigt den N6-Fehlerbildschirm, damit kein
> Beenden-Weg Daten kostet; Schritte 5 bis 11 laufen best effort weiter) und (e) dem neuen
> Pflicht-Gate **G35** (Phase 8, in der Gate-Übersicht und der Phase-8-Abnahme verankert).
> Ein zweiter, handgeschriebener Beenden-Pfad ist damit ein Gate-Verstoss.]**

B.8, N10, N11.5 ("Wiederherstellung ganz zuletzt"), N11.8.1/N11.8.3 und Phase 8
Punkt 2 (Fenster-X, gemeinsame Routine, `atexit`) definieren je Teilstücke. Es fehlt
die eine, nummerierte Soll-Sequenz, gegen die man implementieren und testen kann,
inklusive der Punkte, die bisher nirgends stehen:

- ausstehenden G17-Debounce-Timer abbrechen und synchron persistieren,
- `copy_task`-Auto-Clear: Clipboard sofort leeren, wenn es noch App-Inhalt trägt (V7),
- Verhalten, wenn die Auto-Sperre feuert, während ein nativer Dialog offen ist (U5),
- Killswitch/Reset im entsperrten Zustand: DB schliessen und Schlüssel nullen
  **vor** der Datei-Löschung (U21),
- Funk-Wiederherstellung als letzter Schritt (nach dem W1-Entscheid),
- Mutex-Freigabe, `LOCK_PROFILE_DIR`-Behandlung.

**Patch:** In Phase 8 eine "Beenden-/Sperr-Sequenz" als nummerierte Liste
festschreiben (eine gemeinsame Funktion, alle Ausgänge rufen sie: Lock, Auto-Lock,
Off-Knopf, Finish, Killswitch-Ende, Reset, Fenster-X, `atexit`). (Vorschlag Gate G35.)

### S6. Mit G10 wurde auch die nicht sync-spezifische Fehler-Hygiene entsorgt; es gibt weder Fehlercode-Katalog noch Logging-Politik  ✅ ERLEDIGT (2026-07-13)

**Status: behoben im Bauplan (N11.12, neues Pflicht-Gate G29).** Der Patch ist vollständig
umgesetzt: (a) **B.2** hat jetzt eine verbindliche Fehlerkonvention plus den kanonischen
**Fehlercode-Katalog** (`not_found`, `invalid`, `locked`, `passphrase`, `rate_limited`,
`vault`, `canceled`, `internal`) mit Spalten für Bedeutung, statischen `message`-Text und
Frontend-Verhalten, inklusive der Codes, die bewusst **stumm** bleiben (`locked`,
`canceled`). (b) `str(exc)` ans Frontend ist ausdrücklich verboten; Details gehen nur in
einen **redigierten In-Memory-Ringpuffer** (50 Einträge, Pfade werden zu `<path>`, nie
Bridge-Argumente), einsehbar im Status-Modal und geleert in Schritt 3 der
`teardown()`-Sequenz (G35). (c) Die **Logging-Politik** steht in N11.12.2: im Release kein
persistentes Logfile, Diagnose nur hinter `NOATODO_DEBUG`, nie Passphrase/Schlüssel/
Aufgabentext, und der Auslieferungsbuild wird in Phase 9 darauf geprüft. G29 ist in der
Gate-Tabelle B.9, in Phase 7 (SOFORT, spätestens dort), in der Abnahme von Phase 7 und 9
sowie in der Gate-Schnellübersicht eingetragen; die Angreiferklassen K3/K5 stehen bereits
in B.10.6. Der ursprüngliche Befund steht unverändert darunter.

Das alte G10 ("Fehlermeldungen ohne Geheimnisse") wurde zusammen mit dem Sync
entfernt, obwohl sein Kern lokal weitergilt: Der `@bridge`-Decorator gibt heute
`str(exc)` ans Frontend (`api.py:32`); schon eine banale `OSError` enthält absolute
Pfade samt Windows-Benutzernamen, die als Toast auf dem Bildschirm landen (und dort
z.B. bei Screen-Sharing sichtbar sind). Ausserdem: Es gibt keinen kanonischen
Katalog der Fehlercodes (`not_found`, `internal`, künftig `locked`, `invalid`,
Unlock-Fehler), und keine Aussage, ob/wo das Backend loggt. Eine Tresor-App, die
später doch ein Logfile bekommt, unterläuft ihre eigene Verschlüsselung.

**Patch (Vorschlag Gate G29):** (a) Generische Fehler ans Frontend für alle Methoden
(statischer Text, kein `str(exc)`), Details nur in einen In-Memory-Ringpuffer
(einsehbar im Status-Modal); (b) Fehlercode-Tabelle in B.2 (Code -> Bedeutung ->
Frontend-Verhalten, inkl. welche Codes stumm bleiben, z.B. `locked` beim Boot);
(c) Logging-Politik: im Release kein persistentes Logfile, niemals Task-/Listen-Text,
Passphrase, Schlüssel oder Pfade in Meldungen.

### S7. Das UX-Audit hat keinen Status und ist inzwischen zur Falle geworden  ✅ ERLEDIGT (2026-07-13)

**Status: behoben im Bauplan (N11.14).** Beide Teile des Patches sind umgesetzt.
(a) **Audit-Triage:** N11.14 fuehrt jede Audit-Nummer (1.1 bis 10) mit Status und einem
Satz: ✅ erledigt, 🔵 eingeplant, 🟡 gueltig, ❌ hinfaellig. Ausdrücklich hinfällig sind
Fälligkeiten (7.1), Suche (7.2), Meta-Feld (7.3), Notizen (7.4), Smart-Ansicht (7.5),
Screenshot-Schalter (7.6), Sync-/Sign-in-UX (8.3), Glocke (1.3), "Clear completed" (3.8)
und der Mini-Shortcut (2.3). Zwei Punkte wurden dabei **gewichtiger**: `G` (3.12) und die
Offline-Pille (4.2), weil `set_online` seit N11.5 den echten Windows-Flugmodus schaltet.
Das Audit-Dokument wird nicht mehr fortgeschrieben, die Triage-Tabelle ist ab jetzt sein
Status und gewinnt bei Widerspruch.
(b) **Behauptungs-Lücke geschlossen:** Am Code geprüft (`app.js`, `renderTask`): es gibt
**keinen** Hover-Papierkorb, `.t-del` und der `del-task`-Handler sind Reste. Entscheidung
des Nutzers (2026-07-13): **Plan korrigieren statt Code nachrüsten.** Bauplan Phase 6.5
Punkt 2 sagt jetzt „Löschen über den Rail-Papierkorb (wirkt auf die ausgewählte Aufgabe),
kein Hover-Button auf der Karte", inklusive Hinweis auf den alten Falschstand; die Abnahme
von Phase 6.5 ist mitgezogen, CLAUDE.md ebenfalls. Ein Hover-Papierkorb bleibt ein
**offener** UX-Punkt (Audit 1.6/3.4, Phase 7), kein umgesetzter Stand.
Der ursprüngliche Befund steht unverändert darunter.

Der Bauplan verweist pauschal auf das Audit ("werden separat abgearbeitet",
Zeile 1236-1239). Das Audit (Stand 06-12) enthält aber inzwischen drei Sorten
Punkte, ohne Kennzeichnung: **erledigt** (Listen-Löschen 1.1, Profil-Menü-Zugang,
Sprachmix 2.1/2.2), **hinfällig** (Meta-Feld 7.3, Suche 7.2, Benachrichtigungen,
Sync-Statuspille 4.2, Screenshot-Schalter in 7.6, Fälligkeiten 7.1 je nach
W15-Entscheid) und **weiter gültig** (gestaffeltes Esc 3.1, Tastaturnavigation 3.10,
A11y 5.x, Scroll-Verlust bei Voll-Re-Render 6.1, Kontrast 4.6, Boot-Fehlerbildschirm
6.3). Dazu eine handfeste Behauptungs-Lücke: Bauplan Phase 6.5 Punkt 2 sagt
"Papierkorb-Button erscheint beim Hover auf der Karte" (umgesetzt 2026-06-10),
das Audit 1.6 widerspricht, und im heutigen `renderTask` (app.js:204 ff.) existiert
tatsächlich **kein** Task-Papierkorb; gelöscht wird nur über die Rail. Der Plan
behauptet hier etwas, das der Code nicht tut.

**Patch:** Kurze Audit-Triage als Nachtrag (je Audit-Nummer: gültig / erledigt /
hinfällig, ein Satz), und die Phase-6.5-Behauptung entweder im Code einlösen
(Hover-Papierkorb rendern) oder im Plan auf "Löschen über Rail" korrigieren.

---

## TEIL 3: Unklarheiten und Ratestellen

Sortiert nach Baustelle. Jede Nummer nennt, was eine ausführende KI heute raten
müsste, und einen konkreten Entscheidungs- bzw. Formulierungsvorschlag.

### Onboarding, Vault-Verwaltung, Konfiguration (Phase 8)

**U1. Der komplette Einrichtungs-/Verwaltungs-Flow hat keine Bridge-Methoden.**
**[ERLEDIGT 2026-07-13, Bauplan N11.13: B.2 hat jetzt `get_boot_state()`
(dreiwertig `onboarding|locked|unlocked`, der erste und einzige Boot-Aufruf),
`choose_vault_dir()`, `create_vault(path, passphrase)`, `change_passphrase(old, new)` und
`reset_vault()`, jeweils mit Vertrag und Fehlercodes; `get_state()` bleibt bewusst
zweiwertig, damit die G13-Regel scharf bleibt. Die G13-Allowlist ist an allen fünf Stellen
um `get_boot_state`, `choose_vault_dir`, `create_vault`, `reset_vault` erweitert
(`change_passphrase` ausdrücklich nicht). B.4 hat einen Onboarding-Abschnitt mit den drei
Screens (Ort inkl. Cloud-Pfad-Warnung, Passphrase mit Verlust-Warnung als Pflichttext plus
aktiver Checkbox, fertig/entsperrt starten) und den "Forgot passphrase?"-Reset im
Lock-Screen. U2 (`config.json`-Schema) ist seit dem 2026-07-15 in N11.15 erledigt, U8
(Passphrase-Wechsel inkl. `.bak`) in N11.3 (a-d, Entscheid 2026-07-13, Secure-Delete am
2026-07-15 präzisiert); aus diesem Befund-Cluster ist damit nichts mehr offen. **Nachschlag 2026-07-15: eine restliche Ratestelle im
Anlege-Flow geschlossen (N11.15.6): zeigt das Onboarding auf einen Ordner, in dem schon eine
`tasks.db.enc` liegt (der von N11.15.5 selbst erzeugte Dev-Python-zu-`.exe`-Fall), wird der
bestehende Tresor NIE überschrieben. `choose_vault_dir()` meldet jetzt `has_vault:true` und das
Onboarding bietet dann nur „diesen Tresor öffnen" statt „neu anlegen"; `create_vault()` bricht
als Backend-Riegel mit `invalid` ab, falls die Datei schon existiert.]**
B.2 nennt sich "vollständige Methodenliste", enthält aber nichts für: Tresor anlegen
(`create_vault(path, passphrase)`), Speicherort wählen (Ordner-Dialog),
Passphrase ändern (N11.3 verlangt es in den Einstellungen), Reset vom Lock-Screen
(`reset_vault()`), und keinen Boot-Zustand für "kein Tresor vorhanden" (N11.8.2
braucht dreiwertig `onboarding | locked | unlocked`; `get_state().locked` ist nur
zweiwertig). Auch B.4 hat keinen Abschnitt für die Onboarding-Screens (Reihenfolge,
Pflichttexte wie die Verlust-Warnung, aktive Bestätigung). Ohne das rät die KI die
halbe Phase 8 frei.
**Vorschlag:** B.2 ergänzen um `get_boot_state()` (oder `get_state()` um
`state: 'onboarding'|'locked'|'unlocked'`), `choose_vault_dir()` (nativer Dialog im
Backend), `create_vault(path, passphrase)`, `change_passphrase(old, new)`,
`reset_vault()`; B.4 um einen Onboarding-Abschnitt (3 Screens: Ort, Passphrase +
Verlust-Warnung mit aktiver Bestätigung, fertig/gesperrt starten).

**U2. `config.json` ist unterspezifiziert.** **[ERLEDIGT 2026-07-15, Bauplan N11.15
(sechs Unterpunkte). Verbindliches Schema Version 1
`{version, vault_path, radio_baseline, unlock_ratelimit:{fails, stage, next_try_at,
locked_at, duration}}`, geschrieben nur atomar (`.tmp` + `fsync` + `os.replace`, wie
G16), Ort fest `%LOCALAPPDATA%\NoaToDo\config.json` ueber die eine Hilfsfunktion
`config_path()`, Inhalt niemals geheim (kein Passphrase/Schluessel/Pepper/Salt). Die
Fehlerfaelle sind durchweg **pro Sicherheit** entschieden: fehlende Datei = Erststart
(Onboarding, Normalfall); **korrupte/zu neue Datei = KEIN stiller Erststart**, sondern
Umbenennen nach `config.json.bad` und Fehlerbildschirm (N6) mit "Tresor suchen / neuen
anlegen", weil ein stiller Erststart nach Datenverlust aussaehe und den Nutzer zu einem
zweiten Tresor verleiten wuerde, waehrend der echte unberuehrt liegt; **unerreichbarer
Pfad (USB-Stick weg, Netzlaufwerk down) ist ausdruecklich NICHT "kein Tresor"** und
fuehrt nie ins Onboarding, sondern in den Fehlerbildschirm mit "Erneut versuchen / Pfad
neu waehlen / neu anlegen". Dafuer wird `get_boot_state()` vierwertig
(`onboarding|locked|unlocked|vault_error` mit `reason`), `get_state()` bleibt zweiwertig
(G13 scharf). Wechseldatentraeger und UNC-Pfade sind erlaubt, aber nur mit Warnung
(dieselbe Stelle wie die G32-Cloud-Warnung: kein sicheres Ueberschreiben, leichter
Fremdzugriff, Fehlerbildschirm bei fehlendem Laufwerk), und ein fehlgeschlagener
Write-back ist dann kein stiller Datenverlust, sondern ein N6-Bildschirm. Store-Python-
Redirect (V8): Pfad nur ueber `config_path()`, keine Migration (Wechsel Dev-Python zur
`.exe` landet im Onboarding und zeigt per "Tresor suchen" auf die vorhandene
`tasks.db.enc`). Rate-Limit-Zustand und Funk-Ausgangszustand leben beide in diesem Schema
(U6/W1). Nachtrag N11.15.6: zeigt das Onboarding auf einen Ordner mit schon vorhandener
`tasks.db.enc`, wird der bestehende Tresor NIE ueberschrieben (`choose_vault_dir()`
meldet `has_vault:true`, `create_vault()` bricht als Backend-Riegel mit `invalid` ab).]**
N11.3 sagt nur "Pfad und nicht-geheime
Startinfos". Offen: exaktes Schema (Versionsfeld!), Verhalten bei fehlender oder
korrupter Datei, bei nicht mehr erreichbarem Vault-Pfad (USB-Stick entfernt,
Netzlaufwerk weg), ob UNC-/Wechseldatenträger-Pfade erlaubt sind, und wo der
Rate-Limit-Zustand (U6) und der gemerkte Funk-Ausgangszustand (W1) leben.
**Vorschlag:** Schema festschreiben, z.B. `{version:1, vault_path, radio_baseline,
unlock_ratelimit:{fails, stage, next_try_at}}`; Fehlerfälle: Datei fehlt/korrupt ->
wie Erststart, aber mit Hinweis; Pfad unerreichbar -> eigener Fehlerbildschirm mit
"erneut suchen / neuen Tresor anlegen". Store-Python-Randfall beachten (V8).

**U3. Das Lock-Screen-Zweitprofil (N11.8.3) hat eine ungelöste technische
Grundannahme.** **[ERLEDIGT 2026-07-13, verschärft 2026-07-15: N11.8.3 benennt die
Grundannahme ausdrücklich als Spike-Pflicht, die als ERSTES in Phase 8 zu klären ist,
mit jetzt neun Spike-Fragen als nummerierter Liste (zwei Profile pro Prozess als
Kernfrage, js_api-Umfang des Lock-Fensters, Taskbar-Verhalten, Fensterzustand nach
Unlock, X-Knopf des Lock-Fensters = `teardown("quit")` nach N11.11/G35, Boot-Reihenfolge
mit der Start-Weiche N11.8.2, WebView2-Prozesse vor dem Wischen wirklich beendet (sonst
`0x800700AA`/G14-Bruch), DevTools/Remote-Debugging am Lock-Fenster hart aus auch bei
`NOATODO_DEBUG`, Tastaturregel im gesperrten Zustand). Pro Sicherheit verschärft: der
Zwei-Profil-WebView-Weg ist **beweispflichtig** (nicht annehmen, sondern zeigen, dass
zwei isolierte Profile laufen UND `PROFILE_DIR` im gesperrten Zustand nachweislich
freigegeben und gewischt ist); ohne vollen Beweis gilt **im Zweifel** der native
Fallback (schlankes WinForms-Lock-Fenster ohne WebView, kein `LOCK_PROFILE_DIR`). Der
frühere zweite Fallback (prozess-interner WebView-Neustart) ist als überflüssige
Angriffs-/Cache-Fläche **verworfen**. Die Zielvorgabe "PROFILE_DIR im gesperrten Zustand
freigegeben und gewischt, der Lock-Screen sieht nie Aufgabendaten" ist als unverhandelbar
festgehalten und um einen G35-nahen Abnahmepunkt ergänzt (kein abnahmefähiger Build ohne
nachweislich gewischtes `PROFILE_DIR` vor Anzeige des Lock-Screens). Phase 8 trägt den
Spike zusätzlich als ersten Handgriff im Tun-Vorspann. Das Problem ist damit behoben.]** Der Plan markiert die PyWebView-Mechanik als "in Phase 8 zu
verifizieren", benennt aber die eigentliche Hürde nicht: `private_mode` und
`storage_path` sind bei PyWebView Parameter von `webview.start()`, also **global pro
Prozess**, nicht pro Fenster. Zwei Fenster mit zwei verschiedenen Profilen im selben
Prozess gibt die PyWebView-API damit möglicherweise gar nicht her. Weitere offene
Spike-Fragen: js_api-Umfang des Lock-Fensters, Taskbar-Verhalten (zwei Icons?),
Wiederherstellung von Fensterzustand (maximiert, Mini-Modus) nach dem Entsperren,
X-Knopf des Lock-Fensters (= `quit_app`-Pfad?), Boot-Reihenfolge (das Hauptfenster
ruft `get_state()` erst nach Unlock).
**Vorschlag:** Die Spike-Fragen als Liste in N11.8.3 aufnehmen und einen Fallback
benennen, falls PyWebView zwei Profile nicht hergibt: z.B. Lock-Screen als eigenes
schlankes natives Fenster (WinForms, ohne WebView) oder ein Prozess-interner
Neustart des WebView-Teils; die Zielvorgabe ("App-Profil wischbar,
Lock-Screen-Profil springt ein") bleibt, nur der Weg ist offen und muss als
Erstes im Phase-8-Spike geklärt werden.

**U4. "Inaktivität" der Auto-Sperre ist undefiniert.** **[ERLEDIGT 2026-07-15, Volltext
im Bauplan **N11.4.2**. Der Vorschlag unten wurde übernommen und sicherheitsseitig
gehärtet: (a) der Backend-Timer (monotone Uhr, eigener Thread, N11.8.4) ist die
**alleinige Autorität** und **fail-safe**: bleiben die Pings aus (Frontend hängt, stürzt
ab, wird per XSS stillgelegt), sperrt die App; das Frontend kann die Sperre nur
*aufschieben*, nie *verhindern*. (b) `activity_ping()` setzt **nur** `last_activity` auf
die monotone Backend-Uhr, nimmt keinen Zeitwert vom Frontend an und kann den Timer nicht
abschalten. (c) **Nur** `activity_ping` zählt als Aktivität, kein anderer Bridge-Aufruf,
damit ein Hintergrund-Poll wie `get_wifi_signal()` die App nicht wachhält. (d)
`activity_ping` steht **nicht** in `ALLOWED_WHEN_LOCKED` (G13) und rührt gesperrt den
Timer nicht an. (e) Kein Lese-Ausnahme: Lesen ohne Eingabe führt zur Sperre. Die
Drosselung (höchstens alle 30 s, führende Flanke) meldet nur *unter*, verschiebt die
Sperre also nie nach hinten, höchstens nach vorn. Ehrlich: `activity_ping` ist keine
Grenze gegen ein *kompromittiertes* Frontend (XSS = RCE, dann hat der Angreifer ohnehin
`api`-Vollzugriff); die Garantie kommt allein aus dem autoritativen, fail-safe Timer.]**
Was setzt den Timer zurück?
Nur Bridge-Aufrufe wären falsch (15 Minuten in einer Liste **lesen** ohne Klick =
Sperre mitten im Gebrauch); globale System-Idle-Zeit (GetLastInputInfo) wäre das
andere Extrem (App sperrt nie, solange irgendwo getippt wird, auch wenn NoaToDo
stundenlang im Hintergrund offen liegt: genau das Szenario, das N11.8.4 absichern
will).
**Vorschlag:** Aktivität = Eingabe-Ereignisse im App-Fenster (Maus/Tastatur/Scroll
im DOM); das Frontend meldet sie gedrosselt (z.B. höchstens alle 30 s) als
`activity_ping()` über die Bridge; der Backend-Timer (monotone Uhr, eigener Thread,
N11.8.4) sperrt bei `now - last_activity > timeout`.

**U5. Auto-Sperre vs. offene native Dialoge.** **[ERLEDIGT 2026-07-13, Volltext im
Bauplan **N11.11.5** (Schritt 2 der Sequenz N11.11.2 verweist dorthin). Wichtig: der
hier vorgeschlagene Patch ("Sperre aufschieben") wurde **bewusst nicht wörtlich
übernommen**, weil er zwei neue Löcher reisst, die N11.11.5 ausdrücklich benennt:
(a) ein offener Dialog würde die Auto-Sperre **unbegrenzt** aushebeln (Klasse K3:
`Ctrl+E` drücken, Dialog offen stehen lassen, weggehen, die App sperrt nie wieder,
und die Aufgaben bleiben hinter dem Dialog sichtbar), (b) ein nach der Sperre
zurückkehrender Dialog würde eine **Klartext-Export-Datei im gesperrten Zustand**
schreiben, an G13 vorbei. Statt "aufschieben" gilt daher **aufteilen**: Bei
`autolock` mit offenem Dialog laufen die Schritte 1 bis 7 der Sequenz **sofort**
(einfrieren, Write-back, Clipboard, DB zu, Schlüssel genullt) und der Lock-Screen
wird per `evaluate_js` gerendert (reines DOM, unter einem modalen Dialog
unproblematisch); nur die **nativen** Schritte 9 bis 11 (Ansicht abbauen,
`PROFILE_DIR` wischen) warten, und die Sequenz **schliesst den Dialog selbst**
(WM_CLOSE auf dem UI-Thread), statt auf ihn zu warten. Das Dialog-Ergebnis wird
danach verworfen (keine Datei, Export-Puffer genullt, `{"error":"locked"}`). Jeder
andere Ausgang bricht den Dialog sofort ab. Dazu: höchstens **ein** nativer Dialog
gleichzeitig über einen gemeinsamen Kontextmanager in `api.py` (Flag im `finally`
freigegeben, zweiter Dialog = neuer Fehlercode `busy` in B.2), ein Wächter gegen ein
verwaistes Flag, und ein offener Dialog zählt **nicht** als Aktivität (der Timer
läuft weiter). G35 hat dafür vier zusätzliche Abnahmepunkte (g) bis (j).]** Feuert der Timer, während der
Export-Save-Dialog oder der Onboarding-Ordnerdialog offen ist, baut die Sperre nach
N11.8.3 das Hauptfenster ab, unter einem modalen nativen Dialog: Absturz-/
Hänger-Risiko.
**Vorschlag:** Während ein nativer Dialog offen ist, wird die Sperre aufgeschoben
und feuert unmittelbar nach dem Schliessen (Flag um `create_file_dialog`).

**U6. Rate-Limit: Persistenz und Uhrbasis fehlen.** **[ERLEDIGT 2026-07-13, Bauplan
N11.4.1: `{fails, stage, next_try_at, locked_at, duration}` werden in `config.json`
persistiert (ausserhalb des Tresors, der beim Entsperren ja zu ist), zurueckgesetzt nur
durch erfolgreiches `unlock()` (und durch `reset_vault()`, das ohnehin alles loescht).
Zwei Uhren: monotone Uhr innerhalb der Sitzung, UTC-Wanduhr ueber Neustarts hinweg; bei
`jetzt < locked_at` (Uhr zurueckgestellt) oder widerspruechlichen Werten wird die
laufende Sperrzeit **komplett neu gestartet**, nie verkuerzt. Die ehrliche Einordnung
(bremst nur K3, der Offline-Rater umgeht die Leiter, Dateizugriff kann `config.json`
loeschen) steht in N11.4.1 und in der K3-Zeile von B.10.2. Die genaue Fehlerbehandlung
der Datei steht seit dem 2026-07-15 in N11.15.2 (U2 erledigt): kaputte Datei nach
`config.json.bad`, Fehlerbildschirm, danach frische, leere Leiter, was die Leiter genau
so zuruecksetzt wie das Loeschen der Datei. Am 2026-07-15 in N11.4.1 zusaetzlich
festgeschrieben (schloss den letzten Ratepfad): der Fehlversuch wird gezaehlt und
`config.json` **atomar geschrieben, BEVOR** Argon2id/AEAD ueberhaupt laufen und bevor eine
Antwort zurueckgeht (sonst umgeht ein Prozess-Kill mitten in der Pruefung die Zaehlung
genauso billig wie der Off-Knopf); Stufe/`duration`/`next_try_at` folgen aus `fails` ueber
**eine** deterministische Funktion (live und beim Start identisch), bei Widerspruch
`fails`/`stage` gewinnt der hoehere Wert; innerhalb der Sitzung gilt die **laengere** der
beiden Restzeiten (`max(monoton, wanduhr)`), nie die kuerzere.]** Die N11.4-Leiter, nur im RAM
gehalten, wird durch Off-Knopf + Neustart in Sekunden zurückgesetzt (der Lock-Screen
hat den Off-Knopf ja gerade prominent). Wanduhr-Zeitstempel sind per Systemuhr
manipulierbar; die monotone Uhr überlebt den Neustart nicht.
**Vorschlag:** Zustand `{fails, stage, next_try_at}` in `config.json` persistieren
(U2); bei Rückwärtssprüngen der Systemuhr die laufende Sperrzeit neu starten.
Ehrliche Einordnung ins Bedrohungsmodell: Die Leiter bremst den beiläufigen Rater am
Gerät; der ernsthafte Angreifer kopiert die Datei und rät offline, dagegen stehen
nur Argon2-Kosten + Pepper.

**U7. Entsperr-Fehler: drei Quellen, keine entscheidbare Logik.** **[ERLEDIGT
2026-07-15, Bauplan N6 (Block „Entscheidbare Fehlerlogik beim Entsperren") plus
Querverweis in N4. Die Dreiteilung ist jetzt verbindlich und wird **vor** der teuren
Ableitung am unverschlüsselten Container-Kopf entschieden: (1) Datei fehlt am
`config.json`-Pfad -> `vault`, **kein** stilles Onboarding (das entscheidet nur der Boot
über `get_boot_state()`, sonst könnte blosses Löschen der Datei den „neuen Tresor"-Weg
erzwingen); (2) Kopf unlesbar (Magic/Version/Struktur, Salt/KDF-Parameter/Nonce) ->
`vault` mit `.bak`-Angebot, geprüft ohne Passphrase und ohne Argon2 und nur am nicht
geheimen Kopf; (3) Kopf lesbar, AEAD-Tag scheitert -> `passphrase`. Das vorgeschlagene
`{ok:false, reason:'wrong_pass'|'locked_out'|'file_damaged'|'no_vault'}` wird bewusst
**nicht** übernommen (dupliziert die einzige Wahrheit aus B.2 und verletzt G29):
verbindlich sind die kanonischen Codes `passphrase` / `rate_limited` (mit `retry_in`) /
`vault`; „kein Tresor" ist ein Boot-Zustand, kein `unlock`-Ergebnis. Sicherheitsregeln
(pro Sicherheit entschieden): nur `passphrase` treibt die N11.4-Ladder voran (ein
kaputter Kopf ist kein Rateversuch und kann die Ladder weder umgehen noch zurücksetzen),
die Meldung bleibt neutral, `.bak`-Wiederherstellung ist ein vollwertiger Versuch unter
derselben Ladder und überschreibt die Primärdatei erst nach erfolgreichem Entsperren.
Der „vielleicht beschädigt: Backup versuchen?"-Sekundärhinweis erscheint nach
`DAMAGE_HINT_AFTER = 5` aufeinanderfolgenden `passphrase`-Ergebnissen, rein informativ,
ohne die neutrale Meldung oder die Ladder zu ändern.]** B.2 sagt
`unlock -> {ok:bool}`, die Fehlerkonvention sagt `{error, message}`, N4 will
"wrong passphrase", N6 will bei beschädigter Datei einen `.bak`-Hinweis. Technisch
kann der AEAD-Tag **nicht** zwischen falscher Passphrase und manipulierter Datei
unterscheiden; unterscheidbar sind nur: Datei fehlt (-> Onboarding, N11.8.2), Header
unlesbar/Magic falsch/Version unbekannt (-> Fehlerbildschirm "Datei beschädigt" mit
`.bak`-Angebot), Tag-Fehler (-> "wrong passphrase").
**Vorschlag:** Genau diese Dreiteilung als verbindliche Fehlerlogik in N4/N6
schreiben; Rückgabeformat festlegen, z.B. `{ok:false, reason:'wrong_pass'|
'locked_out'|'file_damaged'|'no_vault', retry_in:<s>}`; nach z.B. 5 Tag-Fehlern
zusätzlich den Hinweis "oder Datei beschädigt: Backup-Stand versuchen?" anbieten
(löst den N4/N6-Zielkonflikt sauber auf).

**U8. Passphrase-Wechsel: vier ungeklärte Details, eines davon sicherheitsrelevant.
[Sec]** **[ERLEDIGT (N11.3 a-d, Entscheid 2026-07-13; Secure-Delete-Präzisierung
2026-07-15) plus fester Phase-9-Krypto-Test: alle vier Punkte sind festgeschrieben.
(a) Frisches Salt und frische Nonce, kein Weiterverwenden alten Schlüsselmaterials.
(b) Der DPAPI-Pepper bleibt (konto-, nicht passphrase-gebunden), er wird nicht rotiert.
(c) Die `.bak`-Generation wird im selben Zug mit dem neuen Schlüssel neu geschrieben
(bevorzugt, erhält die G16-Absturzsicherung) oder gelöscht, und zwar über den
Secure-Delete-Pfad des Tresor-Abbaus (überschreiben, dann entlinken) statt per blankem
`os.remove`, sodass nach dem Wechsel keine Datei mehr mit der alten Passphrase lesbar ist
und auch keine alt-lesbaren Chiffrat-Bytes in freigegebenen Sektoren übrig bleiben; die
Restgrenze (SSD-Wear-Leveling) ist ehrlich vermerkt, letzte Deckung bleibt dann der
Pepper. (d) Beim Wechsel werden die Argon2-Parameter auf den G8-Soll gehoben, der Wechsel
ist damit der definierte KDF-Upgrade-Pfad. Der Phase-9-Test prüft, dass danach weder
`tasks.db.enc` noch `tasks.db.enc.bak` mit der alten Passphrase entschlüsselbar ist.]**
N11.3 sagt nur "Tresor wird neu verpackt". Offen: (a) frisches Salt und
frische Nonce (muss); (b) Pepper behalten oder rotieren (Vorschlag: behalten, er ist
konto-, nicht passphrase-gebunden); (c) **die `.bak`-Generation enthält nach dem
Wechsel weiter den mit der ALTEN Passphrase lesbaren Stand**: Wer die Passphrase
wechselt, weil sie kompromittiert ist, bleibt über `.bak` angreifbar; `.bak` muss
beim Wechsel sofort mit dem neuen Schlüssel neu geschrieben (oder gelöscht) werden;
(d) beim Wechsel gleich die Argon2-Parameter auf den aktuellen Soll-Stand heben
(KDF-Upgrade-Pfad, sonst existiert keiner).
**Vorschlag:** Alle vier Punkte in N11.3 festschreiben; (c) zusätzlich als
Phase-9-Testfall.

### Phase 7: Export, Undo, Verschieben

**U9. Undo beim Listen-Löschen: der Plan bietet zwei Architekturen mit "oder" an.**
**[ERLEDIGT 2026-07-15, Bauplan N11.2.1: die Soft-Delete-Variante ist gestrichen (kein
`deleted_at` in B.1), das Backend hält genau die letzte gelöschte Liste samt Aufgaben
(Text, `done`, `position`) in einem RAM-Puffer; `undo_delete_list(id)` stellt an der alten
`position` wieder her, ein `id`-Mismatch (Puffer schon ersetzt/verfallen) liefert
`not_found`. Eine neue Löschung überschreibt den Puffer; ein eigener Verfalls-Timer im
Backend existiert nicht (der 6-s-Toast ist reine UI, ein spätes Undo darf gelingen, solange
der Puffer lebt). Sicherheitsrelevant: der Puffer wird bei jedem Austritt aus dem
entsperrten Zustand verworfen, umgesetzt in `teardown()` Schritt 7 (N11.11.2) zusammen mit
dem Schlüssel-Nullen, und `undo_delete_list` steht NICHT in der G13-Allowlist. Damit hält
eine gesperrte App nie gelöschten Aufgabentext im RAM.]**
"Im RAM des Backends **(oder** als `deleted_at`-Soft-Delete)" ist eine echte
Ratestelle: Soft-Delete wäre ein Schema-Eingriff (B.1 kennt kein `deleted_at`) und
verseucht alle Abfragen; RAM ist trivial. Weitere offene Fragen: Wie viele
Löschungen werden gehalten (nur die letzte?), wird an der alten Position
wiederhergestellt, wer besitzt den 6-s-Timer (Frontend-Toast oder Backend-Verfall),
was passiert mit dem Puffer bei Lock/Quit?
**Vorschlag:** Festschreiben: Das Backend hält genau die letzte gelöschte Liste samt
Aufgaben im RAM; `undo_delete_list(id)` stellt an der alten `position` wieder her;
der Puffer verfällt bei der nächsten Löschung, bei Lock/Panic/Quit und beim
App-Ende; der Toast (6 s) ist reine UI, ein spätes Undo nach Toast-Ablauf darf
gelingen, solange der Puffer lebt.

**U10. Exportformate und -verhalten sind halb spezifiziert.** **[ERLEDIGT 2026-07-15,
Bauplan Phase 7 Punkt 1: fünf Festlegungen ergänzt. (1) Default-Dateiname
`export_list` = bereinigter Listenname (G21), `export_all` = `NoaToDo-Export-YYYY-MM-DD`
(lokales Datum); leerer Name -> `NoaToDo-Liste`. (2) `txt`: je Aufgabe `[ ] `/`[x] `
ohne Einrückung, Listenname als Zeile plus `=`-Linie, bei `export_all` eine Leerzeile
je Liste. (3) Kodierung UTF-8 ohne BOM, Zeilenenden CRLF. (4) Dialog-Abbruch: keine
Datei, kein "Exported"-Toast, Rückgabe `canceled` (nach G29/B.2 bewusst still),
festgehalten als G21c-Abnahmepunkt (Abbruch = kein Nebeneffekt, keine Meldung). (5)
Gesamtexport in Sidebar-Reihenfolge (`lists.position`). Der Vorschlag ist damit
vollständig umgesetzt, inkl. Abbruch in die Abnahme.]** Offen: exakter
Dateiname (`export_list`: bereinigter Listenname; `export_all`: fester Name, z.B.
`NoaToDo-Export-2026-07-12.md`?), `txt`-Format konkret ("analog als reiner Text"
sagt nichts über die Checkbox-Darstellung: `[x] `-Präfix? Einrückung?), Kodierung
(UTF-8 ohne BOM festlegen), Verhalten bei Dialog-Abbruch (Rückgabe? kein
"Exported"-Toast!), Listen-Reihenfolge im Gesamtexport (Sidebar-`position`).
**Vorschlag:** Fünf Festlegungen in Phase 7 Punkt 1 ergänzen; das Abbruch-Verhalten
in die Abnahme aufnehmen (die alte "Exported ohne Datei"-Unehrlichkeit, UX 1.5, darf
nicht als "Exported nach Abbruch" wiederkehren).

**U11. `reorder`/`reorder_lists`/`move_task`: Randfälle undefiniert.** **[ERLEDIGT
2026-07-15, Bauplan **N11.2.2**. Der Vorschlag wurde übernommen und präzisiert:
`ordered_ids` muss die Aufgabenmenge der Liste (offene **und** erledigte zusammen) bzw.
die Listenmenge **exakt** treffen: als Menge gleich, keine fehlende, keine doppelte, keine
fremde oder listenfremde ID, ein echtes Array von Strings. Jede Abweichung ->
`{"error":"invalid"}` und es wird **nichts** geschrieben (alles oder nichts, kein
Teil-Reorder); das Backend nummeriert `position` neu 0..n-1. `move_task` prüft beide IDs
(fehlend -> `not_found`, Ziel = aktuelle Liste oder kein String -> `invalid`), **behält
`done`** und hängt die Aufgabe ans Ende ihrer Sektion in der Zielliste (höchste Position;
da das Frontend je Sektion nach Position sortiert, landet sie am Ende der Erledigt- bzw.
der offenen Aufgaben), danach werden Quell- und Zielliste konsistent 0..n-1
durchnummeriert. Härtung gegen Nicht-Array-/Nicht-String-Eingaben unter G20.]** Was passiert
bei unvollständigen `ordered_ids` (nur die offenen? nur ein Teil?), fremden IDs,
Duplikaten? Wie werden Positionen vergeben (Neunummerierung 0..n-1?)? Behält eine
mit `move_task` verschobene erledigte Aufgabe ihren done-Status (und landet in der
done-Sektion der Zielliste)?
**Vorschlag:** `ordered_ids` muss exakt die Aufgabenmenge der Liste (bzw. die
Listenmenge) sein, sonst `{"error":"invalid"}`; das Backend nummeriert 0..n-1 neu;
`move_task` behält `done` und hängt ans Ende der jeweiligen Sektion.

**U12. Doppelte Listennamen.** **[ERLEDIGT 2026-07-15, Bauplan Phase 7 / Export-Schritt
(N11.2): erlaubt. Der Listenname ist ein reiner Anzeigewert, Schlüssel ist überall die
Listen-ID (`'l'+uuid`); keine Eindeutigkeitsprüfung beim Anlegen oder Umbenennen (ein
Verbot brächte nur einen neuen Fehlerpfad, keinen Sicherheitsgewinn). Die drei genannten
Berührungspunkte sind einzeln geklärt: (a) **`Ctrl+1-9` / Listen-Wechsel** ist positions-,
nicht namensbasiert, Duplikate wirken dort gar nicht (auch nicht „optisch"). (b)
**`export_list`** kollidiert bei gleichem Namen nur als Datei auf der Platte, das regelt der
Save-Dialog (Überschreiben/Umbenennen). (c) **`export_all`** (eine Datei, N11.2) ist der
einzige echte Fall doppelter Überschriften: die Namen bleiben **wörtlich** und stehen in
**Sidebar-Reihenfolge**, es wird nichts still umbenannt oder zusammengeführt (eine md/txt-
Datei, die der Nutzer einmal speichert, Duplikate spiegeln nur seine eigene Wahl). „Duplikate
erlaubt" betrifft nur den Anzeigenamen und lockert **G21 nicht**: die Sicherheit des
Dateinamens (reservierte Windows-Namen wie `CON`, Pfadtrenner, `..`, Newline-Ersetzung)
bleibt Pflicht, unabhängig davon, ob der Name einmalig ist.]** Nirgends entschieden, ob zwei
Listen "Ideas" heissen dürfen (betrifft Rename-Modal, Export-Dateinamen, `Ctrl+1-9` nur optisch).
**Vorschlag:** erlauben (IDs sind der Schlüssel), nur festhalten; der Save-Dialog
regelt Dateinamens-Kollisionen beim Export ohnehin.

**U13. Positions-Invarianten beim Abhaken.** **[ERLEDIGT 2026-07-15, Bauplan B.1
("Positions-Invariante beim Abhaken"): `position` wird **je Sektion** gefuehrt (`open`
und `done` je eigene 0..n-Sequenz). Abhaken haengt ans Ende von `done` (`MAX+1` unter den
erledigten), Wieder-Oeffnen ans Ende von `open`, neue Aufgabe ans Ende von `open`;
`reorder` vergibt 0..n innerhalb einer Sektion; sortiert wird je Sektion nach
`(position, created_at)`. Bewusst so entschieden (Nutzer, nicht bloss das Ist-Verhalten
eingefroren): das heutige Backend fuehrt **eine** gemeinsame Listen-Sequenz und laesst
`position` beim Abhaken unveraendert, weshalb B.1 das Code-Delta ausdruecklich benennt
(`toggle_task` und `add_task` sind anzupassen, `get_lists` bleibt).]** Wo landet eine
abgehakte Aufgabe in der
done-Sektion (oben? unten?), und wohin kehrt sie beim Wieder-Öffnen zurück? Heute
macht der Code irgendetwas Konsistentes; als Vertrag ist es nirgends fixiert und
ändert sich beim nächsten Refactor stillschweigend.
**Vorschlag:** Ein Satz in B.1: "Abhaken hängt ans Ende von `done`, Wieder-Öffnen ans
Ende von `open`; `position` wird je Sektion geführt."

### N11.5: echter Flugmodus

**U14. Die technische Basis ist nicht benannt.** **[ERLEDIGT 2026-07-15, Bauplan N11.5
Block „Technische Basis, verbindlich (U14-Entscheid)": Umsetzung ist
Radio-Enumeration (`Radio.GetRadiosAsync()`, gefiltert nach `RadioKind` WiFi/Bluetooth/
MobileBroadband) + `SetStateAsync` je Radio, mit Ruecklesen des `.State` (kein
Flugmodus-Flag, das ist per oeffentlicher API nicht schaltbar). Das Projektionspaket ist
benannt und wird gepinnt: die modularen PyWinRT-Pakete `winrt-runtime`,
`winrt-Windows.Devices.Radios`, `winrt-Windows.Devices.Enumeration`,
`winrt-Windows.Foundation` (schmalere Flaeche als `winsdk`, das nur Rueckfalloption
bleibt), aufgenommen in `requirements.txt` + `requirements.lock.txt` und unter G11.
Verweigerter Zugriff (`RequestAccessAsync` != `Allowed`) degradiert sichtbar: Tooltip
„no radio access", kein Radio wird angefasst, realer Zustand bleibt stehen, `set_online`
liefert `{online:<real>, partial:true}`, stilles Fehlschlagen ist verboten.]** "WinRT
`Windows.Devices.Radios`" braucht in Python ein Projektionspaket (`winsdk`/`winrt-*`):
eine **neue
Abhängigkeit**, die nirgends in Phase 0/requirements/G11 auftaucht (Pinning!).
Ausserdem ist der **System-Flugmodus als Flag per öffentlicher API nicht schaltbar**;
schaltbar sind einzelne Radios. "Echten Windows-Flugmodus einschalten" ist also
genau genommen nicht umsetzbar, umsetzbar ist "alle Radios aus" (Windows zeigt dann
kein Flugzeug-Symbol). Verhalten bei verweigertem Zugriff (`RequestAccessAsync` ->
Denied) ist undefiniert.
**Vorschlag:** N11.5 präzisieren: Umsetzung = Radio-Enumeration + `SetStateAsync`
je Radio (WLAN, Bluetooth, ggf. Mobilfunk), Paket benennen und pinnen; bei
verweigertem Zugriff degradiert der Schalter sichtbar (Tooltip "no radio access",
Zustand bleibt lokal) statt still zu scheitern.

**U15. `set_online`-Semantik unter echter Hardware.** **[ERLEDIGT 2026-07-15, Bauplan
N11.5 (`set_online`-Vertrag + `get_wifi_signal`-Kadenz). `set_online` antwortet erst nach
Abschluss mit `{online, partial}` und meldet immer den **verifizierten realen** Zustand,
nie die Absicht; die schutzrelevante Offline-Richtung aggregiert **pro Sicherheit**:
`online:true`, sobald auch nur ein Radio noch an ist, damit die App nie faelschlich
"dunkel" behauptet. Teil-Erfolg erzeugt einen `pushToast` mit statischem Text (G29, nennt
das verweigernde Radio); hoechstens eine Radio-Operation gleichzeitig (kein Doppel-
Schalten). Verweigerter Gesamt-Zugriff bleibt bei U14 (sichtbare Degradierung).
`get_wifi_signal()` pollt alle 10 s, aber nur online + Fenster sichtbar + entsperrt,
pausiert bei offline/minimiert/gesperrt und zaehlt nicht als Auto-Sperre-Aktivitaet (U4).]**
Der Aufruf wird asynchron und
kann teilweise scheitern (WLAN ok, Bluetooth verweigert). Was gibt `set_online`
zurück, wann, und was zeigt die UI bei Teil-Erfolg? Wie oft pollt
`get_wifi_signal()` (heute: Frontend-Intervall, nirgends festgelegt)?
**Vorschlag:** `set_online` antwortet erst nach Abschluss mit
`{online, partial:bool}`; Teil-Erfolg erzeugt einen Toast; `get_wifi_signal`-Kadenz
festlegen (z.B. 10 s, pausiert bei offline).

### Theme, Fenster, Kleinkram

**U16. Theme-Auto: drei kleine Entscheidungen fehlen.** **[ERLEDIGT 2026-07-15, Bauplan
N11.6: alle drei Vorschläge übernommen. (1) `Ctrl+J` aus `theme=auto` setzt den Override
auf das Gegenteil des aktuell angezeigten (effektiven) Themes; aus einem festen Theme
heraus auf das jeweils andere feste. (2) Zurück zu `auto` geht nur über das
Appearance-Segment in den Einstellungen; `Ctrl+J` kehrt nie von selbst nach `auto`
zurück. (3) Die Gegenprüfung läuft alle 60 s, das Windows-Ereignis bleibt der Hauptweg.
Die `Ctrl+J`-Sonderregel steht jetzt auch in der Kürzel-Tabelle B.5.]** Was tut `Ctrl+J` bei
`theme=auto` (Vorschlag: Override auf das Gegenteil des aktuell effektiven Themes)?
Wie kommt man zurück zu `auto` (nur übers Settings-Segment?)? Und die "seltene
Gegenprüfung": welches Intervall (Vorschlag: 60 s)?

**U17. Argon2id: konkrete Parameter und der RAM-Randfall.** **[ERLEDIGT 2026-07-15:
entschieden in Bauplan N11.4.3, im Zweifel pro Sicherheit. Feste Soll-Parameter
festgeschrieben (Argon2id v0x13, `memory_cost=262144` KiB = 256 MiB, `time_cost=3`,
`parallelism=4`, `hash_len=32`, 16-Byte-Salt), im `.enc`-Header (G16) und dort als
AEAD-`associated_data` authentifiziert (V1). Bewusst 256 statt 512 MiB: Verfügbarkeit
zählt als Sicherheitsziel, ein per Pepper an den PC gebundener Tresor darf sich nicht
selbst aussperren; gegen den Offline-Angreifer wirkt ohnehin primär der DPAPI-Pepper.
`MemoryError` bekommt einen eigenen Fehlercode `memory` (B.2): nie „falsche Passphrase",
nie Absturz, treibt die Rate-Limit-Ladder nicht voran; Anhebung über den
Passphrase-Wechsel (N11.3 (d)). Zusätzlich gegen einen aufgeblähten Header ein
Akzeptanzbereich (64 bis 512 MiB) vor der Allokation, sonst `vault` (N6 Schritt 2).]**
G8 nannte Spannen
(256-512 MB, t >= 3, "parallelism passend"); in den G16-Header müssen aber konkrete
Zahlen. Ausserdem kann eine 512-MB-Allokation auf RAM-knappen Maschinen scheitern:
Dann ist der Tresor auf genau diesem PC (an den er per Pepper gebunden ist!) nicht
entsperrbar, solange der RAM knapp ist; ein `MemoryError` mitten im Unlock darf
weder als "wrong passphrase" erscheinen noch die App abstürzen lassen.
**Vorschlag:** Default festschreiben (z.B. `memory_cost=256 MiB, time_cost=3,
parallelism=4`), `MemoryError` abfangen und verständlich melden ("close some
programs and retry"); die Parameter stehen im Header und werden beim
Passphrase-Wechsel (U8d) auf den Soll-Stand gehoben.

**U18. HKDF-Kleinigkeit.** **[ERLEDIGT 2026-07-15, Bauplan G15: die HKDF-Ableitung ist
jetzt verbindlich als `HKDF-SHA256(ikm=master_secret, salt=None, info=<label>, length=32)`
festgeschrieben, zweimal mit demselben Master-Secret, plus die beiden bisher unbenannten,
jetzt festen und versionierten Labels `b"noatodo/aes-key/v1"` und `b"noatodo/chacha-key/v1"`;
`salt=None` ist begründet (Master-Secret schon gleichverteilt, das Salt sitzt in Argon2id).]**
G15 nennt die `info`-Labels, aber nicht den HKDF-Salt.
Eine Zeile genügt: `HKDF-SHA256(salt=None, info=b"noatodo/...", length=32)`, damit
zwei Implementierungen kompatibel sind.

**U19. G17 unter dem N11.9-Fallback ist offen.** **[ERLEDIGT 2026-07-15, Bauplan N11.9:
der Vorschlag ist übernommen. `tasks.db.enc` bleibt in BEIDEN Varianten das debounced
Persistenzziel (G17: ~3 s, spätestens 30 s, U20; `.tmp`+`fsync`+`os.replace`, `.bak`,
G16). Die SQLCipher-Arbeitsdatei des Fallbacks ist kein zweites Persistenzziel und nie
Quelle der Wahrheit, sondern reines Betriebsmittel: beim Start kommentarlos
gelöscht/ersetzt, keine Crash-Recovery aus ihr (nach einem Absturz verworfen, nie
gelesen; Wiederherstellungsstand ist allein das zuletzt geschriebene `.enc` bzw. dessen
`.bak`). Damit gilt G17 wörtlich in beiden Modi und kein möglicherweise verfälschtes
Betriebsmittel geht als Wahrheit durch.]** G17 sagt "In-Memory-DB debounced
als neues `tasks.db.enc` persistieren". Im Fallback-Modus (SQLCipher-Arbeitsdatei
auf Platte) stellt sich die Frage: Wird trotzdem alle ~3 s das komplette `.enc` neu
geschrieben (Doppel-Schreiblast), oder ist die Arbeitsdatei die Wahrheit und `.enc`
entsteht nur bei Lock/Quit? Letzteres bräuchte eine Crash-Recovery-Regel (nach
einem Crash ist die Arbeitsdatei neuer als `.enc`: importieren oder verwerfen?),
sonst bricht das G17-Versprechen "Crash kostet höchstens Sekunden" genau im
Fallback-Modus.
**Vorschlag:** Einheitlich halten: `.enc` bleibt in beiden Varianten das debounced
Persistenzziel; die Arbeitsdatei ist reines Betriebsmittel und wird beim Start
kommentarlos gelöscht/ersetzt. Dann gilt G17 wörtlich in beiden Modi.

**U20. G17-Debounce ohne Obergrenze.** **[ERLEDIGT 2026-07-15, Bauplan G17 (Gate-Definition
im B.9-Nachtrag, dazu die Übersichtstabelle): der Debounce (ca. 3 s nach der letzten
Änderung) bekommt eine **harte Obergrenze: spätestens alle 30 s wird auch bei fortlaufenden
Änderungen geschrieben**. Ohne die Kappe schöbe Dauereingabe den Write-back unbegrenzt auf
("3 s nach der letzten Änderung" hiesse bei Dauertippen "nie") und ein Crash kostete mehr
als die zugesagten Sekunden.]** "3 s nach der letzten Änderung" heisst bei
Dauereingabe: nie. **Vorschlag:** Zusatz "spätestens alle 30 s, auch bei laufenden
Änderungen".

**U21. Killswitch/Reset im entsperrten Zustand: Reihenfolge.** **[ERLEDIGT 2026-07-13:
in die Sequenz N11.11.2 aufgenommen, Schritte 6 bis 8, inklusive Pepper-Löschung und
dem dokumentierten Nebeneffekt für frühere `.enc`-Kopien.]** N11.8.1 listet die
Löschziele, aber nicht die Reihenfolge relativ zu offenen Handles: erst
DB-Verbindung schliessen und Schlüssel nullen (G25), dann Dateien/Pepper löschen,
dann Profile wischen, dann beenden. Der Reset (N11.3) muss ausdrücklich dieselbe
Routine nutzen (inkl. Pepper-Löschung; der neue Tresor bekommt einen frischen
Pepper). Angenehmer Nebeneffekt, der dokumentiert gehört: Mit dem Pepper sterben
auch alle **früher kopierten** `.enc`-Stände endgültig, selbst wenn der Angreifer
später die Passphrase erführe.
**Vorschlag:** In die S5-Sequenz aufnehmen.

**U22. `Ctrl+Shift+!` und Tastaturlayouts.** **[Überholt durch den W5-Entscheid
vom 2026-07-13: der Hotkey ist ersatzlos gestrichen, die Layout-Frage entfällt. Die
bleibende Lektion ist am 2026-07-15 als stehende Regel in B.5 verankert ("Layout-Regel"):
künftige Modifikator-plus-Satzzeichen-Kürzel werden über `e.code` definiert, nicht über
`e.key`; die heutigen `e.key`-Hotkeys `F`/`G`/`?` bleiben korrekt.]**
Falls der Hotkey nach W5 (wieder)
eingeführt wird: Auf DE-Layout ist `!` = Shift+1 (funktioniert mit `e.key === '!'`),
auf Layouts mit `!` hinter AltGr feuert die Kombination nie.
**Vorschlag:** Auf `e.code`-Basis definieren (Ctrl+Shift+Digit1) oder als
Ctrl+Shift+1 dokumentieren.

**U23. Fehlercode-Katalog / Toast-Regel.** **[ERLEDIGT 2026-07-15. Der Kern war schon
mit S6/G29 behoben: der kanonische B.2-Katalog hat eine Spalte „Frontend-Verhalten", die
je Code Toast vs. stumm vs. eigener Bildschirm festlegt. Ergänzt wurde nun der von U23
verlangte Klartext (neuer Absatz „Toast-Politik auf einen Blick" in B.2): Toast **nur**
bei `not_found`, `invalid`, `busy`, `internal`; stumm bei `locked` und `canceled`; die
Entsperr-Fehler `passphrase`/`rate_limited`/`vault` haben ihre eigene N4/N6-Darstellung
statt eines Toasts. Terminologie-Korrektur: **ein Code `no_vault` existiert nicht** (der
U23-Text nannte ihn); „kein Tresor" ist der Onboarding-Boot-Zustand aus
`get_boot_state()` (N11.8.2, U7) und damit ebenfalls toastfrei, ein Tresor-Fehler zur
Laufzeit ist `vault`.]** Siehe S6; zusätzlich den B.2-Satz "Das
Frontend zeigt das als Toast" präzisieren: `locked` und `no_vault` sind
Normalzustände (kein Toast), `invalid`/`internal` sind Toasts, Unlock-Fehler haben
ihre eigene N4-Darstellung.

**U24. Fensterzustand über Lock/Mini hinweg.** **[ERLEDIGT 2026-07-15: entschieden in
N11.6 (Mini) und N11.8.3-Spike-Frage 4 (Unlock). Nach dem Entsperren kommt das Fenster
**immer maximiert** zurück (N11.6-Grundzustand) und **nie im Mini-Modus**; der
Vor-Sperr-Fensterzustand (Grösse/Position/Mini) wird **pro Sicherheit bewusst nicht** über
die Sperrgrenze getragen, der Lock setzt auf den neutralen Grundzustand zurück (der Spike
muss das nur noch nachweisen, nicht mehr entscheiden). **Mini-Ende ohne Sperre** stellt
dagegen exakt die beim Mini-Start gemerkten Fenster-Bounds (Position, Grösse,
Maximiert-Flag) wieder her, reines WinForms-Bounds-Merken in `set_mini`, ohne
Spike-Abhängigkeit.]** `maximized=True` ist umgesetzt;
undefiniert ist, in welchem Zustand das Fenster nach dem Unlock
(N11.8.3-Neuaufbau) und nach Mini-Ende erscheint (wieder maximiert? letzte Grösse?).
Klein, gehört in die U3-Spike-Liste.

**U25. Die Python-Version ist nirgends festgelegt.** **[ERLEDIGT 2026-07-15: G11 in B.9
um den Interpreter erweitert. Die Ziel-Python-Version ist auf **3.11.x** festgeschrieben
(Doku und Build-Umgebung); der Release-Build aus Phase 9 laeuft nachweislich unter 3.11.x
(Kriteriumsspalte der G11-Zeile). Begruendung im Gate: der Interpreter ist selbst eine
gepinnte Abhaengigkeit, weil `sqlcipher3-wheels` Wheels nur fuer bestimmte CPython-Versionen
liefert und die `.exe` gegen genau diesen Interpreter gebaut werden muss. Auch in CLAUDE.md
(Key dependencies) gespiegelt.]** Real läuft Store-Python 3.11;
`sqlcipher3-wheels` liefert Wheels nur für bestimmte Versionen; Phase 9 baut eine
`.exe`. **Vorschlag:** G11 um "Python auf 3.11.x pinnen (Dokumentation +
Build-Umgebung)" ergänzen.

---

## TEIL 4: Detail-Verbesserungen an bestehenden Gates

**V1 (G16): Header authentifizieren, `.tmp` verifizieren, Platz prüfen.** **[ERLEDIGT
2026-07-15: alles in der normativen G16-Zeile verankert (associated_data,
`.tmp`-Probeentschlüsselung vor der `.bak`-Rotation, Plattenplatz-Prüfung, Nonce als
geprüft vermerkt), gespiegelt in Phase-8-Gateliste, Schnellübersicht und CLAUDE.md.]** Der
G16-Header (Magic, Version, Argon2-Parameter, Salt, Nonce) ist bisher nicht
authentifiziert; er gehört als `associated_data` in `ChaCha20Poly1305.encrypt/
decrypt` (eine Zeile; macht jede Header-Manipulation zum sauberen AEAD-Fehler und
verhindert künftige Format-Downgrades). Zusätzlich: das frisch geschriebene `.tmp`
vor der `.bak`-Rotation einmal probeweise entschlüsseln (erst nach Erfolg rotieren,
sonst können zwei fehlerhafte Schreibzyklen beide Generationen zerstören) und freien
Plattenplatz vor dem Wrap prüfen. Die zufällige 12-Byte-Nonce ist bei dieser
Schreibfrequenz unbedenklich (kein Handlungsbedarf, nur als geprüft vermerken).

**V2 (G18): drei Präzisierungen.** **[ERLEDIGT 2026-07-15: (a) verbindliche, versionierte
Konstruktion `ikm = HKDF-Extract(salt=pepper, ikm=passphrase_utf8)` vor Argon2id in der
normativen G18-Zeile festgeschrieben (gespiegelt in G15, B.7, Phase-8-Gateliste,
CLAUDE.md); (b) war seit 2026-07-13 konditioniert (B.10.4/G18); (c) steht seit N11.13 in
der Onboarding-Verlust-Warnung (B.4, "G18/V2").]** (a) `argon2-cffi` exponiert Argon2s
Keyed-Secret-Parameter (K) **nicht**; der Gate-Text "fliesst als Argon2id-`secret`
in die Ableitung ein" ist mit der gepinnten Bibliothek so nicht umsetzbar. Verfahren
festlegen, z.B. `ikm = HKDF-Extract(salt=pepper, ikm=passphrase_bytes)` vor Argon2
oder `argon2(passphrase || pepper)` mit fester Längenkodierung; Hauptsache eine
verbindliche, versionierte Konstruktion. (b) Überversprechen konditionieren (S4:
DPAPI hängt ohne BitLocker am Windows-Passwort). (c) Die Verlust-Warnung im
Onboarding (N11.3) muss neben "Passphrase vergessen = Daten weg" auch die
**Konto-Bindung** nennen: Windows-Profil neu aufgesetzt oder PC gewechselt = Daten
weg, selbst mit korrekter Passphrase. Der Plan-Autor hat das entschieden; der
End-Nutzer muss es beim Einrichten erfahren.

**V3 (G19): Mutex-Namensraum.** **[ERLEDIGT 2026-07-15 (im Plan): Zielname
`Global\NoaToDo-<User-SID>` in der normativen G19-Zeile festgeschrieben, Umstellung als
Rest-Pflicht des Gates (spätestens Phase 8); der Code nutzt heute noch `Local\...`.]**
`Local\NoaToDoSingleton` ist pro Logon-Session
eindeutig: Derselbe Benutzer über RDP/schnelle Benutzerumschaltung startet eine
zweite Instanz auf demselben Profil und derselben DB, exakt die Korruption, die G19
verhindern soll. **Patch:** `Global\NoaToDo-<User-SID>`.

**V4 (G13): als Allowlist formulieren.** **[ERLEDIGT 2026-07-13: die normative G13-Zeile
ist als explizite Allowlist formuliert (inzwischen acht Methoden nach dem U1-Entscheid,
N11.13); abweichend vom Vorschlag bleiben `lock`/`panic` bewusst gesperrt statt
idempotent erlaubt.]** Statt "jede ausser ..." eine explizite
Menge `ALLOWED_WHEN_LOCKED = {"unlock", "quit_app", "killswitch", "get_state"}`
(wobei `get_state` gesperrt nur `{"locked": true}` liefert; `lock`/`panic` dürfen
idempotent erlaubt sein). Vorteil: Jede künftig ergänzte Methode ist automatisch
gesperrt statt automatisch offen; W4 zeigt, wie schnell die Ausnahmenliste driftet.

**V5 (G20): Werte und Typen prüfen, nicht nur Keys und Längen.** **[ERLEDIGT 2026-07-15:
als Punkt (d) in die normative G20-Zeile aufgenommen (Enums, Akzent-Hex-Whitelist,
`sidebarWidth`-Klemmung beim Schreiben, `autoLock`-Stufen, `edit_task.fields`-Typprüfung,
deklaratives Schema am Decorator), gespiegelt in Schnellübersicht und CLAUDE.md.]** Konkret:
`theme`/`density`/`sidebar` gegen Enums, `accent` gegen die sechs erlaubten
Hex-Werte (der Wert landet als CSS-Variable im DOM; mit Whitelist ist CSS-Injection
über Settings komplett tot), `sidebarWidth` beim **Schreiben** auf 180-520 klemmen
(heute laut CLAUDE.md nur beim Lesen geparst), `sound` bool, `autoLock` ganzzahlig
aus 0/1/5/15/30/60. `edit_task.fields` typprüfen. Am besten als kleines
deklaratives Schema pro Bridge-Methode am Decorator, dann kann Phase 9 das Schema
direkt testen.

**V6 (G21): verbotene Zeichen und Länge fehlen.** **[ERLEDIGT 2026-07-15: als Punkt (a2)
in die normative G21-Zeile aufgenommen (verbotene Windows-Zeichen und `..` durch `_`,
Kappung auf ca. 120 Zeichen, dann Gerätenamen-Prüfung; gilt für `export_list` und
`export_all`), gespiegelt in Phase 7, Schnellübersicht und CLAUDE.md.]** G21 entschärft Gerätenamen,
Punkte/Leerzeichen und Newlines, nicht aber die unter Windows unzulässigen Zeichen
`< > : " / \ | ? *` und `..`-Sequenzen im vorgeschlagenen Dateinamen (Listennamen
sind Freitext) und keine Längenkappung. **Patch:** Zeichen durch `_` ersetzen,
Ergebnis auf ~120 Zeichen kürzen, dann die bestehende Gerätenamen-Prüfung; gilt für
`export_list` und `export_all`.

**V7 (G23): Sperr-/Beenden-Pfade müssen das Clipboard sofort leeren.** **[ERLEDIGT
2026-07-13: Schritt 5 der Sequenz N11.11.2.]** Der
60-s-Auto-Clear lässt bei Lock/Panic/Quit/Killswitch bis zu 60 s Task-Text im
Clipboard zurück, während die App längst "zu" ist. Die Prüf-Logik ("nur wenn es noch
unser Inhalt ist") existiert bereits für den Timer; sie gehört zusätzlich in die
S5-Sequenz.

**V8 (G14): den Store-Python-Redirect einarbeiten.** **[ERLEDIGT 2026-07-15: in der
normativen G14-Zeile verankert (Wisch immer in-process auf dem effektiven Pfad,
Phase-9-Erststart entfernt bekannte Alt-Pfade einmalig, nie eine `tasks.db.enc`);
Volltext in N11.15.5 samt neuem Punkt (d) "Aufraeumen ja, Migration nein".]**
CLAUDE.md dokumentiert, dass
`%LOCALAPPDATA%`-Schreibzugriffe der Store-Python-Installation nach
`...\Packages\PythonSoftwareFoundation...\LocalCache\...` umgeleitet werden; G14
erwähnt das nicht. Folgen: (a) Wisch-Werkzeuge/Anleitungen, die den literalen Pfad
nennen, verfehlen die echten Daten; (b) nach dem Umstieg auf die Phase-9-`.exe`
(keine Umleitung mehr) bleibt der alte umgeleitete Profilordner samt Cache für immer
liegen, niemand wischt ihn je. **Patch:** G14-Zusatz: Das Wischen operiert immer
in-process auf dem effektiven Pfad; Phase 9 bekommt einen Erststart-Schritt, der
bekannte Alt-Pfade einmalig entfernt; gleiches gilt für `config.json` (U2).

**V9 (G11): endlich einlösen + Python pinnen.** **[ERLEDIGT 2026-07-13: der G11-Text ist
umformuliert (`requirements.lock.txt` ist die führende gepinnte Menge, Installation im
Release-Build nur daraus mit `--require-hashes`; `requirements.txt` bleibt bewusst die
lose Direktbedarfs-Liste) und der Python-Pin 3.11.x (U25) steht in G11 und CLAUDE.md.]**
`requirements.txt` ist bis heute
ungepinnt (nur die Lock-Datei ist es); entweder requirements.txt pinnen oder den
Gate-Text auf "requirements.lock.txt ist führend, Installation nur daraus, Phase 9
mit `--require-hashes`" umformulieren, damit Anspruch und Praxis übereinstimmen.
Plus U25 (Python-Version).

**V10 (Phase 9): Update-/Release-Story fehlt komplett.** **[ERLEDIGT 2026-07-15: als
Punkt 5 in Phase 9 aufgenommen (Version + Build-Datum im Status-Modal, bewusst kein
Auto-Update, manueller Bezugsweg über die im Status-Modal genannte Quelle,
Rebuild-Kadenz bei CVEs in `cryptography`/`pywebview`/`sqlcipher3-wheels`), plus
Abnahme-Punkt.]** Kein Wort zu: Version
sichtbar machen (Status-Modal), wie Nutzer von einer neuen Version erfahren
(bewusst kein Auto-Update bei einer Offline-App, aber dann wenigstens ein manueller
Weg), und dass gepinnte Abhängigkeiten altern (Rebuild-Kadenz bei CVEs in
`cryptography`/`pywebview`; der Browser-Teil ist dank Evergreen-WebView2 versorgt).
**Patch:** Drei Sätze in Phase 9.

**V11 (G22): auf alle UI-Claims ausweiten.** **[ERLEDIGT 2026-07-13 (mit S2): die
normative G22-Zeile gilt für alle UI-Claims (Header-Pill, Lock-Screen-Untertitel,
Panik-Endschirm), mit Termin 2026-07-20; die Umsetzung im Code steht noch aus und
hängt am Termin, nicht mehr an der Plan-Lücke. **Code-Stand 2026-07-16:**
`get_status()` und das Status-Modal sind ehrlich umgesetzt (`active:false`,
Warnfarbe, `dev_key`-Flag); Header-Pill und Lock-Screen-Untertitel existieren im
Code gar nicht (nichts zu ändern); **offen bis zum Termin bleibt allein der
Panik-Endschirm-Text** ("All data securely wiped", heute falsch).]** Siehe S2: Header-Pill,
Lock-Screen-Untertitel und Panik-Endschirm-Text ("securely wiped") müssen bis
Phase 8 genauso ehrlich degradiert werden wie das Status-Modal (Beleg für heute:
app.js:517).

**V12 (G28/Phase 9): den Beweis automatisieren.** **[ERLEDIGT 2026-07-15: der
pytest-Scan (SQLite-Klartext-Header + bekannter Task-String) steht in der normativen
G28-Zeile, in N11.9 und in der Phase-9-Testliste; dort neu ausserdem XSS-Trägheitstest,
Rate-Limit-Leiter inkl. Persistenz und Datei-Killswitch (Folgestart = Onboarding);
G13-Test und `.bak`-Neuverschlüsselung standen schon drin.]** G28 verlangt den
Verschlüsselungs-Beweis; als Einmal-Handgriff verrottet er. **Patch:** pytest-Test,
der das Arbeits-Artefakt (Serialisat bzw. Temp-Datei) auf den SQLite-Klartext-Header
(`SQLite format 3`) und auf einen bekannten Task-String scannt und bei Fund failt.
In dieselbe Phase-9-Testliste gehören ausserdem: der G13-Test mit der
**Dreier-Ausnahme** (W4), ein XSS-Trägheitstest (Task-Text `<img src=x onerror=...>`
wird als Text gerendert), die Rate-Limit-Leiter inkl. Persistenz (U6), die
`.bak`-Neuverschlüsselung nach Passphrase-Wechsel (U8c) und der Datei-Killswitch
(löscht `.enc`/`.bak`/Pepper; Folgestart = Onboarding).

---

## TEIL 5: Nicht abgedeckte Angriffsvektoren  ✅ ERLEDIGT (2026-07-15)

**Status: alle sieben Befunde sind am 2026-07-15 entschieden und im Bauplan
verankert.** A1 bis A3 als Gates G31 bis G33 (Phase 8), A4 und A6 zusammen als Gate
G34 (Phase 9; der Teilpunkt `text_select=False` SOFORT mit Termin 2026-07-20), alle
vier als normative Zeilen in der B.9-Gate-Tabelle samt Prüfweg und
B.10.6-Klassenzuordnung; A5 als Ergänzung des bestehenden Gates G27
(Frontend-Integrität); A7 als verbindliche Fenstertitel-Regel in B.4 (bewusst kein
eigenes Gate). "Erledigt" heisst hier: der Bauplan deckt den Vektor jetzt ab; die
Umsetzung folgt in der jeweiligen Phase. Die Befunde stehen unverändert darunter,
je mit einer Entschieden-Zeile.

**A1. RAM-Inhalte erreichen die Platte an allen Schichten vorbei: Pagefile,
Ruhezustand, Crash-Dumps. [Sec] ✅ ERLEDIGT (2026-07-15)** Die entsperrte DB lebt im RAM (G6/N11.9); Windows
schreibt RAM aber auf die Platte: `pagefile.sys` (Auslagerung), `hiberfil.sys`
(Ruhezustand = kompletter RAM-Abzug inkl. Schlüsseln und Klartext-Daten),
WER-Minidumps beim Crash des **Python-Prozesses** (der Plan behandelt nur
WebView2-Crashdumps in G14). Ein Offline-Angreifer mit der Platte liest daraus
Schlüssel und Inhalte, ohne die Kaskade anzufassen; das G25-Nullen verkürzt nur das
Fenster. **Patch (Vorschlag Gate G31):** (a) Ehrlichkeit: BitLocker/
Geräteverschlüsselung als Voraussetzung im Bedrohungsmodell und in der
Einrichtungs-UI empfehlen (der BitLocker-Status ist per WMI abfragbar und könnte im
Status-Modal stehen); (b) Schlüssel-`bytearray`s zusätzlich per `VirtualLock` gegen
Auslagern sperren (ctypes, Best-Effort, so dokumentieren); (c) WER-Dumps für den
eigenen Prozess minimieren und sicherstellen, dass `faulthandler`/Tracebacks nie in
Dateien schreiben.
**Entschieden (2026-07-15): als Gate G31 übernommen** (normative Zeile in der
B.9-Tabelle, Phase 8): BitLocker-Empfehlung in der Einrichtungs-UI plus realer
BitLocker-Status im Status-Modal (bei scheiternder WMI-Abfrage ehrlich "unbekannt",
nie ein falsches "geschützt"), `VirtualLock` für alle Schlüssel-Puffer mit
dokumentierter Grenze (hilft nicht gegen `hiberfil.sys` und Crash-Dumps, nur
BitLocker deckt das), keine Traceback-/Dump-Dateien (deckt sich mit G29).

**A2. Tresor im Cloud-Sync-Ordner: Versionshistorie konserviert jeden Stand. [Sec] ✅ ERLEDIGT (2026-07-15)**
N11.3 lässt den Nutzer den Speicherort **frei wählen**; landet `tasks.db.enc` in
OneDrive/Dropbox (naheliegend: "Dokumente" ist oft umgeleitet), erzeugt das
G17-Rewriting (alle ~3 s) hunderte serverseitige Versionen pro Tag: Jeder alte Stand
bleibt beim Anbieter wiederherstellbar (gelöschte Aufgaben leben in Cloud-Versionen
weiter; der Killswitch löscht sie dort **nicht**), und Änderungsfrequenz +
Dateigrösse ergeben ein präzises Nutzungsprofil. Verschlüsselt bleibt alles, aber
Retention und Metadaten widersprechen dem Local-first-Versprechen und entwerten den
Killswitch teilweise. **Patch (Vorschlag Gate G32):** Onboarding schlägt
`%LOCALAPPDATA%\NoaToDo\` als Default vor; liegt der gewählte Pfad unter einer
bekannten Sync-Wurzel (OneDrive-Umgebungsvariablen, Dropbox-`info.json`), erscheint
eine deutliche Warnung (inkl. "Killswitch/Reset löschen Cloud-Versionen nicht");
Hinweis auch in der Killswitch-Doku.
**Entschieden (2026-07-15): als Gate G32 übernommen** (B.9, Phase 8/Onboarding), mit
konkretisierter Erkennung (OneDrive-Umgebungsvariablen, Dropbox-`info.json`,
Pfad-Heuristik als Best-Effort), der Warnung mit beiden Kernsätzen, und ausdrücklich
als Warnung, nicht als Sperre (die freie Ortswahl aus N11.3 bleibt); der
Killswitch-Satz steht zusätzlich in B.10.3 Punkt 6.

**A3. Die Dev-Altdaten: die heutige `tasks.db` ist mit öffentlichem Schlüssel
lesbar, ihr Verbleib ist ungeregelt. [Sec] ✅ ERLEDIGT (2026-07-15)** `DEV_AES_KEY` steht im Repo-Quelltext;
die lokale `Code/data/tasks.db` mit den echten Aufgaben des Nutzers ist damit
faktisch Klartext (im Git-Repo liegt sie dank `.gitignore` korrekt **nicht**, das
wurde geprüft). N11.3 sagt nur "alte Dev-DB wird verworfen; keine Migration". Offen:
**wie** verworfen? Ein `os.remove` hinterlässt auf SSD forensische Reste (dasselbe
Argument, mit dem G6 die Temp-Kopien eliminiert); ausserdem existieren ggf.
`tasks.db-journal`/`-wal` und alte Export-Dateien aus der Dev-Zeit. **Patch
(Vorschlag Gate G33):** Der Phase-8-Erststart löscht `tasks.db` samt Journal/WAL
(bestmöglich überschreiben + löschen) und der Plan dokumentiert ehrlich: Daten, die
während der Dev-Phase geschrieben wurden, können forensisch auf der SSD verbleiben;
wer das ausschliessen muss, braucht ein frisches, vollverschlüsseltes System. Das
sollte der Nutzer einmal bewusst lesen.
**Entschieden (2026-07-15): als Gate G33 übernommen** (B.9, Phase 8): Zeitpunkt
fixiert (beim ersten `create_vault()`, bevor der neue Tresor in Betrieb geht), über
den Secure-Delete-Pfad aus N11.3 (c) und ausdrücklich samt `-journal`/`-wal`/`-shm`;
Einmal-Hinweis mit der ehrlichen SSD-Restgrenze. N11.3 verweist jetzt auf G33, das
offene "wie verworfen?" ist geschlossen.

**A4. Debug-Schalter und DevTools im Release-Build. ✅ ERLEDIGT (2026-07-15)** `NOATODO_DEBUG=1` aktiviert
DevTools (main.py:523, `debug=_debug_enabled()`). Respektiert die Phase-9-`.exe`
dieselbe Umgebungsvariable, bekommt jeder mit kurzem Zugriff (oder eine neugierige
zweite Person am selben Konto) eine Konsole mit vollem `pywebview.api.*`-Zugriff auf
die laufende App, inklusive `killswitch()` (Datenvernichtung ohne Passphrase, per
G13 gesperrt erlaubt!). **Patch (Teil von Gate G34):** Der Release-Build ignoriert
die Env-Var (Build-Konstante), DevTools hart aus, zusätzlich
`AreDevToolsEnabled=false` in den CoreWebView2-Settings, soweit erreichbar.
**Entschieden (2026-07-15): als Teil von Gate G34 übernommen** (B.9, Phase 9):
Release-Build ignoriert die Env-Var hart (`_debug_enabled()` liefert im gefrorenen
Build immer `False`), `AreDevToolsEnabled=false`; Prüfweg in B.9 und in der
Phase-9-Abnahme (Start der Release-`.exe` mit gesetztem `NOATODO_DEBUG=1`).

**A5. Manipulierte Frontend-Dateien = persistente Codeausführung im Tresor. ✅ ERLEDIGT (2026-07-15)** G27
signiert die `.exe`; `index.html`/`app.js`/`style.css` liegen daneben (One-Folder)
oder werden entpackt. Wer sie einmal schreiben kann, besitzt die App dauerhaft: Das
nächste `boot()` lädt das manipulierte JS mit voller Bridge, kann die
Passphrase-Eingabe des (HTML-)Lock-Screens mitlesen und nach dem Entsperren alles
abgreifen, bei intakter Exe-Signatur. Gegen Malware-als-Nutzer gibt es keine
vollständige Verteidigung (S4), aber stille **Persistenz** lässt sich erschweren.
**Patch (G27-Ergänzung):** Frontend-Assets ins signierte Binary einbetten und aus
dem Speicher bzw. einem frisch entpackten Pfad laden, oder beim Start ein
Hash-Abgleich gegen ein im Binary eingebettetes Manifest; bei Abweichung mit klarer
Meldung verweigern.
**Entschieden (2026-07-15): als Ergänzung in Gate G27 eingearbeitet** (B.9-Zeile und
Phase-9-Volltext): Assets ins signierte Binary einbetten **oder** Start-Hash-Prüfung
gegen ein eingebettetes Manifest, bei Abweichung Startabbruch mit klarer Meldung
(kein "trotzdem fortfahren"); nach B.10 eingeordnet als K4-Persistenz-Hürde, die
nie als vollständiger K4-Schutz verkauft wird.

**A6. Kopier- und Auslass-Kanäle am gehärteten Clipboard vorbei. ✅ ERLEDIGT (2026-07-15)** G23 härtet nur
den Rail-Button-Pfad. Daneben existieren: (a) Textselektion + natives Strg+C:
PyWebView deaktiviert die Selektion per Default (`text_select=False`), aber
`main.py` setzt den Parameter **nicht** explizit; der Schutz ist also unbeabsichtigt
und ungetestet, und ein künftiges `text_select=True` "für Komfort" würde G23 lautlos
aushebeln. Eingabefelder bleiben immer selektierbar (laut Phase 6.5 Punkt 3
akzeptiert), deren Strg+C landet aber in Win+V-History und Cloud-Clipboard,
ungehärtet. (b) Drag-out von markiertem Text in andere Apps. (c) **Strg+P**: Der
WebView2-Browser-Accelerator öffnet den Druckdialog, "Als PDF drucken" exportiert
die komplette Ansicht als Klartext-PDF an G21 vorbei. (d) Das
WebView2-Standard-Kontextmenü. **Patch (Vorschlag Gate G34, Release-Härtung):**
`text_select=False` explizit setzen + Regressionstest; im Release
`AreBrowserAcceleratorKeysEnabled=false` und `AreDefaultContextMenusEnabled=false`
(CoreWebView2-Settings), soweit über PyWebView erreichbar; den Rest
(Eingabefeld-Copy, Foto vom Bildschirm) ehrlich ins Bedrohungsmodell.
**Entschieden (2026-07-15): als Teil von Gate G34 übernommen**, zeitlich aufgeteilt:
`text_select=False` explizit setzen + Regressionstest **SOFORT** (Termin 2026-07-20,
S2-Regel), `AreBrowserAcceleratorKeysEnabled=false` (tötet `Strg+P`) und
`AreDefaultContextMenusEnabled=false` in Phase 9; der Eingabefeld-Copy-Kanal steht
jetzt ehrlich im Bedrohungsmodell (B.10.3 Punkt 8), Foto vom Bildschirm bleibt
Nicht-Ziel. **Code-Stand 2026-07-16: `text_select=False` ist explizit in
`main.py` `create_window` gesetzt (der zuvor unbeabsichtigte Default ist jetzt eine
bewusste, kommentierte Entscheidung); der Regressionstest folgt mit der
Phase-9-Testliste, da es heute noch kein Test-Setup gibt. Der Release-Rest (a)/(c)
bleibt Phase 9.**

**A7. Fenstertitel und sichtbare Metadaten. ✅ ERLEDIGT (2026-07-15)** Der native Fenstertitel ist für jeden
Prozess ohne Privilegien lesbar (Fenster-Enumeration) und taucht in
Screen-Sharing-Übersichten, Task-Switchern und Tools wie PowerToys auf. Heute ist er
konstant "NoaToDo" (gut); es gibt aber keine Regel, die verhindert, dass später
Listen- oder Task-Namen in den Titel wandern (naheliegend z.B. im Mini-Modus).
**Patch:** Ein Satz als Regel in B.4: "Der native Fenstertitel enthält nie
Nutzerinhalte."
**Entschieden (2026-07-15): als verbindliche Regel in B.4 übernommen** (konstanter
Titel "NoaToDo", nie Nutzerinhalte, in keinem Modus inkl. Mini-Modus; ausgeweitet
auf Taskbar-Tooltip, Jumplist-Einträge und Taskbar-Fortschritt; Prüfweg: Grep nach
`set_title`/`window.title` ausserhalb der Konstante; bewusst kein eigenes Gate).

---

## TEIL 6: Neue Gates und Priorisierung

### Vorgeschlagene neue Gates (ab G29; G28 ist seit N11.9 vergeben)

| Gate | Phase | Kurz | Quelle |
|---|---|---|---|
| G29 | 7 (mit G20) | Fehler-Hygiene: kein `str(exc)` ans Frontend, Fehlercode-Katalog in B.2, keine Pfade/Interna in Meldungen; Release ohne persistentes Logfile (RAM-Ringpuffer im Status-Modal) | S6 |
| ✅ G30 | Doku, vor 8 | Bedrohungsmodell B.10: Angreiferklassen, Nicht-Ziele (Malware-als-Nutzer), Voraussetzungen (BitLocker), G18-Zusage konditionieren, Panik-Endschirm-Falschaussage als bewusste Abwägung dokumentieren **(ERLEDIGT 2026-07-13: B.10 steht im Bauplan, G30 ist in beiden Gate-Tabellen und in der Checkliste)** | S4 |
| G31 ✅ übernommen (2026-07-15) | 8 | RAM-auf-Platte-Lecks: BitLocker-Empfehlung (+ Anzeige), `VirtualLock` für Schlüssel-Puffer, WER-/Traceback-Dump-Minimierung. **Im Bauplan als normative B.9-Zeile festgeschrieben** (Prüfweg, `hiberfil.sys`-Grenze dokumentiert, Phase-8-Gateliste + Abnahme) | A1 |
| G32 ✅ übernommen (2026-07-15) | 8 | Vault-Ort: Default `%LOCALAPPDATA%`, Warnung bei Cloud-Sync-Pfaden inkl. Hinweis "Killswitch löscht Cloud-Versionen nicht". **Im Bauplan als normative B.9-Zeile festgeschrieben** (Erkennung konkretisiert: OneDrive-Env-Vars, Dropbox-`info.json`, Pfad-Heuristik; Warnung statt Sperre) | A2 |
| G33 ✅ übernommen (2026-07-15) | 8 | Dev-Altdaten entsorgen: `tasks.db` + Journal/WAL beim Umstieg bestmöglich löschen; forensische Rest-Ehrlichkeit dokumentieren. **Im Bauplan als normative B.9-Zeile festgeschrieben** (Zeitpunkt: erstes `create_vault()`; Secure-Delete-Pfad aus N11.3 (c); Einmal-Hinweis) | A3 |
| G34 ✅ übernommen (2026-07-15) | 9; `text_select` SOFORT | Release-Härtung WebView2: `NOATODO_DEBUG` wirkungslos, DevTools aus, `text_select=False` explizit + Test, Browser-Accelerator-Keys und Standard-Kontextmenü aus. **Im Bauplan als normative B.9-Zeile festgeschrieben** (`text_select=False` mit Termin 2026-07-20; Eingabefeld-Copy ehrlich in B.10.3 Punkt 8) | A4, A6 |
| G35 ✅ übernommen (2026-07-13) | 8 | Eine gemeinsame, nummerierte Sperr-/Beenden-Sequenz für alle Ausgänge (Lock, Auto-Lock, Off, Finish, Killswitch, Reset, Fenster-X, atexit): Debounce-Flush, Clipboard-Clear, Schlüssel-Nullen, Wischen, Funk-Restore zuletzt, Mutex-Freigabe. **Im Bauplan als N11.11 + Gate G35 festgeschrieben** (Routine `teardown(reason)`, 11 Schritte, Tabelle Schritt/Ausgang, Abnahme in Phase 8) | S5, U5, U21, V7, V8 |
| G36 (U1-Teil ✅ übernommen 2026-07-13) | 8 (Spezifikations-Pflicht) | Onboarding-/Vault-Bridge-Vertrag: `get_boot_state`, `create_vault`, `choose_vault_dir`, `change_passphrase` (inkl. `.bak`-Neuverschlüsselung), `reset_vault`; Onboarding-Screens in B.4; `config.json`-Schema. **Bridge-Vertrag und Screens sind als Bauplan-N11.13 festgeschrieben; `config.json`-Schema (U2) seit dem 2026-07-15 in N11.15 erledigt; der Passphrase-Wechsel inkl. `.bak` (U8) ist in N11.3 (a-d) entschieden; aus diesem Cluster ist nichts mehr offen** | U1, U2, U8 |

(G36 ist kein Sicherheits-Gate im engen Sinn, sondern eine Spezifikations-Pflicht;
es steht hier, damit es derselben "nicht optional"-Disziplin unterliegt.)

### Priorisierte Reihenfolge

**P0, Entscheidung + Doku-Konsolidierung (vor jedem weiteren Bauschritt; ein
konzentrierter Nachmittag):**
1. **W1 entscheiden** (Sperre vs. Funk; Empfehlung: entkoppeln). Das ist die einzige
   Stelle, an der der Plan aktiv schädliches Verhalten spezifiziert.
2. W2 + W3 fixen (Phase-8-Tun und G14-Zeile): die zwei gefährlichsten
   Krypto-/Regressionsfallen.
3. W4, W5, W7, W8, W9, W18 (Gate-/Nachtrags-Angleichungen); W10-W14, W16, W17
   (Kleinkram in einem Rutsch); die CLAUDE.md-Lock-Policy (W7) mitziehen; den
   W15-Entscheid (Fälligkeiten) notieren.
4. S1/S2-Mechanik einführen (eine normative Gate-Tabelle mit Status/Datum/Prüfweg),
   S3-Konsolidierungsregel, S7-Audit-Triage.

**P1, sofortige Code-Punkte (Stunden, keine Abhängigkeiten):**
5. G22/V11 endlich umsetzen (app.js:517 und alle UI-Claims).
6. G29-Basisschutz: `str(exc)` raus aus `api.py:32`.
7. G11/V9: requirements pinnen (bzw. Gate-Text an die Lock-Datei angleichen);
   `text_select=False` explizit in `create_window` (A6a).

**P2, in Phase 7 einarbeiten:**
8. U9-U13 (Undo-, Export-, Reorder-Festlegungen), V5, V6, G29 vollständig.

**P3, vor bzw. in Phase 8:**
9. U1-U8 (Onboarding-Vertrag, config.json, Zweitprofil-Spike inkl.
   PyWebView-Grundannahme, Auto-Lock-Aktivität, Dialog-Aufschub,
   Rate-Limit-Persistenz, Unlock-Fehlerlogik, Passphrase-Wechsel inkl. `.bak`),
   U18-U21 (HKDF-Detail, G17-Fallback-Klärung, Debounce-Obergrenze,
   Killswitch-Reihenfolge; U17 (Argon2-Werte + MemoryError) ist seit 2026-07-15 erledigt,
   N11.4.3), V1-V4, V7, V8, A1-A3 (G31-G33, ✅ als Gates übernommen 2026-07-15;
   bleibt die Umsetzung in Phase 8), G35, G30.
10. N11.5-Präzisierung: U14 (Radio-Paket + verweigerter Zugriff) und U15
    (`set_online`-Vertrag + `get_wifi_signal`-Kadenz) sind seit dem 2026-07-15 erledigt;
    bleibt der W1-Entscheid.

**P4, Phase 9:**
11. A4-A6 (G34 + G27-Ergänzung, ✅ übernommen 2026-07-15; `text_select=False` ist
    P1-sofort, Termin 2026-07-20), V10 (Release-Story), V12 (Testliste inkl.
    G28-Automatisierung), U25/V9 (Python-Pin, Hash-Build).

---

## Schlussbemerkung

Die N11-Runde hat gezeigt, dass der Plan-Prozess funktioniert: Die schwersten
Altkonflikte (In-Memory vs. Kaskade, Killswitch vs. G13, Win+L) wurden erkannt und
sauber entschieden, inklusive eines neuen Beweis-Gates. Die verbleibenden Probleme
haben zwei Muster. **Erstens** wurden die N10/N11-Entscheidungen nur teilweise in
den Altbestand zurückgeschrieben; die gefährlichsten Reste sind die Lock/Funk-
Kollision (W1, die einzige Stelle, die aktiv schädliches Verhalten vorschreibt),
die Phase-8-Tun-Liste mit dem alten Krypto-Design (W2) und die G14-Zeile mit
`private_mode=True` (W3). **Zweitens** fehlen Querschnitts-Verträge, die keiner
Phase "gehören": der Onboarding-/Vault-Bridge-Vertrag (U1), die eine
Sperr-/Beenden-Sequenz (S5), das Bedrohungsmodell (S4) und die Fehler-/
Logging-Politik (S6). Nichts davon stellt das Design in Frage; es sind durchweg
Präzisierungen, und der grösste Teil ist reine Dokumentenarbeit, die verhindert,
dass die teure Phase 8 gegen die falsche Hälfte des Plans gebaut wird.
