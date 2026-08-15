"""Windows-Hell/Dunkel-Zustand lesen und beobachten (N11.6, Bauplan B.6).

Bei ``theme = auto`` (Default) folgt NoaToDo dem Windows-Theme. Der Bauplan
schreibt dafuer zwei Wege vor, die dieses Modul in einer Schleife vereint:

* **Ereignisbasiert (Hauptweg):** ``RegNotifyChangeKeyValue`` auf dem Schluessel
  ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize``
  meldet jede Aenderung sofort. Das ist derselbe Wert, den Windows beim
  Umschalten von "Hell"/"Dunkel" schreibt (``AppsUseLightTheme``).
* **Gegenpruefung alle 60 s (Rueckfalllinie, U16-Entscheid 2026-07-15):** der
  Wait laeuft mit genau diesem Timeout ab und liest den Wert erneut. Damit
  zieht die App auch dann nach, wenn die Benachrichtigung ausbleibt.

Bewusst ohne Fensterklasse und ohne ``WM_SETTINGCHANGE``-Hook: die Registry-
Benachrichtigung braucht keine Message-Loop und laeuft daher in einem eigenen
Daemon-Thread, ohne sich mit dem WinForms-UI-Thread zu verzahnen (siehe die
Thread-Regeln in CLAUDE.md).

Das Modul liest ausschliesslich einen oeffentlichen Anzeige-Zustand des
Betriebssystems. Es beruehrt keine Tresor-Daten und keine Schluessel.
"""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable, Optional

try:
    import winreg
except ImportError:  # pragma: no cover - nur auf Nicht-Windows
    winreg = None  # type: ignore[assignment]

# Der Schluessel, den Windows beim Hell/Dunkel-Umschalten schreibt.
_PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
_VALUE = "AppsUseLightTheme"

# Win32-Konstanten
_REG_NOTIFY_CHANGE_LAST_SET = 0x00000004
_KEY_NOTIFY = 0x0010
_INFINITE = 0xFFFFFFFF
_WAIT_OBJECT_0 = 0x00000000
_WAIT_TIMEOUT = 0x00000102

# Gegenpruefung alle 60 s (B.6/N11.6, U16). Das Ereignis bleibt der Hauptweg.
RECHECK_MS = 60_000


def read_os_dark() -> Optional[bool]:
    """``True`` = Windows zeigt Apps dunkel, ``False`` = hell, ``None`` = unlesbar.

    ``None`` ist ein ehrliches "weiss nicht" (Wert fehlt, Registry nicht lesbar,
    fremdes Betriebssystem): der Aufrufer behaelt dann sein bisheriges Theme,
    statt eine Umschaltung zu raten.
    """
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PERSONALIZE) as key:
            value, _kind = winreg.QueryValueEx(key, _VALUE)
        # 1 = Apps hell, 0 = Apps dunkel (Windows-Semantik, invertiert zu unserer).
        return int(value) == 0
    except Exception:
        return None


class ThemeWatcher:
    """Beobachtet den Windows-Hell/Dunkel-Zustand in einem Daemon-Thread.

    ``callback(dark: bool)`` feuert nur bei einer echten Aenderung gegenueber
    dem zuletzt gemeldeten Wert, nie bei jedem Tick. Ein unlesbarer Wert
    (``None``) meldet nichts: kein Rauschen, keine geratene Umschaltung.
    """

    def __init__(self, callback: Callable[[bool], None]):
        self._callback = callback
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = None          # Win32-Event zum sofortigen Aufwecken
        self._started = False
        self._lock = threading.Lock()
        self.last: Optional[bool] = read_os_dark()

    # -- Lebenszyklus ------------------------------------------------------
    def start(self) -> None:
        """Startet den Beobachter. Idempotent (mehrfacher Aufruf ist ein No-op)."""
        with self._lock:
            if self._started or winreg is None:
                return
            self._started = True
            self._stop_evt = ctypes.windll.kernel32.CreateEventW(None, True, False, None)
            self._thread = threading.Thread(
                target=self._run, name="noatodo-ostheme", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Beendet den Beobachter (weckt den Wait sofort auf)."""
        with self._lock:
            if not self._started:
                return
            self._started = False
            if self._stop_evt:
                ctypes.windll.kernel32.SetEvent(self._stop_evt)

    # -- Innenleben --------------------------------------------------------
    def _run(self) -> None:
        kernel32 = ctypes.windll.kernel32
        advapi32 = ctypes.windll.advapi32
        notify_evt = kernel32.CreateEventW(None, True, False, None)
        key = None
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _PERSONALIZE, 0,
                winreg.KEY_READ | _KEY_NOTIFY)
            handles = (wintypes.HANDLE * 2)(
                wintypes.HANDLE(notify_evt), wintypes.HANDLE(self._stop_evt))
            while self._started:
                # Vor jedem Warten neu registrieren: die Benachrichtigung gilt
                # laut Win32-Vertrag immer nur fuer EINE Aenderung.
                kernel32.ResetEvent(notify_evt)
                rc = advapi32.RegNotifyChangeKeyValue(
                    wintypes.HANDLE(int(key)), False,
                    _REG_NOTIFY_CHANGE_LAST_SET, wintypes.HANDLE(notify_evt), True)
                if rc != 0:
                    # Registrierung fehlgeschlagen: nur noch die 60-s-Gegenpruefung
                    # (der Hauptweg faellt aus, die Rueckfalllinie traegt weiter).
                    kernel32.WaitForSingleObject(
                        wintypes.HANDLE(self._stop_evt), RECHECK_MS)
                else:
                    kernel32.WaitForMultipleObjects(2, handles, False, RECHECK_MS)
                if not self._started:
                    break
                self._poll()
        except Exception:
            # Der Beobachter ist Komfort, kein Sicherheitsweg: faellt er aus,
            # bleibt das zuletzt gesetzte Theme stehen (kein Absturz, keine
            # Fehlermeldung an den Nutzer).
            pass
        finally:
            try:
                if key is not None:
                    key.Close()
            except Exception:
                pass
            for handle in (notify_evt, self._stop_evt):
                try:
                    if handle:
                        kernel32.CloseHandle(handle)
                except Exception:
                    pass
            self._stop_evt = None

    def _poll(self) -> None:
        dark = read_os_dark()
        if dark is None or dark == self.last:
            return
        self.last = dark
        try:
            self._callback(dark)
        except Exception:
            pass
