"""Erzeugt ``requirements.lock.hashes.txt`` (Gate G11, Bauplan Phase 9).

Warum: ``requirements.lock.txt`` pinnt jede Abhaengigkeit auf eine feste
Version, aber eine Version allein sagt nichts darueber, ob das heruntergeladene
Artefakt dasselbe ist wie damals (ein kompromittierter Index oder ein
nachtraeglich ausgetauschtes Wheel faellt nicht auf). Der Release-Build
installiert deshalb mit **pip-Hash-Checking**:

    .\\venv\\Scripts\\python.exe -m pip install --require-hashes ^
        -r requirements.lock.hashes.txt

``--require-hashes`` erzwingt, dass **jede** Anforderung eine exakte Version und
mindestens einen ``--hash`` traegt; passt ein heruntergeladenes Artefakt nicht,
bricht pip ab, statt es zu installieren.

Aufruf (aus ``Code/``, mit dem venv-Python des Projekts, Netz noetig):

    .\\venv\\Scripts\\python.exe tools\\lock_hashes.py

Der Schritt laedt jedes Wheel aus ``requirements.lock.txt`` in einen
Temp-Ordner, bildet den SHA-256 und schreibt die Hash-Datei neu. Er ist
**bewusst kein Teil des Builds**: Hashes aendern sich nur, wenn sich die
gepinnten Versionen aendern, und dann soll das ein sichtbarer, eigener Schritt
mit eigener Pruefung sein (Rebuild-Kadenz, V10).
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
LOCK = os.path.join(CODE, "requirements.lock.txt")
OUT = os.path.join(CODE, "requirements.lock.hashes.txt")

HEADER = """\
# NoaToDo: gepinnte Abhaengigkeiten MIT Artefakt-Hashes (Gate G11).
# Erzeugt von tools/lock_hashes.py, nicht von Hand pflegen: wer eine Version
# aendert, aendert sie in requirements.lock.txt und laesst das Werkzeug neu
# laufen.
#
# Installation fuer den Release-Build (bricht bei jedem abweichenden Artefakt ab):
#   python -m pip install --require-hashes -r requirements.lock.hashes.txt
#
# Interpreter: CPython {py} (gepinnt, U25). Hashes gelten fuer die Wheels
# dieser Plattform ({plat}).
"""


def _requirements() -> list[str]:
    reqs = []
    with open(LOCK, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                reqs.append(line)
    return reqs


def _norm(name: str) -> str:
    """Paketname nach PEP 503 vereinheitlichen.

    Noetig, weil derselbe Name in drei Schreibweisen auftritt: in der
    Lock-Datei (``jaraco.context``, ``winrt-Windows.Devices.Radios``), im
    Dateinamen des Artefakts (``jaraco_context``, ``winrt_Windows.Devices...``)
    und intern bei pip. Punkt, Strich und Unterstrich sind dabei gleichwertig.
    """
    return re.sub(r"[-_.]+", "-", name).lower()


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if sys.version_info[:2] != (3, 11):
        raise SystemExit(
            "Abbruch (G11/U25): Hashes werden fuer CPython 3.11.x gebildet, "
            f"hier laeuft {sys.version.split()[0]}.")
    reqs = _requirements()
    print(f"[hashes] {len(reqs)} gepinnte Pakete aus requirements.lock.txt")
    with tempfile.TemporaryDirectory(prefix="noatodo-wheels-") as tmp:
        # Kein ``--only-binary :all:``: nicht jedes gepinnte Paket hat ein Wheel
        # (``proxy_tools`` etwa liegt nur als Quellarchiv vor). Das
        # Hash-Checking gilt fuer beide Artefaktarten gleichermassen.
        cmd = [sys.executable, "-m", "pip", "download",
               "--no-deps", "-d", tmp, *reqs]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            sys.stderr.write(res.stdout[-4000:] + res.stderr[-4000:])
            raise SystemExit("Abbruch: pip download ist fehlgeschlagen.")
        files = sorted(os.listdir(tmp))
        digests: dict[str, list[str]] = {}
        for name in files:
            if name.endswith(".whl"):
                # Wheel: <name>-<version>-<python>-<abi>-<plattform>.whl
                parts = name[:-4].split("-")
                if len(parts) < 2:
                    continue
                pkg, version = parts[0], parts[1]
            else:
                # Quellarchiv: <name>-<version>.tar.gz / .zip
                stem = name
                for suffix in (".tar.gz", ".tar.bz2", ".zip", ".tgz"):
                    if stem.endswith(suffix):
                        stem = stem[: -len(suffix)]
                        break
                else:
                    continue
                pkg, _, version = stem.rpartition("-")
                if not pkg:
                    continue
            key = f"{_norm(pkg)}=={version}"
            digests.setdefault(key, []).append(_sha256(os.path.join(tmp, name)))

    lines = [HEADER.format(py=sys.version.split()[0], plat=sys.platform)]
    missing = []
    for req in reqs:
        name, _, version = req.partition("==")
        hashes = digests.get(f"{_norm(name)}=={version}")
        if not hashes:
            missing.append(req)
            continue
        joined = " \\\n    ".join(f"--hash=sha256:{h}" for h in hashes)
        lines.append(f"{req} \\\n    {joined}")
    if missing:
        raise SystemExit("Abbruch: kein Artefakt gefunden fuer " + ", ".join(missing))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"[hashes] geschrieben: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
