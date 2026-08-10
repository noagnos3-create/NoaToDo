"""Build- und Laufzeit-Identitaet der App (Bauplan Phase 9).

Eine Quelle fuer alles, was sich zwischen "aus dem Quellbaum gestartet" und
"gefrorene ``NoaToDo.exe``" unterscheidet:

- **Version und Build-Datum** (V10): dieselben Werte, die in die
  ``.exe``-Ressourcen geschrieben und im Status-Modal angezeigt werden.
- **Release-Schalter** (Gate G34 a): im gefrorenen Build ist ``NOATODO_DEBUG``
  wirkungslos, ``debug_enabled()`` liefert dort **immer** ``False``. Das ist
  bewusst eine Build-Konstante und keine Einstellung: sonst bekaeme jeder mit
  kurzem Zugriff (K3) per Umgebungsvariable eine DevTools-Konsole mit vollem
  ``pywebview.api.*``-Zugriff, inklusive ``killswitch()``.
- **Pfadaufloesung**: im Quellbaum liegen Frontend und Icon neben dieser Datei,
  im One-file-Build entpackt PyInstaller sie in einen frischen Temp-Ordner
  (``sys._MEIPASS``). Jeder Zugriff auf mitgelieferte Dateien laeuft ueber
  :func:`resource_path`, nie ueber ``__file__``.

Der Build-Stempel selbst wird nicht hier gepflegt, sondern beim Bauen erzeugt:
``tools/build_exe.py`` schreibt ein ``_buildstamp.py`` mit Build-Datum, Commit
und dem Frontend-Hash-Manifest (G27) und legt es mit ins Bundle. Fehlt die
Datei (normaler Entwicklerstart), gilt der Lauf als Entwicklerlauf.
"""
from __future__ import annotations

import os
import sys

# Versionsnummer der App. Wird beim Build in die .exe-Ressourcen geschrieben
# (FileVersion/ProductVersion) und im Status-Modal angezeigt (V10). Vier
# Zahlen-Felder sind Windows-Pflicht in der Ressource, hier steht die
# menschliche Fassung.
VERSION = "1.0.0"

# Bezugsquelle im Klartext (V10): NoaToDo prueft NIE selbst uebers Netz auf
# Updates und ruft nie nach Hause. Das Status-Modal nennt stattdessen diese
# Adresse, dort schaut der Nutzer selbst nach.
SOURCE_URL = "https://github.com/noagnos3-create/NoaToDo"

# Optionaler Build-Stempel (von tools/build_exe.py erzeugt, nur im Bundle).
try:  # pragma: no cover, existiert nur im gebauten Bundle
    import _buildstamp as _stamp
except Exception:
    _stamp = None

BUILD_DATE: str | None = getattr(_stamp, "BUILD_DATE", None)
BUILD_COMMIT: str | None = getattr(_stamp, "BUILD_COMMIT", None)
# Wurde die .exe nach dem Bauen signiert? Setzt der Build-Schritt, der wirklich
# signiert hat. Default False, damit die App nie eine Signatur behauptet, die
# es nicht gibt (G22; diese Fassung ist unsigniert, N11.29 b).
BUILD_SIGNED: bool = bool(getattr(_stamp, "SIGNED", False))
# Frontend-Hash-Manifest fuer Gate G27: {"frontend/app.js": "<sha256 hex>", ...}
FRONTEND_MANIFEST: dict = getattr(_stamp, "FRONTEND_MANIFEST", {}) or {}


def is_frozen() -> bool:
    """Laeuft die App als gefrorenes PyInstaller-Bundle (``NoaToDo.exe``)?"""
    return bool(getattr(sys, "frozen", False))


def is_release() -> bool:
    """Gilt die Release-Haertung (G34)?

    Genau dann, wenn das Programm gefroren laeuft. Ein Entwicklerstart aus dem
    Quellbaum darf DevTools weiter benutzen, der ausgelieferte Build nie.
    """
    return is_frozen()


def debug_enabled() -> bool:
    """DevTools/Diagnose an? (Gate G34 a, N11.12.2)

    Im Release **hart aus**, unabhaengig von der Umgebung. Nur im Quellbaum
    entscheidet ``NOATODO_DEBUG``.
    """
    if is_release():
        return False
    return os.environ.get("NOATODO_DEBUG", "").lower() in ("1", "true", "yes")


def bundle_dir() -> str:
    """Wurzel der mitgelieferten Dateien (Frontend, Icon).

    Gefroren: der von PyInstaller entpackte Temp-Ordner (``sys._MEIPASS``),
    der pro Start frisch ist und beim Ende wieder verschwindet. Im Quellbaum:
    der ``Code``-Ordner, in dem diese Datei liegt.
    """
    if is_frozen():
        base = getattr(sys, "_MEIPASS", None)
        if base:
            return base
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts: str) -> str:
    """Pfad zu einer mitgelieferten Datei, in beiden Betriebsarten korrekt."""
    return os.path.join(bundle_dir(), *parts)


def frontend_dir() -> str:
    """Ordner mit ``index.html``/``app.js``/``style.css``/``fonts``."""
    return resource_path("frontend")


def index_html() -> str:
    return resource_path("frontend", "index.html")


def icon_path() -> str:
    return resource_path("frontend", "icon.ico")


def app_dir() -> str:
    """Ordner, in dem die App "wohnt" (nicht der entpackte Bundle-Ordner).

    Gefroren: der Ordner der ``.exe`` (dort wuerde eine daneben gelegte
    Alt-Datei liegen). Im Quellbaum: der ``Code``-Ordner. Wird fuer Altlasten
    gebraucht (G33: alte Dev-Datenbank ``data/tasks.db``), nie fuer Tresor,
    Konfig oder Profil: die liegen an ihren eigenen, vom Nutzer bzw. von
    ``%LOCALAPPDATA%`` bestimmten Orten.
    """
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def version_line() -> str:
    """Kurzform "1.0.0 (2026-08-10)" bzw. "1.0.0 (dev)" fuer Log und Status."""
    return f"{VERSION} ({BUILD_DATE or 'dev'})"


def build_info() -> dict:
    """Die Werte fuer das Status-Modal (V10)."""
    return {
        "version": VERSION,
        "build_date": BUILD_DATE,
        "commit": BUILD_COMMIT,
        "frozen": is_frozen(),
        "signed": BUILD_SIGNED,
        "source": SOURCE_URL,
    }
