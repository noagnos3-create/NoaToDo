"""NoaToDo, Einstiegspunkt (Bauplan Phase 3).

Erzeugt die Api-Bridge, öffnet das PyWebView-Fenster mit ``js_api`` und stellt
einen Kanal Backend -> Frontend bereit (für Lock-Events).
Der Windows-Sitzungssperre-Hook ist als Platzhalter vorgesehen (echte Logik in
Phase 8 / Bauplan B.8).
"""
from __future__ import annotations

import ctypes
import json
import os
import shutil
import tempfile
import time

import webview

from backend import db as db_module
from backend.api import Api

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "frontend", "index.html")

# Fester WebView2-Profilordner (Gate G14). Ersetzt den frueheren Privatmodus, der
# pro Start ein neues Temp-Profil anlegte und sich anhaeufte. Liegt unter
# %LOCALAPPDATA%\NoaToDo\webview, also benutzerprivat. Enthaelt nur nicht-sensiblen
# UI-Cache (eigene HTML/CSS/JS/Fonts, GPU-Status), nie Aufgabeninhalte: das
# Frontend nutzt kein localStorage/IndexedDB/Cookies/fetch, alle Daten kommen ueber
# die In-Memory-Bridge ins DOM. Das sichere Wischen bei Lock/Panic kommt in Phase 8
# (siehe Bauplan Gate G14).
_LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
PROFILE_DIR = os.path.join(_LOCALAPPDATA, "NoaToDo", "webview")

# Haelt den Single-Instance-Mutex fuer die gesamte Prozesslebensdauer offen.
_single_instance_handle = None

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

    WICHTIG (Race): Der an ``webview.start`` uebergebene on_start-Callback laeuft
    in einem eigenen Thread und kann feuern, BEVOR PyWebView ``window.native``
    (die BrowserForm) gesetzt hat. In diesem Fenster ist ``window.native`` noch
    ``None`` und der Handle damit 0. Mit ``wait=True`` wird deshalb kurz (bis ~5 s)
    auf den Handle gepollt, statt 0 zurueckzugeben.
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


# Die optisch hoehere Titelleiste wird NICHT nativ erzeugt: ein per WM_NCCALCSIZE
# vergroesserter nicht-Client-Bereich liess die Zusatzhoehe unbemalt (weisser
# Streifen), weil DWM die Caption nur in Standardhoehe bemalt und es keinen API-Weg
# gibt, diesen Streifen zu fuellen. Stattdessen rueckt das Frontend seinen Inhalt um
# 6px nach unten und legt diese 6px in Titelleistenfarbe (--surface, identisch zur
# per DWM gesetzten Caption-Farbe) an die Oberkante (siehe style.css, border-top auf
# .app). Native Caption und Streifen sind dadurch nahtlos und farbgleich.


_APP_USER_MODEL_ID = "NoaGnos.NoaToDo"


def _set_app_user_model_id() -> None:
    """Eigene AppUserModelID setzen, damit die Taskbar das App-Icon (statt das
    von python.exe) zeigt und Fenster korrekt unter NoaToDo gruppiert."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_USER_MODEL_ID)
    except Exception:
        pass


# ctypes-Strukturen fuer den Fenster-Eigenschaftsspeicher (IPropertyStore).
# Hierueber bekommt der Taskbar-Button sein Icon, siehe _apply_taskbar_identity.
class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_uint32)]


class _PROPVARIANT(ctypes.Structure):
    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("p", ctypes.c_void_p),
        ("p2", ctypes.c_void_p),
    ]


def _make_guid(text: str) -> _GUID:
    g = _GUID()
    ctypes.oledll.ole32.CLSIDFromString(ctypes.c_wchar_p(text), ctypes.byref(g))
    return g


def _apply_taskbar_identity(hwnd: int, app_id: str, icon_path: str) -> None:
    """Verknuepft den Taskbar-Button mit AppID UND Icon.

    Sobald ein Fenster eine explizite AppUserModelID hat (siehe
    ``_set_app_user_model_id``), leitet Windows das *Taskbar*-Icon nicht mehr aus
    ``Form.Icon`` ab, sondern sucht das fuer diese AppID registrierte Icon (sonst
    nur ueber eine installierte Startmenue-Verknuepfung). NoaToDo hat keine solche
    Verknuepfung, daher zeigt die Taskbar das generische python.exe-Icon, waehrend
    die Titelleiste ueber ``Form.Icon`` korrekt das Logo zeigt. Hier wird dem
    Fenster-Eigenschaftsspeicher deshalb ``System.AppUserModel.RelaunchIconResource``
    (= ``icon.ico,0``) plus die AppID mitgegeben, damit der Taskbar-Button das Logo
    nutzt. Laeuft bereits auf dem UI-Thread (Aufruf aus ``_startup_window_setup``).
    """
    if not hwnd or not os.path.isfile(icon_path):
        return
    # System.AppUserModel.* teilen alle dieselbe FMTID; pid 5 = ID, pid 3 = RelaunchIconResource.
    fmtid_appusermodel = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"
    iid_ipropertystore = "{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}"
    store = ctypes.c_void_p()
    try:
        ctypes.oledll.shell32.SHGetPropertyStoreForWindow(
            ctypes.c_void_p(hwnd),
            ctypes.byref(_make_guid(iid_ipropertystore)),
            ctypes.byref(store),
        )
    except Exception:
        return
    if not store:
        return
    try:
        vtbl = ctypes.cast(store, ctypes.POINTER(ctypes.c_void_p))[0]
        funcs = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))
        set_value = ctypes.WINFUNCTYPE(
            ctypes.HRESULT, ctypes.c_void_p,
            ctypes.POINTER(_PROPERTYKEY), ctypes.POINTER(_PROPVARIANT),
        )(funcs[6])
        commit = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p)(funcs[7])
        release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(funcs[2])

        fmtid = _make_guid(fmtid_appusermodel)
        entries = [
            (_PROPERTYKEY(fmtid, 5), app_id),
            (_PROPERTYKEY(fmtid, 3), icon_path + ",0"),
        ]
        for key, value in entries:
            pv = _PROPVARIANT()
            try:
                ctypes.oledll.propsys.InitPropVariantFromString(
                    ctypes.c_wchar_p(value), ctypes.byref(pv))
                set_value(store, ctypes.byref(key), ctypes.byref(pv))
            finally:
                ctypes.oledll.ole32.PropVariantClear(ctypes.byref(pv))
        commit(store)
        release(store)
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


def _run_on_ui_thread(window, work) -> None:
    """Native Fenster-Mutationen asynchron auf dem WinForms-UI-Thread ausfuehren.

    NACHGEWIESENER DEADLOCK (Stack-Dump 2026-06-13): WinForms-Aufrufe ueber
    Thread-Grenzen (z. B. ``window.native.Icon = ...`` in ``_apply_window_icon``)
    direkt aus dem ``on_start``-/API-Worker-Thread blockieren die Nachrichten-
    schleife, wenn der UI-Thread gerade das WebView2-Steuerelement initialisiert
    (``edgechromium.py:__init__``). Folge: das Fenster erscheint nie, mal weiss,
    mal "reagiert nicht", je nach Timing. ``BeginInvoke`` stellt die Arbeit nur in
    die UI-Warteschlange und kehrt sofort zurueck; sie laeuft, sobald der UI-Thread
    wieder Nachrichten verarbeitet (also nach der WebView2-Init). Kein blockierender
    Cross-Thread-Aufruf mehr, damit kein Deadlock. Wartet kurz, bis das Fenster-
    handle existiert, sonst wirft ``BeginInvoke``.
    """
    deadline = time.monotonic() + 5.0
    while True:
        native = getattr(window, "native", None)
        try:
            ready = native is not None and native.IsHandleCreated
        except Exception:
            ready = False
        if ready:
            try:
                from System import Action
                native.BeginInvoke(Action(work))
            except Exception:
                pass
            return
        if time.monotonic() > deadline:
            return
        time.sleep(0.05)


def emit(window, event: str, payload=None) -> None:
    """Backend -> Frontend: ruft ``window.noa.<event>(payload)`` im Frontend auf.

    Wird für ``onLocked`` genutzt (Bauplan B.2). Robust gegen ein noch nicht
    geladenes Frontend.
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


def _acquire_single_instance() -> bool:
    """Belegt einen benannten Windows-Mutex (Gate G19, vorgezogen).

    Verhindert eine zweite Instanz: zwei Prozesse wuerden sich denselben festen
    WebView2-Profilordner (und spaeter ``tasks.db.enc`` bzw. dessen Arbeitskopie)
    gegenseitig sperren oder ueberschreiben (weisses Fenster, "reagiert nicht",
    spaeter Datenkorruption). Gibt True zurueck, wenn diese Instanz die erste ist.
    """
    global _single_instance_handle
    kernel32 = ctypes.windll.kernel32
    _single_instance_handle = kernel32.CreateMutexW(None, False, "Local\\NoaToDoSingleton")
    _ERROR_ALREADY_EXISTS = 183
    return kernel32.GetLastError() != _ERROR_ALREADY_EXISTS


def _cleanup_stale_webview_profiles() -> None:
    """Loescht verwaiste WebView2-Profile aus frueheren Privatmodus-Starts (Gate G14).

    Bis 2026-06-20 lief die App mit ``private_mode=True``: pywebview legte pro Start
    ein Profil unter ``%TEMP%\\tmpXXXXXXXX\\EBWebView`` an, das bei hartem Beenden
    nicht aufgeraeumt wurde und sich anhaeufte (zeitweise Starthaenger ueber eine
    Minute). Seit dem Wechsel auf ``PROFILE_DIR`` entstehen keine neuen mehr; dieser
    Einmal-Wisch raeumt die Altlasten weg. Es werden nur Temp-Ordner mit der
    typischen ``tmp*``-Benennung UND einer ``EBWebView``-Signatur angefasst; noch
    gesperrte Ordner (laufende ``msedgewebview2.exe``) werden uebersprungen.
    """
    temp_root = tempfile.gettempdir()
    try:
        entries = os.listdir(temp_root)
    except OSError:
        return
    for name in entries:
        if not name.startswith("tmp"):
            continue
        candidate = os.path.join(temp_root, name)
        if not os.path.isdir(os.path.join(candidate, "EBWebView")):
            continue
        try:
            shutil.rmtree(candidate)
        except OSError:
            # In Benutzung oder gesperrt: ignorieren, kein harter Fehler.
            pass


def _purge_webview_cache() -> None:
    """Loescht HTTP- und Code-Cache im WebView2-Profil bei jedem Start.

    Bug (2026-06-23): Seit dem Wechsel auf den festen Profilordner (PROFILE_DIR,
    kein Privatmodus mehr, Stand 2026-06-20) ueberlebt der WebView2-Disk-Cache den
    Neustart. Das Frontend wird per ``file://`` geladen; fuer Dateien ohne
    Cache-Header vergibt Chromium eine heuristische Frische (rund 10 % des
    Dateialters) und liefert ``index.html``/``app.js``/``style.css`` aus dem Cache,
    statt sie frisch von der Platte zu lesen. Folge: Aenderungen am Frontend
    erscheinen erst Stunden bis einen Tag spaeter, selbst nach komplettem Schliessen
    und Neustart. Frueher (Temp-Profil pro Start) trat das nicht auf, weil der Cache
    jedes Mal verschwand. Hier wird genau dieses Verhalten gezielt wiederhergestellt,
    ohne das ganze Profil zu opfern: nur die reinen Cache-Ordner ("Cache",
    "Code Cache") werden entfernt, der GPU-/Shader-Status bleibt erhalten. Laeuft
    vor ``webview.start``, solange WebView2 die Ordner noch nicht gesperrt hat;
    gesperrte Ordner (verwaister ``msedgewebview2.exe``) werden uebersprungen.
    """
    if not os.path.isdir(PROFILE_DIR):
        return
    cache_dir_names = {"Cache", "Code Cache"}
    for root, dirs, _files in os.walk(PROFILE_DIR):
        for name in list(dirs):
            if name in cache_dir_names:
                try:
                    shutil.rmtree(os.path.join(root, name))
                except OSError:
                    # Gesperrt oder in Benutzung: ignorieren, kein harter Fehler.
                    pass
                # Nicht in den (idealerweise geloeschten) Cache-Ordner absteigen.
                dirs.remove(name)


def _frontend_stamp() -> str:
    """Aenderungszeit der wichtigsten Frontend-Dateien als kurzer Stempel.

    Reine Diagnose: macht im Terminal sichtbar, welcher Frontend-Stand geladen
    wird, damit "es hat sich nichts geaendert" sofort auf alt-laufendes Fenster
    vs. echter Neustart zurueckgefuehrt werden kann.
    """
    parts = []
    for name in ("frontend/index.html", "frontend/app.js", "frontend/style.css"):
        path = os.path.join(HERE, name)
        try:
            ts = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(path)))
        except OSError:
            ts = "??"
        parts.append(f"{os.path.basename(name)} {ts}")
    return "Frontend: " + ", ".join(parts)


def main() -> None:
    # Sichtbare Startmeldung: bestaetigt im Terminal, welcher Code laeuft. Hilft,
    # einen veralteten Start zu erkennen (fehlt die Zeile, laeuft nicht dieser Stand).
    # Zusaetzlich die Aenderungszeit der geladenen Frontend-Dateien ausgeben: das
    # Frontend wird per file:// frisch von der Platte geladen (kein Hot-Reload im
    # laufenden Fenster), daher zeigen diese Zeitstempel zweifelsfrei, welcher
    # Stand gerade geladen wird. Stimmen sie nicht mit der letzten Bearbeitung
    # ueberein, laeuft noch ein altes Fenster: erst ganz schliessen, dann neu starten.
    print("[NoaToDo] Start. " + _frontend_stamp(), flush=True)

    # Single-Instance-Schutz (Gate G19): zweite Instanz sofort beenden, sonst
    # Profil-/DB-Kollision auf dem gemeinsamen festen Profilordner.
    if not _acquire_single_instance():
        ctypes.windll.user32.MessageBoxW(
            0,
            "NoaToDo läuft bereits. Es kann nur eine Instanz geöffnet sein.",
            "NoaToDo",
            0x40,  # MB_ICONINFORMATION
        )
        print("[NoaToDo] Bereits aktiv, zweite Instanz beendet sich.", flush=True)
        return

    # Altlasten frueherer Privatmodus-Starts einmalig wegraeumen (Gate G14).
    _cleanup_stale_webview_profiles()

    # WebView2-Cache bei jedem Start leeren, damit Frontend-Aenderungen sofort
    # sichtbar sind (siehe _purge_webview_cache). Behebt den "alte Version laeuft
    # trotz Neustart"-Bug, der mit dem festen Profilordner aufkam.
    _purge_webview_cache()

    # Per-Monitor-V2-DPI-Kontext: muss vor dem ersten Fenster gesetzt sein.
    # Python.exe hat kein DPI-Manifest und laeuft sonst als DPI-unaware,
    # was bewirkt, dass Titelleiste und Rahmen bei erhoehter Monitor-Skalierung
    # kleiner erscheinen als bei anderen Windows-Apps. Scheitert dieser Aufruf
    # (z.B. weil PyWebView ihn schon gesetzt hat), ist das kein Fehler.
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))

    # Vor dem Fenster-Start: Taskbar soll das App-Icon statt python.exe zeigen.
    _set_app_user_model_id()

    # Schicht-1-Schlüssel: in der Entwicklung fester Dev-Key (Bauplan Phase 1).
    # In Phase 8 wird er aus der Passphrase via Argon2id abgeleitet.
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
        # Windows-Sitzungssperre-Hook entfaellt bewusst (N11.8.4: Win+L loest keine
        # App-Sperre aus; die Auto-Sperre laeuft stattdessen als Hintergrund-Timer).
        # Alle nativen Fenster-Operationen laufen ueber den UI-Thread (BeginInvoke),
        # NICHT direkt aus diesem Worker-Thread: sonst Deadlock mit der WebView2-
        # Initialisierung, siehe _run_on_ui_thread. Im UI-Thread existiert das
        # Handle bereits, daher _get_hwnd ohne wait.
        def _startup_window_setup():
            hwnd = _get_hwnd(window)
            icon_path = os.path.join(HERE, "frontend", "icon.ico")
            _apply_window_icon(window, icon_path)
            # Titelleiste kommt aus Form.Icon (oben), die Taskbar braucht wegen der
            # expliziten AppUserModelID ein eigens registriertes Icon, sonst bleibt
            # der Taskbar-Button generisch. Siehe _apply_taskbar_identity.
            _apply_taskbar_identity(hwnd, _APP_USER_MODEL_ID, icon_path)
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

        _run_on_ui_thread(window, _startup_window_setup)

        def _on_setting_change(key: str, value) -> None:
            if key == "dark":
                dark = str(value).lower() not in ("false", "0", "")
                _run_on_ui_thread(window, lambda: _apply_titlebar_theme(_get_hwnd(window), dark))

        api._on_setting_change = _on_setting_change

        def _on_frame_changed(mini: bool) -> None:
            # Der Mini-Modus wechselt FormBorderStyle und erzeugt damit das
            # native Fensterhandle neu (die HWND-Zahl aendert sich). Nach dem
            # Verlassen muss die Titelleisten-Farbe neu ans Theme angeglichen
            # werden. Ueber den UI-Thread, sonst Cross-Thread-Deadlock wie in
            # on_start.
            def _frame_setup():
                h = _get_hwnd(window)
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

            _run_on_ui_thread(window, _frame_setup)

        api._on_frame_changed = _on_frame_changed

    icon = os.path.join(HERE, "frontend", "icon.ico")
    # Fester WebView2-Profilordner statt Privatmodus (Gate G14, Stand 2026-06-20).
    # Frueher lief die App mit private_mode=True und legte pro Start ein neues
    # Temp-Profil an, das sich anhaeufte und den Start ausbremste. Der feste Ordner
    # (private_mode=False, storage_path=PROFILE_DIR) ist erst zusammen mit dem
    # Single-Instance-Schutz oben (Gate G19) tragfaehig: er verhindert, dass eine
    # zweite/verwaiste Instanz das geteilte Profil sperrt (sonst weisses Fenster,
    # "reagiert nicht"). Was im Profil liegt, ist nur nicht-sensibler UI-Cache, nie
    # Aufgabeninhalte (siehe Kommentar an PROFILE_DIR). Das sichere Wischen dieses
    # Ordners bei lock()/panic()/sauberem Quit folgt in Phase 8 (Bauplan G14).
    os.makedirs(PROFILE_DIR, exist_ok=True)
    webview.start(
        on_start,
        debug=_debug_enabled(),
        icon=icon,
        private_mode=False,
        storage_path=PROFILE_DIR,
    )


def _debug_enabled() -> bool:
    """DevTools aktivieren, wenn NOATODO_DEBUG gesetzt ist."""
    return os.environ.get("NOATODO_DEBUG", "").lower() in ("1", "true", "yes")


if __name__ == "__main__":
    main()
