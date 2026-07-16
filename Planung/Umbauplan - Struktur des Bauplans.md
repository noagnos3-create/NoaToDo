# Umbauplan: Struktur des Bauplans NoaToDo

> **Was dieses Dokument ist.** Ein reiner **Struktur-Umbauplan** fuer
> `Planung/Bauplan - NoaToDo.md`. Es beschreibt, **wie** man den Bauplan uebersichtlicher
> macht, indem die Nachtrag-Schichten (N10, N11.*) in den Haupttext eingearbeitet werden,
> und welche weiteren strukturellen Verbesserungen sich anbieten. Es ist selbst **keine**
> neue Fassung des Bauplans und aendert den Bauplan nicht; es ist die Anleitung fuer den
> spaeteren Umbau.

> **Eiserne Regel (steht bewusst ganz oben).** Beim Umbau aendert sich **inhaltlich
> nichts**, ausnahmslos. Keine Zusage, keine Zahl, kein Grenzwert, kein Gate, keine
> Begruendung, kein Datum, keine Befund-ID wird geaendert, gestrichen oder neu erfunden.
> Bewegt werden nur **Text an einen besseren Ort**, **Ueberschriften**, **Reihenfolge** und
> **Verweise**. Wo dieser Umbauplan von "Zusammenfuehren", "Verschieben" oder "Einarbeiten"
> spricht, ist immer **wortgleiches Umziehen** gemeint, nie Umformulieren. Der Bauplan ist
> inhaltlich ein fertiges Werk; hier wird nur seine Ablage aufgeraeumt.

---

## 0. Ausgangslage in einem Absatz

Der Bauplan ist inhaltlich vollstaendig und dicht, aber in **Schichten** gewachsen:
Urtext (Teil A bis D), der B.9-Sicherheits-Nachtrag, der UX-Nachtrag vom 2026-06-13
(N2 bis N10) und der grosse Nachtrag N11 (N11.1 bis N11.15.6). Am 2026-07-13 gab es einen
Konsolidierungs-Pass (Plananalyse S3): Seitdem **widerspricht** der Haupttext den
Nachtraegen nicht mehr, und es gilt die Redaktionsregel "neue Entscheidungen sofort in den
Haupttext, Nachtrag nur noch Aenderungsprotokoll". Dieser Pass hat den **Widerspruch**
beseitigt, aber **nicht** die eigentliche Heimat der Inhalte verschoben: Die verbindliche
Spezifikation vieler Kernthemen (teardown-Sequenz, config.json, Auto-Sperre, Rate-Limit,
Argon2-Parameter, Entsperr-Fehlerlogik, Onboarding, Verschluesselungs-Detailfassung) lebt
bis heute **ausschliesslich in den N11-Unterabschnitten** und wird vom Haupttext nur per
Zeiger referenziert. Genau das erzeugt die vom Nutzer beschriebene Unsicherheit. Dieser
Umbauplan holt diese Inhalte an ihren fachlichen Ort im Haupttext (Teil B / Teil C) und
laesst in den Nachtraegen nur noch das reine Aenderungsprotokoll zurueck, so wie es die
Redaktionsregel eigentlich schon vorsieht.

---

## 1. Warum der 2026-07-13-Pass nicht genuegt (praezise Diagnose)

Der bestehende Konsolidierungs-Stand behauptet zwei Dinge, von denen nur das erste real
eingeloest ist:

1. **"Der Haupttext widerspricht den Nachtraegen nicht mehr."** Stimmt. Das war die Arbeit
   der W-Fixes (W2 bis W18).
2. **"Nachtraege sind nur noch Aenderungsprotokoll."** Stimmt **nicht**. Sie sind weiterhin
   die einzige normative Heimat grosser Spezifikationsteile.

Der Beweis steht im Bauplan selbst. Die Leseanweisung im Kopf (Zeilen 18 bis 21) sagt
woertlich: **"Vor Beginn jeder Phase zuerst die Nachtraege N10 und N11 lesen ... Wer nur
von oben nach unten liest, hat die spaetesten Entscheidungen nie gesehen."** Ein Haupttext,
der wirklich alles enthielte, braeuchte diesen Satz nicht. Er steht da, weil der Haupttext
eben **nicht** selbsttragend ist.

Zweiter Beleg: Mehrere N11-Unterabschnitte tragen ein Entscheidungsdatum **nach** dem
2026-07-13 (z.B. N11.2.2, N11.4.2, N11.4.3, N11.11.5, N11.15.*, alle 2026-07-15) und sind
trotzdem als neue, tief verschachtelte Nachtrag-Bloecke angehaengt worden, statt an ihren
Vertrag im Haupttext zu wandern. Die Redaktionsregel wurde also seit ihrer Einfuehrung
faktisch nicht befolgt. Das ist kein Vorwurf an den Inhalt, sondern genau die mechanische
Luecke, die dieser Umbauplan schliesst.

### Die sieben strukturellen Befunde im Einzelnen

| Nr | Befund | Konkrete Belegstelle im Bauplan |
|---|---|---|
| D1 | **Spezifikation lebt in den Nachtraegen, nicht im Vertrag.** Kernthemen sind nur in N11.* normativ; der Haupttext zeigt per "Volltext in N11.x" dorthin. | teardown = N11.11; config.json = N11.15; Auto-Sperre/Inaktivitaet = N11.4.2; Rate-Limit = N11.4.1; Argon2-Parameter = N11.4.3; Entsperr-Fehlerlogik = N6; Verschluesselungs-Fassung = N11.9 |
| D2 | **Mehrere "einzige Wahrheiten", die im Kreis aufeinander zeigen.** B.2 (Fehlercodes), B.5 (Shortcuts), B.9 (Gates), N11.11 (Ausgaenge) sind je fuer sich "einzige Wahrheit", verweisen aber gegenseitig. Ein Leser muss fuer ein Thema durch 4 bis 8 Stellen springen. | "unlock" verteilt auf B.2, N4, N6, N11.4, N11.4.1, N11.4.3, N11.12 |
| D3 | **Gate-Mehrfachbuchfuehrung.** Ein Gate steht in bis zu vier Fassungen: B.9-Grundtabelle **oder** B.9-Nachtragstabelle (G13 bis G35), Phasen-Gateliste, Schnelluebersicht, B.10.6. Die Regel S1 ("bei Aenderung alle vier Stellen anfassen") ist selbst schon ein Struktur-Symptom. | zwei getrennte Gate-Tabellen in B.9; Wiederholung in Phase 7/8/9; Schnelluebersicht am Ende; B.10.6 |
| D4 | **Zwei kollidierende Leseregeln.** Kopf sagt "von oben nach unten" und zugleich "aber erst die Nachtraege am Ende lesen". Beides zusammen ist nicht ausfuehrbar. | Zeilen 16 bis 21 |
| D5 | **Tiefe und nicht-monotone Nummerierung.** Verschachtelung bis N11.11.5.4 und N11.15.6; **N11.2.2 steht physisch vor N11.2.1**; die Nachtrag-Zaehlung (N2, N4, N5 ... ohne N1/N3) bildet keine Logik mehr ab. | N11.2.2 bei Zeile 2317, N11.2.1 erst bei 2343 |
| D6 | **Spezifikation und Entscheidungshistorie sind im selben Block verschmolzen.** Jeder N11-Abschnitt mischt "was gilt" mit "warum, wann entschieden, welcher Befund". Das macht die Bloecke lang und den reinen Baupfad unlesbar. | jeder N11.*-Abschnitt beginnt mit "*Loest Ux ...*" gefolgt von der Norm |
| D7 | **Hinfaelliges und Durchgestrichenes liegt im Baupfad.** `ANHANG 1 [HINFAELLIG]` traegt noch die kompletten Seed-Daten; N7/N8/N9 enthalten `~~durchgestrichene~~` Passagen; Inline-Marker "[Gestrichen durch N11.10]". Als Historie ok, aber sie stehen mitten in der Bauanleitung. | ANHANG 1; N7 "Clear completed"; N8; N9; N10.1 Klammer |

---

## 2. Leitprinzipien des Umbaus

Fuenf Prinzipien; sie sind der Massstab fuer jede Einzelentscheidung weiter unten.

- **P1, Inhalts-Erhaltung ueber alles.** Jeder normative Satz zieht **wortgleich** um.
  Geaendert werden duerfen nur Ueberschrift, Position und die verbindenden Verweis-Saetze
  ("siehe N11.x" wird zu "siehe B.8.4" oder entfaellt, wenn der Inhalt nun daneben steht).
- **P2, ein Fakt, ein Zuhause.** Jede verbindliche Aussage hat **genau einen** normativen
  Ort (ihren Vertrag in Teil B oder ihre Phase in Teil C). Alle anderen Stellen verweisen
  nur dorthin und wiederholen den Wortlaut nicht.
- **P3, Spezifikation und Register trennen.** Ein Abschnitt sagt entweder, **was gilt**
  (Vertrag/Phase), oder **wann/warum es entschieden wurde** (Entscheidungsregister). Nie
  beides vermischt. Das ist die Redaktionsregel des Bauplans, nur konsequent zu Ende
  gefuehrt.
- **P4, IDs sind unveraenderliche Etiketten, keine Kapitelnummern.** `N11.4.3`, `G35`,
  `U17`, `V1` und die uebrigen Kuerzel bleiben **stabil** und wandern als Etikett mit ihrem
  Inhalt mit. So bricht **kein** bestehender Verweis (Code-Kommentare, CLAUDE.md,
  Plananalyse zitieren diese IDs). Details in Abschnitt 4.
- **P5, ein Pass, review-bar.** Der Umbau laeuft in klar getrennten Etappen auf einem
  eigenen Branch, jede Etappe fuer sich pruefbar (Abschnitt 6). Kein "grosser Wurf" in
  einem Rutsch.

---

## 3. Zielstruktur

Das Zielskelett behaelt Teil A bis D bei und macht Teil B (die Vertraege) zur
**vollstaendigen** normativen Heimat. Neu bzw. ausgebaut:

```
TEIL A  Gesamtbild                     (fast unveraendert)
        A.4  Global gestrichene Features   <- NEU: die eine Streich-Liste (aus N11.1)
        A.5  Sprach- und Plattform-Basis   <- aus dem Kopf des UX-Nachtrags (EN, Windows-only)

TEIL B  Vertraege (verbindlich, VOLLSTAENDIG, selbsttragend)
        B.1  Datenmodell               <- + Positions-Invariante (schon da), Meta-Streichung
        B.2  Bridge-API                <- + Onboarding-/Vault-Methoden (N11.13),
                                          Entsperr-Fehlerlogik (N6), config-Bezug
        B.3  Design-Tokens             (unveraendert)
        B.4  UI-Aufbau + Screens       <- + Onboarding-Screens, Lock-/Fehlerbildschirm-UX
        B.5  Tastenkuerzel             (bereits einzige Wahrheit; bleibt)
        B.6  Einstellungen             <- + theme/sound/autoLock, Whitelist (N11.6/N11.7)
        B.7  Verschluesselung          <- + beide Schichten (N11.9), Argon2-Parameter (N11.4.3)
        B.8  Sperr-, Auto-Sperr- und Beenden-Politik   <- GROSSER SAMMELPUNKT, siehe unten
        B.9  Sicherheits-Gates         <- EINE zusammengefuehrte Gate-Tabelle
        B.10 Bedrohungsmodell          (bereits gut; bleibt)
        B.11 Unverschluesselte Konfiguration (config.json)   <- NEU aus N11.15

TEIL C  Baufolge Phase 0 bis 9         <- jede Phase verweist nur noch auf ihre B-Vertraege
        Phase 8 behaelt die reinen Phasen-Prozeduren (z.B. den Zweitprofil-Spike N11.8.3)

TEIL D  Roadmap / spaetere Erweiterungen   <- + N8-Reste

ANHANG  1  Entscheidungsregister       <- NEU: N10 + N11 als reines Protokoll (Tabelle)
        2  Audit-Status (Triage)       <- N11.14 hierher (Status eines Fremd-Dokuments)
        3  Historie / hinfaellige Staende  <- ANHANG 1 alt (Seed), durchgestrichene Reste
        4  Icon-Set                    (unveraendert)
```

Die neue Unterstruktur von **B.8** ist das Herzstueck des Umbaus, weil sich hier die
meisten verstreuten Nachtraege sammeln:

```
B.8  Sperr-, Auto-Sperr- und Beenden-Politik
     B.8.1  Was sperrt, was nicht                (B.8-Tabelle + N11.8.4 Win+L)
     B.8.2  Verstaerkte Sperre / Raum-Bereinigung (N10.1, ohne Offline: N11.10)
     B.8.3  Auto-Sperre: Definition der Inaktivitaet (N11.4.2)
     B.8.4  Entsperr-Rate-Limit und seine Persistenz (N11.4, N11.4.1)
     B.8.5  Die gemeinsame teardown(reason)-Sequenz (N11.11 inkl. Tabelle N11.11.3)
     B.8.6  Native Dialoge und die aufgeteilte Auto-Sperre (N11.11.5)
     B.8.7  Killswitch und Reset als Datei-Operation (N11.8.1, Bezug N11.13)
```

Ergebnis: Wer Phase 8 baut, liest **B.7, B.8, B.11 und die Gate-Tabelle** und hat alles.
Der Satz "vorher die Nachtraege lesen" entfaellt, weil es keine nachgelagerte Norm mehr
gibt.

---

## 4. Der Schluesseltrick: IDs von Kapitelnummern entkoppeln

Das groesste Risiko beim Umziehen von Inhalten ist, **Verweise zu brechen**. Der Code, die
CLAUDE.md und die Plananalyse zitieren ueberall feste IDs (`N11.11.2`, `G35`, `U5`, `V1`,
`A3`). Wuerde man beim Aufraeumen umnummerieren, braechen Dutzende Verweise auf einmal.

Loesung: **Die IDs bleiben, ihr Text zieht um.** Eine ID wie `N11.4.3` ist ab dem Umbau
kein Kapitel mehr, sondern das **Etikett einer Entscheidung**. Der Inhalt von N11.4.3 (die
Argon2-Parameter) steht dann in **B.7**, dort mit dem Etikett markiert:

> "Fest verdrahtete Argon2id-Parameter (Entscheid **U17 / N11.4.3**, 2026-07-15): ..."

Und im Entscheidungsregister (Anhang 1) steht die Zeile:

> `U17 / N11.4.3 | 2026-07-15 | Argon2id-Parameter fest verdrahtet + MemoryError-Randfall | Norm jetzt in B.7`

So gilt:

- **Jeder bestehende Verweis auf `N11.4.3` bleibt aufloesbar** (das Register fuehrt die ID
  und zeigt auf ihren neuen Ort). Kein Code-Kommentar, keine CLAUDE.md-Zeile bricht.
- Die **physische** Reihenfolge im Register kann monoton und sauber sein, ohne dass das die
  Verweise beruehrt (Befund D5 ist damit ohne Umnummerieren erledigt).
- Wer kuenftig "N11.2.2" sucht, findet die Registerzeile und von dort die Norm in ihrem
  Vertrag.

**Regel:** Beim Umbau wird **keine** bestehende ID veraendert oder recycelt. Neue
Entscheidungen bekommen die naechste freie Nummer in derselben Systematik und tragen ihren
Inhalt sofort in den Vertrag ein (nicht in einen neuen Nachtrag-Block).

---

## 5. Migrationskarte (was zieht wohin)

Die folgende Tabelle ist die eigentliche Arbeitsliste. **Spalte "Norm nach"** = wohin der
verbindliche Wortlaut wandert. **Spalte "Register"** = die ID/Datum/Begruendung-Zeile, die
im Entscheidungsregister (Anhang 1) verbleibt. Nichts wird geloescht: Was nicht Norm ist,
wird Register; was historisch ist, wird Anhang 3.

### 5a. UX-Nachtrag 2026-06-13 (Kopf, N2 bis N10)

| Block | Inhalt (Kurz) | Norm nach | Register / Anhang |
|---|---|---|---|
| Kopf: Sprach-/Plattform-Entscheid | UI durchgehend Englisch, nur Windows, keine Mac-Symbole | **A.5** (neu) | Datum 2026-06-13 |
| Kopf: "Was bereits im Plan steht" | reine Querverweisliste | entfaellt (Verweise loesen sich im Zielbau auf) | Anhang 3 (Historie) |
| N2 | persistente Offline-Statuspille | **B.4** (Main/Banner) als optionaler UX-Ausbau | ID N2 |
| N4 | echter Lock-Screen mit Passphrase-UX | **B.4** (LockScreen) + Verweis Phase 8 | ID N4 |
| N5 | Panik nur per Maus, kein Hotkey | schon in **B.5** verankert; Wortlaut dort belassen | ID N5 (Entscheid W5) |
| N6 | Entsperr-/Boot-Fehlerbildschirm + **entscheidbare Fehlerlogik** | **B.2** (unlock-Vertrag) + **B.4** (Fehlerbildschirm) | ID N6 (Entscheid U7) |
| N7 | move_task, reorder_lists | **B.2** + **Phase 7**; "Clear completed" gestrichen | ID N7; Streichung nach A.4 |
| N8 | Roadmap-Ideen | **Teil D** | ID N8 |
| N9 | Startverhalten-Setting (durch N11.6 ueberholt) | entfaellt als Norm | Anhang 3 (ueberholt) |
| N10.1 | verstaerkte Sperre ("Panik light") | **B.8.2** (ohne Offline, N11.10) | ID N10; Offline-Streichung = W1 |
| N10.2 | Off-Knopf im Lock-Screen | **B.4** (LockScreen) + **B.8.5** | ID N10 |
| N10.3 | Panik-Endschirm + Killswitch | **B.4** (PanicPanel) + **B.8.7** | ID N10; Aussage-Abwaegung bleibt B.10.5 |
| N10.4 | Verhalten nach Killswitch | **B.8.7** (Datei-Op, N11.8.1) | ID N10 |
| N10.5 | Bridge-Erweiterung quit_app/killswitch | schon in **B.2**; belassen | ID N10 |

### 5b. Nachtrag N11

| Block | Inhalt (Kurz) | Norm nach | Register / Anhang |
|---|---|---|---|
| N11.1.1 bis N11.1.6 | ersatzlos gestrichene Features (Benachrichtigungen, Backups, Meta, Seed, JSON-Export, Faelligkeiten) | **A.4** (eine gebuendelte Streich-Liste) + je ein Einzeiler am fachlichen Ort (B.1 Meta, B.2 Export, Phase 1 Seed) | IDs N11.1.x, W15 |
| N11.2 | zweistufiger Export, Undo nur Listen | **Phase 7** + **B.2** | ID N11.2 |
| N11.2.1 | Undo-Architektur (RAM-Puffer, kein Soft-Delete) | **B.2** (undo_delete_list) + **Phase 7** | ID N11.2.1 (Entscheid U9) |
| N11.2.2 | Randfaelle reorder/reorder_lists/move_task | **B.2** bzw. Validierungsvertrag bei **G20** | ID N11.2.2 (Entscheid U11) |
| N11.3 | Ersteinrichtung, Passphrase-Regel, Reset, Passphrase-Wechsel (a bis d) | **B.2** (create_vault/change_passphrase/reset_vault) + **B.4** (Onboarding) + **B.7** (KDF-Upgrade) | ID N11.3 (Entscheid U8) |
| N11.4 | Auto-Sperre-Default, Rate-Limit-Leiter | **B.8.3 / B.8.4** | ID N11.4 |
| N11.4.1 | Rate-Limit persistiert | **B.8.4** + **B.11** (config-Feld) | ID N11.4.1 (Entscheid U6) |
| N11.4.2 | Definition "Inaktivitaet" | **B.8.3** | ID N11.4.2 (Entscheid U4) |
| N11.4.3 | Argon2-Parameter + MemoryError | **B.7** + **B.2** (Code `memory`) | ID N11.4.3 (Entscheid U17) |
| N11.5 | echter Flugmodus, set_online-Vertrag, get_wifi_signal-Kadenz | **B.2** (set_online/get_wifi_signal) + **B.4** + **Phase 0** (Abhaengigkeiten) | IDs N11.5, U14, U15 |
| N11.6 | Theme folgt Windows, Header, Fenster maximiert, Ton, Mini-Bounds | **B.6** (theme/sound) + **B.4** (Header/Fenster) + **B.5** (Ctrl+J) | IDs N11.6, U16, U24 |
| N11.7 | Settings-Whitelist, Roadmap-Folgen | **B.6** + Gate **G20** | ID N11.7 |
| N11.8.1 | Killswitch = Datei-Operation | **B.8.7** | ID N11.8.1 |
| N11.8.2 | Start-Weiche (Existenz tasks.db.enc) | **B.2** (get_boot_state) | ID N11.8.2 |
| N11.8.3 | Zweitprofil-Spike, 9 Fragen, nativer Fallback | **Phase 8** (reine Phasen-Prozedur, bleibt dort) | ID N11.8.3 (Entscheid U3) |
| N11.8.4 | Win+L loest keine Sperre aus | **B.8.1** | ID N11.8.4 |
| N11.9 | beide Verschluesselungs-Schichten, Arbeitskopie, Write-back identisch | **B.7** | ID N11.9 (Gate G28) |
| N11.10 | Sperre schaltet nicht mehr offline | **B.8.2** + **B.5** (set_online) | ID N11.10 (Entscheid W1) |
| N11.11 (.1 bis .4) | teardown(reason): eine Funktion, Soll-Sequenz, Schritt-Tabelle, Gate G35 | **B.8.5** (komplett, inkl. Sequenz-Tabelle) | ID N11.11 (Entscheid S5) |
| N11.11.5 (.1 bis .4) | native Dialoge, aufgeteilte Auto-Sperre | **B.8.6** | ID N11.11.5 (Entscheid U5) |
| N11.12 (.1 bis .3) | Fehler-Hygiene, Ringpuffer, Logging-Politik, Gate G29 | **B.2** (Fehlerkonvention, groesstenteils schon da) + kurze Logging-Regel in **B.9/Phase 9** | ID N11.12 (Entscheid S6) |
| N11.13 | Onboarding-Bridge, dreiwertiger Boot-Zustand | **B.2** + **B.4** (beides schon dort verankert) | ID N11.13 (Entscheid U1) |
| N11.14 | Triage des UX/UI-Audits | **Anhang 2** (Status eines Fremd-Dokuments, gehoert nicht in den Baupfad) | ID N11.14 (Entscheid S7) |
| N11.15 (.1 bis .6) | config.json-Schema, Fehlerfaelle, unerreichbarer Tresor, Redirect, Ueberschreib-Schutz | **B.11** (neu, komplett) | ID N11.15 (Entscheid U2), V8 |

> **Lesehilfe zur Tabelle.** "Norm nach" ist der neue, einzige normative Ort. Wo bereits
> heute die Norm im Haupttext steht (z.B. N11.13 in B.2/B.4), heisst der Umbau nur:
> **Register-Zeile ziehen**, den erklaerenden N11-Block auf das Protokoll eindampfen. Wo
> die Norm heute **nur** im Nachtrag steht (z.B. N11.11, N11.15, N11.4.*), heisst der
> Umbau: **Wortlaut in den Vertrag umziehen**, Etikett dranlassen, Register-Zeile
> hinterlassen.

---

## 6. Gate-Konsolidierung (Befund D3)

Getrennt behandelt, weil es zwei Stufen hat.

**Etappe Gate-1 (einfach, hoher Nutzen): die zwei Tabellen in B.9 zu einer machen.**
Heute stehen die Gates in **zwei** Tabellen (Grundset G6 bis G12, dann "Nachtrag G13 bis
G35"). Historisch nachvollziehbar, sachlich unnoetig. Zusammenfuehren zu **einer** nach
Gate-Nummer sortierten Tabelle mit den bestehenden Spalten (Gate, Phase, Status, Stand,
Pruefweg, Punkt). Rein strukturell, kein Wort aendert sich. Die Einleitungstexte der beiden
Tabellen (die Historie, wann welches Gate kam) wandern als ein Absatz ins
Entscheidungsregister.

**Etappe Gate-2 (optional, groesserer Schnitt): Gate-Zeile = Tracker, Definition = Vertrag.**
Der Bauplan kennt das Muster bereits ("Volltext-Anker", z.B. G28 zeigt auf N11.9). Heute
ist es aber uneinheitlich: G13, G14, G16, G20, G21, G34 tragen ihren kompletten Volltext
**in der Gate-Zeile**, andere zeigen nach aussen. Vereinheitlichen auf: **jede** Gate-Zeile
enthaelt Nummer, Phase, Status, Stand, Pruefweg und einen **Kurz-Punkt plus Volltext-Anker**
in den zustaendigen Vertrag/die Phase. Die langen Inline-Bloecke (G13 nach B.8.5/B.2, G14
nach B.8.5, G20/G21 nach B.2 bzw. Phase 7) ziehen wortgleich dorthin. Danach gilt sauber:

- **B.9 verfolgt** Gates (Status, Termin, Pruefweg).
- **Der Vertrag/die Phase definiert** den Inhalt.

Damit verschwindet die "Mehrfachbuchfuehrung" aus S1 fast von selbst: Die Phasen-Gatelisten
und die Schnelluebersicht bleiben bewusst **nicht-normativ** (nur Nummer plus Stichwort plus
Verweis), und es gibt nur noch **einen** Ort, an dem sich Gate-Inhalt aendert (der Vertrag)
und **einen**, an dem sich Gate-Status aendert (B.9). Die S1-Redaktionsregel schrumpft von
"vier Stellen" auf "zwei".

> Etappe Gate-2 ist invasiver; sie steht bewusst **nach** der Nachtrag-Einarbeitung
> (Abschnitt 7, Etappe 3), damit jede Etappe klein und pruefbar bleibt. Wer knapp bei Zeit
> ist, macht nur Gate-1; schon das nimmt viel Dichte raus.

---

## 7. Ausfuehrung in Etappen

Jede Etappe ist ein eigener, reviewbarer Schritt auf einem Branch. Reihenfolge bewusst so,
dass die riskanten Umzuege (Norm verschieben) zuletzt kommen und auf einer schon
aufgeraeumten Ablage sitzen.

- **Etappe 0, Sicherung und Kartierung.** Den Ist-Bauplan als Referenz einfrieren (Kopie
  oder Commit-Tag). Die Migrationskarte (Abschnitt 5) in eine Checkliste ueberfuehren: eine
  Zeile pro Nachtrag-Block, Haken erst, wenn Norm umgezogen **und** Register-Zeile
  geschrieben ist. Kein Wort wird hier veraendert.
- **Etappe 1, Geruest ohne Umzug.** Die neuen leeren Huellen anlegen: A.4, A.5, die
  B.8-Unterstruktur (B.8.1 bis B.8.7), B.11, Anhang 1 (Register), Anhang 2 (Audit-Status),
  Anhang 3 (Historie). Noch **kein** Inhalt verschoben. Damit ist die Zielablage sichtbar,
  bevor irgendetwas wandert. **Erledigt 2026-07-16:** alle Huellen angelegt (jeweils mit
  Zeiger auf den heutigen normativen Ort und die fuellende Etappe); zur
  Kollisionsvermeidung wurden die Alt-Anhaenge gemaess Zielskelett umbenannt (Seed nach
  "ANHANG 1 alt", Icon-Set nach "ANHANG 4") und die drei Verweise darauf umgebogen
  (Phase 1 Punkt 4, N11.1 Punkt 4, B.4-Icons-Zeile); die B.8-Ueberschrift traegt den
  Zielnamen. Kein Inhalt verschoben, verify_umbau.py gruen.
- **Etappe 2, Gate-1.** Die zwei B.9-Tabellen zu einer zusammenfuehren (nur Umstellen,
  kein Wort). Ergebnis einmal prueft: Gate-Anzahl vorher/nachher gleich, jede
  Gate-Nummer genau einmal vorhanden.
- **Etappe 3, Norm-Umzug nach Migrationskarte.** Block fuer Block aus Abschnitt 5
  abarbeiten. Pro Block: (a) normativen Wortlaut in den Zielvertrag **ausschneiden und
  einfuegen**, Etikett (ID) dranlassen; (b) im Nachtrag-Block nur noch die Protokollzeile
  fuer Anhang 1 zuruecklassen; (c) Checklisten-Haken. **Reihenfolge innerhalb der Etappe:**
  erst die Bloecke, deren Norm heute schon im Haupttext steht (nur Register ziehen: N11.13,
  N5, N11.10, Teile N11.12), dann die reinen Umzuege (N11.11, N11.15, N11.4.*, N6, N11.9).
  So gewoehnt man sich am risikoarmen Teil die Mechanik an.
- **Etappe 4, Leseregel und Zeiger.** Den Kopf-Satz "vorher die Nachtraege lesen" streichen
  (der Haupttext ist jetzt selbsttragend) und die "von oben nach unten"-Regel wieder allein
  gelten lassen. Alle "siehe N11.x"-Zeiger im Dokument auf die neuen Vertrags-Orte
  umbiegen; Zeiger, die jetzt neben ihrem Inhalt stehen, entfallen.
- **Etappe 5, Historie einraeumen.** ANHANG 1 alt (Seed) und alle `~~durchgestrichenen~~`
  bzw. "[Ueberholt/Gestrichen durch ...]"-Reste nach **Anhang 3** verschieben. Der Baupfad
  (Teil A bis C) enthaelt danach keine hinfaelligen Passagen mehr, nur noch Verweise ins
  Register/Anhang 3.
- **Etappe 6 (optional), Gate-2.** Gate-Volltexte aus den langen B.9-Zeilen in ihre
  Vertraege ziehen (Abschnitt 6). Nur wenn Zeit; klar getrennt vom Rest.
- **Etappe 7, Abnahme.** Abschnitt 9 durchpruefen. Dann CLAUDE.md dort nachziehen, wo sie
  auf Struktur zeigt (nicht auf IDs, die bleiben ja): die "Bridge API"-Tabelle und die
  Abschnitts-Namen. Inhaltlich aendert sich auch in CLAUDE.md nichts.

---

## 8. Das Entscheidungsregister (Anhang 1)

Der Zielzustand der Nachtraege ist **eine Tabelle**, die genau das tut, was die
Redaktionsregel verlangt: protokollieren, nicht spezifizieren. Vorschlag fuer die Spalten:

| Spalte | Inhalt |
|---|---|
| ID | die stabile Etikett-ID (`N11.4.3`, `U17`, `G35`, `W1`, `V1`, `A3` ...) |
| Datum | Entscheidungsdatum (unveraendert uebernommen) |
| Thema | ein Satz, woertlich aus dem bisherigen "*Loest Ux*"-Vorspann |
| Norm jetzt in | Zeiger auf den Vertrag/die Phase (z.B. "B.8.5") |

Die **Begruendung** (das "warum", die ehrliche Einordnung, die Angriffsvektor-Diskussion)
ist selbst Inhalt und darf nicht verloren gehen. Zwei zulaessige Ablagen, je nach Charakter:

- Ist die Begruendung **normativ** (sie schraenkt ein, was gebaut werden darf, z.B. "256
  MiB und nicht 512, weil Verfuegbarkeit als Sicherheitsziel zaehlt"), wandert sie **mit
  dem Inhalt in den Vertrag** (als "Begruendung"-Absatz oder Zitatblock, wortgleich).
- Ist die Begruendung reine **Historie** ("*Loest U11 der Plananalyse: es war offen,
  was bei ...*"), wandert sie ins Register (Spalte Thema) bzw. nach Anhang 3.

Faustregel: Wenn das Loeschen des Satzes eine Bau-Entscheidung offenlassen wuerde, ist er
Norm und bleibt im Vertrag. Wenn er nur erklaert, warum frueher etwas anders war, ist er
Historie.

---

## 9. Inhalts-Erhaltung: Garantien und Pruefung

Weil "es aendert sich inhaltlich nichts" die Kernbedingung ist, hier die konkreten
Schutzmechanismen, mit denen sich das **belegen** laesst.

- **G-Erhalt-1, Vollstaendigkeitsliste.** Die Checkliste aus Etappe 0 hat eine Zeile pro
  Nachtrag-Block. Der Umbau ist erst fertig, wenn jede Zeile abgehakt ist (Norm umgezogen
  **und** Registerzeile geschrieben). Kein Block darf "verdunsten".
- **G-Erhalt-2, ID-Erreichbarkeit.** Jede ID, die heute im Dokument, im Code oder in
  CLAUDE.md vorkommt, muss nach dem Umbau ueber das Register auf genau einen Ort aufloesen.
  Pruefung: die Menge der IDs vorher (Grep ueber `N\d`, `G\d`, `U\d`, `W\d`, `V\d`, `S\d`,
  `A\d`) gleich der Menge im Register nachher.
- **G-Erhalt-3, Zahlen- und Grenzwert-Inventar.** Vor dem Umbau die harten Werte
  auflisten (12 Zeichen Passphrase, 256 MiB / time_cost 3 / parallelism 4 / hash_len 32,
  Akzeptanzbereich 64 bis 512 MiB, Leiter 10 s / 30 s / 1 min / 5 min / 15 min / 30 min /
  1 h / 5 h / 10 h, 3 Freiversuche, 2 s Pause, 2 Versuche je Stufe, 4096/256 Zeichen,
  Ringpuffer 50, DAMAGE_HINT_AFTER 5, sidebarWidth 180 bis 520, autoLock {0,1,5,15,30,60},
  Debounce 3 s / Kappe 30 s, Clipboard 60 s, `NOA1`, Nonce 12 Byte, Salt 16 Byte,
  `.bak` eine Generation). Nach dem Umbau dieselbe Liste erneut ziehen: identisch, sonst
  Fehler.
- **G-Erhalt-4, Wort-Diff auf Norm-Ebene.** Da nur umgezogen wird, muss ein normalisiertes
  Wort-Inventar (Ueberschriften, Zeiger und Whitespace herausgerechnet) vorher und nachher
  praktisch deckungsgleich sein. Abweichungen sind entweder ein Fehler oder ein bewusst als
  Historie nach Anhang 3 verschobener Block; beides muss man einzeln benennen koennen.
- **G-Erhalt-5, Gate-Zaehlung.** Anzahl der Gates und ihre Nummern vorher gleich nachher
  (relevant fuer Etappe 2/6).
- **G-Erhalt-6, Vier-Augen auf die riskanten Bloecke.** N11.11 (teardown-Sequenz und ihre
  Schritt-Tabelle), N11.15 (config-Schema) und N6 (Entsperr-Fehlerlogik) sind die dichten,
  reihenfolge-sensiblen Bloecke; ihr Umzug wird gesondert gegengelesen, weil dort die
  **Reihenfolge** selbst normativ ist (Schritt 7 nie vor 5/6, Schritt 10 immer zuletzt).

---

## 10. Risiken und ausdrueckliche Nicht-Ziele

- **Nicht-Ziel: irgendeine Entscheidung "verbessern".** Auffaellt beim Umziehen etwas, das
  fachlich fragwuerdig wirkt, wird es **nicht** hier geaendert, sondern als Befund in die
  Plananalyse gemeldet und dort nach dem ueblichen Weg entschieden. Der Umbau bleibt rein
  strukturell (P1).
- **Nicht-Ziel: IDs umnummerieren.** Siehe Abschnitt 4. Das Aufraeumen der Nummerierung
  (D5) geschieht ueber die **physische** Registerreihenfolge, nie ueber neue IDs.
- **Risiko: gebrochene Verweise.** Gemindert durch P4 (IDs bleiben) und G-Erhalt-2. Der
  einzige Ort, an dem sich Verweise aendern, sind die "siehe N11.x"-Wegweiser **innerhalb**
  des Bauplans; die werden in Etappe 4 systematisch umgebogen.
- **Risiko: CLAUDE.md und Code driften.** CLAUDE.md spiegelt Teile des Plans. Sie zeigt
  aber ueberwiegend auf **IDs** (die bleiben) und auf grobe Abschnitts-Namen. Etappe 7
  zieht nur die Struktur-Verweise nach; kein inhaltlicher Eingriff.
- **Risiko: Begruendungs-Verlust.** Der subtilste Fehler waere, eine als "Historie"
  eingestufte Begruendung wegzuwerfen, die in Wahrheit normativ war (z.B. "256 statt 512
  MiB, weil ..."). Deshalb Abschnitt 8 mit der Faustregel und G-Erhalt-6.
- **Risiko: halber Umbau.** Bleibt der Umbau in der Mitte stehen, hat man kurzzeitig zwei
  Heimaten fuer einen Fakt. Deshalb die Etappen klein und die Checkliste bindend: ein Block
  ist entweder ganz umgezogen oder gar nicht angefasst.

---

## 11. Vorher/Nachher an einem Beispiel (Thema "Entsperren")

Damit der Nutzen greifbar ist, das dichteste Beispiel. **Heute** muss man fuer die
vollstaendige Regel des Entsperrens acht Stellen zusammensuchen:

- B.2, Zeile `unlock()` (Grobvertrag),
- N4 (Lock-Screen-UX, Spinner, Caps-Lock),
- N6 (entscheidbare Fehlerlogik: fehlt/unlesbar/AEAD, Rueckgabeformat, .bak-Regel,
  DAMAGE_HINT_AFTER),
- N11.4 (Rate-Limit-Leiter),
- N11.4.1 (Persistenz der Leiter, Uhren, persist-before-verify),
- N11.4.3 (Argon2-Parameter, MemoryError, Code `memory`),
- N11.12 (Fehlercode-Katalog, kein `str(exc)`),
- B.2-Fehlercode-Tabelle (Codes `passphrase`/`rate_limited`/`vault`/`memory`).

**Nachher** steht die Entsperr-Regel an genau einem Vertrag: **B.2 `unlock()`** haelt den
Ablauf und die Fehlerlogik (aus N6), verweist fuer die Kosten auf **B.7** (Argon2, aus
N11.4.3), fuer die Leiter auf **B.8.4** (aus N11.4/N11.4.1) und fuer die UX auf **B.4**
(aus N4). Vier benachbarte Vertrags-Orte statt acht ueber das Dokument verstreute Bloecke;
jede Regel steht dort, wo man sie beim Bauen sucht, und jede traegt weiter ihr Etikett
(N6, N11.4.1, U17 ...), sodass jeder Alt-Verweis aufloesbar bleibt.

---

## 12. Abnahme (Definition of Done)

Der Umbau gilt als fertig, wenn **alle** folgenden Punkte zutreffen:

- [ ] Teil A bis C ist **selbsttragend**: kein "Volltext in N11.x", keine Norm liegt mehr
      ausschliesslich in einem Nachtrag-Block.
- [ ] Der Kopf-Hinweis "vorher die Nachtraege lesen" ist entfernt; es gilt nur noch "von
      oben nach unten".
- [ ] Jede N10-/N11-ID hat eine Zeile im **Entscheidungsregister (Anhang 1)** mit Zeiger
      auf ihren normativen Ort.
- [ ] B.9 hat **eine** Gate-Tabelle; jede Gate-Nummer kommt genau einmal vor; Zahl und
      Nummern gleich wie vorher (G-Erhalt-5).
- [ ] B.8 traegt die vollstaendige Sperr-/Auto-Sperr-/Beenden-Politik (inkl. teardown-
      Sequenztabelle und Dialog-Regel); B.11 traegt das vollstaendige config.json-Schema.
- [ ] Zahlen-/Grenzwert-Inventar vorher = nachher (G-Erhalt-3); ID-Menge vorher = nachher
      (G-Erhalt-2).
- [ ] Hinfaelliges (Seed, durchgestrichene Reste) liegt gebuendelt in **Anhang 3**, nicht
      mehr im Baupfad.
- [ ] CLAUDE.md-Struktur-Verweise nachgezogen; **kein** inhaltlicher Eingriff dort.
- [ ] Ein Gegenleser bestaetigt fuer N11.11, N11.15 und N6, dass die **Reihenfolge** der
      Schritte unveraendert ist (G-Erhalt-6).

Wenn diese Liste steht, ist der Bauplan so uebersichtlich wie moeglich, **ohne dass sich
ein einziger Fachinhalt geaendert hat**, und die Redaktionsregel des Plans ist zum ersten
Mal wirklich eingeloest: neue Entscheidung sofort in den Vertrag, Nachtrag nur noch
Protokoll.

---

## Anhang A: Etappe-0-Arbeitscheckliste (Baseline + Blockliste)

Konkrete, abhakbare Fassung von Etappe 0. Die Baseline-Inventare sind bereits mit den
echten Ist-Werten aus dem Bauplan gefuellt (Stand des Umbauplan-Commits), damit man nach
dem Umbau exakt dagegen pruefen kann.

### A.0 Sicherung

- [x] Ist-Bauplan als Referenz einfrieren (Commit-Tag oder Kopie), bevor irgendein Wort
      wandert. Erledigt 2026-07-16: annotiertes Git-Tag `bauplan-vor-umbau` auf Commit
      `de45ede` (main).

### A.1 Baseline-Inventare (Ist-Werte, fuer die Erhalt-Pruefung)

**Gate-Baseline (G-Erhalt-5).** 30 vorkommende Gate-Nummern:

```
G6 G7 G8 G9 G10 G11 G12 G13 G14 G15 G16 G17 G18 G19 G20 G21 G22 G23
G24 G25 G26 G27 G28 G29 G30 G31 G32 G33 G34 G35
```

- [ ] Nach dem Umbau muss dieselbe Menge (30 Nummern) auftauchen. Hinweis: **G10 und G24**
      sind entfernte Sync-Gates (nur historisch erwaehnt), **G26** ist verworfen; diese
      drei bleiben als Erwaehnung, werden aber nicht zu aktiven Gates. Aktiv-Gates unveraendert.

**Entscheid-/Befund-ID-Baseline (G-Erhalt-2).** Jede dieser IDs muss nach dem Umbau ueber
das Register (Anhang 1) auf genau einen Ort aufloesen:

- N-Bloecke: `N10 N10.1 N10.3 N10.4 N11 N11.1..N11.1.6 N11.2 N11.2.1 N11.2.2 N11.3 N11.4
  N11.4.1..N11.4.3 N11.5 N11.6 N11.7 N11.8 N11.8.1..N11.8.4 N11.9 N11.10 N11.11
  N11.11.1..N11.11.5(.1..4) N11.12(.1..3) N11.13 N11.14 N11.15(.1..6)`
- U: `U1..U25` (im Bauplan referenziert: U1 bis U25)
- W: `W1 W3 W4 W5 W6 W8 W15 W18`
- S: `S1..S7` | V: `V1..V12` (Teilmenge referenziert) | A: `A1..A7`

- [ ] ID-Menge vorher = ID-Menge im Register nachher.

**Zahlen-Inventar (G-Erhalt-3):** siehe Abschnitt 9, dort ist die Liste der harten
Grenzwerte gefuehrt. Vor Etappe 3 einmal ziehen, nach Etappe 3 erneut, identisch.

- [x] Zahlen-Inventar vorher erfasst (2026-07-16: die Liste der harten Grenzwerte steht in
      Abschnitt 9, G-Erhalt-3).

**Vorgefundener Defekt, bei Etappe 0 aufzunehmen (kein Inhalt, ein toter Zeiger):**

- [ ] **`N11.16` ist eine tote Referenz.** In N11.15.3 steht "die Vokabeln sind dieselben
      wie in der Entsperr-Fehlerlogik **(N11.16)**", aber einen Abschnitt N11.16 **gibt es
      nicht**. Die gemeinte Entsperr-Fehlerlogik ist **N6**. Beim Umzug (N6 wandert nach
      B.2 `unlock()`) diesen Zeiger auf den neuen B.2-Ort umbiegen. Reiner Zeiger-Fix,
      **kein** inhaltlicher Eingriff.

### A.2 Blockliste (eine Zeile pro Nachtrag-Block)

Legende **Typ:** `M` = normativer Wortlaut zieht um (Arbeit + Risiko) · `R` = Norm steht
schon im Vertrag, nur Register-Zeile ziehen (billig) · `H` = nach Anhang 3 (Historie) ·
`Spezial` = eigener Zielort. **`!`** = reihenfolge-/dichte-sensibel, mit Opus und
Gegenlesen (G-Erhalt-6). Zwei Haken je Zeile: **[N]** Norm am Zielort · **[R]**
Register-Zeile geschrieben.

| Block | Typ | Zielort | [N] | [R] |
|---|---|---|---|---|
| Kopf: Sprach-/Plattform-Entscheid | M | A.5 | [ ] | [ ] |
| N2 Offline-Pille | M | B.4 | [ ] | [ ] |
| N4 Lock-Screen-UX | M | B.4 | [ ] | [ ] |
| N5 Panik nur Maus | R | B.5 | [ ] | [ ] |
| N6 Entsperr-Fehlerlogik | M ! | B.2 + B.4 | [ ] | [ ] |
| N7 move_task/reorder_lists | R | B.2 + Phase 7 | [ ] | [ ] |
| N8 Roadmap | M | Teil D | [ ] | [ ] |
| N9 Startverhalten (ueberholt) | H | Anhang 3 | [ ] | [ ] |
| N10.1 verstaerkte Sperre | M | B.8.2 | [ ] | [ ] |
| N10.2 Off-Knopf | R | B.4 + B.8.5 | [ ] | [ ] |
| N10.3 Panik-Endschirm | R | B.4 | [ ] | [ ] |
| N10.4 nach Killswitch | M | B.8.7 | [ ] | [ ] |
| N10.5 Bridge quit/killswitch | R | B.2 | [ ] | [ ] |
| N11.1.1-.6 gestrichene Features | M | A.4 (+ Einzeiler B.1/B.2/Phase 1) | [ ] | [ ] |
| N11.2 Export/Undo | R | Phase 7 + B.2 | [ ] | [ ] |
| N11.2.1 Undo-Architektur | M | B.2 + Phase 7 | [ ] | [ ] |
| N11.2.2 reorder/move-Randfaelle | M | B.2 (bei G20) | [ ] | [ ] |
| N11.3 Einrichtung/Passphrase/Reset | M | B.2 + B.4 + B.7 | [ ] | [ ] |
| N11.4 Auto-Sperre/Rate-Limit | M | B.8.3 + B.8.4 | [ ] | [ ] |
| N11.4.1 Rate-Limit persistiert | M ! | B.8.4 + B.11 | [ ] | [ ] |
| N11.4.2 Inaktivitaets-Definition | M | B.8.3 | [ ] | [ ] |
| N11.4.3 Argon2-Parameter/MemoryError | M ! | B.7 + B.2 | [ ] | [ ] |
| N11.5 echter Flugmodus | M | B.2 + B.4 + Phase 0 | [ ] | [ ] |
| N11.6 Theme/Header/Fenster/Ton | M | B.6 + B.4 + B.5 | [ ] | [ ] |
| N11.7 Settings-Whitelist | R | B.6 + G20 | [ ] | [ ] |
| N11.8.1 Killswitch = Datei-Op | M | B.8.7 | [ ] | [ ] |
| N11.8.2 Start-Weiche | R | B.2 | [ ] | [ ] |
| N11.8.3 Zweitprofil-Spike | Spezial | bleibt Phase 8 | [ ] | [ ] |
| N11.8.4 Win+L sperrt nicht | R | B.8.1 | [ ] | [ ] |
| N11.9 beide Krypto-Schichten | M ! | B.7 | [ ] | [ ] |
| N11.10 Sperre nicht mehr offline | M | B.8.2 + B.5 | [ ] | [ ] |
| N11.11.1-.4 teardown-Sequenz | M ! | B.8.5 | [ ] | [ ] |
| N11.11.5.1-.4 native Dialoge | M ! | B.8.6 | [ ] | [ ] |
| N11.12.1-.3 Fehler-Hygiene | M | B.2 + B.9/Phase 9 | [ ] | [ ] |
| N11.13 Onboarding-Bridge/Boot | R | B.2 + B.4 | [ ] | [ ] |
| N11.14 Audit-Triage | Spezial | Anhang 2 | [ ] | [ ] |
| N11.15.1-.6 config.json | M ! | B.11 | [ ] | [ ] |

**Ableitung fuer die Modell-/Budget-Frage:** Die Zeilen mit `!` (N6, N11.4.1, N11.4.3,
N11.9, N11.11, N11.11.5, N11.15) sind der teure, riskante Kern (Opus, Gegenlesen). Alle
`R`-Zeilen sind billig (nur Register). Damit ist Etappe 3 planbar aufteilbar: erst alle
`R` (schnell, risikoarm), dann die `M` ohne `!`, zuletzt die `!`-Zeilen einzeln.

- [x] Alle Zeilen mit `!` sind fuer den Opus-Durchgang mit Gegenlesen markiert (N6,
      N11.4.1, N11.4.3, N11.9, N11.11, N11.11.5, N11.15).
- [x] Diese Blockliste ist vollstaendig gegen die N-/U-Baseline aus A.1 geprueft (kein
      Block fehlt). Geprueft 2026-07-16 gegen die Nachtrag-Ueberschriften des Bauplans
      (N2 bis N10 inkl. N10.1 bis N10.5, N11.1 bis N11.15.6): jeder Block hat eine Zeile.
