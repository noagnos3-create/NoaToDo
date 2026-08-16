# NoaToDo, a local encrypted to-do app for Windows.
# Copyright (C) 2026 Noa Gnos
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Echter Windows-Flugmodus ueber die WinRT-Radio-APIs (Etikett N11.5).

Der Online/Offline-Schalter (Flugzeug/Globus, Taste ``G``) ist seit N11.5 kein
Deko-Flag mehr: offline schalten heisst, **alle** Funkgeraete des PCs (WLAN,
Bluetooth, Mobilfunk) real auszuschalten, online schalten aktiviert sie wieder.
Es gibt kein oeffentliches Flugmodus-Flag; schaltbar sind nur die einzelnen
Radios, darum enumeriert dieses Modul sie (``Radio.GetRadiosAsync``) und setzt
je Treffer ``SetStateAsync`` (U14).

Verbindliche Facetten (N11.5, U14/U15):

- **Antwort erst nach Abschluss, nie feuern-und-vergessen.** Nach dem Schalten
  wird der reale Zustand aller Radios neu eingelesen und zurueckgegeben, nie die
  blosse Absicht.
- **Sicherheits-Aggregation, Offline ist die schutzrelevante Richtung.** Der
  aggregierte ``online`` ist wahr, sobald **irgendein** verwaltetes Radio noch an
  ist. Die App behauptet also nie "dunkel", solange noch etwas sendet.
- **Verweigerter Zugriff degradiert sichtbar statt still.** Ist
  ``RequestAccessAsync`` nicht ``Allowed`` (oder fehlen die winrt-Pakete), wird
  **kein** Radio angefasst; der Aufrufer zeigt den Tooltip "no radio access" und
  laesst den realen Zustand stehen.
- **Kein Doppel-Schalten.** Hoechstens **eine** Radio-Operation gleichzeitig
  (nicht blockierendes Lock); ein zweiter Ausloeser waehrend einer laufenden
  Operation wird ignoriert.
- **Externe Aenderungen spiegeln.** Aendert der Nutzer den Funk in den
  Windows-Einstellungen, feuert ``StateChanged`` je Radio; der registrierte
  Callback meldet den neuen aggregierten Zustand ans Frontend (ereignisbasiert,
  eine Gegenpruefung ueber ``read_online`` ist die seltene Rueckfalllinie).

**Kein Sicherheits-Riegel (B.10):** der Schalter ist ein Privatsphaere-/
Bequemlichkeits-Werkzeug gegen beilaeufiges Funken, kein Schutz gegen
Schadsoftware, die Radios selbst wieder anschalten koennte. Er darf nur nie
*behaupten*, dunkel zu sein, wenn er es nicht ist.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

try:  # Modulare PyWinRT-Pakete (Phase 0, G11). Fehlen sie, degradiert alles
    # sichtbar auf "no radio access", nie ein stiller Falsch-Zustand.
    import winrt.windows.devices.radios as _radios
    import winrt.windows.foundation.collections  # noqa: F401 (IVectorView-Projektion)
    _WINRT_OK = True
except Exception:  # pragma: no cover (nur auf Nicht-Zielplattformen)
    _radios = None
    _WINRT_OK = False

# RadioKind-Ganzzahlen (Windows.Devices.Radios.RadioKind): Other=0, WiFi=1,
# MobileBroadband=2, Bluetooth=3, FM=4. Angefasst werden nur WLAN, Mobilfunk und
# Bluetooth; Other und GPS/FM bleiben unberuehrt (U14).
_KIND_WIFI = 1
_KIND_MOBILE = 2
_KIND_BLUETOOTH = 3
_MANAGED_KINDS = frozenset((_KIND_WIFI, _KIND_MOBILE, _KIND_BLUETOOTH))
_KIND_LABEL = {_KIND_WIFI: "WiFi", _KIND_MOBILE: "Mobile data", _KIND_BLUETOOTH: "Bluetooth"}

# RadioState: Unknown=0, On=1, Off=2, Disabled=3.
_STATE_ON = 1

# RadioAccessStatus: Unspecified=0, Allowed=1, DeniedBySystem=2, DeniedByUser=3.
_ACCESS_ALLOWED = 1


class RadioController:
    """Kapselt die Radio-Enumeration, das Schalten und die Ereignis-Spiegelung.

    Ein Prozess-Singleton (:func:`get_controller`); die Api verdrahtet den
    Aenderungs-Callback und ``main.py`` nutzt :meth:`restore` in teardown
    Schritt 10.
    """

    def __init__(self) -> None:
        # Genau EINE Radio-Operation gleichzeitig (kein Doppel-Schalten, U15).
        self._op_lock = threading.Lock()
        self._access: int | None = None      # gecachter RadioAccessStatus
        self._subscribed = False
        self._handlers: list[tuple[Any, int]] = []   # (Radio, Token) fuer Cleanup
        self._on_change: Callable[[bool], None] | None = None
        self._last_online: bool | None = None

    # -- Verfuegbarkeit / Zugriff ----------------------------------------
    @property
    def available(self) -> bool:
        """True, wenn die winrt-Pakete geladen sind (sonst durchweg degradiert)."""
        return _WINRT_OK

    def _request_access(self) -> bool:
        """``RequestAccessAsync`` einmalig auswerten und cachen (U14)."""
        if not _WINRT_OK:
            return False
        if self._access is None:
            try:
                self._access = int(_radios.Radio.request_access_async().get())
            except Exception:
                self._access = 0   # Unspecified: sicherheitshalber wie verweigert
        return self._access == _ACCESS_ALLOWED

    def _managed(self) -> list[Any]:
        """Alle verwalteten Radios (WLAN/Mobilfunk/Bluetooth), frisch gelesen."""
        radios = _radios.Radio.get_radios_async().get()
        return [rd for rd in radios if int(rd.kind) in _MANAGED_KINDS]

    def read_online(self) -> bool | None:
        """Realer aggregierter Zustand: True, wenn irgendein Radio an ist.

        ``None`` bedeutet "nicht lesbar" (Pakete fehlen oder Enumeration
        gescheitert); der Aufrufer faelscht dann keinen Zustand.
        """
        if not _WINRT_OK:
            return None
        try:
            managed = self._managed()
        except Exception:
            return None
        return any(int(rd.state) == _STATE_ON for rd in managed)

    def snapshot(self) -> dict[str, int] | None:
        """Aktuellen Zustand je Radio (Name -> RadioState-Int) fuer den Merker."""
        if not _WINRT_OK:
            return None
        try:
            managed = self._managed()
        except Exception:
            return None
        try:
            return {rd.name: int(rd.state) for rd in managed}
        except Exception:
            return None

    # -- Schalten --------------------------------------------------------
    def set_online(self, target_online: bool) -> dict[str, Any]:
        """Alle verwalteten Radios schalten, danach den realen Zustand zurueckgeben.

        Rueckgabe: ``{online, partial, access, refused}``.
        - ``online``: verifizierter, aggregierter Realzustand (``None`` = nicht
          ermittelbar, Aufrufer faelscht nichts).
        - ``partial``: True, wenn nicht jedes Ziel-Radio den Wunschzustand
          erreicht hat.
        - ``access``: ``allowed`` | ``denied`` | ``unavailable`` | ``busy`` |
          ``error``.
        - ``refused``: Label des ersten nicht gehorchenden Radios (fuer den
          ehrlichen Pillen-Tooltip) oder ``None``.
        """
        if not _WINRT_OK:
            return {"online": None, "partial": True, "access": "unavailable", "refused": None}
        if not self._request_access():
            return {"online": self.read_online(), "partial": True,
                    "access": "denied", "refused": None}
        # Kein Doppel-Schalten: laeuft schon eine Operation, ignorieren (U15).
        if not self._op_lock.acquire(blocking=False):
            return {"online": None, "partial": True, "access": "busy", "refused": None}
        try:
            return self._do_set(target_online)
        finally:
            self._op_lock.release()

    def _do_set(self, target_online: bool) -> dict[str, Any]:
        target = _radios.RadioState.ON if target_online else _radios.RadioState.OFF
        try:
            managed = self._managed()
        except Exception:
            return {"online": self.read_online(), "partial": True,
                    "access": "error", "refused": None}
        for rd in managed:
            try:
                rd.set_state_async(target).get()   # blockiert bis fertig (U15)
            except Exception:
                pass   # ein einzelnes verweigerndes Radio darf den Rest nicht stoppen
        # Realzustand NEU einlesen (nie feuern-und-vergessen).
        try:
            managed = self._managed()
        except Exception:
            pass
        any_on = False
        refused: str | None = None
        for rd in managed:
            try:
                on = int(rd.state) == _STATE_ON
                kind = int(rd.kind)
            except Exception:
                continue
            if on:
                any_on = True
            if on != target_online and refused is None:
                refused = _KIND_LABEL.get(kind, "Radio")
        # U15-Aggregation: online, sobald irgendein Radio an ist (in beide
        # Richtungen; offline ist die schutzrelevante, ehrlichere Anzeige).
        online = any_on
        self._last_online = online
        return {"online": online, "partial": refused is not None,
                "access": "allowed", "refused": refused}

    def restore(self, baseline: dict[str, int] | None) -> None:
        """teardown Schritt 10 / Crash-Recovery: Ausgangszustand wiederherstellen.

        ``baseline`` ist der beim ersten App-Offline gemerkte Zustand (Name ->
        RadioState-Int, 1 = On). Best effort; ohne Pakete/Zugriff ein No-op.
        """
        if not _WINRT_OK or not baseline:
            return
        if not self._request_access():
            return
        with self._op_lock:
            try:
                managed = self._managed()
            except Exception:
                return
            for rd in managed:
                try:
                    want = baseline.get(rd.name)
                except Exception:
                    want = None
                if want is None:
                    continue
                target = _radios.RadioState.ON if want == _STATE_ON else _radios.RadioState.OFF
                try:
                    if int(rd.state) != want:
                        rd.set_state_async(target).get()
                except Exception:
                    pass

    # -- Externe Aenderungen spiegeln ------------------------------------
    def set_change_callback(self, cb: Callable[[bool], None] | None) -> None:
        self._on_change = cb

    def subscribe(self) -> None:
        """``StateChanged`` je verwaltetem Radio registrieren (idempotent).

        Meldet externe Funk-Aenderungen (Nutzer schaltet in den
        Windows-Einstellungen) sofort ueber den Callback.
        """
        if not _WINRT_OK or self._subscribed:
            return
        if not self._request_access():
            return
        try:
            managed = self._managed()
        except Exception:
            return
        for rd in managed:
            try:
                token = rd.add_state_changed(self._on_state_changed)
                self._handlers.append((rd, token))
            except Exception:
                pass
        # Ausgangswert merken, damit der erste echte Wechsel als solcher zaehlt.
        self._last_online = any(int(rd.state) == _STATE_ON for rd, _ in self._handlers) \
            if self._handlers else self._last_online
        self._subscribed = True

    def _on_state_changed(self, sender: Any, args: Any) -> None:
        """WinRT-Ereignis-Thread: neuen aggregierten Zustand melden, wenn er sich aendert.

        Liest bewusst nur die (nicht blockierende) ``.state``-Property der schon
        abonnierten Radios, kein ``.get()`` im Callback-Thread.
        """
        try:
            any_on = False
            for rd, _token in self._handlers:
                try:
                    if int(rd.state) == _STATE_ON:
                        any_on = True
                except Exception:
                    pass
            online = any_on
        except Exception:
            return
        if online == self._last_online:
            return
        self._last_online = online
        cb = self._on_change
        if cb is not None:
            try:
                cb(online)
            except Exception:
                pass


_controller: RadioController | None = None


def get_controller() -> RadioController:
    """Prozess-Singleton des Radio-Controllers."""
    global _controller
    if _controller is None:
        _controller = RadioController()
    return _controller
