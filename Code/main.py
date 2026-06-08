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

# Titelleiste: Farben passend zu den CSS-Design-Tokens (dark/light --surface).
_TB_DARK  = "#1f1b14"
_TB_LIGHT = "#faf6ee"
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10 1903+
_DWMWA_CAPTION_COLOR           = 35  # Windows 11 22000+


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
        # Unter der normalen Layout-Mindestgröße, damit der Mini-Modus
        # (Api.set_mini, ~360px breit, oben rechts angeheftet) wirklich
        # schrumpfen kann und nicht von der OS-Mindestgröße geblockt wird.
        min_size=(340, 480),
    )
    api._window = window  # privat, sonst kollidiert es mit PyWebViews Methoden-Introspektion

    def on_start():
        _register_session_lock_hook(window, api)
        hwnd = ctypes.windll.user32.FindWindowW(None, "NoaToDo")
        raw = database.get_setting("dark")
        initial_dark = str(raw).lower() != "false" if raw is not None else True
        _apply_titlebar_theme(hwnd, initial_dark)

        def _on_setting_change(key: str, value) -> None:
            if key == "dark":
                h = ctypes.windll.user32.FindWindowW(None, "NoaToDo")
                _apply_titlebar_theme(h, str(value).lower() not in ("false", "0", ""))

        api._on_setting_change = _on_setting_change

    icon = os.path.join(HERE, "frontend", "icon.ico")
    webview.start(on_start, debug=_debug_enabled(), icon=icon)


def _debug_enabled() -> bool:
    """DevTools aktivieren, wenn NOATODO_DEBUG gesetzt ist."""
    return os.environ.get("NOATODO_DEBUG", "").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    main()
