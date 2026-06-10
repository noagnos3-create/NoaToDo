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

def _get_hwnd(window) -> int:
    """HWND des PyWebView-Fensters: direkt via window.native (WinForms-Form-Handle).

    PyWebView setzt window.native = BrowserForm-Instanz in BrowserForm.__init__,
    bevor on_start aufgerufen wird. Der native Handle ist deshalb immer verfuegbar
    und zuverlässiger als eine Fenstersuche per Titel oder PID.
    """
    try:
        # ToInt64 statt ToInt32: ein IntPtr-Handle kann auf 64-bit-Systemen
        # oberhalb von 2^31 liegen; ToInt32 wuerfe dann eine OverflowException
        # und Schutz/Theme blieben lautlos aus.
        return int(window.native.Handle.ToInt64())
    except Exception:
        return 0


# Screenshot-Schutz (Phase 6.5 / Gate G26): WDA_EXCLUDEFROMCAPTURE blendet das
# Fenster in Screenshots, Snipping Tool und Bildschirmfreigaben schwarz aus
# (Windows 10 2004+). WDA_MONITOR ist der schwächere Fallback älterer Systeme.
# Schützt nicht gegen ein abfotografierendes Handy. Ein Settings-Schalter dafür
# kann später ergänzt werden; Default ist AN.
_WDA_MONITOR            = 0x00000001
_WDA_EXCLUDEFROMCAPTURE = 0x00000011


def _apply_screenshot_protection(hwnd: int) -> None:
    """Nimmt das App-Fenster aus jeder Bildschirmaufnahme heraus (best effort)."""
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
        hwnd = _get_hwnd(window)
        _apply_screenshot_protection(hwnd)
        _apply_window_icon(window, os.path.join(HERE, "frontend", "icon.ico"))
        raw = database.get_setting("dark")
        initial_dark = str(raw).lower() != "false" if raw is not None else True
        _apply_titlebar_theme(hwnd, initial_dark)

        def _on_setting_change(key: str, value) -> None:
            if key == "dark":
                _apply_titlebar_theme(_get_hwnd(window), str(value).lower() not in ("false", "0", ""))

        api._on_setting_change = _on_setting_change

        def _on_frame_restored() -> None:
            # Nach Rückkehr aus dem Mini-Modus war der native Rahmen kurz
            # ausgeblendet (rahmenloses Lesefenster). Die Titelleisten-Farbe
            # erneut an das aktuelle Theme anpassen.
            raw2 = database.get_setting("dark")
            dark = str(raw2).lower() != "false" if raw2 is not None else True
            _apply_titlebar_theme(_get_hwnd(window), dark)

        api._on_frame_restored = _on_frame_restored

    icon = os.path.join(HERE, "frontend", "icon.ico")
    webview.start(on_start, debug=_debug_enabled(), icon=icon)


def _debug_enabled() -> bool:
    """DevTools aktivieren, wenn NOATODO_DEBUG gesetzt ist."""
    return os.environ.get("NOATODO_DEBUG", "").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    main()
