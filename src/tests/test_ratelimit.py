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

"""Entsperr-Rate-Limit-Leiter samt Persistenz (B.8.4 / N11.4.1, Befund U6).

Geprueft wird, was die Leiter ueberhaupt erst wirksam macht: die Stufen selbst,
dass der Zustand einen **Prozess-Neustart ueberlebt** (sonst setzte der
Off-Knopf des Sperrfensters sie in zwei Klicks zurueck), dass ein Kill mitten
im Versuch den Zaehler **nicht** senkt (persist-before-verify), dass nur der
Erfolg aufraeumt und dass eine zurueckgedrehte Uhr nichts verkuerzt.
"""
from __future__ import annotations

import json
import os

from backend import config as config_module
from backend import security as security_module


def _neuer_limiter():
    """Ein Limiter, der wie in der App auf config.json arbeitet.

    Bewusst ueber echte Dateizugriffe (in den Temp-LOCALAPPDATA der Fixture):
    genau die Persistenz ist der Punkt dieses Tests. Der Zwischenspeicher
    entspricht ``Api._load_config``/``_save_config``: die Konfig wird einmal
    gelesen und danach als **ein** Dict weitergereicht (der Limiter aendert
    genau dieses Dict und laesst es speichern). Ein frischer Limiter steht
    fuer einen neu gestarteten Prozess.
    """
    zwischenspeicher = {}

    def load():
        if "cfg" not in zwischenspeicher:
            try:
                cfg = config_module.load_config()
            except config_module.ConfigDamaged:
                cfg = None
            zwischenspeicher["cfg"] = cfg or config_module.new_config(
                "C:/tresor/tasks.db.enc")
        return zwischenspeicher["cfg"]

    def save(cfg):
        zwischenspeicher["cfg"] = cfg
        config_module.save_config(cfg)

    return security_module.RateLimiter(load, save)


def test_stufenfunktion_ist_die_vereinbarte_leiter():
    """B.8.4: 3 Freiversuche, dann 10 s, 30 s, 1 min, ... je 2 Versuche."""
    assert security_module.ladder_stage(0) == (0, 0)
    assert security_module.ladder_stage(3) == (0, 0)          # noch frei
    assert security_module.ladder_stage(4)[1] == 10
    assert security_module.ladder_stage(5)[1] == 10           # 2 Versuche je Stufe
    assert security_module.ladder_stage(6)[1] == 30
    assert security_module.ladder_stage(8)[1] == 60
    # Deckel: die Leiter waechst nicht ins Unendliche.
    weit = security_module.ladder_stage(1000)
    assert weit[1] == security_module.LADDER_DURATIONS[-1]
    # Monoton steigend, keine Delle.
    dauern = [security_module.ladder_stage(f)[1] for f in range(1, 30)]
    assert dauern == sorted(dauern)


def test_freiversuche_dann_sperre_und_persistenz():
    rl = _neuer_limiter()
    for _ in range(3):
        wartezeit = rl.register_fail()
        assert wartezeit == security_module.RETRY_PAUSE_SECONDS   # nur die 2 s
    assert rl.register_fail() == 10                              # 4. Versuch: Stufe 1

    # Der Zustand liegt wirklich in config.json (unverschluesselt, B.11).
    with open(config_module.config_path(), "r", encoding="utf-8") as fh:
        gespeichert = json.load(fh)["unlock_ratelimit"]
    assert gespeichert["fails"] == 4
    assert gespeichert["stage"] == 1
    assert gespeichert["duration"] == 10
    assert gespeichert["next_try_at"]

    # "Prozessneustart": frischer Limiter, gleiche Datei. Die Sperre gilt weiter.
    nach_neustart = _neuer_limiter()
    assert nach_neustart.remaining() > 0


def test_kill_mitten_im_versuch_senkt_den_zaehler_nicht():
    """Persist-before-verify: gezaehlt wird VOR der Pruefung, nicht danach."""
    rl = _neuer_limiter()
    rl.register_fail()
    rl.register_fail()
    # Kein reset(), kein sauberes Ende: einfach ein neuer Prozess.
    with open(config_module.config_path(), "r", encoding="utf-8") as fh:
        assert json.load(fh)["unlock_ratelimit"]["fails"] == 2
    assert _neuer_limiter()._rl()["fails"] == 2


def test_nur_der_erfolg_raeumt_auf():
    rl = _neuer_limiter()
    for _ in range(4):
        rl.register_fail()
    rl.reset()
    assert rl.remaining() == 0
    with open(config_module.config_path(), "r", encoding="utf-8") as fh:
        gespeichert = json.load(fh)["unlock_ratelimit"]
    assert gespeichert["fails"] == 0 and gespeichert["stage"] == 0


def test_kein_rateversuch_nimmt_den_zaehler_zurueck():
    """N6: ``memory``/``vault`` treiben die Leiter nicht voran."""
    rl = _neuer_limiter()
    rl.register_fail()
    rl.register_fail()
    rl.undo_last_fail()
    assert rl._rl()["fails"] == 1


def test_zurueckgedrehte_uhr_verkuerzt_nichts():
    """N11.4.1: bei widerspruechlichen Zeiten startet die Sperre komplett neu."""
    rl = _neuer_limiter()
    for _ in range(4):
        rl.register_fail()      # Stufe 1, 10 s
    cfg = config_module.load_config()
    # Angreifer dreht die Uhr zurueck: locked_at liegt "in der Zukunft".
    cfg["unlock_ratelimit"]["locked_at"] = "2999-01-01T00:00:00+00:00"
    cfg["unlock_ratelimit"]["next_try_at"] = "2999-01-01T00:00:10+00:00"
    config_module.save_config(cfg)
    nach_neustart = _neuer_limiter()
    rest = nach_neustart.remaining()
    assert rest > 0, "eine zurueckgedrehte Uhr darf die Sperre nie aufheben"


def test_config_json_enthaelt_keine_geheimnisse():
    """B.11: die unverschluesselte Konfig traegt nur Startinfos."""
    rl = _neuer_limiter()
    rl.register_fail()
    with open(config_module.config_path(), "r", encoding="utf-8") as fh:
        roh = fh.read()
    assert set(json.loads(roh)) <= {
        "version", "vault_path", "radio_baseline", "unlock_ratelimit"}
    for verboten in ("passphrase", "pepper", "salt", "key", "argon"):
        assert verboten not in roh.lower()
    assert os.path.basename(config_module.config_path()) == "config.json"
