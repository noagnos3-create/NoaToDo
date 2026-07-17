"""Datenschicht für NoaToDo (Bauplan Phase 1).

Schicht 1 der Verschlüsselung (SQLCipher / AES-256) sitzt direkt hier: nach
``connect()`` wird sofort ``PRAGMA key`` gesetzt. Die äußere ChaCha20-Schicht und
die echte Argon2-Schlüsselableitung kommen in Phase 8 (``backend/security.py``).

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

    def __init__(self, path: str, aes_key: str):
        self.path = path
        # True, solange der oeffentliche Entwicklungs-Schluessel benutzt wird
        # (Phase 1, DEV_AES_KEY). Steuert die ehrliche Statusanzeige (Gate G22):
        # solange dies True ist, darf die UI keine echte Verschluesselung
        # behaupten. In Phase 8 wird der Schluessel aus der Passphrase abgeleitet,
        # dann ist dies False.
        self.dev_key = aes_key == DEV_AES_KEY
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.conn = sqlcipher3.connect(path, check_same_thread=False)
        # Schicht 1: Schlüssel SOFORT nach dem Öffnen setzen.
        # PRAGMA erlaubt keine Parameter-Bindung -> Wert quoten/escapen.
        # (aes_key ist intern abgeleitet, nie Nutzer-Roheingabe.)
        self.conn.execute("PRAGMA key = '%s'" % aes_key.replace("'", "''"))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlcipher3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._drop_legacy_columns()

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

    # -- Aufgaben schreiben ------------------------------------------------
    def add_task(self, list_id: str, text: str) -> dict[str, Any]:
        now = _now()
        tid = _new_id("t")
        pos = self.conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS p FROM tasks WHERE list_id = ?",
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
            "SELECT done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise KeyError(task_id)
        new_done = 0 if row["done"] else 1
        self.conn.execute(
            "UPDATE tasks SET done = ?, updated_at = ? WHERE id = ?",
            (new_done, _now(), task_id),
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

    # -- Killswitch (Nachtrag N10) ------------------------------------------
    def killswitch(self) -> dict[str, Any]:
        """Löscht unwiderruflich alle Nutzerdaten aus der Datenbank.

        Wird nur vom Panik-Endschirm aus aufgerufen (zweistufig bestätigt).
        Leert lists/tasks/settings vollständig, schreibt die
        Standard-Settings neu und setzt den 'seeded'-Marker, damit der nächste
        Start wie ein Erststart ohne Demo-Daten aussieht. ``secure_delete``
        überschreibt gelöschte Seiten mit Nullen, ``VACUUM`` baut die Datei neu
        auf, damit nichts in freien Seiten liegen bleibt. Ehrliche Einordnung:
        auf SSD/NTFS ist das noch kein forensisches Secure-Delete; das kommt mit
        der Phase-8-Härtung (In-Memory-DB G6, .enc-Neuaufbau G16).
        """
        self.conn.execute("PRAGMA secure_delete = ON")
        self.conn.execute("DELETE FROM tasks")
        self.conn.execute("DELETE FROM lists")
        self.conn.execute("DELETE FROM settings")
        for k, v in _DEFAULT_SETTINGS.items():
            self.conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)", (k, v)
            )
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES ('seeded', 'true')"
        )
        self.conn.commit()
        self.conn.execute("VACUUM")
        return {"ok": True}


# Standard-Einstellungen: schreibt der Erststart-Seed und der Killswitch (N10)
# identisch, damit eine gekillte DB von einem Erststart nicht unterscheidbar ist.
_DEFAULT_SETTINGS = {
    "accent": "#d97757",
    "dark": "true",
    "density": "comfortable",
    "sidebar": "open",
}


# Entwicklungs-Standardschlüssel (Phase 1). In Phase 8 wird er aus der
# Passphrase via Argon2id abgeleitet und nie gespeichert.
DEV_AES_KEY = "noatodo-dev-key-phase1"

_DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tasks.db"
)


def connect(aes_key: str = DEV_AES_KEY, path: str = _DEFAULT_DB_PATH) -> Database:
    """SQLCipher-Arbeitskopie öffnen, Schema sicherstellen, ggf. seeden."""
    db = Database(path, aes_key)
    db.seed_if_empty()
    return db
