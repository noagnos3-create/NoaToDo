"""Gate G13: die Sperre ist eine Allowlist, keine Ausnahmeliste.

Der Test iteriert ueber **alle** oeffentlichen Bridge-Methoden der ``Api``
(dynamisch, damit eine neu ergaenzte Methode auffaellt statt still
durchzurutschen) und prueft im gesperrten Zustand:

- alles ausserhalb von ``ALLOWED_WHEN_LOCKED`` liefert ``locked``,
- ``get_state()`` verraet gesperrt nichts ausser ``{"locked": true}``,
- die erlaubten Methoden werden **nicht** vom Decorator blockiert (sie muessen
  gerade gesperrt funktionieren: entsperren, beenden, Killswitch, Onboarding).
"""
from __future__ import annotations

import inspect

import pytest

from backend import api as api_module
from backend import security as security_module

# Platzhalter je Argumenttyp: der Aufruf soll ueberhaupt bis zum Decorator
# kommen: was danach passiert, interessiert diesen Test nicht.
DUMMY = {
    "list_id": "l-x", "id": "l-x", "task_id": "t-x", "target_list_id": "l-y",
    "name": "x", "text": "x", "fields": {"text": "x"}, "ordered_ids": ["l-x"],
    "format": "md", "key": "theme", "value": "auto", "flag": True,
    "passphrase": "x" * 12, "old": "x" * 12, "new": "y" * 12, "path": "C:/x",
}


@pytest.fixture
def locked_api():
    api = api_module.Api(security_module.Session())
    api.locked = True
    return api


def _public_methods():
    for name, fn in inspect.getmembers(api_module.Api, inspect.isfunction):
        if name.startswith("_"):
            continue
        yield name, fn


def _call(api, name, fn):
    kwargs = {}
    for param in list(inspect.signature(fn).parameters)[1:]:
        kwargs[param] = DUMMY.get(param, "x")
    return getattr(api, name)(**kwargs)


def test_gesperrt_liefert_alles_ausserhalb_der_allowlist_locked(locked_api):
    geprueft = 0
    for name, fn in _public_methods():
        if name in api_module.ALLOWED_WHEN_LOCKED:
            continue
        res = _call(locked_api, name, fn)
        assert isinstance(res, dict), f"{name} liefert kein Dict"
        assert res.get("error") == "locked", f"{name} ist gesperrt nicht blockiert"
        geprueft += 1
    assert geprueft >= 15, "die Bridge ist kleiner als erwartet, Test pruefen"


def test_get_state_verraet_gesperrt_nichts(locked_api):
    assert locked_api.get_state() == {"locked": True}


def test_erlaubte_methoden_werden_nicht_blockiert(locked_api, monkeypatch):
    """Die Allowlist muss gesperrt wirklich durchlassen (N10.5/N11.13).

    Geprueft wird nur, dass der Decorator sie nicht abweist; die Methoden
    selbst duerfen mit einem fachlichen Fehler antworten (etwa ``vault``,
    weil hier keine Tresordatei liegt). Die zwei Methoden mit echter
    Aussenwirkung (Fenster schliessen, Datenvernichtung) werden dafuer auf
    ihren Vertrag beobachtet statt ausgefuehrt.
    """
    beobachtet = []
    monkeypatch.setattr(api_module.Api, "quit_app",
                        lambda self: beobachtet.append("quit") or {"ok": True})
    monkeypatch.setattr(api_module.Api, "killswitch",
                        lambda self: beobachtet.append("kill") or {"ok": True})

    for name in sorted(api_module.ALLOWED_WHEN_LOCKED):
        fn = getattr(api_module.Api, name)
        if name in ("quit_app", "killswitch"):
            getattr(locked_api, name)()
            continue
        if name == "choose_vault_dir":
            continue    # oeffnet einen nativen Dialog, hier nicht aufrufbar
        res = _call(locked_api, name, fn)
        assert not (isinstance(res, dict) and res.get("error") == "locked"), \
            f"{name} steht in der Allowlist, wird aber blockiert"
    assert sorted(beobachtet) == ["kill", "quit"]


def test_allowlist_ist_genau_die_vereinbarte_menge():
    """N10.5/N11.13: die Menge ist verbindlich, nicht beliebig erweiterbar."""
    assert api_module.ALLOWED_WHEN_LOCKED == {
        "unlock", "quit_app", "killswitch", "get_state",
        "get_boot_state", "choose_vault_dir", "create_vault", "reset_vault",
    }
    # change_passphrase gehoert ausdruecklich NICHT dazu (braucht den
    # entsperrten Zustand).
    assert "change_passphrase" not in api_module.ALLOWED_WHEN_LOCKED
    assert "activity_ping" not in api_module.ALLOWED_WHEN_LOCKED
