"""Beenden-Sequenz und Datei-Killswitch (G35 / G25 / B.8.7, Befund V12).

Der Killswitch ist die einzige Stelle, die absichtlich Nutzerdaten vernichtet;
entsprechend genau wird geprueft, dass er (a) wirklich alles Genannte entfernt
und (b) der Folgestart im Onboarding landet. Dazu die Schluessel-Hygiene aus
G25: nach der Sequenz stehen die Schluesselpuffer auf Null.
"""
from __future__ import annotations

import os

import pytest

from backend import config as config_module
from backend import security as security_module


@pytest.fixture(autouse=True)
def frische_teardown_sperre():
    """``run_teardown`` merkt sich prozessweit ein bereits laufendes Beenden.

    Das ist im Betrieb genau richtig (Idempotenz, Schritt 1 der Sequenz), wuerde
    hier aber den zweiten Test verschlucken. Deshalb vor jedem Test zuruecksetzen.
    """
    security_module._teardown_terminal = False
    yield
    security_module._teardown_terminal = False


def test_killswitch_entfernt_tresor_bak_und_konfig(open_vault):
    enc = open_vault.enc_path
    open_vault.db.add_list("Weg damit")
    open_vault.flush()
    open_vault.flush()                       # zweiter Wrap legt die .bak an
    config_module.save_config(config_module.new_config(enc))
    assert os.path.exists(enc) and os.path.exists(enc + ".bak")

    session = security_module.Session()
    session.vault = open_vault
    security_module.run_teardown("killswitch", session)

    assert not os.path.exists(enc)
    assert not os.path.exists(enc + ".bak")
    assert not os.path.exists(config_module.config_path())
    # Ohne Konfig ist der naechste Start ein Erststart (Onboarding, N11.8.2).
    assert config_module.load_config() is None


def test_killswitch_nullt_die_schluessel(open_vault):
    """G25: nach der Sequenz stehen Schluessel und Master-Secret auf Null."""
    session = security_module.Session()
    session.vault = open_vault
    aes = open_vault._aes_key
    chacha = open_vault._chacha_key
    assert any(aes) and any(chacha)
    security_module.run_teardown("killswitch", session)
    assert not any(aes), "aes_key wurde nicht genullt"
    assert not any(chacha), "chacha_key wurde nicht genullt"
    assert session.vault is None


def test_sperren_schreibt_den_stand_und_laesst_die_datei_stehen(open_vault):
    """Gegenprobe: ``lock`` vernichtet nichts, es sichert den Stand (G17/G16)."""
    enc = open_vault.enc_path
    open_vault.db.add_list("Bleibt")
    session = security_module.Session()
    session.vault = open_vault
    security_module.run_teardown("lock", session)
    assert os.path.exists(enc)
    v = security_module.Vault.unlock(enc, "correct horse battery")
    try:
        assert [x["name"] for x in v.db.get_lists_with_tasks()] == ["Bleibt"]
    finally:
        v.close()


def test_arbeitsdatei_ist_nach_dem_sperren_weg(open_vault):
    """N11.9: die (verschluesselte) Arbeitsdatei ueberlebt die Sperre nicht."""
    work = open_vault.work_path
    assert work and os.path.exists(work)
    session = security_module.Session()
    session.vault = open_vault
    security_module.run_teardown("lock", session)
    assert not os.path.exists(work)


def test_es_gibt_genau_eine_teardown_routine():
    """G35: eine Sequenz, kein zweiter handgeschriebener Ausgang."""
    import inspect

    quelle = inspect.getsource(security_module)
    assert quelle.count("\ndef run_teardown(") == 1
    # Die Gruende sind die vereinbarten neun Ausgaenge (N11.11).
    for grund in ("lock", "autolock", "quit", "panic_finish", "killswitch",
                  "reset", "atexit"):
        assert f'"{grund}"' in quelle
