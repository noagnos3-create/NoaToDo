# Plananalyse: Widersprüche, strukturelle Mängel und offene Angriffsvektoren

Stand: 2026-07-12.
Analysierte Dokumente: `Planung/Bauplan - NoaToDo.md` (Hauptgegenstand),
`Planung/weiteres/technische Grundlage.txt`, `Planung/weiteres/UX-UI Verbesserungen.md`,
`CLAUDE.md`. Wo der Plan Behauptungen über den Code macht, wurde der tatsächliche
Code (`Code/backend/*.py`, `Code/main.py`, `Code/frontend/*`) als Beleg herangezogen.
Zeilenangaben beziehen sich auf den heutigen Stand der Dateien.

Dieses Dokument ist bewusst vollständig statt kurz (gleiche Philosophie wie das
UX-Audit). Es ist in fünf Teile gegliedert:

- **Teil 1 (W1-W12):** Stellen, an denen der Plan sich selbst widerspricht.
- **Teil 2 (S1-S9):** Strukturelle Mängel des Plans als Dokument und Prozess.
- **Teil 3 (V1-V11):** Verbesserungen an bereits definierten Sicherheits-Gates
  (der Gate-Gedanke ist richtig, aber einzelne Gates haben Lücken im Detail).
- **Teil 4 (A1-A9):** Angriffsvektoren, die der Plan bisher gar nicht abdeckt,
  jeweils mit konkretem Patch-Vorschlag.
- **Teil 5:** Vorgeschlagene neue Gates (G28 ff.) und eine priorisierte Reihenfolge.

Nichts in diesem Dokument ändert den Plan; es ist die Grundlage für die Entscheidung,
was übernommen wird.

---

## TEIL 1: Selbstwidersprüche im Plan

### W1. Argon2-Hash speichern vs. nicht speichern (B.7 gegen G15), vierfach im Dokument

Das ist der gefährlichste Widerspruch, weil er den Kern der Phase-11-Krypto betrifft
und eine ausführende KI je nach Lesepfad zwei inkompatible Designs baut.

**Fundstellen, die das ALTE Design beschreiben (Argon2-Hash wird gespeichert,
Schlüssel als Teilstücke des KDF-Outputs):**
- B.7 Punkt 3 (Zeile 393-399): "Gespeichert wird nur der Argon2-Hash der Passphrase
  (zum Prüfen beim Entsperren) und das Salt" sowie "als getrennte Teilstücke aus dem
  KDF-Output".
- B.7 Punkt 5, Ablaufdiagramm (Zeile 420): "Argon2-Hash prüfen" als expliziter Schritt.
- Phase 11, Tun Punkt 1 (Zeile 1160): "`unlock(passphrase)` prüft den Argon2-Hash".
- Phase 11, Tun Punkt 3 (Zeile 1169-1170): "nur den Argon2-Hash der Passphrase ablegen".
- **CLAUDE.md**, Abschnitt "Passphrase / key derivation": "Store only the Argon2 hash
  (for unlock verification) and the salt" und "derive both keys as separate slices of
  KDF output".

**Fundstellen, die das NEUE Design vorschreiben (kein Hash, HKDF, Poly1305-Prüfung):**
- B.9 Nachtrag G15 (Zeile 535) und Phase-11-Gateliste (Zeile 1250-1253).
- Die "Präzisierung"-Box in B.7 (Zeile 403-411) erklärt zwar, dass G15/G18 die alten
  Details ersetzen, aber der ersetzte Text steht unverändert davor und danach, und
  Phase 11 "Tun" wiederholt das alte Design OHNE Hinweis auf die Präzisierung.

**Warum das kritisch ist:** Phase 11 "Tun" und die Phase-11-Gateliste stehen direkt
untereinander und fordern Gegenteiliges. Wer die Tun-Liste abarbeitet, speichert einen
Argon2-Verifikations-Hash und liefert damit genau das Offline-Orakel, das G15 verhindern
soll. Zusätzlich widerspricht CLAUDE.md (die Datei, die jede KI-Session zuerst liest)
dem verbindlichen G15.

**Patch:** B.7 Punkt 3, B.7 Punkt 5, Phase 11 Tun 1 und Tun 3 auf die G15-Formulierung
umschreiben (Master-Secret, HKDF mit `info`-Labels, Prüfung über den AEAD-Tag), die
"Präzisierung"-Box danach streichen (sie wird überflüssig, wenn der Haupttext stimmt),
und CLAUDE.md im Abschnitt "Passphrase / key derivation" nachziehen. Grundregel: ein
ersetztes Design wird ersetzt, nicht annotiert (siehe auch S1).

### W2. Arbeitskopie auf Platte vs. In-Memory-DB (B.7 gegen G6), inkl. CLAUDE.md

- B.7 (Zeile 378-383) beschreibt als Hauptdesign: Entpacken auf Platte, "Arbeitskopie
  in %TEMP% mit restriktiven Rechten", beim Sperren sicher löschen. Die In-Memory-Variante
  heisst dort ausdrücklich "Alternative für Puristen (optional, nicht Default)"
  (Zeile 435).
- G6 (Zeile 503 und 1184-1190) erklärt exakt diese Alternative zum **gewählten Default**
  ("ist hier der gewählte Default").
- CLAUDE.md, "Critical constraints", beschreibt weiterhin das Platten-Design als Ziel:
  "On unlock: unwrap -> write SQLCipher working copy to %TEMP% ...".

**Wirkung:** Wieder zwei inkompatible Bauanleitungen für Phase 11. Das Platten-Design
zieht ausserdem einen ganzen Rattenschwanz nach sich (Secure-Delete auf SSD, Shutdown-
Szenarien, Temp-Forensik), den G6 gerade eliminieren soll.

**Patch:** B.7 so umschreiben, dass In-Memory das Design ist und die Platten-Arbeitskopie
höchstens als verworfene Alternative dokumentiert wird. CLAUDE.md nachziehen. Punkt 5
(Ablaufdiagramm) entsprechend anpassen.

### W3. G6 (In-Memory) bricht unbemerkt das Doppel-Kaskaden-Versprechen von B.7

Das ist kein Formulierungs-, sondern ein ungelöster Design-Widerspruch:

B.7 verspricht verbindlich: `tasks.db.enc` = ChaCha20-Poly1305(**SQLCipher-Datei**),
"beide Schichten sind Pflicht". G6 verlangt gleichzeitig, dass die entsperrte DB nur
in `:memory:` existiert. Der Plan sagt an keiner Stelle, **wie** eine SQLCipher-Datei
in eine In-Memory-DB gelangen soll, und je nach Antwort kippt eine der beiden Zusagen:

1. **Weg über eine Temp-Datei** (SQLCipher-Bytes auf Platte schreiben, öffnen,
   `sqlite3`-Backup-API nach `:memory:`): widerspricht G6 direkt, die entschlüsselte
   Struktur liegt wieder auf der Platte.
2. **`Connection.deserialize()`** auf den SQLCipher-Bytes im RAM: erhält beide
   Schichten, setzt aber voraus, dass `sqlcipher3-wheels` die Serialize/Deserialize-API
   überhaupt exponiert und sie mit `PRAGMA key` zusammenspielt. Das ist ungeprüft; der
   Plan verlässt sich stillschweigend darauf.
3. **Payload als Klartext-SQLite** (im RAM entschlüsseln, plain `:memory:`-SQLite,
   beim Wrap nur ChaCha20 drum): dann existiert Schicht 1 (AES-256) im Ruhezustand
   **gar nicht mehr**, `tasks.db.enc` wäre nur noch einfach verschlüsselt, während
   B.7, `get_status()` und der Lock-Screen weiter "Doppel-Kaskade" behaupten. Das wäre
   dieselbe Sorte stiller Ehrlichkeitsbruch, die G22 an anderer Stelle verbietet.

Zusatzeffekt: G7 (roher Hex-Key für `PRAGMA key`) ergibt nur in den Varianten 1 und 2
Sinn. In Variante 3 gäbe es kein SQLCipher mehr, G7 wäre gegenstandslos. Die Gates
G6 und G7 stehen als unabhängige Pflichten nebeneinander, obwohl G7 von der G6-
Umsetzungsentscheidung abhängt.

**Patch:** Vor Phase 11 einen kleinen technischen Spike verbindlich einplanen:
prüfen, ob `sqlcipher3-wheels` `serialize()`/`deserialize()` unterstützt.
- Falls ja: Variante 2 als verbindlichen Mechanismus in B.7/G6 festschreiben
  (Payload = SQLCipher-Bytes, deserialisieren, `PRAGMA key` als Hex-Raw-Key, G7 gilt).
- Falls nein: bewusst entscheiden und dokumentieren, z.B. Variante 3 wählen, aber
  dann Schicht 1 ersetzen statt streichen: `tasks.db.enc` = ChaCha20-Poly1305(
  AES-256-GCM(serialisierte SQLite-Bytes)) mit zwei per HKDF getrennten Schlüsseln.
  Beide Schichten bleiben im Ruhezustand real, SQLCipher entfällt als Abhängigkeit.
  Status-Texte und B.7 entsprechend anpassen.
In jedem Fall: die Entscheidung gehört in den Plan, nicht in den Moment der Umsetzung.

### W4. G14 fordert `private_mode=True`, der auch im Plan dokumentierte Ist-Stand verbietet es

- Die G14-Definition in der B.9-Nachtragstabelle (Zeile 534) sagt wörtlich: "Pflicht:
  `webview.start(..., private_mode=True)` **explizit** setzen".
- Die aktualisierte G14-Beschreibung in der Phase-11-Gateliste (Zeile 1219-1249) und
  CLAUDE.md sagen das Gegenteil: `private_mode=False` mit festem `PROFILE_DIR` ist
  seit 2026-06-20 umgesetzt, und "Do NOT reintroduce `private_mode=True`" (der
  Privatmodus verursachte die Temp-Profil-Altlasten und Starthänger).

**Wirkung:** Wer die B.9-Tabelle als Referenz nimmt (sie ist als "verbindlich und vom
Nutzer bestätigt" markiert), baut eine dokumentierte Regression wieder ein. Genau dieser
Fehlertyp (Copy-Drift zwischen den drei Gate-Kopien) ist schon einmal passiert, siehe S1.

**Patch:** Die G14-Zeile in der B.9-Tabelle neu schreiben: fester Profilordner + Mutex
als umgesetzter Stand, offen nur noch das sichere Wischen bei lock/panic/quit und der
Umgang mit verwaisten `msedgewebview2.exe`. Der Satz mit `private_mode=True` muss dort
ersatzlos raus.

### W5. `sqlcipher3-binary` vs. `sqlcipher3-wheels`

- B.7 Schicht 1 (Zeile 363-364): "Paket `sqlcipher3-binary`".
- Phase 0, Tun Punkt 2 (Zeile 699-701): `requirements.txt` soll `sqlcipher3-binary`
  enthalten.
- Realität (CLAUDE.md, `Code/requirements.txt`, `requirements.lock.txt`):
  `sqlcipher3-binary` hat keine Windows-Wheels; verwendet wird `sqlcipher3-wheels`.

**Wirkung:** Wer Phase 0 nach Plan ausführt, scheitert bei der Installation auf Windows.

**Patch:** Beide Stellen auf `sqlcipher3-wheels` (Import `sqlcipher3`) korrigieren,
mit dem Hinweis aus requirements.txt (identische API).

### W6. "Optional verschlüsselt" und "optionale App-Sperre" vs. "immer verschlüsselt, beide Schichten Pflicht"

Der Plan sagt an vier Stellen "optional", obwohl B.7 Verschlüsselung und B.8 die Sperre
als zwingend definieren:

- A.1 (Zeile 30): "Optionale App-Sperre (Lock-Screen)". B.8 und Phase 11 machen die
  Sperre samt Passphrase aber zur Pflicht (App startet **immer** gesperrt; ohne
  Passphrase gibt es gar keinen Schlüssel, die DB kann nicht geöffnet werden). Eine
  "optionale" Sperre ist mit passphrase-abgeleiteten Schlüsseln technisch unmöglich.
- A.2, Architekturdiagramm (Zeile 55): "data/tasks.db (SQLite, lokal, optional
  verschlüsselt)".
- Phase 11, Ziel (Zeile 1154): "und (optional) Datenbank-Verschlüsselung real machen".
- Phase 11, Abnahme (Zeile 1271): "bei aktivierter Verschlüsselung ist tasks.db ohne
  Passphrase nicht lesbar". Es gibt keinen Zustand "deaktivierte Verschlüsselung";
  ausserdem heisst das Ruhe-Artefakt `tasks.db.enc`, nicht `tasks.db`.

**Patch:** Alle vier Stellen bereinigen ("optional" streichen, Dateiname korrigieren).
Das ist billig, verhindert aber, dass jemand einen unverschlüsselten Modus als legitime
Auslegung des Plans baut, was G9 durch die Hintertür wieder öffnen würde.

### W7. Phasenumfang: "Phase 0-11" vs. "Phase 0 bis 12"

- Einleitung (Zeile 12): "Teil C ist die eigentliche Schritt-für-Schritt-Baufolge
  (Phase 0-11)".
- Teil-C-Überschrift (Zeile 672): "Baufolge (Phase 0 bis 12)"; Phase 12 existiert
  vollständig inkl. Gate G27.
- CLAUDE.md, "Build phases": endet bei Phase 11, Phase 12 fehlt dort komplett.

**Patch:** Einleitung und CLAUDE.md auf Phase 12 erweitern. Klein, aber CLAUDE.md ist
die Datei, nach der sich Sessions richten; eine dort unsichtbare Phase wird vergessen.

### W8. Nachtrags-Überschrift "Gates G13 bis G25" enthält G26 und G27, Nummerierung ausser Reihenfolge

Die B.9-Nachtragstabelle (Überschrift Zeile 522) heisst "G13 bis G25", enthält aber auch
G26 (verworfen) und G27, und die Zeilenreihenfolge ist G22, G23, **G26**, G24, G25, G27.
Wer die Tabelle gegen die Überschrift prüft oder Gates abzählt, übersieht G26/G27 leicht.

**Patch:** Überschrift auf "G13 bis G27" ändern und die Tabellenzeilen numerisch
sortieren (G26 hinter G25).

### W9. B.2 nennt sich "vollständige Methodenliste", ist es aber nicht mehr

B.2 (Zeile 135-136) beansprucht Vollständigkeit als Vertrag. Tatsächlich fehlen dort
`set_mini(flag)` und `get_wifi_signal()`, beide implementiert und in CLAUDE.md
dokumentiert. Umgekehrt beschreibt B.4/B.6 weiterhin den Toolbar-Modus
`flush`/`floating` als Einstellung, während CLAUDE.md festhält, dass `toolbar` nicht
mehr im Settings-UI existiert und beim Lesen ignoriert wird (Rail immer floating).

**Wirkung:** Der "Vertrag zwischen vorne und hinten" ist keiner mehr, wenn er stillschweigend
hinter der Implementierung herhinkt. Neue Methoden ohne Vertragseintrag bekommen auch
keine Gate-Prüfung (Beispiel: `get_wifi_signal` startet einen `netsh`-Subprozess; so
etwas sollte durch die B.2-Pflege automatisch einen Sicherheitsblick bekommen).

**Patch:** B.2 um `set_mini` und `get_wifi_signal` ergänzen; Regel in den Plan
aufnehmen: jede neue Bridge-Methode wird erst in B.2 eingetragen (inkl. Sicherheits-
notiz), dann gebaut. Toolbar-Passagen in B.4/B.6 an den Ist-Zustand angleichen oder
die Rückkehr des Features explizit beschliessen.

### W10. CDN-Optionen widersprechen der eigenen CSP- und Local-First-Doktrin

- A.3 (Zeile 74-77): "Wer lieber React behalten will, kann React/ReactDOM per CDN laden".
- technische Grundlage §2 (Zeile 27): "Optional: Tailwind per CDN als Design-Beschleuniger".

Beides ist mit der verbindlichen CSP (`default-src 'self'`, B.9 Regel 2), dem
Font-Lokal-Gebot (B.3: "kein externer Font-Load") und G12 (keine externe Navigation)
unvereinbar. Eine "erlaubte Alternative", die die Pflicht-CSP bricht, ist keine.

**Patch:** Beide CDN-Sätze streichen oder mit dem expliziten Vermerk versehen, dass
sie mit CSP/G12 unvereinbar sind und nur mit lokal gebündelten Kopien denkbar wären.

### W11. technische Grundlage.txt beschreibt ein anderes Fundament als der Bauplan

Der Bauplan verspricht in der Einleitung (Zeile 5-7), die App laufe "auf dem in
`technische Grundlage.txt` beschriebenen Fundament". Die Grundlage sagt aber:
SQLite über Pythons **eingebautes `sqlite3`-Modul** (§2), keine Verschlüsselung,
kein SQLCipher, kein Argon2, keine Doppel-Kaskade. Der Bauplan hat das Fundament
längst ersetzt, ohne dass das Dokument es erfährt.

**Patch:** Entweder die Grundlage aktualisieren (SQLCipher + Kaskade als Fundament)
oder im Bauplan den Verweis präzisieren ("Fundament mit den in B.7 beschlossenen
Abweichungen"). Sonst gilt für eine ausführende KI Dokument gegen Dokument.

### W12. B.5-Tastenkürzel-Tabelle hinkt dem Soll-Stand hinterher

CLAUDE.md dokumentiert `Ctrl+ArrowUp`/`Ctrl+ArrowDown` (Listenwechsel) und die
Randbedingungen ("F braucht eine offene Liste", Verhalten im gesperrten Zustand);
B.5 kennt beides nicht. Das UX-Audit (2.3) listet weitere Lücken (fehlender
Mini-Modus-Shortcut, `Esc`/`?` nicht im Modal). B.5 ist als "verbindlich" markiert,
beschreibt aber nicht mehr das verbindliche Verhalten.

**Patch:** B.5 einmal mit CLAUDE.md und dem realen `onKeyGlobal` abgleichen und die
Tabelle als die eine Wahrheit führen (CLAUDE.md kann darauf verweisen).

---

## TEIL 2: Strukturelle Mängel

### S1. Dreifache Gate-Buchführung ohne führende Quelle, Drift ist bereits eingetreten

Jedes Gate existiert bis zu dreimal: Definition in B.9, Wiederholung in der Phase,
Kurzzeile in der Schlusstabelle. Der Plan nennt das Absicht ("damit sie nicht übersehen
werden"), aber ohne festgelegte führende Quelle divergieren die Kopien nachweislich:
G14 (W4) fordert in einer Kopie das Gegenteil der anderen; G12 trägt je nach Stelle die
Phase "3/11", "vor 7 (vorgezogen)" oder "3". Bei G22 ("SOFORT") widersprechen sich
Anspruch und dokumentierter Stand seit einem Monat (siehe S2).

**Patch:** B.9 zur einzigen normativen Quelle erklären (Definition + Statusspalte +
Datum). Die Phasen-Wiederholungen auf reine Verweise reduzieren ("Gates dieser Phase:
G20, G21, G22, siehe B.9"), die Schlusstabelle generieren oder als "nur Übersicht,
nicht normativ" markieren. Bei jeder Statusänderung wird genau eine Stelle editiert.

### S2. "SOFORT"-Gates ohne Termin, Besitzer oder Prüfmechanik; G22 und Teile von G10 sind seit einem Monat überfällig

G22 ist seit 2026-06-10 als "SOFORT, spätestens mit 7" markiert. Stand heute
(2026-07-12) zeigt `frontend/app.js:531-532` weiterhin die Fantasiewerte
"AES-256 + ChaCha20 · Argon2id / active" und "Tasks.Read · token valid", und der
`@bridge`-Decorator gibt weiterhin `str(exc)` ans Frontend (`backend/api.py:32`),
was G10 mindestens für Pfad-Lecks heute schon relevant macht (siehe V11). Der Plan
besitzt keine Mechanik, die "sofort" von "irgendwann in Phase 7" unterscheidbar macht:
kein Fälligkeitsdatum, keine Statusspalte mit Datum, kein Prüfkommando.

**Patch:** In der (nach S1 einzigen) Gate-Tabelle drei Spalten ergänzen: Status,
Datum, Prüfweg (ein Satz oder ein konkreter Grep/Handgriff, z.B. für G22: "Status-Modal
öffnen; es darf kein 'active' bei Encryption stehen, solange `DEV_AES_KEY` existiert").
"SOFORT"-Punkte bekommen ein konkretes Zieldatum oder werden sofort erledigt; alles
andere ist Selbsttäuschung mit Ansage.

### S3. Die Schnell-Checkliste widerspricht dem erreichten Stand

Phasen 0-5 sind in der Checkliste unangehakt, obwohl Phase 6 (angehakt) sie logisch
voraussetzt und die App läuft. Für einen menschlichen Leser ist das kosmetisch; für
eine ausführende KI mit der Regel "eine Phase nach der anderen, nicht vorgreifen"
ist es eine Aufforderung, bei Phase 0 zu beginnen.

**Patch:** Phasen 0-5 abhaken (mit Datum), und die Checkliste bei jedem Phasenabschluss
pflegen. Zusätzlich die Regel aus der Einleitung ergänzen: "Vorgezogene Gates (G12,
G19, G22, Teile von G14, G23) sind erlaubt und in B.9 mit Datum vermerkt", denn die
strikte Phasenregel wird vom Plan selbst systematisch durchbrochen.

### S4. Es gibt kein explizites Bedrohungsmodell

Die Gates adressieren implizit mindestens fünf verschiedene Angreifer, ohne sie je zu
benennen: (1) Remote-Angreifer über den Sync-Kanal (G1-G4, B.9), (2) Dieb der Datei
oder Platte (B.7, G15-G18), (3) forensischer Zugriff auf den Rechner (G6, G14, G23),
(4) Person mit kurzem physischen Zugriff auf die laufende App (B.8, G13),
(5) Reverse-Engineer des Binaries (G27). Weil das Modell fehlt:

- gibt es Überversprechen: G18 sagt, ohne Pepper könne ein Datei-Dieb "offline gar
  nicht raten". Das stimmt nur, solange der Dieb nicht auch den Credential-Manager-
  Bestand hat; bei einer gestohlenen ungeschützten Platte hängt der DPAPI-Schutz des
  Peppers direkt an der Stärke des Windows-Anmeldepassworts (offline knackbar).
  Ohne BitLocker ist der Pepper also kein absolutes "gar nicht", sondern "so stark
  wie das Windows-Passwort".
- fehlt die ehrliche Grenze: Malware, die als derselbe Benutzer läuft, liest Pepper
  (keyring), Tastatur (Passphrase) und RAM; dagegen hilft keine der geplanten
  Massnahmen. Das darf so sein, muss aber ausgesprochen werden, sonst werden Gates
  gegen diesen Angreifer "erfunden" (G26 war genau so ein Fall).
- fehlen Umgebungs-Voraussetzungen: mehrere Schutzversprechen (siehe A3) gelten nur
  mit aktiver Festplattenverschlüsselung (BitLocker).

**Patch:** Neuen Abschnitt B.10 "Bedrohungsmodell" einziehen: Tabelle Angreiferklasse ->
was schützt -> was schützt NICHT -> Voraussetzungen. Jedes Gate referenziert die
Klasse(n), gegen die es wirkt. Aufwand: eine Seite; Nutzen: Überversprechen und
Schein-Gates werden systematisch sichtbar. (Vorschlag als Gate G28 in Teil 5.)

### S5. Der Lebenszyklus Lock/Panic/Quit gegen laufende Hintergrundarbeit ist nirgends spezifiziert

G4 (Schreib-Lock), G13 (Lock serverseitig), G17 (debounced Write-back) und der
Sync-Thread (Phase 9) beschreiben je ein Teil, aber ihre Wechselwirkung fehlt:

- Was passiert, wenn `lock()` feuert, während der Sync-Thread mitten in einem
  DB-Write steckt? (Schlüssel nullen, während ein anderer Thread sie benutzt,
  ist Korruption oder Crash.)
- Was passiert mit einem noch ausstehenden Debounce-Timer (G17), der nach dem
  Nullen der Schlüssel feuert?
- In welcher Reihenfolge laufen: Sync stoppen, Debounce abbrechen/flushen, Wrap
  nach G16, Schlüssel nullen (G25), WebView-Cache wischen (G14), UI sperren?
- Windows-Shutdown/`WM_ENDSESSION` fehlt als Ereignis komplett (B.8 kennt nur die
  Sitzungssperre). Mit G6/In-Memory kostet ein harter Shutdown nur die letzten
  Sekunden (G17), aber der saubere Shutdown-Pfad sollte denselben Wrap-Weg gehen
  wie `lock()`.

**Patch:** In Phase 11 eine verbindliche Sperr-Sequenz festschreiben (Zustandsmaschine,
eine halbe Seite): (1) neue Bridge-Calls ablehnen (G13-Flag setzen), (2) Sync-Thread
signalisieren und auf Abschluss des laufenden Schreibvorgangs warten (G4-Lock
akquirieren), (3) Debounce-Timer abbrechen und synchron persistieren (G16-Wrap),
(4) Schlüssel nullen (G25), (5) UI-Event `onLocked`. Panic identisch plus
offline schalten, Clipboard leeren (V9) und Profilordner wischen. `quit` und
`WM_ENDSESSION` nutzen dieselbe Sequenz.

### S6. G10 verlangt "serverseitig loggen", aber es gibt keine Logging-Policy

Der Plan sagt mehrfach "Details nur serverseitig loggen" und "keine Tokens/Delta-Links/
Pfade im Log", definiert aber nie: Wo landen Logs (Datei? stderr? gar nicht)? Was darf
grundsätzlich hinein? Eine Tresor-App, die Task-Inhalte oder auch nur Task-IDs und
Zeitstempel in eine unverschlüsselte Logdatei schreibt, unterläuft ihre eigene
Verschlüsselung (Nutzungsprofil + Inhalte im Klartext neben dem Tresor).

**Patch (Vorschlag Gate G33):** Logging-Policy in B.9 aufnehmen: niemals Task-Text,
Listennamen, Meta, Passphrase, Schlüssel, Tokens, Delta-Links; im Release-Build kein
persistentes Logfile (nur In-Memory-Ringpuffer, einsehbar über das Status-Modal),
Datei-Logging nur als bewusste Debug-Option; Exceptions werden vor dem Loggen um Pfade
gekürzt.

### S7. Kein Passphrase-Wechsel, keine Recovery-Story, kein KDF-Upgrade-Pfad

Phase 11/12 definieren Ersteinrichtung und Entsperren, aber:

- **Passphrase ändern** existiert im gesamten Plan nicht (weder Bridge-Methode noch
  UI). Ohne den Flow bleibt eine einmal kompromittierte oder schwache Passphrase für
  immer.
- **Argon2-Parameter-Upgrade:** Der G16-Header speichert die Parameter, aber es gibt
  kein Verfahren, bestehende Tresore bei einem Parameter-Update (stärkere Hardware,
  neue Empfehlungen) neu zu wrappen.
- **Verlust-Szenarien** sind nur halb gedacht: G18 hat den Pepper-Recovery-Export,
  aber es gibt keine dokumentierte Antwort auf "Passphrase vergessen" (korrekt wäre:
  ehrlich "Daten weg", das sollte im Onboarding stehen) und keine auf "tasks.db.enc
  und .bak beide defekt" (siehe A8).

**Patch (Vorschlag Gate G34):** Neue Bridge-Methode `change_passphrase(old, new)`
(entsperrt prüfen, neues Salt + frische Nonce, komplettes Re-Wrap nach G16, Pepper
bleibt); beim Entsperren Header-Parameter mit Soll vergleichen und bei Abweichung
transparent neu wrappen ("KDF-Upgrade on unlock"); Onboarding-Text mit der ehrlichen
Verlustregel ("keine Hintertür, Passphrase weg = Daten weg").

### S8. Phase 8 ignoriert die praktische Token-Cache-Frage (Windows-Credential-Grössenlimit)

Der Plan sagt "Refresh-Token via keyring in den Credential Manager". Real serialisiert
MSAL einen Token-Cache (JSON mit Access-/Refresh-Token, Account-Metadaten), der
typischerweise mehrere KB gross ist; Windows-Credential-Blobs sind auf 2560 Bytes
begrenzt, `keyring` schlägt dann fehl oder es wird gestückelt. Genau an solchen
ungeplanten Stellen entstehen unsichere Ad-hoc-Lösungen ("schreiben wir den Cache
halt in eine Datei").

**Patch (Vorschlag Gate G35):** In Phase 8 festschreiben, wie der MSAL-Cache
persistiert wird. Saubere Optionen: (a) `msal-extensions` mit
`FilePersistenceWithDataProtection` (DPAPI-verschlüsselte Cache-Datei, dafür gebaut),
oder (b) nur das Refresh-Token extrahieren und in keyring legen, Access-Tokens stets
frisch holen. Verboten: Cache im Klartext auf Platte oder in der DB.

### S9. Der Plan behauptet über sich selbst Vollständigkeit an Stellen, die veralten

Wiederkehrendes Muster (W1, W4, W9, W11, S3): Absolut formulierte Aussagen
("vollständige Methodenliste", "verbindlich", "exakt wie das Konzept") ohne Datums-
oder Stand-Vermerk. Die Nachträge zeigen, dass das Team diszipliniert nachträgt,
aber immer additiv (neue Boxen, neue Tabellen) statt substituierend; dadurch wächst
die Zahl widersprüchlicher Textschichten mit jedem Audit.

**Patch:** Redaktionsregel in die Einleitung: Nachträge ersetzen den Alttext an Ort
und Stelle (der Alt-Wortlaut darf in einer Fussnote überleben), Boxen wie die
"Präzisierung" in B.7 sind nur Übergangszustand und werden beim nächsten Edit
eingearbeitet. Einmalige "Konsolidierungs-Session" für die in Teil 1 gelisteten
Stellen einplanen, bevor Phase 7 startet.

---

## TEIL 3: Verbesserungen an bestehenden Gates

### V1. G2 (Host-Whitelist) präzisieren: exakter Host-Vergleich, Schema-Zwang, keine Suffix-Prüfung

G2 sagt nur "Host ist `graph.microsoft.com`". Damit die Umsetzung nicht daneben greift:

- **Exakter Vergleich** des geparsten Hostnamens (`urlsplit(url).hostname ==
  "graph.microsoft.com"`), niemals `url.startswith(...)` oder `hostname.endswith(
  "graph.microsoft.com")` (sonst passt `graph.microsoft.com.evil.com` bzw.
  `https://graph.microsoft.com.evil.com/...`).
- **Schema erzwingen:** nur `https`, sonst abbrechen (ein `http://graph.microsoft.com`
  würde das Bearer-Token im Klartext senden).
- **Userinfo/Port ablehnen:** URLs mit `@` im Authority-Teil oder explizitem Port
  verwerfen (klassische Parser-Verwirrung `https://graph.microsoft.com@evil.com/`).
- Delta-/Next-Links nie aus der Antwort "reparieren" oder zusammensetzen; entweder
  sie bestehen die Prüfung, oder der Sync bricht mit `sync_failed` ab.

### V2. G5 (OAuth-Härtung) um zwei konkrete httpx-Punkte ergänzen

- "Kein Proxy-Vertrauen" steht als Wort im Gate, hat aber keinen technischen Anker:
  httpx honoriert per Default `HTTP(S)_PROXY`-Umgebungsvariablen (`trust_env=True`).
  Konkretisieren: `httpx.Client(trust_env=False)` für alle Graph-/Auth-Calls, TLS-
  Verifikation explizit an (Default belassen, `verify=False` verboten wie gehabt).
- Loopback-Redirect: dokumentieren, dass ein lokaler Port-Squatter den Redirect zwar
  empfangen kann, PKCE den Code aber wertlos macht; wichtig ist, dass der eigene
  Listener bei belegtem Port einen anderen freien Port nutzt und der Flow bei
  `state`-Mismatch kommentarlos abbricht (kein Retry mit demselben `state`).

### V3. G16 (Dateiformat) härten: Header als AAD binden, Recovery-Realismus

- Der Header (Magic, Version, Argon2-Parameter, Salt, Nonce) ist im aktuellen Entwurf
  **nicht authentifiziert**; Poly1305 deckt nur den Ciphertext. Ein Angreifer kann
  Version/Parameter/Salt manipulieren. Praktisch führt das "nur" zu Entschlüsselungs-
  fehlern, aber es öffnet Format-Verwirrung bei künftigen Versionen (Downgrade auf
  eine schwächere v2-Interpretation). **Patch:** den kompletten Header als
  `associated_data` in `ChaCha20Poly1305.encrypt/decrypt` geben; kostet eine Zeile
  und macht jede Header-Manipulation zu einem sauberen AEAD-Fehler. (Vorschlag
  Gate G30.)
- Nonce-Strategie ist mit `os.urandom(12)` und dieser Schreibfrequenz in Ordnung
  (Kollisionsrisiko vernachlässigbar); kein Handlungsbedarf, nur als geprüft vermerken.
- Die eine `.bak`-Generation schützt nicht gegen den Fall "zwei defekte Wraps in
  Folge" oder "Platte voll während des Wraps". **Patch:** vor `os.replace` das frisch
  geschriebene `.tmp` einmal probeweise entschlüsseln (Tag-Check über die ersten
  Bytes genügt nicht, AEAD prüft ohnehin alles beim Decrypt) und `.bak` erst rotieren,
  wenn das neue File verifiziert ist; freien Plattenplatz vor dem Wrap prüfen.
  Zusätzlich die D.3-Idee "automatische Backups mit Rotation" von "später" zu einem
  Phase-11-Anhängsel machen (täglich eine Generation, N=7, alles nur `.enc`-Kopien,
  kostet fast nichts und entschärft A8).

### V4. G18 (DPAPI-Pepper): drei Detailprobleme

1. **`argon2-cffi` exponiert den Argon2-`secret`-Parameter (Key K) nicht.** Das Gate
   schreibt "Argon2id-`secret`-Parameter" vor, aber die gepinnte Bibliothek
   (`argon2-cffi`, high-level wie `low_level.hash_secret_raw`) bietet dafür keinen
   Parameter (das `secret`-Argument dort IST die Passphrase). Vor Phase 11 prüfen;
   falls unverändert: Pepper stattdessen definiert einmischen, z.B.
   `ikm = HKDF-Extract(salt=pepper, ikm=passphrase)` vor Argon2, oder
   `argon2(passphrase_bytes + pepper)` mit fester Längenkodierung. Kryptografisch
   gleichwertig für den Zweck, aber es muss EIN Verfahren verbindlich im Plan stehen,
   sonst entstehen inkompatible Tresore.
2. **Der Recovery-Export in Klartext neutralisiert den Pepper**, wenn der Nutzer die
   Recovery-Datei dort ablegt, wo auch das Backup der `tasks.db.enc` liegt (der
   realistische Normalfall: beides im selben Cloud-Ordner oder auf demselben Stick).
   **Patch (Vorschlag Gate G39):** Recovery-Export nicht als Klartext-Pepper, sondern
   als ChaCha20-Poly1305-Blob, verschlüsselt mit einem NUR aus der Passphrase
   (eigenes Salt, ohne Pepper) abgeleiteten Schlüssel. Dann gilt: Recovery-Datei +
   `tasks.db.enc` zusammen sind ohne Passphrase weiterhin wertlos (gleiches
   Sicherheitsniveau wie "kein Pepper"), aber der legitime Nutzer kann nach
   Windows-Verlust mit Passphrase + Recovery-Datei wiederherstellen. Im Setup-Dialog
   ausdrücklich sagen: "nicht neben die Datenbank legen".
3. **Überversprechen entschärfen** ("gar nicht raten"): siehe S4; der Satz sollte die
   Bedingung nennen (Pepper fällt mit dem Windows-Konto bzw. dem Windows-Passwort,
   ohne BitLocker).

### V5. G19 (Single-Instance): `Local\`-Mutex deckt nicht alle Fälle

`Local\NoaToDoSingleton` ist pro **Logon-Session** eindeutig. Meldet sich derselbe
Benutzer zweimal an (RDP + Konsole, schnelle Benutzerumschaltung), laufen zwei
Instanzen mit demselben `%LOCALAPPDATA%`-Profil und derselben DB: exakt die
Korruption, die G19 verhindern soll. **Patch:** `Global\NoaToDo-<User-SID>` als
Mutex-Name (SID statt Benutzername, um Kollisionen und Sonderzeichen zu vermeiden);
pro Benutzer bleibt es genau eine Instanz, verschiedene Benutzer stören sich nicht.
(Vorschlag Gate G37.)

### V6. G13 (Lock serverseitig): als Allowlist formulieren, nicht als Blocklist

"Jede Methode ausser `unlock`" ist als Verbotsliste formuliert; sicherer ist die
Erlaubnisliste, weil neue Methoden (W9 zeigt: die Bridge wächst) sonst standardmässig
durchrutschen könnten, je nachdem wie der Decorator gebaut wird. **Patch:** Im
Decorator eine explizite Menge `ALLOWED_WHEN_LOCKED = {"unlock", "lock", "panic",
"get_state"}` (wobei `get_state` gesperrt nur `{"locked": true}` liefert, `lock`/
`panic` idempotent sind); alles andere liefert `{"error": "locked"}`, ohne die DB
zu berühren. Auch `set_mini`/`get_wifi_signal` fallen damit automatisch unter die
Sperre. Backend-Events (`emit`) dürfen im gesperrten Zustand keine Inhalte tragen
(kein `onNotification` mit Task-Titel an einen gesperrten Screen).

### V7. G20 (Eingabe-Validierung): Werte und Typen fehlen, nicht nur Keys und Längen

G20 prüft Länge, Steuerzeichen, `reorder`-Typ und Setting-**Keys**. Offen bleiben:

- **Setting-Werte:** `accent` gegen die sechs erlaubten Hex-Werte prüfen (der Wert
  landet als CSS-Variable im DOM; mit Whitelist ist die Klasse "CSS-Injection über
  Settings" komplett tot), `density`/`sidebar`/`toolbar` gegen Enums, `sidebarWidth`
  auch beim **Schreiben** auf 180-520 klemmen (heute wird laut CLAUDE.md nur beim
  Lesen geparst), Bool-Keys nur `true`/`false`.
- **`edit_task.fields`:** `done` als bool erzwingen, `due_at` gegen ISO-8601 validieren
  (heute nimmt die Spalten-Whitelist jeden String; ein kaputtes Datum crasht später
  still die Fälligkeitslogik aus Phase 10, importierte Daten siehe A5).
- **Systematik statt Einzelfälle:** pro Bridge-Methode ein kleines deklaratives
  Schema (Typ, Maxlänge, Enum/Regex) am Decorator, statt verstreuter `if`-Prüfungen.
  Das macht die G20-Abnahme testbar (Phase 12 kann das Schema direkt abklopfen).
  (Vorschlag Gate G36.)

### V8. G21 (Export-Härtung): unzulässige Zeichen und Länge fehlen

G21 entschärft reservierte Gerätenamen, Punkte/Leerzeichen und Zeilenumbrüche, aber
nicht die unter Windows verbotenen Dateinamenszeichen `< > : " / \ | ? *` und nicht
die Länge. Wichtig, weil der Dateiname aus dem **Listennamen** entsteht und der ab
Phase 9 untrusted ist (Graph-Listenname). Ein Name wie `..\..\autostart\x` darf den
Save-Dialog-Vorschlag nicht in fremde Ordner lenken. **Patch:** die neun Zeichen
plus `..`-Sequenzen durch `_` ersetzen, Ergebnis auf ~120 Zeichen kürzen, erst danach
die bestehende Gerätenamen-Prüfung anwenden. (In `export_list` zentral, gilt dann
für md/txt/json gleichermassen.)

### V9. G23 (Clipboard): Panic muss das Clipboard sofort leeren

Der 60-Sekunden-Auto-Clear ist gut, aber `panic()` lässt einen bis zu 60 s alten
Task-Text im Clipboard zurück, während die App längst gesperrt ist. **Patch:** in die
Panic-/Lock-Sequenz (S5) aufnehmen: Clipboard leeren, sofern es noch den eigenen
Inhalt trägt (die Prüf-Logik existiert für den Timer bereits).

### V10. G8 (Passphrase-Stärke): Politik konkretisieren, Unlock-Kosten bedenken

"Erzwungene Passphrase-Stärke" braucht eine Definition, sonst wird es eine
Kompositionsregel ("1 Grossbuchstabe, 1 Zahl"), die nachweislich schwache Passwörter
produziert. **Patch:** Mindestlänge 12 (Empfehlung 4+ Wörter), Stärkeschätzer statt
Zeichenklassen-Regeln, Blockliste der 10k häufigsten Passwörter; keine maximale Länge.
Zusätzlich dokumentieren: Argon2id mit 256-512 MB heisst bei Auto-Lock (15 min) viele
Entsperrungen pro Tag mit je 1-3 s und RAM-Spitze; das ist der Preis des Designs und
gewollt (N4-Spinner), aber der Plan sollte festhalten, dass die Kosten NICHT über
schwächere Parameter, sondern höchstens über einen längeren Auto-Lock-Timeout
justiert werden dürfen.

### V11. G10 (Fehler ohne Geheimnisse): auf alle Methoden ausweiten, heute schon relevant

G10 gilt laut Plan nur für Auth-/Sync-Methoden. Der Decorator gibt aber für **alle**
Methoden `str(exc)` ans Frontend (`api.py:32`), und schon eine banale `sqlite3`- oder
`OSError`-Exception enthält absolute Pfade (Benutzername im Profilpfad). Auch die
`not_found`-Meldung echot die übergebene ID zurück. **Patch:** generischer Fehlercode
für alle Methoden als Default (`{"error": "internal"}` ohne Message oder mit
statischem Text), Details in den Ringpuffer aus S6/G33. Das ist eine Fünf-Zeilen-
Änderung und kann sofort passieren, zusammen mit G22.

---

## TEIL 4: Bisher nicht abgedeckte Angriffsvektoren

### A1. ID-Spoofing über den Sync: Cloud-Daten können lokale Aufgaben überschreiben und Invarianten brechen

**Szenario:** IDs importierter Objekte kommen wörtlich aus der Graph-Antwort und werden
Primärschlüssel (B.1, Phase 9 "Upsert nach stabiler Graph-id"). Lokale IDs sind
`t`/`l` + UUID. Ein Angreifer mit Kontrolle über das Microsoft-Konto oder die
Antwortdaten (kompromittiertes Konto ist laut B.9 ausdrücklich Teil des Modells) kann
Tasks mit **frei gewählter ID** liefern, z.B. `t<uuid-einer-lokalen-Aufgabe>`:

- Der Upsert schreibt dann per `UPDATE ... WHERE id = ?` in eine **lokale** Zeile und
  überschreibt sie mit Cloud-Inhalt. Das bricht die härteste Zusage des Plans
  ("Lokale Aufgaben werden **nie** angefasst", A.1, B.9, D.1) still und dauerhaft.
- Alle Codepfade, die vom ID-Präfix auf die Herkunft schliessen, werden unzuverlässig.
  Das betrifft konkret **G24**: Die Migrations-Heuristik "synced=1 UND ID beginnt mit
  `l`" ist nur beim allerersten Sign-in sicher (dann existieren nur Seeds); läuft sie
  je erneut (erneutes Sign-in nach Sign-out, Reparatur-Lauf), stuft sie echte
  Graph-Listen, deren Base64-ID zufällig oder absichtlich mit `l` beginnt, auf
  `local` um ("Geister-Divergenz").

**Patch (Vorschlag Gate G29):**
1. Importierte IDs beim Schreiben **namespacen**: gespeicherte ID = `g:` + Graph-ID
   (oder eigene Spalte `graph_id` mit UNIQUE-Index und lokal generiertem
   Primärschlüssel). Kollisionn mit `t`/`l`-Präfixen ist damit strukturell unmöglich.
2. Upsert zusätzlich absichern: `UPDATE ... WHERE id = ? AND source = 'graph'`
   (Defense-in-Depth, falls das Namespacing je umgangen wird).
3. Importierte IDs validieren (Länge begrenzen, Zeichensatz auf Base64/URL-Zeichen
   einschränken), bevor sie in DB und DOM (`data-id`) gelangen.
4. G24 robust machen: Seed-Listen beim Seeden explizit markieren (Settings-Key
   `seedListIds` oder Spalte `seed=1`) und die Migration an dieser Markierung
   festmachen statt am ID-Präfix; Migration idempotent formulieren.

### A2. Windows-Benachrichtigungen exfiltrieren Task-Inhalte an beiden Verschlüsselungsschichten vorbei

**Szenario:** Phase 10 sendet Toasts mit Task-Titeln ("Reminder: <Task-Text>").
Windows persistiert Toast-Inhalte in der Benachrichtigungs-Datenbank des Benutzers
(`wpndatabase.db` unter `%LOCALAPPDATA%`), im Klartext und ausserhalb jeder
App-Kontrolle; zusätzlich bleiben sie im Action Center sichtbar, auch wenn die App
längst gesperrt ist, und erscheinen je nach System auf gekoppelten Geräten
("Phone Link"). Damit landet genau der Inhalt, den die Doppel-Kaskade schützt, in
einer unverschlüsselten OS-Datenbank plus auf dem Sperrbildschirm. Der Plan behandelt
Toast-**Design** (Phase 10 Punkt 6), aber nicht Toast-**Inhalt** als Datenleck.

**Patch (Vorschlag Gate G32):**
1. Default: Windows-Toasts inhaltsarm ("A task is due", Listen-/Taskname NUR in der
   In-App-Pille, die unter der Sperre steht). Voller Text im Toast als bewusste
   Opt-in-Einstellung mit einem Satz Erklärung des Risikos.
2. Bei `lock()`/`panic()` keine weiteren Toasts erzeugen (Prüfung im Backend, analog
   zur bestehenden Kanal-Logik aus Phase 10 Punkt 4).
3. Im Bedrohungsmodell (S4/G28) ehrlich vermerken: bereits gezeigte Toasts liegen
   in der OS-Notification-DB; das ist mit winotify nicht rückholbar.

### A3. RAM-Inhalte erreichen die Platte: Pagefile, Ruhezustand, Crash-Dumps

**Szenario:** Mit G6 ist die entsperrte DB "nur im RAM". Windows schreibt RAM aber
auf die Platte: (a) `pagefile.sys` beim Auslagern, (b) `hiberfil.sys` beim Ruhezustand
(kompletter RAM-Abzug inkl. Schlüsseln und Klartext-DB), (c) WER-Minidumps bei einem
Python-Prozess-Crash (der Plan erwähnt nur WebView2-Crashdumps in G14). Ein Offline-
Angreifer mit der Platte liest daraus Schlüssel und Inhalte, ohne die Kaskade je
anzufassen. G25 (Nullen) verkürzt nur das Zeitfenster.

**Patch (Vorschlag Gate G31):**
1. **Ehrlichkeit zuerst:** ins Bedrohungsmodell und in die Doku: ohne BitLocker
   (bzw. Geräteverschlüsselung) gibt es dieses Leck prinzipbedingt; BitLocker als
   empfohlene Voraussetzung nennen (Status-Modal könnte den BitLocker-Status des
   Systemlaufwerks anzeigen, das ist eine WMI-Abfrage).
2. Schlüsselmaterial (die G25-`bytearray`s) zusätzlich per `VirtualLock` gegen
   Auslagern sperren (ctypes, Best-Effort, dokumentiert als solches).
3. WER-Dumps für den eigenen Prozess unterbinden oder minimieren
   (`SetErrorMode`/`WerAddExcludedApplication`, Best-Effort ohne Adminrechte), und
   in Phase 12 prüfen, dass `faulthandler`/Tracebacks keine Inhalte in Dateien
   schreiben.

### A4. `tasks.db.enc` in Cloud-/Sync-Ordnern: Versionshistorie und Metadaten

**Szenario:** B.7 nennt "Cloud-Ordner" als geschütztes Szenario, G17 schreibt die
Datei aber alle ~3 s neu. Liegt `data/` in OneDrive/Dropbox (bei `Dokumente`-
Umleitung schnell passiert), entstehen serverseitig hunderte Versionen pro Tag:
(a) Jede Version bleibt beim Anbieter wiederherstellbar, gelöschte Aufgaben leben
dort in alten Blobs weiter (der Nutzer kann sie nicht löschen), (b) die
Änderungsfrequenz ist ein präzises Nutzungsprofil, (c) die Dateigrösse verrät
Datenwachstum. Verschlüsselt bleibt alles, aber Retention und Metadaten widersprechen
dem "local-first, nichts verlässt den Rechner"-Versprechen.

**Patch (Vorschlag Gate G38):** Ablageort der DB von `Code/data/` (bzw. dem
Installationsordner) nach `%LOCALAPPDATA%\NoaToDo\` verlegen (dort synchronisiert
kein Standard-Cloud-Client); beim Start prüfen, ob der DB-Pfad unter einem bekannten
Sync-Wurzelpfad liegt (OneDrive-Env-Vars, Dropbox-`info.json`) und dann eine einmalige
Warnung zeigen. Im Bedrohungsmodell den Punkt "bewusstes Cloud-Backup der .enc ist
okay, Live-Sync des Arbeitsverzeichnisses nicht" festhalten.

### A5. Unvalidierte Graph-Felder jenseits von Text: `due_at`, Zeitstempel, Strukturfelder

**Szenario:** Regel 4/G3 validieren Länge und Steuerzeichen von **Strings**. Der Sync
übernimmt aber auch strukturierte Felder: Fälligkeiten (`dueDateTime`), Status,
Zeitstempel, Etags. Ein bösartiges Konto liefert kaputte oder extreme Werte
(Jahr 99999, kein ISO-Format, 10-KB-Etag). Folgen: Crash-Schleife im Sync (DoS,
die App synct nie wieder, weil derselbe Datensatz jedes Mal crasht), kaputte
Fälligkeitslogik in Phase 10 (Erinnerungs-Thread wirft bei jedem Tick), aufgeblähte
DB über Nicht-Text-Felder, die kein Längenlimit haben.

**Patch:** G3 erweitern: pro importiertem Feld ein Schema (Datum: striktes
ISO-8601-Parsing mit Bereichsprüfung, sonst Feld verwerfen und Task ohne Fälligkeit
importieren; Etag/IDs: Maxlänge; unbekannte Felder ignorieren). Grundsatz in B.9
aufnehmen: **ein** defekter Datensatz wird geloggt und übersprungen, er darf nie den
Gesamt-Sync oder den App-Start verhindern.

### A6. WebView2-Komfortfunktionen als Datenabfluss: Autofill, Passwort-Speichern, Rechtschreibprüfung

**Szenario:** Der Lock-Screen (N4) ist ein HTML-Passwortfeld in einem Chromium.
WebView2 bringt Browser-Komfort mit: Passwort-Speichern-Prompt, Autofill-Speicher,
Rechtschreibprüfung. Im schlimmsten Fall bietet die Runtime an, die **Passphrase zu
speichern** (landet dann im WebView2-Profil auf der Platte, per DPAPI des Benutzers
lesbar), oder Task-Eingaben wandern in Autofill-/Wörterbuch-Daten im Profilordner,
den G14 erst bei lock/panic wischt.

**Patch (Teil von Vorschlag Gate G40):** In Phase 11 beim Fensterstart die
WebView2-Settings hart setzen, soweit über pywebview/CoreWebView2 erreichbar:
`IsPasswordAutosaveEnabled=false`, `IsGeneralAutofillEnabled=false`; im Markup
zusätzlich `autocomplete="off"`, `spellcheck="false"`, `autocapitalize="off"` auf
Passphrase- und Task-Eingaben. In der G14-Abnahme verankern: nach einer Sitzung mit
Eingaben darf der Profilordner keine Autofill-/Passwortdaten enthalten.

### A7. Debug-Schalter und DevTools im Release-Build

**Szenario:** `NOATODO_DEBUG=1` aktiviert DevTools (CLAUDE.md, "Running the app").
Wenn die verteilte `.exe` (Phase 12) dieselbe Env-Var respektiert, bekommt jeder mit
kurzem Zugriff auf den Rechner (oder eine neugierige zweite Person am selben Konto)
eine Konsole mit vollem `pywebview.api.*`-Zugriff auf die laufende, entsperrte App
und kann zudem am gesperrten Screen den Frontend-Zustand inspizieren. Es ist kein
Krypto-Bruch (gleiches Privileg wie der Benutzer), aber es hebelt G13-UI-Annahmen
und senkt die Hürde von "Malware schreiben" auf "Umgebungsvariable setzen".

**Patch (Teil von Vorschlag Gate G40):** In Phase 12 festschreiben: der Release-Build
ignoriert `NOATODO_DEBUG` (Build-Konstante statt Env-Var), DevTools sind hart aus
(`debug=False`, zusätzlich `AreDevToolsEnabled=false` in den CoreWebView2-Settings,
soweit erreichbar). Debug-Funktionalität existiert nur in Dev-Läufen aus dem
Quellbaum.

### A8. Integrität der App-Dateien: manipulierte `app.js` ist persistente Codeausführung im Tresor

**Szenario:** G27 signiert die `.exe`, aber die Frontend-Dateien (`index.html`,
`app.js`, `style.css`) liegen daneben (One-Folder-Build) oder werden zur Laufzeit
entpackt. Wer sie einmal schreiben kann (kurzer physischer Zugriff, ein anderes
Programm mit Benutzerrechten), besitzt dauerhaft die App: Das nächste `boot()` lädt
das manipulierte JS mit voller Bridge, das die Passphrase-Eingabe des Lock-Screens
mitlesen und Daten nach dem Entsperren abgreifen kann; die Signatur der `.exe`
bleibt dabei intakt. Das ist die Persistenz-Variante des "Malware als Benutzer"-
Angreifers und verdient eine bewusste Entscheidung statt Schweigen.

**Patch:** In G27 ergänzen: (a) Frontend-Assets in das signierte Binary einbetten
(PyInstaller-Bundle/Nuitka-Onefile und aus dem Speicher bzw. einem beim Start in ein
frisches Temp-Verzeichnis entpackten Pfad laden), oder (b) beim Start einen
Hash-Abgleich der Assets gegen eine im Binary eingebettete Manifest-Liste machen und
bei Abweichung mit klarer Meldung verweigern. Plus ehrliche Zeile im Bedrohungsmodell:
gegen einen Angreifer, der als derselbe Benutzer schreiben UND lesen kann, gibt es
keine vollständige Verteidigung (der kann auch Tastatur mitlesen); Ziel ist nur,
stille Persistenz zu erschweren und erkennbar zu machen.

### A9. Store-Python-Pfadumleitung unterläuft das G14-Wischen

**Szenario:** CLAUDE.md dokumentiert, dass `%LOCALAPPDATA%`-Schreibzugriffe der
Store-Python-Installation nach `...\Packages\PythonSoftwareFoundation...\LocalCache\
Local\NoaToDo\webview` umgeleitet werden. Der Bauplan (G14) kennt diese Umleitung
nicht. Zwei konkrete Löcher: (a) Ein externes Wisch-/Deinstallations-Werkzeug, das den
literalen Pfad `%LOCALAPPDATA%\NoaToDo` bereinigt, verfehlt die realen Daten;
(b) beim Umstieg auf die Phase-12-`.exe` (kein Store-Python, keine Umleitung) bleibt
der alte umgeleitete Profilordner mit allem Cache-Inhalt für immer liegen; niemand
wischt ihn je.

**Patch:** In G14 aufnehmen: das Wischen operiert immer auf dem **effektiven** Pfad
(in-process, wie CLAUDE.md beschreibt); Phase 12 bekommt einen Erststart-Migrations-
schritt, der bekannte Alt-Pfade (umgeleiteter Package-Pfad) einmalig entfernt; die
Deinstallations-/Reset-Doku nennt beide Pfade.

---

## TEIL 5: Vorgeschlagene neue Gates und Priorisierung

### Vorschlag neue Gates (Nummerierung schliesst an G27 an)

| Gate | Phase | Kurz | Quelle |
|---|---|---|---|
| G28 | Doku, vor 7 | Bedrohungsmodell-Abschnitt B.10: Angreiferklassen, was schützt (nicht), Voraussetzungen (BitLocker), Überversprechen von G18 präzisieren | S4, V4.3 |
| G29 | 9 (vor erstem Sync) | Graph-IDs namespacen (`g:`-Präfix oder eigene Spalte), Upsert auf `source='graph'` beschränken, ID-Validierung, G24 an expliziter Seed-Markierung statt ID-Präfix festmachen | A1 |
| G30 | 11 | `tasks.db.enc`-Header als AAD in ChaCha20-Poly1305 binden; `.tmp` vor `os.replace` verifizieren, `.bak` erst danach rotieren; Plattenplatz-Check | V3 |
| G31 | 11/12 | RAM-auf-Platte-Lecks: BitLocker-Empfehlung (+ Anzeige im Status-Modal), `VirtualLock` für Schlüssel-Puffer, WER-Dump-Minimierung, keine Traceback-Dateien | A3 |
| G32 | 10 | Toast-Inhalts-Minimierung: Default ohne Task-Text, Volltext nur als Opt-in; keine Toasts im gesperrten Zustand; wpndatabase-Leck im Bedrohungsmodell dokumentieren | A2 |
| G33 | 8 (vor erstem Netz-Feature) | Logging-Policy: nie Inhalte/Schlüssel/Tokens/Pfade; Release ohne persistentes Logfile (RAM-Ringpuffer im Status-Modal) | S6 |
| G34 | 11 | `change_passphrase(old, new)` + KDF-Parameter-Upgrade beim Entsperren + ehrliche Verlustregel im Onboarding | S7 |
| G35 | 8 | MSAL-Cache-Persistenz definieren: `msal-extensions` mit DPAPI-Datei ODER nur Refresh-Token in keyring; Klartext-Cache verboten (Credential-Blob-Limit 2560 Bytes beachten) | S8 |
| G36 | 7 | Deklaratives Parameter-Schema pro Bridge-Methode (Typen, Enums, Bereiche, `due_at`-ISO-Prüfung, Setting-**Werte**) am `@bridge`-Decorator | V7 |
| G37 | 11 (mit G19-Review) | Mutex auf `Global\NoaToDo-<UserSID>` umstellen (RDP/Fast-User-Switching-Fall) | V5 |
| G38 | 11/12 | DB nach `%LOCALAPPDATA%\NoaToDo\` verlegen; Warnung, wenn der DB-Pfad in einem Cloud-Sync-Wurzelverzeichnis liegt | A4 |
| G39 | 11 | Pepper-Recovery-Export passphrase-verschlüsselt statt Klartext; Setup-Hinweis "nicht neben die DB legen" | V4.2 |
| G40 | 11/12 | Release-Härtung WebView2: Password-Autosave/Autofill aus, `spellcheck=off` auf sensiblen Feldern, `NOATODO_DEBUG` im Release wirkungslos, DevTools hart aus | A6, A7 |

### Priorisierte Reihenfolge

**P0, Dokument-Hygiene vor dem nächsten Bauschritt (kostet einen Nachmittag, verhindert Fehlbauten):**
1. W4 fixen (G14-Zeile in B.9): höchstes Regression-Risiko, ein Satz.
2. W1/W2/W6 fixen (B.7 + Phase 11 + CLAUDE.md auf G15/G6-Stand bringen): sonst wird
   Phase 11 nach der falschen Hälfte des Plans gebaut.
3. S1/S2 einführen (eine normative Gate-Tabelle mit Status/Datum/Prüfweg).
4. W5, W7, W8, W11, S3 (Kleinkram in einem Rutsch).

**P1, sofort umsetzbare Code-Punkte, die der Plan selbst schon als "sofort" führt:**
5. G22 endlich umsetzen (Status-Modal ehrlich; Beleg für den Verzug: `app.js:531`).
6. V11/G10-Basisschutz für alle Methoden (`str(exc)` raus aus `api.py:32`).

**P2, vor Phase 9 (Untrusted-Kanal):**
7. G29/A1 (ID-Namespacing + G24-Robustheit): muss VOR dem ersten Sync entschieden
   sein, nachträgliche ID-Migration ist teuer.
8. V1 (G2-Präzisierung), A5 (Feld-Schema im Sync), G33 (Logging-Policy, vor Phase 8).
9. G35 (Token-Cache) und V2 als Teil der Phase-8-Abnahme.

**P3, in Phase 11 einarbeiten (jetzt nur in den Plan schreiben):**
10. W3 klären (Spike: deserialize-Support), dann B.7/G6/G7 konsistent machen.
11. G30, G31, G34, G37, G38, G39, G40, V4 (Pepper-Details), V6 (Allowlist),
    V9 (Panic-Clipboard), S5 (Sperr-Sequenz), V10 (Passphrase-Politik).

**P4, Phase 10/12:**
12. G32 (Toast-Inhalte) mit Phase 10; A8 (Asset-Integrität) und A9 (Alt-Pfad-Wisch)
    mit Phase 12 / G27.

---

## Schlussbemerkung

Die Gesamtqualität des Plans ist hoch: Gate-Denken, ehrliche Einordnungen (B.7,
G27/Kerckhoffs), dokumentierte Fehlentscheidungen (G26) und die Audit-Nachträge sind
deutlich besser als der Durchschnitt solcher Dokumente. Die Schwächen sind fast alle
vom selben Typ: **additive Nachträge ohne Konsolidierung** (Teil 1) und **fehlende
Querschnitts-Spezifikationen** (Bedrohungsmodell, Lebenszyklus, Logging, Recovery in
Teil 2). Die neuen Angriffsvektoren in Teil 4 entstehen überwiegend dort, wo Daten
die eigene Verschlüsselungsgrenze verlassen (OS-Benachrichtigungen, Pagefile,
Cloud-Ordner, Clipboard war schon erkannt) oder wo Fremddaten mehr dürfen als gedacht
(IDs als Primärschlüssel). Nichts davon erfordert einen Umbau des Designs; alles ist
mit gezielten Ergänzungen an den bestehenden Gates lösbar.
