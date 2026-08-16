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

"""Datenschicht für NoaToDo (Bauplan Phase 1, Schicht-1-Schluessel seit Phase 8 echt).

Schicht 1 der Verschlüsselung (SQLCipher / AES-256) sitzt direkt hier: sofort
nach dem Öffnen wird der aus der Passphrase abgeleitete Schlüssel als **roher
Hex-Schlüssel** gesetzt (Gate G7: ``PRAGMA key = "x'<64 Hex>'"``, kein zweites
PBKDF2 über den schon teuer abgeleiteten Key, kein Quote-Escaping). Der frühere
öffentliche ``DEV_AES_KEY`` ist mit Phase 8 **ersatzlos entfernt** (Gate G9): es
gibt keinen Code-Pfad mehr, der die DB ohne den abgeleiteten Schlüssel öffnet.
Die äußere ChaCha20-Schicht, die Argon2-Ableitung und der Tresor-Lebenszyklus
liegen in ``backend/security.py``; diese Datei bekommt nur den fertigen 32-Byte-
Schlüssel als ``bytes``.

Die Klasse :class:`Database` kapselt eine SQLCipher-Verbindung und liefert genau
die Strukturen, die das Frontend erwartet (siehe Bauplan B.1/B.2).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

import sqlcipher3

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _now() -> str:
    """Aktueller Zeitpunkt als ISO-8601-UTC-String (alle ``*_at``-Felder)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    """Lokale ID erzeugen: ``'l'`` für Listen, ``'t'`` für Aufgaben."""
    return prefix + uuid.uuid4().hex


class InvalidInput(ValueError):
    """Semantische G20-Verletzung in der Datenschicht (z.B. `ordered_ids`
    ist nicht exakt die Aufgabenmenge der Liste, N11.2.2). Der
    ``@bridge``-Decorator macht daraus den Katalog-Code ``invalid``."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS lists (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL,
  position    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
  id          TEXT PRIMARY KEY,
  list_id     TEXT NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  done        INTEGER NOT NULL DEFAULT 0,
  position    INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_list ON tasks(list_id);
"""


class Database:
    """Eine geöffnete (entschlüsselte) NoaToDo-Datenbank."""

    def __init__(self, path: str, aes_key: bytes):
        self.path = path
        if not isinstance(aes_key, (bytes, bytearray)) or len(aes_key) != 32:
            # Gate G9: es gibt keinen Fallback-Schluessel und keinen String-Key
            # mehr. Ohne einen echten 32-Byte-Schluessel wird nichts geoeffnet.
            raise ValueError("aes_key must be 32 raw bytes")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlcipher3.connect(path, check_same_thread=False)
        # Schicht 1: Schlüssel SOFORT nach dem Öffnen als ROHER Hex-Schlüssel
        # setzen (Gate G7): "x'<64 Hex-Zeichen>'". So legt SQLCipher kein
        # eigenes PBKDF2 über den schon per Argon2id abgeleiteten Key, und es
        # gibt kein Quote-Escaping. PRAGMA erlaubt keine Parameter-Bindung; der
        # Hex-String stammt ausschliesslich aus os-Zufall/Argon2, nie aus
        # Nutzereingaben.
        self.conn.execute("PRAGMA key = \"x'%s'\"" % bytes(aes_key).hex())
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlcipher3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._drop_legacy_columns()
        self._migrate_settings()

    def rekey(self, new_key: bytes) -> None:
        """Schicht-1-Schluessel wechseln (Passphrase-Wechsel, N11.3).

        ``PRAGMA rekey`` verschluesselt alle Seiten mit dem neuen Schluessel
        neu, ohne die Verbindung zu schliessen. Danach ist die Arbeitsdatei
        nur noch mit ``new_key`` zu oeffnen.
        """
        if not isinstance(new_key, (bytes, bytearray)) or len(new_key) != 32:
            raise ValueError("new_key must be 32 raw bytes")
        self.conn.execute("PRAGMA rekey = \"x'%s'\"" % bytes(new_key).hex())
        self.conn.commit()

    def _drop_legacy_columns(self) -> None:
        """Einmal-Migration: Altspalten fliegen aus Bestands-DBs.

        ``meta`` (eine Aufgabe ist nur noch ``text`` + ``done``, N11.1.3) sowie
        die Reste der 2026-07-09 entfernten Sync-Integration und der gestrichenen
        Faelligkeiten (``synced``/``source``/``graph_etag``/``due_at``, N11.1.6).
        Neue DBs entstehen ohne diese Spalten (SCHEMA oben); hier werden sie aus
        aelteren Entwicklungs-DBs entfernt, damit kein verwaister Freitext liegen
        bleibt. Scheitert ein ALTER (sehr alte SQLite-Engine ohne DROP COLUMN),
        bleibt die Spalte ungenutzt stehen; kein harter Fehler.
        """
        legacy = ("meta", "synced", "source", "graph_etag", "due_at")
        try:
            cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(tasks)")}
            for col in legacy:
                if col in cols:
                    self.conn.execute(f"ALTER TABLE tasks DROP COLUMN {col}")
            self.conn.commit()
        except Exception:
            pass

    def _migrate_settings(self) -> None:
        """Einmal-Migration der Settings-Keys auf den Stand von B.6 (N11.6/N11.7).

        ``dark`` (Bool) ist durch ``theme`` (``auto``|``light``|``dark``)
        ersetzt, ``toolbar`` ist ersatzlos entfallen (die Rail ist immer
        ``floating``). Bestands-Tresore bekommen genau einmal ``theme = auto``
        gesetzt, danach gilt allein der vom Nutzer gewaehlte Wert.

        Der alte ``dark``-Wert wird bewusst NICHT auf ein festes Theme
        abgebildet: der Default von N11.6 ist ``auto``, und ein aus ``dark=true``
        abgeleitetes festes Dunkel wuerde genau das Feature aushebeln, das die
        Migration einfuehrt (der Nutzer kaeme nie in den Automatik-Zustand,
        ohne ihn von Hand zu waehlen). Die Wahl bleibt ueber das
        Appearance-Segment jederzeit erreichbar.
        """
        try:
            rows = {r["key"] for r in self.conn.execute("SELECT key FROM settings")}
            if "theme" not in rows:
                self.conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('theme', 'auto')")
            for dead in ("dark", "toolbar"):
                if dead in rows:
                    self.conn.execute("DELETE FROM settings WHERE key = ?", (dead,))
            self.conn.commit()
        except Exception:
            pass

    # -- Lebenszyklus ------------------------------------------------------
    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    # -- Serialisierung ----------------------------------------------------
    @staticmethod
    def _task_dict(row: sqlcipher3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "list_id": row["list_id"],
            "text": row["text"],
            "done": bool(row["done"]),
            "position": row["position"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    # -- Listen lesen ------------------------------------------------------
    def get_lists_with_tasks(self) -> list[dict[str, Any]]:
        """Alle Listen mit eingebetteten ``open``/``done``-Aufgaben (B.1)."""
        lists = self.conn.execute(
            "SELECT * FROM lists ORDER BY position, created_at"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for lrow in lists:
            tasks = self.conn.execute(
                "SELECT * FROM tasks WHERE list_id = ? ORDER BY position, created_at",
                (lrow["id"],),
            ).fetchall()
            open_tasks = [self._task_dict(t) for t in tasks if not t["done"]]
            done_tasks = [self._task_dict(t) for t in tasks if t["done"]]
            result.append(
                {
                    "id": lrow["id"],
                    "name": lrow["name"],
                    "open": open_tasks,
                    "done": done_tasks,
                }
            )
        return result

    def _get_list(self, list_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM lists WHERE id = ?", (list_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "position": row["position"],
        }

    # -- Listen schreiben --------------------------------------------------
    def add_list(self, name: str) -> dict[str, Any]:
        now = _now()
        lid = _new_id("l")
        pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM lists"
        ).fetchone()["p"]
        self.conn.execute(
            "INSERT INTO lists (id, name, position, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (lid, name, pos, now, now),
        )
        self.conn.commit()
        return {"id": lid, "name": name, "open": [], "done": []}

    def rename_list(self, list_id: str, name: str) -> dict[str, Any]:
        self.conn.execute(
            "UPDATE lists SET name = ?, updated_at = ? WHERE id = ?",
            (name, _now(), list_id),
        )
        self.conn.commit()
        return {"ok": True}

    def delete_list(self, list_id: str) -> dict[str, Any]:
        # Aufgaben verschwinden via ON DELETE CASCADE.
        self.conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
        self.conn.commit()
        return {"ok": True}

    # -- Undo beim Listen-Loeschen (N11.2.1) --------------------------------
    def get_list_snapshot(self, list_id: str) -> dict[str, Any]:
        """Vollabzug einer Liste samt Aufgaben fuer den RAM-Undo-Puffer.

        Reiner Lesezugriff; das eigentliche Loeschen macht ``delete_list``.
        Der Abzug enthaelt alle Spalten (inkl. ``position`` und Zeitstempeln),
        damit ``restore_list`` die Liste bit-genau und an alter Stelle
        wiederherstellen kann. Kein Soft-Delete, kein ``deleted_at``-Feld:
        der Puffer lebt nur im RAM der entsperrten Sitzung (U9-Entscheid).
        """
        lrow = self.conn.execute(
            "SELECT * FROM lists WHERE id = ?", (list_id,)
        ).fetchone()
        if lrow is None:
            raise KeyError(list_id)
        trows = self.conn.execute(
            "SELECT * FROM tasks WHERE list_id = ?", (list_id,)
        ).fetchall()
        return {
            "list": {k: lrow[k] for k in lrow.keys()},
            "tasks": [{k: r[k] for k in r.keys()} for r in trows],
        }

    def restore_list(self, snap: dict[str, Any]) -> dict[str, Any]:
        """Gepufferte Liste an ihrer alten Position wieder einfuegen (N11.2.1).

        Nachfolgende Listen ruecken eine Position zurueck, die Aufgaben kommen
        mit ihren alten Positionen und IDs zurueck. Existiert die ID wider
        Erwarten schon (Puffer-Logik verletzt), schlaegt der INSERT fehl und
        der ``@bridge``-Decorator liefert ``internal``; es entsteht nie eine
        zweite Kopie.
        """
        lst = snap["list"]
        self.conn.execute(
            "UPDATE lists SET position = position + 1 WHERE position >= ?",
            (lst["position"],),
        )
        self.conn.execute(
            "INSERT INTO lists (id, name, position, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (lst["id"], lst["name"], lst["position"], lst["created_at"], lst["updated_at"]),
        )
        for t in snap["tasks"]:
            self.conn.execute(
                "INSERT INTO tasks (id, list_id, text, done, position,"
                " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (t["id"], t["list_id"], t["text"], t["done"], t["position"],
                 t["created_at"], t["updated_at"]),
            )
        self.conn.commit()
        return {"ok": True}

    # -- Aufgaben schreiben ------------------------------------------------
    def add_task(self, list_id: str, text: str) -> dict[str, Any]:
        now = _now()
        tid = _new_id("t")
        # Positions-Invariante (B.1, U13): position wird JE SEKTION gefuehrt;
        # eine neue Aufgabe haengt ans Ende von open (MAX+1 nur unter done=0).
        pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM tasks"
            " WHERE list_id = ? AND done = 0",
            (list_id,),
        ).fetchone()["p"]
        self.conn.execute(
            "INSERT INTO tasks (id, list_id, text, done, position,"
            " created_at, updated_at)"
            " VALUES (?, ?, ?, 0, ?, ?, ?)",
            (tid, list_id, text, pos, now, now),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
        return self._task_dict(row)

    def toggle_task(self, task_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT list_id, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise KeyError(task_id)
        new_done = 0 if row["done"] else 1
        # Positions-Invariante (B.1, U13): die Aufgabe wechselt die Sektion und
        # haengt ans ENDE der Zielsektion (Abhaken -> Ende von done,
        # Wieder-Oeffnen -> Ende von open); ihre alte position gehoert zur
        # alten Sektion und waere in der neuen bedeutungslos.
        pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM tasks"
            " WHERE list_id = ? AND done = ?",
            (row["list_id"], new_done),
        ).fetchone()["p"]
        self.conn.execute(
            "UPDATE tasks SET done = ?, position = ?, updated_at = ? WHERE id = ?",
            (new_done, pos, _now(), task_id),
        )
        self.conn.commit()
        return {"id": task_id, "done": bool(new_done)}

    def edit_task(self, task_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Erlaubte Felder: ``text``, ``done`` (kein ``meta`` mehr, N11.1.3)."""
        allowed = {"text", "done"}
        sets = []
        vals: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "done":
                value = 1 if value else 0
            sets.append(f"{key} = ?")
            vals.append(value)
        if sets:
            sets.append("updated_at = ?")
            vals.append(_now())
            vals.append(task_id)
            self.conn.execute(
                f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", vals
            )
            self.conn.commit()
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return self._task_dict(row)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._task_dict(row) if row is not None else None

    def delete_task(self, task_id: str) -> dict[str, Any]:
        self.conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.conn.commit()
        return {"ok": True}

    def reorder(self, list_id: str, ordered_ids: list[str]) -> dict[str, Any]:
        """Aufgaben-Reihenfolge speichern, alles oder nichts (G20/N11.2.2).

        ``ordered_ids`` muss als Menge EXAKT alle Aufgaben-IDs dieser Liste
        sein (offene und erledigte zusammen; keine fehlende, doppelte, fremde
        oder listenfremde ID), sonst ``InvalidInput`` und es wird nichts
        geschrieben. Bei gueltiger Eingabe wird ``position`` je Sektion (B.1,
        U13: ``open`` und ``done`` haben eigene 0..n-Sequenzen) in der
        uebergebenen Reihenfolge neu vergeben.
        """
        if self._get_list(list_id) is None:
            raise KeyError(list_id)
        rows = self.conn.execute(
            "SELECT id, done FROM tasks WHERE list_id = ?", (list_id,)
        ).fetchall()
        done_by_id = {r["id"]: r["done"] for r in rows}
        if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != set(done_by_id):
            raise InvalidInput("ordered_ids must match the list's task set")
        now = _now()
        counters = {0: 0, 1: 0}
        for tid in ordered_ids:
            section = done_by_id[tid]
            self.conn.execute(
                "UPDATE tasks SET position = ?, updated_at = ? WHERE id = ?",
                (counters[section], now, tid),
            )
            counters[section] += 1
        self.conn.commit()
        return {"ok": True}

    def _renumber_sections(self, list_id: str) -> None:
        """``position`` je Sektion 0..n-1 neu vergeben (B.1-Invariante, U13).

        Reine Konsistenz-Nacharbeit nach einem Verschieben: ``open`` und
        ``done`` behalten je eine eigene, lueckenlose 0..n-Sequenz. Bewusst
        ohne ``updated_at``-Anfassen der Nachbarn (nur die bewegte Aufgabe
        traegt einen neuen Zeitstempel).
        """
        for done in (0, 1):
            rows = self.conn.execute(
                "SELECT id FROM tasks WHERE list_id = ? AND done = ?"
                " ORDER BY position, created_at",
                (list_id, done),
            ).fetchall()
            for pos, r in enumerate(rows):
                self.conn.execute(
                    "UPDATE tasks SET position = ? WHERE id = ?", (pos, r["id"])
                )

    def move_task(self, task_id: str, target_list_id: str) -> dict[str, Any]:
        """Aufgabe in eine andere Liste verschieben (N7/N11.2.2, U11-Entscheid).

        Beide IDs werden geprueft: fehlende Aufgabe oder Zielliste ->
        ``KeyError`` (Katalog: ``not_found``), Ziel = aktuelle Liste ->
        ``InvalidInput`` (``invalid``). Die Aufgabe BEHAELT ihren
        ``done``-Status und haengt ans Ende ihrer Sektion in der Zielliste;
        danach werden Quell- und Zielliste je Sektion 0..n-1 durchnummeriert.
        """
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise KeyError(task_id)
        if self._get_list(target_list_id) is None:
            raise KeyError(target_list_id)
        if row["list_id"] == target_list_id:
            raise InvalidInput("target is the current list")
        source_list_id = row["list_id"]
        pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM tasks"
            " WHERE list_id = ? AND done = ?",
            (target_list_id, row["done"]),
        ).fetchone()["p"]
        self.conn.execute(
            "UPDATE tasks SET list_id = ?, position = ?, updated_at = ?"
            " WHERE id = ?",
            (target_list_id, pos, _now(), task_id),
        )
        self._renumber_sections(source_list_id)
        self._renumber_sections(target_list_id)
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return self._task_dict(row)

    def reorder_lists(self, ordered_ids: list[str]) -> dict[str, Any]:
        """Sidebar-Reihenfolge der Listen speichern (N7/N11.2.2, U11).

        Dieselbe Alles-oder-nichts-Regel wie ``reorder``: ``ordered_ids``
        muss als Menge EXAKT alle Listen-IDs sein (keine fehlende, doppelte
        oder fremde ID), sonst ``InvalidInput`` und es wird nichts
        geschrieben. Bei gueltiger Eingabe wird ``lists.position`` 0..n-1 in
        der uebergebenen Reihenfolge neu vergeben.
        """
        all_ids = {
            r["id"] for r in self.conn.execute("SELECT id FROM lists").fetchall()
        }
        if len(ordered_ids) != len(set(ordered_ids)) or set(ordered_ids) != all_ids:
            raise InvalidInput("ordered_ids must match the full list set")
        now = _now()
        for pos, lid in enumerate(ordered_ids):
            self.conn.execute(
                "UPDATE lists SET position = ?, updated_at = ? WHERE id = ?",
                (pos, now, lid),
            )
        self.conn.commit()
        return {"ok": True}

    # -- Einstellungen -----------------------------------------------------
    def get_setting(self, key: str, default: Any = None) -> Any:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def get_all_settings(self) -> dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def set_setting(self, key: str, value: Any) -> dict[str, Any]:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        self.conn.commit()
        return {"ok": True}

    def is_empty(self) -> bool:
        row = self.conn.execute("SELECT COUNT(*) AS c FROM lists").fetchone()
        return row["c"] == 0

    # -- Seed --------------------------------------------------------------
    def seed_if_empty(self) -> None:
        """Erststart-Initialisierung: nur Standard-Einstellungen, keine Demo-Daten.

        Die App startet bewusst mit leeren Listen. Es werden weiterhin die
        Standard-Settings und der 'seeded'-Marker geschrieben, damit der nächste
        Start nichts neu anlegt (und der Killswitch-Zustand aus Nachtrag N10
        weiterhin leer bleibt).
        """
        if not self.is_empty():
            return
        if self.get_setting("seeded") == "true":
            return
        # Standard-Einstellungen plus 'seeded'-Marker (siehe oben).
        for k, v in _DEFAULT_SETTINGS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        self.conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('seeded', 'true')"
        )
        self.conn.commit()

# Der DB-basierte ``killswitch`` (Zeilen loeschen + VACUUM) ist mit Phase 8
# ersatzlos entfernt (N11.8.1/B.8.7): der Killswitch ist jetzt eine reine
# DATEI-Operation ohne Schluessel (tasks.db.enc + .bak + Metadaten + Pepper +
# Arbeitsordner loeschen), umgesetzt in ``security.Session.delete_vault_files``.
# Eine Zeilen-Loeschung waere mit dem gesperrten Zustand (keine Schluessel im
# RAM) und mit G13 (Killswitch gerade gesperrt erlaubt) unvereinbar.


# Standard-Einstellungen: schreibt der Erststart-Seed in einen frisch
# angelegten (leeren) Tresor.
_DEFAULT_SETTINGS = {
    "accent": "#d97757",
    # Theme folgt per Default dem Windows-Hell/Dunkel-Zustand (N11.6, B.6);
    # der frühere Bool-Key `dark` ist damit ersatzlos entfallen.
    "theme": "auto",
    "density": "comfortable",
    "sidebar": "open",
    # Sidebar-Startbreite. Wird NUR beim Erststart-Seed geschrieben; sobald der
    # Nutzer die Sidebar einmal gezogen hat, gilt ausschliesslich sein
    # gespeicherter Wert (``set_setting`` klemmt ihn auf 180 bis 520, G20/V5).
    # Muss zu SIDEBAR_WIDTH_DEFAULT in frontend/app.js passen.
    "sidebarWidth": "300",
    "exportDone": "true",
    "sound": "true",
    "autoLock": "15",
}
