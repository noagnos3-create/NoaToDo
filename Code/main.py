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
import subprocess
import tempfile
import threading
import time

import webview

import buildinfo
from backend import config as config_module
from backend import radio as radio_module
from backend import security as security_module
from backend.api import Api

# Pfade zu mitgelieferten Dateien IMMER ueber buildinfo (Phase 9): im
# Quellbaum liegen sie neben dieser Datei, im One-file-Build in dem pro Start
# frisch entpackten Bundle-Ordner (sys._MEIPASS). ``HERE`` bleibt nur als
# Quellbaum-Bezug erhalten und darf nicht mehr fuer Frontend/Icon dienen.
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = buildinfo.index_html()
ICON = buildinfo.icon_path()

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

# Titelleistenfarben und die DWM-Attribute dazu stehen in wintheme.py (eine
# Quelle fuer das native Aussehen, siehe _apply_titlebar_theme weiter unten).
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
    """Passt Titelleistenfarbe und Textmodus per DWM-API an das App-Theme an.

    Die Umsetzung liegt in ``wintheme`` (eine Quelle fuer das native Aussehen),
    damit WebView-Fenster und natives Sperrfenster exakt dieselbe Titelleiste
    bekommen. Der Import ist bewusst lazy: er zieht System.Windows.Forms nach
    und soll erst laufen, wenn ohnehin schon ein Fenster existiert.
    """
    if not hwnd:
        return
    try:
        import wintheme
        wintheme.apply_titlebar_theme(hwnd, dark)
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


def _current_user_sid() -> str | None:
    """SID des aktuellen Benutzers als String (fuer den G19-Mutex-Namen).

    Ueber das Prozess-Token (OpenProcessToken -> GetTokenInformation(TokenUser)
    -> ConvertSidToStringSidW). Scheitert das, gibt es None zurueck; der
    Aufrufer faellt dann auf den alten ``Local\\``-Namen zurueck.
    """
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32
        # 64-bit-sichere Signaturen: Handles/Pointer sind c_void_p, nicht int.
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        advapi32.OpenProcessToken.argtypes = (
            ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p))
        advapi32.GetTokenInformation.argtypes = (
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32))
        advapi32.ConvertSidToStringSidW.argtypes = (
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_wchar_p))
        kernel32.LocalFree.argtypes = (ctypes.c_void_p,)
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        TOKEN_QUERY = 0x0008
        TokenUser = 1
        token = ctypes.c_void_p()
        proc = kernel32.GetCurrentProcess()
        if not advapi32.OpenProcessToken(proc, TOKEN_QUERY, ctypes.byref(token)):
            return None
        try:
            length = ctypes.c_uint32(0)
            advapi32.GetTokenInformation(token, TokenUser, None, 0, ctypes.byref(length))
            buf = ctypes.create_string_buffer(length.value)
            if not advapi32.GetTokenInformation(token, TokenUser, buf, length.value,
                                                ctypes.byref(length)):
                return None
            # TOKEN_USER beginnt mit SID_AND_ATTRIBUTES: der erste Pointer ist die SID.
            sid_ptr = ctypes.cast(buf, ctypes.POINTER(ctypes.c_void_p))[0]
            str_ptr = ctypes.c_wchar_p()
            if not advapi32.ConvertSidToStringSidW(sid_ptr, ctypes.byref(str_ptr)):
                return None
            try:
                return str_ptr.value
            finally:
                kernel32.LocalFree(str_ptr)
        finally:
            kernel32.CloseHandle(token)
    except Exception:
        return None


def _acquire_single_instance() -> bool:
    """Belegt einen benannten Windows-Mutex (Gate G19).

    Verhindert eine zweite Instanz: zwei Prozesse wuerden sich denselben festen
    WebView2-Profilordner und ``tasks.db.enc`` (bzw. dessen Arbeitskopie)
    gegenseitig sperren oder ueberschreiben (weisses Fenster, "reagiert nicht",
    Datenkorruption). Gibt True zurueck, wenn diese Instanz die erste ist.

    Namensraum ``Global\\NoaToDo-<User-SID>`` (V3, Rest-Pflicht aus Phase 8):
    ein ``Local\\``-Mutex ist nur pro Logon-Session eindeutig, sodass derselbe
    Benutzer per RDP oder Benutzerumschaltung eine zweite Instanz auf demselben
    Tresor starten koennte (genau die Korruption, gegen die G19 existiert).
    ``Global\\`` ist maschinenweit, das SID-Suffix macht ihn pro Benutzer
    eindeutig (verschiedene Benutzer haben eigene Tresore und duerfen je eine
    Instanz laufen lassen). Ohne ermittelbare SID Fallback auf den alten Namen.
    """
    global _single_instance_handle
    kernel32 = ctypes.windll.kernel32
    sid = _current_user_sid()
    name = f"Global\\NoaToDo-{sid}" if sid else "Local\\NoaToDoSingleton"
    _single_instance_handle = kernel32.CreateMutexW(None, False, name)
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


def _is_allowed_navigation(uri: str) -> bool:
    """Gate G12: nur die eigene lokale Frontend-Seite ist erlaubtes Ziel.

    Erlaubt sind ``about:`` (interne Leerseiten) und ``file:``-URIs, die in den
    eigenen ``frontend``-Ordner zeigen. ALLES andere (http/https, fremde
    file-Pfade, sonstige Schemata) wird verweigert: die App ist rein lokal und
    navigiert nie woandershin; ein per XSS eingeschleustes
    ``window.location='https://...'`` liefe sonst als Exfiltrationskanal an
    der CSP vorbei (die CSP deckt Subressourcen, nicht die Top-Navigation).

    Loopback-Ausnahme (korrigiert 2026-07-17): PyWebView 5.x liefert das
    Frontend NICHT per ``file://`` aus, sondern grundsaetzlich ueber einen
    eigenen lokalen HTTP-Server (``http://127.0.0.1:<port>/``), und zwar in
    JEDEM Modus, nicht nur mit NOATODO_DEBUG. Die Ausnahme darf daher nicht an
    den Debug-Modus gekoppelt sein: der Release-Build ignoriert NOATODO_DEBUG
    hart (G34), eine Debug-Kopplung wuerde also gerade dort (und in jedem
    normalen Start) den eigenen Startaufruf blockieren und das Fenster schwarz
    lassen. Erlaubt wird ausschliesslich Loopback (127.0.0.1/localhost/::1);
    jede entfernte http/https-Adresse (der eigentliche Exfiltrations-Vektor,
    gegen den G12 schuetzt) bleibt weiter verweigert.
    """
    from urllib.parse import unquote, urlparse

    u = (uri or "").strip().lower()
    if u.startswith("about:"):
        return True
    if u.startswith("http://"):
        host = (urlparse(u).hostname or "")
        return host in ("127.0.0.1", "localhost", "::1")
    if not u.startswith("file:"):
        return False
    frontend_root = buildinfo.frontend_dir().replace("\\", "/").lower()
    path = unquote(urlparse(u).path or "").replace("\\", "/").lstrip("/")
    return path.startswith(frontend_root.lstrip("/"))


def _wire_navigation_guard(window) -> None:
    """Haengt den G12-Navigations-Waechter an das WebView2-Control.

    ``NavigationStarting`` feuert fuer jede Top-Level-Navigation
    (``window.location``, Redirects, ``load_url``); nicht erlaubte Ziele werden
    mit ``args.Cancel`` verworfen, die App bleibt auf der lokalen
    ``index.html``. ``window.open`` landet dank
    ``webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False`` (in main)
    nicht im System-Browser, sondern als ``load_url`` im selben Fenster und
    damit ebenfalls in diesem Waechter. Laeuft ueber den UI-Thread
    (Projektregel: keine WinForms-Zugriffe aus Worker-Threads).
    """

    def _attach():
        try:
            browser = getattr(window.native, "browser", None)
            control = getattr(browser, "webview", None)  # WinForms WebView2
            if control is None:
                return

            def on_nav(_sender, args):
                try:
                    uri = str(args.Uri)
                except Exception:
                    uri = ""
                if not _is_allowed_navigation(uri):
                    args.Cancel = True
                    # Kein URI im Normal-Log (koennte eingeschleuste Daten
                    # tragen); Details nur im Debug-Modus (N11.12.2).
                    if _debug_enabled():
                        print(f"[NoaToDo] G12: Navigation verweigert: {uri}", flush=True)
                    else:
                        print("[NoaToDo] G12: externe Navigation verweigert.", flush=True)

            control.NavigationStarting += on_nav
        except Exception:
            pass

    _run_on_ui_thread(window, _attach)


def _frontend_stamp() -> str:
    """Aenderungszeit der wichtigsten Frontend-Dateien als kurzer Stempel.

    Reine Diagnose: macht im Terminal sichtbar, welcher Frontend-Stand geladen
    wird, damit "es hat sich nichts geaendert" sofort auf alt-laufendes Fenster
    vs. echter Neustart zurueckgefuehrt werden kann. Im gefrorenen Build sagen
    diese Zeiten nichts (das Bundle wird pro Start frisch entpackt), dort steht
    stattdessen Version und Build-Datum (V10).
    """
    if buildinfo.is_frozen():
        return f"Version {buildinfo.version_line()}"
    parts = []
    for name in ("index.html", "app.js", "style.css"):
        path = os.path.join(buildinfo.frontend_dir(), name)
        try:
            ts = time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(path)))
        except OSError:
            ts = "??"
        parts.append(f"{name} {ts}")
    return "Frontend: " + ", ".join(parts)


def _current_dark(api: Api) -> bool:
    """Das EFFEKTIV angezeigte Theme fuer die Titelleiste (N11.6).

    Seit N11.6 entscheidet nicht mehr ein Bool-Setting, sondern
    ``theme = auto|light|dark``; bei ``auto`` zaehlt der Windows-Zustand. Die
    Aufloesung liegt in ``Api._effective_dark()`` (eine Quelle fuer Frontend
    und Titelleiste). Ohne entsperrten Tresor bleibt es bei Dunkel.
    """
    try:
        return api._effective_dark()
    except Exception:
        return True


def _kill_orphaned_webview2(profile_dir: str) -> None:
    """Verwaiste ``msedgewebview2.exe`` beenden, die ``profile_dir`` sperren (G14 c).

    Nur Prozesse, deren Kommandozeile auf genau diesen Profilordner zeigt
    (nicht pauschal alle: andere Apps nutzen WebView2). Ueberleben sie einen
    harten Kill, sperren sie den Ordner und der Wisch (bzw. der naechste Start)
    scheitert an ``0x800700AA`` (ERROR_BUSY). Best effort.
    """
    if not profile_dir:
        return
    esc = profile_dir.replace("\\", "\\\\")
    ps = (
        "Get-CimInstance Win32_Process -Filter \"name='msedgewebview2.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{esc}*' }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        pass


def _wipe_profile_dir() -> None:
    """``PROFILE_DIR`` sicher freigeben und wischen (Gate G14, teardown Schritt 9).

    Wartet kurz, bis die WebView2-Kindprozesse selbst enden (Normalfall nach
    ``window.destroy()``); beendet sonst gezielt die verwaisten
    ``msedgewebview2.exe`` (Crash-/Kill-Fall) und loescht den Ordner. Operiert
    auf dem effektiven (Store-Python-umgeleiteten) Pfad, weil ``os``-Zugriffe
    die Umleitung automatisch sehen (V8). ``LOCK_PROFILE_DIR`` existiert im
    nativen Fallback nicht (N11.8.3), es gibt also nichts weiteres zu wischen.
    """
    if not os.path.isdir(PROFILE_DIR):
        return
    # Kurzes Fenster, damit die Kinder nach dem Fenster-Abbau selbst schliessen.
    for _ in range(20):
        try:
            shutil.rmtree(PROFILE_DIR)
            return
        except OSError:
            time.sleep(0.1)
    # Immer noch gesperrt: verwaiste Prozesse gezielt beenden, dann erneut.
    _kill_orphaned_webview2(PROFILE_DIR)
    try:
        shutil.rmtree(PROFILE_DIR)
    except OSError:
        # Best effort (N11.11.2 Fehlerregel): der naechste Start purged ohnehin.
        pass


# ---------------------------------------------------------------------------
# Nahtloser Fensterwechsel (N11.25)
# ---------------------------------------------------------------------------
# Zwischen zwei Fenstern (WebView <-> natives Sperrfenster) lag bisher eine
# Luecke ohne jedes Fenster: das alte war zu, das neue noch nicht da, dazwischen
# lief der PROFILE_DIR-Wisch (G14) bzw. der WebView2-Anlauf. Auf dem Schirm sah
# das aus, als minimiere sich die App. Die Blende (lockwindow.Curtain) haelt in
# dieser Zeit das App-Bild stehen. Sie ist reine Kosmetik: sie zeigt keinen
# Nutzerinhalt, haelt die teardown-Sequenz nicht auf und schliesst sich zur Not
# selbst (Notbremse im Curtain).
_curtain = None


def _show_curtain(mode: str, icon: str) -> None:
    """Blende auflegen, BEVOR das aktuelle Fenster verschwindet."""
    global _curtain
    _close_curtain()
    try:
        import lockwindow
        curtain = lockwindow.Curtain(
            mode, icon,
            # Taskleisten-Identitaet wie bei den echten Fenstern: sonst
            # erscheint bei jedem Wechsel kurz ein zweiter Eintrag mit dem
            # generischen Python-Symbol statt des NoaToDo-Logos.
            on_ready=lambda hwnd: _apply_taskbar_identity(
                hwnd, _APP_USER_MODEL_ID, icon),
        )
        curtain.show()
        _curtain = curtain
    except Exception:
        _curtain = None


def _close_curtain(next_hwnd: int = 0) -> None:
    """Blende wegnehmen (idempotent, aus jedem Thread).

    ``next_hwnd`` ist das Fenster, das danach bedient wird; die Blende gibt ihm
    den Vordergrund, bevor sie sich schliesst (sonst liegt die Tastatur nach
    dem Wechsel womoeglich in einer fremden App, und die Passphrase laesst sich
    nicht eintippen).
    """
    global _curtain
    curtain, _curtain = _curtain, None
    if curtain is not None:
        try:
            curtain.close(next_hwnd)
        except Exception:
            pass


def _finish_native_teardown() -> None:
    """teardown-Schritt 9 nach dem Fenster-Abbau: PROFILE_DIR wischen (G14),
    danach Schritt 10 (Funk-Ausgangszustand wiederherstellen, N11.5/N11.10)."""
    _wipe_profile_dir()
    _restore_radio_if_needed()


def _restore_radio_if_needed() -> None:
    """teardown Schritt 10 (N11.5/N11.10): Funk-Ausgangszustand wiederherstellen.

    Nur wenn die App den Flugmodus selbst eingeschaltet hatte
    (``config.json.radio_baseline`` gesetzt): den beim ersten App-Offline
    gemerkten Zustand real wieder herstellen (WLAN/Bluetooth/Mobilfunk) und den
    Merker loeschen. Bei Sperre/Auto-Lock ist die Sequenz hier schon beendet, es
    passiert also nie beim Sperren (N11.10). Best effort. Derselbe Aufruf raeumt
    beim naechsten Start einen durch einen Absturz liegengebliebenen Merker auf
    (Crash-Recovery, N11.10).
    """
    try:
        cfg = config_module.load_config()
    except config_module.ConfigDamaged:
        return
    if not cfg or not cfg.get("radio_baseline"):
        return
    baseline = cfg.get("radio_baseline")
    try:
        radio_module.get_controller().restore(baseline)
    except Exception:
        pass
    cfg["radio_baseline"] = None
    try:
        config_module.save_config(cfg)
    except Exception:
        pass


def _determine_boot_state(api: Api) -> None:
    """Boot-Weiche nach N11.8.2/N11.13/N11.15: setzt api._boot_state u.a.

    - config.json fehlt komplett -> Onboarding (Normalfall Erststart).
    - config.json unbrauchbar -> vault_error/config_damaged (N6, Datei nach
      .bad gedreht in load_config).
    - config.json ok, aber tasks.db.enc am Pfad fehlt -> vault_error/
      vault_unreachable (N11.15.3, kein stiller Erststart).
    - config.json ok und Datei da -> locked (Lock-Screen, nur Passphrase).
    """
    try:
        cfg = config_module.load_config()
    except config_module.ConfigDamaged:
        api._boot_state = "vault_error"
        api._boot_reason = "config_damaged"
        api._vault_path = None
        api.locked = True
        return
    if cfg is None:
        api._boot_state = "onboarding"
        api._vault_path = None
        api.locked = False
        return
    api._config_cache = cfg
    vault_path = cfg.get("vault_path")
    api._vault_path = vault_path
    if not vault_path or not os.path.exists(vault_path):
        api._boot_state = "vault_error"
        api._boot_reason = "vault_unreachable"
        api.locked = True
        return
    api._boot_state = "locked"
    api.locked = True


def run_webview(api: Api, icon: str) -> None:
    """Das WebView-Hauptfenster (entsperrt oder im Onboarding) bauen und laufen.

    Blockiert, bis das Fenster abgebaut ist (Lock, Quit, Killswitch, Reset,
    Fenster-X). Danach kehrt ``webview.start`` zurueck und die Boot-Schleife
    fuehrt die nativen teardown-Schritte 9 bis 11 aus (G35).
    """
    # Beim (Neu-)Aufbau der Ansicht ist keine Sperre im Gang (N11.8.3 Frage 4:
    # das Fenster kommt immer maximiert zurueck, nie mini).
    api._teardown_in_progress = False
    api._mini = False
    _purge_webview_cache()

    # Lokaler Import wie ueberall in dieser Datei: wintheme laedt WinForms nach,
    # das erst nach der DPI-/setup_app-Vorbereitung in main() geladen werden soll.
    import wintheme

    window = webview.create_window(
        "NoaToDo",
        INDEX,
        js_api=api,
        width=1200,
        height=800,
        # Immer maximiert (N11.6/N11.8.3 Frage 4), nie Mini ueber die Sperrgrenze.
        maximized=True,
        min_size=(340, 480),
        # Gate G34 (b): Task-/Listentext ist NICHT selektierbar (bewusst gesetzt).
        text_select=False,
        # N11.25: PyWebView reicht das an WebView2 als DefaultBackgroundColor
        # durch. Ohne das steht das Fenster bis zum ersten Bild auf Weiss und
        # blitzt beim Aufbau hell auf; mit dem App-Grundton geht es nahtlos aus
        # der Blende in die App ueber.
        background_color=wintheme.BG,
    )
    api._window = window

    # teardown-Request fuer die WebView-Phase (G35 Schritte 9-11 folgen nach dem
    # Fenster-Abbau in der Boot-Schleife): das Fenster ueber den UI-Thread
    # schliessen, damit webview.start() zurueckkehrt.
    def request_teardown():
        # Nahtloser Wechsel (N11.25): geht es nach dem Abbau weiter (Sperre
        # oder Onboarding), legt sich die Blende ZUERST ueber das Fenster, so
        # dass der Bildschirm zwischen den Fenstern nie leer wird. Beim
        # Beenden (quit/killswitch/panic-finish) gibt es bewusst keine Blende:
        # dort soll nichts stehenbleiben.
        try:
            nxt = api._session.next_state
        except Exception:
            nxt = "exit"
        if nxt == "locked":
            _show_curtain("lock", icon)
        elif nxt == "onboarding":
            _show_curtain("plain", icon)

        form = getattr(window, "native", None)
        if form is not None:
            try:
                from System import Action
                form.BeginInvoke(Action(form.Close))
                return
            except Exception:
                pass
        try:
            window.destroy()
        except Exception:
            pass

    api._request_teardown = request_teardown

    # Kam die App aus einer Blende (Entsperren, Onboarding nach Reset), wird sie
    # erst weggenommen, wenn im Fenster wirklich etwas steht: `loaded` feuert bei
    # geladenem Dokument, die kurze Nachlaufzeit deckt den ersten render()-Lauf
    # des Frontends ab. Der Hintergrund des Fensters ist ohnehin der App-Grundton
    # (background_color), es kann also nichts hell aufblitzen.
    def _on_loaded():
        # Mit dem Fensterhandle: die Blende uebergibt dem Hauptfenster den
        # Vordergrund, bevor sie geht (sonst kann man nach dem Entsperren
        # nicht sofort tippen).
        threading.Timer(0.25, lambda: _close_curtain(_get_hwnd(window))).start()

    window.events.loaded += _on_loaded

    def on_start():
        # Gate G12: externe Navigation abriegeln.
        _wire_navigation_guard(window)

        def _startup_window_setup():
            hwnd = _get_hwnd(window)
            icon_path = ICON
            _apply_window_icon(window, icon_path)
            _apply_taskbar_identity(hwnd, _APP_USER_MODEL_ID, icon_path)
            _apply_titlebar_theme(hwnd, _current_dark(api))
            if hwnd:
                # N11.25: Windows' Oeffnen-/Schliessen-Animation fuer dieses
                # Fenster abschalten. Sonst zieht sich das Hauptfenster beim
                # Sperren sichtbar unter der Blende zusammen und schiebt sich
                # beim Entsperren darunter wieder auf.
                try:
                    import wintheme
                    wintheme.disable_window_transitions(hwnd)
                except Exception:
                    pass
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, 0, 0, 0, 0,
                    _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOOWNERZORDER | _SWP_FRAMECHANGED,
                )
            # Fenster-X (FormClosing) nimmt denselben sicheren Beenden-Pfad wie
            # der Off-Knopf (B.8 Punkt 2 / G14 / G35): teardown('quit'). Nur,
            # wenn nicht ohnehin schon eine teardown-Sequenz laeuft (Lock/Quit/
            # Killswitch/Reset schliessen das Fenster selbst, dann wuerde ein
            # zweiter quit_app next_state verfaelschen).
            try:
                native = getattr(window, "native", None)
                if native is not None:
                    from System.Windows.Forms import FormClosingEventHandler

                    def on_form_closing(_sender, _args):
                        if not api._teardown_in_progress:
                            api._teardown_in_progress = True
                            try:
                                security_module.run_teardown("quit", api._session)
                            except Exception:
                                pass
                    native.FormClosing += FormClosingEventHandler(on_form_closing)
            except Exception:
                pass

        _run_on_ui_thread(window, _startup_window_setup)

        def _on_setting_change(key: str, value) -> None:
            # N11.6: der gespeicherte Wert ist `auto|light|dark`; die Titelleiste
            # braucht das daraus aufgeloeste EFFEKTIVE Theme.
            if key == "theme":
                _run_on_ui_thread(
                    window, lambda: _apply_titlebar_theme(_get_hwnd(window), _current_dark(api)))

        api._on_setting_change = _on_setting_change

        # N11.6: Windows hat hell/dunkel gewechselt und `theme=auto` steht.
        # Der Callback kommt aus dem Beobachter-Thread, also ueber den
        # UI-Thread marshallen (WinForms-Regel, CLAUDE.md).
        def _on_theme_change(dark: bool) -> None:
            _run_on_ui_thread(window, lambda: _apply_titlebar_theme(_get_hwnd(window), dark))

        api._on_theme_change = _on_theme_change

        def _on_frame_changed(mini: bool) -> None:
            def _frame_setup():
                h = _get_hwnd(window)
                if not mini:
                    _apply_titlebar_theme(h, _current_dark(api))
                    if h:
                        ctypes.windll.user32.SetWindowPos(
                            h, 0, 0, 0, 0, 0,
                            _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_NOOWNERZORDER | _SWP_FRAMECHANGED,
                        )

            _run_on_ui_thread(window, _frame_setup)

        api._on_frame_changed = _on_frame_changed

    os.makedirs(PROFILE_DIR, exist_ok=True)
    # N11.25: WebView2 (Chromium) haelt ein Fenster, das vollstaendig von einem
    # anderen verdeckt ist, fuer unsichtbar und hoert auf, Bilder zu liefern.
    # Genau das ist beim Entsperren der Fall: die Uebergabe-Blende liegt
    # darueber, waehrend die App laedt. Ohne diesen Schalter stand nach dem
    # Wegnehmen der Blende fuer einen Moment eine leere Flaeche da, statt der
    # fertigen App. Reiner Darstellungsschalter, keine Sicherheitswirkung.
    _extra_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
    if "CalculateNativeWindowOcclusion" not in _extra_args:
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
            _extra_args + " --disable-features=CalculateNativeWindowOcclusion").strip()
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
    webview.start(
        on_start,
        debug=_debug_enabled(),
        icon=icon,
        private_mode=False,
        storage_path=PROFILE_DIR,
    )
    api._window = None
    # Das Fenster ist weg: den Titelleisten-Callback loesen, damit ein spaeteres
    # Windows-Theme-Ereignis nicht auf ein totes Fenster zeigt (N11.6).
    api._on_theme_change = None


def main() -> None:
    print("[NoaToDo] Start. " + _frontend_stamp(), flush=True)

    # Single-Instance-Schutz (Gate G19): zweite Instanz sofort beenden.
    if not _acquire_single_instance():
        # Hinweis im App-Design statt der weissen Windows-MessageBox: auch
        # Nebenfenster sollen nie nach Windows aussehen (wintheme).
        try:
            import wintheme
            wintheme.show_message(
                "NoaToDo is already running.\nOnly one instance can be open.",
                "NoaToDo",
                ICON,
            )
        except Exception:
            ctypes.windll.user32.MessageBoxW(
                0,
                "NoaToDo läuft bereits. Es kann nur eine Instanz geöffnet sein.",
                "NoaToDo",
                0x40,  # MB_ICONINFORMATION
            )
        print("[NoaToDo] Bereits aktiv, zweite Instanz beendet sich.", flush=True)
        return

    _cleanup_stale_webview_profiles()
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    _set_app_user_model_id()
    # Verwaiste (verschluesselte) Arbeitsdateien eines Absturzes verwerfen
    # (N11.9: keine Crash-Recovery aus der Arbeitsdatei).
    security_module.cleanup_work_dir()
    # N11.10 Crash-Recovery: hat ein frueherer Lauf den Flugmodus eingeschaltet
    # und ist abgestuerzt, ohne Schritt 10 zu erreichen, liegt der Ausgangs-Merker
    # noch in config.json. Ihn hier einmalig wiederherstellen und wegraeumen, damit
    # der Funk nicht dauerhaft aus bleibt.
    _restore_radio_if_needed()
    # Spike-Betriebsbedingung (N11.18): setup_app() (SetCompatibleTextRendering-
    # Default) MUSS vor dem ersten nativen Fenster laufen; es ist idempotent, der
    # spaetere webview.start() ueberspringt es dann. Ohne diesen Aufruf wirft der
    # erste WebView-Start nach dem nativen Lock-Fenster InvalidOperationException.
    try:
        from webview.platforms.winforms import setup_app
        setup_app()
    except Exception:
        pass

    session = security_module.Session()
    api = Api(session)
    icon = ICON

    _determine_boot_state(api)

    # Boot-Schleife: natives Lock-Fenster (gesperrt/Fehler) <-> WebView-Fenster
    # (Onboarding/entsperrt). Genau EIN Fenster zur Zeit (Spike-Frage 3), die
    # nativen teardown-Schritte 9-11 laufen nach jedem Fenster-Abbau (G35).
    try:
        while True:
            state = api._boot_state
            if state in ("locked", "vault_error"):
                import lockwindow
                res = lockwindow.run_lock_window(
                    api, state, api._boot_reason, icon,
                    # Taskleisten-Eintrag des Sperrfensters mit AppID + Logo
                    # verknuepfen (sonst zeigt die Leiste das Python-Symbol).
                    on_ready=lambda hwnd: _apply_taskbar_identity(
                        hwnd, _APP_USER_MODEL_ID, icon),
                    # Nahtloser Wechsel (N11.25): Blende weg, sobald das
                    # Sperrfenster gemalt ist; und wieder auf, bevor es fuer
                    # den Weiterweg (Entsperren/Reset) schliesst.
                    on_painted=_close_curtain,
                    on_leaving=lambda mode: _show_curtain(mode, icon),
                    # Nur die Rueckkehr in eine laufende Sitzung laesst das
                    # Schloss aufgehen (N11.22); beim normalen Start uebernimmt
                    # die Willkommens-Blende mit dem Logo (N11.20).
                    resumed=bool(api._resumed),
                )
                if res == "quit":
                    _close_curtain()
                    _finish_native_teardown()
                    break
                if res == "onboarding":
                    # Reset gelaufen (teardown('reset') hat Schritt 9 noch nicht
                    # gemacht, es gab kein WebView): defensiv wischen, dann ins
                    # Onboarding-WebView.
                    _finish_native_teardown()
                    api._boot_state = "onboarding"
                    api.locked = False
                    api._resumed = False   # Reset: es beginnt wieder von vorn
                    continue
                # res == "unlocked": Tresor offen, weiter zum WebView-Fenster.
                api.locked = False

            # Onboarding oder entsperrt -> WebView-Hauptfenster.
            run_webview(api, icon)

            # Fenster ist abgebaut: die nativen teardown-Schritte 9-11.
            _finish_native_teardown()
            ns = session.next_state
            if ns == "exit":
                _close_curtain()   # beim Beenden bleibt nichts stehen (N11.25)
                break
            if ns == "locked":
                api.locked = True
                api._boot_state = "locked"
                api._boot_reason = None
                # Ab jetzt ist jedes Entsperren eine Rueckkehr in eine laufende
                # Sitzung, kein Programmstart: das Frontend laesst dann die
                # Willkommens-Blende weg (N11.22), die Rueckmeldung gibt das
                # aufgehende Schloss im nativen Sperrfenster.
                api._resumed = True
                session.next_state = "exit"   # bis zum naechsten teardown
                continue
            if ns == "onboarding":
                api.locked = False
                api._boot_state = "onboarding"
                api._resumed = False
                session.next_state = "exit"
                continue
            # Kein teardown gelaufen (unerwartet): sicherheitshalber beenden.
            break
    finally:
        _close_curtain()
        _release_single_instance()
    print("[NoaToDo] Beendet.", flush=True)


def _release_single_instance() -> None:
    """Single-Instance-Mutex freigeben (teardown Schritt 11)."""
    global _single_instance_handle
    if _single_instance_handle:
        try:
            ctypes.windll.kernel32.CloseHandle(_single_instance_handle)
        except Exception:
            pass
        _single_instance_handle = None


def _debug_enabled() -> bool:
    """DevTools aktivieren, wenn NOATODO_DEBUG gesetzt ist.

    Nur im Quellbaum. Der gefrorene Release-Build ignoriert die Variable hart
    (Gate G34 a); die eine Entscheidung dazu liegt in ``buildinfo``.
    """
    return buildinfo.debug_enabled()


if __name__ == "__main__":
    main()
