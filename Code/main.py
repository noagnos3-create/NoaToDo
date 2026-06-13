"""NoaToDo, Einstiegspunkt (Bauplan Phase 3).

Erzeugt die Api-Bridge, öffnet das PyWebView-Fenster mit ``js_api`` und stellt
einen Kanal Backend -> Frontend bereit (für Sync-/Notification-/Lock-Events).
Der Windows-Sitzungssperre-Hook ist als Platzhalter vorgesehen (echte Logik in
Phase 11 / Bauplan B.8).
"""
from __future__ import annotations

import ctypes
import json
import os
import time

import webview

from backend import db as db_module
from backend.api import Api

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "frontend", "index.html")

_TB_DARK  = "#1f1b14"   # entspricht --surface (dark) aus style.css
_TB_LIGHT = "#faf6ee"   # entspricht --surface (light) aus style.css
_TB_TEXT_DARK  = "#f2ead9"  # heller Titeltext auf dunkler Leiste
_TB_TEXT_LIGHT = "#1f1b14"  # dunkler Titeltext auf heller Leiste
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10 1903+
_DWMWA_CAPTION_COLOR           = 35  # Windows 11 22000+
_DWMWA_TEXT_COLOR              = 36  # Windows 11 22000+
# SetWindowPos-Flags fuer Frame-Neuberechnung nach DWM-Aenderungen
_SWP_NOSIZE        = 0x0001
_SWP_NOMOVE        = 0x0002
_SWP_NOZORDER      = 0x0004
_SWP_NOOWNERZORDER = 0x0200
_SWP_FRAMECHANGED  = 0x0020

def _get_hwnd(window, wait: bool = False) -> int:
    """HWND des PyWebView-Fensters: direkt via window.native (WinForms-Form-Handle).

    WICHTIG (Race, Gate G26): Der an ``webview.start`` uebergebene on_start-
    Callback laeuft in einem eigenen Thread und feuert nachweislich, BEVOR
    PyWebView ``window.native`` (die BrowserForm) gesetzt hat. In diesem Fenster
    ist ``window.native`` noch ``None`` und der Handle damit 0. Frueher lief der
    Screenshot-Schutz dann lautlos ins Leere (``_apply_screenshot_protection(0)``
    kehrt sofort zurueck), weshalb Screenshots weiterhin moeglich waren. Mit
    ``wait=True`` wird deshalb kurz (bis ~5 s) auf den Handle gepollt.
    """
    deadline = time.monotonic() + 5.0
    while True:
        try:
            native = getattr(window, "native", None)
            if native is not None:
                # ToInt64 statt ToInt32: ein IntPtr-Handle kann auf 64-bit-
                # Systemen oberhalb von 2^31 liegen; ToInt32 wuerfe dann eine
                # OverflowException und Schutz/Theme blieben lautlos aus.
                h = int(native.Handle.ToInt64())
                if h:
                    return h
        except Exception:
            pass
        if not wait or time.monotonic() > deadline:
            return 0
        time.sleep(0.05)


# Screenshot-Schutz (Phase 6.5 / Gate G26): WDA_EXCLUDEFROMCAPTURE blendet das
# Fenster in Screenshots, Snipping Tool und Bildschirmfreigaben schwarz aus
# (Windows 10 2004+). WDA_MONITOR ist der schwächere Fallback älterer Systeme.
# Schützt nicht gegen ein abfotografierendes Handy. Ein Settings-Schalter dafür
# kann später ergänzt werden; Default ist AN.
_WDA_MONITOR            = 0x00000001
_WDA_EXCLUDEFROMCAPTURE = 0x00000011


def _apply_screenshot_protection(hwnd: int) -> None:
    """Nimmt das App-Fenster aus jeder Bildschirmaufnahme heraus (best effort).

    Die Affinity wird auf dem Top-Level-Fenster gesetzt; das schliesst den
    WebView2-Inhalt (Kindfenster ``Chrome_WidgetWin_0``) bei der Aufnahme mit
    ein, ein separates Setzen auf den Kindfenstern ist nicht noetig (empirisch
    geprueft: zentrale Pixel des maximierten Fensters werden schwarz aufgenommen).
    Wichtig: Nach einer Handle-Neuerzeugung (z. B. FormBorderStyle-Wechsel im
    Mini-Modus) faellt die Affinity auf 0 zurueck und muss neu gesetzt werden.
    """
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        user32.SetWindowDisplayAffinity.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
        if not user32.SetWindowDisplayAffinity(hwnd, _WDA_EXCLUDEFROMCAPTURE):
            user32.SetWindowDisplayAffinity(hwnd, _WDA_MONITOR)
    except Exception:
        pass


def _apply_titlebar_theme(hwnd: int, dark: bool) -> None:
    """Passt Titelleistenfarbe und Textmodus per DWM-API an das App-Theme an."""
    if not hwnd:
        return
    try:
        dwm = ctypes.windll.dwmapi
        dm = ctypes.c_int(1 if dark else 0)
        dwm.DwmSetWindowAttribute(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE,
                                  ctypes.byref(dm), ctypes.sizeof(dm))
        h = _TB_DARK if dark else _TB_LIGHT
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        colorref = ctypes.c_int(r | (g << 8) | (b << 16))
        dwm.DwmSetWindowAttribute(hwnd, _DWMWA_CAPTION_COLOR,
                                  ctypes.byref(colorref), ctypes.sizeof(colorref))
        # Titeltext passend zur Caption-Farbe: hell auf dunkel, dunkel auf hell.
        th = _TB_TEXT_DARK if dark else _TB_TEXT_LIGHT
        tr, tg, tb = int(th[1:3], 16), int(th[3:5], 16), int(th[5:7], 16)
        text_ref = ctypes.c_int(tr | (tg << 8) | (tb << 16))
        dwm.DwmSetWindowAttribute(hwnd, _DWMWA_TEXT_COLOR,
                                  ctypes.byref(text_ref), ctypes.sizeof(text_ref))
    except Exception:
        pass


def _set_app_user_model_id() -> None:
    """Eigene AppUserModelID setzen, damit die Taskbar das App-Icon (statt das
    von python.exe) zeigt und Fenster korrekt unter NoaToDo gruppiert."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NoaGnos.NoaToDo")
    except Exception:
        pass


def _apply_window_icon(window, icon_path: str) -> None:
    """Setzt das App-Logo als Fenster-Icon (Titelleiste oben links + Taskbar).

    Der ``icon=``-Parameter von ``webview.start`` greift unter dem WinForms/
    WebView2-Backend nicht zuverlässig für die Titelleiste, deshalb wird das
    Icon hier direkt auf die native WinForms-Form gesetzt. ``window.native`` ist
    ab ``on_start`` verfuegbar; System.Drawing ist via pythonnet geladen, sobald
    das Fenster lebt.
    """
    if not os.path.isfile(icon_path):
        return
    try:
        from System.Drawing import Icon  # pythonnet, erst nach webview-Start verfuegbar
        window.native.Icon = Icon(icon_path)
    except Exception:
        pass


def emit(window, event: str, payload=None) -> None:
    """Backend -> Frontend: ruft ``window.noa.<event>(payload)`` im Frontend auf.

    Wird für ``onSyncDone``, ``onNotification``, ``onLocked`` genutzt
    (Bauplan B.2). Robust gegen ein noch nicht geladenes Frontend.
    """
    if window is None:
        return
    arg = json.dumps(payload) if payload is not None else "undefined"
    # Abschluss mit ";0": evaluate_js liefert ein Primitive zurück. Sonst kann
    # pythonnet/WebView2 beim Serialisieren eines JS-Objekts in eine Rekursion
    # laufen (bekanntes pywebview-Verhalten auf Windows).
    js = f"window.noa && window.noa.{event} && window.noa.{event}({arg});0"
    try:
        window.evaluate_js(js)
    except Exception:
        pass


def _register_session_lock_hook(window, api: Api) -> None:
    """Platzhalter für den Windows-Sitzungssperre-Hook (Phase 11 / B.8).

    Geplant: ``WTSRegisterSessionNotification`` auf das Fensterhandle,
    ``WM_WTSSESSION_CHANGE`` abfangen und bei ``WTS_SESSION_LOCK`` ``api.lock()``
    aufrufen. Wird in Phase 11 implementiert.
    """
    # TODO(Phase 11): ctypes/pywin32 WTSRegisterSessionNotification verdrahten.
    return


def main() -> None:
    # Per-Monitor-V2-DPI-Kontext: muss vor dem ersten Fenster gesetzt sein.
    # Python.exe hat kein DPI-Manifest und laeuft sonst als DPI-unaware,
    # was bewirkt, dass Titelleiste und Rahmen bei erhoehter Monitor-Skalierung
    # kleiner erscheinen als bei anderen Windows-Apps. Scheitert dieser Aufruf
    # (z.B. weil PyWebView ihn schon gesetzt hat), ist das kein Fehler.
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))

    # Vor dem Fenster-Start: Taskbar soll das App-Icon statt python.exe zeigen.
    _set_app_user_model_id()

    # Schicht-1-Schlüssel: in der Entwicklung fester Dev-Key (Bauplan Phase 1).
    # In Phase 11 wird er aus der Passphrase via Argon2id abgeleitet.
    database = db_module.connect()
    api = Api(database)

    window = webview.create_window(
        "NoaToDo",
        INDEX,
        js_api=api,
        width=1200,
        height=800,
        # Die App startet maximiert (Vollbild-Fenster), nicht im kleinen
        # 1200x800-Fenster. Breite/Höhe bleiben als Größe nach dem Wieder-
        # herstellen aus dem Maximierungszustand erhalten.
        maximized=True,
        # Unter der normalen Layout-Mindestgröße, damit der Mini-Modus
        # (Api.set_mini, ~360px breit, oben rechts angeheftet) wirklich
        # schrumpfen kann und nicht von der OS-Mindestgröße geblockt wird.
        min_size=(340, 480),
    )
    api._window = window  # privat, sonst kollidiert es mit PyWebViews Methoden-Introspektion

    def on_start():
        _register_session_lock_hook(window, api)
        # wait=True: on_start kann feuern, bevor window.native gesetzt ist (Race),
        # siehe _get_hwnd. Ohne das Warten bliebe der Screenshot-Schutz lautlos aus.
        hwnd = _get_hwnd(window, wait=True)
        _apply_screenshot_protection(hwnd)
        _apply_window_icon(window, os.path.join(HERE, "frontend", "icon.ico"))
        raw = database.get_setting("dark")
        initial_dark = str(raw).lower() != "false" if raw is not None else True
        _apply_titlebar_theme(hwnd, initial_dark)
        # DWM-Frame-Neuberechnung: DWM-Attribute gelten visuell erst nach
        # SWP_FRAMECHANGED vollstaendig. Stellt sicher, dass die Titelleiste
        # sofort in der richtigen Hoehe und Farbe gerendert wird.
        if hwnd:
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOOWNERZORDER | _SWP_FRAMECHANGED,
            )

        def _on_setting_change(key: str, value) -> None:
            if key == "dark":
                _apply_titlebar_theme(_get_hwnd(window), str(value).lower() not in ("false", "0", ""))

        api._on_setting_change = _on_setting_change

        def _on_frame_changed(mini: bool) -> None:
            # Der Mini-Modus wechselt FormBorderStyle und erzeugt damit das
            # native Fensterhandle neu; dabei geht die Display-Affinity (Gate
            # G26) verloren. Nach jedem Wechsel (rein wie raus) den Schutz neu
            # setzen, das Handle frisch holen (die HWND-Zahl aendert sich).
            h = _get_hwnd(window)
            _apply_screenshot_protection(h)
            if not mini:
                # Rahmen ist zurueck: Titelleisten-Farbe wieder ans Theme angleichen.
                raw2 = database.get_setting("dark")
                dark = str(raw2).lower() != "false" if raw2 is not None else True
                _apply_titlebar_theme(h, dark)
                if h:
                    ctypes.windll.user32.SetWindowPos(
                        h, 0, 0, 0, 0, 0,
                        _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOOWNERZORDER | _SWP_FRAMECHANGED,
                    )

        api._on_frame_changed = _on_frame_changed

    icon = os.path.join(HERE, "frontend", "icon.ico")
    webview.start(on_start, debug=_debug_enabled(), icon=icon)


def _debug_enabled() -> bool:
    """DevTools aktivieren, wenn NOATODO_DEBUG gesetzt ist."""
    return os.environ.get("NOATODO_DEBUG", "").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    main()
