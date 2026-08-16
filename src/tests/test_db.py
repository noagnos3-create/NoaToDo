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

"""Datenbank-Kern (Bauplan Phase 9, Punkt 1: ``db.py``).

Geprueft werden die Zusagen, die anderswo vorausgesetzt werden: CRUD, die
Positions-Invariante pro Abschnitt (B.1/U13), die Spalten-Whitelist von
``edit_task`` und der **leere Erststart** (N11.1.4: keine Demo-Daten).
"""
from __future__ import annotations

import os

import pytest

from backend import db as db_module

KEY = bytes(range(32))


@pytest.fixture
def db(tmp_path):
    d = db_module.Database(str(tmp_path / "work.db"), KEY)
    yield d
    d.close()


def test_erststart_bleibt_leer(db):
    """N11.1.4: ``seed_if_empty`` schreibt nur Settings plus Marker."""
    db.seed_if_empty()
    assert db.get_lists_with_tasks() == []
    assert db.get_setting("seeded") == "true"
    # Die Default-Settings stehen (Stichprobe aus B.6).
    assert db.get_setting("theme") == "auto"
    assert db.get_setting("sidebarWidth") == "300"     # N11.19
    # Ein zweiter Aufruf aendert nichts.
    db.add_list("Nur diese eine")
    db.seed_if_empty()
    assert len(db.get_lists_with_tasks()) == 1


def test_crud_und_abschnitts_positionen(db):
    lst = db.add_list("Test")
    a = db.add_task(lst["id"], "A")
    b = db.add_task(lst["id"], "B")
    c = db.add_task(lst["id"], "C")
    assert [t["position"] for t in (a, b, c)] == [0, 1, 2]

    # Abhaken haengt ans ENDE von done, Wiedereroeffnen ans Ende von open (U13).
    db.toggle_task(a["id"])
    db.toggle_task(b["id"])
    lists = db.get_lists_with_tasks()
    done = lists[0]["done"]
    assert [t["text"] for t in done] == ["A", "B"]
    assert [t["position"] for t in done] == [0, 1]
    db.toggle_task(a["id"])
    lists = db.get_lists_with_tasks()
    assert [t["text"] for t in lists[0]["open"]] == ["C", "A"]

    db.edit_task(c["id"], {"text": "C2"})
    assert db.get_task(c["id"])["text"] == "C2"
    db.delete_task(c["id"])
    assert db.get_task(c["id"]) is None


def test_edit_task_spalten_whitelist(db):
    """Nur ``text`` und ``done`` sind schreibbar; alles andere wird ignoriert."""
    lst = db.add_list("L")
    t = db.add_task(lst["id"], "A")
    before = db.get_task(t["id"])
    # Ein erfundener Spaltenname darf weder schreiben noch die Query brechen.
    db.edit_task(t["id"], {"list_id": "l-fremd", "position": 99, "text": "neu"})
    after = db.get_task(t["id"])
    assert after["text"] == "neu"
    assert after["position"] == before["position"]
    assert db.get_lists_with_tasks()[0]["open"][0]["id"] == t["id"]


def test_reorder_verlangt_die_exakte_menge(db):
    """N11.2.2: fehlende, fremde oder doppelte IDs -> nichts wird geschrieben."""
    lst = db.add_list("L")
    ids = [db.add_task(lst["id"], x)["id"] for x in ("A", "B", "C")]
    with pytest.raises(db_module.InvalidInput):
        db.reorder(lst["id"], ids[:2])                    # unvollstaendig
    with pytest.raises(db_module.InvalidInput):
        db.reorder(lst["id"], ids + [ids[0]])             # doppelt
    with pytest.raises(db_module.InvalidInput):
        db.reorder(lst["id"], ids[:2] + ["t-fremd"])      # fremd
    # Nichts davon hat etwas veraendert.
    assert [t["id"] for t in db.get_lists_with_tasks()[0]["open"]] == ids
    db.reorder(lst["id"], list(reversed(ids)))
    assert [t["id"] for t in db.get_lists_with_tasks()[0]["open"]] == list(reversed(ids))


def test_move_task_behaelt_done_und_haengt_hinten_an(db):
    """U11/N11.2.2: ``done`` bleibt, Ziel-Abschnitt bekommt die hoechste Position."""
    src = db.add_list("Quelle")
    dst = db.add_list("Ziel")
    keep = db.add_task(dst["id"], "schon da")
    db.toggle_task(keep["id"])
    moved = db.add_task(src["id"], "wandert")
    db.toggle_task(moved["id"])
    db.move_task(moved["id"], dst["id"])
    lists = {x["name"]: x for x in db.get_lists_with_tasks()}
    assert lists["Quelle"]["done"] == []
    assert [t["text"] for t in lists["Ziel"]["done"]] == ["schon da", "wandert"]


def test_parametrisierte_queries_kein_sql_injection(db):
    """Ein Listenname mit SQL-Syntax ist Text, kein Befehl."""
    boese = "'; DROP TABLE tasks; --"
    lst = db.add_list(boese)
    t = db.add_task(lst["id"], boese)
    assert db.get_task(t["id"])["text"] == boese
    assert db.get_lists_with_tasks()[0]["name"] == boese


def test_settings_migration_entfernt_alte_schluessel(tmp_path):
    """N11.23: ``dark``/``toolbar`` fliegen raus, ``theme = auto`` kommt einmalig."""
    path = str(tmp_path / "alt.db")
    d = db_module.Database(path, KEY)
    d.conn.execute("DELETE FROM settings WHERE key = 'theme'")
    d.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('dark', 'true')")
    d.conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('toolbar', 'x')")
    d.conn.commit()
    d.close()

    d2 = db_module.Database(path, KEY)
    try:
        assert d2.get_setting("theme") == "auto"     # nicht "dark", bewusst
        assert d2.get_setting("dark") is None
        assert d2.get_setting("toolbar") is None
    finally:
        d2.close()


def test_datei_ist_ohne_schluessel_nicht_zu_oeffnen(tmp_path):
    """G7/G28-Vorstufe: die Arbeitsdatei ist echter SQLCipher-Chiffretext."""
    path = str(tmp_path / "enc.db")
    d = db_module.Database(path, KEY)
    d.add_list("Geheime Liste")
    d.close()
    with open(path, "rb") as fh:
        head = fh.read(16)
    assert head[:15] != b"SQLite format 3"
    assert os.path.getsize(path) > 0
