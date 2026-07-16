#!/usr/bin/env python3
"""
verify_umbau.py  -  Inhalts-Erhalt-Pruefung fuer den Bauplan-Umbau.

Zweck (siehe "Umbauplan - Struktur des Bauplans.md", Abschnitt 9, G-Erhalt-1..6):
Der Umbau darf NUR Text verschieben, nie Inhalt aendern. Dieses Skript vergleicht
den eingefrorenen Referenzstand (Git-Tag) mit dem aktuellen Stand und weist objektiv
nach, ob die eiserne Regel gehalten wurde. Es beweist nicht, dass der Umzug fachlich
"richtig" ist (das bleibt Handarbeit im Diff), sondern nur, dass nichts dazukam,
verschwand oder sich veraenderte.

Vier Pruefungen:
  1. ID-Inventar (G-Erhalt-2/-5): Menge aller Etikett-IDs (G/N/U/W/V/S/A) und
     Gate-Anzahl vorher == nachher. Zeigt jede hinzugekommene / entfernte ID.
  2. Zahlen-Inventar (G-Erhalt-3): Multimenge der Werte-mit-Einheit (MiB, min, s, ...)
     und key=wert-Formen vorher == nachher. Zeigt jede geaenderte Zahl.
  3. Pflicht-Literale (G-Erhalt-3, Netz fuer einheitenlose Werte): kritische Konstanten
     (4096, 262144, NOA1, ...) muessen weiter vorhanden sein.
  4. Wort-Inventar (G-Erhalt-4): normalisierte Wort-Multimenge vorher ~ nachher.
     Ein Umzug erzeugt nur kleine, erklaerbare Abweichungen (Ueberschriften, Zeiger,
     bewusst nach Anhang 3 verschobene Historie). Ein grosser Wort-Diff = Alarm.

Aufruf (aus beliebigem Verzeichnis im Repo):
    py Planung/tools/verify_umbau.py
    py Planung/tools/verify_umbau.py --before bauplan-vor-umbau --after HEAD
    py Planung/tools/verify_umbau.py --after HEAD --words 40

Standard: before = Tag 'bauplan-vor-umbau', after = Datei im Arbeitsverzeichnis.
Nur Python-Standardbibliothek, keine Abhaengigkeiten.
"""

import argparse
import re
import subprocess
import sys
from collections import Counter

# Windows-Terminal gibt sonst cp1252 aus und verstuemmelt Umlaut-Woerter im Diff.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Pfad der Bauplan-Datei, relativ zur Repo-Wurzel (Git nutzt Vorwaerts-Slashes).
BAUPLAN_PATH = "Planung/Bauplan - NoaToDo.md"

DEFAULT_BEFORE = "bauplan-vor-umbau"

# Bekannte, ERWARTETE Abweichungen (kein Bug). Werden gesondert ausgewiesen,
# damit sie den Befund nicht faelschlich rot faerben.
EXPECTED_ID_REMOVALS = {
    # N11.16 ist laut Umbauplan A.1 eine tote Referenz; der Zeiger wird beim
    # Umzug auf den neuen B.2-Ort umgebogen, das Token darf verschwinden.
    "N11.16",
}

EXPECTED_ID_ADDITIONS = {
    # Die Blockliste des Umbauplans (A.2) benennt die N10-Punkte 2 und 5 als
    # N10.2 und N10.5; im alten Bauplan hiessen sie nur "**2.**"/"**5.**".
    # Die Etappe-3-Etiketten und Register-Zeilen fuehren die Token neu ein,
    # das ist gewollt und keine Inhaltsaenderung.
    "N10.2", "N10.5",
}

# --- ID-Familien: Wortgrenzen auf beiden Seiten toeten Fehltreffer
#     (SHA256 -> kein A256, A11y -> kein A11). ---
ID_PATTERNS = {
    "G (Gates)":  re.compile(r"\bG\d+\b"),
    "N (Nachtrag)": re.compile(r"\bN\d+(?:\.\d+)*\b"),
    "U (Entscheid)": re.compile(r"\bU\d+\b"),
    "W (Plananalyse)": re.compile(r"\bW\d+\b"),
    "V (Plananalyse)": re.compile(r"\bV\d+\b"),
    "S (Plananalyse)": re.compile(r"\bS\d+\b"),
    "A (Audit-Befund)": re.compile(r"\bA\d+\b"),
}

# --- Zahlen-mit-Einheit und key=wert-Formen (Multimengen-Diff). ---
NUMBER_PATTERNS = [
    re.compile(r"\b\d+\s*(?:MiB|GiB|KiB)\b"),
    re.compile(r"\b\d+\s*min\b"),
    re.compile(r"\b\d+\s*h\b"),
    re.compile(r"\b\d+\s*s\b"),
    re.compile(r"\b\d+\s*(?:Byte|Bytes)\b"),
    re.compile(r"\b\d+\s*Zeichen\b"),
    re.compile(r"(?:memory_cost|time_cost|parallelism|hash_len)\s*=?\s*\d+"),
    re.compile(r"\bDAMAGE_HINT_AFTER\b\s*=?\s*\d+"),
]

# Einheitenlose kritische Konstanten: muessen weiter mindestens einmal vorkommen.
# (Umzug-sicher: Verschieben laesst sie vorhanden; nur echtes Loeschen faellt auf.)
REQUIRED_LITERALS = [
    "4096",        # Task-Textlimit
    "262144",      # Argon2 memory_cost (KiB)
    "hash_len",
    "parallelism",
    "time_cost",
    "memory_cost",
    "DAMAGE_HINT_AFTER",
    "NOA1",        # .enc-Magic
    "sidebarWidth",
    "autoLock",
]

# Wort-Tokenizer: Buchstaben (inkl. Umlaute), Ziffern, Unterstrich.
WORD_RE = re.compile(r"[0-9A-Za-zÀ-ſ_]+")


def sh(args):
    """Git-Aufruf, gibt stdout als Text zurueck; wirft bei Fehler."""
    res = subprocess.run(
        args, capture_output=True, check=True
    )
    return res.stdout.decode("utf-8", errors="replace")


def repo_root():
    return sh(["git", "rev-parse", "--show-toplevel"]).strip()


def load_before(ref):
    """Bauplan-Inhalt beim Referenz-Stand (Tag/Commit) via git show."""
    return sh(["git", "show", f"{ref}:{BAUPLAN_PATH}"])


def load_after(after, root):
    """after == 'WORKTREE' -> Datei auf der Platte; sonst git show <ref>."""
    if after.upper() == "WORKTREE":
        path = f"{root}/{BAUPLAN_PATH}"
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return sh(["git", "show", f"{after}:{BAUPLAN_PATH}"])


def collapse_ws(text):
    """Whitespace normalisieren, damit '256 MiB' == '256  MiB' == '256\\nMiB'."""
    return re.sub(r"\s+", " ", text)


# ---- Ausgabe-Helfer -------------------------------------------------------

OK, WARN, INFO = "[ OK ]", "[ !! ]", "[ i  ]"


def head(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


# ---- Pruefungen -----------------------------------------------------------

def check_ids(before, after):
    head("1. ID-INVENTAR (G-Erhalt-2 / G-Erhalt-5)")
    all_ok = True
    for name, pat in ID_PATTERNS.items():
        b = set(pat.findall(before))
        a = set(pat.findall(after))
        added = sorted(a - b)
        removed = sorted(b - a)
        unexpected_removed = [x for x in removed if x not in EXPECTED_ID_REMOVALS]
        expected_removed = [x for x in removed if x in EXPECTED_ID_REMOVALS]
        unexpected_added = [x for x in added if x not in EXPECTED_ID_ADDITIONS]
        expected_added = [x for x in added if x in EXPECTED_ID_ADDITIONS]

        status = OK if not unexpected_added and not unexpected_removed else WARN
        if status == WARN:
            all_ok = False
        print(f"{status} {name:20s}  vorher={len(b):3d}  nachher={len(a):3d}")
        if unexpected_added:
            print(f"        + HINZUGEKOMMEN (pruefen!): {', '.join(unexpected_added)}")
        if expected_added:
            print(f"        + hinzugekommen (erwartet, Etikett): {', '.join(expected_added)}")
        if unexpected_removed:
            print(f"        - ENTFERNT (pruefen!): {', '.join(unexpected_removed)}")
        if expected_removed:
            print(f"        - entfernt (erwartet, tote Ref): {', '.join(expected_removed)}")

        # Gate-Sonderregel: Anzahl darf sich nicht aendern.
        if name.startswith("G "):
            if len(a) != len(b):
                print(f"        {WARN} Gate-ANZAHL geaendert: {len(b)} -> {len(a)} "
                      f"(muss gleich bleiben, G-Erhalt-5)")
                all_ok = False
            else:
                print(f"        Gate-Anzahl stabil ({len(a)}).")
    return all_ok


def check_numbers(before, after):
    head("2. ZAHLEN-INVENTAR mit Einheit (G-Erhalt-3)")
    b_text, a_text = collapse_ws(before), collapse_ws(after)
    b_counter, a_counter = Counter(), Counter()
    for pat in NUMBER_PATTERNS:
        for m in pat.findall(b_text):
            b_counter[re.sub(r"\s+", " ", m).strip()] += 1
        for m in pat.findall(a_text):
            a_counter[re.sub(r"\s+", " ", m).strip()] += 1

    diff_keys = sorted(set(b_counter) | set(a_counter),
                       key=lambda k: (b_counter[k] != a_counter[k], k))
    changed = [k for k in diff_keys if b_counter[k] != a_counter[k]]
    if not changed:
        print(f"{OK} Alle {len(set(b_counter) | set(a_counter))} Werte-mit-Einheit "
              f"unveraendert (Anzahl je Wert gleich).")
        return True
    print(f"{WARN} {len(changed)} Werte mit geaenderter Haeufigkeit "
          f"(vorher != nachher):")
    for k in changed:
        print(f"        '{k}'  vorher={b_counter[k]}  nachher={a_counter[k]}")
    return False


def check_literals(after):
    head("3. PFLICHT-LITERALE, einheitenlose Konstanten (G-Erhalt-3)")
    missing = [lit for lit in REQUIRED_LITERALS if lit not in after]
    if not missing:
        print(f"{OK} Alle {len(REQUIRED_LITERALS)} Pflicht-Konstanten weiter vorhanden.")
        return True
    print(f"{WARN} Fehlende Konstanten (im aktuellen Stand nicht mehr gefunden):")
    for lit in missing:
        print(f"        - {lit}")
    return False


def check_words(before, after, top_n):
    head("4. WORT-INVENTAR, normalisiert (G-Erhalt-4)")
    b_words = Counter(w.lower() for w in WORD_RE.findall(before))
    a_words = Counter(w.lower() for w in WORD_RE.findall(after))

    # Multimengen-Differenz in beide Richtungen.
    removed = b_words - a_words   # Vorkommen, die verschwanden
    added = a_words - b_words     # Vorkommen, die dazukamen
    n_removed = sum(removed.values())
    n_added = sum(added.values())

    print(f"Wort-Vorkommen gesamt: vorher={sum(b_words.values())}  "
          f"nachher={sum(a_words.values())}")
    print(f"Verschwundene Vorkommen: {n_removed}   "
          f"Hinzugekommene Vorkommen: {n_added}")
    print("(Bei einem reinen Umzug klein und erklaerbar: Ueberschriften-Woerter,")
    print(" 'siehe'-Zeiger, bewusst nach Anhang 3 verschobene Historie.)")

    if n_removed == 0 and n_added == 0:
        print(f"{OK} Wort-Inventar bit-genau identisch.")
        return True

    def show(label, counter):
        items = counter.most_common(top_n)
        if not items:
            return
        print(f"\n  {label} (Top {min(top_n, len(items))}):")
        for word, cnt in items:
            print(f"        {cnt:4d}x  {word}")

    show("VERSCHWUNDEN", removed)
    show("HINZUGEKOMMEN", added)
    print(f"\n{INFO} Kein automatisches Urteil: pruefe, ob obige Abweichungen NUR")
    print("     Ueberschriften/Zeiger/Historie sind. Inhaltswoerter = Alarm.")
    return None  # neutral: menschliches Urteil noetig


def main():
    ap = argparse.ArgumentParser(
        description="Inhalts-Erhalt-Pruefung Bauplan-Umbau (Tag gegen aktuellen Stand)."
    )
    ap.add_argument("--before", default=DEFAULT_BEFORE,
                    help=f"Referenz-Stand (Tag/Commit). Standard: {DEFAULT_BEFORE}")
    ap.add_argument("--after", default="WORKTREE",
                    help="Aktueller Stand: 'WORKTREE' (Datei auf Platte) oder Tag/Commit. "
                         "Standard: WORKTREE")
    ap.add_argument("--words", type=int, default=30,
                    help="Wie viele abweichende Woerter je Richtung zeigen (Standard 30).")
    args = ap.parse_args()

    try:
        root = repo_root()
    except subprocess.CalledProcessError:
        print("FEHLER: kein Git-Repository gefunden.", file=sys.stderr)
        return 2

    try:
        before = load_before(args.before)
    except subprocess.CalledProcessError:
        print(f"FEHLER: Referenz '{args.before}:{BAUPLAN_PATH}' nicht gefunden.",
              file=sys.stderr)
        return 2
    try:
        after = load_after(args.after, root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"FEHLER: aktueller Stand '{args.after}' nicht lesbar.", file=sys.stderr)
        return 2

    print(f"Vergleich:  before = {args.before}   after = {args.after}")
    print(f"Datei:      {BAUPLAN_PATH}")
    print(f"Groesse:    vorher {len(before)} Zeichen   nachher {len(after)} Zeichen")

    r1 = check_ids(before, after)
    r2 = check_numbers(before, after)
    r3 = check_literals(after)
    r4 = check_words(before, after, args.words)

    head("GESAMTURTEIL")
    hard_fail = (r1 is False) or (r2 is False) or (r3 is False)
    if hard_fail:
        print(f"{WARN} Mindestens eine harte Pruefung (ID / Zahlen / Literale) FEHLGESCHLAGEN.")
        print("     Das deutet auf eine Inhaltsaenderung hin, nicht auf reinen Umzug.")
        print("     Jede oben markierte Abweichung einzeln klaeren.")
    else:
        print(f"{OK} Harte Pruefungen bestanden: IDs, Zahlen und Konstanten unveraendert.")
    if r4 is None:
        print(f"{INFO} Wort-Inventar weicht ab (normal bei Umzug) -> obige Liste sichten.")
    elif r4:
        print(f"{OK} Wort-Inventar identisch.")
    print()
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
