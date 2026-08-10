"""Gemeinsame Test-Vorbereitung (Bauplan Phase 9, Punkt 1).

**Die wichtigste Regel dieser Datei: kein Test fasst echte Nutzerdaten an.**
Die App arbeitet mit drei Dingen ausserhalb des Projektordners, und jedes davon
wird hier auf einen Wegwerf-Ort umgebogen, bevor irgendein Test laeuft:

- ``%LOCALAPPDATA%`` (daraus leiten sich ``config.json`` und der
  Arbeitsordner ab) zeigt auf einen Temp-Ordner,
- der **DPAPI-Pepper** (G18) wird durch einen festen Testwert ersetzt; die
  echten ``keyring``-Aufrufe werden nie ausgefuehrt, sonst koennte ein Test
  (etwa der Killswitch) den Pepper des Nutzers loeschen und dessen Tresor
  unwiderruflich unlesbar machen,
- die Argon2id-Kosten werden auf den unteren Rand des erlaubten Bereichs
  gesetzt (64 MiB, t=1), sonst braeuchte jede Ableitung ~256 MiB und Sekunden.
  Der Bereich selbst wird dabei nicht verlassen (N11.4.3), die Konstruktion
  bleibt also dieselbe wie im Betrieb.
"""
from __future__ import annotations

import os
import sys

import pytest

CODE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CODE not in sys.path:
    sys.path.insert(0, CODE)

from backend import config as config_module  # noqa: E402
from backend import security as security_module  # noqa: E402

# Fester Test-Pepper: 32 Bytes, damit derive_keys dieselbe Konstruktion faehrt
# wie im Betrieb (nur eben ohne Credential Manager).
TEST_PEPPER = bytes(range(32))

# Guenstige, aber gueltige KDF-Parameter (Akzeptanzbereich 64 bis 512 MiB).
FAST_PARAMS = security_module.KdfParams(memory_cost=65536, time_cost=1,
                                        parallelism=1, hash_len=32)


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Jeder Test bekommt ein eigenes ``%LOCALAPPDATA%`` und einen Fake-Pepper."""
    local = tmp_path / "LocalAppData"
    local.mkdir()
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    # Pepper: nie den echten Credential Manager anfassen (weder lesen noch
    # schreiben noch loeschen).
    monkeypatch.setattr(security_module, "get_pepper",
                        lambda create=False: bytearray(TEST_PEPPER))
    monkeypatch.setattr(security_module, "pepper_exists", lambda: True)
    monkeypatch.setattr(security_module, "delete_pepper", lambda: None)

    # Sicherheitsnetz: sollte trotzdem jemand keyring aufrufen, faellt es auf.
    import keyring

    def _blocked(*_a, **_k):
        raise AssertionError("Test hat den echten Credential Manager benutzt")

    monkeypatch.setattr(keyring, "get_password", _blocked)
    monkeypatch.setattr(keyring, "set_password", _blocked)
    monkeypatch.setattr(keyring, "delete_password", _blocked)

    # Konfigpfad haengt am (bereits umgebogenen) LOCALAPPDATA, aber lieber
    # ausdruecklich: ein Test darf nie die config.json des Nutzers ueberschreiben.
    cfg = local / "NoaToDo" / "config.json"
    monkeypatch.setattr(config_module, "config_path", lambda: str(cfg))
    yield


_REAL_PARAMS = security_module.KdfParams


def _params_factory(*args, **kwargs):
    """Ersatz fuer ``KdfParams``: ohne Argumente billig, mit Argumenten echt.

    ``Vault.create``/``change_passphrase`` rufen ``KdfParams()`` (Soll-Kosten),
    ``parse_header`` dagegen ``KdfParams(mem, t, par, hlen)`` mit den Werten
    aus der Datei. Nur der erste Fall wird verbilligt, sonst wuerde der Test
    den Kopf falsch lesen.
    """
    if args or kwargs:
        return _REAL_PARAMS(*args, **kwargs)
    return FAST_PARAMS


@pytest.fixture
def fast_kdf(monkeypatch):
    """Argon2id auf 64 MiB / t=1 herunterdrehen (nur Laufzeit, gleiche Logik)."""
    monkeypatch.setattr(security_module, "KdfParams", _params_factory)
    yield FAST_PARAMS


@pytest.fixture
def vault_path(tmp_path):
    return str(tmp_path / "vault" / "tasks.db.enc")


@pytest.fixture
def open_vault(vault_path, fast_kdf):
    """Ein frisch angelegter, offener Tresor mit guenstigen KDF-Kosten."""
    os.makedirs(os.path.dirname(vault_path), exist_ok=True)
    vault = security_module.Vault.create(vault_path, "correct horse battery")
    yield vault
    try:
        vault.close()
    except Exception:
        pass
