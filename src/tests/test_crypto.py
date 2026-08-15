"""Krypto-Kern: Ableitung, Behaelter, Wechsel, Wiederherstellung.

Deckt aus Phase 9, Punkt 1:
- **G15** Domaenentrennung der Schluessel und die implizite Passphrase-Pruefung
  (kein gespeicherter Hash, ein Tag-Fehler ist die Antwort),
- **G16** Kopfformat, frische Nonce je Wrap, Kopf als AEAD-``associated_data``,
  Parameter-Akzeptanzbereich, ``.bak``-Wiederherstellung nach simuliertem
  Absturz,
- **G18** der Pepper geht wirklich in die Ableitung ein (ein anderer Pepper
  oeffnet den Tresor nicht, "fremdes Windows-Konto"),
- **G28** das Arbeits-Artefakt traegt weder SQLite-Klartextkopf noch Aufgabentext,
- **N11.3/U8c** nach dem Passphrase-Wechsel ist **weder** ``tasks.db.enc``
  **noch** ``tasks.db.enc.bak`` mit der alten Passphrase zu oeffnen.
"""
from __future__ import annotations

import os
import shutil

import pytest

from backend import security as security_module
from conftest import FAST_PARAMS, TEST_PEPPER

PASS = "correct horse battery"


def test_domaenentrennung_der_schluessel(fast_kdf):
    """G15/U18: aes_key und chacha_key sind verschieden und reproduzierbar."""
    salt = b"\x01" * security_module.SALT_LEN
    aes1, chacha1 = security_module.derive_keys(PASS, TEST_PEPPER, salt, FAST_PARAMS)
    aes2, chacha2 = security_module.derive_keys(PASS, TEST_PEPPER, salt, FAST_PARAMS)
    assert bytes(aes1) == bytes(aes2) and bytes(chacha1) == bytes(chacha2)
    assert bytes(aes1) != bytes(chacha1)          # keine rohen Scheiben
    assert len(aes1) == 32 and len(chacha1) == 32
    # Anderes Salt, andere Schluessel.
    aes3, _ = security_module.derive_keys(PASS, TEST_PEPPER, b"\x02" * 16, FAST_PARAMS)
    assert bytes(aes3) != bytes(aes1)
    # Anderer Pepper, andere Schluessel (G18: Bindung ans Windows-Konto).
    aes4, _ = security_module.derive_keys(PASS, bytes(32), salt, FAST_PARAMS)
    assert bytes(aes4) != bytes(aes1)


def test_container_kopf_und_frische_nonce(open_vault):
    """G16: Magic ``NOA1``, und zwei Wraps tragen verschiedene Nonces."""
    path = open_vault.enc_path
    with open(path, "rb") as fh:
        blob1 = fh.read()
    assert blob1[:4] == b"NOA1"
    params, salt, nonce1, header, ciphertext = security_module.read_container(path)
    assert params == FAST_PARAMS
    open_vault.db.add_list("etwas aendern")
    open_vault.flush()
    _p, _s, nonce2, _h, _c = security_module.read_container(path)
    assert nonce1 != nonce2


def test_kopf_ist_authentifiziert(open_vault, fast_kdf):
    """V1: der Kopf geht als associated_data in die AEAD, ein Bit-Dreher faellt auf."""
    path = open_vault.enc_path
    params, salt, nonce, header, ciphertext = security_module.read_container(path)
    aes, chacha = security_module.derive_keys(PASS, TEST_PEPPER, salt, params)
    # Mit echtem Kopf: geht auf.
    assert security_module.unwrap(chacha, header, nonce, ciphertext)
    # Ein veraenderter Kopf (gleiche Laenge) laesst die Pruefung scheitern.
    gefaelscht = bytearray(header)
    gefaelscht[-1] ^= 0x01
    with pytest.raises(security_module.WrongPassphrase):
        security_module.unwrap(chacha, bytes(gefaelscht), nonce, ciphertext)


def test_falsche_passphrase_ist_ein_tag_fehler(open_vault, fast_kdf):
    """G15: kein gespeicherter Hash, die AEAD entscheidet."""
    path = open_vault.enc_path
    open_vault.close()
    with pytest.raises(security_module.WrongPassphrase):
        security_module.Vault.unlock(path, "falsch falsch falsch")
    v = security_module.Vault.unlock(path, PASS)
    v.close()


def test_parameter_ausserhalb_des_bereichs_gelten_als_unlesbar():
    """N11.4.3: ein aufgeblaehter Kopf fuehrt NIE zu einem Argon2-Lauf."""
    riesig = security_module.KdfParams(memory_cost=8 * 1024 * 1024, time_cost=3,
                                       parallelism=4, hash_len=32)
    blob = security_module.pack_header(riesig, b"\x00" * 16, b"\x00" * 12)
    with pytest.raises(security_module.VaultError):
        security_module.parse_header(blob)


def test_bak_rettet_nach_simuliertem_absturz(open_vault, fast_kdf):
    """G16: die Sicherungsgeneration oeffnet mit derselben Passphrase."""
    path = open_vault.enc_path
    open_vault.db.add_list("Wichtig")
    open_vault.flush()          # legt beim Rotieren die .bak an
    open_vault.db.add_list("Noch wichtiger")
    open_vault.flush()
    open_vault.close()
    bak = path + ".bak"
    assert os.path.exists(bak)
    # "Absturz mitten im Schreiben": das Primaer ist Schrott.
    with open(path, "wb") as fh:
        fh.write(b"kaputt")
    with pytest.raises(security_module.VaultError):
        security_module.Vault.unlock(path, PASS)
    shutil.copyfile(bak, path)
    v = security_module.Vault.unlock(path, PASS)
    try:
        namen = [x["name"] for x in v.db.get_lists_with_tasks()]
        assert "Wichtig" in namen
    finally:
        v.close()


def test_g28_arbeitsdatei_zeigt_keinen_klartext(open_vault):
    """G28 (V12): das Arbeits-Artefakt enthaelt weder SQLite-Kopf noch Task-Text."""
    geheim = "Kanarienvogel-Zeichenkette-4711"
    lst = open_vault.db.add_list("L")
    open_vault.db.add_task(lst["id"], geheim)
    open_vault.flush()
    ziele = [open_vault.work_path, open_vault.enc_path]
    for ziel in ziele:
        assert ziel and os.path.exists(ziel), ziel
        with open(ziel, "rb") as fh:
            roh = fh.read()
        assert b"SQLite format 3" not in roh, ziel
        assert geheim.encode("utf-8") not in roh, ziel
        assert geheim.encode("utf-16-le") not in roh, ziel


def test_passphrase_wechsel_macht_den_alten_stand_unlesbar(open_vault, fast_kdf):
    """N11.3 a-d / U8c: weder .enc noch .bak oeffnen danach mit der alten Passphrase."""
    path = open_vault.enc_path
    lst = open_vault.db.add_list("Bleibt erhalten")
    open_vault.db.add_task(lst["id"], "Aufgabe")
    open_vault.flush()

    neues_salt = os.urandom(security_module.SALT_LEN)
    neue_params = FAST_PARAMS
    neu_aes, neu_chacha = security_module.derive_keys(
        "ganz neue passphrase", TEST_PEPPER, neues_salt, neue_params)
    open_vault.rewrap_with(neu_aes, neu_chacha, neue_params, neues_salt)
    open_vault.close()

    for datei in (path, path + ".bak"):
        assert os.path.exists(datei)
        with pytest.raises(security_module.WrongPassphrase):
            security_module.Vault.unlock(datei, PASS)

    v = security_module.Vault.unlock(path, "ganz neue passphrase")
    try:
        listen = v.db.get_lists_with_tasks()
        assert listen[0]["name"] == "Bleibt erhalten"
        assert listen[0]["open"][0]["text"] == "Aufgabe"
        # Frisches Salt (a) und Soll-Parameter (d).
        assert v.salt == neues_salt
        assert v.params == neue_params
    finally:
        v.close()


def test_secure_delete_entfernt_und_ueberschreibt(tmp_path):
    """U21/N11.3 (c): kein blankes os.remove auf Tresor-Artefakten."""
    ziel = tmp_path / "geheim.bin"
    ziel.write_bytes(b"streng geheimer inhalt" * 100)
    security_module.secure_delete(str(ziel))
    assert not ziel.exists()
    # Ein nicht existierender Pfad ist kein Fehler (Aufrufer duerfen blind loeschen).
    security_module.secure_delete(str(tmp_path / "gibtsnicht"))
