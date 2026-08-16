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

"""Unverschluesselte Startkonfiguration ``config.json`` (Bauplan B.11 / N11.15).

Enthaelt NUR nicht-geheime Startinfos: den Tresor-Pfad, den Funk-Merker
(``radio_baseline``, N11.10) und den persistierten Rate-Limit-Zustand
(``unlock_ratelimit``, N11.4.1). Niemals Aufgaben-/Listentexte, Passphrase,
Schluessel, Pepper, Salt oder Argon2-Parameter (die liegen im G16-Header bzw.
im Credential Manager).

Regeln aus B.11:
- Ort ``%LOCALAPPDATA%\\NoaToDo\\config.json``, aufgeloest NUR ueber
  :func:`config_path` (Store-Python-Redirect V8: im Prozess transparent).
- Schreiben immer atomar (``.tmp`` + ``flush`` + ``fsync`` + ``os.replace``),
  einziger Schreiber ist die eine Instanz (G19).
- Fehlt die Datei komplett: Erststart/Onboarding (kein Fehler).
- Existiert sie, ist aber unbrauchbar (kein JSON, ``version`` unbekannt/zu neu,
  Pflichtfeld fehlt/falscher Typ): KEIN stiller Erststart. Die Datei wird nach
  ``config.json.bad`` umbenannt (genau eine Generation) und der Boot endet im
  N6-Fehlerbildschirm (``config_damaged``).
"""
from __future__ import annotations

import json
import os
from typing import Any

CONFIG_VERSION = 1


class ConfigDamaged(Exception):
    """config.json existiert, ist aber unbrauchbar (N11.15.2).

    Die Datei wurde bereits nach ``config.json.bad`` umbenannt; der Aufrufer
    zeigt den N6-Fehlerbildschirm ("Konfiguration unlesbar") mit den zwei
    Auswegen "Tresor suchen" und "Neuen Tresor anlegen".
    """


def _default_ratelimit() -> dict[str, Any]:
    return {"fails": 0, "stage": 0, "next_try_at": None, "locked_at": None, "duration": 0}


def config_path() -> str:
    """Der EINE Aufloesungspunkt fuer den Konfig-Pfad (N11.15.1, nie hartkodieren)."""
    local = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local"
    )
    return os.path.join(local, "NoaToDo", "config.json")


def _valid(cfg: Any) -> bool:
    """Pflichtfelder und Typen des Schemas v1 (N11.15.1)."""
    if not isinstance(cfg, dict):
        return False
    if not isinstance(cfg.get("version"), int):
        return False
    if cfg["version"] > CONFIG_VERSION:
        # Eine neuere App hat geschrieben: nicht anfassen, nicht raten.
        return False
    if not isinstance(cfg.get("vault_path"), str) or not cfg["vault_path"]:
        return False
    rl = cfg.get("unlock_ratelimit")
    if not isinstance(rl, dict) or not isinstance(rl.get("fails"), int):
        return False
    rb = cfg.get("radio_baseline")
    if rb is not None and not isinstance(rb, dict):
        return False
    return True


def load_config() -> dict[str, Any] | None:
    """Konfig laden.

    Rueckgabe:
    - ``None``: Datei fehlt komplett -> Erststart/Onboarding (Normalfall).
    - dict: gueltige Konfig.
    - wirft :class:`ConfigDamaged`: Datei vorhanden, aber unbrauchbar; sie
      wurde nach ``config.json.bad`` umbenannt (genau eine Generation).
    """
    path = config_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        cfg = None
    if cfg is not None and _valid(cfg):
        return cfg
    # Unbrauchbar: nach .bad wegdrehen (nicht ueberschreiben, N11.15.2).
    try:
        bad = path + ".bad"
        if os.path.exists(bad):
            os.remove(bad)
        os.replace(path, bad)
    except OSError:
        pass
    raise ConfigDamaged()


def save_config(cfg: dict[str, Any]) -> None:
    """Konfig atomar und vollstaendig schreiben (N11.15.1, wie G16)."""
    cfg = dict(cfg)
    cfg["version"] = CONFIG_VERSION
    cfg.setdefault("radio_baseline", None)
    cfg.setdefault("unlock_ratelimit", _default_ratelimit())
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def new_config(vault_path: str) -> dict[str, Any]:
    """Frische Konfig (Onboarding, "Tresor suchen", nach Reset)."""
    return {
        "version": CONFIG_VERSION,
        "vault_path": vault_path,
        "radio_baseline": None,
        "unlock_ratelimit": _default_ratelimit(),
    }


def delete_config() -> None:
    """Konfig entfernen (Killswitch/Reset raeumen den Vault-Eintrag weg, U21)."""
    try:
        os.remove(config_path())
    except OSError:
        pass
