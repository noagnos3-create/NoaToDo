"""Die ``js_api``-Bridge zwischen Frontend und Backend (Bauplan Phase 2 / B.2).

Jede öffentliche Methode wird vom Frontend als ``pywebview.api.<name>(...)``
aufgerufen und gibt ein JSON-serialisierbares Dict/Listen-Objekt zurück. Tritt ein
Fehler auf, kommt ``{"error": code, "message": ...}`` zurück (Fehlerkonvention B.2).

In Phase 2 sind alle lokalen Methoden echt (lesen/schreiben die DB). Die
Sicherheits-Methoden (Lock/Unlock/Panic) sind sinnvolle Platzhalter und werden
in Phase 8 ausgefüllt.
"""
from __future__ import annotations

import ctypes
import functools
import os
import threading
from typing import Any, Callable

from . import db as db_module


def bridge(fn: Callable) -> Callable:
    """Fängt Ausnahmen ab und liefert die Fehlerkonvention aus B.2."""

    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except KeyError as exc:
            return {"error": "not_found", "message": f"Unbekannte ID: {exc}"}
        except Exception as exc:  # pragma: no cover - defensiv
            return {"error": "internal", "message": str(exc)}

    return wrapper


# Typumwandlung beim Lesen der settings-Tabelle (dort liegt alles als String).
_BOOL_SETTINGS = {"dark"}


def _typed_settings(raw: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _BOOL_SETTINGS:
            out[k] = str(v).lower() == "true"
        else:
            out[k] = v
    return out


class Api:
    """Wird in ``main.py`` als ``js_api`` an das PyWebView-Fenster gehängt."""

    def __init__(self, database: db_module.Database):
        self.db = database
        self.online = True
        self.locked = False
        # Unterstrich-Präfix ist Pflicht: PyWebView durchsucht das Api-Objekt
        # rekursiv nach exponierbaren Methoden (util.get_functions) und steigt
        # dabei in jedes öffentliche Attribut ab. Ein dort liegendes Window-
        # Objekt würde über window.dom.body ein evaluate_js() auslösen, bevor das
        # Fenster bereit ist -> "Main window failed to start". Namen mit "_"
        # werden von der Introspektion übersprungen.
        self._window = None  # von main.py gesetzt, für Backend->Frontend-Events
        self._mini = False        # kompakter Mini-Fenster-Modus aktiv?
        self._on_setting_change = None  # optionaler Callback(key, value) für main.py
        self._on_frame_changed = None  # Callback(mini) nach jedem Mini-Modus-Wechsel
                                       # (Handle wird neu erzeugt: Titelleisten-Theme
                                       # muss neu gesetzt werden)
        self._clip_timer = None   # Timer für das Auto-Leeren der Zwischenablage

    # =====================================================================
    # Gesamtzustand
    # =====================================================================
    @bridge
    def get_state(self) -> dict[str, Any]:
        return {
            "lists": self.db.get_lists_with_tasks(),
            "settings": _typed_settings(self.db.get_all_settings()),
            "online": self.online,
            "locked": self.locked,
        }

    @bridge
    def get_lists(self) -> list[dict[str, Any]]:
        return self.db.get_lists_with_tasks()

    # =====================================================================
    # Listen
    # =====================================================================
    @bridge
    def add_list(self, name: str) -> dict[str, Any]:
        name = (name or "").strip()
        if not name:
            return {"error": "invalid", "message": "Listenname darf nicht leer sein."}
        return self.db.add_list(name)

    @bridge
    def rename_list(self, list_id: str, name: str) -> dict[str, Any]:
        name = (name or "").strip()
        if not name:
            return {"error": "invalid", "message": "Listenname darf nicht leer sein."}
        return self.db.rename_list(list_id, name)

    @bridge
    def delete_list(self, list_id: str) -> dict[str, Any]:
        return self.db.delete_list(list_id)

    # =====================================================================
    # Aufgaben
    # =====================================================================
    @bridge
    def add_task(self, list_id: str, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"error": "invalid", "message": "Aufgabentext darf nicht leer sein."}
        return self.db.add_task(list_id, text)

    @bridge
    def toggle_task(self, task_id: str) -> dict[str, Any]:
        return self.db.toggle_task(task_id)

    @bridge
    def edit_task(self, task_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self.db.edit_task(task_id, fields or {})

    @bridge
    def delete_task(self, task_id: str) -> dict[str, Any]:
        return self.db.delete_task(task_id)

    @bridge
    def reorder(self, list_id: str, ordered_ids: list[str]) -> dict[str, Any]:
        return self.db.reorder(list_id, ordered_ids or [])

    # =====================================================================
    # Export / Kopieren (Grundgerüst; Save-Dialog folgt in Phase 7)
    # =====================================================================
    def _list_or_none(self, list_id: str) -> dict[str, Any] | None:
        for lst in self.db.get_lists_with_tasks():
            if lst["id"] == list_id:
                return lst
        return None

    @bridge
    def export_list(self, list_id: str, fmt: str = "md") -> dict[str, Any]:
        lst = self._list_or_none(list_id)
        if lst is None:
            return {"error": "not_found", "message": "Liste nicht gefunden."}
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in lst["name"]).strip()
        if fmt == "json":
            import json

            content = json.dumps(lst, ensure_ascii=False, indent=2)
            return {"filename": f"{safe}.json", "content": content}
        # md / txt (kein Meta mehr, N11.1.3)
        lines: list[str] = []
        if fmt == "md":
            lines.append(f"# {lst['name']}")
            lines.append("")
            for t in lst["open"]:
                lines.append(f"- [ ] {t['text']}")
            for t in lst["done"]:
                lines.append(f"- [x] {t['text']}")
            ext = "md"
        else:  # txt
            lines.append(lst["name"])
            lines.append("=" * len(lst["name"]))
            for t in lst["open"]:
                lines.append(f"[ ] {t['text']}")
            for t in lst["done"]:
                lines.append(f"[x] {t['text']}")
            ext = "txt"
        return {"filename": f"{safe}.{ext}", "content": "\n".join(lines)}

    @bridge
    def copy_task(self, task_id: str) -> dict[str, Any]:
        """Kopiert genau EINE Aufgabe gehärtet in die Zwischenablage (Gate G23).

        Das Kopieren passiert komplett im Backend: der Text wird mit Formaten
        abgelegt, die ihn von der Win+V-History und dem Cloud-Clipboard
        ausschliessen, und nach ``CLIPBOARD_CLEAR_SECONDS`` automatisch wieder
        gelöscht, sofern die Zwischenablage noch unseren Inhalt trägt. Eine
        ganze Liste kopiert man bewusst nicht mehr, dafür gibt es den Export.
        """
        task = self.db.get_task(task_id)
        if task is None:
            return {"error": "not_found", "message": "Aufgabe nicht gefunden."}
        text = task["text"]
        if not _set_clipboard_secure(text):
            return {"error": "clipboard", "message": "Zwischenablage nicht verfügbar."}
        if self._clip_timer is not None:
            self._clip_timer.cancel()
        self._clip_timer = threading.Timer(
            CLIPBOARD_CLEAR_SECONDS, _clear_clipboard_if_matches, args=(text,)
        )
        self._clip_timer.daemon = True
        self._clip_timer.start()
        return {"ok": True, "clears_in": CLIPBOARD_CLEAR_SECONDS}

    # =====================================================================
    # Einstellungen
    # =====================================================================
    @bridge
    def set_setting(self, key: str, value: Any) -> dict[str, Any]:
        result = self.db.set_setting(key, value)
        if self._on_setting_change:
            self._on_setting_change(key, value)
        return result

    # =====================================================================
    # Fenster (Mini-/Kompaktmodus)
    # =====================================================================
    @bridge
    def set_mini(self, flag: bool) -> dict[str, Any]:
        """Schaltet den kompakten Mini-Fenster-Modus um.

        Im Mini-Modus wird das Fenster auf ein schmales Lesefenster verkleinert
        und oben rechts am Bildschirm angeheftet, sodass nur die gerade offene
        Liste sichtbar bleibt. Beim Verlassen wird die vorherige Größe/Position
        wiederhergestellt.

        WICHTIG (Bugfix): Diese Methode läuft im PyWebView-API-Worker-Thread, NICHT
        im WinForms-UI-Thread. Frühere Versionen riefen win.resize/win.move/
        win.on_top und manuelle SetWindowLong/SetWindowPos-Aufrufe direkt aus
        diesem Worker-Thread auf. Das sind threadübergreifende Zugriffe auf das
        Fenster (TopMost und Rahmen-Stilbits sind handle-relevant); sie konnten die
        Windows-Nachrichtenschleife verklemmen und das rahmenlose, immer im
        Vordergrund liegende Mini-Fenster komplett einfrieren (Bildschirm hängt).
        Deshalb marshallen wir die gesamte Fenster-Mutation über form.Invoke auf
        den UI-Thread (siehe _apply_mini_window).
        """
        win = self._window
        if win is None:
            return {"error": "no_window", "message": "Kein Fenster verfügbar."}
        flag = bool(flag)
        if flag == self._mini:
            return {"mini": self._mini}
        if not self._apply_mini_window(win, flag):
            return {"error": "window", "message": "Fensterumschaltung fehlgeschlagen."}
        self._mini = flag
        # Der FormBorderStyle-Wechsel hat das Fensterhandle neu erzeugt. main.py
        # passt ueber diesen Callback beim Verlassen des Mini-Modus die
        # Titelleisten-Farbe wieder ans Theme an.
        if self._on_frame_changed:
            try:
                self._on_frame_changed(flag)
            except Exception:
                pass
        return {"mini": self._mini}

    def _apply_mini_window(self, win, flag: bool) -> bool:
        """Führt die Fenster-Mutation für den Mini-Modus auf dem UI-Thread aus.

        Nutzt die native WinForms-Form (``win.native``) und schaltet Rahmen,
        Größe, Position und Vordergrund-Eigenschaft ausschließlich über
        ``form.Invoke`` um. So gibt es keine threadübergreifenden Fensterzugriffe
        mehr. Liefert True bei Erfolg, False wenn keine native Form verfügbar ist.
        """
        form = getattr(win, "native", None)
        if form is None:
            return False
        try:
            FormBorderStyle, FormWindowState, Size, Point, Screen, Action = _winforms_types()
        except Exception:
            return False

        def work():
            if flag:
                # Aus dem Maximiert-Zustand zuerst auf Normal, sonst greift die
                # neue Größe nicht.
                if form.WindowState != FormWindowState.Normal:
                    form.WindowState = FormWindowState.Normal
                # Rahmenlos über die verwaltete Eigenschaft (kein manuelles
                # SetWindowLong nötig): das Mini-Panel bringt eine eigene
                # Kopfzeile mit.
                form.FormBorderStyle = getattr(FormBorderStyle, "None")
                mini_w, mini_h, margin = 360, 600, 16
                wa = Screen.PrimaryScreen.WorkingArea
                form.Size = Size(mini_w, mini_h)
                form.Location = Point(
                    max(wa.X, wa.X + wa.Width - mini_w - margin), wa.Y + margin
                )
                # Bleibt im Vordergrund, sonst verschwindet das kleine
                # Lesefenster hinter der nächsten App (UX-Nacharbeit 6.5).
                form.TopMost = True
            else:
                # Beim Verlassen immer wieder maximiert öffnen (Nutzerwunsch).
                form.TopMost = False
                # Rahmen (Titelleiste + Resize-Rahmen) wiederherstellen.
                form.FormBorderStyle = FormBorderStyle.Sizable
                form.WindowState = FormWindowState.Maximized

        try:
            if getattr(form, "InvokeRequired", False):
                form.Invoke(Action(work))
            else:
                work()
            return True
        except Exception:
            return False

    # =====================================================================
    # Status / Diagnose
    # =====================================================================
    @bridge
    def get_status(self) -> dict[str, Any]:
        db_path = getattr(self.db, "path", None)
        size = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0
        # Gate G22 (ehrliche Sicherheits-Behauptungen): Solange der oeffentliche
        # Entwicklungs-Schluessel benutzt wird, meldet der Status den REALEN
        # (unsicheren) Zustand, nie "active"/"encrypted". Schicht 2 (ChaCha20) und
        # die Passphrase-Ableitung existieren erst ab Phase 8. Keine Verschluesselung
        # vortaeuschen, solange der Schluessel oeffentlich im Repo steht.
        dev_key = getattr(self.db, "dev_key", True)
        if dev_key:
            encryption = {
                "layer1": "SQLCipher · AES-256 (public dev key, INSECURE)",
                "layer2": "ChaCha20-Poly1305 · Argon2id (not implemented)",
                "active": False,
                "dev_key": True,
            }
        else:
            encryption = {
                "layer1": "SQLCipher · AES-256",
                "layer2": "ChaCha20-Poly1305 · Argon2id",
                "active": True,
                "dev_key": False,
            }
        return {
            "db": {
                "path": db_path,
                "size": size,
                "size_human": f"{size / 1024:.1f} KB" if size else "0 KB",
            },
            "encryption": encryption,
            "runtime": {"webview2": _webview2_version()},
        }

    # =====================================================================
    # Netzwerk / Offline-Modus
    #
    # Die App arbeitet rein lokal. Der Online/Offline-Schalter ist ein reiner
    # Datenschutz-/Flugmodus-Umschalter (keine Cloud, kein Sync); ``online`` und
    # das WLAN-Symbol sind nur kosmetische Statusanzeigen.
    # =====================================================================
    @bridge
    def set_online(self, flag: bool) -> dict[str, Any]:
        self.online = bool(flag)
        return {"online": self.online}

    @bridge
    def get_wifi_signal(self) -> dict[str, Any]:
        # Liest die echte WLAN-Signalstaerke ueber "netsh wlan show interfaces".
        # Rein visuell fuer das WLAN-Symbol in der Tool-Rail. "level" 0..3 bildet
        # die Signalstaerke auf die Boegen des Symbols ab (0 = nur Punkt, kein
        # Signal / kein WLAN). Labelunabhaengig: gesucht wird eine Zeile mit
        # "Signal" und einem Prozentwert (so auch auf deutschem Windows: "Signal : 53%").
        import re
        import subprocess

        try:
            out = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            text = out.stdout.decode("utf-8", "ignore")
        except Exception:
            return {"connected": False, "percent": None, "level": 0}

        percent = None
        for line in text.splitlines():
            if "Signal" in line and "%" in line:
                m = re.search(r"(\d{1,3})\s*%", line)
                if m:
                    percent = max(0, min(100, int(m.group(1))))
                    break
        if percent is None:
            return {"connected": False, "percent": None, "level": 0}
        if percent <= 25:
            level = 1
        elif percent <= 60:
            level = 2
        else:
            level = 3
        return {"connected": True, "percent": percent, "level": level}

    # =====================================================================
    # Sicherheit (Stubs: Phase 8)
    # =====================================================================
    @bridge
    def lock(self) -> dict[str, Any]:
        self.locked = True
        return {"locked": True}

    @bridge
    def unlock(self, passphrase: str) -> dict[str, Any]:
        # Phase 8: Argon2-Hash prüfen + Schlüssel ableiten. Vorerst immer offen.
        self.locked = False
        return {"ok": True}

    @bridge
    def panic(self) -> dict[str, Any]:
        self.locked = True
        self.online = False
        return {"locked": True}

    @bridge
    def killswitch(self) -> dict[str, Any]:
        """Löscht unwiderruflich alle Nutzerdaten aus der DB (Nachtrag N10).

        Nur vom Panik-Endschirm aus erreichbar (zweistufig bestätigter
        Killswitch-Knopf). Löscht ausschließlich Datenbank-Inhalte, nie das
        Programm; der nächste Start verhält sich wie ein Erststart ohne
        Demo-Daten (Details in db.killswitch).
        """
        return self.db.killswitch()

    @bridge
    def quit_app(self) -> dict[str, Any]:
        """Beendet die App sauber (Off-Knopf des Lock-Screens, Panik-Endschirm).

        Läuft im API-Worker-Thread: das Schließen wird deshalb per
        ``form.BeginInvoke`` auf den WinForms-UI-Thread gestellt (asynchron,
        nicht blockierend), analog zu set_mini; ein direkter Fensterzugriff von
        hier könnte die Nachrichtenschleife verklemmen. Das sichere Wischen der
        Spuren (PROFILE_DIR, Gate G14) folgt in Phase 8 auf genau diesem Pfad.
        """
        win = self._window
        if win is None:
            return {"error": "no_window", "message": "Kein Fenster verfügbar."}
        form = getattr(win, "native", None)
        if form is not None:
            try:
                from System import Action  # pythonnet, nach webview.start verfügbar

                form.BeginInvoke(Action(form.Close))
                return {"ok": True}
            except Exception:
                pass
        # Fallback ohne native Form: PyWebViews eigener Weg.
        win.destroy()
        return {"ok": True}


# ---------------------------------------------------------------------------
# Sichere Zwischenablage (Phase 6.5 / Gate G23)
#
# Windows hält Clipboard-Inhalte standardmässig in der Win+V-History fest und
# synchronisiert sie je nach Einstellung ins Cloud-Clipboard (Microsoft-Konto,
# andere Geräte). Für eine Tresor-App ist beides inakzeptabel. Die folgenden
# Helfer legen Text deshalb direkt per Win32-API ab, zusammen mit den
# Ausschluss-Formaten, und können den Inhalt gezielt wieder löschen.
# ---------------------------------------------------------------------------
_CF_UNICODETEXT = 13
_GMEM_MOVEABLE = 0x0002
_CLIP_EXCLUSION_FORMATS = (
    # Vorhandensein/Wert 0 dieser registrierten Formate signalisiert Windows:
    # nicht in die History aufnehmen, nicht in die Cloud laden, nicht von
    # Clipboard-Monitoren verarbeiten lassen.
    "ExcludeClipboardContentFromMonitorProcessing",
    "CanIncludeInClipboardHistory",
    "CanUploadToCloudClipboard",
)
CLIPBOARD_CLEAR_SECONDS = 60


def _clip_apis():
    """user32/kernel32 mit 64-bit-sicheren Signaturen (Handles sind Pointer)."""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = (ctypes.c_uint, ctypes.c_size_t)
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = (ctypes.c_void_p,)
    kernel32.GlobalUnlock.argtypes = (ctypes.c_void_p,)
    user32.OpenClipboard.argtypes = (ctypes.c_void_p,)
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = (ctypes.c_uint, ctypes.c_void_p)
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = (ctypes.c_uint,)
    user32.RegisterClipboardFormatW.argtypes = (ctypes.c_wchar_p,)
    return user32, kernel32


def _global_handle(kernel32, data: bytes):
    """Bytes in einen GMEM_MOVEABLE-Block kopieren (Eigentum geht ans Clipboard)."""
    handle = kernel32.GlobalAlloc(_GMEM_MOVEABLE, len(data))
    if not handle:
        return None
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        return None
    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    return handle


def _set_clipboard_secure(text: str) -> bool:
    """Text als CF_UNICODETEXT ablegen, von History/Cloud-Sync ausgeschlossen."""
    try:
        user32, kernel32 = _clip_apis()
        if not user32.OpenClipboard(None):
            return False
        try:
            user32.EmptyClipboard()
            payload = text.encode("utf-16-le") + b"\x00\x00"
            handle = _global_handle(kernel32, payload)
            if handle is None or not user32.SetClipboardData(_CF_UNICODETEXT, handle):
                return False
            zero = (0).to_bytes(4, "little")
            for name in _CLIP_EXCLUSION_FORMATS:
                fmt = user32.RegisterClipboardFormatW(name)
                if fmt:
                    hzero = _global_handle(kernel32, zero)
                    if hzero is not None:
                        user32.SetClipboardData(fmt, hzero)
            return True
        finally:
            user32.CloseClipboard()
    except Exception:
        return False


def _read_clipboard_text() -> str | None:
    """Aktuellen CF_UNICODETEXT-Inhalt lesen (None, wenn keiner/nicht lesbar)."""
    try:
        user32, kernel32 = _clip_apis()
        if not user32.OpenClipboard(None):
            return None
        try:
            handle = user32.GetClipboardData(_CF_UNICODETEXT)
            if not handle:
                return None
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return None
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    except Exception:
        return None


def _clear_clipboard_if_matches(expected: str) -> None:
    """Zwischenablage leeren, aber nur wenn sie noch unseren Text enthält.

    Läuft als Timer-Callback ``CLIPBOARD_CLEAR_SECONDS`` nach dem Kopieren.
    Hat der Nutzer inzwischen selbst etwas anderes kopiert, bleibt das
    unangetastet.
    """
    try:
        if _read_clipboard_text() != expected:
            return
        user32, _kernel32 = _clip_apis()
        if user32.OpenClipboard(None):
            try:
                user32.EmptyClipboard()
            finally:
                user32.CloseClipboard()
    except Exception:
        pass


def _winforms_types():
    """Lädt die für den Mini-Modus benötigten WinForms-/Drawing-Typen.

    Wird erst zur Laufzeit (nach ``webview.start``) aufgerufen, wenn pythonnet und
    die WinForms-Assembly bereits geladen sind. Importe deshalb bewusst lazy, nicht
    auf Modulebene (api.py wird in main.py vor ``webview.start`` importiert).
    """
    import clr

    try:
        clr.AddReference("System.Windows.Forms")
        clr.AddReference("System.Drawing")
    except Exception:
        pass
    from System import Action
    from System.Drawing import Point, Size
    from System.Windows.Forms import FormBorderStyle, FormWindowState, Screen

    return FormBorderStyle, FormWindowState, Size, Point, Screen, Action


def _webview2_version() -> str:
    """Liest die installierte WebView2-Runtime-Version aus der Registry (best effort)."""
    try:
        import winreg

        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sub in (
                r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients"
                r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
                r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
                r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
            ):
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        return winreg.QueryValueEx(key, "pv")[0]
                except OSError:
                    continue
    except Exception:
        pass
    return "unknown"
