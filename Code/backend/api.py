"""Die ``js_api``-Bridge zwischen Frontend und Backend (Bauplan Phase 2 / B.2).

Jede öffentliche Methode wird vom Frontend als ``pywebview.api.<name>(...)``
aufgerufen und gibt ein JSON-serialisierbares Dict/Listen-Objekt zurück. Tritt ein
Fehler auf, kommt ``{"error": code, "message": ...}`` zurück (Fehlerkonvention B.2).

In Phase 2 sind alle lokalen Methoden echt (lesen/schreiben die DB). Die
Microsoft- und Sicherheits-Methoden sind sinnvolle Platzhalter und werden in den
Phasen 7–11 ausgefüllt.
"""
from __future__ import annotations

import functools
import os
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
        self.window = None  # von main.py gesetzt, für Backend->Frontend-Events

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
    def add_task(self, list_id: str, text: str, meta: str | None = None) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"error": "invalid", "message": "Aufgabentext darf nicht leer sein."}
        return self.db.add_task(list_id, text, meta)

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
        # md / txt
        lines: list[str] = []
        if fmt == "md":
            lines.append(f"# {lst['name']}")
            lines.append("")
            for t in lst["open"]:
                meta = f" ({t['meta']})" if t.get("meta") else ""
                lines.append(f"- [ ] {t['text']}{meta}")
            for t in lst["done"]:
                meta = f" ({t['meta']})" if t.get("meta") else ""
                lines.append(f"- [x] {t['text']}{meta}")
            ext = "md"
        else:  # txt
            lines.append(lst["name"])
            lines.append("=" * len(lst["name"]))
            for t in lst["open"]:
                meta = f" — {t['meta']}" if t.get("meta") else ""
                lines.append(f"[ ] {t['text']}{meta}")
            for t in lst["done"]:
                meta = f" — {t['meta']}" if t.get("meta") else ""
                lines.append(f"[x] {t['text']}{meta}")
            ext = "txt"
        return {"filename": f"{safe}.{ext}", "content": "\n".join(lines)}

    @bridge
    def copy_list(self, list_id: str) -> dict[str, Any]:
        result = self.export_list(list_id, "txt")
        if "error" in result:
            return result
        return {"text": result["content"]}

    # =====================================================================
    # Einstellungen
    # =====================================================================
    @bridge
    def set_setting(self, key: str, value: Any) -> dict[str, Any]:
        return self.db.set_setting(key, value)

    # =====================================================================
    # Status / Diagnose
    # =====================================================================
    @bridge
    def get_status(self) -> dict[str, Any]:
        db_path = getattr(self.db, "path", None)
        size = os.path.getsize(db_path) if db_path and os.path.exists(db_path) else 0
        return {
            "db": {
                "path": db_path,
                "size": size,
                "size_human": f"{size / 1024:.1f} KB" if size else "0 KB",
            },
            "encryption": {
                "layer1": "SQLCipher · AES-256",
                "layer2": "ChaCha20-Poly1305 · Argon2id",
                "active": True,
            },
            "graph": {"scope": "Tasks.Read", "signed_in": False, "token": "offline"},
            "last_sync": None,
            "runtime": {"webview2": _webview2_version()},
        }

    # =====================================================================
    # Microsoft (Stubs — Phasen 8/9)
    # =====================================================================
    @bridge
    def sign_in(self) -> dict[str, Any]:
        return {"error": "not_implemented", "message": "Microsoft-Login folgt in Phase 8."}

    @bridge
    def sign_out(self) -> dict[str, Any]:
        return {"ok": True}

    @bridge
    def sync_now(self) -> dict[str, Any]:
        return {"changed": 0, "lists": 0}

    @bridge
    def set_online(self, flag: bool) -> dict[str, Any]:
        self.online = bool(flag)
        return {"online": self.online}

    # =====================================================================
    # Sicherheit (Stubs — Phase 11)
    # =====================================================================
    @bridge
    def lock(self) -> dict[str, Any]:
        self.locked = True
        return {"locked": True}

    @bridge
    def unlock(self, passphrase: str) -> dict[str, Any]:
        # Phase 11: Argon2-Hash prüfen + Schlüssel ableiten. Vorerst immer offen.
        self.locked = False
        return {"ok": True}

    @bridge
    def panic(self) -> dict[str, Any]:
        self.locked = True
        self.online = False
        return {"locked": True}


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
