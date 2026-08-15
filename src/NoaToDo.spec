# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Bauplan fuer NoaToDo (Bauplan Phase 9, Entscheid N11.29 a).

Gebaut wird **eine einzelne** ``NoaToDo.exe`` (One-file): alle Python-Module,
die Abhaengigkeiten und das komplette ``frontend/`` liegen im Binary und werden
pro Start in einen frischen Temp-Ordner entpackt (``sys._MEIPASS``, aufgeloest
ueber ``buildinfo.resource_path``). Damit ist der G27-Pflichtpunkt
"Frontend-Assets ins Binary einbetten" erfuellt; die zusaetzliche Hash-Pruefung
gegen das eingebettete Manifest macht ``integrity.py``.

Nicht direkt aufrufen, sondern ueber ``tools/build_exe.py``: der Build-Schritt
erzeugt vorher ``_buildstamp.py`` (Build-Datum, Commit, Frontend-Manifest) und
die Versions-Ressource und raeumt beides hinterher wieder weg.
"""
import os

from PyInstaller.utils.hooks import collect_all, copy_metadata

HERE = os.path.abspath(SPECPATH)

datas = [(os.path.join(HERE, "frontend"), "frontend")]
binaries = []
hiddenimports = [
    # Eigene Module, die nur in Funktionskoerpern importiert werden.
    "buildinfo", "integrity", "lockwindow", "wintheme",
    # Build-Stempel (existiert nur waehrend des Builds).
    "_buildstamp",
    # PyWebView waehlt sein Backend zur Laufzeit.
    "webview.platforms.winforms", "webview.platforms.edgechromium",
    # keyring findet seine Backends ueber Entry Points (G18: DPAPI-Pepper).
    "keyring.backends.Windows", "win32ctypes.core", "win32ctypes.core.ctypes",
]

# keyring braucht seine Metadaten, sonst findet es zur Laufzeit kein Backend.
datas += copy_metadata("keyring")

# Pakete mit nativen Anteilen vollstaendig einsammeln: SQLCipher (Schicht 1),
# und die modularen WinRT-Pakete des echten Flugmodus (N11.5), die ueber
# Namensraum-Pakete und .pyd-Erweiterungen laufen.
for _pkg in (
    "sqlcipher3",
    "winrt",
    "winrt.windows.devices.radios",
    "winrt.windows.devices.enumeration",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
):
    try:
        _d, _b, _h = collect_all(_pkg)
    except Exception:
        continue
    datas += _d
    binaries += _b
    hiddenimports += _h

_version_res = os.path.join(HERE, "build", "version_info.txt")
if not os.path.isfile(_version_res):
    _version_res = None

# One-folder statt One-file, wenn ``NOATODO_ONEDIR`` gesetzt ist (Bauplan
# Phase 9: "erst one-folder zum Debuggen, dann one-file pruefen"). Der Ordnerbau
# ist ausserdem der einzige Weg, den G27-Nachweis von Hand zu fuehren: nur dort
# liegt eine ``app.js`` zum Veraendern neben der ``.exe``.
ONEDIR = bool(os.environ.get("NOATODO_ONEDIR"))
# Nur zum Untersuchen eines Builds: mit Konsole bauen, damit die Startmeldungen
# sichtbar sind (die Auslieferung ist immer fensterlos). Kein Sicherheitsschalter:
# der Release-Schalter fuer DevTools sitzt in buildinfo (G34 a).
CONSOLE = bool(os.environ.get("NOATODO_CONSOLE"))

a = Analysis(
    [os.path.join(HERE, "main.py")],
    pathex=[HERE],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Nicht gebraucht und nur Angriffsflaeche/Groesse: Tk, Test- und
        # Entwicklerwerkzeuge gehoeren nicht in eine ausgelieferte Tresor-App.
        # PIL steht mit dabei, weil Pillow im Entwickler-venv liegt (nur fuer
        # tools/make_icon.py) und nichts davon in die .exe gehoert.
        "tkinter", "unittest", "pytest", "pydoc", "doctest", "PyInstaller",
        "PIL",
    ],
    noarchive=False,
    # Gate G27: mit Optimierungsstufe 2 uebersetzen, also .pyc ohne Docstrings
    # und ohne `assert`s. Der Quelltext selbst liegt ohnehin nicht bei.
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    *([] if ONEDIR else [a.binaries, a.datas]),
    [],
    exclude_binaries=ONEDIR,
    name="NoaToDo",
    debug=False,
    bootloader_ignore_signals=False,
    # Kein Strippen (Windows-Binaries mag PyInstaller so nicht) und **kein UPX**:
    # gepackte Binaries sind ein klassisches Virenscanner-Warnsignal und wuerden
    # den Start verlangsamen, ohne Sicherheit zu bringen (G27-Leitlinie:
    # Haertung darf die Funktion nie beeintraechtigen).
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    # Fensteranwendung: keine Konsole hinter dem Fenster.
    console=CONSOLE,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(HERE, "frontend", "icon.ico"),
    version=_version_res,
)

if ONEDIR:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="NoaToDo",
    )
