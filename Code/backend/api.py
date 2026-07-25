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
import inspect
import os
import re
import secrets
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable

from . import config as config_module
from . import db as db_module
from . import radio as radio_module
from . import security as security_module

# ---------------------------------------------------------------------------
# Fehler-Hygiene (Gate G29 / Bauplan N11.12).
#
# Der kanonische Fehlercode-Katalog steht in Bauplan B.2 und ist die einzige
# Wahrheit: ans Frontend geht IMMER nur ein Code aus dieser Tabelle plus der
# statische englische Text, nie str(exc), nie Pfade, Tracebacks, SQL-Fragmente
# oder Nutzertext. Details landen ausschliesslich im redigierten
# In-Memory-Ringpuffer (Api._errors, einsehbar im Status-Modal, geleert bei
# Sperre/Panik/Killswitch/Quit). Im Release existiert kein persistentes Logfile.
# ---------------------------------------------------------------------------
ERROR_MESSAGES = {
    "not_found": "Item not found.",
    "invalid": "Invalid input.",
    "locked": "App is locked.",
    "passphrase": "Wrong passphrase.",
    "rate_limited": "Too many attempts.",
    "vault": "Vault cannot be opened.",
    "canceled": "Canceled.",
    "busy": "A dialog is already open.",
    "memory": "Not enough memory. Close other apps and try again.",
    "internal": "Something went wrong.",
}


def _err(code: str, **extra: Any) -> dict[str, Any]:
    """Fehlerobjekt nach B.2: Code + statischer Katalogtext (+ Zusatzfelder)."""
    out: dict[str, Any] = {"error": code, "message": ERROR_MESSAGES[code]}
    out.update(extra)
    return out


# Alles, was wie ein Windows-/UNC-/POSIX-Pfad aussieht, wird im Ringpuffer
# durch <path> ersetzt (N11.12.1). Bewusst grosszuegig: lieber ein Wort zu viel
# redigiert als ein Benutzername zu wenig.
_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\|~[\\/]|/(?=[\w.]))[^\s'\",;|]*")


def _redact(text: str) -> str:
    """Pfade maskieren und auf 200 Zeichen kappen (Ringpuffer-Redaktion)."""
    return _PATH_RE.sub("<path>", str(text))[:200]


# ---------------------------------------------------------------------------
# Eingabe-Validierung an der Bridge (Gate G20 / Bauplan B.2, V5, N11.2.2).
#
# Jede Bridge-Methode traegt ihr kleines deklaratives Schema direkt am
# @bridge-Decorator: Parametername -> Validator. Ein Validator prueft Typ und
# Wert, normalisiert (Steuerzeichen strippen, Ueberlaenge abschneiden) und
# wirft InvalidInput bei jedem Verstoss (-> Katalog-Code "invalid"). Das
# Schema liegt introspektierbar an der Methode (wrapper._schema), damit die
# Phase-9-Tests direkt gegen die Regeln testen koennen.
# ---------------------------------------------------------------------------
MAX_TASK_TEXT = 4096
MAX_LIST_NAME = 256

# Steuerzeichen U+0000-U+001F ausser Tab (09) und Newline (0A) entfernen (G20).
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f]")


class InvalidInput(ValueError):
    """Verletzung der G20-Validierung; wird im Decorator zu ``invalid``."""


def v_text(max_len: int) -> Callable[[Any], str]:
    """Pflicht-Freitext: String, Steuerzeichen raus, auf max_len gekappt."""

    def check(value: Any) -> str:
        if not isinstance(value, str):
            raise InvalidInput("not a string")
        value = _CTRL_RE.sub("", value)[:max_len].strip()
        if not value:
            raise InvalidInput("empty")
        return value

    return check


def v_id(value: Any) -> str:
    """Brauchbare ID: nicht-leerer String (Existenz prueft die DB, not_found)."""
    if not isinstance(value, str) or not value:
        raise InvalidInput("bad id")
    return value


def v_str_list(value: Any) -> list[str]:
    """Echte Liste von Strings (kein String, kein Dict, keine Zahlen)."""
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise InvalidInput("not a list of strings")
    return value


def v_bool(value: Any) -> bool:
    """Bool, auch als 'true'/'false'-String (JS data-Attribute liefern Strings)."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise InvalidInput("not a bool")


def v_fmt(value: Any) -> str:
    """Exportformat: nur ``md`` oder ``txt`` (JSON ist gestrichen, N11.1.5)."""
    if value not in ("md", "txt"):
        raise InvalidInput("bad format")
    return value


def v_task_fields(value: Any) -> dict[str, Any]:
    """``edit_task.fields``: nur bekannte Felder, `text` String, `done` Bool (V5)."""
    if not isinstance(value, dict) or not value:
        raise InvalidInput("fields")
    out: dict[str, Any] = {}
    for key, val in value.items():
        if key == "text":
            out[key] = v_text(MAX_TASK_TEXT)(val)
        elif key == "done":
            if not isinstance(val, bool):
                raise InvalidInput("done not bool")
            out[key] = val
        else:
            raise InvalidInput("unknown field")
    return out


# Whitelist + Wert-Schema fuer set_setting (G20 c/d, V5, N11.7). Die sechs
# Akzent-Hexwerte sind die festen Presets aus B.3/B.6: der Wert landet als
# CSS-Variable im DOM, die Whitelist toetet CSS-Injection ueber Settings.
# `dark` bleibt uebergangsweise erlaubt, bis N11.6 es durch `theme` ersetzt
# (das heutige Frontend schaltet noch ueber `dark` um); `theme`/`sound`/
# `autoLock` sind schon jetzt validiert, damit die Whitelist mit N11.6/N11.7
# nicht erneut angefasst werden muss.
ACCENT_PRESETS = ("#d97757", "#c75d3a", "#5a9d6b", "#4a86c5", "#d4a23c", "#a66a9c")
SETTINGS_SCHEMA: dict[str, tuple] = {
    "accent": ("enum", ACCENT_PRESETS),
    "dark": ("bool",),  # uebergangsweise, faellt mit N11.6 zugunsten von theme
    "theme": ("enum", ("auto", "light", "dark")),
    "density": ("enum", ("comfortable", "compact")),
    "sidebar": ("enum", ("open", "closed")),
    "railPinned": ("bool",),
    "sidebarWidth": ("int_clamp", 180, 520),
    "sound": ("bool",),
    "autoLock": ("int_enum", (0, 1, 5, 15, 30, 60)),
    "exportDone": ("bool",),  # erledigte Aufgaben in den Export aufnehmen (Default an)
}


def _validate_setting(key: Any, value: Any) -> str:
    """Prueft Key gegen die Whitelist und den Wert je Key (V5).

    Liefert den normalisierten String, der in der settings-Tabelle landet
    (Bools als 'true'/'false', Zahlen dezimal). ``sidebarWidth`` wird schon
    beim SCHREIBEN auf 180-520 geklemmt, nicht erst beim Lesen geparst.
    """
    if not isinstance(key, str) or key not in SETTINGS_SCHEMA:
        raise InvalidInput("unknown setting")
    rule = SETTINGS_SCHEMA[key]
    kind = rule[0]
    if kind == "enum":
        if not isinstance(value, str) or value not in rule[1]:
            raise InvalidInput("bad enum value")
        return value
    if kind == "bool":
        return "true" if v_bool(value) else "false"
    if kind == "int_clamp":
        try:
            num = int(value)
        except (TypeError, ValueError):
            raise InvalidInput("not an int")
        return str(max(rule[1], min(rule[2], num)))
    if kind == "int_enum":
        # Bewusst KEIN str->int-Cast von Floats; '15' (Frontend-String) ist ok.
        try:
            num = int(value) if not isinstance(value, bool) else None
        except (TypeError, ValueError):
            num = None
        if num is None or num not in rule[1]:
            raise InvalidInput("bad value")
        return str(num)
    raise InvalidInput("bad rule")  # pragma: no cover - Schema-Tippfehler


# ---------------------------------------------------------------------------
# Export-Härtung (Gate G21, V6, U10 / Bauplan Phase 7).
#
# Der vorgeschlagene Dateiname entsteht IMMER über _sanitize_export_name:
# Listennamen sind Freitext und dürfen weder reservierte Windows-Gerätenamen
# noch verbotene Zeichen, Pfadtrenner, `..`-Sequenzen oder Steuerzeichen in
# den Save-Dialog tragen. Reihenfolge nach G21: erst Zeichen ersetzen, dann
# auf ca. 120 Zeichen kürzen, dann die Gerätenamen-Prüfung.
# ---------------------------------------------------------------------------
_WIN_FORBIDDEN_RE = re.compile(r'[<>:"/\\|?*]')
_RESERVED_DEVICE_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
EXPORT_NAME_MAX = 120
EXPORT_NAME_FALLBACK = "NoaToDo-Liste"  # U10 Punkt 1: sanitisiert-leerer Name


def _sanitize_export_name(name: str) -> str:
    """Listenname -> sicherer Dateinamens-Stamm (ohne Endung), Gate G21/V6."""
    # Steuerzeichen inkl. Zeilenumbrüchen und Tab durch Leerzeichen ersetzen.
    name = re.sub(r"[\x00-\x1f]", " ", str(name))
    # (a2/V6) Unter Windows verbotene Zeichen und ..-Sequenzen -> "_".
    name = _WIN_FORBIDDEN_RE.sub("_", name)
    name = re.sub(r"\.{2,}", "_", name)
    # (V6) Dann auf ca. 120 Zeichen kappen.
    name = name[:EXPORT_NAME_MAX]
    # (a) Führende/abschliessende Punkte und Leerzeichen entfernen.
    name = name.strip(" .")
    # (a) Reservierte Gerätenamen entschärfen (case-insensitive; geprüft wird
    # der Stamm vor dem ersten Punkt, damit auch "CON.backup" -> "_CON.backup";
    # die Format-Endung kommt erst danach dazu und ändert daran nichts).
    if name and name.split(".", 1)[0].upper() in _RESERVED_DEVICE_NAMES:
        name = "_" + name
    return name or EXPORT_NAME_FALLBACK


def _one_line(text: str) -> str:
    """G21 (b): Zeilenumbrüche im Task-Text/Listennamen -> ein Leerzeichen."""
    return re.sub(r"[\r\n]+", " ", str(text))


def _export_md(lists: list[dict[str, Any]], include_done: bool = True) -> list[str]:
    """md-Zeilen (U10): `#`-Überschrift je Liste, `- [ ]`/`- [x]` je Aufgabe.

    ``include_done`` (Setting ``exportDone``): erledigte Aufgaben nur ausgeben,
    wenn wahr (Default an). Bei aus bleibt die `#`-Überschrift der Liste stehen,
    nur die `- [x]`-Zeilen entfallen.
    """
    lines: list[str] = []
    for lst in lists:
        if lines:
            lines.append("")
        lines.append(f"# {_one_line(lst['name'])}")
        lines.append("")
        for t in lst["open"]:
            lines.append(f"- [ ] {_one_line(t['text'])}")
        if include_done:
            for t in lst["done"]:
                lines.append(f"- [x] {_one_line(t['text'])}")
    return lines


def _export_txt(lists: list[dict[str, Any]], include_done: bool = True) -> list[str]:
    """txt-Zeilen (U10 Punkt 2): Name, `=`-Zeile, `[ ] `/`[x] ` ohne
    Einrückung; bei mehreren Listen trennt eine Leerzeile.

    ``include_done`` (Setting ``exportDone``): erledigte Aufgaben nur ausgeben,
    wenn wahr (Default an).
    """
    lines: list[str] = []
    for lst in lists:
        if lines:
            lines.append("")
        name = _one_line(lst["name"])
        lines.append(name)
        lines.append("=" * max(1, len(name)))
        for t in lst["open"]:
            lines.append(f"[ ] {_one_line(t['text'])}")
        if include_done:
            for t in lst["done"]:
                lines.append(f"[x] {_one_line(t['text'])}")
    return lines


def _crlf(lines: list[str]) -> str:
    """U10 Punkt 3: CRLF-Zeilenenden (Notepad-tauglich), Abschluss-Newline."""
    return "\r\n".join(lines) + "\r\n"


class _NativeDialogBusy(Exception):
    """Zweiter nativer Dialog, während schon einer offen ist (N11.11.5)."""


# Serverseitige Lock-Durchsetzung als ALLOWLIST (Gate G13, B.2). Alles, was
# NICHT hier steht, wird gesperrt mit {"error":"locked"} abgewiesen, ohne die
# DB zu beruehren; das schliesst lock()/panic() ausdruecklich ein und macht
# jede kuenftig ergaenzte Methode per Default gesperrt. get_state() liefert
# gesperrt nur {"locked": true}. Die vier Onboarding-/Reset-Methoden laufen
# gerade OHNE Schluessel; change_passphrase steht bewusst NICHT drin.
ALLOWED_WHEN_LOCKED = {
    "unlock", "quit_app", "killswitch", "get_state",
    "get_boot_state", "choose_vault_dir", "create_vault", "reset_vault",
}


def bridge(fn: Callable | None = None, *, schema: dict[str, Callable] | None = None,
           mutates: bool = False) -> Callable:
    """Fängt Ausnahmen ab und liefert die Fehlerkonvention aus B.2 (Gate G29),
    validiert Argumente gegen das deklarative Schema (Gate G20) und setzt die
    serverseitige Lock-Durchsetzung als Allowlist durch (Gate G13).

    Nutzung: ``@bridge``, ``@bridge(schema={...})`` oder zusaetzlich
    ``mutates=True`` fuer schreibende Methoden (dann wird nach einem
    erfolgreichen Aufruf der G17-Write-back angestossen). Das Schema haengt als
    ``wrapper._schema`` an der Methode (introspektierbar fuer Phase-9-Tests).

    Ans Frontend gehen nur Katalog-Codes mit statischem Text; bei ``internal``
    zusaetzlich eine kurze ``ref`` auf den Ringpuffer-Eintrag.
    """

    def deco(fn: Callable) -> Callable:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            # Gate G13: gesperrt ist alles ausserhalb der Allowlist tot, ohne
            # die DB zu beruehren. Zuerst, vor jeder Validierung/Ausfuehrung.
            if getattr(self, "locked", False) and fn.__name__ not in ALLOWED_WHEN_LOCKED:
                return _err("locked")
            try:
                if schema:
                    bound = sig.bind(self, *args, **kwargs)
                    for name, validator in schema.items():
                        if name in bound.arguments:
                            bound.arguments[name] = validator(bound.arguments[name])
                    result = fn(*bound.args, **bound.kwargs)
                else:
                    result = fn(self, *args, **kwargs)
            except InvalidInput:
                return _err("invalid")
            except db_module.InvalidInput:
                return _err("invalid")
            except _NativeDialogBusy:
                # N11.11.5: höchstens ein nativer Dialog gleichzeitig; der
                # zweite Aufruf bekommt den Katalog-Code busy, kein Fehler.
                return _err("busy")
            except TypeError as exc:
                # Falsche Argument-Anzahl/-Form am Bind: unbrauchbarer Aufruf.
                if "bind" in str(exc) or "argument" in str(exc):
                    self._log_error(fn.__name__, "invalid", exc)
                    return _err("invalid")
                ref = self._log_error(fn.__name__, "internal", exc)
                return _err("internal", ref=ref)
            except KeyError as exc:
                self._log_error(fn.__name__, "not_found", exc)
                return _err("not_found")
            except MemoryError as exc:
                # N11.4.3: Speicher-Not ist weder "falsche Passphrase" noch ein
                # anonymer interner Fehler; eigener Code, kein Absturz.
                self._log_error(fn.__name__, "memory", exc)
                return _err("memory")
            except Exception as exc:  # pragma: no cover - defensiv
                ref = self._log_error(fn.__name__, "internal", exc)
                return _err("internal", ref=ref)
            # G17: nach einer erfolgreichen Mutation den debounced Write-back
            # anstossen (kein Fehler-Dict, echte Aenderung).
            if mutates and not (isinstance(result, dict) and result.get("error")):
                self._notify_change()
            return result

        wrapper._schema = schema or {}
        wrapper._mutates = mutates
        return wrapper

    if fn is not None:
        return deco(fn)
    return deco


# Typumwandlung beim Lesen der settings-Tabelle (dort liegt alles als String).
_BOOL_SETTINGS = {"dark", "exportDone", "sound"}


def _typed_settings(raw: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _BOOL_SETTINGS:
            out[k] = str(v).lower() == "true"
        else:
            out[k] = v
    return out


class Api:
    """Wird in ``main.py`` als ``js_api`` an das PyWebView-Fenster gehängt.

    Seit Phase 8 haelt die Api keine offene DB mehr direkt, sondern eine
    :class:`security.Session` mit einem entsperrten :class:`security.Vault`
    (oder keinem, wenn gesperrt). ``self._db`` ist eine Property auf die DB der
    Sitzung; gesperrt gibt es keine DB, und die G13-Allowlist im
    ``@bridge``-Decorator laesst schreibende/lesende Methoden gar nicht erst zu.
    """

    def __init__(self, session: "security_module.Session"):
        self._session = session
        session.api = self
        self.online = True
        # Startet gesperrt, sobald ein Tresor existiert; main.py setzt den
        # Zustand ueber die Boot-Weiche. Onboarding laeuft mit locked=False
        # (es gibt noch keinen Tresor, aber auch keine Daten).
        self.locked = True
        # Boot-Zustand (dreiwertig, N11.13; N11.15.3 macht ihn vierwertig):
        # 'onboarding' | 'locked' | 'unlocked' | 'vault_error'. main.py setzt
        # ihn beim Start; get_boot_state() liefert ihn ans Frontend.
        self._boot_state = "onboarding"
        self._boot_reason = None   # bei vault_error: config_damaged|vault_unreachable
        self._vault_path = None    # Pfad aus config.json (None = Onboarding)
        # Entsperr-Rate-Limit-Leiter (B.8.4/N11.4.1), persistiert in config.json.
        self._rate = security_module.RateLimiter(self._load_config, self._save_config)
        # Unterstrich-Präfix ist Pflicht: PyWebView durchsucht das Api-Objekt
        # rekursiv nach exponierbaren Methoden (util.get_functions) und steigt
        # dabei in jedes öffentliche Attribut ab. Ein dort liegendes Window-
        # Objekt würde über window.dom.body ein evaluate_js() auslösen, bevor das
        # Fenster bereit ist -> "Main window failed to start". Namen mit "_"
        # werden von der Introspektion übersprungen.
        self._window = None  # von main.py gesetzt, für Backend->Frontend-Events
        # Callback, den main.py setzt: baut das aktuelle Fenster ab (WebView
        # oder natives Lock-Fenster) und laesst die Boot-Schleife die nativen
        # teardown-Schritte 9 bis 11 nach session.next_state ausfuehren (G35).
        self._request_teardown = None
        # True, sobald eine teardown-ausloesende Methode (lock/quit/killswitch/
        # reset/autolock) laeuft. Der Fenster-X-Handler (main.py) prueft es, um
        # nicht bei einer bereits laufenden Sperre faelschlich quit_app zu
        # feuern (das wuerde next_state='locked' zu 'exit' verfaelschen).
        self._teardown_in_progress = False
        self._mini = False        # kompakter Mini-Fenster-Modus aktiv?
        self._on_setting_change = None  # optionaler Callback(key, value) für main.py
        self._on_frame_changed = None  # Callback(mini) nach jedem Mini-Modus-Wechsel
        self._clip_timer = None   # Timer für das Auto-Leeren der Zwischenablage
        # Höchstens EIN nativer Dialog gleichzeitig (N11.11.5): alle
        # create_file_dialog-Aufrufe laufen über _native_dialog(); ein zweiter
        # Aufruf bei offenem Dialog liefert den Katalog-Code busy.
        self._dialog_lock = threading.Lock()
        self._dialog_open = False   # ist gerade ein nativer Dialog offen?
        self._dialog_voided = False  # nach einer Sperre: Dialog-Ergebnis verwerfen
        # N11.11.5: feuert die Auto-Sperre bei offenem nativem Dialog, laufen
        # Schritte 1-7 sofort, aber die NATIVEN Schritte 9-11 (Fenster abbauen,
        # PROFILE_DIR wischen) werden GEPARKT, bis der Dialog zu ist (sonst wird
        # das Hauptfenster unter einem modalen Dialog abgebaut -> Haenger/Crash).
        self._pending_window_teardown = False
        # Redigierter Fehler-Ringpuffer (Gate G29 / N11.12.1): die letzten 50
        # Fehler, NUR im RAM, nie auf der Platte. Eintraege sind bereits beim
        # Schreiben redigiert (Pfade -> <path>, 200 Zeichen) und enthalten nie
        # Bridge-Argumente. Geleert bei Sperre/Panik/Killswitch/Quit.
        self._errors = deque(maxlen=50)
        # Undo-Puffer der letzten geloeschten Liste (N11.2.1): genau EINE
        # Loeschung, nur im RAM, verworfen im teardown (Schritt 7).
        self._undo_list = None
        # Zwischengespeicherte config.json (ein Schreiber, G19). Wird lazy
        # geladen und bei Bedarf atomar zurueckgeschrieben.
        self._config_cache = None

    # =====================================================================
    # DB-Zugriff und Session-Verdrahtung
    # =====================================================================
    @property
    def _db(self) -> "db_module.Database":
        """Die DB der entsperrten Sitzung.

        Gesperrt gibt es keine; da aber die G13-Allowlist alle DB-beruehrenden
        Methoden gesperrt abweist, kommt hier im Normalfall nur der entsperrte
        Zustand an. Fehlt die DB dennoch, ist das ein interner Fehler. Der
        ``_``-Praefix ist Pflicht: PyWebView durchsucht bei der Bridge-
        Introspektion alle OEFFENTLICHEN Attribute des js_api-Objekts (ruft
        ``getattr`` auf jedes); eine oeffentliche ``db``-Property wuerde dabei
        im gesperrten/Onboarding-Zustand ``RuntimeError`` werfen und den
        Fensterstart abbrechen.
        """
        vault = self._session.vault
        if vault is None or vault.db is None:
            raise RuntimeError("vault not open")
        return vault.db

    def _notify_change(self) -> None:
        """G17-Write-back nach einer erfolgreichen Mutation anstossen."""
        wb = self._session.writeback
        if wb is not None:
            wb.notify_change()

    def _load_config(self) -> dict:
        """config.json lazy laden (fuer die Rate-Limit-Leiter)."""
        if self._config_cache is None:
            try:
                cfg = config_module.load_config()
            except config_module.ConfigDamaged:
                cfg = None
            if cfg is None:
                cfg = config_module.new_config(self._vault_path or "")
            self._config_cache = cfg
        return self._config_cache

    def _save_config(self, cfg: dict) -> None:
        self._config_cache = cfg
        config_module.save_config(cfg)

    def _log_error(self, method: str, code: str, exc: BaseException) -> str:
        """Fehler in den Ringpuffer schreiben; liefert die kurze ``ref``."""
        ref = secrets.token_hex(2).upper()
        self._errors.appendleft(
            {
                "ts": datetime.now().strftime("%H:%M:%S"),
                "method": method,
                "code": code,
                "exc": type(exc).__name__,
                "ref": ref,
                "msg": _redact(exc),
            }
        )
        return ref

    # =====================================================================
    # Gesamtzustand
    # =====================================================================
    @bridge
    def get_state(self) -> dict[str, Any]:
        # Gate G13: gesperrt gibt get_state NICHTS heraus ausser dem Fakt der
        # Sperre (keine Listen, keine Settings). Damit bleibt die Regel scharf,
        # dass ein einziger JS-Aufruf gesperrt keine Daten liefert.
        if self.locked:
            return {"locked": True}
        return {
            "lists": self._db.get_lists_with_tasks(),
            "settings": _typed_settings(self._db.get_all_settings()),
            "online": self.online,
            "locked": self.locked,
        }

    @bridge
    def get_boot_state(self) -> dict[str, Any]:
        """Dreiwertige (bei Fehlern vierwertige) Boot-Weiche (N11.13/N11.15.3).

        Erster und einziger Aufruf des Frontends vor dem Rendern. main.py hat
        den Zustand beim Start ueber die Existenz von ``tasks.db.enc``
        entschieden (N11.8.2). Nach einem Unlock steht die Sitzung, dann meldet
        die Methode ``unlocked``. Gibt nie Aufgabendaten heraus (nur den Pfad,
        kein Geheimnis).
        """
        if self._session.vault is not None and not self.locked:
            state = "unlocked"
        else:
            state = self._boot_state
        out = {"state": state, "vault_path": self._vault_path}
        if state == "vault_error" and self._boot_reason:
            out["reason"] = self._boot_reason
        return out

    @bridge
    def get_lists(self) -> list[dict[str, Any]]:
        return self._db.get_lists_with_tasks()

    # =====================================================================
    # Listen
    # =====================================================================
    @bridge(schema={"name": v_text(MAX_LIST_NAME)}, mutates=True)
    def add_list(self, name: str) -> dict[str, Any]:
        return self._db.add_list(name)

    @bridge(schema={"list_id": v_id, "name": v_text(MAX_LIST_NAME)}, mutates=True)
    def rename_list(self, list_id: str, name: str) -> dict[str, Any]:
        return self._db.rename_list(list_id, name)

    @bridge(schema={"list_id": v_id}, mutates=True)
    def delete_list(self, list_id: str) -> dict[str, Any]:
        # Undo-Puffer (N11.2.1, U9): GENAU die letzte Loeschung wird samt allen
        # Aufgaben im RAM gehalten; eine neue Loeschung ueberschreibt den
        # Puffer und verwirft die vorige endgueltig. Kein Soft-Delete.
        self._undo_list = self._db.get_list_snapshot(list_id)  # KeyError -> not_found
        return self._db.delete_list(list_id)

    @bridge(schema={"list_id": v_id}, mutates=True)
    def undo_delete_list(self, list_id: str) -> dict[str, Any]:
        """Letzte Listen-Loeschung rueckgaengig machen (N11.2.1).

        Der 6-s-Toast ist reine Frontend-Anzeige; der Puffer hier hat keinen
        eigenen Verfalls-Timer und lebt, bis er ueberschrieben oder beim
        Austritt aus dem entsperrten Zustand verworfen wird. Ein spaetes Undo
        nach dem Toast darf deshalb gelingen. Stimmt die ID nicht mit dem
        Puffer ueberein (inzwischen ersetzt oder verfallen), kommt
        ``not_found`` und es wird NIE eine zweite Kopie angelegt.
        """
        buf = self._undo_list
        if buf is None or buf["list"]["id"] != list_id:
            return _err("not_found")
        self._undo_list = None
        return self._db.restore_list(buf)

    # =====================================================================
    # Aufgaben
    # =====================================================================
    @bridge(schema={"list_id": v_id, "text": v_text(MAX_TASK_TEXT)}, mutates=True)
    def add_task(self, list_id: str, text: str) -> dict[str, Any]:
        return self._db.add_task(list_id, text)

    @bridge(schema={"task_id": v_id}, mutates=True)
    def toggle_task(self, task_id: str) -> dict[str, Any]:
        return self._db.toggle_task(task_id)

    @bridge(schema={"task_id": v_id, "fields": v_task_fields}, mutates=True)
    def edit_task(self, task_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        return self._db.edit_task(task_id, fields)

    @bridge(schema={"task_id": v_id}, mutates=True)
    def delete_task(self, task_id: str) -> dict[str, Any]:
        return self._db.delete_task(task_id)

    @bridge(schema={"list_id": v_id, "ordered_ids": v_str_list}, mutates=True)
    def reorder(self, list_id: str, ordered_ids: list[str]) -> dict[str, Any]:
        return self._db.reorder(list_id, ordered_ids)

    @bridge(schema={"task_id": v_id, "target_list_id": v_id}, mutates=True)
    def move_task(self, task_id: str, target_list_id: str) -> dict[str, Any]:
        """Aufgabe in eine andere Liste verschieben (N7/N11.2, Phase 7).

        Randfaelle nach N11.2.2 (U11): fehlende Aufgabe/Zielliste ->
        ``not_found``, Ziel = aktuelle Liste -> ``invalid``; ``done`` bleibt
        erhalten, die Aufgabe haengt ans Ende ihrer Sektion in der Zielliste.
        """
        return self._db.move_task(task_id, target_list_id)

    @bridge(schema={"ordered_ids": v_str_list}, mutates=True)
    def reorder_lists(self, ordered_ids: list[str]) -> dict[str, Any]:
        """Sidebar-Reihenfolge der Listen speichern (N7/N11.2, Phase 7).

        Validierung nach N11.2.2 (U11): exakt die volle Listenmenge, sonst
        ``invalid`` und nichts wird geschrieben (alles oder nichts).
        """
        return self._db.reorder_lists(ordered_ids)

    # =====================================================================
    # Export (Phase 7 / Gate G21: Härtung + echter Save-Dialog)
    # =====================================================================
    def _list_or_none(self, list_id: str) -> dict[str, Any] | None:
        for lst in self._db.get_lists_with_tasks():
            if lst["id"] == list_id:
                return lst
        return None

    def _native_dialog(self):
        """Kontext für native Dialoge (N11.11.5): höchstens einer gleichzeitig.

        Flag im ``finally`` freigegeben; ein zweiter Aufruf bei offenem Dialog
        wirft ``_NativeDialogBusy`` (-> Katalog-Code ``busy`` im Decorator).
        Ein offener Dialog zählt NICHT als Aktivität (Auto-Lock, N11.4.2). Beim
        Eintritt wird ``_dialog_voided`` zurueckgesetzt; feuert waehrend des
        offenen Dialogs eine Sperre, setzt ``_resolve_native_dialog`` es auf
        True und das Ergebnis wird verworfen (N11.11.5 Punkt 5).
        """
        import contextlib

        @contextlib.contextmanager
        def guard():
            if not self._dialog_lock.acquire(blocking=False):
                raise _NativeDialogBusy()
            self._dialog_open = True
            self._dialog_voided = False
            try:
                yield
            finally:
                self._dialog_open = False
                self._dialog_lock.release()
                # N11.11.5: hat eine Auto-Sperre waehrend des offenen Dialogs
                # gefeuert, wurden die nativen Schritte 9-11 geparkt. Jetzt, wo
                # der Dialog zu ist (keine Modalitaet mehr), das Fenster abbauen.
                if self._pending_window_teardown:
                    self._pending_window_teardown = False
                    if self._request_teardown:
                        self._request_teardown()

        return guard()

    def _resolve_native_dialog(self, cancel: bool) -> bool:
        """teardown Schritt 2 (N11.11.5): offenen Dialog aufloesen.

        Liefert True, wenn gerade ein Dialog offen war (dann duerfen die
        nativen teardown-Schritte 9 bis 11 bei ``autolock`` geparkt werden, bis
        er zurueckkehrt). Setzt das Ergebnis auf nichtig (``_dialog_voided``),
        sodass ein nach der Sperre zurueckkehrender Dialog KEINE Datei schreibt
        und ``locked`` liefert (Angriffsvektor 2). ``cancel`` (jeder Grund
        ausser autolock) versucht zusaetzlich, das modale Fenster sofort zu
        schliessen (Best-Effort ueber WM_CLOSE ans aktive Popup).
        """
        if not self._dialog_open:
            return False
        self._dialog_voided = True
        if cancel:
            try:
                self._close_active_dialog()
            except Exception:
                pass
        return True

    def _close_active_dialog(self) -> None:
        """Best-Effort: das modale Dialogfenster des Hauptfensters schliessen.

        Sendet WM_CLOSE an das aktive Popup, das dem Hauptformular gehoert.
        Gelingt es nicht (kein Handle), bleibt der Rest geparkt und laeuft,
        sobald der Nutzer den Dialog selbst schliesst (N11.11.5 Punkt 4). Nur
        ueber den UI-Thread, wenn ein Fenster existiert.
        """
        win = self._window
        native = getattr(win, "native", None) if win is not None else None
        if native is None:
            return

        def work():
            try:
                hwnd = int(native.Handle.ToInt64())
                # GetWindow(hwnd, GW_ENABLEDPOPUP=6) liefert das aktive,
                # dem Fenster gehoerende modale Popup (der Save-Dialog).
                popup = ctypes.windll.user32.GetWindow(hwnd, 6)
                if popup:
                    ctypes.windll.user32.PostMessageW(popup, 0x0010, 0, 0)  # WM_CLOSE
            except Exception:
                pass

        try:
            from System import Action
            native.BeginInvoke(Action(work))
        except Exception:
            pass

    def _export_via_dialog(self, filename: str, lines: list[str]) -> dict[str, Any]:
        """Save-Dialog zeigen und die Datei wirklich schreiben (G21 c).

        UTF-8 ohne BOM, CRLF-Zeilenenden (U10 Punkt 3). Dialog-Abbruch: keine
        Datei, kein Nebeneffekt, Rückgabe ``canceled`` (nach B.2 bewusst
        still, U10 Punkt 4). Feuert waehrend des Dialogs eine Sperre
        (``_dialog_voided``), wird der gewaehlte Pfad verworfen, der
        Export-Inhalt aus dem Speicher genullt und ``locked`` geliefert
        (N11.11.5 Punkt 5).
        """
        win = self._window
        if win is None:
            raise RuntimeError("window not ready")   # -> internal + ref (G29)
        import webview

        with self._native_dialog():
            result = win.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename)
        # PyWebView liefert je nach Version einen String oder eine Sequenz.
        if isinstance(result, (list, tuple)):
            result = result[0] if result else None
        if self._dialog_voided or self.locked:
            # Eine Sperre ist waehrend des offenen Dialogs gefeuert: nichts
            # schreiben, den Export-Inhalt verwerfen (N11.11.5 Punkt 5).
            lines[:] = []
            return _err("locked")
        if not result:
            return _err("canceled")
        with open(result, "w", encoding="utf-8", newline="") as fh:
            fh.write(_crlf(lines))
        return {"ok": True, "filename": os.path.basename(str(result))}

    def _export_include_done(self) -> bool:
        """Setting ``exportDone`` (Default an): sollen erledigte Aufgaben mit in
        den Export? Gilt für ``export_list`` und ``export_all`` gleichermaßen."""
        return self._db.get_setting("exportDone", "true") != "false"

    @bridge(schema={"list_id": v_id, "fmt": v_fmt})
    def export_list(self, list_id: str, fmt: str = "md") -> dict[str, Any]:
        """Eine Liste als md/txt exportieren (zweistufiger Export, Schritt
        "aktuelle Liste"; N11.2, kein JSON mehr, N11.1.5).

        Der Dateinamens-Vorschlag ist der über G21/V6 sanitisierte Listenname;
        die Endung setzt das gewählte Format, nie der Nutzer-Text (U10).
        Erledigte Aufgaben nur, wenn das Setting ``exportDone`` an ist.
        """
        lst = self._list_or_none(list_id)
        if lst is None:
            return _err("not_found")
        done = self._export_include_done()
        lines = _export_md([lst], done) if fmt == "md" else _export_txt([lst], done)
        return self._export_via_dialog(
            f"{_sanitize_export_name(lst['name'])}.{fmt}", lines
        )

    @bridge(schema={"fmt": v_fmt})
    def export_all(self, fmt: str = "md") -> dict[str, Any]:
        """Alle Listen in EINE Datei exportieren (N11.2, Schritt "alle Listen").

        Reihenfolge = Sidebar-Reihenfolge (``lists.position``, U10 Punkt 5);
        Listennamen stehen wörtlich und dürfen doppelt vorkommen (U12), je
        Liste als größere Überschrift. Dateinamens-Vorschlag:
        ``NoaToDo-Export-YYYY-MM-DD.<fmt>`` (lokales Datum, U10 Punkt 1).
        Erledigte Aufgaben nur, wenn das Setting ``exportDone`` an ist.
        """
        lists = self._db.get_lists_with_tasks()
        done = self._export_include_done()
        lines = _export_md(lists, done) if fmt == "md" else _export_txt(lists, done)
        date = datetime.now().strftime("%Y-%m-%d")
        return self._export_via_dialog(f"NoaToDo-Export-{date}.{fmt}", lines)

    @bridge(schema={"task_id": v_id})
    def copy_task(self, task_id: str) -> dict[str, Any]:
        """Kopiert genau EINE Aufgabe gehärtet in die Zwischenablage (Gate G23).

        Das Kopieren passiert komplett im Backend: der Text wird mit Formaten
        abgelegt, die ihn von der Win+V-History und dem Cloud-Clipboard
        ausschliessen, und nach ``CLIPBOARD_CLEAR_SECONDS`` automatisch wieder
        gelöscht, sofern die Zwischenablage noch unseren Inhalt trägt. Eine
        ganze Liste kopiert man bewusst nicht mehr, dafür gibt es den Export.
        """
        task = self._db.get_task(task_id)
        if task is None:
            return _err("not_found")
        return self._copy_secure(task["text"])

    def _copy_secure(self, text: str) -> dict[str, Any]:
        """Gemeinsamer gehaerteter Clipboard-Pfad (G23) inkl. Auto-Clear-Timer."""
        if not _set_clipboard_secure(text):
            # Kein eigener Katalog-Code: Clipboard-Ausfall ist ein interner
            # Fehler; der @bridge-Decorator macht daraus internal + ref.
            raise RuntimeError("clipboard unavailable")
        # Merker fuer teardown Schritt 5 (V7): so kann die Sperre pruefen, ob
        # noch UNSER Inhalt im Clipboard liegt, bevor sie es leert.
        self._last_clip_text = text
        if self._clip_timer is not None:
            self._clip_timer.cancel()
        self._clip_timer = threading.Timer(
            CLIPBOARD_CLEAR_SECONDS, _clear_clipboard_if_matches, args=(text,)
        )
        self._clip_timer.daemon = True
        self._clip_timer.start()
        return {"ok": True, "clears_in": CLIPBOARD_CLEAR_SECONDS}

    @bridge
    def copy_errors(self) -> dict[str, Any]:
        """Kopiert den redigierten Fehler-Ringpuffer (G29) als Text.

        Nutzt denselben gehaerteten Backend-Clipboard-Pfad wie ``copy_task``
        (Gate G23: keine Win+V-History, kein Cloud-Clipboard, Auto-Clear).
        Der Puffer ist bereits redigiert (Pfade -> <path>, keine Argumente),
        es verlaesst also nichts Sensibles die App.
        """
        if not self._errors:
            return {"ok": True, "clears_in": 0}
        lines = [
            f"{e['ts']} {e['method']} {e['code']} {e['exc']} ref={e['ref']} {e['msg']}"
            for e in self._errors
        ]
        return self._copy_secure("\n".join(lines))

    # =====================================================================
    # Einstellungen
    # =====================================================================
    @bridge(mutates=True)
    def set_setting(self, key: str, value: Any) -> dict[str, Any]:
        # G20 (c)/(d): Key-Whitelist + Wert-/Typ-Pruefung je Key (V5). Der
        # normalisierte String landet in der DB; alles andere ist "invalid".
        normalized = _validate_setting(key, value)
        result = self._db.set_setting(key, normalized)
        if self._on_setting_change:
            self._on_setting_change(key, normalized)
        return result

    # =====================================================================
    # Fenster (Mini-/Kompaktmodus)
    # =====================================================================
    @bridge(schema={"flag": v_bool})
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
            raise RuntimeError("window not ready")   # -> internal + ref (G29)
        flag = bool(flag)
        if flag == self._mini:
            return {"mini": self._mini}
        if not self._apply_mini_window(win, flag):
            raise RuntimeError("mini switch failed")  # -> internal + ref (G29)
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
        # Gate G22 (ehrliche Sicherheits-Behauptungen): seit Phase 8 ist die
        # Verschluesselung real (beide Schichten, Argon2id, DPAPI-Pepper), also
        # meldet der Status jetzt den echten aktiven Zustand mit den konkreten
        # Werten (kein Dev-Key mehr, G9). Die Groesse bezieht sich auf das
        # einzige Ruhe-Artefakt tasks.db.enc, nicht auf eine Klartext-DB.
        enc_path = self._vault_path
        exists = bool(enc_path and os.path.exists(enc_path))
        size = os.path.getsize(enc_path) if exists else 0
        # "Zeitpunkt des letzten Wraps" (G22-Restsatz, Audit 8.4): tasks.db.enc
        # wird ausschliesslich von wrap_to_file() geschrieben, die Mtime der
        # Datei IST damit der letzte Wrap. Kein eigener Zaehler noetig, und der
        # Wert bleibt auch ueber einen Absturz hinweg ehrlich. Nicht lesbar ->
        # None (das Modal schreibt dann "unknown", nie eine erfundene Zeit).
        last_wrap = None
        if exists:
            try:
                last_wrap = time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(enc_path)))
            except OSError:
                last_wrap = None
        params = security_module.KdfParams()
        encryption = {
            "layer1": "SQLCipher · AES-256",
            "layer2": "ChaCha20-Poly1305",
            "kdf": (f"Argon2id · {params.memory_cost // 1024} MiB · "
                    f"t={params.time_cost} · p={params.parallelism}"),
            "pepper": security_module.pepper_exists(),
            "last_wrap": last_wrap,
            "active": True,
            "dev_key": False,
        }
        return {
            "db": {
                "path": enc_path,
                "size": size,
                "size_human": f"{size / 1024:.1f} KB" if size else "0 KB",
                "artifact": "tasks.db.enc",
            },
            "encryption": encryption,
            "bitlocker": _bitlocker_status(enc_path),
            "runtime": {"webview2": _webview2_version()},
            # Redigierter Fehler-Ringpuffer (G29): neueste zuerst, nur fuer die
            # "Recent errors"-Sektion des Status-Modals. Eintraege sind schon
            # beim Schreiben redigiert (<path>, 200 Zeichen, keine Argumente).
            "errors": list(self._errors),
        }

    # =====================================================================
    # Netzwerk / echter Flugmodus (N11.5)
    #
    # Der Online/Offline-Schalter (Flugzeug/Globus, Taste ``G``) schaltet seit
    # N11.5 den ECHTEN Windows-Flugmodus: offline = alle Funkgeraete des PCs
    # (WLAN/Bluetooth/Mobilfunk) real aus, online = wieder an. Umgesetzt in
    # ``backend/radio.py`` ueber die WinRT-Radio-APIs. Fehlen die Pakete oder ist
    # der Zugriff verweigert, degradiert der Schalter sichtbar ("no radio
    # access") und behauptet NIE faelschlich, dunkel zu sein (U14/U15/B.10).
    # =====================================================================
    @bridge(schema={"flag": v_bool})
    def set_online(self, flag: bool) -> dict[str, Any]:
        """Echten Flugmodus schalten, verifizierten Realzustand zurueckgeben (U15).

        Antwortet erst nach Abschluss mit ``{online, partial, access, refused}``.
        Beim Offline-Schalten wird der Funk-Ausgangszustand einmalig in
        ``config.json`` gemerkt (N11.10 Crash-Fall), damit der Beenden-Schritt 10
        ihn wiederherstellen kann. ``self.online`` traegt danach den ehrlichen,
        aggregierten Realzustand (nie die blosse Absicht).
        """
        ctrl = radio_module.get_controller()
        if not ctrl.available:
            # Kein Radio-Zugriff moeglich: NIE faelschlich "offline" behaupten.
            return {"online": self.online, "partial": True, "access": "unavailable",
                    "refused": None}
        # Vor dem ersten Ausschalten den Ausgangszustand persistieren (N11.10).
        if not flag:
            self._capture_radio_baseline(ctrl)
        res = ctrl.set_online(flag)
        self._ensure_radio_mirror(ctrl)
        online = res.get("online")
        if isinstance(online, bool):
            self.online = online
        else:
            # busy/error/unavailable: keinen Zustand faelschen, Realwert melden.
            online = self.online
        return {"online": online, "partial": bool(res.get("partial")),
                "access": res.get("access"), "refused": res.get("refused")}

    def _capture_radio_baseline(self, ctrl: "radio_module.RadioController") -> None:
        """Ausgangszustand des Funks einmalig in ``config.json`` merken (N11.10).

        Nur wenn ein echter Tresor-Pfad existiert (waehrend des Onboardings gibt
        es noch keine gueltige config.json) und noch kein Merker gesetzt ist (der
        erste App-Offline-Schritt haelt den Vor-App-Zustand fest, spaetere
        Umschaltungen ueberschreiben ihn nicht).
        """
        if not self._vault_path:
            return
        try:
            cfg = self._load_config()
        except Exception:
            return
        if cfg.get("radio_baseline"):
            return
        snap = ctrl.snapshot()
        if not snap:
            return
        cfg["radio_baseline"] = snap
        try:
            self._save_config(cfg)
        except Exception:
            pass

    def _ensure_radio_mirror(self, ctrl: "radio_module.RadioController | None" = None) -> None:
        """Externe Funk-Aenderungen ereignisbasiert ins Frontend spiegeln (N11.5).

        Idempotent: registriert den ``StateChanged``-Callback genau einmal.
        """
        if ctrl is None:
            ctrl = radio_module.get_controller()
        if not ctrl.available:
            return
        ctrl.set_change_callback(self._on_radio_external)
        ctrl.subscribe()

    def _on_radio_external(self, online: bool) -> None:
        """Callback aus dem WinRT-Ereignis-Thread (radio.py).

        Spiegelt eine externe Funk-Aenderung nur, wenn die App entsperrt ist und
        das WebView-Fenster steht (gesperrt laeuft das native Lock-Fenster, dann
        gibt es kein Ziel-DOM). Reines Statusleisten-Update ueber ``onNetChange``.
        """
        if self.locked or self._window is None:
            return
        if bool(online) == self.online:
            return
        self.online = bool(online)
        try:
            self._window.evaluate_js(
                "window.noa && window.noa.onNetChange && window.noa.onNetChange(%s);0"
                % ("true" if online else "false"))
        except Exception:
            pass

    @bridge
    def get_wifi_signal(self) -> dict[str, Any]:
        # Liest die echte WLAN-Signalstaerke ueber "netsh wlan show interfaces".
        # Rein visuell fuer das WLAN-Symbol in der Tool-Rail. "level" 0..3 bildet
        # die Signalstaerke auf die Boegen des Symbols ab (0 = nur Punkt, kein
        # Signal / kein WLAN). Labelunabhaengig: gesucht wird eine Zeile mit
        # "Signal" und einem Prozentwert (so auch auf deutschem Windows: "Signal : 53%").
        # Zusaetzlich (N11.5): die seltene Gegenpruefung der Rueckfalllinie. Das
        # Frontend pollt nur online + Fenster sichtbar + entsperrt, also ein
        # guenstiger Moment, den realen Funk-Zustand mit self.online abzugleichen
        # (Ereignisse sind die Primaerquelle). "online" reist mit zurueck.
        import re
        import subprocess

        online = self._radio_reconcile()
        try:
            out = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                timeout=4,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            text = out.stdout.decode("utf-8", "ignore")
        except Exception:
            return {"connected": False, "percent": None, "level": 0, "online": online}

        percent = None
        for line in text.splitlines():
            if "Signal" in line and "%" in line:
                m = re.search(r"(\d{1,3})\s*%", line)
                if m:
                    percent = max(0, min(100, int(m.group(1))))
                    break
        if percent is None:
            return {"connected": False, "percent": None, "level": 0, "online": online}
        if percent <= 25:
            level = 1
        elif percent <= 60:
            level = 2
        else:
            level = 3
        return {"connected": True, "percent": percent, "level": level, "online": online}

    def _radio_reconcile(self) -> bool:
        """Rueckfalllinie zu den Ereignissen (N11.5): realen Funk-Zustand abgleichen.

        Liest den aggregierten Realzustand und korrigiert ``self.online`` still,
        falls er abgedriftet ist (z.B. ein Ereignis ging verloren). Gibt den
        aktuellen ``self.online`` zurueck; ist der Funk nicht lesbar, bleibt der
        bisherige Wert unveraendert (nichts faelschen).
        """
        try:
            ctrl = radio_module.get_controller()
            if not ctrl.available:
                return self.online
            real = ctrl.read_online()
            if isinstance(real, bool) and real != self.online:
                self.online = real
        except Exception:
            pass
        return self.online

    # =====================================================================
    # Auto-Sperre-Aktivitaet (B.8.3 / N11.4.2)
    # =====================================================================
    @bridge
    def activity_ping(self) -> dict[str, Any]:
        """Stempelt Aktivitaet auf die monotone Backend-Uhr (N11.4.2).

        Der EINZIGE Aufruf, der den Auto-Sperr-Timer zuruecksetzt; er nimmt
        keinen Zeitwert entgegen, kann ``last_activity`` nie in die Zukunft
        setzen und den Timer nicht abschalten. Steht bewusst NICHT in
        ALLOWED_WHEN_LOCKED: gesperrt liefert der Decorator ``locked`` und der
        Timer bleibt unberuehrt (eine gesperrte App laesst sich nicht
        wachhalten).
        """
        al = self._session.autolock
        if al is not None:
            al.ping()
        return {"ok": True}

    # =====================================================================
    # Onboarding / Tresor-Verwaltung (N11.13, Phase 8)
    # =====================================================================
    @bridge
    def choose_vault_dir(self) -> dict[str, Any]:
        """Nativer Ordner-Dialog fuer den Tresor-Ort (N11.13, G32).

        Prueft die Schreibbarkeit, warnt bei erkannten Cloud-/Wechsel-/
        Netzpfaden (G32/N11.15.4) und meldet ``has_vault:true``, wenn im Ordner
        schon eine ``tasks.db.enc`` liegt (dann bietet das Onboarding "Diesen
        Tresor oeffnen" statt "neu anlegen", N11.15.6). Abbruch -> ``canceled``.
        """
        win = self._window
        if win is None:
            raise RuntimeError("window not ready")
        import webview

        with self._native_dialog():
            result = win.create_file_dialog(webview.FOLDER_DIALOG)
        if isinstance(result, (list, tuple)):
            result = result[0] if result else None
        if not result:
            return _err("canceled")
        path = str(result)
        if not os.path.isdir(path) or not os.access(path, os.W_OK):
            return _err("invalid")
        has_vault = os.path.exists(os.path.join(path, "tasks.db.enc"))
        return {
            "path": path,
            "has_vault": has_vault,
            "warning": _path_risk_warning(path),
        }

    @bridge(schema={"path": v_id, "passphrase": v_id})
    def create_vault(self, path: str, passphrase: str) -> dict[str, Any]:
        """Neuen, leeren Tresor anlegen (N11.13, Onboarding-Schritt 3).

        Passphrase-Regel: ausschliesslich Mindestlaenge 12 (N11.3). Ein
        bestehender Tresor wird NIE ueberschrieben (Backend-Riegel N11.15.6:
        vorhandene ``tasks.db.enc`` -> ``invalid``). G33: eine alte Dev-DB wird
        beim ersten Anlegen ueber den Secure-Delete-Pfad entsorgt. Danach ist
        die App entsperrt.
        """
        if len(passphrase) < 12:
            return _err("invalid")
        enc_path = os.path.join(path, "tasks.db.enc")
        if os.path.exists(enc_path):
            return _err("invalid")   # N11.15.6: nie ueberschreiben
        if not os.path.isdir(path) or not os.access(path, os.W_OK):
            return _err("invalid")
        try:
            vault = security_module.Vault.create(enc_path, passphrase)
        except MemoryError:
            return _err("memory")
        except security_module.VaultError:
            return _err("vault")
        # G33: alte Dev-DB (data/tasks.db samt Journalen) sicher wegraeumen.
        _cleanup_dev_legacy_db()
        cfg = config_module.new_config(enc_path)
        config_module.save_config(cfg)
        self._config_cache = cfg
        self._vault_path = enc_path
        self._attach_vault(vault)
        return {"ok": True}

    @bridge(schema={"path": v_id})
    def open_existing_vault(self, path: str) -> dict[str, Any]:
        """Vorhandenen Tresor im Onboarding oeffnen (N11.15.6), nie ueberschreiben.

        Der Ordner enthaelt schon eine ``tasks.db.enc``: statt einen neuen
        anzulegen, wird nur der Pfad in eine frische ``config.json`` geschrieben
        und die Boot-Schleife ins native Lock-Fenster geschickt (Passphrase-
        Eingabe). Laeuft im Onboarding (``locked=False``), gibt nie Daten
        heraus.
        """
        enc_path = os.path.join(path, "tasks.db.enc")
        if not os.path.exists(enc_path):
            return _err("vault")
        cfg = config_module.new_config(enc_path)
        config_module.save_config(cfg)
        self._config_cache = cfg
        self._vault_path = enc_path
        self._boot_state = "locked"
        self.locked = True
        # Kein teardown noetig (es ist kein Tresor offen, keine Schluessel):
        # nur das WebView abbauen, die Boot-Schleife zeigt dann das native
        # Lock-Fenster.
        self._session.next_state = "locked"
        self._teardown_in_progress = True
        if self._request_teardown:
            self._request_teardown()
        return {"ok": True}

    @bridge(schema={"old": v_id, "new": v_id})
    def change_passphrase(self, old: str, new: str) -> dict[str, Any]:
        """Passphrase in den Einstellungen aendern (N11.3 a-d, nur entsperrt).

        Bewusst NICHT in ALLOWED_WHEN_LOCKED (braucht die Schluessel). Die
        alte Passphrase wird ueber die abgeleiteten Schluessel geprueft (kein
        gespeicherter Hash); frisches Salt + frische Nonce, der Pepper bleibt,
        die ``.bak`` wird mit dem neuen Schluessel neu geschrieben (nichts
        bleibt alt-lesbar), die Argon2-Parameter werden auf den Soll-Stand
        gehoben. Rate-Limit wie beim Entsperren.
        """
        vault = self._session.vault
        if vault is None:
            raise RuntimeError("vault not open")
        if len(new) < 12:
            return _err("invalid")
        wait = self._rate.remaining()
        if wait > 0:
            return _err("rate_limited", retry_in=wait)
        pepper = security_module.get_pepper(create=False)
        try:
            old_aes, old_chacha = security_module.derive_keys(
                old, pepper, vault.salt, vault.params)
        except MemoryError:
            security_module.zeroize(pepper)
            return _err("memory")
        ok = vault.matches_aes(old_aes)
        security_module.zeroize(old_aes)
        security_module.zeroize(old_chacha)
        if not ok:
            # Falsche alte Passphrase: als Rateversuch werten (N11.13).
            self._rate.register_fail()
            security_module.zeroize(pepper)
            return _err("passphrase", retry_in=self._rate.remaining() or 2)
        new_salt = os.urandom(security_module.SALT_LEN)
        new_params = security_module.KdfParams()   # Soll-Stand (KDF-Upgrade)
        try:
            new_aes, new_chacha = security_module.derive_keys(
                new, pepper, new_salt, new_params)
        except MemoryError:
            security_module.zeroize(pepper)
            return _err("memory")
        finally:
            security_module.zeroize(pepper)
        vault.rewrap_with(new_aes, new_chacha, new_params, new_salt)
        self._rate.reset()
        return {"ok": True}

    @bridge
    def reset_vault(self) -> dict[str, Any]:
        """Ausweg der vergessenen Passphrase (N11.13): teardown('reset').

        Loescht Tresor + .bak + Metadaten + Pepper (Schritte 6-8), beendet die
        App NICHT, sondern laesst die Boot-Schleife ins Onboarding springen
        (next_state='onboarding'). Im UI wie der Killswitch abgesichert
        (Bestaetigung, dann RESET tippen); erreichbar auch aus dem gesperrten
        Zustand (Allowlist).
        """
        self._teardown_in_progress = True
        security_module.run_teardown("reset", self._session)
        # run_teardown('reset') hat config.json bereits geloescht (Schritt 8);
        # den Ratelimiter NUR im Speicher zuruecksetzen, sonst schriebe
        # _rate.reset() ueber _load_config eine neue Konfig mit leerem
        # vault_path zurueck (naechster Boot faelschlich vault_error).
        self._vault_path = None
        self._config_cache = None
        self._rate.reset_memory()
        self._boot_state = "onboarding"
        if self._request_teardown:
            self._request_teardown()
        return {"ok": True}

    # =====================================================================
    # Sperren / Entsperren / Panik / Beenden (B.8, Phase 8)
    # =====================================================================
    @bridge
    def unlock(self, passphrase: str) -> dict[str, Any]:
        """Entsperren nach der N6-Fehlerlogik (B.2) + Rate-Limit (N11.4.1).

        Reihenfolge (im Zweifel pro Sicherheit): (1) unverschluesselten Kopf
        lesen und pruefen (Datei fehlt / Kopf unlesbar -> ``vault``, KEIN
        Argon2, treibt die Leiter nicht); (2) Rate-Limit pruefen
        (``rate_limited`` + retry_in); (3) persist-before-verify: den Versuch
        zaehlen und schreiben, BEVOR die teure Ableitung laeuft; (4) ableiten +
        AEAD (Tag-Fehler -> ``passphrase`` + retry_in, treibt die Leiter;
        MemoryError -> ``memory``, treibt sie NICHT; fehlender Pepper ->
        ``vault``, treibt sie nicht); (5) Erfolg: Leiter zuruecksetzen,
        Sitzung aufbauen, entsperrt.
        """
        if not self._vault_path:
            return _err("vault")
        # (1) Kopf lesen/pruefen ohne Passphrase, ohne Argon2 (N6 Schritt 1/2).
        try:
            params, salt, nonce, header, ciphertext = security_module.read_container(
                self._vault_path)
        except security_module.VaultError:
            return _err("vault")
        # (2) Rate-Limit.
        wait = self._rate.remaining()
        if wait > 0:
            return _err("rate_limited", retry_in=wait)
        # (3) persist-before-verify: jetzt zaehlen und schreiben.
        self._rate.register_fail()
        # (4) Pepper + Ableitung + AEAD.
        try:
            pepper = security_module.get_pepper(create=False)
        except security_module.VaultError:
            self._rate.undo_last_fail()   # fehlender Pepper ist kein Rateversuch
            return _err("vault")
        try:
            aes_key, chacha_key = security_module.derive_keys(
                passphrase, pepper, salt, params)
        except MemoryError:
            self._rate.undo_last_fail()   # Speicher-Not treibt die Leiter nicht
            security_module.zeroize(pepper)
            return _err("memory")
        finally:
            security_module.zeroize(pepper)
        try:
            inner = security_module.unwrap(chacha_key, header, nonce, ciphertext)
        except security_module.WrongPassphrase:
            security_module.zeroize(aes_key)
            security_module.zeroize(chacha_key)
            return _err("passphrase", retry_in=self._rate.remaining() or 2)
        # (5) Erfolg.
        try:
            vault = security_module.Vault.from_keys(
                self._vault_path, aes_key, chacha_key, params, salt, inner)
        finally:
            inner = b""
        self._rate.reset()
        self._attach_vault(vault)
        return {"ok": True}

    @bridge
    def lock(self) -> dict[str, Any]:
        """Sperren (Lock-Button / Ctrl+L): die eine teardown-Sequenz (G35).

        Steps 1-8 laufen synchron (flush, DB zu, Schluessel nullen); die
        nativen Schritte 9-11 (WebView abbauen, PROFILE_DIR wischen, Lock-
        Screen) uebernimmt main.py ueber den teardown-Request. N11.10: der
        Online-/Funkzustand wird beim Sperren NICHT angefasst.
        """
        self._teardown_in_progress = True
        try:
            security_module.run_teardown("lock", self._session)
        except security_module.TeardownAbort:
            # Schritt 4 (Write-back) gescheitert: nicht sperren, Fehler zeigen.
            self._teardown_in_progress = False
            return _err("vault")
        if self._request_teardown:
            self._request_teardown()
        return {"locked": True}

    @bridge
    def panic(self) -> dict[str, Any]:
        """Panik-Confirm: KEIN Ausgang (N11.11.1), fuehrt in den Endschirm.

        Raeumt den Raum (Frontend) + schaltet ECHT offline (N11.10: nur der
        Panik-Flow schaltet neben dem Nutzer-Toggle noch Funk) + verwirft die
        fluechtigen RAM-Puffer. Der eigentliche Abbau (Schluessel nullen,
        Dateien) passiert erst ueber die Endschirm-Knoepfe (Finish ->
        quit_app -> teardown('quit'); Killswitch -> teardown('killswitch')).
        Der Ausgangszustand wird gemerkt, damit das Beenden ihn wiederherstellt.
        """
        try:
            ctrl = radio_module.get_controller()
            if ctrl.available:
                self._capture_radio_baseline(ctrl)
                res = ctrl.set_online(False)
                if isinstance(res.get("online"), bool):
                    # Ehrlich: bleibt ein Radio an (verweigert), zeigt online.
                    self.online = res["online"]
            # Ohne Radio-Zugriff bleibt self.online ehrlich stehen (U15).
        except Exception:
            pass
        self._errors.clear()
        self._undo_list = None
        return {"locked": True}

    @bridge
    def killswitch(self) -> dict[str, Any]:
        """Unwiderrufliche Datei-Loeschung (B.8.7/N11.8.1): teardown('killswitch').

        Reine Datei-Operation ohne Schluessel (tasks.db.enc + .bak + Metadaten
        + Pepper + Arbeitsordner), funktioniert gesperrt wie entsperrt
        (Allowlist). Danach beendet die Boot-Schleife die App; der naechste
        Start ist mangels Datei ein leerer Erststart.
        """
        self._teardown_in_progress = True
        security_module.run_teardown("killswitch", self._session)
        self._vault_path = None
        self._config_cache = None
        if self._request_teardown:
            self._request_teardown()
        return {"ok": True}

    @bridge
    def quit_app(self) -> dict[str, Any]:
        """Sauberes Beenden (Off-Knopf, Panik-Finish, Fenster-X):
        teardown('quit').

        Flush, DB zu, Schluessel nullen; danach baut main.py das Fenster ab,
        wischt PROFILE_DIR (G14) und beendet den Prozess. Loescht nie Nutzer-
        oder App-Daten.
        """
        self._teardown_in_progress = True
        try:
            security_module.run_teardown("quit", self._session)
        except security_module.TeardownAbort:
            self._teardown_in_progress = False
            return _err("vault")
        if self._request_teardown:
            self._request_teardown()
        return {"ok": True}

    # =====================================================================
    # Session-Verdrahtung (von main.py / teardown genutzt, nie ueber die Bridge)
    # =====================================================================
    def _attach_vault(self, vault: "security_module.Vault") -> None:
        """Frisch entsperrte/angelegte Sitzung aktivieren (Write-back + Auto-Lock)."""
        self._session.vault = vault
        self._session.writeback = security_module.WriteBack(vault.flush)
        if self._session.autolock is None:
            self._session.autolock = security_module.AutoLock(
                self._autolock_minutes, self._on_autolock)
            self._session.autolock.start()
        self._session.autolock.arm()
        self.locked = False
        self._boot_state = "unlocked"
        self._teardown_in_progress = False
        # N11.5: beim Entsperren den ECHTEN Funk-Zustand uebernehmen (nicht das
        # Default-True raten) und die ereignisbasierte Spiegelung starten.
        try:
            ctrl = radio_module.get_controller()
            if ctrl.available:
                real = ctrl.read_online()
                if isinstance(real, bool):
                    self.online = real
                self._ensure_radio_mirror(ctrl)
        except Exception:
            pass

    def _autolock_minutes(self) -> int:
        """Aktuelles Auto-Lock-Timeout in Minuten (Setting ``autoLock``, 0=nie)."""
        try:
            return int(self._db.get_setting("autoLock", "15"))
        except Exception:
            return 15

    def _on_autolock(self) -> None:
        """Callback des Auto-Sperr-Timers (eigener Thread, B.8.3).

        Feuert die teardown('autolock')-Sequenz. Bei offenem nativem Dialog
        laufen Schritte 1-7 sofort und die nativen Schritte werden ueber
        main.py geparkt (N11.11.5); der Timer selbst bleibt fail-safe.
        """
        self._teardown_in_progress = True
        try:
            security_module.run_teardown("autolock", self._session)
        except security_module.TeardownAbort:
            self._teardown_in_progress = False
            return
        # Frontend sofort auf den Lock-Screen (reines DOM, auch unter einem
        # modalen Dialog sicher, N11.11.5 Punkt 2).
        try:
            if self._window is not None:
                self._window.evaluate_js(
                    "window.noa && window.noa.onLocked && window.noa.onLocked();0")
        except Exception:
            pass
        # N11.11.5: War beim Feuern ein nativer Dialog offen (deferred_native),
        # sind Schritte 1-7 gelaufen (Schluessel genullt), aber das Hauptfenster
        # darf NICHT unter dem modalen Dialog abgebaut werden. Den Dialog selbst
        # schliessen (Best effort) und den Fenster-Abbau parken, bis der Dialog
        # zurueckkehrt (dann feuert der _native_dialog-Kontext den geparkten
        # Abbau). Sonst (kein Dialog): sofort abbauen.
        if getattr(self._session, "deferred_native", False):
            self._pending_window_teardown = True
            try:
                self._close_active_dialog()
            except Exception:
                pass
        elif self._request_teardown:
            self._request_teardown()

    def _clear_own_clipboard(self) -> None:
        """teardown Schritt 5 (V7/G23): Clipboard leeren, wenn App-Inhalt drin.

        Bricht den 60-s-Auto-Clear-Timer ab und leert das Clipboard sofort,
        aber NUR wenn es noch unseren zuletzt kopierten Text traegt (dieselbe
        Pruefung wie der Auto-Clear). Fremder Inhalt (der Nutzer hat inzwischen
        etwas anderes kopiert) bleibt unangetastet.
        """
        if self._clip_timer is not None:
            try:
                self._clip_timer.cancel()
            except Exception:
                pass
            self._clip_timer = None
        last = getattr(self, "_last_clip_text", None)
        if last is not None:
            _clear_clipboard_if_matches(last)
            self._last_clip_text = None

    def _detach_db(self) -> None:
        """teardown Schritt 6: nach dem Schliessen des Vault greift kein
        DB-Zugriff mehr durch (die ``db``-Property wirft dann, und die
        G13-Allowlist blockt ohnehin alle DB-Methoden im gesperrten Zustand).
        Der Konfig-Cache bleibt gueltig (er enthaelt nichts Geheimes)."""
        return

    def _drop_volatile(self) -> None:
        """teardown Schritt 7: fluechtige RAM-Puffer verwerfen (G29/N11.2.1)."""
        self._errors.clear()
        self._undo_list = None


# ---------------------------------------------------------------------------
# BitLocker-Status (Gate G31): ehrlich "unknown" bei unlesbarer Abfrage
# ---------------------------------------------------------------------------

def _bitlocker_status(path: str | None) -> dict[str, Any]:
    """Realer BitLocker-Schutzstatus des Tresor-Laufwerks (G31, B.10.4).

    Fragt ``Win32_EncryptableVolume`` per PowerShell/WMI ab. Ist die Abfrage
    nicht lesbar (kein Admin, WMI-Klasse fehlt, Timeout), meldet die Funktion
    ehrlich ``"unknown"`` und NIE ein falsches "protected" (G22/G31). Rein
    informativ fuer das Status-Modal; die App erzwingt nichts.
    """
    drive = None
    if path:
        drive = os.path.splitdrive(os.path.abspath(path))[0]  # z.B. "C:"
    if not drive:
        drive = os.path.splitdrive(os.path.abspath(os.getcwd()))[0]
    result = {"state": "unknown", "drive": drive}
    if not drive:
        return result
    import subprocess

    # ProtectionStatus: 0 = aus, 1 = an, 2 = unbekannt. Ueber die Security-WMI-
    # Klasse, die keine Admin-Rechte fuer das reine Lesen braucht.
    ps = (
        "$v = Get-CimInstance -Namespace 'root/cimv2/Security/MicrosoftVolumeEncryption' "
        "-ClassName Win32_EncryptableVolume "
        f"-Filter \"DriveLetter='{drive}'\" -ErrorAction Stop; "
        "$v.ProtectionStatus"
    )
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        val = out.stdout.decode("ascii", "ignore").strip()
    except Exception:
        return result
    if val == "1":
        result["state"] = "protected"
    elif val == "0":
        result["state"] = "off"
    # alles andere (leer, "2", Fehler): bleibt "unknown" (ehrlich)
    return result


# ---------------------------------------------------------------------------
# Tresor-Ort-Warnungen (Gate G32 / N11.15.4): Cloud, Wechsel-, Netzpfade
# ---------------------------------------------------------------------------

def _path_risk_warning(path: str) -> str | None:
    """Warntext bei riskanten Tresor-Orten (G32/N11.15.4), sonst ``None``.

    Erkennt Cloud-Sync-Ordner (OneDrive/Dropbox, Env-Vars + Heuristik) sowie
    Wechsel-/Netzlaufwerke. Nennt bei Cloud immer BEIDE Kernsaetze:
    Versionshistorie beim Anbieter UND Killswitch/Reset loeschen dort nichts.
    Warnung, nie Sperre.
    """
    p = os.path.abspath(path)
    low = p.lower()
    cloud_roots = []
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        v = os.environ.get(var)
        if v:
            cloud_roots.append(v.lower())
    is_cloud = any(low.startswith(r) for r in cloud_roots)
    if not is_cloud and ("onedrive" in low or "dropbox" in low or "google drive" in low):
        is_cloud = True
    if is_cloud:
        return ("This folder is in a cloud-synced location. The encrypted file "
                "would be uploaded, the provider keeps version history, and "
                "Killswitch/Reset cannot delete those cloud copies.")
    # Wechsel-/Netzlaufwerk (best effort).
    try:
        drive = os.path.splitdrive(p)[0]
        if drive:
            dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive + "\\"))
            if dtype == 2:   # DRIVE_REMOVABLE
                return ("This is a removable drive. If it is unplugged, the app "
                        "cannot open the vault, and secure erase is not reliable "
                        "on foreign file systems.")
            if dtype == 4:   # DRIVE_REMOTE
                return ("This is a network/UNC location. If the share is offline "
                        "the app cannot open the vault, and secure erase is not "
                        "reliable there.")
        if p.startswith("\\\\"):
            return ("This is a network/UNC location. If the share is offline the "
                    "app cannot open the vault, and secure erase is not reliable "
                    "there.")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Alte Dev-DB entsorgen (Gate G33): beim ersten create_vault
# ---------------------------------------------------------------------------

def _cleanup_dev_legacy_db() -> None:
    """Alte Klartext-lesbare Dev-DB ``data/tasks.db`` sicher wegraeumen (G33).

    Die frueheren Phasen oeffneten ``data/tasks.db`` mit einem oeffentlichen
    Schluessel. Beim ersten echten ``create_vault()`` wird sie samt
    ``-journal``/``-wal``/``-shm`` ueber den Secure-Delete-Pfad entsorgt (nie
    blankes ``os.remove``). Ehrliche Restgrenze (SSD-Wear-Leveling) nennt das
    Onboarding als Einmal-Hinweis.
    """
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tasks.db")
    for suffix in ("", "-journal", "-wal", "-shm"):
        security_module.secure_delete(base + suffix)


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
