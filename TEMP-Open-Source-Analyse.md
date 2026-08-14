# NoaToDo: Analyse vor dem Öffentlich-Stellen

> **Temporäre Datei.** Gehört nicht ins Projekt, lebt nur auf dem Branch
> `oupen-source-NoaToDo`. Vor dem Öffentlich-Stellen löschen oder den Branch verwerfen.
> Inhaltsgleich mit der Chat-Antwort.
>
> Stand: 2026-08-14. Grundlage: Vollprüfung des Repos (56 getrackte Dateien, 83 Commits,
> ~9.750 Zeilen Python, ~4.560 Zeilen Frontend) plus Abgleich mit dem bereits
> veröffentlichten Schwesterprojekt `noagnos3-create/silicant`.

---

## 0. Urteil in drei Sätzen

Der **Code** ist bereit: keine Geheimnisse in der Historie, keine Netzwerkaufrufe, keine
Telemetrie, englische UI, und das Bedrohungsmodell hat die Veröffentlichung sogar schon
vorweggenommen (Kerckhoffs, K5: "Wer den Code vollständig versteht, kommt an die Daten
kein Stück näher").

Das **Repo** ist nicht bereit: es gibt keine Lizenz, kein README, keine Font-Lizenz
(das ist der einzige echte Rechts-Blocker), und es liegen 2,2 MB interne Planung plus
eine 112 KB grosse KI-Arbeitsanweisung drin, die bei Silicant bewusst nicht öffentlich
wurden.

**Realistischer Aufwand:** 1 konzentrierter Abend für den Pflichtteil (Etappe 1 bis 3
unten), ein zweiter für Politur, CI und Release.

---

## 1. Befundlage: was ich geprüft habe

### 1.1 Die guten Nachrichten (verifiziert, nicht angenommen)

| Prüfung | Ergebnis |
|---|---|
| Geheimnisse in der Git-Historie | **Sauber.** Die gelöschten `backend/auth.py`, `graph_sync.py`, `notify.py` waren einzeilige Platzhalter-Docstrings. Keine Azure-Client-ID, kein Token, kein Schlüssel, nirgends in 83 Commits. |
| Netzwerkcode | **Keiner.** Kein `urllib`, `requests`, `httpx`, `socket`, `urlopen`. Nur `subprocess` für `netsh wlan` (WLAN-Stärke) und WMI (BitLocker-Status). Die Zusage "ruft nie nach Hause" ist von aussen nachprüfbar, und genau das ist ein Verkaufsargument. |
| Nutzer-Daten im Repo | **Keine.** `.gitignore` deckt `*.db`, `*.db.enc`, `*.db.enc.bak`, `Code/data/` ab. Kein Tresor, kein `config.json`, kein Build-Artefakt getrackt. |
| Sprache der Oberfläche | **Englisch**, durchgehend. Deutsch steckt ausschliesslich in Kommentaren und Docstrings. Genau **eine** Ausnahme, siehe Befund C2. |
| Persönliche Daten im Text | **Keine.** Der Bauplan enthält nichts Privates. Der einzige Rest ist ein Kommentar in `app.js:514`, der den gelöschten Fake-Namen "Noa Andersen" historisch erwähnt. |
| E-Mail in Commits | `noagnos3@gmail.com` in 78 von 83 Commits. **Kein neues Risiko:** dieselbe Adresse ist in der Historie von `silicant` schon öffentlich. Details unter B8. |
| Remote-Branches | Nur `main`. Die alten `phase-8`/`phase-9`-Branches sind weg. 9 geschlossene PRs werden mit öffentlich, inhaltlich harmlos. |
| Repo-Grösse | 2,5 MB `.git`. Kein History-Rewrite nötig, keine LFS-Frage. |

### 1.2 Die Silicant-Vorlage (dein eigener Weg von letztem Mal)

Ich habe `noagnos3-create/silicant` geklont und die Historie gelesen. Du hast das dort in
genau dieser Reihenfolge gemacht, und das ist eine brauchbare Schablone:

1. `Prepare for open source: remove personal name, ignore temp files`
2. `Remove CLAUDE.md from public repo, add to .gitignore`
3. `Move build files into build/ folder for better project structure`
4. `Add README with features, installation, usage, and screenshot placeholders`
5. `Improve README: better screenshot layout and complete Built with table`
6. `Remove em dashes from README, replace with commas and colons`
7. `Add GPLv3 license header to all Python files`
8. `Add empty LICENSE file for GPLv3` / `Include GPL v3 license in the project`
9. `Add CONTRIBUTING.md`
10. `Improve .gitignore coverage`
11. `Add GitHub PR template`
12. `Restructure project: move source files to src/, logo to assets/`

Daraus lese ich vier feste Konventionen von dir: **GPLv3**, **Copyright-Halter "Noa Gnos"**,
**CLAUDE.md bleibt privat**, **englisches README nach festem Aufbau**. Ich empfehle, alle
vier beizubehalten. Drei Dinge würde ich diesmal anders machen, siehe 5.3.

---

## 2. Lizenz

### 2.1 Empfehlung: GPL-3.0-or-later

**Begründung, in der Reihenfolge ihres Gewichts:**

1. **Konsistenz.** Silicant ist GPLv3. Zwei Projekte desselben Autors unter derselben
   Lizenz ergeben ein erkennbares Profil, und du musst die Abwägung nicht zweimal führen.
2. **Es passt zum Sicherheitsversprechen.** Der Kern der App ist "du kannst mir glauben,
   weil du nachsehen kannst". Copyleft heisst: **jede** weiterverteilte Abwandlung muss
   ebenfalls nachsehbar sein. Bei MIT dürfte jemand NoaToDo nehmen, eine Hintertür
   einbauen, es als "NoaToDo Pro" verkaufen und den Quelltext für sich behalten. Für eine
   Krypto-App ist das kein theoretisches Ärgernis, sondern das genaue Gegenteil dessen,
   was der Bauplan in B.10 verspricht.
3. **GPLv3 statt GPLv2** wegen der Tivoisierungs- und Patentklauseln und weil GPLv3
   ausdrücklich mit Apache-2.0-Code kompatibel ist (`cryptography` braucht das).
4. **"or later"** statt nur "3.0": kostet nichts und erspart dir eine Neulizenzierung,
   falls je eine GPLv4 kommt. Silicant sagt nur "GPLv3"; die Standard-Header-Formel dort
   enthält aber ohnehin schon "either version 3 of the License, or (at your option) any
   later version". Faktisch ist Silicant also bereits **-or-later**, nur der README-Satz
   sagt es nicht. Bei NoaToDo würde ich es sauber ausschreiben.

### 2.2 Die Alternativen, ehrlich gegeneinander

| Lizenz | Wofür sie hier spricht | Wogegen sie hier spricht | Urteil |
|---|---|---|---|
| **GPL-3.0-or-later** | Schützt die Prüfbarkeit; Konsistenz mit Silicant; Patentklausel; kompatibel mit allen Abhängigkeiten | Firmen meiden GPL-Code; keine proprietären Forks (das ist hier aber der Zweck) | **Empfehlung** |
| MIT | Maximale Verbreitung, kürzeste Datei, null Reibung | Erlaubt genau den geschlossenen Backdoor-Fork, gegen den die App argumentiert | Nein |
| Apache-2.0 | Wie MIT plus expliziter Patentgrant, gute Reputation | Gleiches Kernproblem wie MIT | Nein |
| AGPL-3.0 | Stärkstes Copyleft | Der Netzwerk-Paragraph greift bei einer Offline-Desktop-App **nie**. Schreckt ohne jeden Gegenwert ab. | Nein, wäre Etikettenschwindel |
| Quellcode sichtbar, aber unfrei ("source available", BSL) | Kontrolle über Kommerzialisierung | Wäre **kein** Open Source, und die Font-Lizenz OFL erlaubt Weiterverteilung ohnehin unter freien Bedingungen | Nein |

### 2.3 Kompatibilität der Abhängigkeiten mit GPLv3

Alle laufzeitrelevanten Pakete sind GPLv3-verträglich. Geprüft gegen
`requirements.lock.txt`:

| Paket | Lizenz | GPLv3-kompatibel |
|---|---|---|
| `pywebview` | BSD-3-Clause | ja |
| `bottle` (Transitiv von pywebview) | MIT | ja |
| `pythonnet`, `clr_loader` | MIT | ja |
| `sqlcipher3-wheels` | **zlib/libpng** (auf PyPI deklariert, von mir nachgeschlagen) | ja |
| SQLCipher selbst (im Wheel) | BSD-artig (Zetetic) | ja |
| `cryptography` | Apache-2.0 **oder** BSD-3 (Doppellizenz) | ja (GPLv3 ist mit Apache-2.0 einseitig kompatibel) |
| `argon2-cffi`, `argon2-cffi-bindings` | MIT | ja |
| `keyring`, `jaraco.*`, `more-itertools`, `zipp`, `importlib_metadata` | MIT | ja |
| `cffi`, `pycparser` | MIT / BSD | ja |
| `winrt-*` (PyWinRT) | MIT | ja |
| `pywin32-ctypes` | BSD-3 | ja |
| `pillow` | MIT-CMU | ja (nur Build-Werkzeug, siehe C3) |
| JetBrains Mono, Space Grotesk | **SIL OFL 1.1** | ja, **aber mit Pflichten**, siehe 2.4 |

**Ein Punkt zum Nachprüfen, nicht zum Verschweigen:** welche OpenSSL-Version im
`sqlcipher3-wheels`-Wheel steckt, sagt PyPI nicht. Relevant ist es nur historisch:
OpenSSL 1.x stand unter einer GPL-inkompatiblen Lizenz, OpenSSL ab 3.0 steht unter
Apache-2.0 und ist unproblematisch. Bei einem 2025er-Wheel ist 3.x praktisch sicher.
Trotzdem: einmal in der gebauten `.exe` mit `strings | findstr /i "OpenSSL"` nachsehen
und das Ergebnis in `THIRD-PARTY-NOTICES.md` schreiben. Falls es wider Erwarten 1.1.1
wäre, brauchtest du eine "OpenSSL linking exception" im LICENSE-Zusatz. Fünf Minuten
Arbeit, die dir eine unangenehme Issue erspart.

### 2.4 Die Schriften: der einzige echte Rechts-Blocker

`Code/frontend/fonts/` enthält **neun** `.woff2`-Dateien mit UUID-Namen wie
`9393c2fb-e5c4-4349-95a4-ca44f32ca4cb.woff2`. Ihre `unicode-range`-Blöcke in `style.css`
sind exakt das Google-Fonts-Subset-Schema (latin, latin-ext, cyrillic, cyrillic-ext,
greek, vietnamese). Es sind also Google-Fonts-Auslieferungen von **JetBrains Mono**
(6 Dateien) und **Space Grotesk** (3 Dateien), beide unter der **SIL Open Font License 1.1**.

Heute liegt **keine einzige Lizenzdatei und kein Copyright-Vermerk** dabei. Solange das
Repo privat ist, ist das folgenlos. Ab dem Klick auf "public" verteilst du fremde
Schriften ohne die von der OFL zwingend geforderten Vermerke weiter, und zwar doppelt:
im Repo **und** eingebacken in jede `NoaToDo.exe`.

**Was die OFL 1.1 konkret verlangt:**

- Die Schriftdateien dürfen weiterverteilt und gebündelt werden, auch kommerziell. Kein
  Problem also.
- **Der Lizenztext und der Copyright-Vermerk müssen mitgeliefert werden.** Das ist die
  Bedingung, die aktuell verletzt wäre.
- Ein "Reserved Font Name" darf nicht für abgewandelte Fassungen verwendet werden.
  Beide Familien haben keinen RFN, und du veränderst die Dateien nicht, also irrelevant.
  Die Subsets sind unveränderte Google-Ausschnitte, keine Modifikation im OFL-Sinn.
- Die Schriften dürfen **nicht** allein verkauft werden. Tust du nicht.

**Fix, drei Schritte:**

1. `Code/frontend/fonts/OFL.txt` anlegen (der Standard-OFL-1.1-Text) plus eine
   `Code/frontend/fonts/README.md` mit den zwei Copyright-Zeilen:
   `Copyright 2020 The JetBrains Mono Project Authors (https://github.com/JetBrains/JetBrainsMono)`
   und
   `Copyright 2021 The Space Grotesk Project Authors (https://github.com/floriankarsten/space-grotesk)`
2. **Die UUID-Namen umbenennen.** Nicht juristisch nötig, aber ein anonymer Hash-Name ist
   in einem OSS-Repo genau das Signal "hier wurde etwas irgendwo abgegriffen", das du
   nicht senden willst. Sprechend wäre
   `jetbrains-mono-400-latin.woff2`, `space-grotesk-500-latin.woff2` und so weiter.
   **Achtung, zwei Kopplungen:** die Pfade stehen in `style.css` (36 `@font-face`-Blöcke),
   und die Dateinamen fliessen über `integrity.build_manifest()` in das
   G27-Hash-Manifest ein. Umbenennen heisst also: CSS anpassen, danach neu bauen. Der
   Integritätscheck fällt im Quellbaum nicht auf (ohne Stempel ist er ein No-op), aber
   ein alter, danebenliegender `_buildstamp.py` würde die App nicht mehr starten lassen.
3. In `THIRD-PARTY-NOTICES.md` beide Schriften mit Lizenz und Quelle nennen.

### 2.5 Das UI-Konzept-HTML: eine Nebenfrage, die du kennen solltest

`Planung/weiteres/NoaToDo UI Konzept.html` ist 1,45 MB und erkennbar ein exportiertes
Claude-Artefakt (der Bundler-Vorspann und die Farbe `#d97757` verraten es). Es enthält
keine externen Referenzen, ist also technisch unbedenklich. Zwei Punkte:

- **Urheberrecht:** KI-Ausgaben, die du beauftragt und weiterverarbeitet hast, kannst du
  unter deine Lizenz stellen. Das ist gängige Praxis und für ein Designkonzept
  unkritisch. Kein Blocker.
- **Praktisch** ist die Datei aber der Grund, warum GitHub dein Repo heute als **"HTML"**
  einstuft (verifiziert über die API: `"language": "HTML"`). Ein Python-Projekt, das sich
  als HTML-Projekt ausgibt, taucht in keiner Python-Suche auf. Fix unter B6.

### 2.6 Copyright-Halter

Silicant nutzt `Copyright (C) 2026 Noa Gnos`. Bleib dabei, dann ist die Zuordnung über
beide Projekte eindeutig. Wenn du deinen Klarnamen bewusst nicht mehr nennen willst,
wäre `Copyright (C) 2026 NoaGnos` (der GitHub-Handle) die Alternative, aber dann bitte
konsistent, nicht in einem Projekt so und im anderen anders. Wichtig ist nur, dass
**ein** benennbarer Rechteinhaber dasteht: "NoaToDo Contributors" allein ist bei einem
Ein-Personen-Projekt schwach, weil es niemanden benennt, der die Lizenz durchsetzen kann.

---

## 3. Blocker: das muss vor dem Klick auf "Public" erledigt sein

Absteigend nach Dringlichkeit. B1 bis B5 sind Pflicht, B6 bis B9 stark empfohlen.

### B1. LICENSE-Datei fehlt

Ohne Lizenzdatei ist der veröffentlichte Code **"all rights reserved"**. Niemand darf ihn
legal benutzen, forken oder beitragen, egal was das README behauptet. GitHub zeigt dann
auch keinen Lizenz-Badge.

**Fix:** Volltext der GPL-3.0 nach `LICENSE` (Root). Bei Silicant hast du das in zwei
Commits gemacht ("Add empty LICENSE file", dann "Include GPL v3 license"); diesmal reicht
einer.

### B2. Lizenz-Header in den Quelldateien fehlen

Die GPL empfiehlt sie ausdrücklich, und du hast es bei Silicant so gemacht. Betroffen:
19 Python-Dateien plus `app.js`, `style.css`, `index.html`.

**Zwei Fallen, die du bei Silicant hattest und hier vermeiden solltest:**

- In `silicant/src/main.py` steht der Header als `"""# Silicant ... """` **vor** dem
  eigentlichen Modul-Docstring. Damit ist der Lizenztext der Docstring geworden und die
  echte Moduldoku ein toter String-Ausdruck. Bei NoaToDo wäre das schlimmer, weil die
  Moduldocstrings hier die eigentliche Dokumentation sind.
  **Richtig:** Header als `#`-Kommentarblock **über** dem Docstring.
- `optimize=2` im Release strippt Docstrings, Kommentare sind ohnehin nicht im Bytecode.
  Ein Kommentar-Header kostet also im Bundle nichts.

Kurzform genügt (der GPL-Standardblock), verweisend auf LICENSE:

```python
# NoaToDo, local encrypted to-do app for Windows.
# Copyright (C) 2026 Noa Gnos
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Eigentlicher Modul-Docstring bleibt hier stehen."""
```

**Zwei Kopplungen beachten:** `Code/frontend/*` wird von G27 gehasht (Header setzen,
**dann** bauen), und `tests/test_release.py` prüft per Tokenizer auf verbotene Muster,
ignoriert Kommentare aber korrekt. Kein Testbruch zu erwarten, einmal `pytest` laufen
lassen reicht.

### B3. Font-Lizenz fehlt

Siehe 2.4. Das ist der einzige Punkt, bei dem "public schalten" ohne Fix eine echte
Lizenzverletzung ist.

### B4. README fehlt vollständig

Ein Repo ohne README ist auf GitHub praktisch unsichtbar und wirkt verwahrlost. Der
komplette Entwurf steht in Abschnitt 5.

### B5. Entscheidung CLAUDE.md und Planung/

Beides steht heute im Repo und würde mit veröffentlicht: **112 KB** interne
KI-Arbeitsanweisung plus **2,2 MB** Planung (davon 414 KB Bauplan). Bei Silicant hast du
CLAUDE.md bewusst entfernt und in `.gitignore` gesetzt. Ausführliche Abwägung mit drei
Optionen in Abschnitt 7.

### B6. `.gitattributes` fehlt, GitHub hält das Projekt für HTML

Verifiziert: `"language": "HTML"`. Ursache ist die 1,45-MB-Konzeptdatei plus die
Frontend-Dateien.

**Fix:** `.gitattributes` im Root:

```gitattributes
# Sprachstatistik: Planung ist Dokumentation, kein Quelltext.
Planung/** linguist-documentation
docs/** linguist-documentation
# Mitgelieferte Schriften zählen nicht als eigener Code.
Code/frontend/fonts/** linguist-vendored
# Zeilenenden: die Windows-Skripte brauchen CRLF, der Rest bleibt LF.
* text=auto eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
*.woff2 binary
*.ico binary
*.png binary
*.jpeg binary
```

Der `eol`-Teil ist kein Kosmetikpunkt: `build.bat` mit LF-Zeilenenden verhält sich unter
`cmd.exe` unzuverlässig, und das trifft genau die Leute, die dein Projekt zum ersten Mal
bauen.

### B7. Repo-Metadaten sind auf "privat" eingestellt

Aktueller Stand (API): Beschreibung **"lokale, private ToDo App"** (deutsch, und das Wort
"private" wird im OSS-Kontext als "geschlossen" missverstanden), **keine Topics**, keine
Website, Discussions aus.

**Fix vor dem Umschalten:**

- Beschreibung, englisch, präzise:
  `Local, encrypted to-do app for Windows. Dual-layer encryption, no cloud, no telemetry.`
- Topics: `windows`, `python`, `pywebview`, `webview2`, `sqlcipher`, `encryption`,
  `argon2`, `chacha20-poly1305`, `privacy`, `local-first`, `todo-app`, `desktop-app`
- Discussions einschalten (dann landen "wie mache ich X"-Fragen nicht als Issues)
- Wiki aus lassen (die Doku liegt im Repo)
- "Require contributors to sign off on web-based commits" ist optional, kann aus bleiben

### B8. E-Mail-Adresse in der Commit-Historie

`noagnos3@gmail.com` steht in 78 Commits und wird mit öffentlich. **Wichtig für die
richtige Einordnung:** Dieselbe Adresse ist in der öffentlichen Silicant-Historie bereits
sichtbar. Es entsteht also **keine neue** Offenlegung. Deshalb ist das hier eine Notiz,
kein Blocker.

Wenn du es trotzdem sauber willst, hast du drei Wege, absteigend nach Empfehlung:

1. **Nichts tun**, aber für die Zukunft in den GitHub-Einstellungen "Keep my email
   address private" plus "Block command line pushes that expose my email" aktivieren und
   lokal `git config user.email <ID>+noagnos3-create@users.noreply.github.com` setzen.
   Wirkt ab dem nächsten Commit.
2. History-Rewrite über `git filter-repo --mailmap`. Bei 83 Commits ohne Forks und ohne
   Klone technisch risikoarm, aber **alle Commit-Hashes ändern sich**, die geschlossenen
   PRs zeigen dann auf verwaiste SHAs, und `build_exe.py` schreibt den Commit-Hash in den
   Build-Stempel. Aufwand steht in keinem Verhältnis, weil die Adresse ohnehin schon
   draussen ist.
3. Frisches Repo mit einem einzigen Squash-Commit. Wirft die gesamte Entwicklungsgeschichte
   weg. **Klar dagegen:** die Historie ist bei diesem Projekt ein Aktivposten. 83 Commits,
   die Phase für Phase eine sicherheitskritische App aufbauen, sind genau das, was einem
   Prüfer Vertrauen gibt.

### B9. `SECURITY.md` fehlt

Bei einer normalen App wäre das Politur. Bei einer App, deren Hauptversprechen
Verschlüsselung ist, ist es Pflicht **vor** dem Öffnen, nicht danach. Sonst kommt der
erste Sicherheitsbefund als öffentliches Issue statt privat. Inhalt in 6.3.

---

## 4. Dateistruktur

### 4.1 Ist-Zustand und was daran stört

```
NoaToDo/
├── .gitignore
├── CLAUDE.md                 112 KB, interne KI-Anweisung
├── Code/                     die eigentliche App
│   ├── main.py  buildinfo.py  integrity.py  lockwindow.py  wintheme.py
│   ├── NoaToDo.spec  build.bat  run.ps1  pytest.ini
│   ├── requirements*.txt (4 Stück)
│   ├── backend/  frontend/  tests/  tools/
└── Planung/                  2,2 MB
    ├── Bauplan - NoaToDo.md          414 KB
    ├── Umbauplan - Struktur ....md    46 KB
    ├── tools/verify_umbau.py
    └── weiteres/  (UI-Konzept 1,45 MB, Logo, Skizze, 2 Dokumente)
```

Fünf Dinge stören einen Erstbesucher:

1. **`Code/` als Ordnername.** Kein Ökosystem kennt das. Bei Python erwartet man `src/`
   oder das Paket direkt im Root. Du selbst hast Silicant am Ende genau dahin
   umgebaut ("move source files to src/").
2. **Deutsche Ordnernamen** (`Planung/`, `weiteres/`) in einem sonst englischen Projekt.
3. **Vier `requirements`-Dateien** ohne erklärenden Hinweis: `requirements.txt` (lose),
   `requirements.lock.txt` (gepinnt), `requirements.lock.hashes.txt` (gepinnt mit Hashes),
   `requirements-dev.txt`. Das ist gut durchdacht, sieht aber ohne Erklärung nach Chaos aus.
4. **Kein `docs/`**, obwohl es Screenshots braucht.
5. **Kein `assets/`**, obwohl es ein Logo gibt (das heute in `Planung/weiteres/` liegt und
   deshalb ein Build-Werkzeug zerbricht, siehe C1).

### 4.2 Zielstruktur

Ich empfehle **Variante A** (konventionell). Variante B steht darunter, falls dir der
Umbau zu teuer ist.

**Variante A, konventionell (empfohlen):**

```
NoaToDo/
├── README.md
├── LICENSE                       GPL-3.0 Volltext
├── SECURITY.md                   Meldeweg, Threat-Model-Kurzfassung, ehrliche Grenzen
├── CONTRIBUTING.md               inkl. Sprachregel und Bauplan-Hinweis
├── CHANGELOG.md                  1.0.0
├── THIRD-PARTY-NOTICES.md        Abhängigkeiten + Schriften mit Lizenzen
├── .gitignore
├── .gitattributes                NEU, siehe B6
├── .github/
│   ├── workflows/ci.yml          pytest auf windows-latest
│   ├── workflows/release.yml     optional: .exe bauen und an das Release hängen
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.yml
│       ├── feature_request.yml
│       └── config.yml            Sicherheitslücken -> SECURITY.md, keine Issues
├── assets/
│   └── noatodo-logo.png          aus Planung/weiteres/ hierher
├── docs/
│   ├── screenshot-*.png          4 bis 6 Stück
│   ├── architecture.md           die englische Kurzfassung der Architektur
│   └── threat-model.md           übersetzte Kurzfassung von Bauplan B.10
└── src/
    ├── main.py  buildinfo.py  integrity.py  lockwindow.py  wintheme.py
    ├── NoaToDo.spec  pytest.ini
    ├── requirements.txt  requirements.lock.txt
    ├── requirements.lock.hashes.txt  requirements-dev.txt
    ├── backend/   api.py config.py db.py ostheme.py radio.py security.py
    ├── frontend/  index.html app.js style.css icon.ico fonts/ (+ OFL.txt)
    ├── tests/
    ├── tools/     build_exe.py lock_hashes.py make_icon.py verify_crypto.py
    └── build/     build.bat run.ps1
```

**Variante B, minimal-invasiv:** `Code/` bleibt wie es ist, es kommen nur die neuen
Root-Dateien und `docs/` plus `assets/` dazu. Kostet fast nichts, sieht aber weiter
ungewöhnlich aus.

### 4.3 Was der Umbau wirklich kostet

Ehrlich: **`Code/` nach `src/` umzubenennen ist nicht billig.** Die Zeichenkette `Code/`
steht nicht nur in Pfaden, sondern in der Prosa von CLAUDE.md und des Bauplans, und
CLAUDE.md verlangt selbst, dass Plan und Code nie auseinanderlaufen. Konkret betroffen:

| Ort | Was |
|---|---|
| `Code/tools/build_exe.py` | `HERE`/`CODE`-Ableitung ist relativ, funktioniert weiter; die Doku-Strings nennen `Code/` |
| `Code/NoaToDo.spec` | relativ zu `HERE`, funktioniert weiter |
| `Code/tools/make_icon.py` | zeigt auf `../../Planung/NoaToDo Logo.png`, **ist schon heute kaputt**, siehe C1 |
| `Code/tests/conftest.py` | leitet `CODE` aus `__file__` ab, funktioniert weiter |
| `Code/pytest.ini` | `testpaths`, relativ, funktioniert weiter |
| `Planung/tools/verify_umbau.py` | prüft die Bauplan-Struktur, ggf. Pfadanpassung |
| `CLAUDE.md` | dutzende Nennungen von `Code/...` |
| `Planung/Bauplan - NoaToDo.md` | Projektstruktur-Abschnitt und Phasenbeschreibungen |
| `build.bat`, `run.ps1` | nutzen `%~dp0` bzw. `$MyInvocation`, funktionieren weiter |

Der **Code** übersteht den Umzug also fast von selbst (alle Pfade sind relativ, das ist
gut gemacht), die **Dokumentation** nicht. Plane dafür einen eigenen Commit ein, nicht
einen Nebeneffekt.

Wenn du dich für den Umbau entscheidest, mit `git mv` arbeiten, damit die Historie
zusammenhängend bleibt:

```bash
git mv Code src
git mv "Planung/weiteres/NoaToDo Logo.png" assets/noatodo-logo.png
mkdir -p src/build && git mv src/build.bat src/run.ps1 src/build/
# danach: make_icon.py auf assets/ zeigen lassen, Doku nachziehen
```

Ein Detail, das man leicht übersieht: **`src/build/` kollidiert mit dem
PyInstaller-Arbeitsordner**, den `.gitignore` als `Code/build/` führt. Wenn du
Skripte nach `build/` legst, muss die Ignore-Regel von `Code/build/` auf
`src/build/version_info.txt` verengt werden, sonst ignoriert git deine eigenen
Build-Skripte. Silicant hatte exakt dieses Problem, siehe der Commit
"Remove build/ from .gitignore". **Sauberer:** PyInstaller in `src/.pyi-build/`
arbeiten lassen und `build/` für die Skripte freihalten.

---

## 5. Das README

### 5.1 Aufbau

Silicants Muster funktioniert und sollte die Grundlage sein. NoaToDo braucht zwei
Abschnitte zusätzlich, die Silicant nicht braucht: **Security model** und
**Data and files**. Bei einer Krypto-App ist genau das der Teil, den Leute zuerst lesen.

1. Titel + Logo
2. Tagline (ein fetter Satz)
3. Screenshots (Tabelle, 4 bis 6 Bilder)
4. Features (nach Themen gruppiert)
5. **Security model** (neu, siehe 5.2, das ist dein Alleinstellungsmerkmal)
6. **What NoaToDo deliberately does not do** (neu)
7. System requirements
8. Installation (aus dem Quelltext + eigene `.exe` bauen + fertige `.exe`)
9. Usage inkl. Keyboard-Shortcut-Tabelle (die hast du schon, B.5)
10. **Where your data lives** (neu: Tresorpfad, config.json, Credential Manager, Profil)
11. Built with (Tabelle mit Version und Zweck)
12. Project layout
13. Development (Tests, Build)
14. Contributing (Verweis)
15. License

### 5.2 Entwurf der drei neuen, wichtigen Abschnitte

Diese schreibe ich aus, weil sie den Unterschied machen. Der Rest ist Fleissarbeit nach
Silicant-Muster.

```markdown
## Security model

NoaToDo stores everything in a single encrypted vault file (`tasks.db.enc`) at a location
you choose. There is no server, no account, no sync and no telemetry. The app makes no
outbound network connections of any kind, which you can verify: there is no HTTP client
in the codebase.

### Encryption

| Layer | What |
|:--|:--|
| Outer | ChaCha20-Poly1305 (AEAD). The full file header is authenticated as associated data. |
| Inner | SQLCipher / AES-256. The decrypted image is itself an encrypted database. |
| Key derivation | Argon2id (256 MiB, t=3, p=4, 16-byte per-vault salt) |
| Second factor | A random 32-byte pepper in the Windows Credential Manager (DPAPI), bound in before Argon2id via `HKDF-Extract(salt=pepper, ikm=passphrase)` |
| Domain separation | HKDF-SHA256 with two fixed labels derives the AES and ChaCha keys separately, never raw slices of one secret |

No passphrase and no verification hash is ever written to disk. An unlock is verified
implicitly by the AEAD tag, so the vault file offers an attacker no oracle.

While unlocked, the working copy is itself a SQLCipher-encrypted file, never plaintext.
Keys live only in RAM, are `VirtualLock`ed after derivation and zeroed on every exit path.

### Honest limits

This section is deliberately as prominent as the one above.

- **The vault is bound to this Windows account.** The pepper lives in the Credential
  Manager. Another PC or a fresh Windows profile means the data is gone, even with the
  correct passphrase. There is no recovery, no backdoor key and no support path.
- **The pepper defeats an offline attack only as long as** the attacker has the vault
  file alone, or the disk is encrypted with BitLocker. Whoever has the whole unencrypted
  disk can attack the DPAPI master key, whose strength then rests on your Windows
  password.
- **BitLocker or Windows device encryption is effectively a prerequisite.** NoaToDo
  cannot reach the pagefile, the hibernation file or crash dumps. The app shows your real
  BitLocker status in the status dialog, and says "unknown" when it cannot read it rather
  than claiming anything.
- **Malware running in your own Windows account is an explicit non-goal.** Anything
  running as you can read the pepper, hook the keyboard and read unlocked process memory.
  Hardening (CSP, backend-enforced lock allowlist, frontend hash manifest, no DevTools in
  release) raises the bar and prevents silent persistence. It is never sold as protection
  against this class.
- **This release is not code-signed.** Windows SmartScreen will warn on first run, and a
  tampered binary cannot be detected by signature. Verify the SHA-256 checksum published
  with each release, or build it yourself.
- **The rate limit ladder slows a person at your keyboard, nothing else.** Anyone who can
  copy the vault file guesses offline, where no ladder exists.
- **Exports write plaintext files.** That is the point of an export. Once saved, the file
  is outside the vault and outside this model.

The full threat model, including the six attacker classes it is written against, is in
[docs/threat-model.md](docs/threat-model.md).

## What NoaToDo deliberately does not do

- No cloud, no sync, no account, no telemetry, no update check over the network.
- No notifications of any kind.
- No full-text search, no due dates, no reminders, no recurring tasks.
- No plausible deniability and no hidden second vault.
- No screenshot protection. It was built, it broke rendering on some GPUs, and it never
  defended against the real threat (a phone camera). It will not come back.
- No auto-update. The status dialog names the source URL, you check yourself.

## Where your data lives

| What | Where | Encrypted |
|:--|:--|:--|
| Your tasks | `tasks.db.enc` at the folder you pick during setup | yes, both layers |
| Crash backup | `tasks.db.enc.bak` next to it | yes |
| Vault path, auto-lock timer, unlock rate-limit state | `%LOCALAPPDATA%\NoaToDo\config.json` | no, contains no task data |
| Key pepper | Windows Credential Manager | DPAPI, per Windows account |
| Working copy while unlocked | `%LOCALAPPDATA%\NoaToDo\work\` | yes (SQLCipher), securely deleted on lock |
| WebView2 cache | `%LOCALAPPDATA%\NoaToDo\webview` | no, wiped after every window teardown, holds only the app's own HTML/CSS/JS |

Uninstalling means deleting the vault file, the `%LOCALAPPDATA%\NoaToDo` folder and the
`NoaToDo` entry in the Windows Credential Manager.
```

### 5.3 Drei Fehler aus dem Silicant-README, die du nicht wiederholen solltest

1. **Die `<!-- TODO: Replace this placeholder -->`-Kommentare stehen heute noch im
   öffentlichen Silicant-README** (Zeilen 3, 6, 11 bis 16). Das ist das Erste, was ein
   aufmerksamer Leser sieht. Vor dem Öffnen einmal nach `TODO` greppen.
2. **Der "Project layout"-Abschnitt stimmt nicht mehr.** Er zeigt `main.py` im Root, seit
   dem Umbau liegt alles in `src/`. Wenn du bei NoaToDo umbaust: README **nach** dem
   Umbau schreiben, nicht davor.
3. **Sprachmischung:** Im englischen README steht bei den Einstellungen "Beenden". Bei
   NoaToDo ist die UI durchgehend englisch, das kann dir also nur bei der einen deutschen
   Fallback-Meldung passieren, siehe C2.

Und eine vierte Sache, die bei NoaToDo speziell ist: **keine Geviert- und Halbgeviert-
striche im README.** Bei Silicant brauchte es dafür einen eigenen Nachbesserungs-Commit
("Remove em dashes from README"). Hier gilt die Regel projektweit, also gleich richtig
schreiben.

---

## 6. Was noch rein muss (neue Dateien)

| Datei | Priorität | Zweck / Inhalt |
|---|---|---|
| `LICENSE` | **Pflicht** | GPL-3.0 Volltext |
| `README.md` | **Pflicht** | siehe 5 |
| `Code/frontend/fonts/OFL.txt` + Copyright-Notiz | **Pflicht** | OFL-1.1 Auflage |
| `SECURITY.md` | **Pflicht** | siehe 6.3 |
| `.gitattributes` | hoch | Sprachstatistik + Zeilenenden, siehe B6 |
| `THIRD-PARTY-NOTICES.md` | hoch | GPL-Auflage bei Binärverteilung, siehe 6.2 |
| `CONTRIBUTING.md` | hoch | siehe 6.1 |
| `.github/ISSUE_TEMPLATE/*.yml` + `config.yml` | hoch | lenkt Sicherheitsmeldungen weg von öffentlichen Issues |
| `.github/PULL_REQUEST_TEMPLATE.md` | mittel | von Silicant übernehmen, um den GPL-Satz ergänzt |
| `.github/workflows/ci.yml` | mittel | `pytest` auf `windows-latest`, siehe 9.1 |
| `CHANGELOG.md` | mittel | `1.0.0` mit Phasen-Kurzfassung |
| `docs/screenshot-*.png` | mittel | ohne Bilder klickt niemand |
| `docs/threat-model.md` | mittel | englische Kurzfassung von Bauplan B.10, das Prunkstück |
| `docs/architecture.md` | niedrig | englische Kurzfassung, falls CLAUDE.md nicht mitkommt |
| `.github/workflows/release.yml` | niedrig | `.exe` + SHA-256 automatisch ans Release |
| `CODE_OF_CONDUCT.md` | niedrig | bei einem Ein-Personen-Projekt Zierrat, Contributor Covenant wenn überhaupt |

### 6.1 CONTRIBUTING.md: ein Punkt, den Silicants Fassung nicht hat

Nimm Silicants Datei als Basis, aber ergänze zwingend zwei Absätze, sonst entsteht sofort
Reibung:

- **Sprachregel.** Der gesamte Code ist auf Deutsch kommentiert, die UI ist Englisch.
  Das musst du aussprechen, sonst schickt dir der erste Beitragende eine PR, die alle
  Kommentare übersetzt, oder er kommentiert seinen Beitrag englisch und die Datei wird
  zweisprachig. Meine Empfehlung: **"UI strings, docs and commit messages: English.
  Code comments: German is the existing convention; new comments in German preferred,
  English accepted."** Das ist ehrlich und blockiert niemanden.
- **Der Bauplan-Vorbehalt.** Wenn `Planung/` mitkommt (siehe 7), muss dort stehen, dass
  der Bauplan die verbindliche Quelle ist und Änderungen an Verträgen (Bridge-API,
  Fehlercodes, Shortcuts, Gates) den Plan mitziehen. Ohne diesen Satz sind PRs, die den
  Plan nicht kennen, unvermeidlich und du musst jedes Mal dasselbe erklären.
- **Der Sicherheitsvorbehalt.** "Änderungen an `backend/security.py`, `db.py` oder am
  `.enc`-Format brauchen vor der Umsetzung ein Issue." Sonst bekommst du gut gemeinte
  Krypto-PRs, die du nicht mergen kannst und trotzdem begründen musst.

### 6.2 THIRD-PARTY-NOTICES.md: warum das bei einer `.exe` Pflicht ist

Solange nur Quelltext im Repo liegt, reicht `requirements.txt`. Sobald du die
`NoaToDo.exe` an ein Release hängst, verteilst du kompilierte Fassungen von SQLCipher,
OpenSSL, `cryptography`, Argon2, den PyWinRT-Bindings und den beiden Schriften **in einer
einzigen Datei**. Fast alle diese Lizenzen (BSD, MIT, Apache-2.0, OFL, zlib) verlangen,
dass ihr Lizenztext und Copyright-Vermerk mitgeht.

Praktikable Lösung: eine `THIRD-PARTY-NOTICES.md` im Repo, die alles auflistet, plus im
README beim Download-Abschnitt der Satz, dass die Vermerke dort liegen. Zwei Extras, die
sich lohnen:

- Die Datei aus `requirements.lock.txt` generieren statt sie zu pflegen (ein kleines
  `tools/gen_notices.py` mit `importlib.metadata`), sonst veraltet sie beim ersten
  Dependency-Update.
- Apache-2.0 (`cryptography`) verlangt zusätzlich, eine vorhandene `NOTICE`-Datei
  weiterzugeben. Einmal ins Paket schauen und den Inhalt übernehmen.

### 6.3 SECURITY.md: Entwurf

```markdown
# Security Policy

## Reporting a vulnerability

Please report security issues privately, not as a public issue.

Use GitHub's private vulnerability reporting (Security tab -> Report a vulnerability)
or email <deine Adresse>.

I am a single maintainer working on this in my spare time. Expect a first reply within
7 days. Please allow 90 days before public disclosure.

## Scope

In scope:
- Anything that leaks task text, list names or the passphrase outside the vault.
- Anything that lets code run in the WebView (XSS is effectively RCE here: the frontend
  has full `pywebview.api.*` access).
- Anything that bypasses the lock allowlist, the auto-lock timer or the rate limit ladder.
- Mistakes in the key derivation, the `.enc` container format or the AEAD usage.
- Anything the app claims but does not do. Honest security claims are a hard rule in this
  project; a false claim is a bug even when nothing is technically broken.

Out of scope (documented non-goals, see the threat model):
- Malware or code execution in the same Windows user account.
- A compromised or hostile Windows installation.
- Photos of the screen, shoulder surfing, hardware keyloggers.
- Data recovery after a forgotten passphrase. There is none, by design.
- Plaintext left behind by the export feature.
- The missing code signature. It is known and documented; a certificate is a cost
  question, not an oversight.

## Supported versions

Only the latest release. There are no backports.
```

Vor dem Öffentlich-Stellen im Repo unter Settings -> Security **"Private vulnerability
reporting"** einschalten, sonst geht der Link ins Leere.

---

## 7. Was raus muss oder raus sollte

### 7.1 `CLAUDE.md` (112 KB)

**Empfehlung: raus, wie bei Silicant.** Begründung:

- Es ist eine **Anweisung an eine KI**, keine Dokumentation für Menschen. Sätze wie
  "Do not re-add any toast" und "Do not go back to animating the mask" lesen sich für
  einen Fremden als seltsame Verbotsliste ohne Kontext.
- Es verrät den Arbeitsstil vollständig. Das musst du nicht verstecken, aber du musst es
  auch nicht in den Vordergrund stellen, und es ist die **erste** Datei, die GitHub im
  Root-Listing gross anzeigt.
- Es ist an mindestens zwei Stellen **falsch**, und Fehler in der auffälligsten Datei des
  Repos schaden mehr als die Datei nützt:
  - Es nennt `Planung/Plananalyse - Schwachstellen und Angriffsvektoren.md` als
    "standing audit". Die Datei wurde am 2026-07-16 gelöscht (Commit `90e7023`).
  - Es beschreibt `Code/sound-preview.html` als Datei im Projekt. Sie wurde nie
    committet.
- Der Nutzen für Beitragende ist real, aber ersetzbar: die 5 bis 10 Prozent, die eine
  fremde Person wirklich braucht (Architektur, Bridge-API, Rendering-Modell, die
  `esc()`-Regel, die WinForms-Thread-Regel), passen in eine `docs/architecture.md` von
  zwei Seiten.

**Gegenargument, ehrlich:** CLAUDE.md ist objektiv die beste technische Dokumentation,
die das Projekt hat, und jemand, der `lockwindow.py` verstehen will, ist ohne sie
verloren. Wenn du sie behalten willst, dann bitte **nicht als Root-Datei**, sondern als
`docs/internal-notes.md` mit einem ehrlichen Vorwort ("These are working notes for an AI
assistant, kept because they document why things are the way they are. They are not a
user manual and they are not always current."). Und die beiden Fehler vorher korrigieren.

**Wichtig, egal wie du entscheidest:** wenn CLAUDE.md aus dem öffentlichen Repo
verschwindet, brauchst du sie lokal weiter. Also `.gitignore`-Eintrag **plus**
`git rm --cached CLAUDE.md`, damit die Arbeitskopie erhalten bleibt. Genau so hast du es
bei Silicant gemacht.

### 7.2 `Planung/` (2,2 MB)

Hier würde ich **anders entscheiden als bei Silicant**, und zwar für ein Mitnehmen in
reduzierter Form. Drei Optionen:

**Option 1: alles raus.** Konsistent mit Silicant, kleinstes Repo, keine deutschen
Ordnernamen. Verlust: der Bauplan ist das Aussergewöhnliche an diesem Projekt. Ein
414-KB-Dokument, das die Sicherheitsentscheidungen mit Begründung und Gegenargument
protokolliert, sieht man in einem Hobbyprojekt praktisch nie. Er ist der Grund, warum
jemand dem Verschlüsselungsversprechen glaubt.

**Option 2 (Empfehlung): der Bauplan bleibt, der Rest geht.**

| Datei | Entscheidung | Warum |
|---|---|---|
| `Bauplan - NoaToDo.md` | **bleibt**, nach `docs/bauplan.md` | das Prunkstück, siehe oben |
| `Umbauplan - Struktur des Bauplans.md` | raus | reines Meta-Protokoll über eine Umsortierung |
| `tools/verify_umbau.py` | raus | Werkzeug für genau diesen einmaligen Umbau |
| `weiteres/NoaToDo UI Konzept.html` (1,45 MB) | raus aus `Planung/`, ggf. nach `docs/ui-concept.html` | 60 Prozent des Repos, und verantwortlich für die falsche Spracherkennung; als historisches Designdokument aber nett |
| `weiteres/NoaToDo Logo.png` | **umziehen** nach `assets/` | wird von `tools/make_icon.py` gebraucht, siehe C1 |
| `weiteres/UI Skizze.jpeg` | raus | Handskizze, ohne Kontext wertlos |
| `weiteres/UX-UI Verbesserungen.md` | raus | Zwischenstand von Phase 6, beschreibt lauter Dinge, die es nicht mehr gibt (Fake-Profil, Toasts). Wäre aktiv irreführend. |
| `weiteres/technische Grundlage.txt` | **raus** | Der Bauplan sagt selbst, es sei "historisch und nur teilweise gültig"; es beschreibt Microsoft-Graph-Sync, `winotify` und `sqlite3` ohne SQLCipher, also drei Dinge, die es nicht gibt. Ein Erstleser, der zufällig hier landet, hat ein vollständig falsches Bild. |

Dazu unbedingt ein Vorwort-Kasten oben im Bauplan, englisch, etwa:
`This is the German-language build plan the app was written from. It is the binding
specification for the project, not user documentation, and it documents rejected options
and honest limits alongside the decisions.`

**Option 3: der Bauplan kommt in ein eigenes Repo** (`NoaToDo-Bauplan`) und wird im README
verlinkt. Sauberste Trennung, aber zwei Repos, die auseinanderlaufen können, und CLAUDE.md
verlangt ausdrücklich, dass Code und Plan in **derselben** Änderung synchron bleiben.
Würde ich lassen.

### 7.3 Kleinkram, der raus kann

- `Code/tools/spike_u3_lockwindow.py` (237 Zeilen). Ein Experiment aus Phase 8, dessen
  Ergebnis längst im Code steht. Entweder löschen oder nach `docs/` verschieben mit einer
  Zeile Erklärung. Ein Repo, in dem "spike" im Dateinamen steht, wirkt unaufgeräumt.
  Gegenargument: der Spike **belegt** die Entscheidung N11.18 (zwei WebView2-Profile
  gehen nicht in einem Prozess). Wenn du ihn behältst, dann mit einem Kommentar, der das
  sagt.
- `Code/tools/verify_crypto.py` **bleibt unbedingt**. Das ist der eigenständige
  G28-Nachweis, und für ein OSS-Krypto-Projekt ist ein Skript, mit dem jeder die
  Verschlüsselung selbst nachprüfen kann, Gold wert. Im README erwähnen.

---

## 8. Code-Befunde, die beim Öffnen sofort auffallen würden

Das sind echte kleine Fehler, die ich beim Durchgehen gefunden habe. Keiner ist
dramatisch, alle sind in Minuten behoben, und alle wären in einem öffentlichen Repo
peinlich, weil sie leicht zu finden sind.

### C1. `tools/make_icon.py` ist kaputt

```python
SRC = os.path.join(HERE, "..", "..", "Planung", "NoaToDo Logo.png")
```

Das Logo liegt seit dem Umsortieren in `Planung/weiteres/NoaToDo Logo.png`. Das Skript
kann heute nicht laufen. **Verifiziert**, die Datei existiert unter dem erwarteten Pfad
nicht.

Zusätzlich ist das eine harte Abhängigkeit **aus `Code/` heraus in `Planung/` hinein**.
Wenn `Planung/` nicht mit veröffentlicht wird, ist das Werkzeug im öffentlichen Repo
endgültig unbenutzbar. Beides löst derselbe Fix: Logo nach `assets/noatodo-logo.png`,
Pfad im Skript anpassen.

### C2. Eine deutsche Meldung in einer sonst englischen UI

`main.py:1068`, der Fallback der Einzelinstanz-Meldung:

```python
"NoaToDo läuft bereits. Es kann nur eine Instanz geöffnet sein."
```

Der Normalfall darüber (`wintheme.show_message`) ist korrekt englisch. Der Fallback
greift nur, wenn `wintheme` nicht importierbar ist, also selten, aber er ist die einzige
deutsche Zeichenkette, die ein Nutzer je sehen kann. Auf Englisch umstellen.

Ebenfalls in der Ausgabe: `print("[NoaToDo] Bereits aktiv, ...")` und weitere deutsche
`print`-Zeilen. Die sind Diagnose auf der Konsole und im Release unsichtbar (kein
Konsolenfenster), also unkritisch. Wenn du magst, mit demselben Handgriff mit erledigen.

### C3. `pillow` steht in der Laufzeit-Lock, wird aber nur vom Build-Werkzeug gebraucht

`requirements.lock.txt` und `requirements.lock.hashes.txt` listen `pillow==12.2.0`.
Verifiziert: `PIL` wird **nirgends** zur Laufzeit importiert, nur in
`tools/make_icon.py`. Die lose `requirements.txt` nennt Pillow korrekterweise nicht.

Die Lock-Datei ist offenbar ein `pip freeze` der Entwicklungsumgebung. Das ist an sich
in Ordnung, aber ein Prüfer fragt zu Recht "warum braucht eine To-Do-App eine
Bildbibliothek?". Sauber wäre: Pillow nach `requirements-dev.txt` verschieben und aus
den beiden Lock-Dateien nehmen. **Vorher prüfen**, dass die `.exe` danach noch baut und
startet (PyInstaller zieht Pillow nicht mit, die Spec hat keinen Pillow-Hiddenimport,
sollte also glattgehen).

### C4. Die vier `requirements`-Dateien brauchen eine Erklärung

Der Aufbau ist gut (lose / gepinnt / gepinnt mit Hashes / dev), aber ohne Kommentar
verwirrend. Zwei Zeilen im README-Abschnitt "Development" und je ein Kopfkommentar in den
Dateien lösen das. `requirements.lock.hashes.txt` hat schon einen, die anderen nicht.

### C5. Deutsche Kommentare als Beitrags-Hürde

Kein Fehler, sondern eine Tatsache, die eine Entscheidung braucht: `security.py`,
`api.py`, `lockwindow.py` und `wintheme.py` sind vollständig auf Deutsch dokumentiert,
oft mit sehr dichter Begründungsprosa. Für einen englischsprachigen Beitragenden ist die
Einstiegshürde damit hoch.

**Meine Empfehlung: nicht übersetzen.** Erstens sind es rund 10.000 Zeilen, zweitens ist
die Prosa die eigentliche Qualität (eine maschinelle Übersetzung würde sie zerstören),
drittens ist ein deutschsprachiges Projekt völlig legitim. Stattdessen: im README und in
CONTRIBUTING **einen Satz** dazu, damit es niemanden überrascht, und die neuen englischen
Dokumente (`docs/architecture.md`, `docs/threat-model.md`) als Brücke.

### C6. Die Architektur-Beschreibung in CLAUDE.md ist an einer Stelle veraltet

Der Baum dort zeigt noch

```
data/
├── tasks.db          # current working DB
└── tasks.db.enc      # Phase 8 target
```

Seit Phase 8 gibt es kein `data/tasks.db` mehr, und `tasks.db.enc` liegt am
nutzergewählten Ort, nicht in `Code/data/`. Falls CLAUDE.md doch mitkommt: korrigieren.
Falls nicht: darauf achten, dass der Fehler nicht in `docs/architecture.md` wandert.

---

## 9. Release, CI und die Verteilung der `.exe`

### 9.1 GitHub Actions

Die Tests **müssen auf `windows-latest` laufen**. `sqlcipher3-wheels` liefert nur
Windows-Wheels, und `ostheme.py`/`radio.py`/`wintheme.py` sind Windows-gebunden. Ein
`ubuntu-latest`-Job scheitert schon am Import.

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'     # Gate G11: gepinnt, nicht 3.12
      - run: pip install --require-hashes -r src/requirements.lock.hashes.txt
      - run: pip install -r src/requirements-dev.txt
      - run: python -m pytest
        working-directory: src
```

Zwei Hinweise, die dir sonst eine rote CI bescheren:

- `python-version: '3.11'` ist **nicht optional**, das ist Gate G11 und `build_exe.py`
  bricht auf allem anderen ab.
- `conftest.py` biegt `%LOCALAPPDATA%` um und blockt `keyring` hart. Der Runner hat
  ohnehin keinen Credential Manager mit Inhalt, das passt also. Die 63 Tests brauchen
  bei 64 MiB Argon2 rund 4 Sekunden, das kostet nichts.

Ein grüner CI-Badge im README ist bei einer Sicherheits-App überproportional viel wert:
er beweist, dass die Krypto-Tests bei jedem Commit laufen.

### 9.2 Das Release

- Tag `v1.0.0` setzen, Release anlegen, `NoaToDo.exe` anhängen.
- **SHA-256 des Artefakts im Release-Text nennen.** Bei einer unsignierten Binärdatei ist
  die Prüfsumme die einzige Möglichkeit, die ein Nutzer hat. Der `.exe`-Download ohne
  veröffentlichte Prüfsumme wäre bei diesem Projekt eine Lücke im eigenen Anspruch.
- Im Release-Text die drei Punkte nennen, die sonst als Issues zurückkommen:
  1. **SmartScreen warnt.** Weil unsigniert. Weg: "More info" -> "Run anyway".
  2. **Virenscanner können anschlagen.** One-file-PyInstaller-Bundles entpacken sich zur
     Laufzeit, das ist ein klassisches Heuristik-Muster. Kein UPX zu benutzen war die
     richtige Entscheidung und reduziert es, beseitigt es aber nicht.
  3. **WebView2-Runtime wird vorausgesetzt.** Auf aktuellem Windows 10/11 vorhanden. Die
     App sagt es sonst ehrlich und beendet sich, statt ein weisses Fenster zu zeigen.

### 9.3 Reproduzierbarkeit, ehrlich benannt

Jemand wird fragen: "Wie weiss ich, dass die `.exe` zu diesem Quelltext gehört?" Die
ehrliche Antwort heute: **gar nicht sicher.** PyInstaller-Builds sind ohne zusätzliche
Arbeit nicht bit-reproduzierbar (Zeitstempel, Pfade, Ordnung im Archiv), und eine
Signatur gibt es nicht.

Was du **stattdessen** bieten kannst, und was ich empfehle, weil es zum Ehrlichkeits-Gate
G22 passt:

- Die `.exe` **im CI bauen** statt lokal, und den Workflow-Lauf im Release verlinken.
  Dann ist zumindest öffentlich einsehbar, aus welchem Commit und mit welchen
  Abhängigkeiten sie entstanden ist. Das ist der grösste Vertrauensgewinn pro Aufwand,
  den du hier holen kannst.
- Der Build-Stempel schreibt Commit-Hash und Build-Datum schon in die Binärdatei, und
  das Status-Modal zeigt es an. Das im README erwähnen, es ist ein starkes Detail.
- Im README einen Satz: "Builds are not bit-for-bit reproducible and the binary is not
  signed. If you do not want to trust the published exe, build it yourself: `build.bat`."

### 9.4 Zwei Dinge zu G27, die die Veröffentlichung verändert

Das ist der Punkt, den man leicht übersieht, wenn man nur ans Repo denkt:

- **Der Nuitka-Wunsch aus G27 ("keinen Python-Quelltext mitliefern, vorzugsweise Nuitka,
  weil PyInstaller entpackbar ist") verliert seinen Zweck.** Er sollte Dekompilieren
  erschweren. Wenn der Quelltext auf GitHub liegt, ist Dekompilieren sinnlos. Der
  **Pflichtteil** von G27 (keine Klartext-Docstrings, keine `assert`s im Bundle) bleibt
  sinnvoll, weil er die Binärdatei schlank hält, aber die Begründung ändert sich. Das
  sollte im Bauplan stehen, sonst steht dort dauerhaft eine Anforderung, deren Grund
  entfallen ist.
- **Das Code-Signing wird dagegen wichtiger, nicht unwichtiger.** In dem Moment, wo jeder
  forken und eine eigene `NoaToDo.exe` bauen kann, ist "ist diese Datei die echte?" eine
  reale Frage und keine theoretische. Signatur gibt es nicht, also muss die
  veröffentlichte Prüfsumme diese Rolle übernehmen (9.2).

---

## 10. Womit du nach dem Öffnen rechnen solltest

Zwei Schritte vorausgedacht. Das sind die Reaktionen, die bei einer Krypto-App mit
Abstand am häufigsten kommen, plus die Antwort, die du **vorher** vorbereiten solltest.

| Kommt garantiert | Vorbereitete Antwort |
|---|---|
| "Warum nicht signiert?" | README + SECURITY.md sagen es schon: kein Zertifikat, Kostenfrage, Prüfsumme als Ersatz. Wenn es im README steht, wird es nicht zum Issue. |
| "Rollt ihr eigene Krypto?" | Nein: Argon2id, HKDF, ChaCha20-Poly1305 und SQLCipher sind Standardbausteine, eigen ist nur ihre Kombination. Das gehört als Satz ins README, sonst liest es jemand falsch. |
| "Warum zwei Schichten? Das ist Sicherheitstheater." | Legitime Kritik. Die ehrliche Antwort steht im Bauplan (Defense in Depth gegen einen Implementierungsfehler in einer Schicht) und die musst du **nicht** überverkaufen. |
| "SQLCipher plus ChaCha, aber das Working File liegt auf Platte?" | Bereits beantwortet: die Arbeitskopie ist selbst SQLCipher-verschlüsselt, nie Klartext, und der Grund (N11.9, `sqlcipher3` hat kein `serialize`) ist dokumentiert. Diese Antwort sollte im README stehen, nicht nur im Bauplan. |
| "Der Panik-Knopf löscht ja gar nichts." | Genau das ist eine bewusste Entscheidung (N11.17) mit ausgeschriebener Begründung. Ein Verweis auf `docs/threat-model.md` erledigt es. |
| Issues auf Deutsch | Sprachregel in `ISSUE_TEMPLATE/config.yml` und CONTRIBUTING festlegen. Ich würde "English preferred, German fine" nehmen. |
| "Bitte Linux/macOS-Port" | Antwort vorbereiten: DPAPI, WebView2, WinForms und die WinRT-Radios sind Windows-Kern. Ein Port wäre eine Neuentwicklung. Als "won't fix" mit Begründung ins README unter "System requirements". |
| Ein Bot-PR, der Abhängigkeiten aktualisiert | Dependabot bewusst ein- oder ausschalten. Bei hash-gepinnten Requirements muss die Hash-Datei mitgezogen werden, das schafft Dependabot nicht allein. Ich würde ihn **aus** lassen und stattdessen die im Bauplan schon vorgesehene "Rebuild-Kadenz bei CVEs" im README nennen. |

---

## 11. Die Pflicht, die dein eigenes Projekt dir auferlegt

CLAUDE.md formuliert eine Regel, die auch für diese Änderung gilt und die man beim
Aufräumen leicht vergisst: **eine Änderung, die den Plan nicht nachzieht, ist nicht
fertig.** Die Veröffentlichung ist eine Entscheidung wie jede andere, sie gehört also
protokolliert. Konkret:

1. **Eintrag im Entscheidungsregister (Bauplan Anhang 1):** "NoaToDo wird unter
   GPL-3.0-or-later veröffentlicht, Datum, Begründung." Nach der Redaktionsregel seit dem
   Struktur-Umbau **kein neuer Nachtragsblock**, sondern die Norm in ihren Teil-B-Vertrag
   plus eine Registerzeile.
2. **B.10 ergänzen:** Bislang steht dort "der Quellcode ist kein Schutzgut (Kerckhoffs)".
   Das war bisher eine Annahme, jetzt ist es eine Tatsache. Ein Satz genügt, aber er
   macht aus einer Behauptung eine überprüfbare Aussage, und genau davon lebt B.10.
3. **G27 nachziehen**, siehe 9.4: der Nuitka-Grund entfällt, der Signing-Grund verstärkt
   sich, die Prüfsumme wird zur Ersatzmassnahme.
4. **Phase 9 ergänzen** um den Auslieferungsweg "GitHub Release mit veröffentlichter
   SHA-256" statt nur "Datei weitergeben".
5. **CLAUDE.md spiegeln** (falls sie im Projekt bleibt, siehe 7.1) plus die zwei Fehler
   aus 7.1 korrigieren.
6. **Die Gate-Tabelle B.9** anfassen, falls du G27 umformulierst: die Redaktionsregel
   verlangt, dass die normative Tabelle und nicht nur die Schnellübersicht gepflegt wird.
   Genau das war am 2026-08-10 schon einmal auseinandergelaufen.

---

## 12. Fahrplan

**Etappe 1: Recht (ohne das kein "public")**
1. `LICENSE` (GPL-3.0) anlegen
2. `Code/frontend/fonts/OFL.txt` + Copyright-Notiz der beiden Familien
3. `THIRD-PARTY-NOTICES.md`
4. Lizenz-Header in alle Quelldateien, als `#`-Kommentar **über** dem Docstring
5. `pytest` laufen lassen, nichts darf brechen

**Etappe 2: Aufräumen**
6. Entscheidung CLAUDE.md (Empfehlung: `git rm --cached` + `.gitignore`)
7. Entscheidung `Planung/` (Empfehlung: Bauplan nach `docs/bauplan.md`, Rest raus)
8. Logo nach `assets/`, `make_icon.py` reparieren (C1)
9. Deutsche Fallback-Meldung auf Englisch (C2)
10. Pillow aus den Laufzeit-Locks (C3), danach einmal `build.bat` zur Kontrolle
11. Optional: `Code/` nach `src/` (dann Doku im **selben** Commit nachziehen)

**Etappe 3: Sichtbarkeit**
12. `.gitattributes` (B6)
13. `README.md` schreiben, **nach** dem Umbau, mit den drei Sicherheitsabschnitten aus 5.2
14. Screenshots nach `docs/` (Vorschlag: Liste mit Aufgaben, Lock-Screen mit Ring,
    Status-Modal mit den echten Krypto-Zeilen, Onboarding Schritt 2, Panik-Endschirm)
15. `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
16. `.github/`: PR-Vorlage, Issue-Vorlagen, `config.yml`
17. `grep -rn "TODO" README.md` (der Silicant-Fehler)

**Etappe 4: Vor dem Umschalten**
18. Repo-Beschreibung auf Englisch, Topics setzen (B7)
19. "Private vulnerability reporting" einschalten, Discussions einschalten
20. Bauplan und Register nachziehen (Abschnitt 11)
21. **Dann erst** auf Public schalten

**Etappe 5: Danach**
22. CI-Workflow, Badge ins README
23. Tag `v1.0.0`, Release mit `.exe` + SHA-256 + den drei Hinweisen aus 9.2
24. Branch `oupen-source-NoaToDo` und diese temporäre Datei löschen

---

## 13. Was nur du entscheiden kannst

1. **CLAUDE.md:** raus (wie Silicant), oder als `docs/internal-notes.md` mit Vorwort? Ich
   empfehle raus.
2. **Bauplan:** mitnehmen? Ich empfehle ja, als `docs/bauplan.md`, deutsch, mit englischem
   Vorwortkasten. Er ist der Grund, warum dieses Projekt anders aussieht als andere
   Hobbyprojekte.
3. **`Code/` nach `src/`?** Kostet einen Doku-Durchgang. Ich empfehle ja, weil du es bei
   Silicant genauso gemacht hast und die Pfade im Code alle relativ sind.
4. **Copyright-Halter:** "Noa Gnos" (wie Silicant) oder der Handle?
5. **Wird die `.exe` mitveröffentlicht?** Wenn ja, gelten 6.2 (Notices) und 9.2
   (Prüfsumme) als Pflicht, nicht als Kür.
6. **Kontaktadresse in SECURITY.md:** dieselbe Gmail wie in den Commits, oder eine
   getrennte?

---

## 14. Zwei Sätze zum Schluss

Was dieses Projekt von hundert anderen To-Do-Apps unterscheidet, ist nicht die
Verschlüsselung, sondern dass es **aufschreibt, was es nicht kann**: der Panik-Bildschirm,
der bewusst nicht lügt, das Screenshot-Feature, das verworfen wurde, weil es nichts
abwehrte, die BitLocker-Anzeige, die "unknown" sagt statt zu raten. Das ist genau der
Ton, in dem das README geschrieben sein sollte.

Und es heisst: der wertvollste Abschnitt deines README ist der mit der Überschrift
"Honest limits", nicht der mit der Überschrift "Features".
