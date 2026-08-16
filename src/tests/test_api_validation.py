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

"""Bridge-Validierung und Export-Haertung (Bauplan Phase 9, Punkt 1).

Deckt Gate **G20** (Laengenlimits, Steuerzeichen-Strip, Mengenpruefung bei
``reorder``, Settings-Whitelist samt Wertpruefung V5) und den
Dateinamen-Teil von Gate **G21** (verbotene Windows-Zeichen, ``..``, reservierte
Geraetenamen, Laengenkappung) ab.
"""
from __future__ import annotations

import pytest

from backend import api as api_module
from backend import db as db_module
from backend import security as security_module

KEY = bytes(range(32))


@pytest.fixture
def api(tmp_path):
    """Eine entsperrte Api mit einer Wegwerf-DB, ohne echten Tresor.

    Der Krypto-Teil hat eigene Tests; hier geht es allein um die
    Eingabepruefung an der Bridge.
    """
    session = security_module.Session()
    a = api_module.Api(session)
    a.locked = False
    database = db_module.Database(str(tmp_path / "work.db"), KEY)
    database.seed_if_empty()
    session.vault = type("FakeVault", (), {"db": database, "enc_path": None})()
    yield a
    database.close()


def test_text_wird_gekappt_und_steuerzeichen_entfernt(api):
    lst = api.add_list("L")
    task = api.add_task(lst["id"], "A" * 5000)
    assert len(task["text"]) == 4096                     # G20: 4096 Zeichen
    task2 = api.add_task(lst["id"], "vor\x07nach\tund\nmehr")
    assert "\x07" not in task2["text"]                   # Steuerzeichen raus
    assert "\t" in task2["text"] and "\n" in task2["text"]  # Tab/Newline bleiben
    name = api.add_list("N" * 500)
    assert len(name["name"]) == 256                      # G20: 256 Zeichen


def test_leerer_text_ist_invalid(api):
    lst = api.add_list("L")
    assert api.add_task(lst["id"], "   ")["error"] == "invalid"
    assert api.add_list("")["error"] == "invalid"


def test_unbekannte_id_ist_not_found(api):
    assert api.toggle_task("t-gibtsnicht")["error"] == "not_found"
    assert api.edit_task("t-gibtsnicht", {"text": "x"})["error"] == "not_found"
    assert api.delete_list("l-gibtsnicht")["error"] == "not_found"


def test_settings_whitelist_und_wertpruefung(api):
    assert api.set_setting("accent", api_module.ACCENT_PRESETS[0]) == {"ok": True}
    # V5: Wert je Schluessel geprueft, nicht nur der Schluessel. Die Akzentfarbe
    # landet als CSS-Variable im DOM, die feste Preset-Liste toetet damit die
    # CSS-Injection ueber die Einstellungen.
    assert api.set_setting("accent", "red; background:url(x)")["error"] == "invalid"
    assert api.set_setting("accent", "#000000")["error"] == "invalid"
    assert api.set_setting("theme", "auto") == {"ok": True}
    assert api.set_setting("theme", "neon")["error"] == "invalid"
    assert api.set_setting("autoLock", 15) == {"ok": True}
    assert api.set_setting("autoLock", 7)["error"] == "invalid"
    # N11.23: die beiden Alt-Schluessel sind aus der Whitelist raus.
    assert api.set_setting("dark", True)["error"] == "invalid"
    assert api.set_setting("toolbar", "floating")["error"] == "invalid"
    # Ein voellig fremder Schluessel ebenso.
    assert api.set_setting("__proto__", "x")["error"] == "invalid"
    # sidebarWidth wird beim Schreiben geklemmt (180 bis 520).
    api.set_setting("sidebarWidth", 9999)
    assert int(api.get_state()["settings"]["sidebarWidth"]) <= 520


def test_edit_task_prueft_felder(api):
    lst = api.add_list("L")
    t = api.add_task(lst["id"], "A")
    assert api.edit_task(t["id"], {"text": "B"})["text"] == "B"
    assert api.edit_task(t["id"], {"done": "ja"})["error"] == "invalid"
    assert api.edit_task(t["id"], {"unbekannt": 1})["error"] == "invalid"


def test_reorder_lists_verlangt_die_volle_menge(api):
    a = api.add_list("A")
    b = api.add_list("B")
    assert api.reorder_lists([a["id"]])["error"] == "invalid"
    assert api.reorder_lists([a["id"], b["id"], a["id"]])["error"] == "invalid"
    assert api.reorder_lists([b["id"], a["id"]]) == {"ok": True}


def test_move_task_randfaelle(api):
    src = api.add_list("A")
    dst = api.add_list("B")
    t = api.add_task(src["id"], "x")
    assert api.move_task(t["id"], src["id"])["error"] == "invalid"      # Ziel = Quelle
    assert api.move_task(t["id"], "l-fremd")["error"] == "not_found"
    assert api.move_task(t["id"], dst["id"])["list_id"] == dst["id"]


def test_jede_bridge_methode_hat_ein_schema_oder_keine_argumente():
    """G20 will die Regeln introspektierbar (Phase-9-Testbarkeit).

    Jede oeffentliche Bridge-Methode mit Argumenten traegt ein ``_schema``.
    Zwei bewusste Ausnahmen, und genau die werden hier festgenagelt, damit sie
    nicht unbemerkt mehr werden: ``set_setting`` prueft ueber
    ``SETTINGS_SCHEMA`` je Schluessel (ein pauschales Argument-Schema ginge
    daran vorbei), und ``unlock`` bekommt die Passphrase absichtlich
    unveraendert (ein Kappen oder Strippen wuerde eine gueltige Passphrase
    still verfaelschen und den Tresor unbrauchbar machen).
    """
    import inspect

    erlaubt = {"set_setting", "unlock"}
    ohne_schema = set()
    for name, fn in inspect.getmembers(api_module.Api, inspect.isfunction):
        if name.startswith("_"):
            continue
        params = [p for p in inspect.signature(fn).parameters if p != "self"]
        if params and not getattr(fn, "_schema", None):
            ohne_schema.add(name)
    assert ohne_schema == erlaubt


# ---------------------------------------------------------------------------
# G21: Dateinamen-Haertung des Exports
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("roh, verboten", [
    ('Liste: A/B\\C|D?E*F"G<H>I', ':/\\|?*"<>'),
    ("../../etc/passwd", "/"),
    ("..", "."),
])
def test_exportname_entfernt_verbotene_zeichen(roh, verboten):
    name = api_module._sanitize_export_name(roh)
    for ch in verboten:
        assert ch not in name
    assert ".." not in name
    assert name.strip() != ""


def test_exportname_kappt_und_meidet_geraetenamen():
    assert len(api_module._sanitize_export_name("X" * 400)) <= 120
    for reserviert in ("CON", "con", "PRN", "AUX", "NUL", "COM1", "LPT1"):
        name = api_module._sanitize_export_name(reserviert)
        assert name.upper() not in ("CON", "PRN", "AUX", "NUL", "COM1", "LPT1")
