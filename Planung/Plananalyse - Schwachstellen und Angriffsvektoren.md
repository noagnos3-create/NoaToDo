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
- **Teil 5 (A1-A7):** Angriffsvektoren, die der Plan nicht abdeckt.
- **Teil 6:** Vorschläge für neue Gates (ab **G29**, da N11.9 die Nummer G28 inzwischen
  selbst vergeben hat) und eine priorisierte Reihenfolge.

---

## TEIL 1: Widersprüche

### W1. Sperre vs. echter Flugmodus: N10 und N11.5 widersprechen sich, und die Kopplung ist als Ganzes gefährlich [Sec]

Der schwerste neue Widerspruch, weil er reales Fehlverhalten am System des Nutzers
produziert:

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

### W2. Phase 8 "Tun" beschreibt weiterhin das alte, verworfene Krypto-Design

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

### W3. Die G14-Definitionszeile fordert immer noch `private_mode=True`

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

### W4. G13 existiert in drei Fassungen, zwei davon veraltet

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

### W8. G8 verlangt einen Stärkemesser, N11.3 verbietet ihn

G8 (Zeile 497 und 1037-1038) verlangt "**erzwungene Passphrase-Stärke**
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

N7 (Zeile 1313-1315) führt "Clear completed (UX 3.8)" unter "fest eingeplant"; N11.2
(Zeile 1449-1450) und N11.7 (Zeile 1549) sagen "wird **nicht** gebaut". N8 hat für
seine gestrichenen Punkte Durchstreichungen bekommen, N7 nicht.

**Patch:** Den N7-Punkt durchstreichen oder entfernen (gleiches Muster wie in N8).

### W10. "Optional"-Reste und Geister-Features in A.1/A.2/Phase 8

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

### W11. `sqlcipher3-binary` vs. `sqlcipher3-wheels`

B.7 (Zeile 346) und Phase 0 Tun 2 (Zeile 671) schreiben `sqlcipher3-binary` vor.
Real (requirements.txt, CLAUDE.md): `sqlcipher3-binary` hat keine Windows-Wheels,
verwendet wird `sqlcipher3-wheels` (identische API). Wer Phase 0 nach Plan ausführt,
scheitert bei der Installation.

**Patch:** Beide Stellen korrigieren (ein Satz inkl. Begründung steht schon in
requirements.txt und kann übernommen werden).

### W12. `technische Grundlage.txt` beschreibt eine Architektur, die es nicht mehr gibt

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

### W13. Seed-Reste nach N11.1.4 (keine Demo-Daten mehr)

- Phase 3 Abnahme (Zeile 758): "bekommt die **echten Seed-Daten**": es gibt keine
  Seeds mehr; die Abnahme ist auf einem frischen Tresor nicht erfüllbar wie
  beschrieben (leere Listen + Default-Settings wären korrekt).
- Phase 9 Testliste (Zeile 1141): "db.py: CRUD, **Seed**, ...".

**Patch:** Beide Stellen auf den leeren Erststart umformulieren.

### W14. B.4 beschreibt an vier Stellen eine UI, die N11 abgeschafft hat

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

### W15. Fälligkeiten wurden stillschweigend mitentfernt, ohne Entscheid im Plan

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

Zeile 84 lässt offen, ob IDs aus UUIDs oder Zeitstempeln bestehen (der Code nutzt
`uuid4`). Zeitstempel-IDs wären kollisionsanfällig. Kleinigkeit, aber eine echte
Ratestelle in einem Vertragsabschnitt.

**Patch:** "per `uuid4`" schreiben.

### W17. Schnell-Checkliste widerspricht dem erreichten Stand

Phasen 0-5 sind unangehakt (Zeile 1704-1709), obwohl Phase 6 (angehakt) sie
voraussetzt und die App läuft. Für eine KI mit der Regel "eine Phase nach der
anderen, nicht vorgreifen" ist das eine Einladung, bei Phase 0 zu beginnen.

**Patch:** Phasen 0-5 mit Datum abhaken; künftig bei jedem Phasenabschluss pflegen.

### W18. Das neue Gate G28 fehlt in sämtlichen Gate-Übersichten

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

### S1. Gate-Mehrfachbuchführung ohne führende Quelle; die Drift ist messbar

Jedes Gate existiert bis zu viermal (B.9-Definition, Phasen-Wiederholung,
Schnellübersicht, CLAUDE.md). W3, W4, W8 und W18 sind genau die vorhergesagten
Kopier-Drifts, und bemerkenswert: Die grosse N11-Überarbeitung hat G18 in allen
Kopien nachgezogen, G13/G14 aber nur in je einer. Ohne Mechanik passiert das wieder.

**Patch:** B.9 zur einzigen normativen Quelle erklären (Definition + Status + Datum);
Phasen listen nur Gate-Nummern mit Verweis; die Schnellübersicht wird als "nicht
normativ, Stand <Datum>" markiert oder bei jeder Gate-Änderung mit editiert
(Redaktionsregel: "ein Gate ändern = alle vier Stellen in einem Commit").

### S2. "SOFORT"-Gates ohne Termin und Prüfweg; G22 und G11 sind seit Wochen überfällig, und G22 ist zu eng gefasst

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

### S4. Es gibt kein Bedrohungsmodell, und einzelne Zusagen überdehnen [Sec]

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

### S5. Die gemeinsamen Abläufe (Sperren, Beenden, Panik, Killswitch, Reset) sind über fünf Stellen verstreut und nirgends als eine Sequenz definiert

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

### S6. Mit G10 wurde auch die nicht sync-spezifische Fehler-Hygiene entsorgt; es gibt weder Fehlercode-Katalog noch Logging-Politik

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

### S7. Das UX-Audit hat keinen Status und ist inzwischen zur Falle geworden

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

**U2. `config.json` ist unterspezifiziert.** N11.3 sagt nur "Pfad und nicht-geheime
Startinfos". Offen: exaktes Schema (Versionsfeld!), Verhalten bei fehlender oder
korrupter Datei, bei nicht mehr erreichbarem Vault-Pfad (USB-Stick entfernt,
Netzlaufwerk weg), ob UNC-/Wechseldatenträger-Pfade erlaubt sind, und wo der
Rate-Limit-Zustand (U6) und der gemerkte Funk-Ausgangszustand (W1) leben.
**Vorschlag:** Schema festschreiben, z.B. `{version:1, vault_path, radio_baseline,
unlock_ratelimit:{fails, stage, next_try_at}}`; Fehlerfälle: Datei fehlt/korrupt ->
wie Erststart, aber mit Hinweis; Pfad unerreichbar -> eigener Fehlerbildschirm mit
"erneut suchen / neuen Tresor anlegen". Store-Python-Randfall beachten (V8).

**U3. Das Lock-Screen-Zweitprofil (N11.8.3) hat eine ungelöste technische
Grundannahme.** Der Plan markiert die PyWebView-Mechanik als "in Phase 8 zu
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

**U4. "Inaktivität" der Auto-Sperre ist undefiniert.** Was setzt den Timer zurück?
Nur Bridge-Aufrufe wären falsch (15 Minuten in einer Liste **lesen** ohne Klick =
Sperre mitten im Gebrauch); globale System-Idle-Zeit (GetLastInputInfo) wäre das
andere Extrem (App sperrt nie, solange irgendwo getippt wird, auch wenn NoaToDo
stundenlang im Hintergrund offen liegt: genau das Szenario, das N11.8.4 absichern
will).
**Vorschlag:** Aktivität = Eingabe-Ereignisse im App-Fenster (Maus/Tastatur/Scroll
im DOM); das Frontend meldet sie gedrosselt (z.B. höchstens alle 30 s) als
`activity_ping()` über die Bridge; der Backend-Timer (monotone Uhr, eigener Thread,
N11.8.4) sperrt bei `now - last_activity > timeout`.

**U5. Auto-Sperre vs. offene native Dialoge.** Feuert der Timer, während der
Export-Save-Dialog oder der Onboarding-Ordnerdialog offen ist, baut die Sperre nach
N11.8.3 das Hauptfenster ab, unter einem modalen nativen Dialog: Absturz-/
Hänger-Risiko.
**Vorschlag:** Während ein nativer Dialog offen ist, wird die Sperre aufgeschoben
und feuert unmittelbar nach dem Schliessen (Flag um `create_file_dialog`).

**U6. Rate-Limit: Persistenz und Uhrbasis fehlen.** Die N11.4-Leiter, nur im RAM
gehalten, wird durch Off-Knopf + Neustart in Sekunden zurückgesetzt (der Lock-Screen
hat den Off-Knopf ja gerade prominent). Wanduhr-Zeitstempel sind per Systemuhr
manipulierbar; die monotone Uhr überlebt den Neustart nicht.
**Vorschlag:** Zustand `{fails, stage, next_try_at}` in `config.json` persistieren
(U2); bei Rückwärtssprüngen der Systemuhr die laufende Sperrzeit neu starten.
Ehrliche Einordnung ins Bedrohungsmodell: Die Leiter bremst den beiläufigen Rater am
Gerät; der ernsthafte Angreifer kopiert die Datei und rät offline, dagegen stehen
nur Argon2-Kosten + Pepper.

**U7. Entsperr-Fehler: drei Quellen, keine entscheidbare Logik.** B.2 sagt
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
[Sec]** N11.3 sagt nur "Tresor wird neu verpackt". Offen: (a) frisches Salt und
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

**U10. Exportformate und -verhalten sind halb spezifiziert.** Offen: exakter
Dateiname (`export_list`: bereinigter Listenname; `export_all`: fester Name, z.B.
`NoaToDo-Export-2026-07-12.md`?), `txt`-Format konkret ("analog als reiner Text"
sagt nichts über die Checkbox-Darstellung: `[x] `-Präfix? Einrückung?), Kodierung
(UTF-8 ohne BOM festlegen), Verhalten bei Dialog-Abbruch (Rückgabe? kein
"Exported"-Toast!), Listen-Reihenfolge im Gesamtexport (Sidebar-`position`).
**Vorschlag:** Fünf Festlegungen in Phase 7 Punkt 1 ergänzen; das Abbruch-Verhalten
in die Abnahme aufnehmen (die alte "Exported ohne Datei"-Unehrlichkeit, UX 1.5, darf
nicht als "Exported nach Abbruch" wiederkehren).

**U11. `reorder`/`reorder_lists`/`move_task`: Randfälle undefiniert.** Was passiert
bei unvollständigen `ordered_ids` (nur die offenen? nur ein Teil?), fremden IDs,
Duplikaten? Wie werden Positionen vergeben (Neunummerierung 0..n-1?)? Behält eine
mit `move_task` verschobene erledigte Aufgabe ihren done-Status (und landet in der
done-Sektion der Zielliste)?
**Vorschlag:** `ordered_ids` muss exakt die Aufgabenmenge der Liste (bzw. die
Listenmenge) sein, sonst `{"error":"invalid"}`; das Backend nummeriert 0..n-1 neu;
`move_task` behält `done` und hängt ans Ende der jeweiligen Sektion.

**U12. Doppelte Listennamen.** Nirgends entschieden, ob zwei Listen "Ideas" heissen
dürfen (betrifft Rename-Modal, Export-Dateinamen, `Ctrl+1-9` nur optisch).
**Vorschlag:** erlauben (IDs sind der Schlüssel), nur festhalten; der Save-Dialog
regelt Dateinamens-Kollisionen beim Export ohnehin.

**U13. Positions-Invarianten beim Abhaken.** Wo landet eine abgehakte Aufgabe in der
done-Sektion (oben? unten?), und wohin kehrt sie beim Wieder-Öffnen zurück? Heute
macht der Code irgendetwas Konsistentes; als Vertrag ist es nirgends fixiert und
ändert sich beim nächsten Refactor stillschweigend.
**Vorschlag:** Ein Satz in B.1: "Abhaken hängt ans Ende von `done`, Wieder-Öffnen ans
Ende von `open`; `position` wird je Sektion geführt."

### N11.5: echter Flugmodus

**U14. Die technische Basis ist nicht benannt.** "WinRT `Windows.Devices.Radios`"
braucht in Python ein Projektionspaket (`winsdk`/`winrt-*`): eine **neue
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

**U15. `set_online`-Semantik unter echter Hardware.** Der Aufruf wird asynchron und
kann teilweise scheitern (WLAN ok, Bluetooth verweigert). Was gibt `set_online`
zurück, wann, und was zeigt die UI bei Teil-Erfolg? Wie oft pollt
`get_wifi_signal()` (heute: Frontend-Intervall, nirgends festgelegt)?
**Vorschlag:** `set_online` antwortet erst nach Abschluss mit
`{online, partial:bool}`; Teil-Erfolg erzeugt einen Toast; `get_wifi_signal`-Kadenz
festlegen (z.B. 10 s, pausiert bei offline).

### Theme, Fenster, Kleinkram

**U16. Theme-Auto: drei kleine Entscheidungen fehlen.** Was tut `Ctrl+J` bei
`theme=auto` (Vorschlag: Override auf das Gegenteil des aktuell effektiven Themes)?
Wie kommt man zurück zu `auto` (nur übers Settings-Segment?)? Und die "seltene
Gegenprüfung": welches Intervall (Vorschlag: 60 s)?

**U17. Argon2id: konkrete Parameter und der RAM-Randfall.** G8 nennt Spannen
(256-512 MB, t >= 3, "parallelism passend"); in den G16-Header müssen aber konkrete
Zahlen. Ausserdem kann eine 512-MB-Allokation auf RAM-knappen Maschinen scheitern:
Dann ist der Tresor auf genau diesem PC (an den er per Pepper gebunden ist!) nicht
entsperrbar, solange der RAM knapp ist; ein `MemoryError` mitten im Unlock darf
weder als "wrong passphrase" erscheinen noch die App abstürzen lassen.
**Vorschlag:** Default festschreiben (z.B. `memory_cost=256 MiB, time_cost=3,
parallelism=4`), `MemoryError` abfangen und verständlich melden ("close some
programs and retry"); die Parameter stehen im Header und werden beim
Passphrase-Wechsel (U8d) auf den Soll-Stand gehoben.

**U18. HKDF-Kleinigkeit.** G15 nennt die `info`-Labels, aber nicht den HKDF-Salt.
Eine Zeile genügt: `HKDF-SHA256(salt=None, info=b"noatodo/...", length=32)`, damit
zwei Implementierungen kompatibel sind.

**U19. G17 unter dem N11.9-Fallback ist offen.** G17 sagt "In-Memory-DB debounced
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

**U20. G17-Debounce ohne Obergrenze.** "3 s nach der letzten Änderung" heisst bei
Dauereingabe: nie. **Vorschlag:** Zusatz "spätestens alle 30 s, auch bei laufenden
Änderungen".

**U21. Killswitch/Reset im entsperrten Zustand: Reihenfolge.** N11.8.1 listet die
Löschziele, aber nicht die Reihenfolge relativ zu offenen Handles: erst
DB-Verbindung schliessen und Schlüssel nullen (G25), dann Dateien/Pepper löschen,
dann Profile wischen, dann beenden. Der Reset (N11.3) muss ausdrücklich dieselbe
Routine nutzen (inkl. Pepper-Löschung; der neue Tresor bekommt einen frischen
Pepper). Angenehmer Nebeneffekt, der dokumentiert gehört: Mit dem Pepper sterben
auch alle **früher kopierten** `.enc`-Stände endgültig, selbst wenn der Angreifer
später die Passphrase erführe.
**Vorschlag:** In die S5-Sequenz aufnehmen.

**U22. `Ctrl+Shift+!` und Tastaturlayouts.** Falls der Hotkey nach W5 (wieder)
eingeführt wird: Auf DE-Layout ist `!` = Shift+1 (funktioniert mit `e.key === '!'`),
auf Layouts mit `!` hinter AltGr feuert die Kombination nie.
**Vorschlag:** Auf `e.code`-Basis definieren (Ctrl+Shift+Digit1) oder als
Ctrl+Shift+1 dokumentieren.

**U23. Fehlercode-Katalog / Toast-Regel.** Siehe S6; zusätzlich den B.2-Satz "Das
Frontend zeigt das als Toast" präzisieren: `locked` und `no_vault` sind
Normalzustände (kein Toast), `invalid`/`internal` sind Toasts, Unlock-Fehler haben
ihre eigene N4-Darstellung.

**U24. Fensterzustand über Lock/Mini hinweg.** `maximized=True` ist umgesetzt;
undefiniert ist, in welchem Zustand das Fenster nach dem Unlock
(N11.8.3-Neuaufbau) und nach Mini-Ende erscheint (wieder maximiert? letzte Grösse?).
Klein, gehört in die U3-Spike-Liste.

**U25. Die Python-Version ist nirgends festgelegt.** Real läuft Store-Python 3.11;
`sqlcipher3-wheels` liefert Wheels nur für bestimmte Versionen; Phase 9 baut eine
`.exe`. **Vorschlag:** G11 um "Python auf 3.11.x pinnen (Dokumentation +
Build-Umgebung)" ergänzen.

---

## TEIL 4: Detail-Verbesserungen an bestehenden Gates

**V1 (G16): Header authentifizieren, `.tmp` verifizieren, Platz prüfen.** Der
G16-Header (Magic, Version, Argon2-Parameter, Salt, Nonce) ist bisher nicht
authentifiziert; er gehört als `associated_data` in `ChaCha20Poly1305.encrypt/
decrypt` (eine Zeile; macht jede Header-Manipulation zum sauberen AEAD-Fehler und
verhindert künftige Format-Downgrades). Zusätzlich: das frisch geschriebene `.tmp`
vor der `.bak`-Rotation einmal probeweise entschlüsseln (erst nach Erfolg rotieren,
sonst können zwei fehlerhafte Schreibzyklen beide Generationen zerstören) und freien
Plattenplatz vor dem Wrap prüfen. Die zufällige 12-Byte-Nonce ist bei dieser
Schreibfrequenz unbedenklich (kein Handlungsbedarf, nur als geprüft vermerken).

**V2 (G18): drei Präzisierungen.** (a) `argon2-cffi` exponiert Argon2s
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

**V3 (G19): Mutex-Namensraum.** `Local\NoaToDoSingleton` ist pro Logon-Session
eindeutig: Derselbe Benutzer über RDP/schnelle Benutzerumschaltung startet eine
zweite Instanz auf demselben Profil und derselben DB, exakt die Korruption, die G19
verhindern soll. **Patch:** `Global\NoaToDo-<User-SID>`.

**V4 (G13): als Allowlist formulieren.** Statt "jede ausser ..." eine explizite
Menge `ALLOWED_WHEN_LOCKED = {"unlock", "quit_app", "killswitch", "get_state"}`
(wobei `get_state` gesperrt nur `{"locked": true}` liefert; `lock`/`panic` dürfen
idempotent erlaubt sein). Vorteil: Jede künftig ergänzte Methode ist automatisch
gesperrt statt automatisch offen; W4 zeigt, wie schnell die Ausnahmenliste driftet.

**V5 (G20): Werte und Typen prüfen, nicht nur Keys und Längen.** Konkret:
`theme`/`density`/`sidebar` gegen Enums, `accent` gegen die sechs erlaubten
Hex-Werte (der Wert landet als CSS-Variable im DOM; mit Whitelist ist CSS-Injection
über Settings komplett tot), `sidebarWidth` beim **Schreiben** auf 180-520 klemmen
(heute laut CLAUDE.md nur beim Lesen geparst), `sound` bool, `autoLock` ganzzahlig
aus 0/1/5/15/30/60. `edit_task.fields` typprüfen. Am besten als kleines
deklaratives Schema pro Bridge-Methode am Decorator, dann kann Phase 9 das Schema
direkt testen.

**V6 (G21): verbotene Zeichen und Länge fehlen.** G21 entschärft Gerätenamen,
Punkte/Leerzeichen und Newlines, nicht aber die unter Windows unzulässigen Zeichen
`< > : " / \ | ? *` und `..`-Sequenzen im vorgeschlagenen Dateinamen (Listennamen
sind Freitext) und keine Längenkappung. **Patch:** Zeichen durch `_` ersetzen,
Ergebnis auf ~120 Zeichen kürzen, dann die bestehende Gerätenamen-Prüfung; gilt für
`export_list` und `export_all`.

**V7 (G23): Sperr-/Beenden-Pfade müssen das Clipboard sofort leeren.** Der
60-s-Auto-Clear lässt bei Lock/Panic/Quit/Killswitch bis zu 60 s Task-Text im
Clipboard zurück, während die App längst "zu" ist. Die Prüf-Logik ("nur wenn es noch
unser Inhalt ist") existiert bereits für den Timer; sie gehört zusätzlich in die
S5-Sequenz.

**V8 (G14): den Store-Python-Redirect einarbeiten.** CLAUDE.md dokumentiert, dass
`%LOCALAPPDATA%`-Schreibzugriffe der Store-Python-Installation nach
`...\Packages\PythonSoftwareFoundation...\LocalCache\...` umgeleitet werden; G14
erwähnt das nicht. Folgen: (a) Wisch-Werkzeuge/Anleitungen, die den literalen Pfad
nennen, verfehlen die echten Daten; (b) nach dem Umstieg auf die Phase-9-`.exe`
(keine Umleitung mehr) bleibt der alte umgeleitete Profilordner samt Cache für immer
liegen, niemand wischt ihn je. **Patch:** G14-Zusatz: Das Wischen operiert immer
in-process auf dem effektiven Pfad; Phase 9 bekommt einen Erststart-Schritt, der
bekannte Alt-Pfade einmalig entfernt; gleiches gilt für `config.json` (U2).

**V9 (G11): endlich einlösen + Python pinnen.** `requirements.txt` ist bis heute
ungepinnt (nur die Lock-Datei ist es); entweder requirements.txt pinnen oder den
Gate-Text auf "requirements.lock.txt ist führend, Installation nur daraus, Phase 9
mit `--require-hashes`" umformulieren, damit Anspruch und Praxis übereinstimmen.
Plus U25 (Python-Version).

**V10 (Phase 9): Update-/Release-Story fehlt komplett.** Kein Wort zu: Version
sichtbar machen (Status-Modal), wie Nutzer von einer neuen Version erfahren
(bewusst kein Auto-Update bei einer Offline-App, aber dann wenigstens ein manueller
Weg), und dass gepinnte Abhängigkeiten altern (Rebuild-Kadenz bei CVEs in
`cryptography`/`pywebview`; der Browser-Teil ist dank Evergreen-WebView2 versorgt).
**Patch:** Drei Sätze in Phase 9.

**V11 (G22): auf alle UI-Claims ausweiten.** Siehe S2: Header-Pill,
Lock-Screen-Untertitel und Panik-Endschirm-Text ("securely wiped") müssen bis
Phase 8 genauso ehrlich degradiert werden wie das Status-Modal (Beleg für heute:
app.js:517).

**V12 (G28/Phase 9): den Beweis automatisieren.** G28 verlangt den
Verschlüsselungs-Beweis; als Einmal-Handgriff verrottet er. **Patch:** pytest-Test,
der das Arbeits-Artefakt (Serialisat bzw. Temp-Datei) auf den SQLite-Klartext-Header
(`SQLite format 3`) und auf einen bekannten Task-String scannt und bei Fund failt.
In dieselbe Phase-9-Testliste gehören ausserdem: der G13-Test mit der
**Dreier-Ausnahme** (W4), ein XSS-Trägheitstest (Task-Text `<img src=x onerror=...>`
wird als Text gerendert), die Rate-Limit-Leiter inkl. Persistenz (U6), die
`.bak`-Neuverschlüsselung nach Passphrase-Wechsel (U8c) und der Datei-Killswitch
(löscht `.enc`/`.bak`/Pepper; Folgestart = Onboarding).

---

## TEIL 5: Nicht abgedeckte Angriffsvektoren

**A1. RAM-Inhalte erreichen die Platte an allen Schichten vorbei: Pagefile,
Ruhezustand, Crash-Dumps. [Sec]** Die entsperrte DB lebt im RAM (G6/N11.9); Windows
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

**A2. Tresor im Cloud-Sync-Ordner: Versionshistorie konserviert jeden Stand. [Sec]**
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

**A3. Die Dev-Altdaten: die heutige `tasks.db` ist mit öffentlichem Schlüssel
lesbar, ihr Verbleib ist ungeregelt. [Sec]** `DEV_AES_KEY` steht im Repo-Quelltext;
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

**A4. Debug-Schalter und DevTools im Release-Build.** `NOATODO_DEBUG=1` aktiviert
DevTools (main.py:523, `debug=_debug_enabled()`). Respektiert die Phase-9-`.exe`
dieselbe Umgebungsvariable, bekommt jeder mit kurzem Zugriff (oder eine neugierige
zweite Person am selben Konto) eine Konsole mit vollem `pywebview.api.*`-Zugriff auf
die laufende App, inklusive `killswitch()` (Datenvernichtung ohne Passphrase, per
G13 gesperrt erlaubt!). **Patch (Teil von Gate G34):** Der Release-Build ignoriert
die Env-Var (Build-Konstante), DevTools hart aus, zusätzlich
`AreDevToolsEnabled=false` in den CoreWebView2-Settings, soweit erreichbar.

**A5. Manipulierte Frontend-Dateien = persistente Codeausführung im Tresor.** G27
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

**A6. Kopier- und Auslass-Kanäle am gehärteten Clipboard vorbei.** G23 härtet nur
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

**A7. Fenstertitel und sichtbare Metadaten.** Der native Fenstertitel ist für jeden
Prozess ohne Privilegien lesbar (Fenster-Enumeration) und taucht in
Screen-Sharing-Übersichten, Task-Switchern und Tools wie PowerToys auf. Heute ist er
konstant "NoaToDo" (gut); es gibt aber keine Regel, die verhindert, dass später
Listen- oder Task-Namen in den Titel wandern (naheliegend z.B. im Mini-Modus).
**Patch:** Ein Satz als Regel in B.4: "Der native Fenstertitel enthält nie
Nutzerinhalte."

---

## TEIL 6: Neue Gates und Priorisierung

### Vorgeschlagene neue Gates (ab G29; G28 ist seit N11.9 vergeben)

| Gate | Phase | Kurz | Quelle |
|---|---|---|---|
| G29 | 7 (mit G20) | Fehler-Hygiene: kein `str(exc)` ans Frontend, Fehlercode-Katalog in B.2, keine Pfade/Interna in Meldungen; Release ohne persistentes Logfile (RAM-Ringpuffer im Status-Modal) | S6 |
| G30 | Doku, vor 8 | Bedrohungsmodell B.10: Angreiferklassen, Nicht-Ziele (Malware-als-Nutzer), Voraussetzungen (BitLocker), G18-Zusage konditionieren, Panik-Endschirm-Falschaussage als bewusste Abwägung dokumentieren | S4 |
| G31 | 8 | RAM-auf-Platte-Lecks: BitLocker-Empfehlung (+ Anzeige), `VirtualLock` für Schlüssel-Puffer, WER-/Traceback-Dump-Minimierung | A1 |
| G32 | 8 | Vault-Ort: Default `%LOCALAPPDATA%`, Warnung bei Cloud-Sync-Pfaden inkl. Hinweis "Killswitch löscht Cloud-Versionen nicht" | A2 |
| G33 | 8 | Dev-Altdaten entsorgen: `tasks.db` + Journal/WAL beim Umstieg bestmöglich löschen; forensische Rest-Ehrlichkeit dokumentieren | A3 |
| G34 | 9 | Release-Härtung WebView2: `NOATODO_DEBUG` wirkungslos, DevTools aus, `text_select=False` explizit + Test, Browser-Accelerator-Keys und Standard-Kontextmenü aus | A4, A6 |
| G35 | 8 | Eine gemeinsame, nummerierte Sperr-/Beenden-Sequenz für alle Ausgänge (Lock, Auto-Lock, Off, Finish, Killswitch, Reset, Fenster-X, atexit): Debounce-Flush, Clipboard-Clear, Schlüssel-Nullen, Wischen, Funk-Restore zuletzt, Mutex-Freigabe | S5, U21, V7 |
| G36 | 8 (Spezifikations-Pflicht) | Onboarding-/Vault-Bridge-Vertrag: `get_boot_state`, `create_vault`, `choose_vault_dir`, `change_passphrase` (inkl. `.bak`-Neuverschlüsselung), `reset_vault`; Onboarding-Screens in B.4; `config.json`-Schema | U1, U2, U8 |

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
   U17-U21 (Argon2-Werte, HKDF-Detail, G17-Fallback-Klärung, Debounce-Obergrenze,
   Killswitch-Reihenfolge), V1-V4, V7, V8, A1-A3 (G31-G33), G35, G30.
10. N11.5-Präzisierung (U14, U15) zusammen mit dem W1-Entscheid.

**P4, Phase 9:**
11. A4-A6 (G34), V10 (Release-Story), V12 (Testliste inkl. G28-Automatisierung),
    U25/V9 (Python-Pin, Hash-Build).

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
