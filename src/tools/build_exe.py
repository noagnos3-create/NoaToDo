"""Baut die auslieferbare ``NoaToDo.exe`` (Bauplan Phase 9, Entscheid N11.29).

Aufruf (aus ``src/``, mit dem venv-Python des Projekts):

    .\\venv\\Scripts\\python.exe tools\\build_exe.py

Was der Schritt tut, in dieser Reihenfolge:

1. **Interpreter pruefen (Gate G11 / U25):** gebaut wird ausschliesslich unter
   CPython 3.11.x. ``sqlcipher3-wheels`` liefert Wheels nur fuer bestimmte
   CPython-Versionen, und der Interpreter ist eine gepinnte Abhaengigkeit wie
   jedes Paket.
2. **Build-Stempel schreiben** (``src/_buildstamp.py``): Build-Datum, Commit,
   Signatur-Angabe und das SHA-256-Manifest ueber alle Frontend-Dateien
   (Gate G27, siehe ``integrity.py``). Die Datei ist ein Bau-Artefakt und wird
   am Ende **wieder geloescht**: bliebe sie liegen, liefe der naechste
   Entwicklerstart in die Integritaetspruefung und schluege bei jeder
   Frontend-Aenderung Fehlalarm.
3. **Versions-Ressource schreiben** (``src/build/version_info.txt``), damit
   die ``.exe`` in den Windows-Eigenschaften Version und Namen traegt (V10,
   dieselben Werte wie im Status-Modal).
4. **PyInstaller** mit ``NoaToDo.spec`` laufen lassen (One-file, ``optimize=2``,
   kein UPX, Icon eingebettet).
5. Ergebnis melden, samt der beiden ehrlichen Hinweise: diese Fassung ist
   **nicht signiert** (N11.29 b) und setzt die **WebView2-Runtime** auf dem
   Zielrechner voraus (N11.29 c).

Signieren (sobald ein Zertifikat vorliegt, G27) ist bewusst **nicht**
automatisiert: der Schritt gehoert an eine Stelle mit Zugriff auf den privaten
Schluessel, nicht in ein Skript im Repo.
"""
from __future__ import annotations

import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.dirname(HERE)
sys.path.insert(0, CODE)

import buildinfo  # noqa: E402  (erst nach dem sys.path-Eintrag moeglich)
import integrity  # noqa: E402

STAMP = os.path.join(CODE, "_buildstamp.py")
BUILD_DIR = os.path.join(CODE, "build")
DIST_DIR = os.path.join(CODE, "dist")
SPEC = os.path.join(CODE, "NoaToDo.spec")


def _check_interpreter() -> None:
    if sys.version_info[:2] != (3, 11):
        raise SystemExit(
            "Abbruch (Gate G11/U25): der Release-Build laeuft nur unter "
            f"CPython 3.11.x, hier laeuft {sys.version.split()[0]}."
        )


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=CODE, capture_output=True, text=True, timeout=20)
        return out.stdout.strip()
    except Exception:
        return ""


def _commit() -> str:
    short = _git("rev-parse", "--short", "HEAD")
    if not short:
        return "unknown"
    dirty = _git("status", "--porcelain")
    return short + ("+dirty" if dirty else "")


def _write_stamp(build_date: str, commit: str, manifest: dict) -> None:
    lines = [
        '"""Bau-Artefakt, erzeugt von tools/build_exe.py. Nicht von Hand aendern."""',
        f"BUILD_DATE = {build_date!r}",
        f"BUILD_COMMIT = {commit!r}",
        "# Diese Fassung wird nicht signiert (N11.29 b). Wer signiert, setzt hier",
        "# True, damit das Status-Modal die Wahrheit sagt (G22).",
        "SIGNED = False",
        "FRONTEND_MANIFEST = {",
    ]
    for rel, digest in manifest.items():
        lines.append(f"    {rel!r}: {digest!r},")
    lines.append("}")
    with open(STAMP, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _write_version_resource(build_date: str) -> None:
    os.makedirs(BUILD_DIR, exist_ok=True)
    nums = [int(p) for p in buildinfo.VERSION.split(".")][:4]
    while len(nums) < 4:
        nums.append(0)
    filevers = tuple(nums)
    text = f"""# Erzeugt von tools/build_exe.py (Bauplan Phase 9, V10). Nicht von Hand aendern.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={filevers},
    prodvers={filevers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'NoaGnos'),
         StringStruct('FileDescription', 'NoaToDo, local encrypted to-do app'),
         StringStruct('FileVersion', '{buildinfo.VERSION}'),
         StringStruct('InternalName', 'NoaToDo'),
         StringStruct('OriginalFilename', 'NoaToDo.exe'),
         StringStruct('ProductName', 'NoaToDo'),
         StringStruct('ProductVersion', '{buildinfo.VERSION} ({build_date})'),
         StringStruct('Comments', 'Local only. No cloud, no telemetry, no auto-update.')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open(os.path.join(BUILD_DIR, "version_info.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)


def _drop_stamp() -> None:
    for path in (STAMP, os.path.join(CODE, "__pycache__", "_buildstamp.cpython-311.pyc")):
        try:
            os.remove(path)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    _check_interpreter()
    argv = list(sys.argv[1:] if argv is None else argv)
    onedir = "--onedir" in argv
    if onedir:
        # Ordnerbau (Bauplan Phase 9: "erst one-folder zum Debuggen"). Zugleich
        # der einzige Weg, den G27-Nachweis von Hand zu fuehren: nur hier liegt
        # eine app.js zum Veraendern neben der .exe.
        os.environ["NOATODO_ONEDIR"] = "1"
    else:
        os.environ.pop("NOATODO_ONEDIR", None)
    if "--console" in argv:
        # Nur zum Untersuchen eines Builds (Startmeldungen sichtbar machen).
        # Die Auslieferung ist immer fensterlos.
        os.environ["NOATODO_CONSOLE"] = "1"
    else:
        os.environ.pop("NOATODO_CONSOLE", None)
    try:
        import PyInstaller.__main__ as pyi
    except ImportError:
        raise SystemExit(
            "Abbruch: PyInstaller fehlt. Installieren mit\n"
            "  .\\venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt")

    build_date = datetime.date.today().isoformat()
    commit = _commit()
    manifest = integrity.build_manifest(os.path.join(CODE, "frontend"))
    print(f"[build] Version {buildinfo.VERSION}, Datum {build_date}, Commit {commit}")
    print(f"[build] Frontend-Manifest: {len(manifest)} Dateien (G27)")
    if "+dirty" in commit:
        print("[build] Hinweis: der Arbeitsbaum ist nicht committet, "
              "der Stempel im Binary sagt das ehrlich mit.")

    _write_stamp(build_date, commit, manifest)
    _write_version_resource(build_date)
    try:
        pyi.run([
            SPEC,
            "--noconfirm",
            "--distpath", DIST_DIR,
            "--workpath", os.path.join(BUILD_DIR, "pyi"),
        ])
    finally:
        # IMMER wegraeumen, auch nach einem Abbruch: ein liegengebliebener
        # Stempel wuerde den naechsten Entwicklerstart in die
        # Integritaetspruefung schicken.
        _drop_stamp()

    exe = (os.path.join(DIST_DIR, "NoaToDo", "NoaToDo.exe") if onedir
           else os.path.join(DIST_DIR, "NoaToDo.exe"))
    if not os.path.isfile(exe):
        raise SystemExit("Abbruch: PyInstaller hat keine NoaToDo.exe erzeugt.")
    size = os.path.getsize(exe) / (1024 * 1024)
    print(f"\n[build] Fertig: {exe} ({size:.1f} MB)")
    print("[build] NICHT signiert (N11.29 b): SmartScreen warnt beim ersten "
          "Start auf einem fremden Rechner, und eine Manipulation am Binary "
          "ist nicht per Signatur erkennbar.")
    print("[build] Setzt die Microsoft Edge WebView2 Runtime auf dem Zielrechner "
          "voraus (N11.29 c); fehlt sie, meldet die App das verstaendlich.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
