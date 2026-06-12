# UX/UI Verbesserungen, NoaToDo

Stand: 2026-06-12, nach Abschluss von Phase 6 (plus Phase 6.5 Follow-ups).
Analysierte Dateien: `frontend/app.js`, `frontend/style.css`, `frontend/index.html`, `backend/api.py`, `main.py`, abgeglichen mit `Bauplan - NoaToDo.md` und `CLAUDE.md`.

Dieses Dokument sammelt alles, was sich am User Interface und an der User Experience noch verbessern laesst. Es ist bewusst vollstaendig statt kurz. Am Ende steht eine priorisierte Uebersicht. Sicherheitsrelevante Punkte sind mit **[Sec]** markiert, weil UI-Entscheidungen hier direkt auf die Security-Story der App einzahlen.

---

## 1. Kritische Funde (Funktionsluecken mit direkter UX-Wirkung)

Diese Punkte sind keine Geschmacksfragen, sondern Stellen, an denen die App heute objektiv unfertig oder irrefuehrend ist.

### 1.1 Listen koennen nicht geloescht werden
Das Backend bietet `delete_list(id)` (Bridge-API), aber das Frontend hat keinerlei Aufrufstelle dafuer: kein Button, kein Kontextmenue, kein Modal. Wer eine Liste loswerden will, kommt nur ueber das Loeschen der DB-Datei ans Ziel.

**Vorschlag:** Loeschen ueber ein Listen-Kontextmenue (Rechtsklick auf den Sidebar-Eintrag) oder einen Papierkorb-Button im Rename-Modal, immer mit Bestaetigungs-Modal ("Liste und N Aufgaben loeschen?"). Bei `synced=1`-Listen den Hinweis ergaenzen, dass die Liste beim naechsten Sync wiederkommen kann.

### 1.2 Task-Loeschung ueber die Rail erfolgt ohne Bestaetigung, das Bestaetigungs-Modal ist toter Code
`renderModal` enthaelt einen kompletten `case 'delete'` mit Bestaetigungsdialog (app.js:449), aber nichts setzt jemals `state.modal = 'delete'`. Der Rail-Button `tb-delete` ruft `deleteTask()` direkt auf (app.js:965). Ein Fehlklick auf den Papierkorb loescht also sofort und endgueltig, es gibt kein Undo.

**Vorschlag (eine der beiden Richtungen, nicht beide):**
- Entweder das vorhandene Modal anschliessen (`tb-delete` -> `state.modal = 'delete'`),
- oder (besser fuer den Flow) sofort loeschen, aber den Toast um eine "Undo"-Aktion erweitern (Task 5 Sekunden im Speicher halten, bei Undo per `add_task`/`reorder` wiederherstellen). Dann das Modal aus dem Code entfernen.

### 1.3 Glocken- und Profil-Menue sind unerreichbar (toter Code) und zeigen Fake-Daten
`renderNotifMenu` und `renderProfileMenu` existieren samt Click-Handlern (`open-notif`, `open-profile`), aber `renderHeader` rendert nur den Sidebar-Toggle, keinen Header mit Glocke/Avatar. Die Menues sind im UI nicht erreichbar. Zusaetzlich sind ihre Inhalte hardcodiert: drei erfundene Benachrichtigungen und ein Profil "Noa Andersen, signed in", obwohl MSAL (Phase 8) nicht existiert.

**Vorschlag:** Entscheiden, ob der Header aus dem UI-Konzept (56px, Glocke, Avatar, Schild) kommt oder dauerhaft entfaellt.
- Kommt er: jetzt als leere, ehrliche Variante einbauen (Glocke ohne Fake-Eintraege, Profil im Zustand "not signed in" mit deaktiviertem Sign-in-Hinweis "Phase 8").
- Entfaellt er: `renderNotifMenu`, `renderProfileMenu`, die zugehoerigen `data-act`-Faelle und die `.menu`/`.notif-item`-CSS-Bloecke entfernen. Toter Code taeuscht bei jeder zukuenftigen Aenderung Funktionalitaet vor.

### 1.4 Status-Modal zeigt hardcodierte Fantasiewerte statt `get_status()` **[Sec]**
Das "App status"-Modal (app.js:410) behauptet "Encryption: AES-256 + ChaCha20 · Argon2id, active" und "Microsoft Graph: token valid". Beides ist falsch: die Dual-Layer-Verschluesselung ist Phase 11, der Graph-Login Phase 8. Das Backend hat sogar eine echte `get_status()`-Methode (api.py:307) mit DB-Pfad und Groesse, die das Frontend nie aufruft. Fuer eine App, deren Kernversprechen Sicherheit ist, ist eine geschoente Sicherheitsanzeige das schlechteste denkbare Signal: Wer ihr einmal misstraut, misstraut allem.

**Vorschlag:** Das Modal auf `await api().get_status()` umstellen und nur belegbare Fakten zeigen. Ehrliche Zustaende einfuehren: "Layer 2 (ChaCha20): not yet active (Phase 11)", "Graph: not connected". Gleiches gilt fuer den Panic-Modal-Text, der "stays encrypted" verspricht, und den Lock-Screen-Untertitel "LOCAL VAULT · ENCRYPTED".

### 1.5 Export meldet Erfolg, obwohl keine Datei geschrieben wird
`doExport` zeigt den Toast "Exported list" (app.js:754), aber Phase 7 (Speicherdialog) ist offen, es wird nie eine Datei geschrieben. Der Nutzer glaubt, exportiert zu haben, und findet nichts auf der Platte.

**Vorschlag (bis Phase 7 fertig ist):** Toast-Text auf etwas Ehrliches aendern ("Export prepared, saving comes in Phase 7") oder den Button bis dahin als "coming soon" kennzeichnen. Sobald Phase 7 kommt: Formatwahl anbieten (das Backend kann `md`/`txt`/`json`, das Frontend hardcodiert `'md'`), z. B. ein kleines Popover analog zum Accent-Picker.

### 1.6 CSS- und Handler-Leichen aus Phase 6.5
- `.t-del` (Loeschknopf pro Task) hat CSS (style.css:981) und einen Click-Case (`del-task`, app.js:943), wird aber in `renderTask` nicht gerendert. CLAUDE.md beschreibt den per-Task-Loeschknopf als implementiert, der aktuelle Stand widerspricht dem.
- `.t-grip` (Drag-Griff) hat CSS (style.css:628), wird nie gerendert. Dadurch fehlt jede sichtbare Drag-Affordance (siehe 3.6).
- `.title-row`, `.title-meta`, `.airplane-pill`, `.banner-row` haben CSS, werden ausserhalb des Fokusmodus nie benutzt.

**Vorschlag:** Pro Element entscheiden: rendern oder loeschen. Empfehlung: `.t-del` beim Hover rendern (loest auch 1.2 eleganter), `.t-grip` als Drag-Affordance rendern, Rest entfernen.

### 1.7 Hotkey `N` bei geschlossener Sidebar laeuft ins Leere
`N` setzt `state.adding = true` und fokussiert das New-List-Feld, aber wenn die Sidebar geschlossen ist (`width: 0; opacity: 0`), ist das Feld unsichtbar. Der Nutzer tippt in ein unsichtbares Input.

**Vorschlag:** `N` soll die Sidebar bei Bedarf zuerst oeffnen (Setting `sidebar='open'` setzen), dann das Feld zeigen.

---

## 2. Sprache, Texte, Konsistenz

### 2.1 Sprachmix Deutsch/Englisch
Die UI-Texte sind englisch ("New task…", "Completed", "Settings"), aber `title`-Tooltips und einzelne Strings deutsch ("Listen ein-/ausblenden", "Schließen", "Neues To-Do hinzufügen", "Werkzeugleiste anheften"). Das wirkt unfertig.

**Vorschlag:** Eine Sprache festlegen (vermutlich Englisch, da alle sichtbaren UI-Texte englisch sind) und alle `title`-Attribute angleichen. Wenn spaeter beide Sprachen gewuenscht sind: jetzt schon alle Strings in ein zentrales `STRINGS`-Objekt ziehen, das macht die spaetere Lokalisierung trivial.

### 2.2 Mac-Symbole auf einer Windows-App
Toolbar-Tooltips und das Shortcuts-Modal zeigen `⌘E`, `⌘L`, `⌘⇧!`, `⌘B`, `⌘J`. NoaToDo ist eine reine Windows-App, dort heisst das `Ctrl`/`Strg`. Das ⌘-Symbol ist fuer Windows-Nutzer Rauschen.

**Vorschlag:** Ueberall `Ctrl` (bzw. `Ctrl+Shift+!`) anzeigen. Die kbd-Kapseln im Shortcuts-Modal vertragen Text problemlos.

### 2.3 Shortcuts-Modal ist unvollstaendig
Es fehlen: `Esc` (alles schliessen), `?` selbst, Hinweis auf Doppelklick-Edit, und der Mini-Modus hat gar keinen Shortcut (nur Rail-Button). Ausserdem listet B.5 `Ctrl+E` als Export, aber nicht, dass nur die aktive Liste exportiert wird.

**Vorschlag:** Modal vervollstaendigen, fuer Mini-Modus einen Shortcut ergaenzen (z. B. `Ctrl+M`) und in B.5 nachziehen. Maus-Gesten (Doppelklick = Edit, Klick = Auswahl, Drag = Sortieren) als eigene kleine Sektion im Modal dokumentieren, das loest gleichzeitig das Discoverability-Problem aus 3.4.

### 2.4 Irrefuehrende Toast-Texte
- "Back online, syncing" (app.js:727): es gibt keinen Sync (Phase 9). 
- "Exported list" (siehe 1.5).
- Panic-Modal: "pulls the local database offline", "stays encrypted": beschreibt Phase-11-Verhalten als Gegenwart.

**Vorschlag:** Texte am tatsaechlichen Verhalten ausrichten, Zukunftsfeatures klar als solche labeln. Nach Phase 9/11 wieder anpassen.

### 2.5 Empty-States koennten fuehren statt nur informieren
"// nothing open, you're all caught up" passt zum Terminal-Look, sagt aber Neulingen nicht, wie es weitergeht. 

**Vorschlag:** Eine zweite Zeile mit Handlungsaufforderung: "// press + below to add a task". Im "no lists yet"-Fall analog auf die Sidebar bzw. Taste `N` verweisen.

---

## 3. Interaktionsdesign

### 3.1 Esc raeumt alles gleichzeitig ab
`onKeyGlobal` schliesst bei Esc in einem einzigen Schritt: Menues, Modal, Farb-Popover, Fokusmodus, beide Inline-Eingaben, Edit-Modus und die Task-Auswahl (app.js:986). Wer im Fokusmodus nur ein Modal schliessen will, fliegt aus dem Fokusmodus; wer eine Eingabe abbricht, verliert auch die Auswahl.

**Vorschlag:** Esc gestaffelt behandeln, pro Druck genau eine Ebene (in dieser Reihenfolge): Modal/Popover -> Inline-Eingabe/Edit -> Auswahl -> Fokusmodus/Mini. Das entspricht dem Verhalten praktisch aller Desktop-Apps.

### 3.2 Blur legt eine Liste an
Das New-List-Feld committet bei `blur` (app.js:610): Wer das Feld oeffnet, etwas tippt und dann woanders hinklickt, hat ungewollt eine Liste erstellt. Inline-Task-Edit verhaelt sich gleich (Klick daneben speichert), was dort vertretbar ist, aber die beiden Verhalten sollten bewusst und konsistent gewaehlt sein.

**Vorschlag:** Blur beim New-List-Feld verwerfen statt committen (Enter bleibt der Commit). Alternativ beibehalten, aber dann den "List created"-Toast mit Undo ausstatten.

### 3.3 Kein Undo, nirgends
Loeschen, Abhaken, Umbenennen, Reorder: alles endgueltig. Gerade Abhaken passiert per Einfachklick auf den Kreis und kann bei schnellem Arbeiten danebengehen (der Task verschwindet sofort nach unten in "Completed").

**Vorschlag:** Ein generisches Undo fuer die letzte destruktive Aktion (Task geloescht, Liste geloescht) ueber den Toast. Abhaken braucht kein Undo, wenn die Completed-Sektion gut erreichbar ist, aber siehe 3.8.

### 3.4 Doppelklick-Edit und Klick-Auswahl sind unsichtbare Konventionen
Es gibt keinerlei visuellen Hinweis, dass Doppelklick editiert und Einfachklick auswaehlt. Der Bleistift in der Rail aendert zwar kontextuell seine Bedeutung ("Edit task" vs. "Rename list"), aber das sieht man erst im Tooltip.

**Vorschlag:** 
- Beim Hover ueber eine Task-Karte rechts dezente Aktions-Icons einblenden (Bleistift, Papierkorb), wie es `.t-del` urspruenglich vorsah. Das macht Edit und Delete ohne Rail erreichbar und entdeckbar.
- Maus-Gesten im Shortcuts-Modal dokumentieren (siehe 2.3).

### 3.5 Kein Rechtsklick-Kontextmenue
Fuer eine Desktop-App ist Rechtsklick die natuerlichste Geste. Aktuell oeffnet sich das WebView2-Standardmenue (bzw. nichts).

**Vorschlag:** Eigenes Kontextmenue fuer Task-Karten (Edit, Copy, Delete, Move to list…) und Sidebar-Eintraege (Rename, Export, Delete). Das loest gleich mehrere Luecken (1.1, 3.4, 3.7) mit einem Pattern. Das native WebView2-Kontextmenue unterdruecken.

### 3.6 Drag & Drop ohne Affordance und ohne Alternativen
- Kein sichtbarer Griff (`.t-grip` existiert nur im CSS), nichts signalisiert "sortierbar".
- Keine Tastatur-Alternative (z. B. `Alt+Pfeil hoch/runter` fuer die ausgewaehlte Aufgabe).
- Kein Auto-Scroll, wenn man in einer langen Liste an den Rand draggt.
- Beim Draggen gibt es keinen Drop-Indikator zwischen den Karten, die Karten reordern sich live (funktioniert, aber ein Einfuege-Strich waere praeziser ablesbar).

### 3.7 Aufgaben koennen nicht zwischen Listen verschoben werden
Weder per Drag auf einen Sidebar-Eintrag noch per Menue. Fuer eine Mehrlisten-App eine spuerbare Luecke.

**Vorschlag:** Drag auf Sidebar-Eintrag (Eintrag highlighted als Drop-Ziel) plus "Move to…" im Kontextmenue. Braucht eine kleine Backend-Ergaenzung (`edit_task` um `list_id` erweitern oder eine eigene `move_task`-Methode).

### 3.8 Completed-Sektion: Zustand und Pflege
- `doneOpen` wird bei jedem Listenwechsel zurueckgesetzt (app.js:933). Wer die Sektion offen mag, klickt sie pro Liste immer wieder auf.
- Es gibt kein "Clear completed" (alle erledigten loeschen). Erledigte sammeln sich endlos.
- Erledigte Aufgaben sind nicht sortierbar und zeigen ihr Meta nicht mehr (`renderTask` blendet Meta bei `done` aus), beides okay, aber undokumentiert.

**Vorschlag:** `doneOpen` pro Sitzung global merken (nicht pro Liste zuruecksetzen), "Clear completed" als kleinen Button in den Sektionskopf, mit Bestaetigung/Undo.

### 3.9 Listen in der Sidebar sind nicht sortierbar
Das Schema hat `lists.position`, aber es gibt kein UI zum Umordnen. 

**Vorschlag:** Drag & Drop in der Sidebar analog zu Tasks, gleicher `reorder`-Mechanismus (Backend braucht ein `reorder_lists`).

### 3.10 Tastaturnavigation fuer Aufgaben fehlt komplett
Auswahl geht nur per Mausklick. Es gibt keine Pfeiltasten-Navigation, kein `Space`/`Enter` zum Abhaken der Auswahl, kein `F2` fuer Edit, kein `Entf` fuer Loeschen, keine Moeglichkeit, per `Tab` sinnvoll durch die Aufgaben zu kommen.

**Vorschlag:** Pfeil hoch/runter bewegt die Auswahl, `Space` toggelt, `F2` oder `Enter` editiert, `Entf` loescht (mit Undo), `Alt+Pfeil` sortiert. Das macht die App fuer Power-User und fuer Barrierefreiheit (Abschnitt 5) gleichzeitig besser.

### 3.11 Listenwechsel per Tastatur fehlt
Kein `Ctrl+1..9` fuer Listen, kein `Ctrl+Tab`-Aequivalent. 

### 3.12 Einzeltasten-Hotkeys sind riskant
`G` (online/offline) und `F` (Fokus) feuern bei jedem Tastendruck ausserhalb von Inputs. Ein versehentliches `G` schaltet den (spaeteren) Sync ab, ohne dass der Nutzer es unbedingt bemerkt (der Toast verschwindet nach 2,4 s). Fuer einen Zustandswechsel mit Sync-Folgen ist das eine sehr leichtgewichtige Geste.

**Vorschlag:** `G` auf `Ctrl+G` umlegen oder zumindest einen deutlich sichtbaren, persistenten Offline-Indikator ergaenzen (siehe 4.2). Das Konzept hatte dafuer die `airplane-pill`, deren CSS noch existiert.

### 3.13 Rail-Auto-Hide ist schwer zu entdecken
Bei geschlossener Sidebar und ungepinnter Rail ist die gesamte Werkzeugleiste unsichtbar, bis die Maus zufaellig in die 100px-Zone am rechten Rand kommt. Der Pin-Griff (`.rail-pin`) ist 14px schmal mit `opacity: .3`. Erstnutzer finden Lock, Export und Status moeglicherweise nie.

**Vorschlag:** Wenn die Rail versteckt ist, einen dezenten, permanenten Hinweis am Rand stehen lassen (z. B. den Pin-Griff auf `opacity: .6` und mit drei Punkten), oder die Rail beim ersten Start gepinnt ausliefern und Auto-Hide zur Opt-in-Einstellung machen.

### 3.14 Mini-Modus: kleine Haerten
- `Esc` verlaesst den Mini-Modus sofort (app.js:987), auch wenn man eigentlich nur die Eingabe verwerfen wollte (gestaffeltes Esc, siehe 3.1).
- Kein Listenwechsel im Mini-Fenster moeglich; ein Dropdown im `mini-bar`-Titel waere genug.
- Erledigen ist moeglich (Check funktioniert), aber Auswahl/Edit nicht, okay fuer ein Lesefenster, sollte aber bewusst so dokumentiert sein.

### 3.15 Rail-Aktionen ohne Auswahl wirken tot
"Copy task", "Edit task", "Delete task" tun ohne ausgewaehlte Aufgabe nichts (Copy zeigt immerhin einen Toast, Delete schweigt komplett). Die Buttons sehen aber immer gleich aktiv aus.

**Vorschlag:** Ohne Auswahl die drei Buttons visuell dimmen (`opacity`, `cursor: default`) und im Tooltip "select a task first" zeigen. Der stumme `tb-delete`-Fall sollte mindestens den gleichen Toast bekommen wie Copy.

### 3.16 Sidebar-Resize: Doppelklick-Reset fehlt
Uebliche Konvention: Doppelklick auf den Resize-Handle setzt auf die Standardbreite (256px) zurueck. Aktuell muss man manuell zurueckziehen.

---

## 4. Visuelles Design

### 4.1 Der Hauptbereich hat keinen Listentitel
Im Normalmodus steht der Name der aktiven Liste nur unten im Dock (31px-Pille) und in der Sidebar. Der Hauptbereich beginnt direkt mit "OPEN TASKS". Bei geschlossener Sidebar und viel Inhalt (Dock klebt unten, Inhalt scrollt) fehlt oben jede Orientierung, in welcher Liste man ist. Das CSS fuer einen Titelblock (`.title-row`, `.list-title`, `.title-meta`) existiert bereits und wird nur im Fokusmodus genutzt.

**Vorschlag:** Listentitel oben im Hauptbereich anzeigen (wie im UI-Konzept), das Dock darf dann schlanker werden. Alternativ bewusst beim Dock-Konzept bleiben, dann aber das Dock beim Scrollen nicht ueberdecken lassen und die Pille etwas verkleinern (31px Schrift in einer Pille mit 22px/34px Padding ist sehr dominant und nimmt vertikalen Platz fuer Aufgaben weg).

### 4.2 Online/Offline-Zustand ist fast unsichtbar
Der Zustand zeigt sich nur am Globus-Icon in der (oft versteckten) Rail und kurz im Toast. Das Konzept sah die `airplane-pill` als persistenten Offline-Banner vor, das CSS liegt ungenutzt im Stylesheet.

**Vorschlag:** Offline-Pille im Hauptbereich (oder am Dock) anzeigen, sobald `online=false`. Spaeter (Phase 9) wird daraus der Sync-Status ("last sync 14:02").

### 4.3 Hardcodierte Farben statt Tokens
- `.focus-exit` nutzt `#e07a2c` (style.css:816), eine Farbe, die in keinem Token vorkommt und sich nicht mit dem gewaehlten Akzent aendert.
- Mehrfach hartes `#fff` (`.task.done .check`, `.btn-danger`), das bei hellen Akzenten okay ist, aber `--accent-ink` existiert genau dafuer.

**Vorschlag:** `--accent` bzw. `--danger`/`--accent-ink` verwenden. Sonst wirkt der Fokus-Exit-Knopf bei jedem Akzent ausser Terracotta wie ein Fremdkoerper.

### 4.4 Massive Inline-Styles in JS-Templates **[Sec]**
`renderAccentPop`, `renderModal` (status, rename, settings), `renderNotifMenu`, `renderProfileMenu` bauen ihr Layout ueber lange `style="…"`-Attribute zusammen. Folgen:
1. Theming/Dichte greifen dort nur zufaellig, Aenderungen muessen in JS-Strings gepflegt werden.
2. Die CSP braucht deswegen `style-src 'unsafe-inline'`. Wandern alle Inline-Styles in Klassen, kann die CSP auf `style-src 'self'` verschaerft werden, ein echter Defense-in-Depth-Gewinn passend zu den Gates.

**Vorschlag:** Alle `style="…"` aus den Templates in `style.css`-Klassen ueberfuehren (`.accent-pop`, `.status-row`, `.settings-row`, …), danach CSP verschaerfen. Einzige dynamische Ausnahmen (Swatch-Hintergrundfarbe, Dock-Dot) lassen sich ueber CSS-Custom-Properties pro Element loesen (`style="--c:#5a9d6b"` vermeiden, stattdessen `data-color` + vordefinierte Klassen, es sind ohnehin nur 6 Akzentfarben).

### 4.5 Sehr kleine Schriftgrade
- Sidebar-Zaehler: 8,5px (style.css:513), unter jeder Lesbarkeitsgrenze.
- `kbd`-Hinweis im New-Task-Feld: 10px; Tags: 10,5px; Meta: 10,5px.

**Vorschlag:** Nichts unter 10px; den Zaehler auf mindestens 10,5px anheben. Die Mono-Tags duerfen klein wirken, aber 8,5px ist auf 100%-Skalierung schon grenzwertig und auf High-DPI-Notebooks mit 125% gerade so okay, auf 100%-Desktops nicht.

### 4.6 Kontrast pruefen (WCAG)
Kandidaten, die im Light-Theme vermutlich unter AA (4,5:1) liegen:
- `--text-faint` `#9b8d75` auf `--bg` `#efe8db` und auf `--surface` `#faf6ee` (Meta-Texte, Zaehler, Empty-Notes).
- `--accent-ink` Weiss auf dem Gelb-Akzent `#d4a23c` und dem Gruen `#5a9d6b` (Buttons, aktive Zaehler).
- Placeholder in Akzentfarbe auf `--accent-wash`.

**Vorschlag:** Einmal systematisch mit einem Kontrast-Checker durchgehen. `--text-faint` ist fuer dekorative Linien okay, fuer echte Information (Zaehler, Meta, "due today") sollte mindestens `--text-dim` verwendet werden. Fuer helle Akzente eine dunkle `--accent-ink`-Variante pro Akzent definieren (das Token existiert schon, es ist nur konstant Weiss).

### 4.7 Theme: "System" fehlt
Es gibt nur Dark/Light manuell. `prefers-color-scheme` auszuwerten (Option "System" im Settings-Segment) ist billig und auf Windows 11 erwartetes Verhalten. Die Titelleisten-Logik in `main.py` kann den Wert mitgeliefert bekommen.

### 4.8 Scrollbars inkonsistent gestylt
`.main` und `.list-scroll` haben Custom-Scrollbars, `.mini-scroll` und `.focus-view` nicht: dort erscheint die Default-Scrollbar, im Mini-Fenster besonders auffaellig.

### 4.9 Toast-Verhalten
- Fixe 2,4 s fuer alles; Fehlermeldungen verdienen laengere Standzeit als Bestaetigungen.
- Kein Stapellimit: viele schnelle Aktionen tuermen Toasts unbegrenzt.
- Position `bottom: 92px` kollidiert im Mini-Modus (dort gibt es kein Dock, Toast haengt mitten im Fenster).

**Vorschlag:** Dauer nach Typ (Info 2,5 s, Fehler 5 s), maximal 3 sichtbare Toasts, Position im Mini-Modus auf `bottom: 16px`.

### 4.10 Dock-Eingabe: Enter-Hinweis fehlt
Die Fokus- und Mini-Eingaben zeigen das `↵`-Badge, die Dock-Eingabe (der Hauptweg!) nicht. Dort gibt es nur das X zum Schliessen. Kleiner Hinweis, grosse Wirkung fuer Erstnutzer.

### 4.11 Selektions- vs. Hover-Optik
`.task.selected` und `.list-item.active` nutzen bewusst dieselbe Optik (Akzentrahmen + Balken links). Gut. Aber der Unterschied zwischen "ausgewaehlt" (Klick) und "wird gerade bearbeitet" (`.editing`) ist schwach: editing hat nur `--accent-line`-Rahmen. Eine staerkere Differenzierung (z. B. editing mit gefuelltem Hintergrund) verhindert Verwirrung darueber, in welchem Modus die Karte gerade ist.

### 4.12 Sidebar-Toggle-Icon
Der Sidebar-Toggle nutzt das Plus-Icon, das sich bei offener Sidebar zum X dreht (style.css:465). Die Animation ist huebsch, aber ein Plus oben links liest sich als "etwas hinzufuegen", nicht als "Panel umschalten". Gleichzeitig nutzt das Dock dieselbe Plus-zu-X-Geste fuer "Task hinzufuegen", dieselbe Form bedeutet also zweierlei.

**Vorschlag:** Fuer den Sidebar-Toggle ein Panel-/Hamburger-Icon verwenden (Icons.Menu existiert bereits ungenutzt im Icon-Set) und die Drehanimation dem Dock-Plus vorbehalten.

---

## 5. Barrierefreiheit (A11y)

Aktuell ist die App fuer Tastatur- und Screenreader-Nutzung praktisch nicht zugaenglich. Da alles selbstgebaut ist (keine nativen Controls), muss die Semantik manuell ergaenzt werden.

### 5.1 Fokus-Sichtbarkeit
Es gibt keinerlei definierte `:focus-visible`-Stile. Wer mit Tab navigiert, sieht je nach WebView2-Default fast nichts. 

**Vorschlag:** Globaler Stil `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }`, bei runden Elementen (Check, Dock-Plus) per `border-radius` angepasst.

### 5.2 Semantik der Custom-Controls
- Task-Check ist ein `<button aria-label="toggle">`: nichtssagend. Besser `role="checkbox"`, `aria-checked`, `aria-label` mit dem Aufgabentext ("Mark 'Going Zero' as done").
- Task-Karten sind klickbare `<div>`s ohne Rolle und ohne `tabindex`, fuer Tastatur unerreichbar.
- Sidebar-Listen waeren als `role="listbox"`/`option` oder schlicht als `<nav>` mit `aria-current` sauber.
- Die Segment-Controls im Settings-Modal brauchen `role="radiogroup"`/`radio` + `aria-checked`.
- Collapse-Sektionskopf: `aria-expanded` fehlt.

### 5.3 Modals
Kein `role="dialog"`, kein `aria-modal="true"`, kein Fokus-Trap, kein initialer Fokus (ausser Rename), keine Fokus-Rueckgabe ans ausloesende Element nach dem Schliessen. Tab laeuft hinter dem Scrim weiter durch die App.

### 5.4 Live-Regionen
Toasts (`.toast-wrap`) brauchen `aria-live="polite"` (Fehler: `assertive`), sonst bekommt ein Screenreader von keinerlei Feedback etwas mit.

### 5.5 Bewegung reduzieren
Es gibt viele Animationen (Dock-Grow, Rail-Slide, Plus-Rotation, Modal-Rise), aber kein `@media (prefers-reduced-motion: reduce)`. Ein Block, der Transitions/Animations global verkuerzt, genuegt.

### 5.6 Zielgroessen
- Task-Check: 21px, unter den empfohlenen 24px (WCAG 2.5.8), bei `compact` besonders eng.
- `dock-close`: 24px, grenzwertig.
- `rail-pin`: 14px breit, sehr schwer zu treffen (und mit `opacity .3` auch schwer zu sehen).

**Vorschlag:** Klickflaechen per Padding/Pseudo-Element vergroessern, ohne die Optik zu aendern.

### 5.7 Tooltips
Die Rail-Tooltips sind reine Hover-CSS-Elemente: per Tastatur nie sichtbar, fuer Screenreader unsichtbar (der Button-Inhalt ist nur ein SVG). Mindestens `aria-label` pro Tool-Button.

---

## 6. Architektur-Themen mit direkter UX-Wirkung

### 6.1 Voll-Re-Render bei jeder Aktion
`render()` ersetzt bei fast jeder Interaktion das komplette `root.innerHTML`. Folgen, die man als Nutzer spuert:
- **Scrollposition geht verloren:** Wer in einer langen Liste unten einen Task abhakt, springt nach oben.
- Hover-Zustaende und CSS-Transitions brechen ab und starten neu (sichtbares Flackern bei Sektionen).
- Eingabefokus muss manuell restauriert werden (`refocusNewTask`-Mechanik), was fragil ist.

**Vorschlag (pragmatisch, kein Framework noetig):**
- Kurzfristig: Scrollposition von `.main` vor `render()` sichern und danach wiederherstellen; analog `.list-scroll`.
- Mittelfristig: gezielte Updates fuer die haeufigsten Pfade (Task toggeln, Task hinzufuegen, Auswahl wechseln) statt Voll-Render, die `applyChrome`/`applyRail`-Technik existiert ja schon als Vorbild.
- Im Zuge dessen die ohnehin geplante `textContent`-Umstellung (Gate, Phase 9) erledigen: DOM-Knoten bauen statt HTML-Strings, dann verschwinden `esc()`-Risiken und Voll-Render gemeinsam.

### 6.2 Kein Pending-/Loading-Zustand
Alle Bridge-Aufrufe laufen ohne visuelles Feedback. Lokal ist das schnell genug, aber ab Phase 8/9 (Login, Sync, Export-Dialog) braucht es ein Pattern: Button-Spinner, deaktivierte Aktionen waehrend laufender Operation, Sync-Indikator. Jetzt definieren, nicht erst, wenn der erste langsame Call da ist.

### 6.3 Boot-Fehlerbildschirm
`boot()` rendert bei Fehlern ein nacktes `<pre>boot error</pre>` (app.js:1092). Fuer den Fall "DB beschaedigt/gesperrt" sollte ein gestalteter Fehlerzustand mit Handlungsoption existieren (Retry, Pfadangabe, Hinweis auf Backup), gerade weil ab Phase 11 ein falsches Passwort bzw. eine defekte `.enc`-Datei reale Szenarien sind.

### 6.4 Doppelte Logik fuer Sidebar-Toggle
Der Code fuer "Sidebar umschalten" existiert zweimal nahezu identisch (Click-Handler app.js:919 und Hotkey app.js:995). In eine Funktion ziehen, sonst divergieren die Pfade bei der naechsten Aenderung (genau dort haengt auch der `N`-Bug aus 1.7).

---

## 7. Fehlende Produkt-Features (UX-Sicht, fuer die Roadmap)

Bewusst getrennt von den Maengeln: das hier sind Erweiterungen, keine Reparaturen.

1. **Faelligkeiten:** `due_at` existiert in Schema und `edit_task`-Whitelist, hat aber null UI. Minimal: Datum im Inline-Edit setzen, Anzeige als Meta-Badge, ueberfaellig in `--danger`. Das ist auch Voraussetzung dafuer, dass Phase 10 (Erinnerungen) etwas zum Erinnern hat.
2. **Suche/Filter:** Es gibt keinerlei Suche ueber Aufgaben oder Listen. Ein `Ctrl+F`-Overlay mit Fuzzy-Filter ueber alle Listen waere fuer eine Keyboard-orientierte App der groesste einzelne Produktivitaetsgewinn.
3. **Meta-Feld erklaeren oder strukturieren:** `meta` ist Freitext ohne Label oder Erklaerung (Placeholder "meta"). Entweder klar als freies Notiz-/Tag-Feld benennen ("note") oder in strukturierte Tags ueberfuehren.
4. **Aufgaben-Notizen/Details:** Aktuell ist eine Aufgabe genau eine Zeile. Eine ausklappbare Detailansicht (Beschreibung, Erstellt-Datum, Quelle local/graph) wuerde auch dem Graph-Import (Phase 9) einen Ort geben, importierte Felder anzuzeigen.
5. **"Heute"-/Smart-Ansicht:** Eine virtuelle Liste "Today/Overdue" ueber alle Listen hinweg, sobald due dates existieren.
6. **Settings-Vorbereitung fuer kommende Phasen:** Auto-Lock-Timeout (B.8 sagt "konfigurierbar, Default 15 min"), Screenshot-Schutz an/aus (der Code in `main.py` erwaehnt den Schalter explizit als geplant), Startverhalten (maximiert vs. letzte Groesse). Die Settings-Struktur (Zeilen + Segment) traegt das problemlos.
7. **Mini-Modus-Erweiterungen:** Listenwechsel (siehe 3.14), optional Transparenz/Kompaktheit.

---

## 8. Vorbereitung der Phasen 8 bis 11 aus UX-Sicht

Damit die Security-Phasen spaeter nicht mit Behelfs-UI landen, lohnt es sich, die Patterns jetzt zu entwerfen:

1. **Lock-Screen (Phase 11):** Der aktuelle "4x tippen"-Platzhalter muss durch ein echtes Passphrase-Feld ersetzt werden. Design-Anforderungen: Passwort-Feld mit Show/Hide, Fehlerzustand (falsche Passphrase: Shake + Meldung, keine Information ob Nutzer existiert), Hinweis bei Feststelltaste, Rate-Limit-Anzeige ("try again in 30 s"), und ein Zustand fuer "entsperre…" (Argon2id braucht spuerbar Zeit, das ist gewollt, also braucht es einen Fortschritt/Spinner). **[Sec]**
2. **Panic-Flow:** Heute Modal mit zwei Buttons. Fuer einen Panik-Knopf ist ein Bestaetigungs-Modal diskutabel, der Hotkey `Ctrl+Shift+!` sollte in der Zielversion ohne Rueckfrage sofort sperren (B.8), das Modal nur beim Maus-Klick auf den Rail-Button erscheinen. Jetzt schon so umsetzen, damit sich kein anderes Muskelgedaechtnis einschleift. **[Sec]**
3. **Sign-in/Sync (Phasen 8/9):** Profil- und Glockenmenue (siehe 1.3) als ehrliche leere Zustaende anlegen; Sync-Status (letzter Sync, Fehler) braucht einen festen Ort, am ehesten die Offline-/Status-Pille aus 4.2. Konflikt-Hinweis ("cloud overwrote 2 local edits") als Notification-Eintrag vorsehen.
4. **Status-Modal als ehrliches Security-Dashboard ausbauen** (siehe 1.4): aus `get_status()` gespeist, mit klarer Kennzeichnung, welche Schutzschicht aktiv ist. Das ist das Schaufenster der Security-Story. **[Sec]**

---

## 9. Priorisierte Uebersicht

**P1, vor allem weiteren Feinschliff (Ehrlichkeit + Datenverlust + tote Pfade):**
| # | Punkt | Abschnitt |
|---|---|---|
| 1 | Status-Modal/Toasts/Panic-Texte auf echte Werte umstellen | 1.4, 2.4 |
| 2 | Task-Loeschung: Bestaetigung oder Undo, toten Modal-Code aufloesen | 1.2, 3.3 |
| 3 | Listen loeschen ermoeglichen | 1.1 |
| 4 | Tote Menues (Glocke/Profil) entscheiden: einbauen oder entfernen | 1.3 |
| 5 | Export-Feedback ehrlich machen (bis Phase 7) | 1.5 |
| 6 | `N`-Hotkey bei geschlossener Sidebar reparieren | 1.7 |
| 7 | Scrollposition bei Re-Render erhalten | 6.1 |

**P2, naechster UX-Block:**
| # | Punkt | Abschnitt |
|---|---|---|
| 8 | Esc gestaffelt statt alles-auf-einmal | 3.1 |
| 9 | Hover-Aktionen auf Task-Karten (`.t-del`/Pencil) + Drag-Griff | 1.6, 3.4, 3.6 |
| 10 | Tastaturnavigation fuer Aufgaben (Pfeile, Space, F2, Entf) | 3.10 |
| 11 | Ctrl statt ⌘, Shortcuts-Modal vervollstaendigen, Sprachmix aufloesen | 2.1 bis 2.3 |
| 12 | Fokus-Stile, Modal-Semantik, aria-Labels, aria-live | 5.1 bis 5.4 |
| 13 | Listentitel im Hauptbereich, Offline-Pille | 4.1, 4.2 |
| 14 | Inline-Styles in CSS-Klassen ueberfuehren, danach CSP verschaerfen | 4.4 |
| 15 | Rail-Discoverability (Pin sichtbarer, Default gepinnt) + disabled-Optik | 3.13, 3.15 |

**P3, Politur und Ausbau:**
| # | Punkt | Abschnitt |
|---|---|---|
| 16 | Kontrast-Audit, Mindestschriftgroessen, Akzent-Ink pro Farbe | 4.5, 4.6 |
| 17 | Kontextmenue (Tasks + Listen), Move-to-list, Listen-Reorder | 3.5, 3.7, 3.9 |
| 18 | System-Theme, prefers-reduced-motion, Zielgroessen | 4.7, 5.5, 5.6 |
| 19 | Toast-Feinschliff, Scrollbars, Dock-Politur, Toggle-Icon | 4.8 bis 4.12 |
| 20 | Due dates, Suche, Clear completed, Mini-Listenwechsel | 7, 3.8, 3.14 |
| 21 | Lock-/Panic-/Sync-UX fuer Phasen 8 bis 11 vorentwerfen | 8 |

---

## 10. Was bereits gut ist (beibehalten)

Damit beim Aufraeumen nichts Gutes verloren geht:
- Das Design-System (warme Paper/Charcoal-Toene, Mono-Tags, Terminal-Grid) ist eigenstaendig und konsequent; die Token-Struktur mit `color-mix` ist modern und wartbar.
- Dichte-Umschaltung (`comfortable`/`compact`) ueber zwei Variablen ist vorbildlich schlank.
- Die Plus-zu-X-Rotation am Dock, das Sticky-Dock-Layout und die Collapse-Animation der Completed-Sektion (Grid-Rows-Trick) sind sauber geloest.
- Toast-Layer ausserhalb von `#root` (kein Fokusverlust durch Re-Render) ist die richtige Architekturentscheidung.
- Theme-Switch ohne Transition-Flackern (`theme-switching`-Klasse) und die DWM-Titelleisten-Anpassung in `main.py` zeigen Liebe zum Detail.
- Sidebar-Resize mit `data-resizing`-Attribut (Transition-Unterdrueckung) ist korrekt umgesetzt.
- Die Sicherheits-Disziplin im Frontend (zentrales `esc()`, CSP, keine Inline-Handler) ist fuer eine Vanilla-App ueberdurchschnittlich.
