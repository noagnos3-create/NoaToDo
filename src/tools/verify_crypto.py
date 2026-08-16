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

"""Krypto-Kern-Beweis der Phase 8 (G28 + Roundtrip + Haertung), standalone.

Runbar ohne pytest (es gibt noch kein Test-Setup, CLAUDE.md; die Phase-9-
Testliste verankert den G28-Beweis spaeter als echten pytest, V12). Nutzt einen
ISOLIERTEN Test-Pepper und einen Temp-Pfad, der echte Tresor des Nutzers bleibt
also unangetastet.

Beweist:
- Anlegen -> Wiederoeffnen mit korrekter Passphrase (Dat, Roundtrip),
- G28: weder ``tasks.db.enc`` noch die SQLCipher-Arbeitsdatei zeigen einen
  SQLite-Klartext-Header (``SQLite format 3``) oder Task-/Listentext im
  Roh-Byte-Dump,
- falsche Passphrase -> ``WrongPassphrase`` (AEAD-Tag, kein gespeicherter Hash),
- Body-Manipulation -> sauberer Fehler statt stillem Durchgehen,
- Header-DoS-Schutz: aufgeblaehter ``memory_cost`` -> ``vault`` vor jedem Argon2,
- Passphrase-Wechsel: die alte Passphrase oeffnet danach weder Primaerdatei noch
  ``.bak`` (N11.3 c),
- deterministische Rate-Limit-Stufenfunktion (N11.4.1).

Aufruf:  .\venv\Scripts\python.exe tools\verify_crypto.py
Exit 0 = Beweis erbracht.
"""
from __future__ import annotations

import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from backend import security as sec  # noqa: E402

FAILS: list[str] = []
TASK = "Geheime Aufgabe: Steuererklaerung 2026 abgeben"
LIST = "Privat-Tresor-Liste"


def check(name: str, cond: bool) -> None:
    print(("PASS" if cond else "FAIL"), name, flush=True)
    if not cond:
        FAILS.append(name)


def main() -> int:
    # Pepper und Arbeitsordner isolieren: der echte Tresor bleibt unberuehrt.
    test_pepper = bytearray(b"\x11" * 32)
    sec.get_pepper = lambda create=False: bytearray(test_pepper)
    tmp = tempfile.mkdtemp(prefix="noatodo-crypto-")
    sec.work_dir = lambda: os.path.join(tmp, "work")
    enc = os.path.join(tmp, "tasks.db.enc")

    # 1. Anlegen + Daten + persistieren
    v = sec.Vault.create(enc, "correct horse battery")
    lid = v.db.add_list(LIST)["id"]
    v.db.add_task(lid, TASK)
    v.flush()
    check("enc-Datei existiert", os.path.exists(enc))
    work_path = v.work_path
    v.close()
    check("Arbeitsdatei nach close entfernt", bool(work_path) and not os.path.exists(work_path))

    # 2. G28-Beweis auf tasks.db.enc
    with open(enc, "rb") as fh:
        blob = fh.read()
    check("enc: kein SQLite-Klartext-Header", b"SQLite format 3" not in blob)
    check("enc: kein Task-Text im Rohdump", TASK.encode() not in blob)
    check("enc: kein Listenname im Rohdump", LIST.encode() not in blob)
    check("enc: Magic NOA1 vorn", blob[:4] == b"NOA1")

    # 3. Wiederoeffnen + G28-Beweis auf der Arbeitsdatei
    v2 = sec.Vault.unlock(enc, "correct horse battery")
    lists = v2.db.get_lists_with_tasks()
    check("Roundtrip: Listenname + Task-Text",
          bool(lists) and lists[0]["name"] == LIST
          and lists[0]["open"] and lists[0]["open"][0]["text"] == TASK)
    with open(v2.work_path, "rb") as fh:
        wblob = fh.read()
    check("work: kein SQLite-Klartext-Header", b"SQLite format 3" not in wblob)
    check("work: kein Task-Text im Rohdump", TASK.encode() not in wblob)
    v2.close()

    # 4. Falsche Passphrase
    try:
        sec.Vault.unlock(enc, "totally wrong pass")
        check("falsche Passphrase -> WrongPassphrase", False)
    except sec.WrongPassphrase:
        check("falsche Passphrase -> WrongPassphrase", True)

    # 5. Body-Manipulation -> Fehler (AEAD)
    tampered = bytearray(blob)
    tampered[-1] ^= 0xFF
    tenc = os.path.join(tmp, "tampered.enc")
    with open(tenc, "wb") as fh:
        fh.write(tampered)
    try:
        sec.Vault.unlock(tenc, "correct horse battery")
        check("Body-Manipulation -> Fehler", False)
    except (sec.WrongPassphrase, sec.VaultError):
        check("Body-Manipulation -> Fehler", True)

    # 6. Header-DoS: aufgeblaehter memory_cost -> vault, kein Argon2
    hdr = bytearray(blob[:sec.HEADER_LEN])
    struct.pack_into("<I", hdr, 7, 16 * 1024 * 1024)  # 16 GiB in KiB
    try:
        sec.parse_header(bytes(hdr) + blob[sec.HEADER_LEN:])
        check("aufgeblaehter Header -> VaultError", False)
    except sec.VaultError:
        check("aufgeblaehter Header -> VaultError", True)

    # 7. Passphrase-Wechsel: alte Passphrase oeffnet danach nichts mehr
    v3 = sec.Vault.unlock(enc, "correct horse battery")
    v3.flush()  # sicherstellen, dass eine .bak mit dem ALTEN Schluessel existiert
    new_salt = os.urandom(sec.SALT_LEN)
    new_aes, new_chacha = sec.derive_keys("brand new passphrase 12+", test_pepper,
                                          new_salt, sec.KdfParams())
    v3.rewrap_with(new_aes, new_chacha, sec.KdfParams(), new_salt)
    v3.close()
    try:
        sec.Vault.unlock(enc, "correct horse battery")
        check("nach Wechsel: alte Passphrase scheitert (primaer)", False)
    except sec.WrongPassphrase:
        check("nach Wechsel: alte Passphrase scheitert (primaer)", True)
    if os.path.exists(enc + ".bak"):
        try:
            sec.Vault.unlock(enc + ".bak", "correct horse battery")
            check("nach Wechsel: alte Passphrase scheitert (.bak)", False)
        except (sec.WrongPassphrase, sec.VaultError):
            check("nach Wechsel: alte Passphrase scheitert (.bak)", True)
    v4 = sec.Vault.unlock(enc, "brand new passphrase 12+")
    check("nach Wechsel: neue Passphrase oeffnet + Daten da",
          v4.db.get_lists_with_tasks()[0]["open"][0]["text"] == TASK)
    v4.close()

    # 8. Rate-Limit-Stufenfunktion deterministisch (N11.4.1)
    check("ladder 3 frei", sec.ladder_stage(3) == (0, 0))
    check("ladder 4 -> 10s", sec.ladder_stage(4) == (1, 10))
    check("ladder 6 -> 30s", sec.ladder_stage(6) == (2, 30))
    check("ladder Deckel 10h", sec.ladder_stage(999)[1] == 36000)

    print(flush=True)
    if FAILS:
        print("FAILURES:", FAILS, flush=True)
        return 1
    print("ALL CRYPTO CORE CHECKS PASSED (G28-Beweis erbracht)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
