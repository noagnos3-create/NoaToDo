"""Frontend-Integritaet (Gate G27, Ergaenzung A5 vom 2026-07-15).

Warum das noetig ist: Die Signatur einer ``.exe`` deckt die **danebenliegenden**
``index.html``/``app.js``/``style.css`` nicht ab. Wer sie einmal schreiben kann,
besitzt die App dauerhaft: der naechste Start laedt das manipulierte JS mit
vollem Bridge-Zugriff, liest die Passphrase im Lock-Screen mit und greift nach
dem Entsperren alles ab, bei intakter Signatur des Binaries.

Zwei Pflichtwege nennt G27, NoaToDo geht beide:

1. **Einbetten:** der One-file-Build (N11.29 a) traegt das gesamte Frontend im
   Binary und entpackt es pro Start in einen frischen Ordner. Es gibt also gar
   keine dauerhaft danebenliegende Datei, die jemand austauschen koennte.
2. **Pruefen:** zusaetzlich vergleicht der Start jeden Frontend-Hash gegen ein
   im Binary eingebettetes Manifest (``buildinfo.FRONTEND_MANIFEST``, erzeugt
   von ``tools/build_exe.py``). Bei jeder Abweichung verweigert die App den
   Start mit klarer Meldung; einen "trotzdem fortfahren"-Knopf gibt es nicht.

Einordnung nach B.10 (ehrlich, G22): das erschwert stille K4-Persistenz und ist
**kein** vollstaendiger K4-Schutz. Gegen jemanden, der auch das Binary
austauschen kann, hilft nur die Signaturpruefung durch den Nutzer, und die
setzt ein Zertifikat voraus, das dieser Fassung fehlt (N11.29 b).
"""
from __future__ import annotations

import hashlib
import os

import buildinfo

# Nur diese Dateiarten gehoeren zum Frontend. Alles andere im Ordner (etwa ein
# vom Werkzeug abgelegtes Zwischenprodukt) waere kein Ausfuehrungskanal und
# soll den Build nicht unnoetig zerbrechlich machen.
_TRACKED_SUFFIXES = (".html", ".js", ".css", ".woff2", ".ico", ".svg")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(frontend_dir: str) -> dict[str, str]:
    """Manifest ueber einen Frontend-Ordner erzeugen (Build-Zeit).

    Schluessel sind relative Pfade mit ``/`` als Trenner (plattformneutral und
    stabil sortiert), Werte die SHA-256-Hexwerte.
    """
    manifest: dict[str, str] = {}
    for root, _dirs, files in os.walk(frontend_dir):
        for name in sorted(files):
            if not name.lower().endswith(_TRACKED_SUFFIXES):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, frontend_dir).replace("\\", "/")
            manifest[rel] = _sha256(full)
    return dict(sorted(manifest.items()))


def check() -> list[str]:
    """Laufzeitpruefung: Liste der beanstandeten Dateien (leer = alles gut).

    Ohne eingebettetes Manifest (normaler Entwicklerstart aus dem Quellbaum)
    gibt es nichts zu pruefen: dort ist der Quelltext selbst die Wahrheit, und
    eine Pruefung wuerde nur bei jeder Frontend-Aenderung Fehlalarm schlagen.
    """
    manifest = buildinfo.FRONTEND_MANIFEST
    if not manifest:
        return []
    root = buildinfo.frontend_dir()
    bad: list[str] = []
    for rel, expected in manifest.items():
        full = os.path.join(root, rel.replace("/", os.sep))
        try:
            actual = _sha256(full)
        except OSError:
            bad.append(rel + " (missing)")
            continue
        if actual != expected:
            bad.append(rel)
    return bad


def message(bad: list[str]) -> str:
    """Der Text des Verweigerungs-Fensters (klar, ohne Ausweg, G27)."""
    listed = ", ".join(bad[:3])
    if len(bad) > 3:
        listed += ", ..."
    return (
        "NoaToDo will not start: integrity check failed.\n"
        "\n"
        "A file of the app interface does not match this build:\n"
        f"{listed}\n"
        "\n"
        "Reinstall NoaToDo from a source you trust."
    )
